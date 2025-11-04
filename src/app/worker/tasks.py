from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from rq import get_current_job
from rq.job import Job

from app.core.config import settings
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

    snapshot = RawSnapshot(
        posting_id=job_posting.id,
        fetched_at=datetime.now(timezone.utc),
        mime_type=_resolve_mime_type(response),
        bytes_location=None,
        status_code=response.status_code,
        headers={k: v for k, v in response.headers.items()},
    )

    result = ScrapeJobResult(
        job_posting=job_posting,
        snapshot=snapshot,
        raw_html_preview=_truncate_html(raw_html),
        warnings=warnings,
    )

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
