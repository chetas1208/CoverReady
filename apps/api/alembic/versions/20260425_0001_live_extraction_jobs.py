"""live extraction jobs

Revision ID: 20260425_0001
Revises:
Create Date: 2026-04-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260425_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("industry_code", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("state", sa.String(length=16), nullable=True),
        sa.Column("origin", sa.String(length=32), nullable=False, server_default="live"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        """
        INSERT INTO workspaces (id, name, address, industry_code, state, origin, created_at, updated_at)
        SELECT id, name, address, industry_code, state, origin, created_at, updated_at
        FROM business_profiles
        """
    )

    op.add_column("documents", sa.Column("workspace_id", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("processing_status", sa.String(length=32), nullable=False, server_default="uploaded"))
    op.add_column("documents", sa.Column("latest_job_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_documents_workspace_id", "documents", "workspaces", ["workspace_id"], ["id"])
    op.execute("UPDATE documents SET workspace_id = business_profile_id WHERE workspace_id IS NULL")

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False, server_default="document_extraction"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_foreign_key("fk_documents_latest_job_id", "documents", "processing_jobs", ["latest_job_id"], ["id"])

    op.create_table(
        "document_pages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("image_path", sa.String(length=512), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("provider_page_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.add_column("extraction_runs", sa.Column("job_id", sa.String(), nullable=True))
    op.add_column("extraction_runs", sa.Column("model_id", sa.String(length=128), nullable=True))
    op.add_column("extraction_runs", sa.Column("prompt_version", sa.String(length=64), nullable=True))
    op.add_column("extraction_runs", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("extraction_runs", sa.Column("fallback_reason", sa.Text(), nullable=True))
    op.create_foreign_key("fk_extraction_runs_job_id", "extraction_runs", "processing_jobs", ["job_id"], ["id"])

    op.add_column("evidence_items", sa.Column("workspace_id", sa.String(), nullable=True))
    op.add_column("evidence_items", sa.Column("field_name", sa.String(length=128), nullable=True))
    op.add_column("evidence_items", sa.Column("normalized_value", sa.Text(), nullable=True))
    op.add_column("evidence_items", sa.Column("raw_value", sa.Text(), nullable=True))
    op.add_column("evidence_items", sa.Column("source_bbox_json", sa.JSON(), nullable=True))
    op.add_column("evidence_items", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("evidence_items", sa.Column("extractor_model_id", sa.String(length=128), nullable=True))
    op.add_column("evidence_items", sa.Column("prompt_version", sa.String(length=64), nullable=True))
    op.add_column("evidence_items", sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))
    op.add_column("evidence_items", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending_review"))
    op.create_foreign_key("fk_evidence_items_workspace_id", "evidence_items", "workspaces", ["workspace_id"], ["id"])
    op.execute("UPDATE evidence_items SET workspace_id = business_profile_id WHERE workspace_id IS NULL")
    op.execute("UPDATE evidence_items SET field_name = field WHERE field_name IS NULL")
    op.execute("UPDATE evidence_items SET normalized_value = value WHERE normalized_value IS NULL")

    op.create_table(
        "manual_review_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("evidence_item_id", sa.String(), sa.ForeignKey("evidence_items.id"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])
    op.create_index("ix_evidence_items_document_id", "evidence_items", ["document_id"])
    op.create_index("ix_evidence_items_workspace_id", "evidence_items", ["workspace_id"])
    op.create_index("ix_evidence_items_business_profile_id", "evidence_items", ["business_profile_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_items_business_profile_id", table_name="evidence_items")
    op.drop_index("ix_evidence_items_workspace_id", table_name="evidence_items")
    op.drop_index("ix_evidence_items_document_id", table_name="evidence_items")
    op.drop_index("ix_processing_jobs_status", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_document_id", table_name="processing_jobs")
    op.drop_index("ix_documents_workspace_id", table_name="documents")
    op.drop_table("manual_review_events")
    op.drop_column("evidence_items", "review_status")
    op.drop_column("evidence_items", "status")
    op.drop_column("evidence_items", "prompt_version")
    op.drop_column("evidence_items", "extractor_model_id")
    op.drop_column("evidence_items", "page_number")
    op.drop_column("evidence_items", "source_bbox_json")
    op.drop_column("evidence_items", "raw_value")
    op.drop_column("evidence_items", "normalized_value")
    op.drop_column("evidence_items", "field_name")
    op.drop_column("evidence_items", "workspace_id")
    op.drop_column("extraction_runs", "fallback_reason")
    op.drop_column("extraction_runs", "confidence")
    op.drop_column("extraction_runs", "prompt_version")
    op.drop_column("extraction_runs", "model_id")
    op.drop_column("extraction_runs", "job_id")
    op.drop_table("document_pages")
    op.drop_table("processing_jobs")
    op.drop_column("documents", "latest_job_id")
    op.drop_column("documents", "processing_status")
    op.drop_column("documents", "workspace_id")
    op.drop_table("workspaces")
