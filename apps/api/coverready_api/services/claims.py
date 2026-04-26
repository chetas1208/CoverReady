from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.schemas.api import EvidenceStrength


CLAIM_FIELDS = {
    "license.current": "Active business license on file",
    "occupancy.proof": "Occupancy proof on file",
    "policy.current": "Current policy documentation on file",
    "business.name": "Named insured evidence on file",
    "business.address": "Business address evidence on file",
    "safety.fire_inspection.current": "Fire inspection evidence on file",
    "safety.hood_cleaning.current": "Hood cleaning evidence on file",
    "safety.extinguisher.current": "Extinguisher service evidence on file",
    "safety.suppression_service.current": "Fire suppression service evidence on file",
}

STRENGTH_PRIORITY = {
    EvidenceStrength.verified.value: 5,
    EvidenceStrength.partially_verified.value: 4,
    EvidenceStrength.weak_evidence.value: 3,
    EvidenceStrength.expired.value: 2,
    EvidenceStrength.conflicting.value: 1,
    EvidenceStrength.missing.value: 0,
}


def _effective_strength(evidence: models.EvidenceItem, as_of_date: date) -> str:
    if evidence.is_conflicting or evidence.evidence_strength == EvidenceStrength.conflicting.value:
        return EvidenceStrength.conflicting.value
    if evidence.expires_on and evidence.expires_on < as_of_date:
        return EvidenceStrength.expired.value
    return evidence.evidence_strength


def refresh_claims(session: Session, business_profile_id: str, as_of_date: date) -> None:
    claim_ids = select(models.Claim.id).where(models.Claim.business_profile_id == business_profile_id)
    session.execute(delete(models.ClaimEvidenceLink).where(models.ClaimEvidenceLink.claim_id.in_(claim_ids)))
    session.execute(delete(models.Claim).where(models.Claim.business_profile_id == business_profile_id))

    evidence_items = session.scalars(
        select(models.EvidenceItem).where(models.EvidenceItem.business_profile_id == business_profile_id)
    ).all()
    grouped: dict[str, list[models.EvidenceItem]] = defaultdict(list)
    for evidence in evidence_items:
        if evidence.field in CLAIM_FIELDS:
            grouped[evidence.field].append(evidence)

    for field, title in CLAIM_FIELDS.items():
        items = grouped.get(field, [])
        if not items:
            continue
        items.sort(
            key=lambda item: (STRENGTH_PRIORITY.get(_effective_strength(item, as_of_date), 0), item.confidence),
            reverse=True,
        )
        best = items[0]
        claim = models.Claim(
            business_profile_id=business_profile_id,
            key=field,
            title=title,
            value=best.value,
            status=_effective_strength(best, as_of_date),
            source_evidence_ids=[item.id for item in items],
        )
        session.add(claim)
        session.flush()
        for evidence in items:
            session.add(
                models.ClaimEvidenceLink(
                    claim_id=claim.id,
                    evidence_id=evidence.id,
                    relationship="supports",
                )
            )
