# Current project status

Audit date: 2026-09-19. This is the current evidence record; older Day 1 reports remain historical snapshots.

## Verified locally

- Backend: `135 passed, 1 skipped` with the opt-in live Auth0 test skipped because `COBRI_RUN_LIVE_AUTH=1` was not set.
- Frontend: 5 Vitest tests passed, TypeScript typecheck passed, and the production build passed.
- Root browser flow: 1 Chromium Playwright test passed in 3.8 seconds through the existing `frontend/visual.html` deterministic fixture.
- The deterministic browser fixture covers topic discovery, lesson selection, the coding workspace, answer submission, evaluation feedback, and remediation copy.
- Ruff, Docker, PostgreSQL, provider, Auth0, deployment, and preview-host checks were not rerun in this audit and are not claimed as current evidence.

## Current boundaries

- Local development uses SQLite, the deterministic evaluator, and separate API/worker processes.
- Auth0, Groq, OpenRouter, Docker, PostgreSQL, and deployment checks are opt-in or environment-dependent.
- The root Playwright test does not authenticate against Auth0 or call external providers. It mounts the real learner UI with the existing deterministic fixture API.
- No production deployment, license selection, semantic retrieval, mastery model, or learner profile system is complete.

## Primary commands

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD ".cache/uv"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD ".local/python"
uv run --project backend --locked pytest backend/tests -p no:cacheprovider
cd frontend; npm test -- --run; npm run typecheck; npm run build
cd ..; npx playwright test --project=chromium
```
