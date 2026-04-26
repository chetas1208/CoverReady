#!/usr/bin/env python3
"""Fix evidence field mappings to match the scoring taxonomy, then re-score all workspaces."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from sqlalchemy import select, update, func, distinct
from coverready_api import models
from coverready_api.config.settings import get_settings
from coverready_api.db import build_engine, build_session_maker, init_db
from coverready_api.services.scoring import recalculate_scorecard


# ---- Map raw dataset field names to the taxonomy-expected fields ----
# The scoring engine looks for these exact field strings in evidence items.
FIELD_REMAP = {
    # Documentation completeness
    "license.number":            "license.current",
    "expiration_date":           "license.current",      # license expiry → license.current
    "occupancy_use":             "occupancy.proof",
    "premises_address":          "occupancy.proof",

    # Safety
    "inspection_result":         "safety.fire_inspection.current",
    "inspection_date":           "safety.fire_inspection.current",
    "service_date":              "safety.suppression_service.current",
    "service_type":              "safety.suppression_service.current",
    "next_service_due":          "safety.suppression_service.current",

    # Operations
    "safety_training_date":      "operations.training.current",
    "training_topics":           "operations.training.current",
    "attendee_count":            "operations.training.current",
    "incident_type":             "operations.maintenance.program",
    "mitigation_action":         "operations.maintenance.program",
    "hours_change_question":     "operations.late_night.clarified",
    "requested_documents":       "operations.cooking_controls.current",

    # Coverage alignment
    "general_liability_limit":   "coverage.equipment_values.current",
    "business_personal_property_limit": "coverage.equipment_values.current",
    "business_income_limit":     "coverage.equipment_values.current",
    "additional_insured_required": "coverage.classification.current",

    # Renewal readiness
    "policy_period_end":         "policy.expiration.current",
    "policy_period_start":       "policy.expiration.current",

    # Property
    "address_partial":           "business.address",
    "storefront_signage_present": "business.address",
}


def main():
    settings = get_settings()
    engine = build_engine(settings)
    session_maker = build_session_maker(engine)
    init_db(engine)
    session = session_maker()

    print("=" * 60)
    print("Field Remapping & Re-scoring")
    print("=" * 60)

    # ---- Step 1: Remap evidence fields ----
    total_updated = 0
    for old_field, new_field in FIELD_REMAP.items():
        count = session.scalar(
            select(func.count()).select_from(models.EvidenceItem)
            .where(models.EvidenceItem.field == old_field)
        ) or 0
        if count > 0:
            session.execute(
                update(models.EvidenceItem)
                .where(models.EvidenceItem.field == old_field)
                .values(field=new_field, field_name=new_field)
            )
            total_updated += count
            print(f"  {old_field:45s} → {new_field:40s} ({count} items)")
    session.commit()
    print(f"\nRemapped {total_updated} evidence items across {len(FIELD_REMAP)} field types")

    # Verify fields now
    fields = session.scalars(select(distinct(models.EvidenceItem.field)).order_by(models.EvidenceItem.field)).all()
    print(f"\nPost-remap unique fields ({len(fields)}):")
    for f in fields:
        c = session.scalar(select(func.count()).select_from(models.EvidenceItem).where(models.EvidenceItem.field == f))
        print(f"  {f:45s} ({c:>5} items)")

    # ---- Step 2: Re-score all workspaces ----
    workspace_ids = [
        ws.id for ws in session.scalars(
            select(models.Workspace).order_by(models.Workspace.name)
        ).all()
    ]
    print(f"\nRe-scoring {len(workspace_ids)} workspaces...")
    scores = []
    for ws_id in workspace_ids:
        try:
            sc = recalculate_scorecard(session, settings, ws_id)
            scores.append((ws_id, sc.total_score, sc.uncapped_total_score))
        except Exception as exc:
            print(f"  Error scoring {ws_id}: {exc}")
            scores.append((ws_id, 0, 0))

    scores.sort(key=lambda x: -x[1])
    print(f"\n{'ID':<15} {'Score':>6} {'Uncapped':>8}")
    print("-" * 35)
    for ws_id, score, uncapped in scores[:15]:
        ws = session.get(models.Workspace, ws_id)
        name = ws.name if ws else "?"
        print(f"{ws_id:<15} {score:>6} {uncapped:>8}  {name}")

    best_id = scores[0][0]
    best_score = scores[0][1]
    print(f"\n✅ Best workspace: {best_id} (score={best_score})")
    print(f"   Set this as your active workspace in the UI.")

    session.close()


if __name__ == "__main__":
    main()
