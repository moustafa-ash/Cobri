"""Submission HTTP coverage using scripted dependencies, never a durable queue."""

import pytest

from Cobri.backend.src.cobri.assessments.contracts import EvaluationView, JobView
from cobri.dependencies import get_content_catalog, get_session_store, get_submission_service
from cobri.errors import DependencyUnavailable, IdempotencyConflict, ResourceNotFound
from Cobri.backend.src.cobri.identity.auth import Principal, get_current_principal

from .conftest import ApiHarness
from .doubles import (
    JOB_ID,
    OWNER,
    SESSION_ID,
    SUBMISSION_BODY,
    SUBMISSION_ID,
    UNKNOWN_ID,
    canned_submission,
)

SUBMISSION_URL = f"/api/v1/sessions/{SESSION_ID}/submissions"


def test_accept_and_poll_preserve_arabic_and_verified_identity(api: ApiHarness) -> None:
    response = api.client.post(
        SUBMISSION_URL,
        json=SUBMISSION_BODY,
        headers={"Idempotency-Key": "attempt-1"},
    )
    assert response.status_code == 202
    assert response.headers["location"] == f"/api/v1/submissions/{SUBMISSION_ID}"
    assert response.json()["answer"] == "الإجابة: ٤"
    assert response.json()["reasoning"] is None
    assert response.json()["job"] == {"job_id": str(JOB_ID), "status": "pending"}
    assert response.json()["evaluation"] is None
    principal, session_id, request, key = api.submissions.accept_calls[0]
    assert (principal, session_id, key) == (OWNER, SESSION_ID, "attempt-1")
    assert request.model_dump() == {**SUBMISSION_BODY, "reasoning": None}
    assert api.sessions.get_calls == [(OWNER, SESSION_ID)]
    assert api.catalog.item_calls == [("test-only-programming", "0.0.0-test", "test-item-1")]

    polled = api.client.get(response.headers["location"])
    assert polled.status_code == 200
    assert polled.json() == response.json()
    assert api.submissions.get_calls == [(OWNER, SUBMISSION_ID)]


def test_omitted_and_explicit_null_reasoning_normalize_equally(api: ApiHarness) -> None:
    omitted = api.client.post(
        SUBMISSION_URL,
        json=SUBMISSION_BODY,
        headers={"Idempotency-Key": "same-key"},
    )
    explicit = api.client.post(
        SUBMISSION_URL,
        json={**SUBMISSION_BODY, "reasoning": None},
        headers={"Idempotency-Key": "same-key"},
    )
    assert omitted.status_code == explicit.status_code == 202
    assert omitted.json()["submission_id"] == explicit.json()["submission_id"]
    assert api.submissions.accept_calls[0][2] == api.submissions.accept_calls[1][2]


def test_separate_verdicts_support_uncertain(api: ApiHarness) -> None:
    api.submissions.result = canned_submission().model_copy(
        update={
            "job": JobView(job_id=JOB_ID, status="succeeded"),
            "evaluation": EvaluationView(outcome_verdict="correct", reasoning_verdict="uncertain"),
        }
    )
    response = api.client.get(f"/api/v1/submissions/{SUBMISSION_ID}")
    assert response.status_code == 200
    assert response.json()["evaluation"] == {
        "outcome_verdict": "correct",
        "reasoning_verdict": "uncertain",
    }


@pytest.mark.parametrize("status", ["pending", "running", "failed"])
def test_non_succeeded_jobs_have_no_learner_verdict(api: ApiHarness, status: str) -> None:
    api.submissions.result = {
        **canned_submission().model_dump(),
        "job": {"job_id": JOB_ID, "status": status},
        "evaluation": None,
    }
    response = api.client.get(f"/api/v1/submissions/{SUBMISSION_ID}")
    assert response.status_code == 200
    assert response.json()["job"]["status"] == status
    assert response.json()["evaluation"] is None


@pytest.mark.parametrize(
    "body",
    [
        {**SUBMISSION_BODY, "answer": " "},
        {**SUBMISSION_BODY, "item_id": ""},
        {**SUBMISSION_BODY, "verdict": "correct"},
        {**SUBMISSION_BODY, "owner_id": "someone-else"},
        {**SUBMISSION_BODY, "content_version": "override"},
        {**SUBMISSION_BODY, "answer": "x" * 10_001},
        {**SUBMISSION_BODY, "reasoning": "x" * 10_001},
    ],
)
def test_invalid_body_is_rejected_before_dependencies(api: ApiHarness, body: dict) -> None:
    response = api.client.post(SUBMISSION_URL, json=body, headers={"Idempotency-Key": "attempt-1"})
    assert response.status_code == 422
    assert api.sessions.get_calls == []
    assert api.catalog.item_calls == []
    assert api.submissions.accept_calls == []


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Idempotency-Key": ""},
        {"Idempotency-Key": "contains space"},
        {"Idempotency-Key": "x" * 129},
    ],
)
def test_idempotency_key_is_required_and_bounded(api: ApiHarness, headers: dict) -> None:
    response = api.client.post(SUBMISSION_URL, json=SUBMISSION_BODY, headers=headers)
    assert response.status_code == 422
    assert api.submissions.accept_calls == []


def test_idempotency_conflict_maps_to_409(api: ApiHarness) -> None:
    api.submissions.error = IdempotencyConflict()
    response = api.client.post(
        SUBMISSION_URL,
        json={**SUBMISSION_BODY, "answer": "different"},
        headers={"Idempotency-Key": "reused-key"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "idempotency_conflict"
    assert "location" not in response.headers


@pytest.mark.parametrize(
    "principal",
    [
        Principal(issuer=OWNER.issuer, subject="another-learner"),
        Principal(issuer="https://another-issuer.example", subject=OWNER.subject),
    ],
)
def test_cross_user_session_is_404_before_content_or_acceptance(
    api: ApiHarness, principal: Principal
) -> None:
    api.app.dependency_overrides[get_current_principal] = lambda: principal
    response = api.client.post(
        SUBMISSION_URL,
        json=SUBMISSION_BODY,
        headers={"Idempotency-Key": "attempt-1"},
    )
    assert response.status_code == 404
    assert api.catalog.item_calls == []
    assert api.submissions.accept_calls == []


def test_cross_user_and_missing_submission_are_indistinguishable(api: ApiHarness) -> None:
    api.app.dependency_overrides[get_current_principal] = lambda: Principal(
        issuer=OWNER.issuer, subject="another-learner"
    )
    forbidden = api.client.get(f"/api/v1/submissions/{SUBMISSION_ID}")
    api.app.dependency_overrides[get_current_principal] = lambda: OWNER
    missing = api.client.get(f"/api/v1/submissions/{UNKNOWN_ID}")
    assert forbidden.status_code == missing.status_code == 404
    assert forbidden.json() == missing.json()


@pytest.mark.parametrize(
    "dependency", [get_session_store, get_content_catalog, get_submission_service]
)
def test_missing_runtime_adapter_is_503(api: ApiHarness, dependency) -> None:
    del api.app.dependency_overrides[dependency]
    response = api.client.post(
        SUBMISSION_URL,
        json=SUBMISSION_BODY,
        headers={"Idempotency-Key": "attempt-1"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "dependency_unavailable"
    assert "location" not in response.headers


def test_acceptance_failure_never_returns_202_or_verdict(api: ApiHarness) -> None:
    api.submissions.error = DependencyUnavailable()
    response = api.client.post(
        SUBMISSION_URL,
        json=SUBMISSION_BODY,
        headers={"Idempotency-Key": "attempt-1"},
    )
    assert response.status_code == 503
    assert "location" not in response.headers
    assert "evaluation" not in response.json()


def test_unknown_item_does_not_call_acceptance(api: ApiHarness) -> None:
    api.catalog.error = ResourceNotFound()
    response = api.client.post(
        SUBMISSION_URL,
        json=SUBMISSION_BODY,
        headers={"Idempotency-Key": "attempt-1"},
    )
    assert response.status_code == 404
    assert api.submissions.accept_calls == []


@pytest.mark.parametrize(
    "result",
    [
        {},
        {**canned_submission().model_dump(), "created_at": "2026-09-07T12:00:00"},
        {
            **canned_submission().model_dump(),
            "job": {"job_id": JOB_ID, "status": "failed"},
            "evaluation": {
                "outcome_verdict": "incorrect",
                "reasoning_verdict": "uncertain",
            },
        },
        {
            **canned_submission().model_dump(),
            "job": {"job_id": JOB_ID, "status": "succeeded"},
            "evaluation": None,
        },
        {
            **canned_submission().model_dump(),
            "job": {"job_id": JOB_ID, "status": "succeeded"},
            "evaluation": {
                "outcome_verdict": "misconception_x",
                "reasoning_verdict": "incorrect",
            },
        },
    ],
)
def test_invalid_adapter_response_is_500_without_verdict(api: ApiHarness, result: dict) -> None:
    api.submissions.result = result
    response = api.client.get(f"/api/v1/submissions/{SUBMISSION_ID}")
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "invalid_dependency_response"
    assert "evaluation" not in response.json()


@pytest.mark.parametrize(
    "change",
    [
        {"session_id": UNKNOWN_ID},
        {"content_version": "other-version"},
        {"content_package_id": "other-package"},
        {"item_id": "other-item"},
        {"answer": "other answer"},
        {"reasoning": "unexpected reasoning"},
    ],
)
def test_acceptance_cannot_substitute_request_fields(api: ApiHarness, change: dict) -> None:
    api.submissions.result = {**canned_submission().model_dump(), **change}
    response = api.client.post(
        SUBMISSION_URL,
        json=SUBMISSION_BODY,
        headers={"Idempotency-Key": "attempt-1"},
    )
    assert response.status_code == 500
    assert "location" not in response.headers


def test_catalog_cannot_substitute_item_reference(api: ApiHarness) -> None:
    api.catalog.item = {**api.catalog.item.model_dump(), "item_id": "other-item"}
    response = api.client.post(
        SUBMISSION_URL,
        json=SUBMISSION_BODY,
        headers={"Idempotency-Key": "attempt-1"},
    )
    assert response.status_code == 500
    assert api.submissions.accept_calls == []


def test_poll_rejects_wrong_submission_and_invalid_uuid(api: ApiHarness) -> None:
    api.submissions.result = {
        **canned_submission().model_dump(),
        "submission_id": UNKNOWN_ID,
    }
    assert api.client.get(f"/api/v1/submissions/{SUBMISSION_ID}").status_code == 500
    assert api.client.get("/api/v1/submissions/not-a-uuid").status_code == 422
