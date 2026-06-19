import httpx
import pytest
from httpx import ASGITransport

import src.main
from src.main import app


@pytest.mark.asyncio
async def test_chat_returns_reply(monkeypatch):
    async def fake_run_agent(message: str) -> str:
        assert message == "내일 서울 날씨 어때?"
        return "내일 서울은 12°C에 비가 와요. 우산 챙기세요! ☂️"

    monkeypatch.setattr(src.main, "run_agent", fake_run_agent)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "내일 서울 날씨 어때?"})

    assert resp.status_code == 200
    assert resp.json() == {"reply": "내일 서울은 12°C에 비가 와요. 우산 챙기세요! ☂️"}


@pytest.mark.asyncio
async def test_chat_validation_error_on_missing_message():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_still_ok():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_cors_headers_present(monkeypatch):
    async def fake_run_agent(message: str) -> str:
        return "ok"

    monkeypatch.setattr(src.main, "run_agent", fake_run_agent)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            json={"message": "테스트"},
            headers={"Origin": "http://localhost:5500"},
        )

    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5500"
