from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.db import get_session
from coverready_api.schemas.api import (
    DocumentSummary,
    ProcessingJobRead,
    Scorecard,
    UploadWithJobResponse,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)
from coverready_api.services.document_ingestion import DocumentIngestionService, create_workspace_with_business_profile
from coverready_api.services.events import publish_workspace_event
from coverready_api.services.scoring import latest_scorecard, recalculate_scorecard


router = APIRouter(prefix="/workspaces")


@router.get("", response_model=list[WorkspaceRead])
def list_workspaces(session: Session = Depends(get_session)) -> list[WorkspaceRead]:
    workspaces = session.scalars(
        select(models.Workspace).order_by(models.Workspace.name)
    ).all()
    return [WorkspaceRead.model_validate(ws) for ws in workspaces]


@router.post("", response_model=WorkspaceRead)
def create_workspace(payload: WorkspaceCreate, request: Request, session: Session = Depends(get_session)) -> WorkspaceRead:
    workspace = create_workspace_with_business_profile(session, payload)
    publish_workspace_event(request.app.state.settings, workspace.id, "document.updated", {"workspace_id": workspace.id, "action": "workspace.created"})
    return WorkspaceRead.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(workspace_id: str, session: Session = Depends(get_session)) -> WorkspaceRead:
    workspace = session.get(models.Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return WorkspaceRead.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdate,
    request: Request,
    session: Session = Depends(get_session),
) -> WorkspaceRead:
    workspace = session.get(models.Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(workspace, key, value)
    business = session.get(models.BusinessProfile, workspace_id)
    if business:
        for key, value in updates.items():
            setattr(business, key, value)
    session.commit()
    session.refresh(workspace)
    publish_workspace_event(request.app.state.settings, workspace.id, "document.updated", {"workspace_id": workspace.id, "action": "workspace.updated"})
    return WorkspaceRead.model_validate(workspace)


@router.post("/{workspace_id}/documents", response_model=UploadWithJobResponse)
async def upload_workspace_document(
    workspace_id: str,
    request: Request,
    file: UploadFile = File(...),
    document_type: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> UploadWithJobResponse:
    workspace = session.get(models.Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    contents = await file.read()
    document, job = DocumentIngestionService(session, request.app.state.settings).create_document_with_job(
        workspace=workspace,
        contents=contents,
        filename=file.filename or "upload.bin",
        mime_type=file.content_type,
        document_type=document_type,
    )
    return UploadWithJobResponse(document=DocumentSummary.model_validate(document), job=ProcessingJobRead.model_validate(job))


@router.get("/{workspace_id}/documents", response_model=list[DocumentSummary])
def list_workspace_documents(workspace_id: str, session: Session = Depends(get_session)) -> list[DocumentSummary]:
    documents = session.scalars(
        select(models.Document).where(models.Document.workspace_id == workspace_id).order_by(models.Document.created_at)
    ).all()
    return [DocumentSummary.model_validate(document) for document in documents]


@router.get("/{workspace_id}/jobs", response_model=list[ProcessingJobRead])
def list_workspace_jobs(workspace_id: str, session: Session = Depends(get_session)) -> list[ProcessingJobRead]:
    jobs = session.scalars(
        select(models.ProcessingJob).where(models.ProcessingJob.workspace_id == workspace_id).order_by(models.ProcessingJob.created_at)
    ).all()
    return [ProcessingJobRead.model_validate(job) for job in jobs]


@router.get("/{workspace_id}/score", response_model=Scorecard)
def get_workspace_score(workspace_id: str, request: Request, session: Session = Depends(get_session)) -> Scorecard:
    workspace = session.get(models.Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    scorecard = latest_scorecard(session, workspace_id)
    return scorecard or recalculate_scorecard(session, request.app.state.settings, workspace_id)


@router.get("/{workspace_id}/dashboard")
def get_workspace_dashboard(workspace_id: str, request: Request, session: Session = Depends(get_session)):
    workspace = session.get(models.Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    scorecard = latest_scorecard(session, workspace_id) or recalculate_scorecard(session, request.app.state.settings, workspace_id)
    documents = session.scalars(
        select(models.Document).where(models.Document.workspace_id == workspace_id).order_by(models.Document.created_at)
    ).all()
    evidence_count = session.scalar(select(func.count()).select_from(models.EvidenceItem).where(models.EvidenceItem.workspace_id == workspace_id))
    return {
        "workspace": WorkspaceRead.model_validate(workspace).model_dump(mode="json"),
        "scorecard": scorecard.model_dump(mode="json"),
        "documents": [DocumentSummary.model_validate(document).model_dump(mode="json") for document in documents],
        "evidence_count": evidence_count or 0,
    }
