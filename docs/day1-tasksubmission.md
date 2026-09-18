# Day 1 engineering progress report

**Project:** Cobri intelligent tutoring platform
**Scope:** API, persistence, evaluation, content, worker, provider, and sandbox foundation
**Status:** Locally verified; Auth0 OIDC is configured and live-verified

## Completed work

- Repaired Ahmed’s refactor so every runtime and test import uses the installed `cobri` package.
- Kept configuration, dependency composition, and error translation at the package root.
- Added canonical Pydantic evaluation contracts with independent outcome, reasoning, and diagnostic fields.
- Added a bilingual, versioned Python-functions package with evidence, misconception, rubric, and transfer metadata.
- Added reviewed-package enforcement in the content catalog.
- Added async SQLAlchemy models and repositories for sessions, submissions, idempotency, jobs, evaluations, and worker heartbeats.
- Added Alembic migration support and SQLite local runtime with PostgreSQL compatibility.
- Added atomic submission acceptance, replay/conflict semantics, concurrent idempotency handling, leases, retries, stale-job recovery, and duplicate-safe completion.
- Replaced hard-coded evaluation placeholders with deterministic offline evaluation and a validated Groq-first/OpenRouter-fallback gateway.
- Added an optional digest-pinned Docker sandbox with no network, read-only root, non-root execution, resource limits, timeout, and cleanup.
- Added the `cobri-worker` executable and runtime readiness checks.

## Verification

The locked environment passes Ruff, formatting, Alembic SQLite upgrade, runtime imports, API tests, persistence tests, worker tests, provider-fallback tests, content tests, and sandbox tests. Live Docker sandbox execution, Groq/OpenRouter structured-output requests, a PostgreSQL migration smoke test, and Auth0 OIDC authentication also passed.

Historical Day 1 result: `125 passed, 1 skipped`; current offline evidence is maintained in `docs/verification-report.md`.

## Educational and security invariants

Outcome correctness and reasoning quality remain separate. Insufficient evidence is represented as diagnostic `uncertain`. Infrastructure errors never become learner verdicts. Ownership is derived from verified issuer and subject. No credentials or bearer tokens are logged or committed. Only package-owned tests are executed by the sandbox.

## Deferred scope

Frontend screens, full RAG, remediation, mastery and profile transitions, transfer execution, and license selection remain later work.
