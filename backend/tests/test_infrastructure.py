import pytest
from httpx import ASGITransport, AsyncClient

from cobri.config import Settings
from cobri.main import create_app


@pytest.mark.anyio
async def test_live_health_endpoint():
    app = create_app(Settings())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


@pytest.mark.anyio
async def test_ready_health_endpoint_unconfigured():
    app = create_app(Settings())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/ready")
        assert response.status_code in (200, 503)
        body = response.json()
        assert "status" in body
        assert "missing" in body