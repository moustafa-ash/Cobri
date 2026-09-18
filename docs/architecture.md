# Day 1 architecture

```text
Authenticated client
        |
    FastAPI API
   /      |       \
 JWT   SQLAlchemy  reviewed content
       repositories       |
          |          python-functions
          |
   sessions/submissions/idempotency/jobs
          |
   database-polling worker
       /          \
 Docker sandbox   evaluation gateway
                  /              \
             Groq primary    OpenRouter fallback
```

The API is responsible for authentication, ownership, validation, and durable acceptance. It does not evaluate learner answers during the request. The worker owns processing and writes either a validated evaluation or a failed job without a learner verdict.

## Modules

| Module | Responsibility |
| --- | --- |
| `identity` | JWT verification and principal extraction |
| `content` | Reviewed immutable package and item lookup |
| `tutoring` | Session creation and owned session reads |
| `assessments` | Submission acceptance and result views |
| `evaluations` | Canonical outcome, reasoning, diagnostic, and evidence types |
| `persistence` | SQLAlchemy models, transactions, idempotency, leases, and heartbeat |
| `model_gateway` | Provider-independent structured model calls and fixture fallback |
| `sandbox` | Bounded Docker execution of package-owned tests |
| `worker` | Polling, retries, recovery, evaluation, and persistence |

## Invariants

- Ownership is always derived from verified issuer and subject.
- Submission acceptance and evaluation-job creation are one durable transaction.
- A job is not a learner verdict.
- Outcome correctness and reasoning quality are separate fields.
- Insufficient evidence is diagnostic `uncertain`.
- Draft content cannot be selected.
- Model responses are schema-validated before persistence.
- Provider and sandbox failures remain retryable infrastructure status.
- Test doubles are test-only and never installed by production composition.

## Operational modes

Local development defaults to SQLite, deterministic evaluation, and the API plus `cobri-worker` processes. PostgreSQL is supported through `COBRI_DATABASE_URL`. Real OIDC and provider checks are opt-in. Docker sandbox execution is enabled with `COBRI_SANDBOX_ENABLED=true` and requires Docker Desktop Linux containers.

The frontend now exposes persisted activity counts; durable learner history and transfer-gated
mastery are implemented. Retrieval vectors and quarantined official-source metadata have durable
boundaries, while model downloads, live provider quality, profile recommendations, and hosted
journeys remain gated integrations.

Learner events are append-only and progress is a versioned projection keyed by verified owner,
package version, and item. Content release actions append immutable ledger records; package bytes
are never rewritten by review, publication, supersession, or rollback.
