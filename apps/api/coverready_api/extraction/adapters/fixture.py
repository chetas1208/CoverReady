from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from coverready_api.config.settings import ROOT_DIR, Settings
from coverready_api.schemas.extraction import ExtractRequest, ExtractResult


class FixtureExtractionAdapter:
    provider_name = "fixture"

    def __init__(
        self,
        settings: Settings,
        *,
        model_id: str = "fixture-extractor",
        payload: dict[str, Any] | None = None,
        fixture_name: str | None = None,
    ) -> None:
        self.settings = settings
        self.model_id = model_id
        self._payload = payload
        self._fixture_name = fixture_name

    def extract(self, request: ExtractRequest) -> ExtractResult:
        payload = self._payload or self._load_fixture(request)
        result_payload = {
            "provider": payload.get("provider", self.provider_name),
            "model_id": payload.get("model_id", self.model_id),
            "prompt_version": payload.get("prompt_version", self.settings.extraction_prompt_version),
            "document_type": payload.get("document_type", request.document_type),
            "confidence": payload.get("confidence", 0.7),
            "pages": payload.get("pages", []),
            "raw_payload": payload.get("raw_payload", payload),
            "fallback_reason": payload.get("fallback_reason"),
        }
        return ExtractResult.model_validate(result_payload)

    def _load_fixture(self, request: ExtractRequest) -> dict[str, Any]:
        fixture_name = self._fixture_name or f"{request.document_type}.json"
        fixture_path = ROOT_DIR / "apps" / "api" / "coverready_api" / "extraction" / "fixtures" / fixture_name
        if not fixture_path.exists():
            fixture_path = ROOT_DIR / "apps" / "api" / "coverready_api" / "extraction" / "fixtures" / "generic_document.json"
        return json.loads(Path(fixture_path).read_text())
