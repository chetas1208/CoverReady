from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.config.settings import Settings
from coverready_api.schemas.api import TranslatorRequest, TranslatorResult


def _hash_input(text: str, prompt_version: str, model_id: str) -> str:
    return hashlib.sha256(f"{prompt_version}|{model_id}|{text}".encode()).hexdigest()


def translate_clause(session: Session, settings: Settings, request: TranslatorRequest) -> TranslatorResult:
    model_id = settings.explanation_model if settings.ollama_url else "deterministic-fallback"
    input_hash = _hash_input(request.clause_text, settings.translator_prompt_version, model_id)

    existing = session.scalar(
        select(models.TranslatorRun).where(
            models.TranslatorRun.input_hash == input_hash,
            models.TranslatorRun.prompt_version == settings.translator_prompt_version,
            models.TranslatorRun.model_id == model_id,
        )
    )
    if existing:
        return TranslatorResult.model_validate(existing.response_json)

    summary = request.clause_text.strip().replace("\n", " ")
    summary = summary[:220] + ("..." if len(summary) > 220 else "")
    result = TranslatorResult(
        plain_english_summary=(
            "This clause likely sets a condition, limitation, or trigger in the policy. "
            f"Current wording: {summary}"
        ),
        why_it_matters=(
            "It can affect whether a loss is covered, when extra documentation is required, "
            "or whether the insurer expects a specific control to be in place."
        ),
        questions_to_verify=[
            "What event or condition activates this clause?",
            "Does the wording match how the business actually operates today?",
            "Is there any deadline, endorsement, or exception attached to it?",
        ],
        suggested_next_steps=[
            "Compare the clause to the current declarations page or endorsement schedule.",
            "Ask the broker which documents or controls they would want to confirm this wording.",
            "Flag any mismatch between the clause and current operations before renewal.",
        ],
    )

    session.add(
        models.TranslatorRun(
            business_profile_id=request.business_profile_id,
            clause_text=request.clause_text,
            input_hash=input_hash,
            response_json=result.model_dump(mode="json"),
            model_id=model_id,
            prompt_version=settings.translator_prompt_version,
        )
    )
    session.commit()
    return result

