from __future__ import annotations

from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def load_extraction_prompt(document_type: str) -> str:
    shared = (PROMPT_DIR / "shared_contract.v1.md").read_text()
    specific_path = PROMPT_DIR / f"{document_type}.v1.md"
    specific = specific_path.read_text() if specific_path.exists() else (PROMPT_DIR / "generic_document.v1.md").read_text()
    return f"{shared}\n\n{specific}"
