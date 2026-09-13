# Cobri Day 2 local runbook

## Start

1. Copy `.env.example` to `.env` and configure backend authentication and provider settings.
2. Run `uv sync --project backend --locked`.
3. Start the API with `uv run --project backend --locked uvicorn cobri.main:app --reload`.
4. Start the worker with `uv run --project backend --locked cobri-worker`.
5. Copy `frontend/.env.example` to `frontend/.env.local`, configure Auth0, then run `npm install` and `npm run dev` from `frontend/`.

Use `http://localhost:5173` for the browser origin and configure that exact callback, logout, and
allowed web origin in Auth0. Tokens use the Auth0 React in-memory cache with refresh-token rotation.

## Readiness and recovery

- `GET /health/live` confirms the process is running.
- `GET /health/ready` requires configured authentication and a recent worker heartbeat.
- The worker renews leases and recovers expired jobs. Exhausted jobs become failed without a learner verdict.
- A failed submission can be retried after the infrastructure issue is resolved.
- Rotate credentials in the environment, restart API and worker, and verify readiness. Never log or commit secrets.

## Verification

Run the locked backend suite, Ruff checks, frontend typecheck/tests/build, and `npm run verify:browser`.
Docker, live Auth0, configured providers, and PostgreSQL checks are opt-in and remain incomplete
when those services are unavailable.
