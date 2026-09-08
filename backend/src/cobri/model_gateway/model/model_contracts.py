# app/contracts/evaluations.py
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel

class OutcomeVerdict(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNVERIFIED = "unverified"

class ReasoningVerdict(str, Enum):
    SOUND = "sound"
    PARTIAL = "partial"
    INCORRECT = "incorrect"
    INSUFFICIENT = "insufficient"

class DiagnosticStatus(str, Enum):
    SUPPORTED = "supported"
    UNCERTAIN = "uncertain"

class Evaluation(BaseModel):
    outcome_verdict: OutcomeVerdict
    reasoning_verdict: ReasoningVerdict
    diagnostic_status: DiagnosticStatus
    evidence_references: List[str] = []
    misconception_id: Optional[str] = None