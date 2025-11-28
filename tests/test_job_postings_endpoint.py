import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


class _Scalars:
    def __init__(self, data):
        self._data = data

    def all(self):
        return self._data


class _FakeSession:
    def scalars(self, stmt):  # noqa: ARG002 - stmt unused in fake
        return _Scalars([])


def _get_fake_db():
    yield _FakeSession()


@pytest.mark.anyio
async def test_list_job_postings_empty(monkeypatch):
    app = create_app()
    from app.core import deps as deps_module

    app.dependency_overrides[deps_module.get_db] = _get_fake_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/job-postings")
        assert resp.status_code == 200
        assert resp.json() == []
