# Verification report

## Current revision

The isolated `codex/integration-repair` branch passes the locked offline backend
gate: Ruff, formatting, and 156 tests passed (four live markers remain skipped
in the default offline run). Frontend tests (6), lint, typecheck, build, and
the parameterized offline browser check pass for English/Arabic desktop/mobile
fixtures. The build emits only the known Monaco chunk-size warning.

## Evidence boundaries

SQLite and mocked provider checks are deterministic or mocked evidence. The
opt-in live suite now passes Auth0, Groq-only, OpenRouter-only, PostgreSQL
lease/concurrency, and Docker sandbox checks using local disposable services.
These are local smoke tests, not shared staging evidence.

The content lifecycle validator now checks control-flow evidence, rubrics,
misconceptions, follow-ups, and stable IDs. Deterministic vector ranking,
metadata-aware persistence, a fail-closed semantic hook, and HTTPS-only Tavily
quarantine helpers are implemented. The pinned E5 model is locally cached and
a bounded Tavily request was verified against `docs.python.org`; no active
production semantic index or learner-facing web incorporation is claimed.

Independent provider smoke checks pass with fixed Groq and OpenRouter model
identities. The 120-case fixture remains an unreviewed synthetic fixture, so no
provider quality, human review, Recall@3, or safety gate is claimed.

The 120-case fixture is structurally validated and generated with distinct,
item-specific bilingual inputs. It remains unreviewed synthetic evidence; no
provider quality, human review, retrieval Recall@3, or safety gate is claimed.

No commit, push, publication, or deployment was made. Human content approval,
active semantic-index generation, provider-quality scoring, live authenticated
browser journeys, and release-audit documentation remain open.
