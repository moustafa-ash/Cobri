# Repository Guidelines

## Project Structure & Module Organization

Cobri is a Python 3.12 FastAPI monorepo. Runtime code is under `backend/src/cobri/`; current feature modules are `identity`, `content`, `tutoring`, and `assessments`. Keep cross-cutting configuration and composition at the package root. Tests live in `backend/tests/`, with evaluation fixtures reserved under `backend/tests/fixtures/evaluations/`. `content-packages/` will hold reviewed, versioned learning content; `frontend/` is reserved for the later React/TypeScript client; `docs/` contains architecture and handoff contracts.

## Build, Test, and Development Commands

Run from the repository root in PowerShell:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD ".cache/uv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD ".local/python"
uv sync --project backend --locked
uv run --project backend --locked uvicorn cobri.main:app --reload
uv run --project backend --locked pytest backend/tests
uv run --project backend --locked ruff check backend
uv run --project backend --locked ruff format --check backend
```

The local root `venv/` and `requirements.txt` are convenience setup; `backend/pyproject.toml` and `backend/uv.lock` are authoritative. Copy `.env.example` to `.env` without committing secrets.

## Coding Style & Naming Conventions

Use Python 3.12, four-space indentation, type annotations, and async endpoints/adapters. Use `snake_case` for functions and variables, `PascalCase` for classes and Pydantic models, and lowercase module names. Keep Pydantic models explicit with `extra="forbid"`. Run Ruff before submitting changes; do not hand-edit `uv.lock`.

## Testing Guidelines

Use pytest and FastAPI’s test client. Name files `test_*.py` and tests `test_<behavior>`. Test authenticated ownership, Arabic/English locale independence, `uncertain` verdicts, malformed adapter responses, and infrastructure failures. Test doubles belong under `backend/tests/` only; never enable them in normal runtime. Live authentication is opt-in and requires local provider configuration.

## Commit & Pull Request Guidelines

Use short, imperative commit subjects, for example `Add session endpoint tests` or `Update auth configuration`. Keep commits focused. Pull requests should explain behavior and scope, list validation commands and results, identify pending integrations, and call out configuration or security changes. Do not include secrets, generated virtual environments, or unrelated formatting changes.

## Architecture & Security Rules

Outcome correctness and reasoning correctness are separate; insufficient evidence is `uncertain`. Infrastructure failures must not become learner verdicts. Derive ownership only from verified `(issuer, subject)`. Do not log bearer tokens or commit `.env`, provider keys, database credentials, or access tokens. Durable persistence, queueing, workers, canonical evaluation schemas, reviewed content, and model providers remain behind their documented interfaces until their owners implement them.
