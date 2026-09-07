# Day 1 handoff

This handoff covers shared repository preparation and Moustafa's personal implementation scope. Team ownership applies to Day 1 only; backend and AI/evaluation responsibilities swap on Day 2. Preserve these boundaries when changing owners.

## What this change supplies

| Area | Supplied behavior | Limits |
| --- | --- | --- |
| Repository | Python 3.12/uv project, lockfile, environment example, ignore rules, development instructions | License deferred; no remote, push, or commit requested |
| API | FastAPI configuration, OpenAPI, liveness/readiness, auth/session/submission routes | Default learning adapters remain unavailable |
| Authentication | JWT verification with trusted issuer/audience/JWKS/algorithm configuration | Local signing-key tests are not a live-provider verification |
| Learning HTTP boundary | Input/output validation, ownership-aware adapter calls, status and error mapping | Persistence, queue, and worker not implemented |
| Evaluation boundary | Separate outcome/reasoning verdict views with explicit `uncertain` | No fake evaluator, canonical shared schemas, or model gateway |
| Test doubles | Automated-test-only session/content/submission responses | No in-memory server, login bypass, real content, or durable processing |

See [contracts](day1-contracts.md) for exact API views, asynchronous adapter methods, retry semantics, and ownership rules. See [architecture](architecture.md) for all feature boundaries and educational invariants.

## Verification record

Verification ran locally on 2026-09-07 from the repository root. These checks cover Moustafa's API boundary and test doubles only; they do not establish B/C/D's integrations.

| Check | Result |
| --- | --- |
| Workspace-local Python 3.12 install and locked `uv sync` | Passed with CPython 3.12.14 and 34 installed packages |
| `ruff check backend` | Passed |
| `ruff format --check backend` | Passed; 25 files formatted |
| Automated tests | 117 passed, 1 skipped; live auth skipped by design; 2 upstream TestClient deprecation warnings |
| Actual Uvicorn startup, OpenAPI, liveness, expected unready status | Passed; `/docs` and `/openapi.json` returned `200`, liveness `200`, unconfigured readiness `503`, unauthenticated `/auth/me` `401` |
| Ignore rules keep secrets/generated outputs out and source/lockfiles/content trackable | Passed for representative paths, including `.env`, local runtimes, caches, lockfile, migrations, and reviewed content |
| Live identity-provider authentication | Pending provider configuration and test access token |
| PostgreSQL persistence, durable enqueueing, restart/concurrency behavior | Pending Mohamed's implementation |
| Worker startup | Pending Mohamed's entry point; no runnable worker command yet |
| Canonical evaluation schemas and fake evaluator | Pending Ahmed's implementation |
| Reviewed topic/package, model gateway, real provider smoke test | Pending Asser's implementation and credentials |

The readiness response is a configuration/wiring check; it does not contact JWKS, database, queue, or worker services. The executable local verification commands are in the root README. The live-auth check is opt-in through `COBRI_RUN_LIVE_AUTH=1`; supply the test access token securely through `COBRI_LIVE_ACCESS_TOKEN`. The default test suite explicitly skips that check when it is not enabled/configured.

## Ordered ownership and integration

| Order | Owner | Work / dependency |
| --- | --- | --- |
| 1 | Moustafa (A) | Shared repository, Python/dependencies, environment setup, documentation |
| 2 | Moustafa; review by B/C/D | Provisional HTTP contracts and asynchronous integration interfaces |
| 3 | Moustafa | Configuration, health, JWT verifier, auth principal endpoint |
| 4 | Moustafa | Session endpoints against session/content interfaces; isolated tests |
| 5 | Moustafa | Submission acceptance/polling against durable-service contract; isolated tests |
| 6 | Moustafa | Run documented commands, record results, clarify limitations for handoff |
| Parallel dependency | Mohamed (B) | SQLAlchemy/Alembic migrations, persistence, queue selection, atomic acceptance, separate worker entry point |
| Parallel dependency | Ahmed (C) | Canonical schema review, labeled fixtures, reproducible fake evaluator |
| Parallel dependency | Asser (D) | One reviewed programming topic/package, content adapter, model gateway, provider smoke test |

No external team messages have been sent by this implementation. This document coordinates interfaces for the engineers to review.

## Pending decisions and evidence

- **License:** select the license and exact copyright holder after checking hackathon requirements. Do not create `LICENSE` or package-license metadata until chosen.
- **Authentication:** agree on a live OIDC provider, issuer, audience, trusted JWKS URL, algorithm, and safe test access token. Registration/token issuance are outside this API scope.
- **Mohamed:** choose queue technology and demonstrate atomic submission plus durable work acceptance, owned reads, idempotency under concurrent retries, restart recovery, and honest adapter readiness. Provide the worker startup command with the actual entry point.
- **Ahmed:** review the provisional models and provide canonical evaluation types, evidence-supported labels, and an explicit `uncertain` path. No API verdict should be generated from infrastructure errors.
- **Asser:** deliver the reviewed package/version/item mapping, content-catalog implementation, gateway interface, and real provider smoke result. Without credentials, mark the real provider check pending.

When real adapters arrive, connect them at the dependency boundary and rerun the isolated tests plus true persistence/queue/authentication integration checks. Replace test-only evidence with actual integration evidence only after those checks run successfully.

## Day 2 carryover

Unfinished B/C/D items remain their Day 1 work; record unresolved integration checks for the incoming owners after the responsibility swap. Carry forward the contracts, test commands, actual verification results, and this implementation's limitations.

Remediation, transfer challenges, sandbox execution, full RAG, profile recommendations, and frontend screens remain outside this change. Transfer is a future requirement for mastery; Day 1 makes no mastery claims.
