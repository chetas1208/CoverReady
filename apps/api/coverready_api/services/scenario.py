from __future__ import annotations

import hashlib

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.config.settings import Settings
from coverready_api.schemas.api import ScenarioRequest, ScenarioSimulation


def _hash_input(text: str, business_profile_id: str | None) -> str:
    return hashlib.sha256(f"{business_profile_id or 'none'}|{text}".encode()).hexdigest()


def simulate_scenario(session: Session, settings: Settings, request: ScenarioRequest) -> ScenarioSimulation:
    input_hash = _hash_input(request.scenario, request.business_profile_id)
    existing = session.scalar(select(models.ScenarioRun).where(models.ScenarioRun.input_hash == input_hash))
    if existing:
        return ScenarioSimulation.model_validate(existing.response_json)

    latest_scorecard = None
    if request.business_profile_id:
        latest_scorecard = session.scalar(
            select(models.Scorecard)
            .where(models.Scorecard.business_profile_id == request.business_profile_id)
            .order_by(desc(models.Scorecard.created_at))
        )

    scenario_text = request.scenario.lower()
    missing_documents = latest_scorecard.missing_documents if latest_scorecard else []
    direction = "uncertain"
    why = "The scenario may improve underwriting clarity, but the actual effect depends on the quality and recency of the replacement evidence."
    impact = "This change could help if it replaces a missing, expired, or weak document with current proof."

    if "suppression" in scenario_text:
        direction = "up"
        why = "Current scoring is capped by missing restaurant fire-safety proof, and suppression service evidence is one of the clearest missing items."
        impact = "A current suppression-service record would likely improve property-safety readiness and may remove the restaurant fire-safety score cap."
    elif "declaration" in scenario_text or "policy excerpt" in scenario_text:
        direction = "up"
        why = "The current declarations page is expired, so replacing it with a current policy document would improve documentation and renewal clarity."
        impact = "A current declarations page would likely raise documentation completeness and renewal readiness while reducing uncertainty."
    elif "classification" in scenario_text:
        direction = "up"
        why = "Business classification is only partially supported today, so clearer classification evidence should improve coverage alignment."
        impact = "Correct classification evidence would make the score easier to defend and could improve coverage-alignment scoring."
    elif "hood cleaning" in scenario_text:
        direction = "flat"
        why = "The current workspace already has verified hood-cleaning proof, so additional similar evidence would add little unless it is newer or more detailed."
        impact = "This would mostly reinforce existing evidence rather than materially change the score."
    elif "camera" in scenario_text or "security" in scenario_text:
        direction = "uncertain"
        why = "Security documentation can help underwriting context, but it is not one of the deterministic v1 scoring requirements."
        impact = "This may help an underwriter feel more comfortable, but it is unlikely to change the v1 readiness score much on its own."

    result = ScenarioSimulation(
        scenario=request.scenario,
        likely_score_direction=direction,
        estimated_impact_summary=impact,
        why=why,
        still_needed=list(missing_documents)[:4],
    )
    session.add(
        models.ScenarioRun(
            business_profile_id=request.business_profile_id,
            scenario_text=request.scenario,
            input_hash=input_hash,
            response_json=result.model_dump(mode="json"),
        )
    )
    session.commit()
    return result
