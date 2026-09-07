# Day 1 architecture

Cobri means Concept Bridge. This change prepares the shared repository and implements Moustafa's API/configuration, JWT verifier, and session/submission endpoints. The API is stateless: authenticated ownership is derived from a verified issuer and subject, and durable state belongs behind Mohamed's adapters.

## Runtime boundary

```text
Future React/TypeScript client
              |
        FastAPI API process
        /        |         \
JWT verifier  session /   content catalog
   |          submission    interface
Trusted JWKS  interfaces       |
              |             Asser: pending
         Mohamed: pending
              |
      PostgreSQL + durable work obligation
              |
    Separate worker from the backend codebase
              |
  Ahmed's evaluator / Asser's model gateway
```

Only the API process, JWT verifier, and integration contracts exist in this change. The database, durable queue, worker, evaluator, content catalog implementation, and model gateway are dependencies owned by B/C/D. Test doubles are injected only by automated tests. Production/default application wiring never imports them and returns `503` for unavailable adapters.

The API does not evaluate a submission or infer a learner result during acceptance. It returns `202` only after the submission service promises that both the submission and evaluation work obligation have been durably stored. This promise is a required integration contract, not a durability guarantee established by the API tests.

## Feature modules

| Module | Responsibility | Day 1 implementation here |
| --- | --- | --- |
| `identity` | Verified identity and authentication integration | JWT verifier and principal endpoint |
| `content` | Versioned content access | Narrow catalog interface only |
| `tutoring` | Session orchestration | Session routes and provisional HTTP contracts |
| `assessments` | Submission acceptance and result views | Routes and provisional integration contracts |
| `retrieval` | Context retrieval / RAG | Future; no empty package |
| `model_gateway` | Provider-independent model access; Groq and OpenRouter | Asser's dependency; no implementation |
| `evaluations` | Evaluation schemas, fake/real evaluation | Ahmed's dependency; no implementation |
| `sandbox` | Isolated execution | Future; no empty package |
| `profiles` | Learning profile and recommendations | Future; no empty package |

Shared application configuration, dependency wiring, and error translation stay at the package root. The first feature packages exist because current endpoints consume them, without introducing unused abstractions.

## Durable work and failure handling

Mohamed selects the durable queue implementation. A PostgreSQL jobs table can persist a submission and its pending job in one transaction. With an external broker, a transactional outbox or equivalent durable handoff must preserve the obligation to enqueue even if the process dies after the database commit. A separate uncoordinated save followed by broker publication does not satisfy the contract.

The service accepts an idempotency key scoped to `(issuer, subject, session_id)`. An identical validated request replays the same submission/job identifiers; a changed payload returns a conflict. Ownership and idempotency must be enforced inside Mohamed's durable operation, including concurrent requests. The API's earlier ownership lookup is useful validation and is not a substitute for that transaction check.

Unavailable infrastructure yields an HTTP infrastructure error or a failed processing status without an evaluation. A schema-invalid adapter response is an integration error. Neither case becomes an incorrect learner answer or reasoning verdict.

Readiness reports required configuration/adapters; initial unconfigured startup is deliberately not ready. Liveness only states that the API process is running. Readiness does not prove a model, database transaction, broker, or live identity provider works.

## Educational invariants

- Outcome correctness and reasoning correctness are separate verdicts.
- Insufficient evidence produces `uncertain`; missing reasoning remains representable.
- A wrong answer alone does not prove a misconception.
- Mastery eventually requires a transfer challenge. Day 1 does not infer mastery.
- Model outputs and dependency results must pass schema validation before exposure.
- Infrastructure failures must not become learner failures.
- UI locale and instructional language are independent preferences, each currently `ar` or `en`.

Remediation, transfer challenges, sandbox execution, full RAG, profile recommendations, and frontend screens are outside this implementation. The first reviewed programming topic remains an Asser/Ahmed content decision.
