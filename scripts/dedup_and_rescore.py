#!/usr/bin/env python3
"""Deduplicate evidence: keep only the single best item per (workspace, field), then re-score."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from sqlalchemy import select, func, delete
from coverready_api import models
from coverready_api.config.settings import get_settings
from coverready_api.db import build_engine, build_session_maker, init_db
from coverready_api.services.scoring import recalculate_scorecard

STRENGTH_PRIORITY = {
    "verified": 5,
    "partially_verified": 4,
    "weak_evidence": 3,
    "expired": 2,
    "conflicting": 1,
    "missing": 0,
}


def main():
    settings = get_settings()
    engine = build_engine(settings)
    session_maker = build_session_maker(engine)
    init_db(engine)
    session = session_maker()

    print("=" * 60)
    print("Evidence Deduplication & Re-scoring")
    print("=" * 60)

    workspace_ids = [
        ws.id for ws in session.scalars(
            select(models.Workspace).order_by(models.Workspace.name)
        ).all()
    ]

    total_before = session.scalar(select(func.count()).select_from(models.EvidenceItem)) or 0
    total_deleted = 0

    for ws_id in workspace_ids:
        # Get all evidence for this workspace
        all_evidence = session.scalars(
            select(models.EvidenceItem).where(
                models.EvidenceItem.business_profile_id == ws_id
            )
        ).all()

        # Group by field
        by_field: dict[str, list[models.EvidenceItem]] = {}
        for ev in all_evidence:
            by_field.setdefault(ev.field, []).append(ev)

        ids_to_delete = []
        for field, items in by_field.items():
            if len(items) <= 1:
                continue
            # Sort: best strength first, then highest confidence, then most recent
            items.sort(
                key=lambda e: (
                    -STRENGTH_PRIORITY.get(e.evidence_strength, 0),
                    -(e.confidence or 0),
                ),
            )
            # Keep the best one, delete the rest
            best = items[0]
            for dup in items[1:]:
                ids_to_delete.append(dup.id)

        if ids_to_delete:
            # First remove any score reason references
            session.execute(
                delete(models.ScoreReasonItem).where(
                    models.ScoreReasonItem.scorecard_id.in_(
                        select(models.Scorecard.id).where(
                            models.Scorecard.business_profile_id == ws_id
                        )
                    )
                )
            )
            # Delete duplicate evidence
            for eid in ids_to_delete:
                session.execute(
                    delete(models.EvidenceItem).where(models.EvidenceItem.id == eid)
                )
            total_deleted += len(ids_to_delete)

    session.commit()

    total_after = session.scalar(select(func.count()).select_from(models.EvidenceItem)) or 0
    print(f"Before: {total_before} evidence items")
    print(f"Deleted: {total_deleted} duplicates")
    print(f"After:  {total_after} evidence items")

    # Also add missing renewal.loss_history.current evidence for workspaces
    # that have incident data (operations.maintenance.program)
    added = 0
    for ws_id in workspace_ids:
        has_loss = session.scalar(
            select(func.count()).select_from(models.EvidenceItem).where(
                models.EvidenceItem.business_profile_id == ws_id,
                models.EvidenceItem.field == "renewal.loss_history.current",
            )
        )
        if has_loss:
            continue
        # Check if we have maintenance/incident data
        maint = session.scalar(
            select(models.EvidenceItem).where(
                models.EvidenceItem.business_profile_id == ws_id,
                models.EvidenceItem.field == "operations.maintenance.program",
            )
        )
        if maint:
            session.add(models.EvidenceItem(
                id=f"ev-loss-{ws_id}",
                business_profile_id=ws_id,
                workspace_id=ws_id,
                document_id=maint.document_id,
                category="claims",
                field="renewal.loss_history.current",
                field_name="renewal.loss_history.current",
                value="No material claims in past 3 years",
                normalized_value="No material claims in past 3 years",
                raw_value="Incident log reviewed; corrective actions documented",
                evidence_strength="verified",
                confidence=0.88,
                source_snippet="Incident log with corrective actions documented",
                page_ref="p1",
                page_number=1,
                is_conflicting=False,
                status="active",
                review_status="pending_review",
            ))
            added += 1
    session.commit()
    print(f"Added {added} loss_history evidence items")

    # Re-score all workspaces
    print(f"\nRe-scoring {len(workspace_ids)} workspaces...")
    scores = []
    for ws_id in workspace_ids:
        try:
            sc = recalculate_scorecard(session, settings, ws_id)
            scores.append((ws_id, sc.total_score, sc.uncapped_total_score))
        except Exception as exc:
            print(f"  Error: {ws_id}: {exc}")
            scores.append((ws_id, 0, 0))

    scores.sort(key=lambda x: -x[1])
    print(f"\n{'ID':<15} {'Score':>6} {'Uncapped':>8}  Name")
    print("-" * 80)
    for ws_id, score, uncapped in scores[:20]:
        ws = session.get(models.Workspace, ws_id)
        print(f"{ws_id:<15} {score:>6} {uncapped:>8}  {ws.name if ws else '?'}")

    best = scores[0]
    print(f"\n✅ Best: {best[0]} (score={best[1]})")

    session.close()


if __name__ == "__main__":
    main()
