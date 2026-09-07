# Cobri

Cobri is a bilingual Arabic/English AI tutor. **Co** comes from Concept; **bri** comes from Bridge.

This repository contains the shared Day 1 setup and **Moustafa's API foundation**: FastAPI configuration, JWT verification, and session/submission routes behind integration interfaces. Authentication verification is tested locally with generated signing keys. Learning routes are tested with clearly labeled test doubles.

Database persistence, durable enqueueing, worker processing, a fake evaluator, reviewed content, and model integration are still assigned to the other engineers. Normal API startup does not install test doubles; learning operations return `503` until their adapters are connected. Live identity-provider authentication and a real model-provider smoke test remain pending.

## Repository

```text
backend/
  pyproject.toml             Python dependencies and development tools
  uv.lock                   Reproducible dependency resolution
  src/cobri/                FastAPI application and integration contracts
  tests/                    Isolated API and cryptographic verifier tests
    fixtures/evaluations/   Reserved for Ahmed's labeled evaluation fixtures
frontend/                   Reserved for a later React/TypeScript frontend
content-packages/           Reserved for versioned, reviewed learning content
docs/
  architecture.md           Module boundaries and educational rules
  day1-contracts.md          API and adapter handoff contracts
  day1-handoff.md            Ownership, verification results, pending work
```

The repository uses Python 3.12, FastAPI, and Pydantic v2. PostgreSQL, SQLAlchemy, Alembic, and the durable queue are architecture decisions to be implemented by Mohamed. Only currently used feature modules have Python files.

## Local setup

Prerequisites: Git, PowerShell, `uv`, and network access for the initial Python/package downloads. Run the following from the repository root. The local Python installation avoids dependence on a system Python executable. Reapply the two environment variables in each new terminal.

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD ".cache/uv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD ".local/python"

uv python install 3.12 --no-bin --no-registry
uv sync --project backend --locked

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}
```

The guarded copy preserves existing local configuration. `.env`, virtual environments, downloaded Python, caches, tokens, and generated outputs must remain untracked. Example environment files, dependency lockfiles, migrations, and reviewed content remain trackable.

The application reads the root `.env` and environment variables; environment variables take precedence. Authentication configuration may remain unset for liveness and local automated testing. Do not paste access tokens or provider credentials into source, fixtures, shell history, or committed files.

## Run the API

```powershell
uv run --project backend --locked uvicorn cobri.main:app --reload
```

Open [API documentation](http://127.0.0.1:8000/docs) or [OpenAPI JSON](http://127.0.0.1:8000/openapi.json). In a second terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
```

`GET /health/live` returns `200` for a running process. `GET /health/ready` returns `503` until required authentication configuration and learning adapters are wired. Its `configuration_only` result does not probe JWKS, database, queue, or worker services. This is the expected initial runtime behavior, not a working persisted learning flow.

**Worker startup is pending Mohamed's worker entry point.** There is no worker executable or queue implementation in this change.

## Authentication

Configure `COBRI_AUTH_ISSUER`, `COBRI_AUTH_AUDIENCE`, and `COBRI_AUTH_JWKS_URL` for an identity provider. The JWKS URL is trusted application configuration. `COBRI_AUTH_ALGORITHMS` is a JSON array, defaulting to `["RS256"]`; `["ES256"]` is also supported when required by the provider. The default JWKS timeout is 5 seconds, cache lifetime is 300 seconds, and clock skew allowance is 0 seconds.

The verifier requires a valid signature, issuer, audience, subject, expiry, and applicable time claims. It derives learner identity from `(issuer, subject)`. No registration, token issuance, local login, or authentication bypass is implemented. Missing/invalid bearer tokens return `401`; authentication configuration or JWKS infrastructure failures return `503`.

`GET /api/v1/auth/me` returns the verified principal. Local cryptographic tests establish verifier behavior; they do not establish compatibility with an unconfigured live provider.

## Development checks

```powershell
uv run --project backend --locked ruff check backend
uv run --project backend --locked ruff format --check backend
uv run --project backend --locked pytest backend/tests
```

To format code:

```powershell
uv run --project backend --locked ruff format backend
```

After deliberately changing dependencies, update the manifest, regenerate `backend/uv.lock` with `uv lock --project backend`, and rerun the locked installation and checks. Mohamed will add SQLAlchemy, Alembic, and queue dependencies in the same manifest and lockfile.

The opt-in live-auth test skips by default. To run it, configure the provider above, supply `COBRI_LIVE_ACCESS_TOKEN` securely in your local environment, and explicitly enable the check:

```powershell
$env:COBRI_RUN_LIVE_AUTH = "1"
uv run --project backend --locked pytest backend/tests/test_live_auth.py
Remove-Item Env:COBRI_RUN_LIVE_AUTH -ErrorAction SilentlyContinue
Remove-Item Env:COBRI_LIVE_ACCESS_TOKEN -ErrorAction SilentlyContinue
```

This is an identity-provider test. The real Groq/OpenRouter model-provider smoke test remains Asser's responsibility and is not implemented here.

## API and ownership

| Engineer | Day 1 responsibility | Current integration boundary |
| --- | --- | --- |
| Moustafa (A) | Repository setup, API/configuration, auth verification, session/submission routes | This implementation |
| Mohamed (B) | Migrations, persistence, durable queue, worker | Session and submission service interfaces |
| Ahmed (C) | Shared schemas, labeled fixtures, fake evaluator | Review provisional HTTP models and evaluation views |
| Asser (D) | Initial content, model gateway, real provider smoke test | Content catalog interface; gateway work pending |

See [API and adapter contracts](docs/day1-contracts.md), [architecture](docs/architecture.md), and [handoff and verification](docs/day1-handoff.md). These assignments apply to Day 1; backend and AI/evaluation responsibilities swap on Day 2.

## Educational boundaries

Outcome correctness and reasoning correctness are separate. Insufficient evidence produces `uncertain`; a wrong answer alone does not establish a misconception. Model outputs must be schema validated, infrastructure failures must not become learner verdicts, and UI locale is independent of instructional language. Mastery eventually requires a transfer challenge; this foundation makes no mastery claims.

Remediation, transfer, sandbox execution, full RAG, profile recommendations, and frontend screens are outside this change.

## License

License selection and copyright-holder details are deferred. No `LICENSE` file or package license declaration has been added. The team must choose these after checking applicable hackathon requirements; MIT has not been assumed.
