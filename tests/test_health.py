import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import status
from app.main import create_app


@pytest.mark.anyio
async def test_health():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/health")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"status": "ok"}
