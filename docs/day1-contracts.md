# Day 1 API and adapter contracts

These are provisional HTTP contracts owned by Moustafa for isolated API development. Ahmed owns canonical shared schemas and should review these before integration. The Python models and generated OpenAPI are the executable source of truth; this document records ownership, behavior, and handoff requirements.

## Authentication and HTTP behavior

All `/api/v1/` routes require a bearer access token verified against configured issuer, audience, JWKS, and allowed algorithms. The principal is `{issuer, subject}`. Clients cannot set a resource owner in the request body. Health endpoints are public.

| Method and path | Success | Behavior |
| --- | --- | --- |
| `GET /health/live` | `200` | API process liveness |
| `GET /health/ready` | `200` when configured | `503` while required configuration/adapters are unavailable |
| `GET /api/v1/auth/me` | `200` | Verified issuer and subject |
| `POST /api/v1/sessions` | `201` | Validate selectable content version, then create session |
| `GET /api/v1/sessions/{session_id}` | `200` | Retrieve the authenticated learner's session |
| `POST /api/v1/sessions/{session_id}/submissions` | `202` | Validate ownership/item, then atomically accept through the adapter |
| `GET /api/v1/submissions/{submission_id}` | `200` | Retrieve submission, job state, and validated evaluation if available |

Errors: `401` for missing/invalid tokens; `404` for absent resources or another learner's resources; `409` for conflicting idempotency-key reuse; `422` for invalid request data; `503` for unavailable authentication or integration dependencies; `500` for invalid adapter responses. Errors must not echo secrets or produce learner verdicts.

Authentication requires `iss`, `aud`, `sub`, and `exp`, signature verification, and applicable time checks. The trusted algorithm allowlist defaults to RS256, with ES256 supported through configuration. Algorithm names supplied by the JWT do not establish allowed algorithms. JWKS retrieval is bounded, cached, and does not block the API event loop. Live provider verification remains pending.

## HTTP views

Request and response models reject unexpected fields. IDs such as package/version/item are nonblank strings of at most 128 characters. Resource and job identifiers are UUIDs. Timestamps are timezone-aware UTC. Nonblank text is preserved, including Arabic characters and meaningful whitespace.

### Session

`SessionCreate`:

```json
{
  "content_package_id": "example-package",
  "content_version": "example-version",
  "ui_locale": "en",
  "instructional_language": "ar"
}
```

The package values above illustrate request shape; they do not name installed content. The content catalog must validate that the requested version is selectable.

`SessionView` contains the same four fields plus `session_id` and `created_at`. A session pins its content package and version. Locale and instructional language are separate required fields, each accepting `ar` or `en`.

### Submission, job, and evaluation

`SubmissionCreate` contains:

| Field | Constraint |
| --- | --- |
| `item_id` | Nonblank item identifier within the session's pinned content version |
| `answer` | Required nonblank string, at most 10,000 characters |
| `reasoning` | Optional string or `null`, at most 10,000 characters |

Omitted reasoning remains `null`. Its absence must not be treated as demonstrated incorrect reasoning. The request cannot include a verdict, misconception label, owner, package override, or mastery claim.

`SubmissionView` contains:

```text
submission_id: UUID
session_id: UUID
content_package_id: string
content_version: string
item_id: string
answer: string
reasoning: string | null
created_at: UTC datetime
job:
  job_id: UUID
  status: pending | running | succeeded | failed
evaluation: null | {
  outcome_verdict: correct | incorrect | uncertain
  reasoning_verdict: correct | incorrect | uncertain
}
```

An evaluation is required only when the job is `succeeded` and must be absent for `pending`, `running`, or `failed`. A failed job represents processing failure and has no learner verdict. The API validates adapter responses against these models before returning them. It does not evaluate answers, infer misconceptions, or assess mastery.

`uncertain` is a real permitted result for each verdict independently. An outcome can be correct while reasoning is incorrect or uncertain, and an incorrect answer alone cannot establish a specific misconception.

## Integration interfaces

All methods below are asynchronous. Interfaces live with the feature using them. Runtime composition passes implementations to `cobri.main.create_app(settings, session_store=..., submission_service=..., content_catalog=...)`; `backend/src/cobri/dependencies.py` resolves those values from application state and fails unavailable when they are absent. Tests override those resolver dependencies with classes under `backend/tests/`, and runtime code must not import those doubles.

| Interface and owner | Method | Required result / behavior |
| --- | --- | --- |
| `SessionStore` — Mohamed | `create_session(principal, request)` | Persist a session for the verified principal and return `SessionView` |
| `SessionStore` — Mohamed | `get_session(principal, session_id)` | Return `SessionView`; absent and other-owner sessions are indistinguishable |
| `SubmissionService` — Mohamed | `accept_submission(principal, session_id, request, idempotency_key)` | Atomically accept submission and durable evaluation work; return `SubmissionView` |
| `SubmissionService` — Mohamed | `get_submission(principal, submission_id)` | Return owned `SubmissionView`, including validated processing state |
| `ContentCatalog` — Asser | `require_package(package_id, version)` | Resolve a selectable package/version as a typed reference, or fail |
| `ContentCatalog` — Asser | `require_item(package_id, version, item_id)` | Resolve an item in that exact package/version as a typed reference, or fail |

For session creation, the API checks the content catalog before calling the session store. For submission acceptance, it first resolves the owned session, then validates the item against that session's package/version, then calls `accept_submission`. Mohamed must recheck ownership inside the durable operation to prevent races or alternate callers from bypassing the ownership requirement.

The API boundary validates expected resource identifiers and pinned content references in returned views. Adapters must never expose another learner's resource; ownership enforcement itself remains the adapter's responsibility because public views do not contain ownership metadata.

### Durable acceptance and idempotency

`Idempotency-Key` is required for every submission request. It must contain 1–128 printable, non-space ASCII characters. Its scope is the verified principal `(issuer, subject)` plus `session_id`.

1. The same key with the same validated payload must return the original submission and job IDs. Omitted reasoning and explicit `null` normalize to the same request.
2. The same key with a changed validated payload must raise an idempotency conflict, translated to `409`.
3. Submission storage, idempotency enforcement, ownership checking, and the durable obligation to evaluate must complete before success. Concurrent duplicate requests must not create duplicate work.
4. If the client loses the response after acceptance, retrying with the same key must recover the accepted resource.

Queue selection is **pending Mohamed's decision**. A PostgreSQL jobs table written in the submission transaction is sufficient. An external broker requires a transactional outbox or equivalent durable handoff; a separate save followed by uncoordinated enqueueing can lose work. The worker must account for retries and repeated delivery under Mohamed's chosen queue design.

Moustafa's doubles simulate acceptance/replay/conflict results to verify HTTP behavior. They do not persist data, process work, test transactions, demonstrate durable enqueueing, or establish exactly-once processing. Durability and concurrency checks belong to Mohamed's adapter integration tests.

## Handoff boundaries

- **Mohamed:** implement stores, migrations, durable acceptance, queue choice, worker, adapter readiness, and real transaction/concurrency tests. Add dependencies to the existing backend manifest and lockfile.
- **Ahmed:** review these DTOs; provide canonical schemas, labeled fixtures, and a fake evaluator whose results keep outcome and reasoning separate and support `uncertain`.
- **Asser:** choose and review the initial programming topic/package, implement content lookup, define the model gateway supporting Groq/OpenRouter, and run an opt-in real provider smoke test.
- **Moustafa:** connect reviewed adapters and schemas after delivery, configure a live identity provider, and validate the API against those actual dependencies.

Model outputs must pass Ahmed's schemas before becoming evaluation results. Missing credentials leave the real provider smoke test pending; canned HTTP responses must not be reported as model integration.
