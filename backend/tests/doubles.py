"""Canned HTTP test dependencies: no database, durable queue, or evaluation logic."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from Cobri.backend.src.cobri.assessments.contracts import JobView, SubmissionCreate, SubmissionView
from Cobri.backend.src.cobri.content.ports import ItemReference, PackageReference
from cobri.errors import ResourceNotFound
from Cobri.backend.src.cobri.identity.auth import Principal
from Cobri.backend.src.cobri.tutoring.contracts import SessionCreate, SessionView

OWNER = Principal(issuer="https://issuer.example", subject="learner-1")
SESSION_ID = UUID("00000000-0000-0000-0000-000000000001")
SUBMISSION_ID = UUID("00000000-0000-0000-0000-000000000002")
JOB_ID = UUID("00000000-0000-0000-0000-000000000003")
UNKNOWN_ID = UUID("00000000-0000-0000-0000-000000000099")
CREATED_AT = datetime(2026, 9, 7, 12, tzinfo=UTC)
SESSION_BODY = {
    "content_package_id": "test-only-programming",
    "content_version": "0.0.0-test",
    "ui_locale": "ar",
    "instructional_language": "en",
}
SUBMISSION_BODY = {"item_id": "test-item-1", "answer": "الإجابة: ٤"}


def canned_session() -> SessionView:
    return SessionView(**SESSION_BODY, session_id=SESSION_ID, created_at=CREATED_AT)


def canned_submission() -> SubmissionView:
    return SubmissionView(
        **SUBMISSION_BODY,
        submission_id=SUBMISSION_ID,
        session_id=SESSION_ID,
        content_package_id=SESSION_BODY["content_package_id"],
        content_version=SESSION_BODY["content_version"],
        created_at=CREATED_AT,
        job=JobView(job_id=JOB_ID, status="pending"),
    )


class CannedSessionStore:
    """One preselected record; calls are observed, never durably persisted."""

    def __init__(self) -> None:
        self.result: Any = canned_session()
        self.error: Exception | None = None
        self.create_calls: list[tuple[Principal, SessionCreate]] = []
        self.get_calls: list[tuple[Principal, UUID]] = []

    async def create_session(self, principal: Principal, request: SessionCreate) -> Any:
        self.create_calls.append((principal, request))
        if self.error:
            raise self.error
        return self.result

    async def get_session(self, principal: Principal, session_id: UUID) -> Any:
        self.get_calls.append((principal, session_id))
        if self.error:
            raise self.error
        if principal != OWNER or session_id != SESSION_ID:
            raise ResourceNotFound
        return self.result


class CannedSubmissionService:
    """Return scripted responses; this does not implement idempotency or enqueueing."""

    def __init__(self) -> None:
        self.result: Any = canned_submission()
        self.error: Exception | None = None
        self.accept_calls: list[tuple[Principal, UUID, SubmissionCreate, str]] = []
        self.get_calls: list[tuple[Principal, UUID]] = []

    async def accept_submission(
        self,
        principal: Principal,
        session_id: UUID,
        request: SubmissionCreate,
        idempotency_key: str,
    ) -> Any:
        self.accept_calls.append((principal, session_id, request, idempotency_key))
        if self.error:
            raise self.error
        return self.result

    async def get_submission(self, principal: Principal, submission_id: UUID) -> Any:
        self.get_calls.append((principal, submission_id))
        if self.error:
            raise self.error
        if principal != OWNER or submission_id != SUBMISSION_ID:
            raise ResourceNotFound
        return self.result


class CannedContentCatalog:
    """A test reference only; no draft/reviewed package is loaded or published."""

    def __init__(self) -> None:
        self.package: Any = PackageReference(
            content_package_id=SESSION_BODY["content_package_id"],
            content_version=SESSION_BODY["content_version"],
        )
        self.item: Any = ItemReference(**self.package.model_dump(), item_id="test-item-1")
        self.error: Exception | None = None
        self.package_calls: list[tuple[str, str]] = []
        self.item_calls: list[tuple[str, str, str]] = []

    async def require_package(self, content_package_id: str, content_version: str) -> Any:
        self.package_calls.append((content_package_id, content_version))
        if self.error:
            raise self.error
        return self.package

    async def require_item(
        self, content_package_id: str, content_version: str, item_id: str
    ) -> Any:
        self.item_calls.append((content_package_id, content_version, item_id))
        if self.error:
            raise self.error
        return self.item
