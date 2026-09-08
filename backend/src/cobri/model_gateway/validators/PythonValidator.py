from Cobri.backend.src.cobri.model_gateway.model.model_contracts import OutcomeVerdict
from Cobri.backend.src.cobri.model_gateway.validators.BaseValidator import BaseOutcomeEvaluator

class PythonOutcomeEvaluator(BaseOutcomeEvaluator):
    async def evaluate_outcome(self, code: str) -> OutcomeVerdict:
    
        if not code or "error" in code.lower():
            return OutcomeVerdict.INCORRECT
        return OutcomeVerdict.CORRECT