from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.config.settings import Settings
from coverready_api.schemas.api import EvidenceItem, ProofVaultExtraction


KNOWN_DOCUMENT_TYPES = {
    "license": "business_license",
    "lease": "lease",
    "inspection": "inspection_report",
    "maintenance": "maintenance_receipt",
    "fire": "fire_safety_record",
    "training": "training_record",
    "declaration": "declarations_page",
    "policy": "policy_excerpt",
    "storefront": "storefront_photo",
    "questionnaire": "operations_questionnaire",
}


def guess_document_type(filename: str) -> str:
    lowered = filename.lower()
    for keyword, document_type in KNOWN_DOCUMENT_TYPES.items():
        if keyword in lowered:
            return document_type
    suffix = Path(filename).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        return "property_photo"
    return "other"


def extract_document(session: Session, settings: Settings, document: models.Document) -> ProofVaultExtraction:
    business = session.get(models.BusinessProfile, document.business_profile_id)
    evidence_rows = session.scalars(
        select(models.EvidenceItem).where(models.EvidenceItem.document_id == document.id).order_by(models.EvidenceItem.field)
    ).all()

    evidence_items = [
        EvidenceItem(
            id=row.id,
            category=row.category,
            field=row.field,
            value=row.value,
            evidence_strength=row.evidence_strength,
            confidence=row.confidence,
            source_snippet=row.source_snippet,
            document_id=row.document_id,
            page_ref=row.page_ref,
            expires_on=row.expires_on,
            is_conflicting=row.is_conflicting,
        )
        for row in evidence_rows
    ]

    underwriting_flags: list[str] = []
    missing_information: list[str] = []
    if any(item.evidence_strength in {"expired", "conflicting"} for item in evidence_items):
        underwriting_flags.append("Document contains expired or conflicting evidence that needs review.")
    if not evidence_items:
        missing_information.append("No explicit evidence could be extracted without OCR/model support.")

    extraction = ProofVaultExtraction(
        document_type=document.document_type or guess_document_type(document.source_filename),
        document_date=document.document_date,
        expiration_date=document.expiration_date,
        business_name=business.name if business else None,
        address=business.address if business else None,
        evidence_items=evidence_items,
        underwriting_flags=underwriting_flags,
        missing_information=missing_information,
    )

    session.add(
        models.ExtractionRun(
            document_id=document.id,
            provider="heuristic-fallback" if document.origin == "live" else "seed-fixture",
            status="completed" if evidence_items else "manual_review_required",
            raw_response=extraction.model_dump(mode="json"),
        )
    )
    session.commit()
    return extraction
