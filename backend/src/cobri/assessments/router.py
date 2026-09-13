"""Submission acceptance/polling. The API neither queues nor evaluates work."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response

from cobri.assessments.contracts import (
    AttemptPurpose,
    NextItemView,
    NextStepView,
    SubmissionCreate,
    SubmissionService,
    SubmissionView,
)
from cobri.content.ports import ContentCatalog, ItemReference
from cobri.dependencies import (
    get_content_catalog,
    get_rate_limiter,
    get_session_store,
    get_submission_service,
)
from cobri.errors import IntegrationContractError, ProgressionConflict, validate_result
from cobri.identity.auth import Principal, get_current_principal
from cobri.rate_limit import RateLimiter
from cobri.tutoring.contracts import SessionStore, SessionView

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
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> SubmissionView:
    await limiter.check(principal, "accept_submission")
    # Check ownership before resolving content. B also rechecks inside acceptance.
    session = validate_result(SessionView, await store.get_session(principal, session_id))
    if session.session_id != session_id:
        raise IntegrationContractError
    if body.purpose is AttemptPurpose.ASSESSMENT:
        catalog.get_lesson(session.content_package_id, session.content_version, body.item_id)
    else:
        assert body.parent_submission_id is not None
        parent = validate_result(
            SubmissionView,
            await service.get_submission(principal, body.parent_submission_id),
        )
        _validate_progression(parent, session_id, body, catalog)
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
        or submission.purpose != body.purpose
        or submission.parent_submission_id != body.parent_submission_id
    ):
        raise IntegrationContractError
    response.headers["Location"] = f"/api/v1/submissions/{submission.submission_id}"
    return submission


def _validate_progression(
    parent: SubmissionView,
    session_id: UUID,
    body: SubmissionCreate,
    catalog: ContentCatalog,
) -> None:
    if (
        parent.session_id != session_id
        or parent.evaluation is None
        or parent.job.status != "succeeded"
    ):
        raise ProgressionConflict
    lesson = catalog.lesson_for_item(
        parent.content_package_id, parent.content_version, parent.item_id
    )
    if body.purpose == parent.purpose and body.item_id == parent.item_id:
        return
    if body.purpose is AttemptPurpose.PRACTICE:
        misconception = next(
            (
                item
                for item in lesson.misconceptions
                if item.misconception_id == parent.evaluation.misconception_id
            ),
            None,
        )
        if (
            parent.evaluation.diagnostic_status != "supported"
            or misconception is None
            or body.item_id != misconception.practice.item_id
        ):
            raise ProgressionConflict
    elif body.purpose is AttemptPurpose.TRANSFER:
        if (
            parent.evaluation.outcome_verdict != "correct"
            or parent.evaluation.reasoning_verdict != "sound"
            or lesson.transfer is None
            or body.item_id != lesson.transfer.item_id
        ):
            raise ProgressionConflict


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


@router.get("/submissions/{submission_id}/next", response_model=NextStepView)
async def get_next_step(
    submission_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    service: Annotated[SubmissionService, Depends(get_submission_service)],
    catalog: Annotated[ContentCatalog, Depends(get_content_catalog)],
) -> NextStepView:
    submission = validate_result(
        SubmissionView, await service.get_submission(principal, submission_id)
    )
    if submission.submission_id != submission_id:
        raise IntegrationContractError
    if submission.job.status in {"pending", "running"}:
        return NextStepView(
            action="pending",
            message={"en": "Evaluation is still in progress.", "ar": "ما زال التقييم قيد التنفيذ."},
        )
    if submission.job.status == "failed" or submission.evaluation is None:
        return NextStepView(
            action="failed",
            message={
                "en": "Evaluation is unavailable. Try again later.",
                "ar": "التقييم غير متاح. حاول مرة أخرى لاحقًا.",
            },
        )
    lesson = catalog.lesson_for_item(
        submission.content_package_id, submission.content_version, submission.item_id
    )
    evaluation = submission.evaluation
    if evaluation.outcome_verdict == "correct" and evaluation.reasoning_verdict == "sound":
        if submission.purpose is AttemptPurpose.TRANSFER:
            return NextStepView(
                action="complete",
                message={"en": "Transfer challenge complete.", "ar": "اكتمل تحدي الانتقال."},
            )
        assert lesson.transfer is not None
        return NextStepView(
            action="transfer",
            message={"en": "Apply the idea in a new context.", "ar": "طبّق الفكرة في سياق جديد."},
            next_item=NextItemView(
                item_id=lesson.transfer.item_id,
                purpose=AttemptPurpose.TRANSFER,
                prompt=lesson.transfer.prompt,
            ),
        )
    if evaluation.diagnostic_status == "supported" and evaluation.misconception_id:
        misconception = next(
            (
                item
                for item in lesson.misconceptions
                if item.misconception_id == evaluation.misconception_id
            ),
            None,
        )
        if misconception is not None:
            return NextStepView(
                action="remediation",
                message={
                    "en": "Review this explanation, then try a focused exercise.",
                    "ar": "راجع هذا الشرح، ثم جرّب تدريبًا مركّزًا.",
                },
                remediation=misconception.remediation,
                next_item=NextItemView(
                    item_id=misconception.practice.item_id,
                    purpose=AttemptPurpose.PRACTICE,
                    prompt=misconception.practice.prompt,
                ),
            )
    resolved = catalog.get_item(
        submission.content_package_id, submission.content_version, submission.item_id
    )
    return NextStepView(
        action="retry",
        message={
            "en": (
                "The evidence is not sufficient for a diagnosis. "
                "Explain your reasoning and try again."
            ),
            "ar": "الأدلة غير كافية للتشخيص. اشرح تفكيرك وحاول مرة أخرى.",
        },
        next_item=NextItemView(
            item_id=resolved.item_id,
            purpose=submission.purpose,
            prompt=resolved.prompt,
        ),
    )
