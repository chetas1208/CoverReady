from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceStrength(str, Enum):
    verified = "verified"
    partially_verified = "partially_verified"
    weak_evidence = "weak_evidence"
    missing = "missing"
    expired = "expired"
    conflicting = "conflicting"


class EvidenceCategory(str, Enum):
    license = "license"
    safety = "safety"
    maintenance = "maintenance"
    operations = "operations"
    policy = "policy"
    property = "property"
    claims = "claims"
    other = "other"


class DocumentOrigin(str, Enum):
    demo = "demo"
    live = "live"


class DimensionName(str, Enum):
    documentation_completeness = "documentation_completeness"
    property_safety_readiness = "property_safety_readiness"
    operational_controls = "operational_controls"
    coverage_alignment = "coverage_alignment"
    renewal_readiness = "renewal_readiness"


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EvidenceItem(BaseSchema):
    id: str
    category: str
    field: str
    field_name: str | None = None
    value: str | None
    normalized_value: str | None = None
    raw_value: str | None = None
    evidence_strength: EvidenceStrength
    confidence: float
    source_evidence: str | None = Field(alias="source_snippet", default=None)
    source_bbox_json: dict | None = None
    document_id: str | None = None
    page_ref: str | None = None
    page_number: int | None = None
    expires_on: date | None = None
    is_conflicting: bool = False
    extractor_model_id: str | None = None
    prompt_version: str | None = None
    status: str | None = None
    review_status: str | None = None
    created_at: datetime | None = None


class WorkspaceCreate(BaseSchema):
    name: str
    address: str | None = None
    industry_code: str = "general"
    state: str | None = None
    origin: str = "live"


class WorkspaceUpdate(BaseSchema):
    name: str | None = None
    address: str | None = None
    industry_code: str | None = None
    state: str | None = None


class WorkspaceRead(BaseSchema):
    id: str
    name: str
    address: str | None
    industry_code: str
    state: str | None
    origin: str
    created_at: datetime
    updated_at: datetime


class ProofVaultExtraction(BaseSchema):
    document_type: str | None
    document_date: date | None
    expiration_date: date | None
    business_name: str | None
    address: str | None
    evidence_items: list[EvidenceItem]
    underwriting_flags: list[str]
    missing_information: list[str]


class DocumentSummary(BaseSchema):
    id: str
    business_profile_id: str
    workspace_id: str | None = None
    document_type: str
    status: str
    processing_status: str | None = None
    latest_job_id: str | None = None
    latest_job_stage: str | None = None
    latest_job_attempt: int | None = None
    latest_error: str | None = None
    origin: str
    source_filename: str
    mime_type: str | None
    checksum: str | None
    summary: str | None
    document_date: date | None
    expiration_date: date | None
    created_at: datetime
    updated_at: datetime | None = None


class DocumentAsset(BaseSchema):
    id: str
    document_id: str
    asset_type: str
    page_number: int | None
    text_content: str | None
    preview_label: str | None


class DocumentDetail(DocumentSummary):
    assets: list[DocumentAsset] = []
    evidence_items: list[EvidenceItem] = []


class ProcessingJobRead(BaseSchema):
    id: str
    workspace_id: str | None
    document_id: str
    job_type: str
    status: str
    stage: str = "extraction"
    attempt_count: int
    max_attempts: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    completed_at: datetime | None = None
    progress_percent: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):  # type: ignore[override]
        if hasattr(obj, "__dict__") and not hasattr(obj, "stage"):
            # DB model doesn't have stage/progress_percent/completed_at — derive them
            data = {c.key: getattr(obj, c.key) for c in obj.__table__.columns}
            status = data.get("status", "queued")
            data.setdefault("stage", "extraction")
            data.setdefault("progress_percent", 100 if status == "ready" else 0)
            data.setdefault("completed_at", data.get("finished_at"))
            return cls(**data)
        return super().model_validate(obj, *args, **kwargs)


class EvidenceUpdate(BaseSchema):
    category: str | None = None
    field_name: str | None = None
    normalized_value: str | None = None
    raw_value: str | None = None
    evidence_strength: EvidenceStrength | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_snippet: str | None = None
    expires_on: date | None = None
    is_conflicting: bool | None = None


class ManualEvidenceCreate(BaseSchema):
    workspace_id: str
    category: str
    field_name: str
    normalized_value: str
    raw_value: str | None = None
    evidence_strength: EvidenceStrength = EvidenceStrength.partially_verified
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    source_snippet: str | None = None
    expires_on: date | None = None


class DocumentStatusResponse(BaseSchema):
    document: DocumentSummary
    job: ProcessingJobRead | None


class UploadWithJobResponse(BaseSchema):
    document: DocumentSummary
    job: ProcessingJobRead


class ClaimRecord(BaseSchema):
    id: str
    key: str
    title: str
    value: str | None
    status: str
    source_evidence_ids: list[str] = []


class ScoreReason(BaseSchema):
    rule_id: str
    dimension: DimensionName
    points_awarded: float
    points_possible: float
    status: EvidenceStrength
    plain_reason: str
    source_evidence_ids: list[str] = []


class ScoreCap(BaseSchema):
    cap_id: str
    title: str
    max_total_score: int
    reason: str
    triggered_by_rule_ids: list[str] = []
    triggered_by_fields: list[str] = []


class QuickWin(BaseSchema):
    action: str
    expected_score_impact: str
    effort: str
    reason: str


class MissingRequirement(BaseSchema):
    rule_id: str
    label: str
    dimension: DimensionName
    severity: str
    status: EvidenceStrength
    cap_id: str | None = None
    source_evidence_ids: list[str] = []


class DimensionScore(BaseSchema):
    score: int
    max_score: int
    reason: str
    items: list[ScoreReason]


class Subscores(BaseSchema):
    documentation_completeness: DimensionScore
    property_safety_readiness: DimensionScore
    operational_controls: DimensionScore
    coverage_alignment: DimensionScore
    renewal_readiness: DimensionScore


class Scorecard(BaseSchema):
    id: str | None = None
    business_profile_id: str | None = None
    total_score: int
    uncapped_total_score: int
    score_caps: list[ScoreCap]
    subscores: Subscores
    top_risk_drivers: list[str]
    quick_wins: list[QuickWin]
    missing_documents: list[str]
    manual_review_needed: list[str]
    ruleset_id: str
    ruleset_version: str
    input_hash: str
    explanation_source: str


class ReviewActionResponse(BaseSchema):
    evidence: EvidenceItem
    scorecard: Scorecard


class ScoreProof(BaseSchema):
    scorecard_id: str
    reasons: list[ScoreReason]
    evidence_lookup: dict[str, EvidenceItem]


class DemoState(BaseSchema):
    business_profile_id: str
    business_name: str
    documents_count: int
    evidence_count: int
    latest_scorecard: Scorecard | None


class TranslatorRequest(BaseSchema):
    clause_text: str
    business_profile_id: str | None = None


class TranslatorResult(BaseSchema):
    plain_english_summary: str
    why_it_matters: str
    questions_to_verify: list[str]
    suggested_next_steps: list[str]


class ScenarioRequest(BaseSchema):
    scenario: str
    business_profile_id: str | None = None


class ScenarioSimulation(BaseSchema):
    scenario: str
    likely_score_direction: str
    estimated_impact_summary: str
    why: str
    still_needed: list[str]


class BrokerPacketPreview(BaseSchema):
    business_name: str
    address: str | None
    score_summary: str
    top_strengths: list[str]
    missing_documents: list[str]
    next_best_actions: list[str]
    documents: list[DocumentSummary]


class UploadResponse(BaseSchema):
    document: DocumentSummary
    extraction_status: str


class HealthResponse(BaseSchema):
    status: str
    database_backend: str
    ollama_configured: bool
