from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from rq import get_current_job
from rq.job import Job
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.job_posting import JobPosting as JobPostingModel
from app.models.job_posting import RawSnapshot as RawSnapshotModel
from app.schemas.job_posting import RawSnapshot
from app.schemas.scrape import ScrapeJobCreate, ScrapeJobResult
from app.utils.scrape_parsers import extract_job_posting


def run_scrape_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Background worker entrypoint for scraping a single job posting URL."""
    job = get_current_job()
    request = ScrapeJobCreate.model_validate(payload)
    logger.info("Worker starting scrape url=%s source=%s", request.url, request.source)

    try:
        response = _fetch_url(str(request.url))
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Scrape blocked by remote server url=%s status=%s",
            request.url,
            exc.response.status_code,
        )
        _store_error(job, exc, url=str(request.url), status_code=exc.response.status_code)
        result = _build_error_result(
            url=str(request.url),
            message=str(exc),
            response=exc.response,
        )
        return result.model_dump(mode="json")
    except httpx.RequestError as exc:
        logger.warning("Network error fetching url=%s detail=%s", request.url, exc)
        _store_error(job, exc, url=str(request.url))
        result = _build_error_result(url=str(request.url), message=str(exc))
        return result.model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001 - unexpected failure
        logger.exception("Scrape request failed for url=%s", request.url)
        _store_error(job, exc, url=str(request.url))
        raise

    raw_html = response.text
    job_posting, warnings = extract_job_posting(raw_html, str(request.url), request.source)

    preview = _truncate_html(raw_html)
    snapshot = RawSnapshot(
        posting_id=job_posting.id,
        fetched_at=datetime.now(timezone.utc),
        mime_type=_resolve_mime_type(response),
        bytes_location=None,
        status_code=response.status_code,
        headers={k: v for k, v in response.headers.items()},
        raw_html_preview=preview,
    )

    result = ScrapeJobResult(
        job_posting=job_posting,
        snapshot=snapshot,
        raw_html_preview=preview,
        warnings=warnings,
    )

    _persist_result(result)

    logger.info(
        "Scrape completed url=%s status=%s warnings=%d",
        request.url,
        response.status_code,
        len(warnings),
    )
    return result.model_dump(mode="json")


def _fetch_url(url: str) -> httpx.Response:
    headers = {"User-Agent": settings.scraper_user_agent}
    timeout = settings.scraper_timeout_seconds
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response


def _truncate_html(html: str) -> str:
    limit = max(0, settings.scraper_raw_html_preview_limit)
    if limit and len(html) > limit:
        return html[: limit - 3] + "..."
    return html


def _resolve_mime_type(response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "text/html")
    return content_type.split(";")[0].strip().lower()


def _store_error(job: Job | None, exc: Exception, **context: Any) -> None:
    if job is None:
        return
    job.meta["error"] = str(exc)
    if context:
        job.meta["context"] = context
    job.save_meta()


def _build_error_result(
    url: str,
    message: str,
    response: httpx.Response | None = None,
) -> ScrapeJobResult:
    warnings: list[str] = []
    snapshot: RawSnapshot | None = None

    if response is not None:
        warnings.append(f"http_status_{response.status_code}")
        snapshot = RawSnapshot(
            posting_id=None,
            fetched_at=datetime.now(timezone.utc),
            mime_type=_resolve_mime_type(response),
            bytes_location=None,
            status_code=response.status_code,
            headers={k: v for k, v in response.headers.items()},
        )
    else:
        warnings.append("network_error")

    warnings.append("scrape_failed")

    return ScrapeJobResult(
        job_posting=None,
        snapshot=snapshot,
        raw_html_preview=None,
        warnings=warnings,
        error=f"{message} (url={url})",
    )


def _persist_result(result: ScrapeJobResult) -> None:
    job_posting_schema = result.job_posting
    if job_posting_schema is None:
        return

    session = SessionLocal()
    try:
        stmt = select(JobPostingModel).where(JobPostingModel.url == str(job_posting_schema.url))
        job_posting = session.scalar(stmt)

        if job_posting is None:
            job_posting = JobPostingModel(
                id=job_posting_schema.id,
                external_id=job_posting_schema.external_id,
                title=job_posting_schema.title,
                company=job_posting_schema.company,
                location=job_posting_schema.location,
                description_md=job_posting_schema.description_md,
                requirements=job_posting_schema.requirements,
                posted_at=job_posting_schema.posted_at,
                url=str(job_posting_schema.url),
                source=job_posting_schema.source,
            )
            session.add(job_posting)
        else:
            job_posting.external_id = job_posting_schema.external_id
            job_posting.title = job_posting_schema.title
            job_posting.company = job_posting_schema.company
            job_posting.location = job_posting_schema.location
            job_posting.description_md = job_posting_schema.description_md
            job_posting.requirements = job_posting_schema.requirements
            job_posting.posted_at = job_posting_schema.posted_at
            job_posting.source = job_posting_schema.source

        if result.snapshot:
            snapshot_schema = result.snapshot
            snapshot = RawSnapshotModel(
                id=snapshot_schema.id,
                job_posting=job_posting,
                fetched_at=snapshot_schema.fetched_at,
                mime_type=snapshot_schema.mime_type,
                bytes_location=snapshot_schema.bytes_location,
                status_code=snapshot_schema.status_code,
                headers=snapshot_schema.headers,
                raw_html_preview=snapshot_schema.raw_html_preview or result.raw_html_preview,
            )
            session.add(snapshot)

        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to persist scrape result for url=%s", job_posting_schema.url)
    finally:
        session.close()
