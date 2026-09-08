"""Session HTTP boundary coverage using canned dependencies, never a real store."""

import pytest

from cobri.dependencies import get_content_catalog, get_session_store
from cobri.errors import DependencyUnavailable, ResourceNotFound
from Cobri.backend.src.cobri.identity.auth import Principal, get_current_principal

from .conftest import ApiHarness
from .doubles import OWNER, SESSION_BODY, SESSION_ID, UNKNOWN_ID, canned_session


def test_create_and_get_session_pass_verified_identity_and_preferences(api: ApiHarness) -> None:
    response = api.client.post("/api/v1/sessions", json=SESSION_BODY)
    assert response.status_code == 201
    assert response.headers["location"] == f"/api/v1/sessions/{SESSION_ID}"
    assert response.json()["ui_locale"] == "ar"
    assert response.json()["instructional_language"] == "en"
    assert response.json()["created_at"] == "2026-09-07T12:00:00Z"
    assert api.sessions.create_calls[0][0] == OWNER
    assert api.sessions.create_calls[0][1].model_dump() == SESSION_BODY
    assert api.catalog.package_calls == [("test-only-programming", "0.0.0-test")]
    loaded = api.client.get(response.headers["location"])
    assert loaded.status_code == 200
    assert loaded.json() == response.json()
    assert api.sessions.get_calls == [(OWNER, SESSION_ID)]


@pytest.mark.parametrize(
    "ui_locale,instructional_language", [("en", "ar"), ("ar", "ar"), ("en", "en")]
)
def test_locale_preferences_are_independent(
    api: ApiHarness, ui_locale: str, instructional_language: str
) -> None:
    body = {
        **SESSION_BODY,
        "ui_locale": ui_locale,
        "instructional_language": instructional_language,
    }
    api.sessions.result = {**canned_session().model_dump(), **body}
    response = api.client.post("/api/v1/sessions", json=body)
    assert response.status_code == 201
    assert response.json()["ui_locale"] == ui_locale
    assert response.json()["instructional_language"] == instructional_language


@pytest.mark.parametrize(
    "change",
    [
        {"ui_locale": "fr"},
        {"instructional_language": "fr"},
        {"content_package_id": " "},
        {"content_version": ""},
        {"owner_id": "someone-else"},
        {"subject": "someone-else"},
    ],
)
def test_invalid_session_body_is_rejected(api: ApiHarness, change: dict) -> None:
    response = api.client.post("/api/v1/sessions", json={**SESSION_BODY, **change})
    assert response.status_code == 422
    assert api.sessions.create_calls == []
    assert api.catalog.package_calls == []


@pytest.mark.parametrize("field", ["ui_locale", "instructional_language"])
def test_both_language_preferences_are_required(api: ApiHarness, field: str) -> None:
    body = {key: value for key, value in SESSION_BODY.items() if key != field}
    assert api.client.post("/api/v1/sessions", json=body).status_code == 422


@pytest.mark.parametrize(
    "principal",
    [
        Principal(issuer=OWNER.issuer, subject="another-learner"),
        Principal(issuer="https://another-issuer.example", subject=OWNER.subject),
    ],
)
def test_session_ownership_is_scoped_by_issuer_and_subject(
    api: ApiHarness, principal: Principal
) -> None:
    api.app.dependency_overrides[get_current_principal] = lambda: principal
    forbidden = api.client.get(f"/api/v1/sessions/{SESSION_ID}")
    missing = api.client.get(f"/api/v1/sessions/{UNKNOWN_ID}")
    assert forbidden.status_code == missing.status_code == 404
    assert forbidden.json() == missing.json()
    assert api.sessions.get_calls[0] == (principal, SESSION_ID)


def test_invalid_session_uuid(api: ApiHarness) -> None:
    assert api.client.get("/api/v1/sessions/not-a-uuid").status_code == 422
    assert api.sessions.get_calls == []


@pytest.mark.parametrize("dependency", [get_session_store, get_content_catalog])
def test_missing_runtime_adapter_is_unavailable(api: ApiHarness, dependency) -> None:
    del api.app.dependency_overrides[dependency]
    response = api.client.post("/api/v1/sessions", json=SESSION_BODY)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "dependency_unavailable"


def test_unknown_package_does_not_create_session(api: ApiHarness) -> None:
    api.catalog.error = ResourceNotFound()
    assert api.client.post("/api/v1/sessions", json=SESSION_BODY).status_code == 404
    assert api.sessions.create_calls == []


def test_store_failure_does_not_return_created(api: ApiHarness) -> None:
    api.sessions.error = DependencyUnavailable()
    response = api.client.post("/api/v1/sessions", json=SESSION_BODY)
    assert response.status_code == 503
    assert "location" not in response.headers


@pytest.mark.parametrize(
    "result",
    [
        {},
        {**canned_session().model_dump(), "created_at": "2026-09-07T12:00:00"},
        {**canned_session().model_dump(), "ui_locale": "en"},
    ],
)
def test_invalid_session_adapter_result_is_integration_error(api: ApiHarness, result) -> None:
    api.sessions.result = result
    response = api.client.post("/api/v1/sessions", json=SESSION_BODY)
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "invalid_dependency_response"


def test_catalog_cannot_substitute_package_version(api: ApiHarness) -> None:
    api.catalog.package = {**api.catalog.package.model_dump(), "content_version": "other"}
    response = api.client.post("/api/v1/sessions", json=SESSION_BODY)
    assert response.status_code == 500
    assert api.sessions.create_calls == []


def test_get_rejects_adapter_returning_wrong_session(api: ApiHarness) -> None:
    api.sessions.result = {**canned_session().model_dump(), "session_id": UNKNOWN_ID}
    assert api.client.get(f"/api/v1/sessions/{SESSION_ID}").status_code == 500
