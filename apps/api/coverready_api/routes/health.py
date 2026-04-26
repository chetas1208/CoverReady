from __future__ import annotations

from fastapi import APIRouter, Request

from coverready_api.schemas.api import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def healthcheck(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        database_backend=settings.database_url.split(":", 1)[0],
        ollama_configured=bool(settings.ollama_url),
    )
