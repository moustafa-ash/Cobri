"""Day 2 catalogue and guided progression integration coverage."""

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from cobri.config import Settings
from cobri.identity.auth import Principal, get_current_principal
from cobri.main import create_app
from cobri.worker import EvaluationWorker


def test_catalogue_hides_evaluator_only_material(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'catalogue.db'}",
        content_root=Path(__file__).parents[2] / "content-packages",
        auth_issuer=None,
        auth_audience=None,
        auth_jwks_url=None,
    )
    app = create_app(settings, install_runtime_adapters=True)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        issuer="https://issuer.example", subject="catalogue-learner"
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/content/packages")
        assert response.status_code == 200
        package = next(item for item in response.json() if item["content_version"] == "2.0.0")
        assert len(package["lessons"]) == 3
        detail = client.get(
            "/api/v1/content/packages/python-functions/2.0.0/lessons/function-return-value"
        )
        assert detail.status_code == 200
        assert detail.json()["evidence"]
        assert detail.json()["rubric"]
        assert "expected_code" not in detail.text
        assert "tests" not in detail.text

        supported = client.post(
            "/api/v1/content/topics/discover", json={"query": "Python functions"}
        )
        assert supported.status_code == 200
        assert supported.json()["status"] == "supported"
        assert supported.json()["content_version"] == "2.0.0"
        assert len(supported.json()["options"]) == 3
        assert "expected_code" not in supported.text

        specific = client.post(
            "/api/v1/content/topics/discover", json={"query": "function call composition"}
        )
        assert specific.status_code == 200
        assert [option["item_id"] for option in specific.json()["options"]] == [
            "compose-function-calls"
        ]

        arabic = client.post(
            "/api/v1/content/topics/discover", json={"query": "القيم المعادة من الدوال"}
        )
        assert arabic.status_code == 200
        assert [option["item_id"] for option in arabic.json()["options"]] == [
            "function-return-value"
        ]

        unsupported = client.post("/api/v1/content/topics/discover", json={"query": "Python loops"})
        assert unsupported.status_code == 200
        assert unsupported.json() == {
            "status": "unsupported",
            "options": [],
            "content_package_id": None,
            "content_version": None,
        }


def test_supported_remediation_practice_and_transfer_flow(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'flow.db'}",
        content_root=Path(__file__).parents[2] / "content-packages",
        auth_issuer=None,
        auth_audience=None,
        auth_jwks_url=None,
    )
    app = create_app(settings, install_runtime_adapters=True)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        issuer="https://issuer.example", subject="flow-learner"
    )
    with TestClient(app) as client:
        session = client.post(
            "/api/v1/sessions",
            json={
                "content_package_id": "python-functions",
                "content_version": "2.0.0",
                "ui_locale": "en",
                "instructional_language": "ar",
            },
        ).json()
        assessment = client.post(
            f"/api/v1/sessions/{session['session_id']}/submissions",
            headers={"Idempotency-Key": "assessment"},
            json={
                "item_id": "function-return-value",
                "answer": "def double(n):\n    print(n * 2)",
                "reasoning": "Printing and returning are the same result.",
            },
        )
        assert assessment.status_code == 202
        assessment_id = assessment.json()["submission_id"]
        worker = EvaluationWorker(settings, app.state.submission_service, app.state.content_catalog)
        assert asyncio.run(worker.run_once("flow-worker"))
        remediation = client.get(f"/api/v1/submissions/{assessment_id}/next").json()
        assert remediation["action"] == "remediation"
        assert remediation["next_item"]["item_id"] == "practice-return-square"

        practice = client.post(
            f"/api/v1/sessions/{session['session_id']}/submissions",
            headers={"Idempotency-Key": "practice"},
            json={
                "item_id": "practice-return-square",
                "answer": "def square(n):\n    return n * n",
                "reasoning": "The caller receives the product through return.",
                "purpose": "practice",
                "parent_submission_id": assessment_id,
            },
        )
        assert practice.status_code == 202
        practice_id = practice.json()["submission_id"]
        assert asyncio.run(worker.run_once("flow-worker"))
        transfer_step = client.get(f"/api/v1/submissions/{practice_id}/next").json()
        assert transfer_step["action"] == "transfer"

        transfer = client.post(
            f"/api/v1/sessions/{session['session_id']}/submissions",
            headers={"Idempotency-Key": "transfer"},
            json={
                "item_id": "transfer-rectangle-area",
                "answer": "def rectangle_area(width, height):\n    return width * height",
                "reasoning": "The function returns the product for the caller to use.",
                "purpose": "transfer",
                "parent_submission_id": practice_id,
            },
        )
        assert transfer.status_code == 202
        transfer_id = transfer.json()["submission_id"]
        assert asyncio.run(worker.run_once("flow-worker"))
        complete = client.get(f"/api/v1/submissions/{transfer_id}/next").json()
        assert complete["action"] == "complete"

        invalid = client.post(
            f"/api/v1/sessions/{session['session_id']}/submissions",
            headers={"Idempotency-Key": "invalid-transfer"},
            json={
                "item_id": "transfer-rectangle-area",
                "answer": "answer",
                "reasoning": "reason",
                "purpose": "transfer",
                "parent_submission_id": assessment_id,
            },
        )
        assert invalid.status_code == 409
        assert invalid.json()["detail"]["code"] == "invalid_progression"
