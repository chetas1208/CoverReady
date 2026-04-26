from __future__ import annotations

import json
from datetime import date

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.config.settings import Settings


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def clear_workspace(session: Session) -> None:
    session.execute(update(models.Document).values(latest_job_id=None))
    for model in (
        models.ManualReviewEvent,
        models.ClaimEvidenceLink,
        models.Claim,
        models.MissingRequirement,
        models.ScoreReasonItem,
        models.Scorecard,
        models.EvidenceItem,
        models.ExtractionRun,
        models.OCRRun,
        models.DocumentAsset,
        models.DocumentPage,
        models.ProcessingJob,
        models.Document,
        models.ScenarioRun,
        models.TranslatorRun,
        models.BrokerPacket,
        models.AppSetting,
        models.Workspace,
        models.BusinessProfile,
    ):
        session.execute(delete(model))
    session.commit()


def seed_demo_workspace(session: Session, settings: Settings) -> models.BusinessProfile:
    clear_workspace(session)
    payload = json.loads(settings.demo_seed_path.read_text())

    profile_data = payload["business_profile"]
    business = models.BusinessProfile(
        id=profile_data["id"],
        name=profile_data["name"],
        address=profile_data["address"],
        industry_code=profile_data["industry_code"],
        state=profile_data["state"],
        origin=profile_data["origin"],
    )
    session.add(business)
    session.add(
        models.Workspace(
            id=profile_data["id"],
            name=profile_data["name"],
            address=profile_data["address"],
            industry_code=profile_data["industry_code"],
            state=profile_data["state"],
            origin=profile_data["origin"],
        )
    )
    session.flush()

    for raw_document in payload["documents"]:
        session.add(
            models.Document(
                id=raw_document["id"],
                business_profile_id=business.id,
                workspace_id=business.id,
                document_type=raw_document["document_type"],
                status=raw_document["status"],
                processing_status=raw_document["status"],
                origin=raw_document["origin"],
                source_filename=raw_document["source_filename"],
                mime_type=raw_document["mime_type"],
                checksum=raw_document["checksum"],
                summary=raw_document.get("summary"),
                document_date=_parse_date(raw_document.get("document_date")),
                expiration_date=_parse_date(raw_document.get("expiration_date")),
            )
        )

    session.flush()

    for raw_asset in payload["assets"]:
        session.add(
            models.DocumentAsset(
                document_id=raw_asset["document_id"],
                asset_type=raw_asset["asset_type"],
                page_number=raw_asset.get("page_number"),
                text_content=raw_asset.get("text_content"),
                preview_label=raw_asset.get("preview_label"),
            )
        )

    for raw_evidence in payload["evidence_items"]:
        session.add(
            models.EvidenceItem(
                id=raw_evidence["id"],
                business_profile_id=business.id,
                workspace_id=business.id,
                document_id=raw_evidence["document_id"],
                category=raw_evidence["category"],
                field=raw_evidence["field"],
                field_name=raw_evidence["field"],
                value=raw_evidence.get("value"),
                normalized_value=raw_evidence.get("value"),
                raw_value=raw_evidence.get("value"),
                evidence_strength=raw_evidence["evidence_strength"],
                confidence=raw_evidence["confidence"],
                source_snippet=raw_evidence.get("source_snippet"),
                page_ref=raw_evidence.get("page_ref"),
                expires_on=_parse_date(raw_evidence.get("expires_on")),
                is_conflicting=raw_evidence.get("is_conflicting", False),
            )
        )

    for raw_document in payload["documents"]:
        matching_asset = next((asset for asset in payload["assets"] if asset["document_id"] == raw_document["id"]), None)
        session.add(
            models.OCRRun(
                document_id=raw_document["id"],
                provider="seed-fixture",
                status="completed",
                extracted_text=matching_asset["text_content"] if matching_asset else None,
            )
        )
        session.add(
            models.ExtractionRun(
                document_id=raw_document["id"],
                provider="seed-fixture",
                status="completed",
                raw_response={"summary": raw_document.get("summary")},
            )
        )

    session.add(models.AppSetting(key="workspace_mode", value_json={"mode": "fixture"}))
    session.commit()
    session.refresh(business)
    return business
