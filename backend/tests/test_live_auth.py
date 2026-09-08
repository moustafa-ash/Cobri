"""Opt-in live identity-provider smoke test; skipped during reproducible offline tests."""

import os

import pytest
from fastapi.testclient import TestClient

from cobri.config import Settings
from Cobri.backend.src.cobri.main import create_app


@pytest.mark.live_auth
def test_live_identity_provider():
    if os.getenv("COBRI_RUN_LIVE_AUTH") != "1":
        pytest.skip("Live authentication pending: set COBRI_RUN_LIVE_AUTH=1 to opt in")
    access_token = os.getenv("COBRI_LIVE_ACCESS_TOKEN")
    settings = Settings()
    if not settings.auth_configured or not access_token:
        pytest.skip("Live authentication pending: configure OIDC and COBRI_LIVE_ACCESS_TOKEN")
    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
    # Avoid including tokens, provider diagnostics, or the identity in failure output.
    if response.status_code != 200:
        pytest.fail(f"Live identity-provider verification returned HTTP {response.status_code}")
    assert set(response.json()) == {"issuer", "subject"}
