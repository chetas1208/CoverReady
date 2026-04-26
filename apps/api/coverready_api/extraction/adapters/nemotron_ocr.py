from __future__ import annotations

import json
from typing import Any

import httpx

from coverready_api.config.settings import Settings
from coverready_api.extraction.adapters.base import ExtractionProviderError
from coverready_api.extraction.prompts import load_extraction_prompt
from coverready_api.extraction.renderer import render_document_pages
from coverready_api.schemas.extraction import ExtractPage, ExtractRegion, ExtractRequest, ExtractResult


class NemotronOCRAdapter:
    provider_name = "nemotron-ocr-v1"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model_id = settings.ocr_model

    def extract(self, request: ExtractRequest) -> ExtractResult:
        if not self.settings.nim_base_url:
            raise ExtractionProviderError("COVERREADY_NIM_BASE_URL is not configured.")

        rendered_pages = render_document_pages(request.source_path, request.mime_type, self.settings)
        pages: list[ExtractPage] = []
        raw_pages: list[dict[str, Any]] = []

        for rendered_page in rendered_pages:
            if not rendered_page.data_url:
                pages.append(
                    ExtractPage(
                        page_number=rendered_page.page_number,
                        text=rendered_page.text_content,
                        regions=[],
                        image_path=rendered_page.image_path,
                        width=rendered_page.width,
                        height=rendered_page.height,
                    )
                )
                raw_pages.append({"page_number": rendered_page.page_number, "text": rendered_page.text_content})
                continue

            response_payload = self._call_page(data_url=rendered_page.data_url, document_type=request.document_type)
            text = _text_from_response(response_payload)
            raw_pages.append({"page_number": rendered_page.page_number, "response": response_payload})
            pages.append(
                ExtractPage(
                    page_number=rendered_page.page_number,
                    text=text or rendered_page.text_content,
                    regions=[ExtractRegion(text=text, region_type="OCR", confidence=0.65)] if text else [],
                    image_path=rendered_page.image_path,
                    width=rendered_page.width,
                    height=rendered_page.height,
                )
            )

        confidence = 0.65 if any(page.text for page in pages) else 0.0
        return ExtractResult(
            provider=self.provider_name,
            model_id=self.model_id,
            prompt_version=self.settings.extraction_prompt_version,
            document_type=request.document_type,
            confidence=confidence,
            pages=pages,
            raw_payload={"pages": raw_pages},
        )

    def _call_page(self, data_url: str, document_type: str) -> dict[str, Any]:
        endpoint = _chat_completions_endpoint(self.settings.nim_base_url)
        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "system",
                    "content": load_extraction_prompt(document_type),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Document type hint: {document_type}."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {self.settings.nim_api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.post(endpoint, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ExtractionProviderError(f"Nemotron OCR request failed: {exc}") from exc


def _text_from_response(payload: dict[str, Any]) -> str | None:
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        stripped = content.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed.get("text") or parsed.get("markdown") or stripped
        except json.JSONDecodeError:
            pass
        return stripped
    return None


def _chat_completions_endpoint(base_url: str) -> str:
    stripped = base_url.rstrip("/")
    if stripped.endswith("/chat/completions"):
        return stripped
    if stripped.endswith("/v1"):
        return f"{stripped}/chat/completions"
    return f"{stripped}/v1/chat/completions"
