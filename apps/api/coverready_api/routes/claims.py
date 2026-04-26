from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.db import get_session
from coverready_api.schemas.api import ClaimRecord
from coverready_api.services.workspace import require_business_profile


router = APIRouter()


@router.get("/claims", response_model=list[ClaimRecord])
def list_claims(business_profile_id: str | None = None, session: Session = Depends(get_session)) -> list[ClaimRecord]:
    business = require_business_profile(session, business_profile_id)
    claims = session.scalars(
        select(models.Claim).where(models.Claim.business_profile_id == business.id).order_by(models.Claim.title)
    ).all()
    return [ClaimRecord.model_validate(claim) for claim in claims]

