# CoverReady

CoverReady is a local-first underwriting-readiness workspace for small businesses. It helps owners or brokers organize proof, score insurance readiness, spot missing critical documents, translate policy language, and simulate how better documentation could improve underwriting clarity.

## What is implemented

- FastAPI backend with:
  - SQLite test/dev fallback plus Postgres-ready Docker persistence
  - live workspace APIs
  - upload-to-processing-job document extraction flow
  - Celery/Redis worker path for background extraction
  - Nemotron Parse / Nemotron OCR adapter abstractions with fixture fallback
  - deterministic scoring engine with rule-based caps
  - inspectable score reasons linked to evidence IDs
  - missing-document detection
  - translator, scenario, broker-packet preview, and document routes
- Next.js 15 frontend scaffold with:
  - Upload / Intake
  - Proof Vault
  - Score Dashboard
  - Missing Documents
  - Coverage Translator
  - Scenario Simulator
  - Broker Packet Preview
  - polling-first realtime updates with SSE acceleration
- Shared taxonomy, contracts, and UI tokens packages
- Pytest coverage for scoring, caps, missing-document logic, and API flows

## Quick Start

### Backend

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
COVERREADY_EXTRACTOR_MODE=fixture COVERREADY_JOBS_EAGER=true \
  PYTHONPATH=apps/api uvicorn coverready_api.main:app --reload --app-dir apps/api
```

Run tests:

```bash
PYTHONPATH=apps/api pytest -q
```

Run Alembic migrations against the configured database:

```bash
COVERREADY_DATABASE_URL=postgresql+psycopg://coverready:coverready@localhost:5432/coverready \
  alembic upgrade head
```

Run a local worker when Redis is available:

```bash
PYTHONPATH=apps/api celery -A coverready_api.jobs.celery_app.celery_app worker --loglevel=INFO
```

### Frontend

Node and `pnpm` are required but were not installed in this workspace during implementation.

```bash
corepack enable
pnpm install
pnpm --filter web dev
```

Set `NEXT_PUBLIC_API_BASE_URL` if the API is not at `http://localhost:8000/api/v1`.

### Docker Compose

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

Optional profiles:

- `--profile ai` for Ollama
- `--profile retrieval` for Qdrant

The default compose stack starts Postgres, Redis, API, worker, and web. It uses `COVERREADY_EXTRACTOR_MODE=fixture` so the upload/extract/normalize/score path works without hosted AI credentials.

### NVIDIA Build Hosted API Mode

Set the NIM-compatible base URL and API key for the API and worker:

```bash
export COVERREADY_NIM_BASE_URL=https://integrate.api.nvidia.com
export COVERREADY_NIM_API_KEY=<your-nvidia-api-key>
export COVERREADY_EXTRACTOR_MODE=nim
export COVERREADY_PARSE_MODEL=nvidia/nemotron-parse
export COVERREADY_OCR_MODEL=nvidia/nemotron-ocr-v1
```

Then run the API and Celery worker. CoverReady calls OpenAI-style `/v1/chat/completions`; Nemotron Parse uses the `markdown_bbox` tool so bounding boxes can be persisted when available.

### Self-Hosted NIM Mode

Start your Nemotron Parse/OCR NIM services on a GPU/HPC node and point CoverReady at the service base URL:

```bash
export COVERREADY_NIM_BASE_URL=http://<nim-host>:8000
export COVERREADY_NIM_API_KEY=not-used
export COVERREADY_EXTRACTOR_MODE=nim
```

Use the same Postgres and Redis settings for both API and worker so processing jobs can be picked up consistently.

## Realtime Architecture

CoverReady runs in live database mode only. The database is the durable source of truth for workspaces, documents, processing jobs, evidence review state, scorecards, and broker packets. Redis is used only to fan out transient events between the API, worker, and connected browsers.

- Uploads create a persisted `documents` row and a persisted `processing_jobs` row.
- Jobs move through real backend stages: `queued`, `extracting`, `normalizing`, `scoring`, `ready`, or `failed`.
- The web app polls workspace snapshot and job endpoints with React Query. Polling runs quickly while jobs are active and slows/stops when terminal states are reached.
- `GET /api/v1/workspaces/{workspace_id}/events` streams SSE events for job, document, evidence, score, and packet updates.
- SSE events invalidate React Query caches; missed events are harmless because polling and page refresh rebuild state from the database.
- Evidence approve, reject, edit/save, manual evidence add, reprocess, rescore, and packet refresh all write through backend APIs before the UI updates.

For local realtime:

```bash
COVERREADY_EXTRACTOR_MODE=fixture COVERREADY_JOBS_EAGER=false \
  PYTHONPATH=apps/api uvicorn coverready_api.main:app --reload --app-dir apps/api

PYTHONPATH=apps/api celery -A coverready_api.jobs.celery_app.celery_app worker --loglevel=INFO

pnpm --filter web dev
```

Use `COVERREADY_JOBS_EAGER=true` when you want inline processing without a worker.

## Scoring Engine

- Rules are versioned JSON under [packages/taxonomy/rulesets](packages/taxonomy/rulesets).
- The scoring engine lives under [apps/api/coverready_api/services/scoring.py](apps/api/coverready_api/services/scoring.py).
- Grade multipliers are deterministic and inspectable.
- Every persisted score reason stores linked `source_evidence_ids`.
- LLM-style explanation calls are optional and degrade to deterministic summaries when Ollama is unavailable.

## Key Paths

- [docs/architecture.md](docs/architecture.md)
- [apps/api/coverready_api/main.py](apps/api/coverready_api/main.py)
- [apps/api/coverready_api/services/scoring.py](apps/api/coverready_api/services/scoring.py)
- [apps/web/app/score-dashboard/page.tsx](apps/web/app/score-dashboard/page.tsx)

## Current Limits

- Document rendering uses stored backend file bytes; source-box highlighting depends on extraction providers returning bounding boxes.
- Qdrant/retrieval remains intentionally unwired for this slice.
- Broker packet PDF export is still preview-first.
