from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from coverready_api.config.settings import Settings
from coverready_api.main import create_app


@pytest.fixture()
def app_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'coverready-test.db'}",
        storage_dir=tmp_path / "uploads",
        runtime_dir=tmp_path / "runtime",
        as_of_date="2026-04-22",
        extractor_mode="fixture",
        jobs_eager=True,
    )


@pytest.fixture()
def client(app_settings: Settings) -> TestClient:
    app = create_app(app_settings)
    return TestClient(app)
