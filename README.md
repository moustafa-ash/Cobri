# Cobri

Cobri is a bilingual Arabic/English tutoring platform. The Day 1 implementation contains a FastAPI API, durable SQLite/PostgreSQL-compatible persistence, a database job worker, reviewed content loading, canonical evaluation contracts, provider adapters, and an optional Docker sandbox.

## Repository

```text
backend/src/cobri/
  identity/       JWT verification and principal endpoint
  content/        reviewed versioned content catalog
  tutoring/       session contracts and routes
  assessments/    submission contracts and routes
  evaluations/    canonical learner-evaluation models
  model_gateway/  Groq/OpenRouter adapters and offline evaluator
  persistence/    SQLAlchemy models, repositories, and schema lifecycle
  sandbox/        bounded Docker-based Python execution
  worker.py       database-polling evaluation worker
backend/tests/   API, persistence, worker, provider, and sandbox tests
content-packages/ reviewed versioned learning packages
alembic/         database migration environment and revisions
```

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite, and PostgreSQL are supported. SQLite is the default local database. PostgreSQL uses the same repository interfaces through `asyncpg`.

## Local setup

Run from the repository root in PowerShell:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD ".cache/uv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD ".local/python"
uv sync --project backend --locked

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}
```

The default `.env` uses `sqlite+aiosqlite:///./.data/cobri.db`. Secrets and local databases remain ignored. Configure `COBRI_DATABASE_URL` with `postgresql+asyncpg://...` for PostgreSQL.

## Run the API and worker

```powershell
uv run --project backend --locked uvicorn cobri.main:app --reload
uv run --project backend --locked cobri-worker
```

The API creates the local schema on startup by default. For migration-controlled environments:

```powershell
uv run --project backend --locked alembic -c alembic.ini upgrade head
```

The worker claims pending jobs, evaluates submissions, retries transient failures, recovers stale leases, and writes evaluations idempotently. `/health/ready` remains unavailable until authentication is configured and a worker heartbeat is present.

## API behavior

Public health routes are `/health/live` and `/health/ready`. Authenticated routes are:

- `GET /api/v1/auth/me`
- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST /api/v1/sessions/{session_id}/submissions`
- `GET /api/v1/submissions/{submission_id}`

Ownership derives only from a verified `(issuer, subject)` pair. Submission acceptance requires `Idempotency-Key` and commits the submission, idempotency record, and evaluation job together before returning `202`.

Evaluations keep outcome correctness, reasoning quality, diagnostic support, evidence references, and misconception IDs separate. Infrastructure failures never become learner verdicts. Failed jobs contain no evaluation.

## Content and evaluation

The first package is `python-functions` version `1.0.0`. It covers parameters, return values, and print-versus-return misconceptions in Arabic and English. Only packages with `review_status: reviewed` are selectable.

Without model credentials, the worker uses the deterministic fixture evaluator. With credentials, it tries Groq first and OpenRouter second, validates structured responses against the canonical Pydantic schema, and retries provider failures.

Set `COBRI_SANDBOX_ENABLED=true` to execute package-owned Python tests inside Docker. The sandbox requires Docker Desktop with Linux containers and applies no-network, read-only, non-root, capability, CPU, memory, process, temporary-filesystem, timeout, and cleanup limits. If Docker is unavailable, the worker reports an infrastructure failure and does not produce a learner verdict.

## Verification

```powershell
uv run --project backend --locked ruff check backend
uv run --project backend --locked ruff format --check backend
uv run --project backend --locked pytest backend/tests
```

The live OIDC check is opt-in through `COBRI_RUN_LIVE_AUTH=1` and `COBRI_LIVE_ACCESS_TOKEN`. Groq/OpenRouter smoke tests are also opt-in and require their respective keys. Local cryptographic tests, SQLite persistence, deterministic evaluation, and API contract tests do not require external credentials.

See [API contracts](docs/day1-contracts.md), [architecture](docs/architecture.md), [Day 1 handoff](docs/day1-handoff.md), and the [Day 2 plan](docs/day2-plan.md).

## Scope and license

Frontend screens, full RAG, remediation, mastery decisions, profile recommendations, and transfer execution remain later milestones. License selection and copyright-holder details remain deferred.
