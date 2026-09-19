# Cobri Day 2 Plan

Status: the local deterministic learner-facing slice described here is implemented. Remaining Auth0 browser verification, live integrations, and production work stay open in the [project checklist](project-checklist.md). See [current status](current-status.md) for fresh evidence.

## Objective

Turn the verified Day 1 backend vertical slice into a learner-facing tutoring flow. Day 2 should deliver one complete path from Auth0 browser login through session creation, submission, asynchronous evaluation, feedback, and one evidence-grounded remediation or transfer action.

Day 1 remains the platform baseline: durable acceptance, worker processing, reviewed content selection, canonical evaluations, provider boundaries, and the Docker sandbox are frozen behind their documented interfaces.

## Day 2 scope

### In scope

- A minimal frontend shell for Arabic and English learners.
- Auth0 Authorization Code with PKCE for the browser client.
- API client handling access tokens, `202` submission responses, polling, retries, and ownership-safe errors.
- A learner session screen with prompt, answer editor, submit state, evaluation result, evidence, and diagnostic status.
- Retrieval over the reviewed content package, with item and evidence references preserved in the evaluation flow.
- One remediation path for a supported misconception.
- One transfer challenge generated from package transfer metadata.
- Basic telemetry, structured operational logs, and user-safe error states.
- End-to-end browser/API/worker verification using deterministic evaluation; provider and OIDC live checks stay opt-in in CI.

### Out of scope

- A complete curriculum authoring CMS.
- Full semantic RAG, arbitrary web retrieval, or unreviewed learner-facing content.
- Final mastery scoring, long-term recommendations, social features, payments, or licensing decisions.
- Production deployment, custom domains, and organization-level administration.
- Replacing the Day 1 database queue with Hatchet or another external queue.

## Implementation tasks

### 1. Freeze contracts and integration boundaries

- Record the frontend/API contract for session creation, submission acceptance, result polling, evaluation failure, and authentication errors.
- Add stable error codes and correlation IDs without exposing tokens, provider payloads, or internal exception details.
- Pin the selected content package version for the Day 2 flow and reject draft packages at startup and request time.
- Confirm the learner identity remains the verified `(issuer, subject)` pair; no client-provided user ID may affect ownership.

Acceptance: contract tests cover successful flow, pending evaluation, failed job without evaluation, `401`, `403`, `404`, idempotent replay, and changed-payload `409`.

### 2. Build the frontend vertical slice

- Add the reserved React/TypeScript frontend with a small, accessible layout.
- Implement routes for login, session, submission, evaluation, and remediation/transfer.
- Support Arabic and English copy with locale-independent API payloads and an explicit language switch.
- Make loading, retry, empty, infrastructure-failure, and signed-out states visible and recoverable.
- Keep API models generated or centrally typed from the backend contract to prevent drift.

Acceptance: a learner can navigate the complete local deterministic flow without opening developer tools, and the interface works at mobile and desktop widths.

### 3. Complete real Auth0 browser login

- Create an Auth0 Single Page Application using Authorization Code with PKCE.
- Configure exact local callback, logout, and allowed-origin URLs for the chosen frontend port.
- Request the Day 1 API audience and validate that the browser receives an API access token, not an ID token used as an API credential.
- Store tokens using the selected browser security strategy and document the tradeoff; do not place secrets in the repository.
- Add an opt-in live browser smoke test that creates a session and calls the authenticated API.

Acceptance: login, logout, refresh/reload, expired-token recovery, and API authorization work against the Auth0 tenant; CI clearly skips the test when credentials are absent.

### 4. Add reviewed-content retrieval

- Define a retrieval port that returns package ID, version, item ID, evidence IDs, misconception criteria, rubric, and transfer metadata.
- Implement deterministic lookup for the current Python-functions package before adding embeddings.
- Add item-level retrieval tests for both locales and verify evidence IDs are preserved into evaluation requests and responses.
- Add a later-compatible adapter boundary for semantic retrieval without making it a Day 2 dependency.

Acceptance: every learner-facing explanation and diagnosis references reviewed package evidence, and missing evidence produces a supported/uncertain diagnosis rather than an invented claim.

### 5. Implement remediation and transfer

- Map a supported misconception to a short bilingual remediation explanation and a targeted practice item.
- Keep remediation separate from the original evaluation so re-submission remains idempotent and auditable.
- Select one transfer challenge from reviewed transfer metadata, with a distinct item ID and an explicit relation to the original concept.
- Persist the remediation/transfer attempt and its evaluation using the existing ownership and job interfaces.

Acceptance: a supported misconception produces one evidence-grounded remediation; unsupported evidence remains `uncertain`; a transfer challenge can be completed and evaluated without overwriting the original submission.

### 6. Strengthen operations and security

- Add structured request/job logs with correlation IDs, durations, result status, and retry counts.
- Add metrics or counters for accepted, replayed, conflicted, succeeded, failed, retried, and stale-recovered jobs.
- Set production-safe CORS, trusted origins, request-size limits, and rate-limit seams without weakening local development.
- Review dependency and container pinning, secret handling, Auth0 audience/issuer validation, and Docker sandbox cleanup.
- Add a short runbook for starting the API and worker, checking readiness, recovering stale jobs, and rotating credentials.

Acceptance: logs and health checks diagnose a stuck worker or unavailable provider without revealing bearer tokens or learner secrets.

### 7. Verification and delivery

- Run locked dependency sync, Ruff check, Ruff format check, the full backend suite, frontend lint/typecheck/test, migration upgrade, import check, and local startup checks.
- Run the API-to-database-to-worker-to-sandbox-to-evaluation end-to-end test with Docker enabled.
- Keep live Auth0 and provider tests explicitly marked opt-in and report skipped status when credentials are unavailable.
- Update architecture, API contracts, handoff, and local setup documentation as the frontend flow lands.
- Review the final diff for accidental secrets, generated environments, unrelated files, and migration compatibility before committing.

Acceptance: all required local checks pass, the deterministic end-to-end flow is repeatable from a clean checkout, and the commit contains only Day 2 work and its documentation.

## Suggested execution order

1. Freeze contracts and choose the frontend port, callback URLs, and browser token strategy.
2. Add the frontend shell and typed API client.
3. Configure and verify Auth0 SPA PKCE.
4. Connect the session/submission/evaluation vertical slice.
5. Add deterministic retrieval, remediation, and transfer.
6. Add telemetry, security hardening, and the runbook.
7. Run the full verification matrix and perform a release review.

## Decisions required before implementation

- Frontend framework and dev server port: React/Vite is the smallest fit for the reserved frontend boundary; confirm the port before creating Auth0 callback URLs.
- Browser token strategy: in-memory tokens with refresh-token rotation, or another explicitly accepted approach after security review.
- Initial learner experience: one fixed Python-functions lesson for the vertical slice, or a package/item selector.
- Day 2 deployment target: local-only verification or a shared preview environment.
- Ownership per task: assign frontend, content/retrieval, and operations responsibilities before parallel implementation.

## Definition of done

Day 2 is complete when a real or deterministic learner can sign in, open a reviewed lesson, submit an answer, see an independently evaluated result with evidence, receive supported remediation or an honest uncertain state, complete one transfer challenge, and recover safely from pending or failed infrastructure work. The flow must preserve Day 1 ownership, idempotency, persistence, retry, and security invariants.
