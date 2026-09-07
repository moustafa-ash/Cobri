"""Stateless API entry point. No worker or infrastructure adapters are installed."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from cobri.assessments.contracts import SubmissionService
from cobri.assessments.router import router as submissions_router
from cobri.config import Settings
from cobri.content.ports import ContentCatalog
from cobri.errors import register_error_handlers
from cobri.identity.auth import TokenVerifier
from cobri.identity.router import router as identity_router
from cobri.tutoring.contracts import SessionStore
from cobri.tutoring.router import router as sessions_router


def create_app(
    settings: Settings | None = None,
    *,
    session_store: SessionStore | None = None,
    submission_service: SubmissionService | None = None,
    content_catalog: ContentCatalog | None = None,
) -> FastAPI:
    settings = settings if settings is not None else Settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.state.settings = settings
    app.state.token_verifier = TokenVerifier(settings)
    app.state.session_store = session_store
    app.state.submission_service = submission_service
    app.state.content_catalog = content_catalog
    register_error_handlers(app)
    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(submissions_router, prefix="/api/v1")

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"])
    async def ready() -> JSONResponse:
        # Day 1 checks configuration/wiring only, not provider/DB/worker health.
        missing = [
            name
            for name, configured in (
                ("authentication", settings.auth_configured),
                ("session_store", app.state.session_store is not None),
                ("submission_service", app.state.submission_service is not None),
                ("content_catalog", app.state.content_catalog is not None),
            )
            if not configured
        ]
        return JSONResponse(
            status_code=503 if missing else 200,
            content={
                "status": "unavailable" if missing else "configured",
                "check": "configuration_only",
                "missing": missing,
            },
        )

    return app


app = create_app()
