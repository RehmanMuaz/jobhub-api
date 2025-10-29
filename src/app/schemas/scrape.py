from __future__ import annotations
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from uuid import uuid4
from .common import ID, Source, TimestampedModel

class ScrapeRequest(BaseModel):
    url: HttpUrl
    source: Optional[Source] = None
    priority: int = 0

class ScrapeJobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"

class ScrapeJob(TimestampedModel):
    id: ID = Field(default_factory=uuid4)
    url: HttpUrl
    source: Source = "other"
    status: str = ScrapeJobStatus.QUEUED
    error: str | None = None
    # link to normalized posting if parsed successfully
    posting_id: ID | None = None