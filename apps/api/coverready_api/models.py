from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from coverready_api.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    industry_code: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    state: Mapped[str | None] = mapped_column(String(16))
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="live")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    industry_code: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    state: Mapped[str | None] = mapped_column(String(16))
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="live")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    business_profile_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id"), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"))
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    latest_job_id: Mapped[str | None] = mapped_column(ForeignKey("processing_jobs.id"))
    latest_job_stage: Mapped[str | None] = mapped_column(String(32))
    latest_job_attempt: Mapped[int | None] = mapped_column(Integer)
    latest_error: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="live")
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    checksum: Mapped[str | None] = mapped_column(String(128))
    storage_path: Mapped[str | None] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text)
    document_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, default="document_extraction")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    @property
    def stage(self) -> str:
        return self.status

    @property
    def completed_at(self) -> datetime | None:
        return self.finished_at

    @property
    def progress_percent(self) -> int:
        return {
            "queued": 5,
            "uploaded": 10,
            "extracting": 35,
            "normalizing": 60,
            "scoring": 85,
            "ready": 100,
            "failed": 100,
        }.get(self.status, 0)


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(512))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    provider_page_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DocumentAsset(Base):
    __tablename__ = "document_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    text_content: Mapped[str | None] = mapped_column(Text)
    preview_label: Mapped[str | None] = mapped_column(String(255))


class OCRRun(Base):
    __tablename__ = "ocr_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("processing_jobs.id"))
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    fallback_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_response: Mapped[dict | list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    business_profile_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id"), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    field: Mapped[str] = mapped_column(String(128), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(128))
    value: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    raw_value: Mapped[str | None] = mapped_column(Text)
    evidence_strength: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_snippet: Mapped[str | None] = mapped_column(Text)
    source_bbox_json: Mapped[dict | None] = mapped_column(JSON)
    page_ref: Mapped[str | None] = mapped_column(String(32))
    page_number: Mapped[int | None] = mapped_column(Integer)
    expires_on: Mapped[date | None] = mapped_column(Date)
    is_conflicting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extractor_model_id: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    business_profile_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_evidence_ids: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ClaimEvidenceLink(Base):
    __tablename__ = "claim_evidence_links"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), nullable=False)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_items.id"), nullable=False)
    relationship: Mapped[str] = mapped_column(String(32), nullable=False, default="supports")


class Scorecard(Base):
    __tablename__ = "scorecards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    business_profile_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id"), nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    uncapped_total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    ruleset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    subscores_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    caps_json: Mapped[list | None] = mapped_column(JSON)
    top_risk_drivers: Mapped[list | None] = mapped_column(JSON)
    quick_wins: Mapped[list | None] = mapped_column(JSON)
    missing_documents: Mapped[list | None] = mapped_column(JSON)
    manual_review_needed: Mapped[list | None] = mapped_column(JSON)
    explanation_json: Mapped[dict | None] = mapped_column(JSON)
    explanation_source: Mapped[str | None] = mapped_column(String(64))
    explanation_model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ScoreReasonItem(Base):
    __tablename__ = "score_reason_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    scorecard_id: Mapped[str] = mapped_column(ForeignKey("scorecards.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    points_awarded: Mapped[float] = mapped_column(Float, nullable=False)
    points_possible: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    plain_reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_evidence_ids: Mapped[list[str] | None] = mapped_column(JSON)


class MissingRequirement(Base):
    __tablename__ = "missing_requirements"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    scorecard_id: Mapped[str] = mapped_column(ForeignKey("scorecards.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    cap_id: Mapped[str | None] = mapped_column(String(128))
    source_evidence_ids: Mapped[list[str] | None] = mapped_column(JSON)


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    business_profile_id: Mapped[str | None] = mapped_column(ForeignKey("business_profiles.id"))
    scenario_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TranslatorRun(Base):
    __tablename__ = "translator_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    business_profile_id: Mapped[str | None] = mapped_column(ForeignKey("business_profiles.id"))
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class BrokerPacket(Base):
    __tablename__ = "broker_packets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    business_profile_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id"), nullable=False)
    packet_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ManualReviewEvent(Base):
    __tablename__ = "manual_review_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    evidence_item_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_items.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    before_json: Mapped[dict | list | None] = mapped_column(JSON)
    after_json: Mapped[dict | list | None] = mapped_column(JSON)
    actor: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[dict | list | str | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
