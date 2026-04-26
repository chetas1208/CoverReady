from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from coverready_api.config.settings import Settings


@dataclass(frozen=True)
class RenderedPage:
    page_number: int
    data_url: str | None
    mime_type: str | None
    text_content: str | None = None
    image_path: str | None = None
    width: int | None = None
    height: int | None = None


def _data_url(path: Path, mime_type: str | None = None) -> str:
    detected_mime = mime_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{detected_mime};base64,{encoded}"


def render_document_pages(source_path: str, mime_type: str | None, settings: Settings) -> list[RenderedPage]:
    path = Path(source_path)
    detected_mime = mime_type or mimetypes.guess_type(path.name)[0]

    if detected_mime and detected_mime.startswith("text/"):
        return [RenderedPage(page_number=1, data_url=None, mime_type=detected_mime, text_content=path.read_text(errors="ignore"))]

    if detected_mime and detected_mime.startswith("image/"):
        return [RenderedPage(page_number=1, data_url=_data_url(path, detected_mime), mime_type=detected_mime, image_path=str(path))]

    if detected_mime == "application/pdf" or path.suffix.lower() == ".pdf":
        try:
            import fitz  # type: ignore

            output_dir = settings.runtime_dir / "rendered_pages" / path.stem
            output_dir.mkdir(parents=True, exist_ok=True)
            pages: list[RenderedPage] = []
            with fitz.open(path) as pdf:
                for index, page in enumerate(pdf, start=1):
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    page_path = output_dir / f"{uuid4()}-page-{index}.png"
                    pixmap.save(page_path)
                    text_content = page.get_text("text") or None
                    pages.append(
                        RenderedPage(
                            page_number=index,
                            data_url=_data_url(page_path, "image/png"),
                            mime_type="image/png",
                            text_content=text_content,
                            image_path=str(page_path),
                            width=pixmap.width,
                            height=pixmap.height,
                        )
                    )
            if pages:
                return pages
        except Exception:
            # If page rendering is unavailable, still provide the original bytes
            # so a compatible provider can attempt direct ingestion.
            pass

    return [RenderedPage(page_number=1, data_url=_data_url(path, detected_mime), mime_type=detected_mime, image_path=str(path))]
