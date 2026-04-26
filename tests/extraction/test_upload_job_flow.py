from __future__ import annotations

from sqlalchemy import select

from coverready_api import models


def test_workspace_upload_creates_job_extracts_evidence_and_recomputes_score(client):
    workspace_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "Sunset Bistro LLC",
            "address": "42 Market Street",
            "industry_code": "restaurant",
            "state": "CA",
        },
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]

    upload_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        data={"document_type": "business_license"},
        files={"file": ("business-license.pdf", b"%PDF fixture bytes", "application/pdf")},
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()
    document_id = payload["document"]["id"]
    assert payload["job"]["status"] == "ready"

    status_response = client.get(f"/api/v1/documents/{document_id}/status")
    evidence_response = client.get(f"/api/v1/documents/{document_id}/evidence")
    score_response = client.get(f"/api/v1/workspaces/{workspace_id}/score")

    assert status_response.status_code == 200
    assert status_response.json()["job"]["status"] == "ready"
    assert status_response.json()["document"]["latest_job_stage"] == "ready"
    assert status_response.json()["document"]["latest_job_attempt"] == 1
    assert evidence_response.status_code == 200
    fields = {item["field_name"] for item in evidence_response.json()}
    assert {"license.current", "business.name", "business.address"}.issubset(fields)
    assert any(item["extractor_model_id"] for item in evidence_response.json())
    assert score_response.status_code == 200
    assert score_response.json()["business_profile_id"] == workspace_id


def test_evidence_review_actions_persist_and_rescore(client):
    workspace_id = client.post("/api/v1/workspaces", json={"name": "Acme Cafe", "industry_code": "restaurant"}).json()["id"]
    created = client.post(
        "/api/v1/evidence",
        json={
            "workspace_id": workspace_id,
            "category": "operations",
            "field_name": "operations.training.current",
            "normalized_value": "Fire safety training completed",
            "source_snippet": "Fire safety training completed",
        },
    )
    assert created.status_code == 200
    evidence_id = created.json()["evidence"]["id"]
    assert created.json()["evidence"]["review_status"] == "approved"

    edited = client.patch(f"/api/v1/evidence/{evidence_id}", json={"normalized_value": "Fire safety training completed 2026-04-20"})
    assert edited.status_code == 200
    assert edited.json()["evidence"]["review_status"] == "edited"
    assert edited.json()["scorecard"]["business_profile_id"] == workspace_id

    approved = client.post(f"/api/v1/evidence/{evidence_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["evidence"]["review_status"] == "approved"

    rejected = client.post(f"/api/v1/evidence/{evidence_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["evidence"]["status"] == "rejected"

    evidence_rows = client.get(f"/api/v1/evidence?business_profile_id={workspace_id}").json()
    persisted = next(row for row in evidence_rows if row["id"] == evidence_id)
    assert persisted["review_status"] == "rejected"
    assert persisted["status"] == "rejected"


def test_workspace_events_stream_replays_live_events(client):
    workspace_id = client.post("/api/v1/workspaces", json={"name": "Event Cafe", "industry_code": "restaurant"}).json()["id"]
    upload_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        data={"document_type": "business_license"},
        files={"file": ("business-license.pdf", b"%PDF fixture bytes", "application/pdf")},
    )
    assert upload_response.status_code == 200

    with client.stream("GET", f"/api/v1/workspaces/{workspace_id}/events?replay_only=true") as response:
        assert response.status_code == 200
        lines = response.iter_lines()
        first_lines = [next(lines) for _ in range(2)]

    assert first_lines[0].startswith("event:")
    assert first_lines[1].startswith("data:")


def test_raw_payload_and_document_pages_are_persisted(client):
    workspace_id = client.post("/api/v1/workspaces", json={"name": "Acme Cafe", "industry_code": "restaurant"}).json()["id"]
    document_id = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        data={"document_type": "business_license"},
        files={"file": ("business-license.pdf", b"%PDF fixture bytes", "application/pdf")},
    ).json()["document"]["id"]

    app = client.app
    with app.state.session_maker() as session:
        extraction_run = session.scalar(select(models.ExtractionRun).where(models.ExtractionRun.document_id == document_id))
        pages = session.scalars(select(models.DocumentPage).where(models.DocumentPage.document_id == document_id)).all()

    assert extraction_run is not None
    assert extraction_run.raw_response
    assert extraction_run.model_id == "fixture-nemotron-parse"
    assert pages
    assert pages[0].page_number == 1
