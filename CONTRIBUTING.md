# Contributing

Use Python 3.12 and the locked backend/frontend dependencies. Before proposing a change, run:

```powershell
uv run --project backend --locked ruff check backend
uv run --project backend --locked ruff format --check backend
uv run --project backend --locked pytest backend/tests -p no:cacheprovider
cd frontend; npm ci; npm run typecheck; npm test -- --run; npm run lint; npm run build
```

Keep changes focused and add a regression check for behavior changes. Never commit credentials, learner exports, generated local databases, or unreviewed content as reviewed. Pull requests to `main` require one independent approval and the required CI jobs; repository rules must be configured by an owner. Only the gated release workflow may create release tags after approvals and checks.

Content authors must use immutable package versions and the release ledger. A package or evaluation dataset is not reviewed until the review manifest is explicitly signed against its current digest by `moustafa-ash`.
