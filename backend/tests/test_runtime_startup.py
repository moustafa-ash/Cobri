"""Runtime composition smoke checks for the local SQLite application."""

from fastapi.testclient import TestClient

from cobri.config import Settings
from cobri.main import create_app


def test_uvicorn_entrypoint_exports_runtime_app() -> None:
    from cobri.main import app

    assert app.state.database is not None
    assert app.state.session_store is not None
    assert app.state.submission_service is not None
    assert app.state.content_catalog is not None


def test_runtime_app_starts_and_reports_worker_readiness(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}",
        content_root=tmp_path / "content-packages",
        auth_issuer=None,
        auth_audience=None,
        auth_jwks_url=None,
    )
    (settings.content_root / "placeholder").mkdir(parents=True)
    app = create_app(settings, install_runtime_adapters=True)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        readiness = client.get("/health/ready")
        assert readiness.status_code == 503
        assert "authentication" in readiness.json()["missing"]
        assert "worker" in readiness.json()["missing"]
