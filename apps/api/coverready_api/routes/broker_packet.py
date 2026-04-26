from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from coverready_api.db import get_session
from coverready_api.schemas.api import BrokerPacketPreview
from coverready_api.services.broker_packet import build_broker_packet_preview, persist_broker_packet
from coverready_api.services.workspace import require_business_profile


router = APIRouter(prefix="/broker-packet")


@router.get("/preview", response_model=BrokerPacketPreview)
def preview_broker_packet(
    business_profile_id: str | None = None, session: Session = Depends(get_session)
) -> BrokerPacketPreview:
    business = require_business_profile(session, business_profile_id)
    try:
        return build_broker_packet_preview(session, business.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generate", response_model=BrokerPacketPreview)
def generate_broker_packet(
    request: Request,
    business_profile_id: str | None = None,
    session: Session = Depends(get_session),
) -> BrokerPacketPreview:
    business = require_business_profile(session, business_profile_id)
    return persist_broker_packet(session, business.id, request.app.state.settings)
