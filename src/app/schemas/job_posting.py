from __future__ import annotations
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from uuid import uuid4
from datetime import datetime
from .common import ID, Source, TimestampedModel

class RawSnapshot(TimestampedModel):
    id: ID = Field(default_factory=uuid4)
    posting_id: ID | None = None
    fetched_at: datetime | None = None
    mime_type: str = "text/html"
    bytes_location: str | None = None  # e.g., s3://bucket/key or file path
    status_code: int | None = None
    headers: dict[str, str] | None = None
    raw_html_preview: str | None = None

class JobPosting(TimestampedModel):
    id: ID = Field(default_factory=uuid4)
    external_id: str | None = None  # job id on source site
    title: str
    company: str
    location: str | None = None
    description_md: str
    requirements: List[str] = Field(default_factory=list)
    posted_at: datetime | None = None
    url: HttpUrl
    source: Source
    salary: str | None = None
    salary_predicted: str | None = None
    score: float | None = None
    status: str = " New" # e.g., "New", "Applied" "Interview", "Rejected", "Offer"


class StoredJobPosting(JobPosting):
    latest_snapshot: RawSnapshot | None = None
