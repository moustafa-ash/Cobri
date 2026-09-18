# Verification report

## Scope and evidence boundary

This report covers `codex/integration-repair` at the current working tree. It
does not claim production readiness or educational quality. Evidence is marked
deterministic, mocked, live, historical, failed, skipped, or blocked.

## Completed evidence

- Content lifecycle validation: deterministic and passed. `python-control-flow`
  `1.0.0` is reviewed and published with digest
  `04d25e84dae44e1e688993fdec1a26a1676b5d527da72b53e4687816c0f10ffa`.
  The package bytes were unchanged; only review metadata was added. Review
  record: `docs/reviews/python-control-flow-1.0.0.md`.
- Semantic index: deterministic build passed using the pinned local
  `intfloat/multilingual-e5-small` revision
  `614241f622f53c4eeff9890bdc4f31cfecc418b3`; index and SQLite vectors contain
  package, digest, model, tokenizer, dimension, and normalization metadata.
  Runtime retrieval fails closed for stale, corrupt, mixed, or unavailable
  index/model state and exposes aggregate counters only.
- Tavily quarantine: live bounded run passed with one search, two
  `docs.python.org` results, and two atomically persisted quarantine records.
  Quarantined material is not connected to learner responses.
- Backend offline gate: deterministic, passed — `157 passed, 4 skipped`.
- Frontend tests, lint, typecheck, and build: deterministic, passed. The build
  has the known Monaco chunk-size warning.
- Parameterized browser evidence: mocked/offline, passed for English and
  Arabic desktop/mobile fixtures, including accessibility and responsive
  checks. It is not live Auth0 or deployed-environment evidence.
- Deterministic evaluation fixture: passed for 120 cases (60 English, 60
  Arabic; 24 per category; 40 `python-functions`, 80 `python-control-flow`).
  It validates allocation/schema only and makes no quality claim.

## Failed, skipped, and blocked evidence

- Groq evaluation: live and failed. 23/120 cases completed and 97 failed at the
  provider boundary; adversarial safety and quality thresholds therefore do not
  pass. Provider usage was not exposed, so the $1 ceiling could not be measured
  from telemetry.
- OpenRouter evaluation: live attempt was interrupted after provider
  non-response; the required 120-case denominator is unavailable. This is
  blocked, not a passing result, and no fallback was used.
- Auth0: live configuration probe skipped because the token/configuration was
  not available to the test process. PostgreSQL: live test failed against the
  configured disposable database because its pre-existing job state made the
  attempts assertion non-deterministic. The Docker unit suite passed but is
  mocked/host-independent, not proof of a real sandbox container run.
  Authenticated live browser journeys were not completed.
- OCI ARM64 preview, TLS, remote CI, tag, release, and deployment: blocked.
  No OCI credentials/capacity or deployable composition was verified, so no
  paid fallback or unsupported deployment claim was made.

## Checklist and release status

The mechanically recalculated checklist contains **82 checked** and **55
unchecked** items. The unchecked items include live provider quality, deployed
environment recovery, security/privacy review, OCI preview, and release gates.
The repository has not been tagged or released, and no deployment has occurred.

## Preservation statement

`D:\CoBri` was not modified. Existing ignored secrets, cached models, browser
artifacts, and temporary directories were preserved.
