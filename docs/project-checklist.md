# Cobri project checklist

This is the living completion checklist for the Cobri learner-facing MVP and its production-ready release. Update it only when the corresponding implementation and acceptance checks are complete.

Last reconciled against the local working tree: 2026-09-19. Remote settings and deployment were not inspected or changed.

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
- [x] Select Apache-2.0 and add `LICENSE` plus the Cobri copyright notice in `NOTICE`.
- [x] Add automated CI checks for backend and frontend validation.
- [ ] Apply branch protection, review, and release-tagging rules. (Required settings are specified in docs/governance.md; the GitHub rules themselves were not changed or verified.)

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
- [x] Pass the current offline backend suite: `156 passed, 4 skipped` (live integrations remain opt-in).
- [x] Pass Ruff check and formatting validation.
- [x] Pass SQLite acceptance, replay, conflict, concurrency, worker, and restart-compatible schema tests.
- [x] Pass mocked provider fallback and structured-response validation.
- [x] Smoke-test live Groq and OpenRouter structured responses locally.
- [x] Smoke-test Docker sandbox success and learner-test failure locally.
- [x] Smoke-test Auth0 OIDC locally using the configured EU tenant and RS256 API.
- [x] Smoke-test PostgreSQL 16 locally in a disposable container.
- [ ] Automate opt-in live OIDC and provider checks in an approved secure environment. (The protected preview workflow invokes the checks; the external environment is not provisioned or verified.)
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
- [x] Keep the tutoring chat mounted while a Monaco coding workspace opens beside it on desktop and as a full-screen drawer on mobile.
- [x] Return to the chat after code and reasoning submission, then present evaluation, remediation, practice, and transfer progression in the conversation.
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
- [ ] Add an opt-in live browser authentication test that skips clearly when credentials are unavailable. (The current live script checks a supplied token against the API; it does not exercise the browser login lifecycle.)

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

- [x] Implement typed tutoring states and guarded progression in `backend/src/cobri/tutoring/contracts.py`; assessment/practice/transfer progression is transactionally applied with evaluation events.
- [x] Persist assessment, diagnosis, intervention, retry, transfer, mastery, and profile-update event types with state changes in `backend/src/cobri/persistence/repositories.py`.
- [x] Require changed-context transfer, sandbox-owned test success, sound reasoning, and a valid same-session/package parent chain before mastery.
- [x] Provider output alone cannot award mastery; absent sandbox success cannot master.
- [x] Add learner concept history and progress views based on auditable evidence.
- [x] Add authenticated `GET /api/v1/profile` with deterministic reviewed-content recommendation reason codes; it returns no private learner text.
- [x] Support multiple lessons while preserving immutable package versions for historical sessions.
- [ ] Extend coverage for every legal/illegal state edge, progression replay, multi-worker concurrency, and failure recovery. (Mastery gating and exported/audited history are tested; full transition-matrix and concurrent profile updates are not.)

## 5. Content and retrieval maturity

- [x] Formalize the content lifecycle: draft, review, publish, supersede, and rollback. (The workflow and immutable release ledger are tested; no human publication approval is claimed.)
- [x] Define independent reviewer role and digest-bound acceptance criteria for accuracy, sources, rubrics, misconceptions, bilingual equivalence, tests, and transfer in docs/governance.md.
- [x] Obtain the independent content and dataset approval described by those criteria. (Digest-bound approval by moustafa-ash is recorded; no package publish or release occurred.)
- [x] Complete the Python control-flow package technically and validate prerequisites. (Package bytes remain immutable; its exact-digest review is recorded in the manifest and ledger, and the local catalog now recognizes that ledger approval without editing package bytes. No external deployment or release occurred.)
- [x] Obtain Moustafa's independent content sign-off for every control-flow item before any release.
- [x] Validate every package for stable IDs, prerequisites, evidence, misconceptions, interventions, tests, and language mappings.
- [ ] Add content-version migration and compatibility checks without mutating historical packages.
- [x] Build semantic retrieval only after deterministic retrieval is accepted.
- [x] Record embedding/index versions, retrieval filters, conflicts, and source provenance.
- [x] Decide whether controlled web retrieval belongs in the product; if approved, add source, safety, and conflict controls. (Approved sources are restricted to HTTPS `docs.python.org` results and remain quarantined until review.)
- [ ] Build a content authoring/review workflow or CMS only after the package lifecycle is stable.

## 6. Evaluation quality and model operations

- [ ] Build a representative, versioned evaluation dataset with Arabic and English examples. (120 structurally valid cases: 60 per language, 10 per each of six categories/language; each case has digest-bound reviewer approval, but synthetic benchmark quality is not established.)
- [x] Add dataset cases for correct/sound, reasoning disagreement, supported misconception, prerequisite gap, insufficient evidence, and adversarial behavior; all 120 cases have explicit reviewer approval recorded in the manifest.
- [ ] Measure and pass outcome accuracy, reasoning classification, diagnostic precision, uncertainty calibration, and evidence grounding separately. (The provider report separates available metrics; confidence calibration is blocked because providers return no confidence signal. No live provider result or quality pass is claimed.)
- [x] Provide independently selectable Groq-only and OpenRouter-only benchmark modes with no fallback between them. (Runs remain blocked until Moustafa approves the fixture and credentials are explicitly configured.)
- [x] Define selected quality gates: 100% safety, at least 90% for scored core metrics, and at least 95% supported Recall@3.
- [ ] Select latency, quota-failure, and cost thresholds before provider operations are considered production-ready.
- [x] Persist runtime provider/model, prompt/schema/rubric, exact package digest/version, deterministic retrieval index, dataset applicability, latency, and fallback provenance via migration `0007`.
- [ ] Add adversarial tests for prompt injection, malformed outputs, unsafe code, and evidence fabrication. (Sandbox, provider-failure, and fabricated-evidence coverage exists; explicit prompt-injection and malformed-output cases remain incomplete.)
- [ ] Require human review before promoting model or prompt changes.
- [ ] Integrate provider/model/latency/fallback/quota/failure metrics and thresholds in production operations. (Local worker records provider/model/latency/fallback aggregates without prompts or answers; quota/failure reporting and a deployed metrics backend remain open.)

## 7. Operations, security, and privacy

- [x] Add structured request and job logs with correlation IDs, duration, status, retry count, and safe error details.
- [x] Add metrics for accepted, replayed, conflicted, queued, running, succeeded, failed, retried, and stale-recovered work.
- [x] Add production-safe CORS, trusted hosts/origins, request-size limits, and rate limiting.
- [x] Document a threat model covering identity/ownership, content, providers, sandboxing, and operator access in `docs/governance.md` (production residual risks remain).
- [x] Define learner-data minimization, retention-until-explicit-deletion, operator-mediated export/deletion, and audit policy in `docs/governance.md`; add exact-target export CLI `backend/scripts/export_learner.py`.
- [ ] Verify by tests that logs, traces, analytics, and all provider requests exclude tokens and unnecessary learner content. (Safe error logging and aggregate metrics exist; complete provider-request/log privacy coverage remains open.)
- [ ] Add dependency, container, and secret scanning with an owned remediation process. (Dependency and tracked-secret scans run in CI; a full-SHA-pinned container scan and named remediation owner are still required.)
- [ ] Define credential storage and rotation for every environment.
- [ ] Add database backup, restore, migration, rollback, and disaster-recovery procedures and tests. (`ops/backup.sh`, target-bound destructive `ops/restore.sh`, migration checks, and vendor-neutral procedure exist; disposable PostgreSQL backup/restore and DR drills remain opt-in/unverified.)
- [x] Add an operational runbook for readiness, stuck jobs, provider outages, stale leases, and credential rotation.

## 8. Deployment and release

- [ ] Select and document the preview/staging and production hosting architecture. (OCI and Render preview paths are documented; production architecture is not selected.)
- [ ] Provision production PostgreSQL and decide whether the database queue remains sufficient.
- [ ] Add portable digest-pinned API/worker images and deploy with reproducible builds. (No production host was selected; container images and builds are not yet implemented.)
- [ ] Configure environment isolation, managed secrets, TLS, domains, and least-privilege network access.
- [x] Add CI/CD gates for tests, linting, typing, migrations, dependency and secret checks, checksummed artifacts, and preview promotion.
- [ ] Deploy a shared preview environment and pass the full end-to-end flow there.
- [ ] Add production observability, alerting, uptime checks, and incident ownership.
- [ ] Run bounded load, competing-worker, stale-lease, sandbox-capacity, and provider-degradation checks. (Existing stale-lease/worker tests pass; bounded load/capacity and degradation profiles remain open.)
- [ ] Automate accessibility checks for English/Arabic, keyboard use, RTL/LTR, mobile/desktop, focus, semantics, and contrast. (Existing deterministic browser flow runs; automated accessibility coverage is not present.)
- [ ] Complete accessibility, privacy, security, educational-quality, and release reviews. (Content/evaluation item sign-off is recorded; automated accessibility and complete privacy/security gates, provider evaluation, and release approval remain open.)
- [ ] Verify a clean-checkout installation and document deployment, rollback, and operator procedures. (Deployment and rollback docs exist; fresh clean-install verification and built images remain open.)
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

## Current local acceptance evidence (2026-09-19)

- Backend full suite: **164 passed, 4 skipped** using the local Python 3.12 environment. Skips are opt-in live Auth0, Groq/OpenRouter, and PostgreSQL tests; they are not passes.
- Ruff check and format: passed after formatting the current changes.
- Alembic migration test including `0007_evaluation_provenance`: **1 passed** on disposable SQLite.
- Content prerequisite/lifecycle validation and deterministic 120-case dataset validation: passed. Dataset output says quality/safety **not claimed** pending human/provider evaluation.
- Frontend typecheck, Vitest (**6 passed**), ESLint, and production build passed. Build reports the existing large Monaco-related chunk warning.
- Deterministic Playwright learner flow passed at desktop (1280x900) and mobile (390x844); this is not an Auth0 journey or automated accessibility audit.
- `git diff --check`: passed.
- Wheel/container build: not verified. `uv build` was blocked because the sandbox cannot reach PyPI to resolve Hatchling; no build success is claimed.
- Human approval: `moustafa-ash` approved all content items and evaluation cases; digest-bound records are in the review manifest and content release ledger. Provider quality evaluation and external release remain separate gates.
- External state: no GitHub rules, providers, cloud infrastructure, deployment, tag, or release action was performed.
