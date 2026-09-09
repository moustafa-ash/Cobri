"""Provisional API views only. Ahmed owns the canonical evaluation schemas."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Protocol, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from cobri.content.ports import Reference
from cobri.evaluations.contracts import (
    DiagnosticStatus,
    Evaluation,
    OutcomeVerdict,
    ReasoningVerdict,
)
from cobri.identity.auth import Principal


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    item_id: Reference
    answer: Annotated[str, Field(min_length=1, max_length=10_000, pattern=r"\S")]
    reasoning: Annotated[str | None, Field(max_length=10_000)] = None


class EvaluationView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    outcome_verdict: OutcomeVerdict
    reasoning_verdict: ReasoningVerdict
    diagnostic_status: DiagnosticStatus = DiagnosticStatus.SUPPORTED
    evidence_references: list[str] = Field(default_factory=list)
    misconception_id: str | None = None

    @classmethod
    def from_evaluation(cls, evaluation: Evaluation) -> "EvaluationView":
        return cls(**evaluation.model_dump())


class JobView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    job_id: UUID
    status: Literal["pending", "running", "succeeded", "failed"]


class SubmissionView(SubmissionCreate):
    submission_id: UUID
    session_id: UUID
    content_package_id: Reference
    content_version: Reference
    created_at: AwareDatetime
    job: JobView
    evaluation: EvaluationView | None = None

    @field_validator("created_at")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def separate_processing_from_verdicts(self) -> Self:
        if (self.job.status == "succeeded") != (self.evaluation is not None):
            raise ValueError("Only succeeded jobs must have an evaluation")
        return self


class SubmissionService(Protocol):
    """Mohamed supplies the single durable acceptance operation and scoped reads.

    accept_submission must atomically recheck session ownership, persist the
    immutable payload/content reference, and record the obligation to evaluate.
    It must enforce concurrent idempotency on (issuer, subject, session_id, key).
    Identical validated payloads replay original IDs; changed payloads raise
    IdempotencyConflict. Acknowledgement is permitted only after commit.
    No queue implementation is selected by this interface.
    """

    async def accept_submission(
        self,
        principal: Principal,
        session_id: UUID,
        request: SubmissionCreate,
        idempotency_key: str,
    ) -> SubmissionView: ...

    async def get_submission(self, principal: Principal, submission_id: UUID) -> SubmissionView: ...
