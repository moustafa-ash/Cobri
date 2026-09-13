# Day 1 handoff

Day 1 is implemented locally across the API, persistence, evaluation, content, worker, provider, sandbox, and OIDC boundaries. Groq, OpenRouter, Docker, PostgreSQL, and Auth0 have been smoke-tested locally.

## Delivered

| Area | Current state |
| --- | --- |
| Repository and tooling | Private GitHub repository created at `moustafa-ash/Cobri` and pushed to `origin/main`; Python 3.12, uv lockfile, Alembic, Ruff, tests, environment template |
| API | FastAPI health, auth, session, submission, and polling routes |
| Identity | JWT signature, issuer, audience, JWKS, expiry, algorithm, and ownership checks |
| Persistence | Async SQLAlchemy repositories compatible with SQLite and PostgreSQL |
| Acceptance | Atomic submission, idempotency record, and evaluation job transaction |
| Worker | Database polling, leases, retry limits, stale-job recovery, heartbeat, duplicate-safe completion |
| Evaluation | Canonical outcome/reasoning/diagnostic schema and deterministic offline evaluator |
| Content | Versioned bilingual Python-functions package with reviewed-package enforcement |
| Providers | Groq-first/OpenRouter-fallback structured gateway, validated before persistence |
| Sandbox | Optional Docker runner with bounded, network-isolated execution |

## Runtime boundaries

The default API process uses `cobri.main:app`. It installs the local SQLite repositories and reviewed content catalog. The separate worker is started with `cobri-worker`. Test doubles remain under `backend/tests/` and are never imported by normal runtime composition.

`202` is returned only after the database transaction stores the submission, idempotency key, and evaluation job. A worker later changes the job to `succeeded` with an evaluation or to `failed` without a learner verdict.

## Verification status

The external checks below are the Day 1 record. They are not evidence that those services are
available in the current environment. At the Day 2 baseline audit, Docker was unavailable on
`PATH`; live Auth0, provider, Docker, and PostgreSQL checks remained pending re-verification.

- Locked dependency synchronization: passed.
- API and integration suite at Day 1: passed, `125 passed, 1 skipped`; the skipped test is live OIDC.
- SQLite acceptance, replay, conflict, concurrent duplicate requests, worker evaluation, and restart-compatible schema: passed.
- Provider fallback and structured response validation: passed with mocked providers; live Groq and OpenRouter structured-output requests passed.
- Reviewed-content rejection: passed.
- Docker sandbox live execution: passed with the digest-pinned Python image for both passing and failing learner tests.
- Live OIDC: passed with the Auth0 EU tenant and RS256 custom API configuration.
- Real PostgreSQL smoke test: passed against a disposable PostgreSQL 16 container; SQLite remains the default local database.

## Contracts and invariants

- Ownership is derived from verified `(issuer, subject)`, never request data.
- Outcome correctness and reasoning quality remain independent.
- `DiagnosticStatus.UNCERTAIN` means evidence is insufficient; provider or infrastructure failure is not a learner result.
- Evidence references are retained with evaluations.
- Draft content is never selectable.
- Only package-owned tests are sent to the sandbox.
- No bearer tokens or provider credentials are logged or committed.

## Deferred work

Frontend screens, full RAG, remediation, mastery and profile transitions, transfer execution, and license selection remain outside this Day 1 implementation. The proposed follow-up is tracked in [Day 2 plan](day2-plan.md).
