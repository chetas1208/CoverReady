from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import delete, desc, or_, select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.config.settings import Settings
from coverready_api.schemas.api import (
    DimensionName,
    DimensionScore,
    EvidenceItem,
    EvidenceStrength,
    MissingRequirement,
    QuickWin,
    ScoreCap,
    ScoreProof,
    ScoreReason,
    Scorecard,
    Subscores,
)
from coverready_api.services.claims import refresh_claims
from coverready_api.services.events import publish_workspace_event
from coverready_api.services.explanation import maybe_generate_explanation
from coverready_api.services.taxonomy import CapRule, RequirementRule, RulesetBundle, load_ruleset_bundle


GRADE_MULTIPLIERS = {
    EvidenceStrength.verified.value: 1.0,
    EvidenceStrength.partially_verified.value: 0.6,
    EvidenceStrength.weak_evidence.value: 0.25,
    EvidenceStrength.missing.value: 0.0,
    EvidenceStrength.expired.value: 0.0,
    EvidenceStrength.conflicting.value: 0.0,
}

STATUS_PRIORITY = {
    EvidenceStrength.verified.value: 5,
    EvidenceStrength.partially_verified.value: 4,
    EvidenceStrength.weak_evidence.value: 3,
    EvidenceStrength.expired.value: 2,
    EvidenceStrength.conflicting.value: 1,
    EvidenceStrength.missing.value: 0,
}


@dataclass
class RequirementEvaluation:
    rule: RequirementRule
    status: str
    points_awarded: float
    points_possible: float
    source_evidence_ids: list[str]
    reason: str


def _round_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _normalize_value(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().split())


def _serialize_evidence(row: models.EvidenceItem) -> EvidenceItem:
    return EvidenceItem(
        id=row.id,
        category=row.category,
        field=row.field_name or row.field,
        field_name=row.field_name,
        value=row.normalized_value if row.normalized_value is not None else row.value,
        normalized_value=row.normalized_value,
        raw_value=row.raw_value,
        evidence_strength=row.evidence_strength,
        confidence=row.confidence,
        source_snippet=row.source_snippet,
        source_bbox_json=row.source_bbox_json,
        document_id=row.document_id,
        page_ref=row.page_ref,
        page_number=row.page_number,
        expires_on=row.expires_on,
        is_conflicting=row.is_conflicting,
        extractor_model_id=row.extractor_model_id,
        prompt_version=row.prompt_version,
        status=row.status,
        review_status=row.review_status,
    )


def _effective_strength(item: EvidenceItem, as_of_date: date) -> str:
    if item.is_conflicting or item.evidence_strength == EvidenceStrength.conflicting:
        return EvidenceStrength.conflicting.value
    if item.expires_on and item.expires_on < as_of_date:
        return EvidenceStrength.expired.value
    return item.evidence_strength.value if isinstance(item.evidence_strength, EvidenceStrength) else item.evidence_strength


def _field_conflicts(evidence_by_field: dict[str, list[EvidenceItem]], as_of_date: date) -> dict[str, list[str]]:
    conflicts: dict[str, list[str]] = {}
    for field, items in evidence_by_field.items():
        active_values = {
            _normalize_value(item.value)
            for item in items
            if _effective_strength(item, as_of_date) not in {EvidenceStrength.missing.value, EvidenceStrength.expired.value}
            and item.value
        }
        conflict_ids = [item.id for item in items if item.is_conflicting]
        if len(active_values) > 1 or conflict_ids:
            conflicts[field] = [item.id for item in items]
    return conflicts


def _select_best_item(items: list[EvidenceItem], as_of_date: date) -> EvidenceItem | None:
    if not items:
        return None
    return sorted(
        items,
        key=lambda item: (STATUS_PRIORITY[_effective_strength(item, as_of_date)], item.confidence),
        reverse=True,
    )[0]


def _summarize_requirement(rule: RequirementRule, status: str, source_count: int) -> str:
    if status == EvidenceStrength.verified.value:
        return f"{rule.title} verified from {source_count} source document(s)."
    if status == EvidenceStrength.partially_verified.value:
        return f"{rule.title} is only partially verified."
    if status == EvidenceStrength.weak_evidence.value:
        return f"{rule.title} has only weak supporting evidence."
    if status == EvidenceStrength.expired.value:
        return f"{rule.title} is expired and needs a current replacement."
    if status == EvidenceStrength.conflicting.value:
        return f"{rule.title} has conflicting evidence that needs review."
    return f"{rule.title} is missing."


def _evaluate_requirement(
    rule: RequirementRule,
    evidence_by_field: dict[str, list[EvidenceItem]],
    conflicts: dict[str, list[str]],
    as_of_date: date,
) -> RequirementEvaluation:
    multipliers: list[float] = []
    statuses: list[str] = []
    source_evidence_ids: list[str] = []
    for field in rule.required_fields:
        field_items = evidence_by_field.get(field, [])
        if field in conflicts:
            statuses.append(EvidenceStrength.conflicting.value)
            multipliers.append(0.0)
            source_evidence_ids.extend(conflicts[field])
            continue
        best = _select_best_item(field_items, as_of_date)
        if best is None:
            statuses.append(EvidenceStrength.missing.value)
            multipliers.append(0.0)
            continue
        effective = _effective_strength(best, as_of_date)
        statuses.append(effective)
        multipliers.append(GRADE_MULTIPLIERS[effective])
        source_evidence_ids.append(best.id)

    average_multiplier = sum(multipliers) / len(rule.required_fields)
    if EvidenceStrength.conflicting.value in statuses:
        status = EvidenceStrength.conflicting.value
    elif average_multiplier == 0 and EvidenceStrength.expired.value in statuses:
        status = EvidenceStrength.expired.value
    elif average_multiplier == 0:
        status = EvidenceStrength.missing.value
    elif average_multiplier == 1 and all(item == EvidenceStrength.verified.value for item in statuses):
        status = EvidenceStrength.verified.value
    elif average_multiplier >= 0.6:
        status = EvidenceStrength.partially_verified.value
    else:
        status = EvidenceStrength.weak_evidence.value

    points_awarded = rule.points * average_multiplier
    return RequirementEvaluation(
        rule=rule,
        status=status,
        points_awarded=points_awarded,
        points_possible=rule.points,
        source_evidence_ids=sorted(set(source_evidence_ids)),
        reason=_summarize_requirement(rule, status, len(set(source_evidence_ids))),
    )


def _dimension_reason(items: list[ScoreReason], score: int, max_score: int) -> str:
    verified = [item.plain_reason for item in items if item.status == EvidenceStrength.verified]
    gaps = [item.plain_reason for item in items if item.status in {EvidenceStrength.missing, EvidenceStrength.expired, EvidenceStrength.conflicting}]
    weak = [item.plain_reason for item in items if item.status == EvidenceStrength.weak_evidence]

    fragments = [f"{score}/{max_score}."]
    if verified:
        fragments.append(verified[0])
    if gaps:
        fragments.append(gaps[0])
    elif weak:
        fragments.append(weak[0])
    return " ".join(fragments)


def _score_input_hash(
    business_profile: models.BusinessProfile,
    evidence_items: list[EvidenceItem],
    ruleset: RulesetBundle,
    as_of_date: date,
) -> str:
    payload = {
        "business_profile": {
            "id": business_profile.id,
            "name": business_profile.name,
            "address": business_profile.address,
            "industry_code": business_profile.industry_code,
        },
        "ruleset_id": ruleset.ruleset_id,
        "ruleset_version": ruleset.version,
        "as_of_date": as_of_date.isoformat(),
        "evidence_items": sorted(
            [
                {
                    "id": item.id,
                    "field": item.field,
                    "value": item.value,
                    "strength": _effective_strength(item, as_of_date),
                    "expires_on": item.expires_on.isoformat() if item.expires_on else None,
                }
                for item in evidence_items
            ],
            key=lambda item: item["id"],
        ),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _evaluate_caps(
    cap_rules: list[CapRule],
    requirement_statuses: dict[str, RequirementEvaluation],
    conflicts: dict[str, list[str]],
) -> list[ScoreCap]:
    caps: list[ScoreCap] = []
    for cap_rule in cap_rules:
        trigger = cap_rule.trigger
        if trigger.type in {"missing_requirement", "missing_any_requirement"}:
            matching = [
                requirement_statuses[rule_id]
                for rule_id in trigger.rule_ids
                if rule_id in requirement_statuses and requirement_statuses[rule_id].status != EvidenceStrength.verified.value
            ]
            if matching:
                caps.append(
                    ScoreCap(
                        cap_id=cap_rule.cap_id,
                        title=cap_rule.title,
                        max_total_score=cap_rule.max_total_score,
                        reason=", ".join(item.rule.title for item in matching),
                        triggered_by_rule_ids=[item.rule.rule_id for item in matching],
                        triggered_by_fields=[],
                    )
                )
        elif trigger.type == "conflict_fields":
            triggered_fields = [field for field in trigger.fields if field in conflicts]
            if triggered_fields:
                caps.append(
                    ScoreCap(
                        cap_id=cap_rule.cap_id,
                        title=cap_rule.title,
                        max_total_score=cap_rule.max_total_score,
                        reason="Conflicting values found in identity-related evidence.",
                        triggered_by_rule_ids=[],
                        triggered_by_fields=triggered_fields,
                    )
                )
    return caps


def _quick_wins(missing_items: list[MissingRequirement], caps: list[ScoreCap]) -> list[QuickWin]:
    capped_rule_ids = {rule_id for cap in caps for rule_id in cap.triggered_by_rule_ids}
    quick_wins: list[QuickWin] = []
    severity_rank = {"critical": 0, "important": 1, "moderate": 2}
    sorted_missing = sorted(
        missing_items,
        key=lambda item: (severity_rank.get(item.severity, 3), item.dimension.value, item.label),
    )
    for item in sorted_missing[:4]:
        cap_note = " and may remove a score cap" if item.rule_id in capped_rule_ids else ""
        quick_wins.append(
            QuickWin(
                action=f"Upload {item.label.lower()}",
                expected_score_impact=f"Improves {item.dimension.value.replace('_', ' ')}{cap_note}",
                effort="low" if item.status in {EvidenceStrength.missing, EvidenceStrength.expired} else "medium",
                reason=f"{item.label} is currently {item.status.value.replace('_', ' ')}.",
            )
        )
    return quick_wins


def _manual_review_items(reasons: list[ScoreReason]) -> list[str]:
    items: list[str] = []
    for reason in reasons:
        if reason.status in {EvidenceStrength.expired, EvidenceStrength.conflicting}:
            items.append(reason.plain_reason)
    return items


def calculate_scorecard(
    business_profile: models.BusinessProfile,
    evidence_rows: list[models.EvidenceItem],
    ruleset: RulesetBundle,
    as_of_date: date,
) -> tuple[Scorecard, list[ScoreReason], list[MissingRequirement], dict[str, EvidenceItem]]:
    evidence_items = [_serialize_evidence(row) for row in evidence_rows]
    evidence_by_field: dict[str, list[EvidenceItem]] = defaultdict(list)
    evidence_lookup: dict[str, EvidenceItem] = {}
    for item in evidence_items:
        evidence_by_field[item.field].append(item)
        evidence_lookup[item.id] = item

    conflicts = _field_conflicts(evidence_by_field, as_of_date)
    requirement_evaluations: dict[str, RequirementEvaluation] = {}
    dimension_possible: dict[str, float] = defaultdict(float)
    dimension_awarded: dict[str, float] = defaultdict(float)
    reason_items: list[ScoreReason] = []
    missing_items: list[MissingRequirement] = []

    for rule in ruleset.requirements:
        evaluation = _evaluate_requirement(rule, evidence_by_field, conflicts, as_of_date)
        requirement_evaluations[rule.rule_id] = evaluation
        dimension_possible[rule.dimension] += evaluation.points_possible
        dimension_awarded[rule.dimension] += evaluation.points_awarded

        reason = ScoreReason(
            rule_id=rule.rule_id,
            dimension=rule.dimension,
            points_awarded=round(evaluation.points_awarded, 2),
            points_possible=evaluation.points_possible,
            status=evaluation.status,
            plain_reason=evaluation.reason,
            source_evidence_ids=evaluation.source_evidence_ids,
        )
        reason_items.append(reason)

        if rule.document_requirement and evaluation.status != EvidenceStrength.verified.value:
            severity = "critical" if rule.rule_id.startswith("doc.") or rule.rule_id.startswith("safety.") else "important"
            missing_items.append(
                MissingRequirement(
                    rule_id=rule.rule_id,
                    label=rule.missing_document_label,
                    dimension=rule.dimension,
                    severity=severity,
                    status=evaluation.status,
                    cap_id=None,
                    source_evidence_ids=evaluation.source_evidence_ids,
                )
            )

    dimension_scores: dict[str, DimensionScore] = {}
    for dimension, max_score in ruleset.dimensions.items():
        items = [reason for reason in reason_items if reason.dimension == dimension]
        awarded = dimension_awarded.get(dimension, 0.0)
        possible = dimension_possible.get(dimension, 0.0)
        score = _round_half_up((awarded / possible) * max_score) if possible else 0
        dimension_scores[dimension] = DimensionScore(
            score=score,
            max_score=max_score,
            reason=_dimension_reason(items, score, max_score),
            items=items,
        )

    caps = _evaluate_caps(ruleset.caps, requirement_evaluations, conflicts)
    missing_by_rule = {item.rule_id: item for item in missing_items}
    for cap in caps:
        for rule_id in cap.triggered_by_rule_ids:
            if rule_id in missing_by_rule:
                missing_by_rule[rule_id].cap_id = cap.cap_id

    uncapped_total_score = sum(item.score for item in dimension_scores.values())
    total_score = min([uncapped_total_score, *[cap.max_total_score for cap in caps]]) if caps else uncapped_total_score
    top_risk_drivers = [cap.title for cap in caps] + [item.label for item in missing_items if item.cap_id is None][:3]
    quick_wins = _quick_wins(missing_items, caps)
    manual_review_needed = _manual_review_items(reason_items)

    scorecard = Scorecard(
        total_score=total_score,
        uncapped_total_score=uncapped_total_score,
        score_caps=caps,
        subscores=Subscores(**dimension_scores),
        top_risk_drivers=top_risk_drivers[:5],
        quick_wins=quick_wins,
        missing_documents=[item.label for item in missing_items],
        manual_review_needed=manual_review_needed,
        ruleset_id=ruleset.ruleset_id,
        ruleset_version=ruleset.version,
        input_hash=_score_input_hash(business_profile, evidence_items, ruleset, as_of_date),
        explanation_source="pending",
    )
    return scorecard, reason_items, missing_items, evidence_lookup


def recalculate_scorecard(session: Session, settings: Settings, business_profile_id: str) -> Scorecard:
    business_profile = session.get(models.BusinessProfile, business_profile_id)
    if business_profile is None:
        raise ValueError("Business profile not found.")
    as_of_date = date.fromisoformat(settings.as_of_date)
    evidence_rows = session.scalars(
        select(models.EvidenceItem).where(
            models.EvidenceItem.business_profile_id == business_profile_id,
            or_(models.EvidenceItem.status.is_(None), models.EvidenceItem.status != "rejected"),
            or_(models.EvidenceItem.review_status.is_(None), models.EvidenceItem.review_status != "rejected"),
        )
    ).all()
    ruleset = load_ruleset_bundle(settings, business_profile.industry_code)
    scorecard, reasons, missing_items, _ = calculate_scorecard(business_profile, evidence_rows, ruleset, as_of_date)
    explanation_payload, explanation_source = maybe_generate_explanation(settings, scorecard)
    scorecard.explanation_source = explanation_source

    refresh_claims(session, business_profile_id, as_of_date)

    existing_scorecard_ids = select(models.Scorecard.id).where(models.Scorecard.business_profile_id == business_profile_id)
    session.execute(delete(models.ScoreReasonItem).where(models.ScoreReasonItem.scorecard_id.in_(existing_scorecard_ids)))
    session.execute(delete(models.MissingRequirement).where(models.MissingRequirement.scorecard_id.in_(existing_scorecard_ids)))

    scorecard_row = models.Scorecard(
        business_profile_id=business_profile_id,
        total_score=scorecard.total_score,
        uncapped_total_score=scorecard.uncapped_total_score,
        ruleset_id=scorecard.ruleset_id,
        ruleset_version=scorecard.ruleset_version,
        input_hash=scorecard.input_hash,
        subscores_json=scorecard.subscores.model_dump(mode="json"),
        caps_json=[cap.model_dump(mode="json") for cap in scorecard.score_caps],
        top_risk_drivers=scorecard.top_risk_drivers,
        quick_wins=[item.model_dump(mode="json") for item in scorecard.quick_wins],
        missing_documents=scorecard.missing_documents,
        manual_review_needed=scorecard.manual_review_needed,
        explanation_json=explanation_payload,
        explanation_source=explanation_source,
        explanation_model=settings.explanation_model if settings.ollama_url else "deterministic-fallback",
        prompt_version=settings.explanation_prompt_version,
    )
    session.add(scorecard_row)
    session.flush()

    for reason in reasons:
        session.add(
            models.ScoreReasonItem(
                scorecard_id=scorecard_row.id,
                rule_id=reason.rule_id,
                dimension=reason.dimension.value,
                points_awarded=reason.points_awarded,
                points_possible=reason.points_possible,
                status=reason.status.value,
                plain_reason=reason.plain_reason,
                source_evidence_ids=reason.source_evidence_ids,
            )
        )
    for missing in missing_items:
        session.add(
            models.MissingRequirement(
                scorecard_id=scorecard_row.id,
                rule_id=missing.rule_id,
                label=missing.label,
                dimension=missing.dimension.value,
                severity=missing.severity,
                status=missing.status.value,
                cap_id=missing.cap_id,
                source_evidence_ids=missing.source_evidence_ids,
            )
        )

    session.commit()
    session.refresh(scorecard_row)
    publish_workspace_event(
        settings,
        business_profile_id,
        "score.updated",
        {
            "scorecard_id": scorecard_row.id,
            "total_score": scorecard_row.total_score,
            "uncapped_total_score": scorecard_row.uncapped_total_score,
        },
    )
    return hydrate_scorecard(session, scorecard_row)


def hydrate_scorecard(session: Session, scorecard_row: models.Scorecard) -> Scorecard:
    reasons = session.scalars(
        select(models.ScoreReasonItem).where(models.ScoreReasonItem.scorecard_id == scorecard_row.id)
    ).all()
    return Scorecard(
        id=scorecard_row.id,
        business_profile_id=scorecard_row.business_profile_id,
        total_score=scorecard_row.total_score,
        uncapped_total_score=scorecard_row.uncapped_total_score,
        score_caps=[ScoreCap.model_validate(cap) for cap in (scorecard_row.caps_json or [])],
        subscores=Subscores.model_validate(scorecard_row.subscores_json),
        top_risk_drivers=list(scorecard_row.top_risk_drivers or []),
        quick_wins=[QuickWin.model_validate(item) for item in (scorecard_row.quick_wins or [])],
        missing_documents=list(scorecard_row.missing_documents or []),
        manual_review_needed=list(scorecard_row.manual_review_needed or []),
        ruleset_id=scorecard_row.ruleset_id,
        ruleset_version=scorecard_row.ruleset_version,
        input_hash=scorecard_row.input_hash,
        explanation_source=scorecard_row.explanation_source or "unknown",
    )


def latest_scorecard(session: Session, business_profile_id: str) -> Scorecard | None:
    scorecard_row = session.scalar(
        select(models.Scorecard)
        .where(models.Scorecard.business_profile_id == business_profile_id)
        .order_by(desc(models.Scorecard.created_at))
    )
    if scorecard_row is None:
        return None
    return hydrate_scorecard(session, scorecard_row)


def scorecard_proof(session: Session, scorecard_id: str) -> ScoreProof:
    scorecard_row = session.get(models.Scorecard, scorecard_id)
    if scorecard_row is None:
        raise ValueError("Scorecard not found.")
    reason_rows = session.scalars(
        select(models.ScoreReasonItem).where(models.ScoreReasonItem.scorecard_id == scorecard_id)
    ).all()
    evidence_ids = sorted({evidence_id for row in reason_rows for evidence_id in (row.source_evidence_ids or [])})
    evidence_rows = session.scalars(select(models.EvidenceItem).where(models.EvidenceItem.id.in_(evidence_ids))).all() if evidence_ids else []
    return ScoreProof(
        scorecard_id=scorecard_id,
        reasons=[
            ScoreReason(
                rule_id=row.rule_id,
                dimension=row.dimension,
                points_awarded=row.points_awarded,
                points_possible=row.points_possible,
                status=row.status,
                plain_reason=row.plain_reason,
                source_evidence_ids=list(row.source_evidence_ids or []),
            )
            for row in reason_rows
        ],
        evidence_lookup={row.id: _serialize_evidence(row) for row in evidence_rows},
    )
