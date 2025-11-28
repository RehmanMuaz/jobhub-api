import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.core.services.scrape_service import ScrapeService
from app.schemas.scrape import (
    ScrapeJobCreate,
    ScrapeJobDetail,
    ScrapeJobResponse,
    ScrapeJobResult,
    ScrapeJobStatus,
)


class _FakeScrapeService(ScrapeService):
    def __init__(self):
        pass

    def enqueue_job(self, payload: ScrapeJobCreate) -> ScrapeJobResponse:
        return ScrapeJobResponse(job_id="test-job-1", status=ScrapeJobStatus.queued)

    def get_job(self, job_id: str) -> ScrapeJobDetail:
        return ScrapeJobDetail(job_id=job_id, status=ScrapeJobStatus.completed)

    def get_job_result(self, job_id: str) -> ScrapeJobResult:
        return ScrapeJobResult(job_posting=None, snapshot=None, raw_html_preview=None, warnings=[])


@pytest.mark.anyio
async def test_scrape_enqueues_and_fetches_status(monkeypatch):
    app = create_app()

    from app.core import deps as deps_module

    app.dependency_overrides[deps_module.get_scrape_service] = lambda: _FakeScrapeService()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/scrape/jobs",
            json={"url": "https://example.com/job/1", "source": "other"},
        )
        assert resp.status_code == 202
        job = resp.json()
        assert job["job_id"] == "test-job-1"

        status_resp = await ac.get(f"/api/v1/scrape/jobs/{job['job_id']}")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] in {"completed", "in_progress", "queued"}

        result_resp = await ac.get(f"/api/v1/scrape/jobs/{job['job_id']}/result")
        assert result_resp.status_code == 200
