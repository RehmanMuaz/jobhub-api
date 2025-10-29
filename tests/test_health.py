import pytest
from httpx import AsyncClient
from fastapi import status
from app.main import create_app


@pytest.mark.anyio
async def test_health():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/health")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {"status": "ok"}