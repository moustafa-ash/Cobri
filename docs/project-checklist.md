# Cobri project checklist

This is the living completion checklist for the Cobri learner-facing MVP and its production-ready release. Update it only when the corresponding implementation and acceptance checks are complete.

## Status rules

- `[x]` means implemented and verified in the current repository or explicitly recorded as a completed smoke test in the Day 1 handoff.
- `[ ]` means required work is not yet complete.
- A successful local or opt-in smoke test does not mean the integration is production-deployed.
- Infrastructure failures must remain operational failures and must never become learner verdicts.

## 1. Repository and project foundation

- [x] Create the private `moustafa-ash/Cobri` GitHub repository and push the project to `origin/main`.
- [x] Establish the Python 3.12 FastAPI monorepo structure.
- [x] Make `backend/pyproject.toml` and `backend/uv.lock` the authoritative dependency files.
- [x] Add Ruff, pytest, Alembic, environment templates, and local setup documentation.
- [x] Ignore secrets, local databases, virtual environments, and generated local tooling state.
- [x] Document architecture, API contracts, Day 1 handoff, Day 2 plan, and the local Day 2 runbook.
- [ ] Select a project license and add the approved license file.
- [ ] Add automated CI checks for backend and frontend validation.
- [ ] Define branch protection, review, and release-tagging rules.

## 2. Day 1 backend foundation

### API and identity

- [x] Add liveness and readiness endpoints.
- [x] Add authenticated principal, session creation/read, submission, and polling routes.
- [x] Verify JWT signature, issuer, audience, JWKS, expiry, time claims, and allowed algorithms.
- [x] Derive ownership only from the verified `(issuer, subject)` pair.
- [x] Keep absent and foreign resources ownership-safe.
- [x] Keep authentication failures separate from unavailable authentication infrastructure.

### Persistence and asynchronous evaluation

- [x] Add async SQLAlchemy repositories compatible with SQLite and PostgreSQL.
- [x] Add the initial Alembic migration and schema lifecycle.
- [x] Atomically persist the submission, idempotency record, and evaluation job before returning `202`.
- [x] Scope idempotency to learner and session, replay identical requests, and reject changed payloads.
- [x] Add a database-polling worker with leases, retries, stale-job recovery, heartbeat, and duplicate-safe completion.
- [x] Store either a validated evaluation or a failed job without a learner verdict.

### Evaluation, content, providers, and sandbox

- [x] Define canonical outcome, reasoning, diagnostic, misconception, and evidence fields.
- [x] Keep outcome correctness independent from reasoning quality.
- [x] Represent insufficient diagnostic evidence as `uncertain`.
- [x] Add a deterministic offline evaluator for credential-free development and tests.
- [x] Add a provider-independent structured gateway with Groq first and OpenRouter fallback.
- [x] Validate provider responses against the canonical schema before persistence.
- [x] Add the reviewed, immutable, bilingual `python-functions` content package.
- [x] Reject draft content and preserve evidence references.
- [x] Add optional bounded Docker execution for package-owned Python tests.
- [x] Keep provider, sandbox, and other infrastructure failures out of learner evaluations.
- [x] Keep runtime composition free of test doubles.

### Day 1 verification record

- [x] Pass locked dependency synchronization.
- [x] Pass the recorded backend suite: `125 passed, 1 skipped`.
- [x] Pass Ruff check and formatting validation.
- [x] Pass SQLite acceptance, replay, conflict, concurrency, worker, and restart-compatible schema tests.
- [x] Pass mocked provider fallback and structured-response validation.
- [x] Smoke-test live Groq and OpenRouter structured responses locally.
- [x] Smoke-test Docker sandbox success and learner-test failure locally.
- [x] Smoke-test Auth0 OIDC locally using the configured EU tenant and RS256 API.
- [x] Smoke-test PostgreSQL 16 locally in a disposable container.
- [ ] Automate opt-in live OIDC and provider checks in an approved secure environment.
- [ ] Verify all external integrations in the shared preview or staging environment.

## 3. Learner-facing vertical slice

### Stable integration contract

- [x] Freeze frontend contracts for session creation, submission acceptance, polling, evaluation failure, and authentication errors.
- [x] Add stable error codes and end-to-end correlation IDs without exposing secrets or internal exceptions.
- [x] Pin the reviewed content package version used by the learner flow.
- [x] Cover success, pending, failure, `401`, ownership-safe missing resources, replay, and conflict behavior with contract tests.

### Frontend

- [x] Create the React and TypeScript frontend application.
- [x] Add accessible login, lesson/session, submission, evaluation, remediation, and transfer routes.
- [x] Start with bilingual topic chat, offer matching reviewed lesson options, and clearly reject unsupported topics.
- [x] Add a centrally typed or generated API client to prevent contract drift.
- [x] Add a repeatable frontend lint gate.
- [x] Handle `202` polling, retries, expired authentication, and ownership-safe errors.
- [x] Add explicit loading, empty, signed-out, infrastructure-failure, retry, and recovery states.
- [x] Keep interface locale separate from instructional language.
- [x] Provide Arabic and English copy, correct RTL/LTR behavior, and a visible language switch.
- [x] Verify keyboard use, screen-reader semantics, contrast, and responsive mobile/desktop layouts.

### Real browser authentication

- [x] Create and configure the local Auth0 single-page application using Authorization Code with PKCE.
- [ ] Configure exact callback, logout, allowed-origin, issuer, and API-audience values for each environment.
- [x] Use API access tokens rather than ID tokens for backend authorization.
- [x] Approve and document in-memory browser token storage with refresh-token rotation.
- [ ] Verify login, logout, reload, expiry recovery, and authenticated API calls in the browser.
- [ ] Add an opt-in live browser authentication test that skips clearly when credentials are unavailable.

### Reviewed-content retrieval

- [x] Define a retrieval port that returns package/version, item, evidence, rubric, misconception criteria, and transfer metadata.
- [x] Implement deterministic retrieval from the selected reviewed package before semantic retrieval.
- [x] Test item retrieval in Arabic and English.
- [x] Preserve evidence identifiers through retrieval, evaluation, persistence, and presentation.
- [x] Return an honest supported or uncertain diagnosis when evidence is missing or conflicting.
- [x] Keep a later-compatible semantic retrieval adapter boundary without making it a dependency of the first vertical slice.

### Remediation, retry, and transfer

- [x] Map a supported misconception to a short evidence-grounded bilingual explanation.
- [x] Select a targeted practice item without overwriting the original submission.
- [x] Persist remediation and retry attempts through the existing ownership and job interfaces.
- [x] Select a fresh, changed-context transfer challenge from reviewed package metadata.
- [x] Evaluate and persist the transfer attempt independently.
- [x] Preserve `uncertain` when the evidence does not support a named misconception.

### Vertical-slice acceptance

- [x] Let a learner sign in, open a reviewed lesson, submit an answer and reasoning, and poll to completion.
- [x] Show separate outcome, reasoning, evidence, and diagnostic results.
- [x] Complete one supported remediation/retry or show an honest uncertain state.
- [x] Complete and evaluate one transfer challenge.
- [x] Recover safely from pending and failed infrastructure work.
- [x] Pass the deterministic browser-to-API-to-database-to-worker-to-evaluation flow at mobile and desktop widths.

## 4. Complete tutoring and learner model

- [ ] Implement the authoritative tutoring state machine and validate every legal transition.
- [ ] Add persisted learner events for assessment, diagnosis, intervention, retry, transfer, and profile updates.
- [ ] Define mastery criteria that require successful changed-context transfer.
- [ ] Prevent a model response alone from declaring mastery or changing learner state.
- [ ] Add learner concept history and progress views based on auditable evidence.
- [ ] Add safe profile recommendations without exposing private reasoning or unsupported claims.
- [ ] Support multiple lessons while preserving immutable package versions for historical sessions.
- [ ] Add tests for state transition ordering, replay, concurrency, failure recovery, and audit history.

## 5. Content and retrieval maturity

- [ ] Formalize the content lifecycle: draft, review, publish, supersede, and rollback.
- [ ] Define reviewer roles and acceptance criteria for educational accuracy, sources, rubrics, and bilingual quality.
- [ ] Add more reviewed concepts and transfer items beyond the initial Python-functions package.
- [ ] Validate every package for stable IDs, prerequisites, evidence, misconceptions, interventions, tests, and language mappings.
- [ ] Add content-version migration and compatibility checks without mutating historical packages.
- [ ] Build semantic retrieval only after deterministic retrieval is accepted.
- [ ] Record embedding/index versions, retrieval filters, conflicts, and source provenance.
- [ ] Decide whether controlled web retrieval belongs in the product; if approved, add source, safety, and conflict controls.
- [ ] Build a content authoring/review workflow or CMS only after the package lifecycle is stable.

## 6. Evaluation quality and model operations

- [ ] Build a representative, versioned evaluation dataset with Arabic and English examples.
- [ ] Add regression cases for correct answers, incorrect reasoning, known misconceptions, prerequisite gaps, and insufficient evidence.
- [ ] Measure outcome accuracy, reasoning classification, diagnostic precision, uncertainty calibration, and evidence grounding separately.
- [ ] Compare pinned Groq, OpenRouter, and optional provider/model profiles without automatic fallback hiding attribution.
- [ ] Define quality, latency, quota, and cost acceptance thresholds.
- [ ] Add prompt, model, schema, rubric, and evaluation-dataset version tracking.
- [ ] Add adversarial tests for prompt injection, malformed outputs, unsafe code, and evidence fabrication.
- [ ] Require human review before promoting model or prompt changes.
- [ ] Add provider usage, latency, fallback, quota, and failure monitoring without logging learner secrets.

## 7. Operations, security, and privacy

- [x] Add structured request and job logs with correlation IDs, duration, status, retry count, and safe error details.
- [x] Add metrics for accepted, replayed, conflicted, queued, running, succeeded, failed, retried, and stale-recovered work.
- [x] Add production-safe CORS, trusted hosts/origins, request-size limits, and rate limiting.
- [ ] Complete a threat model covering authentication, ownership, content, providers, sandboxing, and administrative access.
- [ ] Define learner-data classification, retention, deletion, export, and audit policies.
- [ ] Verify that logs, traces, analytics, and provider requests do not expose tokens or unnecessary learner data.
- [ ] Add dependency, container, and secret scanning with an owned remediation process.
- [ ] Define credential storage and rotation for every environment.
- [ ] Add database backup, restore, migration, rollback, and disaster-recovery procedures and tests.
- [x] Add an operational runbook for readiness, stuck jobs, provider outages, stale leases, and credential rotation.

## 8. Deployment and release

- [ ] Select and document the preview/staging and production hosting architecture.
- [ ] Provision production PostgreSQL and decide whether the database queue remains sufficient.
- [ ] Containerize and deploy the API and worker with pinned, reproducible builds.
- [ ] Configure environment isolation, managed secrets, TLS, domains, and least-privilege network access.
- [ ] Add CI/CD gates for tests, linting, typing, migrations, security checks, and artifact provenance.
- [ ] Deploy a shared preview environment and pass the full end-to-end flow there.
- [ ] Add production observability, alerting, uptime checks, and incident ownership.
- [ ] Run load, concurrency, worker-recovery, sandbox-capacity, and provider-degradation tests.
- [ ] Complete accessibility, privacy, security, educational-quality, and release reviews.
- [ ] Verify a clean-checkout installation and document deployment, rollback, and operator procedures.
- [ ] Tag the approved release and publish the final handoff without secrets or unsupported claims.

## 9. Final definition of done

- [ ] A learner can securely complete the bilingual assessment, reasoning evaluation, supported diagnosis or uncertainty, remediation/retry, changed-context transfer, and profile-update loop.
- [ ] Every learner-facing diagnosis and explanation is grounded in reviewed, versioned evidence.
- [ ] Ownership, idempotency, persistence, retries, and audit history remain correct under concurrency and failure.
- [ ] External provider, OIDC, database, and sandbox integrations are verified in the target deployed environment.
- [ ] Quality, security, privacy, accessibility, operational, and recovery acceptance criteria pass.
- [ ] The approved license, architecture, contracts, runbooks, contributor guidance, and release handoff are current.
- [ ] The production release is deployed, monitored, recoverable, and approved by the project owners.

## Explicitly deferred unless the product scope changes

These items are not required to complete the current Cobri MVP:

- Social features.
- Payments and subscriptions.
- Organization-level administration.
- Arbitrary unreviewed web content.
- A large curriculum-authoring CMS.
