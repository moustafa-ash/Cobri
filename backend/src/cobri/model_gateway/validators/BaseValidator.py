from abc import ABC, abstractmethod
from Cobri.backend.src.cobri.model_gateway.model.model_contracts import OutcomeVerdict, ReasoningVerdict, DiagnosticStatus

class BaseOutcomeEvaluator(ABC):
    @abstractmethod
    async def evaluate_outcome(self, code: str) -> OutcomeVerdict:
        """Evaluates whether the submitted code runs and passes test cases."""
        pass

class BaseReasoningEvaluator(ABC):
    @abstractmethod
    async def evaluate_reasoning(
        self, 
        explanation: str, 
        outcome: OutcomeVerdict
    ) -> tuple[ReasoningVerdict, DiagnosticStatus, str | None]:
        """Evaluates explanation against rubrics; returns (reasoning, diagnostic, misconception_id)."""
        pass