from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from coverready_api.schemas.api import EvidenceStrength
from coverready_api.schemas.extraction import ExtractPage, ExtractRegion, ExtractResult, ExtractionBBox, NormalizedEvidenceItem


@dataclass(frozen=True)
class SourceLine:
    page_number: int
    text: str
    bbox: ExtractionBBox | None = None


class EvidenceNormalizer:
    def normalize(self, result: ExtractResult) -> list[NormalizedEvidenceItem]:
        direct_items = self._normalize_direct_contract(result)
        if direct_items:
            return direct_items

        lines = _source_lines(result.pages)
        normalizers = {
            "business_license": self._business_license,
            "safety_certificate": self._safety_certificate,
            "maintenance_receipt": self._maintenance_receipt,
            "declarations_page": self._declarations_page,
            "inspection_report": self._inspection_report,
            "generic_document": self._generic_document,
        }
        items = normalizers.get(result.document_type, self._generic_document)(result, lines)
        return _dedupe(items)

    def _normalize_direct_contract(self, result: ExtractResult) -> list[NormalizedEvidenceItem]:
        raw_items = result.raw_payload.get("evidence_items")
        if not isinstance(raw_items, list):
            return []
        normalized: list[NormalizedEvidenceItem] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            value = item.get("normalized_value", item.get("value"))
            raw_value = item.get("raw_value", value)
            snippet = item.get("source_snippet") or item.get("source_evidence")
            if value is None and raw_value is None and snippet is None:
                continue
            normalized.append(
                NormalizedEvidenceItem.model_validate(
                    {
                        "category": item["category"],
                        "field_name": item.get("field_name") or item.get("field"),
                        "normalized_value": value,
                        "raw_value": raw_value,
                        "evidence_strength": item.get("evidence_strength", _strength(result.confidence)),
                        "confidence": min(float(item.get("confidence", result.confidence)), result.confidence),
                        "source_snippet": snippet,
                        "source_bbox_json": item.get("source_bbox_json") or item.get("bbox"),
                        "page_number": item.get("page_number"),
                        "extractor_model_id": result.model_id,
                        "prompt_version": result.prompt_version,
                        "status": item.get("status", "pending_review"),
                        "expires_on": _parse_date(item.get("expires_on")),
                        "is_conflicting": item.get("is_conflicting", False),
                    }
                )
            )
        return normalized

    def _business_license(self, result: ExtractResult, lines: list[SourceLine]) -> list[NormalizedEvidenceItem]:
        items: list[NormalizedEvidenceItem] = []
        status_line = _first_line(lines, [r"\b(status|license status)\b.*\b(active|current|valid)\b", r"\bactive\b"])
        if status_line:
            items.append(_item(result, "license", "license.current", "active", status_line, confidence_boost=0.05))

        name_line = _first_line(lines, [r"\b(business name|licensee|owner)\b\s*[:\-]\s*(.+)", r"\bname\b\s*[:\-]\s*(.+)"])
        if name_line:
            items.append(_item(result, "other", "business.name", _label_value(name_line.text), name_line))

        address_line = _first_line(lines, [r"\b(address|business location|premises)\b\s*[:\-]\s*(.+)"])
        if address_line:
            items.append(_item(result, "other", "business.address", _label_value(address_line.text), address_line))

        expiration_line = _first_line(lines, [r"\b(expir\w*|valid through|valid until)\b.*?(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})"])
        expiration = _date_from_text(expiration_line.text) if expiration_line else None
        if expiration_line and expiration:
            items.append(
                _item(
                    result,
                    "license",
                    "license.expiration",
                    expiration.isoformat(),
                    expiration_line,
                    expires_on=expiration,
                )
            )
        return items

    def _safety_certificate(self, result: ExtractResult, lines: list[SourceLine]) -> list[NormalizedEvidenceItem]:
        items: list[NormalizedEvidenceItem] = []
        text = "\n".join(line.text for line in lines).lower()
        date_line = _first_line(lines, [r"\b(service|inspection|certification|date)\b.*?(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})"])
        source = date_line or (lines[0] if lines else None)
        if not source:
            return []
        value = _date_from_text(source.text)
        normalized_value = value.isoformat() if value else _label_value(source.text) or "documented"
        if "suppression" in text:
            items.append(_item(result, "safety", "safety.suppression_service.current", normalized_value, source))
        if "extinguisher" in text:
            items.append(_item(result, "safety", "safety.extinguisher.current", normalized_value, source))
        if "fire inspection" in text or "fire marshal" in text:
            items.append(_item(result, "safety", "safety.fire_inspection.current", normalized_value, source))
        return items

    def _maintenance_receipt(self, result: ExtractResult, lines: list[SourceLine]) -> list[NormalizedEvidenceItem]:
        text = "\n".join(line.text for line in lines).lower()
        source = _first_line(lines, [r"\b(hood|clean|maintenance|service)\b"]) or (lines[0] if lines else None)
        if not source:
            return []
        value = _date_from_text(source.text)
        normalized_value = value.isoformat() if value else "documented"
        field = "safety.hood_cleaning.current" if "hood" in text else "operations.maintenance.program"
        return [_item(result, "maintenance", field, normalized_value, source)]

    def _declarations_page(self, result: ExtractResult, lines: list[SourceLine]) -> list[NormalizedEvidenceItem]:
        items: list[NormalizedEvidenceItem] = []
        source = _first_line(lines, [r"\b(policy period|effective|expiration|expires)\b"]) or (lines[0] if lines else None)
        if source:
            items.append(_item(result, "policy", "policy.current", _label_value(source.text) or "documented", source))
            expiration = _date_from_text(source.text)
            if expiration:
                items.append(_item(result, "policy", "policy.expiration.current", expiration.isoformat(), source, expires_on=expiration))
        class_line = _first_line(lines, [r"\b(classification|business class|class code)\b\s*[:\-]\s*(.+)"])
        if class_line:
            items.append(_item(result, "policy", "coverage.classification.current", _label_value(class_line.text), class_line))
        return items

    def _inspection_report(self, result: ExtractResult, lines: list[SourceLine]) -> list[NormalizedEvidenceItem]:
        source = _first_line(lines, [r"\b(fire inspection|inspection status|passed|approved)\b"]) or (lines[0] if lines else None)
        if not source:
            return []
        value = "passed" if re.search(r"\b(passed|approved|satisfactory)\b", source.text, re.I) else _label_value(source.text) or "documented"
        return [_item(result, "safety", "safety.fire_inspection.current", value, source)]

    def _generic_document(self, result: ExtractResult, lines: list[SourceLine]) -> list[NormalizedEvidenceItem]:
        items: list[NormalizedEvidenceItem] = []
        name_line = _first_line(lines, [r"\b(business name|named insured|tenant)\b\s*[:\-]\s*(.+)"])
        if name_line:
            items.append(_item(result, "other", "business.name", _label_value(name_line.text), name_line))
        address_line = _first_line(lines, [r"\b(address|premises|location)\b\s*[:\-]\s*(.+)"])
        if address_line:
            items.append(_item(result, "other", "business.address", _label_value(address_line.text), address_line))
        return items


def _source_lines(pages: list[ExtractPage]) -> list[SourceLine]:
    lines: list[SourceLine] = []
    for page in pages:
        if page.regions:
            for region in page.regions:
                for text_line in _split_lines(region):
                    lines.append(SourceLine(page_number=page.page_number, text=text_line, bbox=region.bbox))
        elif page.text:
            for text_line in page.text.splitlines():
                stripped = text_line.strip()
                if stripped:
                    lines.append(SourceLine(page_number=page.page_number, text=stripped))
    return lines


def _split_lines(region: ExtractRegion) -> list[str]:
    if not region.text:
        return []
    return [line.strip() for line in region.text.splitlines() if line.strip()]


def _first_line(lines: list[SourceLine], patterns: list[str]) -> SourceLine | None:
    for pattern in patterns:
        for line in lines:
            if re.search(pattern, line.text, re.I):
                return line
    return None


def _label_value(text: str) -> str | None:
    if ":" in text:
        return text.split(":", 1)[1].strip(" -")
    if "-" in text:
        return text.split("-", 1)[1].strip(" -")
    match = re.search(r"\b(?:business name|licensee|owner|name|address|classification|tenant|named insured)\b\s+(.+)", text, re.I)
    return match.group(1).strip() if match else text.strip()


def _date_from_text(text: str) -> date | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", text)
    return _parse_date(match.group(1)) if match else None


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    stripped = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return date.fromisoformat(stripped) if fmt == "%Y-%m-%d" else datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue
    return None


def _strength(confidence: float) -> EvidenceStrength:
    if confidence >= 0.85:
        return EvidenceStrength.verified
    if confidence >= 0.65:
        return EvidenceStrength.partially_verified
    if confidence > 0:
        return EvidenceStrength.weak_evidence
    return EvidenceStrength.missing


def _item(
    result: ExtractResult,
    category: str,
    field_name: str,
    value: str | None,
    source: SourceLine,
    *,
    confidence_boost: float = 0.0,
    expires_on: date | None = None,
) -> NormalizedEvidenceItem:
    confidence = min(1.0, result.confidence + confidence_boost)
    return NormalizedEvidenceItem(
        category=category,
        field_name=field_name,
        normalized_value=value,
        raw_value=value,
        evidence_strength=_strength(confidence),
        confidence=confidence,
        source_snippet=source.text,
        source_bbox_json=source.bbox,
        page_number=source.page_number,
        extractor_model_id=result.model_id,
        prompt_version=result.prompt_version,
        expires_on=expires_on,
    )


def _dedupe(items: list[NormalizedEvidenceItem]) -> list[NormalizedEvidenceItem]:
    seen: set[tuple[str, str | None]] = set()
    output: list[NormalizedEvidenceItem] = []
    for item in items:
        key = (item.field_name, item.normalized_value)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output
