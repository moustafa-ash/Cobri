"""Submission acceptance/polling. The API neither queues nor evaluates work."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response

from Cobri.backend.src.cobri.assessments.contracts import SubmissionCreate, SubmissionService, SubmissionView
from Cobri.backend.src.cobri.content.ports import ContentCatalog, ItemReference
from Cobri.backend.src.cobri.core.dependencies import get_content_catalog, get_session_store, get_submission_service
from Cobri.backend.src.cobri.core.errors import IntegrationContractError, validate_result
from Cobri.backend.src.cobri.identity.auth import Principal, get_current_principal
from Cobri.backend.src.cobri.tutoring.contracts import SessionStore, SessionView

router = APIRouter(tags=["submissions"])


@router.post("/sessions/{session_id}/submissions", response_model=SubmissionView, status_code=202)
async def accept_submission(
    session_id: UUID,
    body: SubmissionCreate,
    response: Response,
    principal: Annotated[Principal, Depends(get_current_principal)],
    store: Annotated[SessionStore, Depends(get_session_store)],
    service: Annotated[SubmissionService, Depends(get_submission_service)],
    catalog: Annotated[ContentCatalog, Depends(get_content_catalog)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[!-~]+$")
    ],
) -> SubmissionView:
    # Check ownership before resolving content. B also rechecks inside acceptance.
    session = validate_result(SessionView, await store.get_session(principal, session_id))
    if session.session_id != session_id:
        raise IntegrationContractError
    item = validate_result(
        ItemReference,
        await catalog.require_item(
            session.content_package_id, session.content_version, body.item_id
        ),
    )
    expected_item = (session.content_package_id, session.content_version, body.item_id)
    if (item.content_package_id, item.content_version, item.item_id) != expected_item:
        raise IntegrationContractError
    submission = validate_result(
        SubmissionView,
        await service.accept_submission(principal, session_id, body, idempotency_key),
    )
    if (
        submission.session_id != session_id
        or (submission.content_package_id, submission.content_version, submission.item_id)
        != expected_item
        or submission.answer != body.answer
        or submission.reasoning != body.reasoning
    ):
        raise IntegrationContractError
    response.headers["Location"] = f"/api/v1/submissions/{submission.submission_id}"
    return submission


@router.get("/submissions/{submission_id}", response_model=SubmissionView)
async def get_submission(
    submission_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    service: Annotated[SubmissionService, Depends(get_submission_service)],
) -> SubmissionView:
    submission = validate_result(
        SubmissionView, await service.get_submission(principal, submission_id)
    )
    if submission.submission_id != submission_id:
        raise IntegrationContractError
    return submission
