from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.config.settings import Settings
from coverready_api.schemas.api import BrokerPacketPreview, DocumentSummary
from coverready_api.services.events import publish_workspace_event


def build_broker_packet_preview(session: Session, business_profile_id: str) -> BrokerPacketPreview:
    business = session.get(models.BusinessProfile, business_profile_id)
    if business is None:
        raise ValueError("Business profile not found.")

    latest_scorecard = session.scalar(
        select(models.Scorecard)
        .where(models.Scorecard.business_profile_id == business_profile_id)
        .order_by(desc(models.Scorecard.created_at))
    )
    documents = session.scalars(
        select(models.Document).where(models.Document.business_profile_id == business_profile_id).order_by(models.Document.created_at)
    ).all()
    top_strengths: list[str] = []
    next_actions: list[str] = []
    score_summary = "No scorecard generated yet."
    missing_documents: list[str] = []

    if latest_scorecard:
        score_summary = (
            f"Insurance-readiness score {latest_scorecard.total_score}/100"
            f" (uncapped {latest_scorecard.uncapped_total_score}/100)."
        )
        top_strengths = [
            reason["plain_reason"]
            for reasons in latest_scorecard.subscores_json.values()
            for reason in reasons["items"]
            if reason["status"] == "verified"
        ][:3]
        next_actions = [item["action"] for item in latest_scorecard.quick_wins or []][:3]
        missing_documents = list(latest_scorecard.missing_documents or [])

    return BrokerPacketPreview(
        business_name=business.name,
        address=business.address,
        score_summary=score_summary,
        top_strengths=top_strengths,
        missing_documents=missing_documents,
        next_best_actions=next_actions,
        documents=[DocumentSummary.model_validate(document) for document in documents],
    )


def persist_broker_packet(session: Session, business_profile_id: str, settings: Settings | None = None) -> BrokerPacketPreview:
    preview = build_broker_packet_preview(session, business_profile_id)
    packet = models.BrokerPacket(
        business_profile_id=business_profile_id,
        packet_json=preview.model_dump(mode="json"),
    )
    session.add(
        packet
    )
    session.commit()
    if settings:
        publish_workspace_event(
            settings,
            business_profile_id,
            "packet.updated",
            {"packet_id": packet.id, "business_profile_id": business_profile_id},
        )
    return preview
