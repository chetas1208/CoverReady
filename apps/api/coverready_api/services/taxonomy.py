from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from coverready_api.config.settings import Settings


class RequirementRule(BaseModel):
    rule_id: str
    dimension: str
    title: str
    points: float
    required_fields: list[str]
    accepted_document_types: list[str] = []
    missing_document_label: str
    document_requirement: bool = False


class CapTrigger(BaseModel):
    type: str
    rule_ids: list[str] = []
    fields: list[str] = []


class CapRule(BaseModel):
    cap_id: str
    title: str
    max_total_score: int
    trigger: CapTrigger


class RulesetBundle(BaseModel):
    ruleset_id: str
    version: str
    source_rulesets: list[str]
    dimensions: dict[str, int]
    requirements: list[RequirementRule]
    caps: list[CapRule]


def _load_ruleset(path: Path) -> dict:
    return json.loads(path.read_text())


@lru_cache(maxsize=8)
def _cached_bundle(taxonomy_dir: str, industry_code: str) -> RulesetBundle:
    base = _load_ruleset(Path(taxonomy_dir) / "base_small_business.v1.json")
    requirements = list(base["requirements"])
    caps = list(base["caps"])
    source_rulesets = [base["ruleset_id"]]

    if industry_code == "restaurant":
        overlay = _load_ruleset(Path(taxonomy_dir) / "restaurant_overlay.v1.json")
        requirements.extend(overlay["requirements"])
        caps.extend(overlay["caps"])
        source_rulesets.append(overlay["ruleset_id"])

    return RulesetBundle(
        ruleset_id="+".join(source_rulesets),
        version="1.0.0",
        source_rulesets=source_rulesets,
        dimensions=base["dimensions"],
        requirements=[RequirementRule.model_validate(item) for item in requirements],
        caps=[CapRule.model_validate(item) for item in caps],
    )


def load_ruleset_bundle(settings: Settings, industry_code: str) -> RulesetBundle:
    return _cached_bundle(str(settings.taxonomy_dir), industry_code)
