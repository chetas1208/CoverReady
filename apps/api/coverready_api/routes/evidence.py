from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.db import get_session
from coverready_api.schemas.api import EvidenceItem, EvidenceUpdate, ManualEvidenceCreate, MissingRequirement, ReviewActionResponse
from coverready_api.services.events import publish_workspace_event
from coverready_api.services.scoring import latest_scorecard, recalculate_scorecard
from coverready_api.services.workspace import require_business_profile


router = APIRouter()


@router.get("/evidence", response_model=list[EvidenceItem])
def list_evidence(business_profile_id: str | None = None, session: Session = Depends(get_session)) -> list[EvidenceItem]:
    business = require_business_profile(session, business_profile_id)
    evidence_items = session.scalars(
        select(models.EvidenceItem).where(models.EvidenceItem.business_profile_id == business.id).order_by(models.EvidenceItem.field)
    ).all()
    return [EvidenceItem.model_validate(item) for item in evidence_items]


@router.get("/evidence/{evidence_id}", response_model=EvidenceItem)
def get_evidence(evidence_id: str, session: Session = Depends(get_session)) -> EvidenceItem:
    item = session.get(models.EvidenceItem, evidence_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence item not found.")
    return EvidenceItem.model_validate(item)


@router.post("/evidence", response_model=ReviewActionResponse)
def create_manual_evidence(
    payload: ManualEvidenceCreate,
    request: Request,
    session: Session = Depends(get_session),
) -> ReviewActionResponse:
    workspace = session.get(models.Workspace, payload.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    business = session.get(models.BusinessProfile, workspace.id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    if not payload.field_name.strip() or not payload.normalized_value.strip():
        raise HTTPException(status_code=422, detail="Manual evidence requires a field and normalized value.")

    document = _manual_evidence_document(session, workspace)
    item = models.EvidenceItem(
        business_profile_id=business.id,
        workspace_id=workspace.id,
        document_id=document.id,
        category=payload.category.strip(),
        field=payload.field_name.strip(),
        field_name=payload.field_name.strip(),
        value=payload.normalized_value.strip(),
        normalized_value=payload.normalized_value.strip(),
        raw_value=(payload.raw_value or payload.normalized_value).strip(),
        evidence_strength=payload.evidence_strength.value,
        confidence=payload.confidence,
        source_snippet=payload.source_snippet,
        expires_on=payload.expires_on,
        status="active",
        review_status="approved",
    )
    session.add(item)
    session.flush()
    session.add(
        models.ManualReviewEvent(
            workspace_id=workspace.id,
            document_id=document.id,
            evidence_item_id=item.id,
            action="created",
            before_json=None,
            after_json=_evidence_event_payload(item),
            actor="workspace_user",
        )
    )
    session.commit()
    publish_workspace_event(request.app.state.settings, workspace.id, "evidence.created", {"evidence_id": item.id})
    scorecard = recalculate_scorecard(session, request.app.state.settings, business.id)
    session.refresh(item)
    return ReviewActionResponse(evidence=EvidenceItem.model_validate(item), scorecard=scorecard)


@router.patch("/evidence/{evidence_id}", response_model=ReviewActionResponse)
def update_evidence(
    evidence_id: str,
    payload: EvidenceUpdate,
    request: Request,
    session: Session = Depends(get_session),
) -> ReviewActionResponse:
    item = _require_evidence(session, evidence_id)
    before = _evidence_event_payload(item)
    updates = payload.model_dump(exclude_unset=True)
    if "field_name" in updates and updates["field_name"] is not None:
        field_name = updates["field_name"].strip()
        if not field_name:
            raise HTTPException(status_code=422, detail="Field name cannot be empty.")
        item.field = field_name
        item.field_name = field_name
    if "normalized_value" in updates and updates["normalized_value"] is not None:
        normalized_value = updates["normalized_value"].strip()
        if not normalized_value:
            raise HTTPException(status_code=422, detail="Normalized value cannot be empty.")
        item.value = normalized_value
        item.normalized_value = normalized_value
    if "raw_value" in updates:
        item.raw_value = updates["raw_value"]
    if "category" in updates and updates["category"] is not None:
        category = updates["category"].strip()
        if not category:
            raise HTTPException(status_code=422, detail="Category cannot be empty.")
        item.category = category
    if "evidence_strength" in updates and updates["evidence_strength"] is not None:
        item.evidence_strength = updates["evidence_strength"].value
    if "confidence" in updates and updates["confidence"] is not None:
        item.confidence = updates["confidence"]
    if "source_snippet" in updates:
        item.source_snippet = updates["source_snippet"]
    if "expires_on" in updates:
        item.expires_on = updates["expires_on"]
    if "is_conflicting" in updates and updates["is_conflicting"] is not None:
        item.is_conflicting = updates["is_conflicting"]

    item.review_status = "edited"
    item.status = "active"
    session.add(
        models.ManualReviewEvent(
            workspace_id=item.workspace_id,
            document_id=item.document_id,
            evidence_item_id=item.id,
            action="edited",
            before_json=before,
            after_json=_evidence_event_payload(item),
            actor="workspace_user",
        )
    )
    session.commit()
    publish_workspace_event(request.app.state.settings, item.workspace_id, "evidence.updated", {"evidence_id": item.id})
    scorecard = recalculate_scorecard(session, request.app.state.settings, item.business_profile_id)
    session.refresh(item)
    return ReviewActionResponse(evidence=EvidenceItem.model_validate(item), scorecard=scorecard)


@router.post("/evidence/{evidence_id}/approve", response_model=ReviewActionResponse)
def approve_evidence(evidence_id: str, request: Request, session: Session = Depends(get_session)) -> ReviewActionResponse:
    item = _require_evidence(session, evidence_id)
    if not (item.normalized_value or item.value or "").strip():
        raise HTTPException(status_code=422, detail="Evidence must have a normalized value before approval.")
    before = _evidence_event_payload(item)
    item.review_status = "approved"
    item.status = "active"
    session.add(
        models.ManualReviewEvent(
            workspace_id=item.workspace_id,
            document_id=item.document_id,
            evidence_item_id=item.id,
            action="approved",
            before_json=before,
            after_json=_evidence_event_payload(item),
            actor="workspace_user",
        )
    )
    session.commit()
    publish_workspace_event(request.app.state.settings, item.workspace_id, "evidence.reviewed", {"evidence_id": item.id, "review_status": "approved"})
    scorecard = recalculate_scorecard(session, request.app.state.settings, item.business_profile_id)
    session.refresh(item)
    return ReviewActionResponse(evidence=EvidenceItem.model_validate(item), scorecard=scorecard)


@router.post("/evidence/{evidence_id}/reject", response_model=ReviewActionResponse)
def reject_evidence(evidence_id: str, request: Request, session: Session = Depends(get_session)) -> ReviewActionResponse:
    item = _require_evidence(session, evidence_id)
    before = _evidence_event_payload(item)
    item.review_status = "rejected"
    item.status = "rejected"
    session.add(
        models.ManualReviewEvent(
            workspace_id=item.workspace_id,
            document_id=item.document_id,
            evidence_item_id=item.id,
            action="rejected",
            before_json=before,
            after_json=_evidence_event_payload(item),
            actor="workspace_user",
        )
    )
    session.commit()
    publish_workspace_event(request.app.state.settings, item.workspace_id, "evidence.reviewed", {"evidence_id": item.id, "review_status": "rejected"})
    scorecard = recalculate_scorecard(session, request.app.state.settings, item.business_profile_id)
    session.refresh(item)
    return ReviewActionResponse(evidence=EvidenceItem.model_validate(item), scorecard=scorecard)


@router.get("/missing-documents", response_model=list[MissingRequirement])
def list_missing_documents(
    business_profile_id: str | None = None, session: Session = Depends(get_session)
) -> list[MissingRequirement]:
    business = require_business_profile(session, business_profile_id)
    scorecard = latest_scorecard(session, business.id)
    if scorecard is None:
        return []
    latest_scorecard_row = session.scalar(
        select(models.Scorecard)
        .where(models.Scorecard.business_profile_id == business.id)
        .order_by(models.Scorecard.created_at.desc())
    )
    if latest_scorecard_row is None:
        return []
    rows = session.scalars(
        select(models.MissingRequirement).where(models.MissingRequirement.scorecard_id == latest_scorecard_row.id)
    ).all()
    return [
        MissingRequirement(
            rule_id=row.rule_id,
            label=row.label,
            dimension=row.dimension,
            severity=row.severity,
            status=row.status,
            cap_id=row.cap_id,
            source_evidence_ids=list(row.source_evidence_ids or []),
        )
        for row in rows
    ]


def _require_evidence(session: Session, evidence_id: str) -> models.EvidenceItem:
    item = session.get(models.EvidenceItem, evidence_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence item not found.")
    return item


def _manual_evidence_document(session: Session, workspace: models.Workspace) -> models.Document:
    existing = session.scalar(
        select(models.Document).where(
            models.Document.workspace_id == workspace.id,
            models.Document.document_type == "manual_evidence",
            models.Document.source_filename == "Manual reviewer note",
        )
    )
    if existing:
        return existing
    document = models.Document(
        business_profile_id=workspace.id,
        workspace_id=workspace.id,
        document_type="manual_evidence",
        status="ready",
        processing_status="ready",
        latest_job_stage="ready",
        origin="live",
        source_filename="Manual reviewer note",
        mime_type="text/plain",
        checksum=None,
        storage_path=None,
        summary="Manual evidence entered by reviewer.",
    )
    session.add(document)
    session.flush()
    return document


def _evidence_event_payload(item: models.EvidenceItem) -> dict:
    return {
        "id": item.id,
        "field": item.field_name or item.field,
        "value": item.normalized_value or item.value,
        "status": item.status,
        "review_status": item.review_status,
        "evidence_strength": item.evidence_strength,
    }
