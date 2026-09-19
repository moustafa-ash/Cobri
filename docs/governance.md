# Repository governance and data handling

## Main and release controls

Configure the private GitHub repository's `main` ruleset before relying on remote merges:

- Require one approval from someone other than the author; dismiss stale approvals after new commits.
- Require the `backend-checks`, `frontend-checks`, `browser-check`, and `secret-scan` CI jobs.
- Require branches to be up to date and prohibit force-pushes and branch deletion.
- Restrict release tags to the gated release workflow after all required checks and independent approval.
- Keep preview/protected-environment approval separate from repository review.

These settings are a required operator action, not asserted as configured by this repository. Do not tag or release from a local checkout.

## Threat model

Assets are learner identity (`issuer`, `subject`), answers/reasoning, progress/history, provider credentials, signing keys, reviewed content, and sandbox host resources. Trust boundaries are the browser/API, verified identity provider, database/worker, model provider, content repository, and isolated code runner.

Threats include forged identity or cross-learner access, token/content leakage in logs, provider prompt retention, fabricated evidence or unsupported diagnoses, malicious submitted code escaping isolation, compromised operator credentials, and accidental destructive exports/deletes. Controls: verified issuer-subject ownership, owner-scoped queries, bounded request schemas, no credentials in logs, evidence allow-lists, sandbox disabled unless isolated Docker is explicitly configured, exact-target operator confirmation, and append-only learner events. Remaining risks include provider retention and host/container escape; production provider terms, runtime isolation, least privilege, and independent security review must be approved before deployment.

## Learner data policy

Collect only data needed to provide tutoring and audit progress. Do not log prompts, answers, reasoning, bearer tokens, or provider responses. The policy selected for this MVP is retention until explicit deletion. Export and deletion are operator-mediated, require an identity allow-listed in `COBRI_APPROVED_OPERATOR_IDS` and exact `(issuer, subject)` target confirmation, and must be handled through the repository commands; record the operation in the protected `COBRI_OPERATOR_AUDIT_FILE` without copying learner content into general logs. Protect these local settings and the audit file with operator-only access. No automated retention window is claimed.

Content/evaluation manifests must remain unavailable to learners until `moustafa-ash` review records bind the exact digests. Repository authors must not self-approve educational content. The current control-flow review is recorded in the release ledger; no external deployment or release was performed.

## Educational review standard

The content author and reviewer must be different people; `moustafa-ash` is the designated independent reviewer for this package and dataset. For every item, approve only after checking source accuracy and evidence relevance, English/Arabic meaning and instructional equivalence, rubric observability, misconception support, runnable package-owned tests, and a genuinely changed-context transfer. Reject unsupported claims, ambiguous expected outcomes, broken prerequisites, or untranslated/mistranslated learning intent. For each evaluation case, verify the exact item/version, language, answer/reasoning/category, expected canonical verdict, evidence references, and adversarial handling against that reviewed item. Any correction changes the digest and requires a new review record. Review each case and content item individually; aggregate approval requires all bound entries to be reviewed.
