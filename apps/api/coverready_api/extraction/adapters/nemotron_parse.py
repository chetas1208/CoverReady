from __future__ import annotations

import json
from typing import Any

import httpx

from coverready_api.config.settings import Settings
from coverready_api.extraction.adapters.base import ExtractionProviderError
from coverready_api.extraction.renderer import render_document_pages
from coverready_api.schemas.extraction import ExtractPage, ExtractRegion, ExtractRequest, ExtractResult, ExtractionBBox


class NemotronParseAdapter:
    provider_name = "nemotron-parse"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model_id = settings.parse_model

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

            response_payload = self._call_page(rendered_page.data_url)
            regions = _regions_from_response(response_payload)
            page_text = "\n".join(region.text or "" for region in regions).strip() or rendered_page.text_content
            raw_pages.append({"page_number": rendered_page.page_number, "response": response_payload})
            pages.append(
                ExtractPage(
                    page_number=rendered_page.page_number,
                    text=page_text,
                    regions=regions,
                    image_path=rendered_page.image_path,
                    width=rendered_page.width,
                    height=rendered_page.height,
                )
            )

        confidence = _estimate_confidence(pages)
        return ExtractResult(
            provider=self.provider_name,
            model_id=self.model_id,
            prompt_version=self.settings.extraction_prompt_version,
            document_type=request.document_type,
            confidence=confidence,
            pages=pages,
            raw_payload={"pages": raw_pages},
        )

    def _call_page(self, data_url: str) -> dict[str, Any]:
        endpoint = _chat_completions_endpoint(self.settings.nim_base_url)
        payload = {
            "model": self.model_id,
            "tools": [{"type": "function", "function": {"name": "markdown_bbox"}}],
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": data_url}}],
                }
            ],
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {self.settings.nim_api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.post(endpoint, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ExtractionProviderError(f"Nemotron Parse request failed: {exc}") from exc


def _regions_from_response(payload: dict[str, Any]) -> list[ExtractRegion]:
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        arguments = tool_calls[0].get("function", {}).get("arguments", "[]")
        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
        except json.JSONDecodeError:
            parsed = []
        return _regions_from_parsed(parsed)

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return [ExtractRegion(text=content.strip(), region_type="Text", confidence=0.7)]
    return []


def _regions_from_parsed(parsed: Any) -> list[ExtractRegion]:
    if isinstance(parsed, dict):
        if "pages" in parsed:
            parsed = parsed["pages"]
        elif "text" in parsed or "bbox" in parsed:
            parsed = [parsed]
        else:
            parsed = parsed.get("regions", [])

    regions: list[ExtractRegion] = []
    if not isinstance(parsed, list):
        return regions

    for item in parsed:
        if not isinstance(item, dict):
            continue
        bbox_payload = item.get("bbox")
        bbox = ExtractionBBox.model_validate(bbox_payload) if isinstance(bbox_payload, dict) else None
        text = item.get("text") or item.get("markdown")
        regions.append(
            ExtractRegion(
                text=text,
                bbox=bbox,
                region_type=item.get("type") or item.get("region_type"),
                confidence=item.get("confidence"),
            )
        )
    return regions


def _estimate_confidence(pages: list[ExtractPage]) -> float:
    region_confidences = [region.confidence for page in pages for region in page.regions if region.confidence is not None]
    if region_confidences:
        return max(0.0, min(1.0, sum(region_confidences) / len(region_confidences)))
    text_length = sum(len(page.text or "") for page in pages)
    return 0.8 if text_length >= 40 else 0.2 if text_length else 0.0


def _chat_completions_endpoint(base_url: str) -> str:
    stripped = base_url.rstrip("/")
    if stripped.endswith("/chat/completions"):
        return stripped
    if stripped.endswith("/v1"):
        return f"{stripped}/chat/completions"
    return f"{stripped}/v1/chat/completions"
