from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import Source
from app.schemas.job_posting import JobPosting, RawSnapshot


class ScrapeJobStatus(str, Enum):
    queued = "queued"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    deferred = "deferred"
    canceled = "canceled"
    unknown = "unknown"


class ScrapeJobCreate(BaseModel):
    url: HttpUrl
    source: Source = "other"
    callback_url: HttpUrl | None = None
    metadata: dict[str, Any] | None = None


class ScrapeJobResponse(BaseModel):
    job_id: str
    status: ScrapeJobStatus


class ScrapeJobResult(BaseModel):
    job_posting: JobPosting | None = None
    snapshot: RawSnapshot | None = None
    raw_html_preview: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class ScrapeJobDetail(BaseModel):
    job_id: str
    status: ScrapeJobStatus
    enqueued_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    result: ScrapeJobResult | None = None
    error: str | None = None
