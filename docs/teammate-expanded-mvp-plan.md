# Cobri Expanded MVP: Teammate Handoff Plan

## Starting point

- Repository: `D:\CoBri`
- Branch: `main`
- Baseline: `f17ad0f Add conversational Monaco workspace`
- Stage One result: substantive verification complete.
- Docker Desktop 4.90.0 and Engine 29.7.2 are installed and running on the `desktop-linux` context.
- Pinned sandbox image verified: `python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254`.

## Stage One evidence

- `hello-world` and the pinned Python image ran successfully.
- Real sandbox success, learner-test failure, timeout cleanup, forged-marker rejection, bounded output, non-root, no-network, read-only, and temporary-filesystem probes passed.
- Real API → database → worker Docker flow passed: 3 tests.
- Focused sandbox tests passed: 6 tests.
- Historical Stage One backend suite: 135 passed, 1 skipped. Current offline suite is recorded in `docs/verification-report.md`.
- Ruff check and format check passed.
- No Cobri sandbox containers remain.
- The existing shell did not inherit the user-local Docker PATH entry; use a new shell or the installed CLI path. Elevated Docker access was required by this environment.
- Two generated pytest directories remain ACL-protected and untracked: `.test-tmp-e2e2` and `.test-tmp-full`. Do not delete unrelated processes; remove these artifacts only when Windows permissions allow it.

## Stage One changes

- `backend/src/cobri/sandbox/docker_runner.py` rejects untrusted `COBRI_RESULT:` markers even when a trusted marker is also present.
- The generated harness bounds learner stdout and stderr to 8 KiB before host capture.
- `backend/tests/test_sandbox.py` adds forged-marker and bounded-output regression tests.
- `docs/stage1-docker-verification.md` records commands, versions, results, and the environment caveat.

## Remaining implementation order

1. **Model providers:** verify Groq and OpenRouter independently; test fallback, exhaustion, malformed responses, fabricated/contradictory evidence, and operational-error classification.
2. **PostgreSQL 16:** run disposable Docker PostgreSQL migrations and test atomic acceptance, idempotency, competing workers, leases, retries, recovery, and SQLite parity.
3. **CI:** add SHA-pinned GitHub Actions for locked backend/frontend installation, Ruff, formatting, tests, migrations, typecheck, and build. Keep secret-dependent jobs opt-in.
4. **Learner state:** add append-only learner events, versioned concept progress, legal state transitions, strict `correct + sound` progression, transfer-gated mastery, history/progress APIs, and operator deletion.
5. **Content lifecycle:** add Git-reviewed release metadata for draft/reviewed/published/superseded/rollback states, digest immutability, reviewer separation, and validation/publish/supersede/rollback tooling.
6. **Reviewed content:** author Python control-flow lessons for booleans/conditionals and loops with bilingual evidence, rubrics, misconceptions, remediation, practice, transfer, and package tests. Keep draft until Moustafa explicitly reviews it.
7. **Retrieval:** add local pinned multilingual-E5 embeddings, versioned JSON vectors, exact cosine retrieval, provenance/index metadata, and Tavily official-domain search restricted to `docs.python.org`. Quarantine fetched material until human review.
8. **Evaluation dataset:** create 120 bilingual reviewed cases, run deterministic/Groq-only/OpenRouter-only reports without fallback hiding attribution, and enforce the approved safety-first thresholds.
9. **End-to-end verification:** run Auth0, provider, Docker, semantic retrieval, web quarantine, history, mastery, Arabic/English, mobile/desktop, keyboard, refresh, expiry, duplicate, and worker-recovery checks.
10. **Handoff/release:** update README, architecture, runbooks, Day 2 handoff, and checklist; inspect secrets/diff; create focused commits; push normally to private `origin/main`.

## Locked decisions and boundaries

- Mastery is evidence-gated and requires a successful changed-context transfer; model output alone cannot award it.
- Retain immutable history until operator-mediated learner deletion.
- Use Git review with separate author/reviewer attribution; no runtime CMS.
- Add Python control flow only for the next content expansion.
- Use local E5 + database JSON vectors; do not add pgvector or a vector service yet.
- Use Tavily’s approved free tier with paid overage disabled; search only `docs.python.org`.
- Fetched web content is curator-only until reviewed and published.
- Both Groq and OpenRouter independently meet quality thresholds; operational latency/failure/fallback metrics are reported separately.
- Do not select a project license, deploy, change repository visibility, force-push, or terminate existing user processes.

## Required reporting

After each stage, report what changed, exact commands and results, pass/fail/skip counts, live versus mocked evidence, blockers or approvals needed, and the next stage. Mark checklist items `[x]` only when implementation and verification evidence exists.
