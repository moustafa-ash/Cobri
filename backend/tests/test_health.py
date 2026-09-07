"""Startup remains honest when teammates' runtime dependencies are unavailable."""

from fastapi.testclient import TestClient

from cobri.config import Settings
from cobri.main import create_app

from .doubles import SESSION_BODY


def test_unconfigured_app_is_live_but_not_ready(api_settings: Settings) -> None:
    app = create_app(api_settings)
    assert app.dependency_overrides == {}
    assert app.state.session_store is None
    assert app.state.submission_service is None
    assert app.state.content_catalog is None
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {
            "status": "unavailable",
            "check": "configuration_only",
            "missing": ["authentication", "session_store", "submission_service", "content_catalog"],
        }
        assert client.get("/docs").status_code == 200
        paths = client.get("/openapi.json").json()["paths"]
        expected = {
            "/health/live": "get",
            "/health/ready": "get",
            "/api/v1/auth/me": "get",
            "/api/v1/sessions": "post",
            "/api/v1/sessions/{session_id}": "get",
            "/api/v1/sessions/{session_id}/submissions": "post",
            "/api/v1/submissions/{submission_id}": "get",
        }
        assert set(paths) == set(expected)
        for path, method in expected.items():
            assert method in paths[path]


def test_unconfigured_app_never_bypasses_authentication(api_settings: Settings) -> None:
    with TestClient(create_app(api_settings)) as client:
        response = client.post("/api/v1/sessions", json=SESSION_BODY)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        response = client.post(
            "/api/v1/sessions", json=SESSION_BODY, headers={"Authorization": "Bearer test-only"}
        )
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "authentication_unavailable"
