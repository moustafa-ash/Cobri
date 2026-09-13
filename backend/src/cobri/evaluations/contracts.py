"""Canonical evaluation types shared by the API, worker, and model gateway."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OutcomeVerdict(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNVERIFIED = "unverified"


class ReasoningVerdict(StrEnum):
    SOUND = "sound"
    PARTIAL = "partial"
    INCORRECT = "incorrect"
    INSUFFICIENT = "insufficient"


class DiagnosticStatus(StrEnum):
    SUPPORTED = "supported"
    UNCERTAIN = "uncertain"


class Evaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_verdict: OutcomeVerdict
    reasoning_verdict: ReasoningVerdict
    diagnostic_status: DiagnosticStatus
    evidence_references: list[str] = Field(default_factory=list, max_length=32)
    misconception_id: str | None = Field(default=None, max_length=128)


class EvaluationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: str = Field(min_length=1, max_length=10_000)
    reasoning: str | None = Field(default=None, max_length=10_000)
    item_id: str = Field(min_length=1, max_length=128)
    content_package_id: str = Field(min_length=1, max_length=128)
    content_version: str = Field(min_length=1, max_length=128)
    sandbox_passed: bool | None = None
