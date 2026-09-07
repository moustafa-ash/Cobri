# Evaluation fixture handoff

Reserved for Ahmed's versioned, labeled evaluation examples. No labeled fixture set or fake evaluator is supplied in Moustafa's implementation.

API tests use canned responses from `backend/tests/doubles.py` solely to verify the HTTP boundary. Those responses are not an evaluator, reviewed teaching material, a benchmark, or evidence of model quality.

Ahmed's fixture set should reference a content package ID, version, and item ID; preserve Arabic/English answer and reasoning text; and distinguish expected outcome and reasoning verdicts. Include insufficient-evidence cases labeled `uncertain`, absent reasoning, and cases where the outcome and reasoning disagree. A wrong answer alone must not establish a misconception. Infrastructure failures should be tested separately from learner verdicts.

Ahmed will review the provisional HTTP models before canonical shared schemas and a reproducible fake evaluator are connected.
