"""Provisional HTTP contracts for Ahmed's review, not canonical shared schemas."""

from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import AwareDatetime, field_validator

from Cobri.backend.app.content.ports import PackageReference
from Cobri.backend.app.identity.auth import Principal


class SessionCreate(PackageReference):
    ui_locale: Literal["ar", "en"]
    instructional_language: Literal["ar", "en"]


class SessionView(SessionCreate):
    session_id: UUID
    created_at: AwareDatetime

    @field_validator("created_at")
    @classmethod
    def as_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class SessionStore(Protocol):
    """Mohamed supplies persistence; all lookups are scoped to the principal.

    Missing resources and resources owned by another principal must both raise
    ResourceNotFound. create_session returns only after persistence succeeds.
    """

    async def create_session(self, principal: Principal, request: SessionCreate) -> SessionView: ...

    async def get_session(self, principal: Principal, session_id: UUID) -> SessionView: ...
