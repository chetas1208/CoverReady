from __future__ import annotations

from celery import Celery

from coverready_api.config.settings import get_settings


settings = get_settings()

celery_app = Celery(
    "coverready",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["coverready_api.jobs.document_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)
