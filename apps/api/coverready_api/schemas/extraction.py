from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from coverready_api.schemas.api import EvidenceStrength


DocumentType = Literal[
    "business_license",
    "safety_certificate",
    "maintenance_receipt",
    "declarations_page",
    "inspection_report",
    "generic_document",
]


class ExtractionBBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    xmin: float = Field(ge=0.0, le=1.0)
    ymin: float = Field(ge=0.0, le=1.0)
    xmax: float = Field(ge=0.0, le=1.0)
    ymax: float = Field(ge=0.0, le=1.0)
    coordinate_system: Literal["relative"] = "relative"

    @field_validator("xmax")
    @classmethod
    def xmax_after_xmin(cls, value: float, info):
        xmin = info.data.get("xmin")
        if xmin is not None and value < xmin:
            raise ValueError("xmax must be greater than or equal to xmin")
        return value

    @field_validator("ymax")
    @classmethod
    def ymax_after_ymin(cls, value: float, info):
        ymin = info.data.get("ymin")
        if ymin is not None and value < ymin:
            raise ValueError("ymax must be greater than or equal to ymin")
        return value


class ExtractRegion(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str | None = None
    bbox: ExtractionBBox | None = None
    region_type: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ExtractPage(BaseModel):
    model_config = ConfigDict(extra="allow")

    page_number: int = Field(ge=1)
    text: str | None = None
    regions: list[ExtractRegion] = []
    width: int | None = None
    height: int | None = None
    image_path: str | None = None
    provider_page_id: str | None = None


class ExtractResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    provider: str
    model_id: str
    prompt_version: str
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    pages: list[ExtractPage]
    raw_payload: dict
    fallback_reason: str | None = None


class ExtractRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    document_id: str
    document_type: DocumentType
    source_path: str
    mime_type: str | None = None
    filename: str | None = None


class NormalizedEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    field_name: str
    normalized_value: str | None
    raw_value: str | None
    evidence_strength: EvidenceStrength
    confidence: float = Field(ge=0.0, le=1.0)
    source_snippet: str | None
    source_bbox_json: ExtractionBBox | None = None
    page_number: int | None = Field(default=None, ge=1)
    extractor_model_id: str
    prompt_version: str
    status: Literal["pending_review", "approved", "rejected"] = "pending_review"
    expires_on: date | None = None
    is_conflicting: bool = False


class NormalizedExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: DocumentType
    evidence_items: list[NormalizedEvidenceItem]
    underwriting_flags: list[str] = []
    missing_information: list[str] = []
