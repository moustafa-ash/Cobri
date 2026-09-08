from Cobri.backend.src.cobri.model_gateway.model.model_contracts import Evaluation, OutcomeVerdict, ReasoningVerdict, DiagnosticStatus
from Cobri.backend.src.cobri.model_gateway.validators.BaseValidator import BaseOutcomeEvaluator, BaseReasoningEvaluator

class EvaluationCompositeService:
    def __init__(
        self, 
        outcome_evaluator: BaseOutcomeEvaluator, 
        reasoning_evaluator: BaseReasoningEvaluator
    ):
        self.outcome_evaluator = outcome_evaluator
        self.reasoning_evaluator = reasoning_evaluator

    async def evaluate_submission(self, code: str, explanation: str) -> Evaluation:
        # 1. Evaluate Code Execution / Outcome
        outcome = await self.outcome_evaluator.evaluate_outcome(code)

        # 2. Evaluate Reasoning independently
        reasoning, diagnostic_status, misconception_id = (
            await self.reasoning_evaluator.evaluate_reasoning(explanation, outcome)
        )

        # 3. Apply Domain Invariant: Failed code execution overrides reasoning
        if outcome == OutcomeVerdict.INCORRECT and reasoning == ReasoningVerdict.SOUND:
            reasoning = ReasoningVerdict.INCORRECT

        return Evaluation(
            outcome_verdict=outcome,
            reasoning_verdict=reasoning,
            diagnostic_status=diagnostic_status,
            evidence_references=[],
            misconception_id=misconception_id
        )