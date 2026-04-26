from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from coverready_api.config.settings import Settings


class Base(DeclarativeBase):
    pass


def build_engine(settings: Settings):
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    return create_engine(settings.database_url, future=True, connect_args=connect_args)


def build_session_maker(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def init_db(engine) -> None:
    from coverready_api import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_compat_columns(engine)


def _ensure_sqlite_compat_columns(engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "documents" not in tables:
        return

    def columns(table: str) -> set[str]:
        return {column["name"] for column in inspector.get_columns(table)}

    statements: list[str] = []
    document_columns = columns("documents")
    if "workspace_id" not in document_columns:
        statements.append("ALTER TABLE documents ADD COLUMN workspace_id VARCHAR")
    if "processing_status" not in document_columns:
        statements.append("ALTER TABLE documents ADD COLUMN processing_status VARCHAR(32) NOT NULL DEFAULT 'uploaded'")
    if "latest_job_id" not in document_columns:
        statements.append("ALTER TABLE documents ADD COLUMN latest_job_id VARCHAR")
    if "latest_job_stage" not in document_columns:
        statements.append("ALTER TABLE documents ADD COLUMN latest_job_stage VARCHAR(32)")
    if "latest_job_attempt" not in document_columns:
        statements.append("ALTER TABLE documents ADD COLUMN latest_job_attempt INTEGER")
    if "latest_error" not in document_columns:
        statements.append("ALTER TABLE documents ADD COLUMN latest_error TEXT")
    if "updated_at" not in document_columns:
        statements.append("ALTER TABLE documents ADD COLUMN updated_at DATETIME")

    if "extraction_runs" in tables:
        extraction_columns = columns("extraction_runs")
        for name, ddl in {
            "job_id": "VARCHAR",
            "model_id": "VARCHAR(128)",
            "prompt_version": "VARCHAR(64)",
            "confidence": "FLOAT",
            "fallback_reason": "TEXT",
        }.items():
            if name not in extraction_columns:
                statements.append(f"ALTER TABLE extraction_runs ADD COLUMN {name} {ddl}")

    if "evidence_items" in tables:
        evidence_columns = columns("evidence_items")
        for name, ddl in {
            "workspace_id": "VARCHAR",
            "field_name": "VARCHAR(128)",
            "normalized_value": "TEXT",
            "raw_value": "TEXT",
            "source_bbox_json": "JSON",
            "page_number": "INTEGER",
            "extractor_model_id": "VARCHAR(128)",
            "prompt_version": "VARCHAR(64)",
            "status": "VARCHAR(32) NOT NULL DEFAULT 'active'",
            "review_status": "VARCHAR(32) NOT NULL DEFAULT 'pending_review'",
        }.items():
            if name not in evidence_columns:
                statements.append(f"ALTER TABLE evidence_items ADD COLUMN {name} {ddl}")

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO workspaces (id, name, address, industry_code, state, origin, created_at, updated_at)
                SELECT id, name, address, industry_code, state, origin, created_at, updated_at
                FROM business_profiles
                """
            )
        )
        connection.execute(text("UPDATE documents SET workspace_id = business_profile_id WHERE workspace_id IS NULL"))
        connection.execute(text("UPDATE documents SET updated_at = created_at WHERE updated_at IS NULL"))
        if "evidence_items" in tables:
            connection.execute(text("UPDATE evidence_items SET workspace_id = business_profile_id WHERE workspace_id IS NULL"))
            connection.execute(text("UPDATE evidence_items SET field_name = field WHERE field_name IS NULL"))
            connection.execute(text("UPDATE evidence_items SET normalized_value = value WHERE normalized_value IS NULL"))


def get_session(request: Request) -> Generator[Session, None, None]:
    session_maker: sessionmaker[Session] = request.app.state.session_maker
    session = session_maker()
    try:
        yield session
    finally:
        session.close()
