from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.config.settings import Settings, get_settings
from coverready_api.db import build_engine, build_session_maker
from coverready_api.extraction.adapters.base import ExtractionProviderError
from coverready_api.extraction.normalizer import EvidenceNormalizer
from coverready_api.extraction.orchestrator import ExtractionOrchestrator
from coverready_api.jobs.celery_app import celery_app
from coverready_api.schemas.extraction import ExtractRequest
from coverready_api.services.document_ingestion import normalize_document_type
from coverready_api.services.evidence_writer import EvidenceWriter
from coverready_api.services.events import publish_workspace_event
from coverready_api.services.processing_jobs import ProcessingJobService
from coverready_api.services.scoring import recalculate_scorecard


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_document_job(self, job_id: str) -> str:
    settings = get_settings()
    try:
        run_document_processing(job_id, settings, raise_on_failure=True)
        return job_id
    except ExtractionProviderError as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        raise


def run_document_processing(job_id: str, settings: Settings, *, raise_on_failure: bool = False) -> None:
    engine = build_engine(settings)
    SessionLocal = build_session_maker(engine)
    with SessionLocal() as session:
        try:
            _run_with_session(session, settings, job_id)
        except Exception as exc:
            _mark_failed(session, settings, job_id, str(exc))
            logger.exception("Document processing failed.", extra={"job_id": job_id})
            if raise_on_failure:
                raise


def _run_with_session(session: Session, settings: Settings, job_id: str) -> None:
    job = session.get(models.ProcessingJob, job_id)
    if job is None:
        raise ExtractionProviderError(f"Processing job {job_id} not found.")
    document = session.get(models.Document, job.document_id)
    if document is None:
        raise ExtractionProviderError(f"Document {job.document_id} not found.")

    job.attempt_count += 1
    ProcessingJobService(session).set_status(job, "extracting")
    session.commit()
    _publish_job_update(settings, job, document)

    result = ExtractionOrchestrator(settings).extract(
        ExtractRequest(
            document_id=document.id,
            document_type=normalize_document_type(document.document_type),
            source_path=document.storage_path or "",
            mime_type=document.mime_type,
            filename=document.source_filename,
        )
    )
    session.add(
        models.ExtractionRun(
            document_id=document.id,
            job_id=job.id,
            provider=result.provider,
            model_id=result.model_id,
            prompt_version=result.prompt_version,
            confidence=result.confidence,
            fallback_reason=result.fallback_reason,
            status="completed",
            raw_response=result.raw_payload,
        )
    )
    ProcessingJobService(session).set_status(job, "normalizing")
    session.commit()
    _publish_job_update(settings, job, document)

    evidence_items = EvidenceNormalizer().normalize(result)
    evidence_rows = EvidenceWriter(session).replace_machine_evidence(document, result, evidence_items)
    ProcessingJobService(session).set_status(job, "scoring")
    session.commit()
    publish_workspace_event(
        settings,
        document.workspace_id,
        "evidence.created",
        {"document_id": document.id, "evidence_count": len(evidence_rows)},
    )
    _publish_job_update(settings, job, document)

    recalculate_scorecard(session, settings, document.business_profile_id)
    ProcessingJobService(session).set_status(job, "ready")
    session.commit()
    _publish_job_update(settings, job, document)
    logger.info(
        "Document processing completed.",
        extra={
            "job_id": job.id,
            "workspace_id": job.workspace_id,
            "document_id": document.id,
            "provider": result.provider,
            "model_id": result.model_id,
            "status": "ready",
        },
    )


def _publish_job_update(settings: Settings, job: models.ProcessingJob, document: models.Document) -> None:
    publish_workspace_event(
        settings,
        job.workspace_id or document.workspace_id,
        "job.updated",
        {
            "job_id": job.id,
            "document_id": document.id,
            "status": job.status,
            "stage": job.stage,
            "attempt_count": job.attempt_count,
            "error_message": job.error_message,
            "progress_percent": job.progress_percent,
        },
    )
    publish_workspace_event(
        settings,
        job.workspace_id or document.workspace_id,
        "document.updated",
        {
            "document_id": document.id,
            "processing_status": document.processing_status,
            "latest_job_id": document.latest_job_id,
        },
    )


def _mark_failed(session: Session, settings: Settings, job_id: str, message: str) -> None:
    job = session.get(models.ProcessingJob, job_id)
    if job is None:
        return
    document = session.get(models.Document, job.document_id)
    ProcessingJobService(session).set_status(job, "failed", error_message=message[:2000])
    session.add(
        models.ExtractionRun(
            document_id=job.document_id,
            job_id=job.id,
            provider="extraction-orchestrator",
            model_id=None,
            prompt_version=None,
            confidence=0.0,
            fallback_reason=None,
            status="failed",
            raw_response={"error": message},
        )
    )
    session.commit()
    if document:
        _publish_job_update(settings, job, document)
