from app.schemas import ScrapeRequest, JobPosting
from pydantic import HttpUrl


def test_scrape_request_model():
    sr = ScrapeRequest(url="https://example.com/jobs/123", source="other", priority=1)
    assert str(sr.url).startswith("https://")


def test_job_posting_model():
    jp = JobPosting(
        title="Backend Developer",
        company="JobHub",
        description_md="**Great role**",
        url="https://example.com/jobs/123",
        source="other",
    )
    assert jp.title == "Backend Developer"