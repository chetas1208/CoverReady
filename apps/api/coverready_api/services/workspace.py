from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from coverready_api import models


def get_primary_business_profile(session: Session) -> models.BusinessProfile | None:
    return session.scalar(select(models.BusinessProfile).order_by(models.BusinessProfile.created_at))


def require_business_profile(session: Session, business_profile_id: str | None = None) -> models.BusinessProfile:
    business = session.get(models.BusinessProfile, business_profile_id) if business_profile_id else get_primary_business_profile(session)
    if business is None:
        business = models.BusinessProfile(
            name="Local Business Workspace",
            address=None,
            industry_code="general",
            origin="live",
        )
        session.add(business)
        session.commit()
        session.refresh(business)
    return business

