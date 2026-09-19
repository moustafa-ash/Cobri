# Evaluation fixture handoff

This file contains two unreviewed seed cases. They are schema-valid examples for the canonical `Evaluation` contract, not a benchmark or evidence of model quality.

API tests use canned responses from `backend/tests/doubles.py` solely to verify the HTTP boundary. Those responses are not an evaluator, reviewed teaching material, a benchmark, or evidence of model quality.

Ahmed's fixture set should reference a content package ID, version, and item ID; preserve Arabic/English answer and reasoning text; and distinguish expected outcome and reasoning verdicts. Include insufficient-evidence cases labeled `uncertain`, absent reasoning, and cases where the outcome and reasoning disagree. A wrong answer alone must not establish a misconception. Infrastructure failures should be tested separately from learner verdicts.

The versioned `v1/evaluation.json` artifact contains 60 English and 60 Arabic
cases across six balanced categories. Its manifest remains digest-bound and pending
human sign-off; deterministic validation is a harness check, not provider
quality evidence. Infrastructure failures must be reported separately from
learner verdicts.
