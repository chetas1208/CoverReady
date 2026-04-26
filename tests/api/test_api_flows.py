from __future__ import annotations


def _create_live_restaurant_with_license(client) -> str:
    workspace_response = client.post(
        "/api/v1/workspaces",
        json={"name": "Live Bistro LLC", "address": "42 Market Street", "industry_code": "restaurant", "state": "CA"},
    )
    assert workspace_response.status_code == 200
    workspace_id = workspace_response.json()["id"]
    upload_response = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        data={"document_type": "business_license"},
        files={"file": ("business-license.pdf", b"%PDF fixture bytes", "application/pdf")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["job"]["status"] == "ready"
    return workspace_id


def test_live_workspace_upload_and_latest_scorecard(client):
    workspace_id = _create_live_restaurant_with_license(client)

    latest_response = client.get(f"/api/v1/scorecards/latest?business_profile_id={workspace_id}")
    assert latest_response.status_code == 200
    payload = latest_response.json()
    assert payload["business_profile_id"] == workspace_id
    assert payload["total_score"] <= 100
    assert payload["uncapped_total_score"] <= 100


def test_missing_documents_and_score_proof(client):
    workspace_id = _create_live_restaurant_with_license(client)
    latest = client.get(f"/api/v1/scorecards/latest?business_profile_id={workspace_id}").json()
    proof_response = client.get(f"/api/v1/scorecards/{latest['id']}/proof")
    missing_response = client.get(f"/api/v1/missing-documents?business_profile_id={workspace_id}")

    assert proof_response.status_code == 200
    proof_payload = proof_response.json()
    assert any(reason["source_evidence_ids"] for reason in proof_payload["reasons"])

    assert missing_response.status_code == 200
    missing_labels = {item["label"] for item in missing_response.json()}
    assert "Current fire suppression service proof" in missing_labels
    assert "Current declarations page or policy excerpt" in missing_labels


def test_upload_and_extract_live_document_fallback(client):
    upload_response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("restaurant-note.txt", b"Local upload with no OCR pipeline yet.", "text/plain")},
    )
    assert upload_response.status_code == 200
    document_id = upload_response.json()["document"]["id"]

    extract_response = client.post(f"/api/v1/documents/{document_id}/extract")
    assert extract_response.status_code == 200
    payload = extract_response.json()
    assert payload["document"]["id"] == document_id
    assert payload["job"]["status"] in {"ready", "queued", "extracting", "normalizing", "scoring"}
    assert payload["document"]["processing_status"] == payload["job"]["status"]
