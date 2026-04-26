from __future__ import annotations

from typing import Protocol

from coverready_api.schemas.extraction import ExtractRequest, ExtractResult


class ExtractionProviderError(RuntimeError):
    """Raised when a provider cannot complete extraction."""


class ExtractionAdapter(Protocol):
    provider_name: str
    model_id: str

    def extract(self, request: ExtractRequest) -> ExtractResult:
        ...
