"""Provisional HTTP contracts for Ahmed's review, not canonical shared schemas."""

from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from cobri.content.ports import PackageReference
from cobri.identity.auth import Principal


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
    event_type: str
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
    status: str
    version: int
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


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
