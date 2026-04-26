from __future__ import annotations

from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.models import utcnow


TERMINAL_JOB_STATUSES = {"ready", "failed"}


class ProcessingJobService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_extraction_job(self, document: models.Document, max_attempts: int = 3) -> models.ProcessingJob:
        job = models.ProcessingJob(
            workspace_id=document.workspace_id,
            document_id=document.id,
            job_type="document_extraction",
            status="queued",
            max_attempts=max_attempts,
        )
        self.session.add(job)
        self.session.flush()
        document.latest_job_id = job.id
        document.processing_status = "queued"
        document.status = "queued"
        document.latest_job_stage = "queued"
        document.latest_job_attempt = job.attempt_count
        document.latest_error = None
        document.updated_at = utcnow()
        self.session.flush()
        return job

    def set_status(self, job: models.ProcessingJob, status: str, error_message: str | None = None) -> None:
        now = utcnow()
        job.status = status
        job.updated_at = now
        job.error_message = error_message
        if status in {"extracting", "normalizing", "scoring"} and job.started_at is None:
            job.started_at = now
        if status in TERMINAL_JOB_STATUSES:
            job.finished_at = now

        document = self.session.get(models.Document, job.document_id)
        if document:
            document.processing_status = status
            document.status = status
            document.latest_job_stage = status
            document.latest_job_attempt = job.attempt_count
            document.latest_error = error_message
            document.updated_at = now
        self.session.flush()
