from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_name: str = "CoverReady API"
    environment: str = Field(default_factory=lambda: os.getenv("COVERREADY_ENV", "development"))
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "COVERREADY_DATABASE_URL",
            f"sqlite:///{ROOT_DIR / 'apps' / 'api' / 'data' / 'runtime' / 'coverready.db'}",
        )
    )
    taxonomy_dir: Path = Field(default_factory=lambda: ROOT_DIR / "packages" / "taxonomy" / "rulesets")
    demo_seed_path: Path = Field(default_factory=lambda: ROOT_DIR / "demo" / "restaurant" / "seed.json")
    storage_dir: Path = Field(default_factory=lambda: ROOT_DIR / "apps" / "api" / "data" / "uploads")
    runtime_dir: Path = Field(default_factory=lambda: ROOT_DIR / "apps" / "api" / "data" / "runtime")
    as_of_date: str = Field(default_factory=lambda: os.getenv("COVERREADY_AS_OF_DATE", "2026-04-22"))
    ollama_url: str | None = Field(default_factory=lambda: os.getenv("COVERREADY_OLLAMA_URL"))
    explanation_model: str = Field(default_factory=lambda: os.getenv("COVERREADY_EXPLANATION_MODEL", "gemma3"))
    explanation_prompt_version: str = "score-v1"
    translator_prompt_version: str = "translator-v1"
    scenario_prompt_version: str = "scenario-v1"
    redis_url: str = Field(default_factory=lambda: os.getenv("COVERREADY_REDIS_URL", "redis://localhost:6379/0"))
    nim_base_url: str | None = Field(default_factory=lambda: os.getenv("COVERREADY_NIM_BASE_URL"))
    nim_api_key: str = Field(default_factory=lambda: os.getenv("COVERREADY_NIM_API_KEY", "not-used"))
    parse_model: str = Field(default_factory=lambda: os.getenv("COVERREADY_PARSE_MODEL", "nvidia/nemotron-parse"))
    ocr_model: str = Field(default_factory=lambda: os.getenv("COVERREADY_OCR_MODEL", "nvidia/nemotron-ocr-v1"))
    extraction_prompt_version: str = Field(default_factory=lambda: os.getenv("COVERREADY_EXTRACTION_PROMPT_VERSION", "extract-v1"))
    extractor_mode: str = Field(default_factory=lambda: os.getenv("COVERREADY_EXTRACTOR_MODE", "auto"))
    extraction_min_confidence: float = Field(
        default_factory=lambda: float(os.getenv("COVERREADY_EXTRACTION_MIN_CONFIDENCE", "0.55"))
    )
    extraction_min_text_length: int = Field(
        default_factory=lambda: int(os.getenv("COVERREADY_EXTRACTION_MIN_TEXT_LENGTH", "40"))
    )
    jobs_eager: bool = Field(
        default_factory=lambda: os.getenv("COVERREADY_JOBS_EAGER", "false").lower() in {"1", "true", "yes"}
    )

    def ensure_dirs(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
