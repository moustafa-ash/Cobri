# Day 1 API and adapter contracts

These contracts are implemented by the FastAPI API, SQLAlchemy repositories, database worker, content catalog, evaluation layer, and provider gateway.

## Authentication and HTTP behavior

All `/api/v1/` routes require a bearer token verified against configured issuer, audience, JWKS, algorithms, expiry, and time claims. The principal is `{issuer, subject}`. Clients cannot submit an owner ID. Health endpoints are public.

| Method and path | Success | Behavior |
| --- | --- | --- |
| `GET /health/live` | `200` | Process liveness |
| `GET /health/ready` | `200` or `503` | Configuration, database, reviewed-content, and worker-heartbeat readiness |
| `GET /api/v1/auth/me` | `200` | Verified principal |
| `POST /api/v1/sessions` | `201` | Create an owned session pinned to a reviewed package/version |
| `GET /api/v1/sessions/{session_id}` | `200` | Retrieve an owned session |
| `POST /api/v1/sessions/{session_id}/submissions` | `202` | Atomically store submission, idempotency record, and evaluation job |
| `GET /api/v1/submissions/{submission_id}` | `200` | Retrieve owned submission, job state, and completed evaluation |

Errors are `401` for authentication failures, `404` for absent or foreign resources, `409` for changed idempotency payloads, `422` for invalid input, `503` for unavailable infrastructure, and `500` for invalid adapter responses. No error returns a learner verdict.

## Canonical evaluation

```text
OutcomeVerdict: correct | incorrect | unverified
ReasoningVerdict: sound | partial | incorrect | insufficient
DiagnosticStatus: supported | uncertain

Evaluation:
  outcome_verdict
  reasoning_verdict
  diagnostic_status
  evidence_references: string[]
  misconception_id: string | null
```

Outcome and reasoning are independent. `uncertain` belongs to diagnostic support, not to the reasoning enum. Infrastructure failure, provider exhaustion, malformed model output, and sandbox failure are job failures and never evaluation values.

## Persistence and idempotency

`Idempotency-Key` is required and scoped to `(issuer, subject, session_id)`. Identical validated payloads replay the original submission and job IDs. Changed payloads return `409`. The database transaction must commit the submission, idempotency record, and pending job together before the API returns `202`.

The repositories use SQLAlchemy async with SQLite for local development and PostgreSQL for deployment. The worker claims jobs with leases, bounded retries, stale-lease recovery, and duplicate-safe evaluation persistence. PostgreSQL uses row locking with `SKIP LOCKED`; SQLite serializes the local single-worker path.

## Content catalog

Content packages are JSON documents under `content-packages/` with package ID, immutable version, topic, review status, bilingual prompt/title, expected answer metadata, package-owned tests, evidence references, misconception IDs, and transfer metadata. A package or item is selectable only when its status is `reviewed`.

The initial package is `python-functions` version `1.0.0`, covering parameters, return values, and print-versus-return misconceptions.

## Evaluation and provider boundary

The deterministic fixture evaluator is available without external credentials. When configured, the model gateway tries Groq first and OpenRouter second. Responses must validate against the canonical Pydantic model before persistence. Provider timeouts, quota errors, malformed responses, and total exhaustion remain retryable infrastructure failures.

## Sandbox boundary

When enabled, the worker runs only package-owned Python tests in an ephemeral Docker container with no network, read-only root filesystem, non-root user, dropped capabilities, no-new-privileges, CPU/memory/PID limits, bounded temporary storage, timeout, output limits, and forced cleanup. Docker unavailability is an infrastructure result, not a learner verdict.
