from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.db import get_session
from coverready_api.schemas.api import ScoreProof, Scorecard
from coverready_api.services.scoring import hydrate_scorecard, latest_scorecard, recalculate_scorecard, scorecard_proof
from coverready_api.services.workspace import require_business_profile


router = APIRouter(prefix="/scorecards")


@router.post("/recalculate", response_model=Scorecard)
def recalculate(
    request: Request,
    business_profile_id: str | None = None,
    session: Session = Depends(get_session),
) -> Scorecard:
    business = require_business_profile(session, business_profile_id)
    return recalculate_scorecard(session, request.app.state.settings, business.id)


@router.get("/latest", response_model=Scorecard | None)
def get_latest_scorecard(
    business_profile_id: str | None = None, session: Session = Depends(get_session)
) -> Scorecard | None:
    business = require_business_profile(session, business_profile_id)
    return latest_scorecard(session, business.id)


@router.get("/{scorecard_id}", response_model=Scorecard)
def get_scorecard(scorecard_id: str, session: Session = Depends(get_session)) -> Scorecard:
    scorecard_row = session.get(models.Scorecard, scorecard_id)
    if scorecard_row is None:
        raise HTTPException(status_code=404, detail="Scorecard not found.")
    return hydrate_scorecard(session, scorecard_row)


@router.get("/{scorecard_id}/proof", response_model=ScoreProof)
def get_scorecard_proof(scorecard_id: str, session: Session = Depends(get_session)) -> ScoreProof:
    try:
        return scorecard_proof(session, scorecard_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

