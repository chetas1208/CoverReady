from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from coverready_api import models
from coverready_api.services.events import workspace_event_stream


router = APIRouter(prefix="/workspaces")


@router.get("/{workspace_id}/events")
async def stream_workspace_events(workspace_id: str, request: Request, replay_only: bool = False) -> StreamingResponse:
    with request.app.state.session_maker() as session:
        if session.get(models.Workspace, workspace_id) is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")

    return StreamingResponse(
        workspace_event_stream(request.app.state.settings, workspace_id, replay_only=replay_only),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
