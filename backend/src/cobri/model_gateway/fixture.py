"""Deterministic offline evaluator used when external providers are absent."""

from cobri.content.catalog import ContentItem
from cobri.evaluations.contracts import (
    DiagnosticStatus,
    Evaluation,
    EvaluationInput,
    OutcomeVerdict,
    ReasoningVerdict,
)


class FixtureEvaluator:
    def evaluate(self, input_data: EvaluationInput, item: ContentItem) -> Evaluation:
        submitted = " ".join(input_data.answer.strip().split())
        expected = " ".join(item.expected_code.strip().split())
        outcome = OutcomeVerdict.CORRECT if submitted == expected else OutcomeVerdict.INCORRECT
        if not input_data.reasoning or len(input_data.reasoning.strip()) < 5:
            reasoning = ReasoningVerdict.INSUFFICIENT
            status = DiagnosticStatus.UNCERTAIN
            misconception_id = None
        elif "print" in input_data.answer.lower() and "return" not in input_data.answer.lower():
            reasoning = ReasoningVerdict.INCORRECT
            status = DiagnosticStatus.SUPPORTED
            misconception_id = "print-instead-of-return"
        elif outcome is OutcomeVerdict.CORRECT:
            reasoning = ReasoningVerdict.SOUND
            status = DiagnosticStatus.SUPPORTED
            misconception_id = None
        else:
            reasoning = ReasoningVerdict.PARTIAL
            status = DiagnosticStatus.UNCERTAIN
            misconception_id = None
        return Evaluation(
            outcome_verdict=outcome,
            reasoning_verdict=reasoning,
            diagnostic_status=status,
            evidence_references=item.evidence_references,
            misconception_id=misconception_id,
        )
