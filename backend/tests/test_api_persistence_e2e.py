"""API-to-database-to-worker end-to-end coverage without external credentials."""

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from cobri.config import Settings
from cobri.identity.auth import Principal, get_current_principal
from cobri.main import create_app
from cobri.worker import EvaluationWorker


def test_api_submission_reaches_worker_and_evaluation(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'e2e.db'}",
        content_root=Path(__file__).parents[2] / "content-packages",
        auth_issuer=None,
        auth_audience=None,
        auth_jwks_url=None,
    )
    app = create_app(settings, install_runtime_adapters=True)
    principal = Principal(issuer="https://issuer.example", subject="e2e-learner")
    app.dependency_overrides[get_current_principal] = lambda: principal
    with TestClient(app) as client:
        session_response = client.post(
            "/api/v1/sessions",
            json={
                "content_package_id": "python-functions",
                "content_version": "1.0.0",
                "ui_locale": "en",
                "instructional_language": "en",
            },
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["session_id"]
        submission_response = client.post(
            f"/api/v1/sessions/{session_id}/submissions",
            headers={"Idempotency-Key": "e2e-1"},
            json={
                "item_id": "python-function-return-1",
                "answer": "def double(n):\n    return n * 2",
                "reasoning": "It returns the calculated value.",
            },
        )
        assert submission_response.status_code == 202
        submission_id = submission_response.json()["submission_id"]
        worker = EvaluationWorker(
            settings,
            app.state.submission_service,
            app.state.content_catalog,
        )
        assert asyncio.run(worker.run_once())
        result = client.get(f"/api/v1/submissions/{submission_id}")
        assert result.status_code == 200
        assert result.json()["job"]["status"] == "succeeded"
        assert result.json()["evaluation"]["outcome_verdict"] == "correct"
        assert client.get("/api/v1/progress").status_code == 200
        history = client.get(f"/api/v1/sessions/{session_id}/history")
        assert history.status_code == 200
        assert {event["event_type"] for event in history.json()} >= {
            "submission_accepted",
            "evaluation_succeeded",
        }
    app.dependency_overrides.clear()
