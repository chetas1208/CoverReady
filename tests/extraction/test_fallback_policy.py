from __future__ import annotations

import json
from pathlib import Path

from coverready_api.extraction.adapters.fixture import FixtureExtractionAdapter
from coverready_api.extraction.orchestrator import ExtractionOrchestrator
from coverready_api.schemas.extraction import ExtractRequest, ExtractResult


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_strong_parse_result_does_not_trigger_ocr(app_settings):
    parse_payload = _fixture("nemotron_parse_business_license.json")
    parse_adapter = FixtureExtractionAdapter(app_settings, model_id="nvidia/nemotron-parse", payload=parse_payload)
    ocr_adapter = FixtureExtractionAdapter(
        app_settings,
        model_id="nvidia/nemotron-ocr-v1",
        payload=_fixture("nemotron_ocr_maintenance_receipt.json"),
    )

    result = ExtractionOrchestrator(app_settings, parse_adapter=parse_adapter, ocr_adapter=ocr_adapter).extract(
        ExtractRequest(
            document_id="doc-test",
            document_type="business_license",
            source_path="/tmp/unused.pdf",
            mime_type="application/pdf",
        )
    )

    assert result.provider == "nemotron-parse"
    assert result.fallback_reason is None


def test_weak_parse_result_triggers_ocr_fallback(app_settings):
    parse_adapter = FixtureExtractionAdapter(
        app_settings,
        model_id="nvidia/nemotron-parse",
        payload=_fixture("nemotron_parse_weak_scan.json"),
    )
    ocr_adapter = FixtureExtractionAdapter(
        app_settings,
        model_id="nvidia/nemotron-ocr-v1",
        payload=_fixture("nemotron_ocr_maintenance_receipt.json"),
    )

    result = ExtractionOrchestrator(app_settings, parse_adapter=parse_adapter, ocr_adapter=ocr_adapter).extract(
        ExtractRequest(
            document_id="doc-test",
            document_type="maintenance_receipt",
            source_path="/tmp/unused.png",
            mime_type="image/png",
        )
    )

    assert result.provider == "nemotron-ocr-v1"
    assert result.fallback_reason == "parse_confidence_below_0.55"
    assert sum(len(page.text or "") for page in result.pages) > 40


def test_fallback_decision_checks_text_length(app_settings):
    result = ExtractResult.model_validate(_fixture("nemotron_parse_weak_scan.json"))
    decision = ExtractionOrchestrator(app_settings).fallback_decision(result)

    assert decision.should_fallback is True
