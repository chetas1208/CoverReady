from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from coverready_api.db import get_session
from coverready_api.schemas.api import ScenarioRequest, ScenarioSimulation
from coverready_api.services.scenario import simulate_scenario


router = APIRouter(prefix="/scenarios")


@router.post("/simulate", response_model=ScenarioSimulation)
def simulate(
    payload: ScenarioRequest, request: Request, session: Session = Depends(get_session)
) -> ScenarioSimulation:
    return simulate_scenario(session, request.app.state.settings, payload)

