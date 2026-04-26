# CoverReady Foundations

## Repo Tree

```text
coverready/
  apps/
    api/coverready_api/      FastAPI app, scoring engine, live job services, SSE events
    web/                     Next.js 15 frontend with live polling and proof drawer
  packages/
    contracts/               Shared TypeScript API contracts
    taxonomy/                Versioned scoring rulesets and caps
    ui/                      Shared UI navigation and evidence-strength tokens
  demo/restaurant/           Test fixture data for deterministic scoring tests
  infra/docker/              Docker Compose and container entrypoints
  tests/                     Pytest coverage for scoring and API flows
```

## Core Schema

- `business_profiles`: single-workspace business record with industry, origin, and address.
- `documents`: uploaded documents with type, checksum, dates, origin, local storage path, and latest job summary.
- `document_assets`: page/image metadata and extracted text snippets.
- `ocr_runs`: OCR attempts and extracted text records.
- `extraction_runs`: document extraction outputs and fallback/manual-review payloads.
- `evidence_items`: normalized underwriting evidence with field, value, strength, confidence, source snippet, and expiration.
- `claims` and `claim_evidence_links`: derived underwriting claims tied back to supporting evidence IDs.
- `scorecards`: persisted total score, dimension breakdowns, caps, quick wins, and explanation metadata.
- `score_reason_items`: inspectable rule-by-rule scoring reasons with point deltas and source evidence IDs.
- `missing_requirements`: structured missing/expired/weak document list for action prioritization.
- `translator_runs`, `scenario_runs`, `broker_packets`: cached explanation, scenario, and packet-preview outputs.

## Realtime Design

- The database is the durable source of truth.
- Redis Pub/Sub is used only as transient fan-out for events from API and Celery worker processes.
- The frontend polls workspace snapshot and job endpoints with React Query.
- Polling runs quickly while jobs are active and slows/stops once `ready` or `failed`.
- `GET /api/v1/workspaces/{workspace_id}/events` provides SSE invalidation events for job, document, evidence, score, and packet updates.
- Browser refreshes reconstruct all state from persisted rows; no upload/job/evidence workflow depends on client-only state.

## Scoring Design

- Fixed dimension weights: documentation `25`, property safety `20`, operational controls `20`, coverage alignment `20`, renewal readiness `15`.
- Deterministic evidence multipliers:
  - `verified = 1.0`
  - `partially_verified = 0.6`
  - `weak_evidence = 0.25`
  - `missing = 0.0`
  - `expired = 0.0`
  - `conflicting = 0.0`
- Rules live in JSON under `packages/taxonomy/rulesets/` and are merged by industry.
- Score caps currently implemented:
  - missing/expired business license caps total score at `55`
  - missing/expired declarations page or policy excerpt caps at `65`
  - missing occupancy proof caps at `70`
  - missing restaurant fire-safety proof caps at `60`
  - conflicting named insured or address caps at `50`
- Every score reason stores `rule_id`, `dimension`, `points_awarded`, `points_possible`, and `source_evidence_ids`.

## Endpoint List

- `GET /api/v1/health`
- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`
- `GET /api/v1/workspaces/{id}`
- `PATCH /api/v1/workspaces/{id}`
- `POST /api/v1/workspaces/{id}/documents`
- `GET /api/v1/workspaces/{id}/documents`
- `GET /api/v1/workspaces/{id}/jobs`
- `GET /api/v1/workspaces/{id}/score`
- `GET /api/v1/workspaces/{id}/dashboard`
- `GET /api/v1/workspaces/{id}/events`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{id}`
- `GET /api/v1/documents/{id}/status`
- `GET /api/v1/documents/{id}/evidence`
- `GET /api/v1/documents/{id}/download`
- `POST /api/v1/documents/{id}/extract`
- `POST /api/v1/documents/{id}/reprocess`
- `POST /api/v1/evidence`
- `GET /api/v1/evidence`
- `GET /api/v1/evidence/{id}`
- `PATCH /api/v1/evidence/{id}`
- `POST /api/v1/evidence/{id}/approve`
- `POST /api/v1/evidence/{id}/reject`
- `GET /api/v1/claims`
- `GET /api/v1/missing-documents`
- `POST /api/v1/scorecards/recalculate`
- `GET /api/v1/scorecards/latest`
- `GET /api/v1/scorecards/{id}`
- `GET /api/v1/scorecards/{id}/proof`
- `POST /api/v1/translator/explain`
- `POST /api/v1/scenarios/simulate`
- `GET /api/v1/broker-packet/preview`
- `POST /api/v1/broker-packet/generate`
