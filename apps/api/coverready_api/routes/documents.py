from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.db import get_session
from coverready_api.schemas.api import (
    DocumentAsset,
    DocumentDetail,
    DocumentStatusResponse,
    DocumentSummary,
    EvidenceItem,
    ProcessingJobRead,
    UploadResponse,
)
from coverready_api.services.document_ingestion import DocumentIngestionService, get_or_create_default_workspace
from coverready_api.services.events import publish_workspace_event
from coverready_api.services.processing_jobs import ProcessingJobService
from coverready_api.services.workspace import require_business_profile


router = APIRouter(prefix="/documents")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    business_profile_id: str | None = Form(default=None),
    document_type: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> UploadResponse:
    contents = await file.read()
    if business_profile_id:
        business = require_business_profile(session, business_profile_id)
        workspace = session.get(models.Workspace, business.id)
        if workspace is None:
            workspace = models.Workspace(
                id=business.id,
                name=business.name,
                address=business.address,
                industry_code=business.industry_code,
                state=business.state,
                origin=business.origin,
            )
            session.add(workspace)
            session.commit()
            session.refresh(workspace)
    else:
        workspace = get_or_create_default_workspace(session)

    document, job = DocumentIngestionService(session, request.app.state.settings).create_document_with_job(
        workspace=workspace,
        contents=contents,
        filename=file.filename or "upload.bin",
        mime_type=file.content_type,
        document_type=document_type,
    )
    return UploadResponse(document=DocumentSummary.model_validate(document), extraction_status=job.status)


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    business_profile_id: str | None = None,
    session: Session = Depends(get_session),
) -> list[DocumentSummary]:
    business = require_business_profile(session, business_profile_id)
    documents = session.scalars(
        select(models.Document).where(models.Document.business_profile_id == business.id).order_by(models.Document.created_at)
    ).all()
    return [DocumentSummary.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, session: Session = Depends(get_session)) -> DocumentDetail:
    document = session.get(models.Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    assets = session.scalars(
        select(models.DocumentAsset).where(models.DocumentAsset.document_id == document_id).order_by(models.DocumentAsset.page_number)
    ).all()
    evidence_items = session.scalars(
        select(models.EvidenceItem).where(models.EvidenceItem.document_id == document_id).order_by(models.EvidenceItem.field)
    ).all()
    return DocumentDetail(
        **DocumentSummary.model_validate(document).model_dump(),
        assets=[DocumentAsset.model_validate(asset) for asset in assets],
        evidence_items=[
            {
                "id": item.id,
                "category": item.category,
                "field": item.field,
                "value": item.value,
                "evidence_strength": item.evidence_strength,
                "confidence": item.confidence,
                "source_snippet": item.source_snippet,
                "document_id": item.document_id,
                "page_ref": item.page_ref,
                "expires_on": item.expires_on,
                "is_conflicting": item.is_conflicting,
            }
            for item in evidence_items
        ],
    )


@router.get("/{document_id}/download")
def download_document(document_id: str, session: Session = Depends(get_session)):
    from fastapi.responses import FileResponse

    document = session.get(models.Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not document.storage_path:
        raise HTTPException(status_code=404, detail="No file stored for this document.")
    file_path = Path(document.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk.")
    return FileResponse(
        path=str(file_path),
        filename=document.source_filename,
        media_type=document.mime_type or "application/octet-stream",
    )

@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(document_id: str, session: Session = Depends(get_session)) -> DocumentStatusResponse:
    document = session.get(models.Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    job = session.get(models.ProcessingJob, document.latest_job_id) if document.latest_job_id else None
    return DocumentStatusResponse(
        document=DocumentSummary.model_validate(document),
        job=ProcessingJobRead.model_validate(job) if job else None,
    )


@router.get("/{document_id}/evidence", response_model=list[EvidenceItem])
def get_document_evidence(document_id: str, session: Session = Depends(get_session)) -> list[EvidenceItem]:
    document = session.get(models.Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    rows = session.scalars(
        select(models.EvidenceItem).where(models.EvidenceItem.document_id == document_id).order_by(models.EvidenceItem.field)
    ).all()
    return [EvidenceItem.model_validate(row) for row in rows]


@router.post("/{document_id}/extract", response_model=DocumentStatusResponse)
def extract_document_route(document_id: str, request: Request, session: Session = Depends(get_session)) -> DocumentStatusResponse:
    document = session.get(models.Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    job = session.get(models.ProcessingJob, document.latest_job_id) if document.latest_job_id else None
    if job is None or job.status in {"ready", "failed"}:
        job = ProcessingJobService(session).create_extraction_job(document)
        session.commit()
        publish_workspace_event(
            request.app.state.settings,
            document.workspace_id,
            "job.created",
            {"job_id": job.id, "document_id": document.id, "status": job.status},
        )
    DocumentIngestionService(session, request.app.state.settings).enqueue_job(job.id)
    session.refresh(document)
    session.refresh(job)
    return DocumentStatusResponse(
        document=DocumentSummary.model_validate(document),
        job=ProcessingJobRead.model_validate(job),
    )


@router.post("/{document_id}/reprocess")
def reprocess_document(document_id: str, request: Request, session: Session = Depends(get_session)):
    document = session.get(models.Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    job = ProcessingJobService(session).create_extraction_job(document)
    document.status = "queued"
    document.processing_status = "queued"
    session.commit()
    publish_workspace_event(
        request.app.state.settings,
        document.workspace_id,
        "job.created",
        {"job_id": job.id, "document_id": document.id, "status": job.status},
    )
    DocumentIngestionService(session, request.app.state.settings).enqueue_job(job.id)
    session.refresh(document)
    session.refresh(job)
    return DocumentStatusResponse(
        document=DocumentSummary.model_validate(document),
        job=ProcessingJobRead.model_validate(job),
    )
