from __future__ import annotations

from datetime import date

from sqlalchemy import select

from coverready_api import models
from coverready_api.db import build_engine, build_session_maker, init_db
from coverready_api.services.scoring import calculate_scorecard, recalculate_scorecard
from coverready_api.services.seed import seed_demo_workspace
from coverready_api.services.taxonomy import load_ruleset_bundle


def test_demo_scorecard_is_deterministic_and_capped(app_settings):
    engine = build_engine(app_settings)
    init_db(engine)
    Session = build_session_maker(engine)
    with Session() as session:
        business = seed_demo_workspace(session, app_settings)
        first = recalculate_scorecard(session, app_settings, business.id)
        second = recalculate_scorecard(session, app_settings, business.id)

        assert first.total_score == 60
        assert first.uncapped_total_score == 68
        assert second.input_hash == first.input_hash
        assert first.subscores.documentation_completeness.score == 18
        assert {cap.cap_id for cap in first.score_caps} == {
            "cap.coverage_docs_missing",
            "cap.restaurant_fire_safety_missing",
        }


def test_missing_document_logic_and_source_links(app_settings):
    engine = build_engine(app_settings)
    init_db(engine)
    Session = build_session_maker(engine)
    with Session() as session:
        business = seed_demo_workspace(session, app_settings)
        scorecard = recalculate_scorecard(session, app_settings, business.id)
        latest_row = session.scalar(select(models.Scorecard).where(models.Scorecard.business_profile_id == business.id))
        missing_rows = session.scalars(
            select(models.MissingRequirement).where(models.MissingRequirement.scorecard_id == latest_row.id)
        ).all()
        reason_rows = session.scalars(
            select(models.ScoreReasonItem).where(models.ScoreReasonItem.scorecard_id == latest_row.id)
        ).all()

        missing_by_rule = {row.rule_id: row for row in missing_rows}
        assert "Current fire suppression service proof" in scorecard.missing_documents
        assert missing_by_rule["doc.coverage.current_policy"].status == "expired"
        assert missing_by_rule["operations.training.current"].status == "weak_evidence"
        assert any(row.rule_id == "doc.business_license.current" and row.source_evidence_ids for row in reason_rows)


def test_conflicting_identity_triggers_cap(app_settings):
    engine = build_engine(app_settings)
    init_db(engine)
    Session = build_session_maker(engine)
    with Session() as session:
        business = seed_demo_workspace(session, app_settings)
        session.add(
            models.EvidenceItem(
                business_profile_id=business.id,
                document_id="doc_lease_001",
                category="other",
                field="business.name",
                value="Sunset Bistro Incorporated",
                evidence_strength="verified",
                confidence=0.94,
                source_snippet="Tenant: Sunset Bistro Incorporated.",
                page_ref="p1",
                is_conflicting=False,
            )
        )
        session.commit()
        evidence_rows = session.scalars(
            select(models.EvidenceItem).where(models.EvidenceItem.business_profile_id == business.id)
        ).all()
        ruleset = load_ruleset_bundle(app_settings, business.industry_code)
        scorecard, reasons, _, _ = calculate_scorecard(
            business,
            evidence_rows,
            ruleset,
            date.fromisoformat(app_settings.as_of_date),
        )

        assert scorecard.total_score == 50
        assert any(cap.cap_id == "cap.identity_conflict" for cap in scorecard.score_caps)
        name_reason = next(reason for reason in reasons if reason.rule_id == "coverage.named_insured.match")
        assert name_reason.status.value == "conflicting"

