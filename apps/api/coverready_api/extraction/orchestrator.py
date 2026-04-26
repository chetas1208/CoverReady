from __future__ import annotations

from dataclasses import dataclass

from coverready_api.config.settings import Settings
from coverready_api.extraction.adapters.base import ExtractionAdapter, ExtractionProviderError
from coverready_api.extraction.adapters.fixture import FixtureExtractionAdapter
from coverready_api.extraction.adapters.nemotron_ocr import NemotronOCRAdapter
from coverready_api.extraction.adapters.nemotron_parse import NemotronParseAdapter
from coverready_api.schemas.extraction import ExtractRequest, ExtractResult


@dataclass(frozen=True)
class FallbackDecision:
    should_fallback: bool
    reason: str | None = None


class ExtractionOrchestrator:
    def __init__(
        self,
        settings: Settings,
        *,
        parse_adapter: ExtractionAdapter | None = None,
        ocr_adapter: ExtractionAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.parse_adapter = parse_adapter or self._default_parse_adapter(settings)
        self.ocr_adapter = ocr_adapter or self._default_ocr_adapter(settings)

    def extract(self, request: ExtractRequest) -> ExtractResult:
        parse_error: ExtractionProviderError | None = None
        try:
            parse_result = self.parse_adapter.extract(request)
            decision = self.fallback_decision(parse_result)
            if not decision.should_fallback:
                return parse_result
            fallback_reason = decision.reason
        except ExtractionProviderError as exc:
            parse_result = None
            parse_error = exc
            fallback_reason = str(exc)

        try:
            ocr_result = self.ocr_adapter.extract(request)
            return ocr_result.model_copy(update={"fallback_reason": fallback_reason or "parse_result_not_usable"})
        except ExtractionProviderError as exc:
            if parse_error:
                raise ExtractionProviderError(f"Parse failed ({parse_error}); OCR failed ({exc})") from exc
            raise ExtractionProviderError(f"OCR fallback failed after weak parse result: {exc}") from exc

    def fallback_decision(self, result: ExtractResult) -> FallbackDecision:
        text_length = sum(len(page.text or "") for page in result.pages)
        region_count = sum(len(page.regions) for page in result.pages)
        if result.confidence < self.settings.extraction_min_confidence:
            return FallbackDecision(True, f"parse_confidence_below_{self.settings.extraction_min_confidence}")
        if text_length < self.settings.extraction_min_text_length:
            return FallbackDecision(True, f"parse_text_below_{self.settings.extraction_min_text_length}_chars")
        if region_count == 0 and not any(page.text for page in result.pages):
            return FallbackDecision(True, "parse_returned_no_regions_or_text")
        return FallbackDecision(False)

    @staticmethod
    def _default_parse_adapter(settings: Settings) -> ExtractionAdapter:
        if settings.extractor_mode == "fixture" or (settings.extractor_mode == "auto" and not settings.nim_base_url):
            return FixtureExtractionAdapter(settings, model_id="fixture-nemotron-parse")
        return NemotronParseAdapter(settings)

    @staticmethod
    def _default_ocr_adapter(settings: Settings) -> ExtractionAdapter:
        if settings.extractor_mode == "fixture" or (settings.extractor_mode == "auto" and not settings.nim_base_url):
            return FixtureExtractionAdapter(settings, model_id="fixture-nemotron-ocr", fixture_name="generic_document.json")
        return NemotronOCRAdapter(settings)
