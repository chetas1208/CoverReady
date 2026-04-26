from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from coverready_api import models
from coverready_api.schemas.extraction import ExtractResult, NormalizedEvidenceItem


class EvidenceWriter:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_machine_evidence(
        self,
        document: models.Document,
        result: ExtractResult,
        evidence_items: list[NormalizedEvidenceItem],
    ) -> list[models.EvidenceItem]:
        self.session.execute(delete(models.DocumentPage).where(models.DocumentPage.document_id == document.id))
        self.session.execute(
            delete(models.EvidenceItem).where(
                models.EvidenceItem.document_id == document.id,
                models.EvidenceItem.extractor_model_id.is_not(None),
            )
        )

        for page in result.pages:
            self.session.add(
                models.DocumentPage(
                    document_id=document.id,
                    page_number=page.page_number,
                    text_content=page.text,
                    image_path=page.image_path,
                    width=page.width,
                    height=page.height,
                    provider_page_id=page.provider_page_id,
                )
            )

        rows: list[models.EvidenceItem] = []
        for item in evidence_items:
            bbox = item.source_bbox_json.model_dump(mode="json") if item.source_bbox_json else None
            row = models.EvidenceItem(
                business_profile_id=document.business_profile_id,
                workspace_id=document.workspace_id,
                document_id=document.id,
                category=item.category,
                field=item.field_name,
                field_name=item.field_name,
                value=item.normalized_value,
                normalized_value=item.normalized_value,
                raw_value=item.raw_value,
                evidence_strength=item.evidence_strength.value,
                confidence=item.confidence,
                source_snippet=item.source_snippet,
                source_bbox_json=bbox,
                page_ref=f"p{item.page_number}" if item.page_number else None,
                page_number=item.page_number,
                expires_on=item.expires_on,
                is_conflicting=item.is_conflicting,
                extractor_model_id=item.extractor_model_id,
                prompt_version=item.prompt_version,
                status="active",
                review_status=item.status,
            )
            self.session.add(row)
            rows.append(row)

        self.session.flush()
        return rows
