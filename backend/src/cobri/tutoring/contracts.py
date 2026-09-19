"""Provisional HTTP contracts for Ahmed's review, not canonical shared schemas."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from cobri.content.ports import PackageReference
from cobri.identity.auth import Principal


class LearnerEventType(StrEnum):
    ASSESSMENT_SUBMITTED = "assessment_submitted"
    RETRY_SUBMITTED = "retry_submitted"
    INTERVENTION_STARTED = "intervention_started"
    TRANSFER_SUBMITTED = "transfer_submitted"
    EVALUATION_SUCCEEDED = "evaluation_succeeded"
    DIAGNOSIS_RECORDED = "diagnosis_recorded"
    MASTERY_AWARDED = "mastery_awarded"
    PROFILE_UPDATED = "profile_updated"


class LearnerProgressState(StrEnum):
    STARTED = "started"
    NEEDS_RETRY = "needs_retry"
    PRACTICING = "practicing"
    TRANSFER_READY = "transfer_ready"
    MASTERED = "mastered"


def next_progress_state(
    current: LearnerProgressState | None, requested: LearnerProgressState
) -> LearnerProgressState:
    allowed = {
        None: {
            LearnerProgressState.NEEDS_RETRY,
            LearnerProgressState.PRACTICING,
            LearnerProgressState.TRANSFER_READY,
        },
        LearnerProgressState.STARTED: {
            LearnerProgressState.NEEDS_RETRY,
            LearnerProgressState.PRACTICING,
            LearnerProgressState.TRANSFER_READY,
        },
        LearnerProgressState.NEEDS_RETRY: {
            LearnerProgressState.NEEDS_RETRY,
            LearnerProgressState.PRACTICING,
            LearnerProgressState.TRANSFER_READY,
        },
        LearnerProgressState.PRACTICING: {
            LearnerProgressState.NEEDS_RETRY,
            LearnerProgressState.PRACTICING,
            LearnerProgressState.TRANSFER_READY,
        },
        LearnerProgressState.TRANSFER_READY: {
            LearnerProgressState.TRANSFER_READY,
            LearnerProgressState.MASTERED,
        },
        LearnerProgressState.MASTERED: {LearnerProgressState.MASTERED},
    }
    if requested not in allowed[current]:
        raise ValueError(f"invalid learner progress transition: {current} -> {requested}")
    return requested


class SessionCreate(PackageReference):
    ui_locale: Literal["ar", "en"]
    instructional_language: Literal["ar", "en"]


class SessionView(SessionCreate):
    session_id: UUID
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("created_at must include timezone")
        return value.astimezone(UTC)


class LearnerEventView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_id: UUID
    session_id: UUID
    submission_id: UUID | None
    event_type: LearnerEventType
    payload: dict
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class LearnerProgressView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    content_package_id: str
    content_version: str
    item_id: str
    status: LearnerProgressState
    version: int
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ProfileRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    content_package_id: str
    content_version: str
    item_id: str
    reason: str


class LearnerProfileView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    progress: list[LearnerProgressView]
    recommendations: list[ProfileRecommendation]


class SessionStore(Protocol):
    """Mohamed supplies persistence; all lookups are scoped to the principal.

    Missing resources and resources owned by another principal must both raise
    ResourceNotFound. create_session returns only after persistence succeeds.
    """

    async def create_session(self, principal: Principal, request: SessionCreate) -> SessionView: ...

    async def get_session(self, principal: Principal, session_id: UUID) -> SessionView: ...

    async def list_events(
        self, principal: Principal, session_id: UUID
    ) -> list[LearnerEventView]: ...

    async def list_progress(self, principal: Principal) -> list[LearnerProgressView]: ...
