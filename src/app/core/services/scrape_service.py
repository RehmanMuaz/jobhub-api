from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from loguru import logger
from rq import Queue, Retry
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.core.config import settings
from app.schemas.scrape import (
    ScrapeJobCreate,
    ScrapeJobDetail,
    ScrapeJobResponse,
    ScrapeJobResult,
    ScrapeJobStatus,
)
from app.worker.tasks import run_scrape_job


class ScrapeJobNotFoundError(Exception):
    """Raised when a requested scrape job is not present in the queue backend."""


class ScrapeJobResultNotReadyError(Exception):
    """Raised when a scrape job result is requested before completion."""


_STATUS_MAP: dict[str, ScrapeJobStatus] = {
    "queued": ScrapeJobStatus.queued,
    "started": ScrapeJobStatus.in_progress,
    "finished": ScrapeJobStatus.completed,
    "failed": ScrapeJobStatus.failed,
    "deferred": ScrapeJobStatus.deferred,
    "canceled": ScrapeJobStatus.canceled,
    "stopped": ScrapeJobStatus.canceled,
    "scheduled": ScrapeJobStatus.queued,
}


class ScrapeService:
    """Coordinates job submission and status retrieval for scraping tasks."""

    def __init__(self, queue: Queue):
        self._queue = queue

    def enqueue_job(self, payload: ScrapeJobCreate) -> ScrapeJobResponse:
        job_id = str(uuid4())
        retry = self._build_retry()

        self._queue.enqueue(
            run_scrape_job,
            job_id=job_id,
            kwargs={"payload": payload.model_dump(mode="json")},
            retry=retry,
            result_ttl=settings.scraper_result_ttl_seconds,
            failure_ttl=settings.scraper_failure_ttl_seconds,
            description=f"Scrape job for {payload.url}",
        )

        logger.info("Enqueued job %s for url=%s source=%s", job_id, payload.url, payload.source)
        return ScrapeJobResponse(job_id=job_id, status=ScrapeJobStatus.queued)

    def get_job(self, job_id: str) -> ScrapeJobDetail:
        job = self._fetch_job(job_id)
        status = self._map_status(job.get_status())
        result = self._coerce_result(job.result) if job.is_finished and job.result else None
        error = self._extract_error(job)

        detail = ScrapeJobDetail(
            job_id=job_id,
            status=status,
            enqueued_at=job.enqueued_at,
            started_at=job.started_at,
            ended_at=job.ended_at,
            result=result,
            error=error,
        )
        logger.debug("Fetched job status for %s status=%s", job_id, status)
        return detail

    def get_job_result(self, job_id: str) -> ScrapeJobResult:
        detail = self.get_job(job_id)
        if detail.result is None or detail.status is not ScrapeJobStatus.completed:
            raise ScrapeJobResultNotReadyError(job_id)
        return detail.result

    def _fetch_job(self, job_id: str) -> Job:
        try:
            return Job.fetch(job_id, connection=self._queue.connection)
        except NoSuchJobError as exc:
            raise ScrapeJobNotFoundError(job_id) from exc

    def _map_status(self, raw_status: Optional[str]) -> ScrapeJobStatus:
        if raw_status is None:
            return ScrapeJobStatus.unknown
        return _STATUS_MAP.get(raw_status, ScrapeJobStatus.unknown)

    @staticmethod
    def _coerce_result(payload: Any) -> ScrapeJobResult:
        if isinstance(payload, ScrapeJobResult):
            return payload
        return ScrapeJobResult.model_validate(payload)

    @staticmethod
    def _extract_error(job: Job) -> Optional[str]:
        error = job.meta.get("error")
        if error:
            return str(error)
        if job.is_failed and job.exc_info:
            return job.exc_info.splitlines()[-1]
        return None

    def _build_retry(self) -> Optional[Retry]:
        if settings.scraper_retry_max_attempts <= 0:
            return None
        intervals = list(settings.scraper_retry_intervals)
        if not intervals:
            return Retry(max=settings.scraper_retry_max_attempts)
        return Retry(max=settings.scraper_retry_max_attempts, interval=intervals)
