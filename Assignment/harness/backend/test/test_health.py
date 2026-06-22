import httpx
import pytest
from httpx import ASGITransport

from src.main import app


@pytest.mark.asyncio
async def test_config_imports():
    from src.config import settings

    assert settings.model_name == "claude-haiku-4-5"


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
