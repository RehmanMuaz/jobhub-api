from app.schemas import ScrapeJobCreate, JobPosting


def test_scrape_job_create_model():
    sr = ScrapeJobCreate(url="https://example.com/jobs/123", source="other")
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
