from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.config.settings import Settings
from coverready_api.services.events import publish_workspace_event
from coverready_api.services.processing_jobs import ProcessingJobService


logger = logging.getLogger(__name__)


DOCUMENT_TYPE_ALIASES = {
    "business_license": "business_license",
    "license": "business_license",
    "safety_certificate": "safety_certificate",
    "fire_safety_record": "safety_certificate",
    "inspection_report": "inspection_report",
    "inspection": "inspection_report",
    "maintenance_receipt": "maintenance_receipt",
    "maintenance": "maintenance_receipt",
    "declarations_page": "declarations_page",
    "declaration": "declarations_page",
    "policy_excerpt": "declarations_page",
    "generic_document": "generic_document",
    "other": "generic_document",
}


class DocumentIngestionService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def create_document_with_job(
        self,
        *,
        workspace: models.Workspace,
        contents: bytes,
        filename: str,
        mime_type: str | None,
        document_type: str | None = None,
        enqueue: bool = True,
    ) -> tuple[models.Document, models.ProcessingJob]:
        business = self._ensure_business_profile(workspace)
        checksum = hashlib.sha256(contents).hexdigest()
        safe_name = f"{uuid4()}-{Path(filename or 'upload.bin').name}"
        workspace_dir = self.settings.storage_dir / workspace.id
        workspace_dir.mkdir(parents=True, exist_ok=True)
        storage_path = workspace_dir / safe_name
        storage_path.write_bytes(contents)

        document = models.Document(
            workspace_id=workspace.id,
            business_profile_id=business.id,
            document_type=normalize_document_type(document_type or guess_document_type(filename)),
            status="uploaded",
            processing_status="uploaded",
            origin=workspace.origin,
            source_filename=filename or safe_name,
            mime_type=mime_type,
            checksum=checksum,
            storage_path=str(storage_path),
            summary="Uploaded locally. Extraction job queued.",
        )
        self.session.add(document)
        self.session.flush()
        job = ProcessingJobService(self.session).create_extraction_job(document)
        self.session.commit()
        self.session.refresh(document)
        self.session.refresh(job)
        publish_workspace_event(
            self.settings,
            workspace.id,
            "job.created",
            {"job_id": job.id, "document_id": document.id, "status": job.status},
        )
        publish_workspace_event(
            self.settings,
            workspace.id,
            "document.updated",
            {"document_id": document.id, "processing_status": document.processing_status},
        )

        if enqueue:
            self.enqueue_job(job.id)
            self.session.refresh(document)
            self.session.refresh(job)
        return document, job

    def enqueue_job(self, job_id: str) -> None:
        if self.settings.jobs_eager:
            from coverready_api.jobs.document_tasks import run_document_processing

            run_document_processing(job_id, self.settings)
            return

        try:
            from coverready_api.jobs.document_tasks import process_document_job

            process_document_job.delay(job_id)
        except Exception as exc:
            logger.warning("Celery enqueue failed; running document processing inline.", extra={"job_id": job_id, "error": str(exc)})
            from coverready_api.jobs.document_tasks import run_document_processing

            run_document_processing(job_id, self.settings)

    def _ensure_business_profile(self, workspace: models.Workspace) -> models.BusinessProfile:
        business = self.session.get(models.BusinessProfile, workspace.id)
        if business:
            return business
        business = models.BusinessProfile(
            id=workspace.id,
            name=workspace.name,
            address=workspace.address,
            industry_code=workspace.industry_code,
            state=workspace.state,
            origin=workspace.origin,
        )
        self.session.add(business)
        self.session.flush()
        return business


def guess_document_type(filename: str) -> str:
    lowered = filename.lower()
    if "license" in lowered:
        return "business_license"
    if "safety" in lowered or "certificate" in lowered or "fire" in lowered or "suppression" in lowered:
        return "safety_certificate"
    if "inspection" in lowered:
        return "inspection_report"
    if "maintenance" in lowered or "receipt" in lowered or "hood" in lowered:
        return "maintenance_receipt"
    if "declaration" in lowered or "policy" in lowered:
        return "declarations_page"
    return "generic_document"


def normalize_document_type(document_type: str) -> str:
    return DOCUMENT_TYPE_ALIASES.get(document_type, "generic_document")


def create_workspace_with_business_profile(session: Session, payload) -> models.Workspace:
    workspace = models.Workspace(
        name=payload.name,
        address=payload.address,
        industry_code=payload.industry_code,
        state=payload.state,
        origin=payload.origin,
    )
    session.add(workspace)
    session.flush()
    session.add(
        models.BusinessProfile(
            id=workspace.id,
            name=workspace.name,
            address=workspace.address,
            industry_code=workspace.industry_code,
            state=workspace.state,
            origin=workspace.origin,
        )
    )
    session.commit()
    session.refresh(workspace)
    return workspace


def get_or_create_default_workspace(session: Session) -> models.Workspace:
    workspace = session.query(models.Workspace).order_by(models.Workspace.created_at).first()
    if workspace:
        return workspace
    business = session.query(models.BusinessProfile).order_by(models.BusinessProfile.created_at).first()
    if business:
        workspace = models.Workspace(
            id=business.id,
            name=business.name,
            address=business.address,
            industry_code=business.industry_code,
            state=business.state,
            origin=business.origin,
        )
    else:
        workspace = models.Workspace(name="Local Business Workspace", industry_code="general", origin="live")
    session.add(workspace)
    session.flush()
    if session.get(models.BusinessProfile, workspace.id) is None:
        session.add(
            models.BusinessProfile(
                id=workspace.id,
                name=workspace.name,
                address=workspace.address,
                industry_code=workspace.industry_code,
                state=workspace.state,
                origin=workspace.origin,
            )
        )
    session.commit()
    session.refresh(workspace)
    return workspace
