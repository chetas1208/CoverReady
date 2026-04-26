from __future__ import annotations

import json
from pathlib import Path

from coverready_api.extraction.normalizer import EvidenceNormalizer
from coverready_api.schemas.extraction import ExtractResult


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_parse_business_license_maps_to_normalized_evidence():
    result = ExtractResult.model_validate(_fixture("nemotron_parse_business_license.json"))

    items = EvidenceNormalizer().normalize(result)
    by_field = {item.field_name: item for item in items}

    assert {"business.name", "business.address", "license.current"}.issubset(by_field)
    assert by_field["business.name"].normalized_value == "Sunset Bistro LLC"
    assert by_field["business.address"].page_number == 1
    assert by_field["license.current"].source_bbox_json is not None
    assert by_field["license.current"].extractor_model_id == "nvidia/nemotron-parse"
    assert by_field["license.current"].prompt_version == "extract-v1"


def test_direct_contract_payload_is_validated_without_hallucinated_empty_rows():
    result = ExtractResult.model_validate(
        {
            "provider": "fixture",
            "model_id": "contract-model",
            "prompt_version": "extract-v1",
            "document_type": "generic_document",
            "confidence": 0.88,
            "pages": [],
            "raw_payload": {
                "evidence_items": [
                    {
                        "category": "other",
                        "field_name": "business.name",
                        "normalized_value": "Acme LLC",
                        "raw_value": "Acme LLC",
                        "evidence_strength": "verified",
                        "confidence": 0.88,
                        "source_snippet": "Business Name: Acme LLC",
                        "page_number": 1
                    },
                    {
                        "category": "other",
                        "field_name": "business.address",
                        "normalized_value": None,
                        "raw_value": None,
                        "evidence_strength": "missing",
                        "confidence": 0.0,
                        "source_snippet": None
                    }
                ]
            },
        }
    )

    items = EvidenceNormalizer().normalize(result)

    assert len(items) == 1
    assert items[0].field_name == "business.name"
