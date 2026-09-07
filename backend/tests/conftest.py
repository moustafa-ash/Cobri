"""Explicit API dependency overrides; authentication here is a named test double."""

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cobri.config import Settings
from cobri.dependencies import get_content_catalog, get_session_store, get_submission_service
from cobri.identity.auth import get_current_principal
from cobri.main import create_app

from .doubles import OWNER, CannedContentCatalog, CannedSessionStore, CannedSubmissionService


@pytest.fixture
def api_settings() -> Settings:
    # Explicit values isolate HTTP tests from developer environment configuration.
    # No autouse environment cleanup: the opt-in live-auth test needs its own env.
    return Settings(
        _env_file=None,
        app_name="Cobri test",
        auth_issuer=None,
        auth_audience=None,
        auth_jwks_url=None,
        auth_algorithms=["RS256"],
        auth_jwks_timeout_seconds=5,
        auth_jwks_cache_seconds=300,
        auth_clock_skew_seconds=0,
    )


@dataclass
class ApiHarness:
    app: FastAPI
    client: TestClient
    sessions: CannedSessionStore
    submissions: CannedSubmissionService
    catalog: CannedContentCatalog


@pytest.fixture
def api(api_settings: Settings) -> Iterator[ApiHarness]:
    app = create_app(api_settings)
    sessions = CannedSessionStore()
    submissions = CannedSubmissionService()
    catalog = CannedContentCatalog()
    app.dependency_overrides[get_current_principal] = lambda: OWNER
    app.dependency_overrides[get_session_store] = lambda: sessions
    app.dependency_overrides[get_submission_service] = lambda: submissions
    app.dependency_overrides[get_content_catalog] = lambda: catalog
    with TestClient(app) as client:
        yield ApiHarness(app, client, sessions, submissions, catalog)
    app.dependency_overrides.clear()
