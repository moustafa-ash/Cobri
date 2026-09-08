from Cobri.backend.src.cobri.model_gateway.model.model_contracts import OutcomeVerdict, ReasoningVerdict, DiagnosticStatus
from Cobri.backend.src.cobri.model_gateway.validators.BaseValidator import BaseReasoningEvaluator

class LLMReasoningEvaluator(BaseReasoningEvaluator):
    def __init__(self, model_gateway_client):
        self.gateway = model_gateway_client

    async def evaluate_reasoning(
        self, 
        explanation: str, 
        outcome: OutcomeVerdict
    ) -> tuple[ReasoningVerdict, DiagnosticStatus, str | None]:
        if not explanation or len(explanation.strip()) < 5:
            return ReasoningVerdict.INSUFFICIENT, DiagnosticStatus.SUPPORTED, None

        # Here you call the model gateway with pinned prompt templates
        # Example output payload parsing:
        return ReasoningVerdict.SOUND, DiagnosticStatus.SUPPORTED, None