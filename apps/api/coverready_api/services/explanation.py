from __future__ import annotations

from collections.abc import Iterable

import httpx

from coverready_api.config.settings import Settings
from coverready_api.schemas.api import DimensionName, Scorecard


def _fallback_summary(scorecard: Scorecard) -> dict:
    biggest_gap = next(iter(scorecard.missing_documents), None)
    cap_note = scorecard.score_caps[0].title if scorecard.score_caps else "No active score caps."
    return {
        "executive_summary": (
            f"CoverReady scored {scorecard.total_score}/100. "
            f"{cap_note} Primary missing item: {biggest_gap or 'none listed'}."
        ),
        "dimension_notes": {
            dimension.value: getattr(scorecard.subscores, dimension.value).reason for dimension in DimensionName
        },
    }


def maybe_generate_explanation(settings: Settings, scorecard: Scorecard) -> tuple[dict, str]:
    if not settings.ollama_url:
        return _fallback_summary(scorecard), "deterministic-fallback"

    prompt = (
        "Rewrite this insurance-readiness scorecard in plain English JSON with keys "
        "`executive_summary` and `dimension_notes`.\n"
        f"{scorecard.model_dump_json(indent=2)}"
    )
    try:
        response = httpx.post(
            f"{settings.ollama_url.rstrip('/')}/api/generate",
            json={
                "model": settings.explanation_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=20.0,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "")
        if isinstance(text, str) and text.strip():
            return {"executive_summary": text.strip(), "dimension_notes": {}}, "ollama"
    except Exception:
        pass

    return _fallback_summary(scorecard), "deterministic-fallback"


def summarize_verified_reasons(reasons: Iterable[str]) -> str:
    reason_list = [reason for reason in reasons if reason]
    if not reason_list:
        return "No verified evidence yet."
    if len(reason_list) == 1:
        return reason_list[0]
    return f"{reason_list[0]} {reason_list[1]}"

