"""FastAPI entry point with replaceable adapters and local runtime composition."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from cobri.assessments.contracts import SubmissionService
from cobri.assessments.router import router as submissions_router
from cobri.config import Settings
from cobri.content.catalog import FileContentCatalog
from cobri.content.ports import ContentCatalog
from cobri.content.router import router as content_router
from cobri.errors import register_error_handlers
from cobri.identity.auth import TokenVerifier, get_current_principal
from cobri.identity.router import router as identity_router
from cobri.observability import OperationalMetrics
from cobri.persistence.database import Database
from cobri.persistence.models import WorkerHeartbeatRecord
from cobri.persistence.repositories import DatabaseStore
from cobri.rate_limit import InMemoryRateLimiter, RateLimiter
from cobri.tutoring.contracts import SessionStore
from cobri.tutoring.router import router as sessions_router

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    session_store: SessionStore | None = None,
    submission_service: SubmissionService | None = None,
    content_catalog: ContentCatalog | None = None,
    rate_limiter: RateLimiter | None = None,
    install_runtime_adapters: bool = False,
) -> FastAPI:
    settings = settings if settings is not None else Settings()
    database = None
    if install_runtime_adapters:
        database = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if database is not None and settings.auto_create_schema:
            await database.create_schema()
        try:
            yield
        finally:
            if database is not None:
                await database.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID"],
        expose_headers=["Location", "X-Correlation-ID"],
    )
    app.state.settings = settings
    app.state.token_verifier = TokenVerifier(settings)
    app.state.metrics = OperationalMetrics()
    app.state.rate_limiter = rate_limiter or InMemoryRateLimiter(settings.rate_limit_per_minute)
    if install_runtime_adapters:
        assert database is not None
        store = DatabaseStore(database)
        session_store = session_store or store
        submission_service = submission_service or store
        content_catalog = content_catalog or FileContentCatalog(settings.content_root)
    app.state.database = database
    app.state.session_store = session_store
    app.state.submission_service = submission_service
    app.state.content_catalog = content_catalog
    register_error_handlers(app)

    @app.middleware("http")
    async def request_guard(request: Request, call_next):
        started = perf_counter()
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        request.state.correlation_id = correlation_id[:128]
        content_length = request.headers.get("content-length")
        if (
            content_length
            and content_length.isdigit()
            and int(content_length) > settings.max_request_bytes
        ):
            response = JSONResponse(
                status_code=413,
                content={
                    "detail": {
                        "code": "request_too_large",
                        "message": "The request body is too large.",
                    }
                },
            )
        else:
            response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        app.state.metrics.increment(f"http_{response.status_code}")
        logger.info(
            "request_complete method=%s path=%s status=%s duration_ms=%.1f correlation_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started) * 1000,
            request.state.correlation_id,
        )
        return response

    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(content_router, prefix="/api/v1")
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(submissions_router, prefix="/api/v1")

    @app.get(
        "/api/v1/operations/metrics",
        tags=["operations"],
        dependencies=[Depends(get_current_principal)],
    )
    async def metrics() -> dict[str, int]:
        return app.state.metrics.snapshot()

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"])
    async def ready() -> JSONResponse:
        # Runtime readiness includes the database and worker heartbeat when wired.
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
        if database is not None:
            try:
                async with database.session() as session:
                    await session.execute(select(WorkerHeartbeatRecord).limit(1))
            except Exception:
                missing.append("database")
            else:
                heartbeat = await _latest_heartbeat(database)
                heartbeat_at = heartbeat.updated_at if heartbeat else None
                if heartbeat_at is None:
                    missing.append("worker")
                elif heartbeat_at.tzinfo is None:
                    heartbeat_at = heartbeat_at.replace(tzinfo=UTC)
                if heartbeat_at is not None and datetime.now(UTC) - heartbeat_at > timedelta(
                    seconds=settings.worker_lease_seconds * 2
                ):
                    missing.append("worker")
        return JSONResponse(
            status_code=503 if missing else 200,
            content={
                "status": "unavailable" if missing else "configured",
                "check": "runtime",
                "missing": missing,
            },
        )

    return app


async def _latest_heartbeat(database: Database):
    async with database.session() as session:
        return await session.scalar(
            select(WorkerHeartbeatRecord).order_by(WorkerHeartbeatRecord.updated_at.desc())
        )


app = create_app(install_runtime_adapters=True)
