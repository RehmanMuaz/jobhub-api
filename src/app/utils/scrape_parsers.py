from __future__ import annotations

from datetime import datetime
from typing import Iterable, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings
from app.schemas.common import Source
from app.schemas.job_posting import JobPosting

_DESCRIPTION_MIN_LENGTH = 80


def extract_job_posting(html: str, url: str, source: Source) -> Tuple[JobPosting, list[str]]:
    """Extract a best-effort job posting representation from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    warnings: list[str] = []

    title = _resolve_title(soup)
    if not title:
        title = _fallback_title(url)
        warnings.append("title_inferred_from_url")

    company = _resolve_company(soup)
    if not company:
        company = _fallback_company(url)
        warnings.append("company_inferred_from_domain")

    location = _resolve_location(soup)
    if not location:
        warnings.append("location_missing")

    description = _resolve_description(soup)
    if not description:
        description = "No description detected."
        warnings.append("description_missing")

    requirements = _resolve_requirements(soup)
    if not requirements:
        warnings.append("requirements_missing")

    posted_at = _resolve_posted_at(soup)

    job_posting = JobPosting(
        title=title.strip(),
        company=company.strip(),
        location=location.strip() if location else None,
        description_md=_truncate(description.strip()),
        requirements=requirements,
        posted_at=posted_at,
        url=url,
        source=source,
    )

    logger.debug(
        "Extracted posting title=%s company=%s location=%s requirements=%d",
        job_posting.title,
        job_posting.company,
        job_posting.location,
        len(job_posting.requirements),
    )
    return job_posting, warnings


def _resolve_title(soup: BeautifulSoup) -> str | None:
    meta_keys = [
        ("property", "og:title"),
        ("name", "title"),
        ("name", "og:title"),
        ("property", "twitter:title"),
    ]
    for attr, value in meta_keys:
        if title := _meta_content(soup, attr, value):
            return title

    for tag in ("h1", "h2", "title"):
        node = soup.find(tag)
        if node and (text := node.get_text(strip=True)):
            return text
    return None


def _resolve_company(soup: BeautifulSoup) -> str | None:
    meta_keys = [
        ("name", "company"),
        ("property", "og:site_name"),
        ("name", "twitter:site"),
    ]
    for attr, value in meta_keys:
        content = _meta_content(soup, attr, value)
        if content:
            return content.lstrip("@")

    class_keywords = ("company", "employer", "organization")
    for tag in ("span", "div"):
        node = _find_first_with_class_keyword(soup, tag, class_keywords)
        if node and (text := node.get_text(strip=True)):
            return text
    return None


def _resolve_location(soup: BeautifulSoup) -> str | None:
    meta_keys = [
        ("name", "job:location"),
        ("property", "job:location"),
        ("name", "twitter:label1"),
        ("itemprop", "jobLocation"),
    ]
    for attr, value in meta_keys:
        if content := _meta_content(soup, attr, value):
            return content

    for selector in (
        "[data-test*=location]",
        "[class*=location]",
        "[id*=location]",
        "[class*=job-location]",
    ):
        node = soup.select_one(selector)
        if node and (text := node.get_text(" ", strip=True)):
            return text
    return None


def _resolve_description(soup: BeautifulSoup) -> str | None:
    selectors = (
        "[data-test*=description]",
        "[data-testid*=description]",
        "[id*=description]",
        "[class*=description]",
        "[class*=job-description]",
        "[itemprop=description]",
        "article",
        "main",
    )
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        text = node.get_text("\n", strip=True)
        if len(text) >= _DESCRIPTION_MIN_LENGTH:
            return text

    body_text = soup.get_text("\n", strip=True)
    if len(body_text) >= _DESCRIPTION_MIN_LENGTH:
        return body_text
    return None


def _resolve_requirements(soup: BeautifulSoup) -> list[str]:
    containers = soup.select(
        "ul[class*=requirement], ul[id*=requirement], ul[class*=responsibil], ul[id*=responsibil]"
    )
    if not containers:
        containers = soup.select("ul, ol")

    items: list[str] = []
    for container in containers:
        for li in container.find_all("li"):
            text = li.get_text(" ", strip=True)
            if text and len(text) > 5:
                items.append(text)
        if items:
            break

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _resolve_posted_at(soup: BeautifulSoup) -> datetime | None:
    meta_keys = [
        ("property", "article:published_time"),
        ("property", "article:modified_time"),
        ("itemprop", "datePosted"),
        ("name", "date"),
        ("name", "pubdate"),
    ]
    for attr, value in meta_keys:
        raw = _meta_content(soup, attr, value)
        if raw and (parsed := _parse_datetime(raw)):
            return parsed
    return None


def _meta_content(soup: BeautifulSoup, key: str, value: str) -> str | None:
    tag = soup.find("meta", attrs={key: value})
    if tag and (content := tag.get("content")):
        return content.strip()
    return None


def _find_first_with_class_keyword(soup: BeautifulSoup, tag: str, keywords: Iterable[str]):
    lowered = tuple(keyword.lower() for keyword in keywords)
    for node in soup.find_all(tag):
        class_values = node.get("class") or []
        joined = " ".join(class_values).lower()
        if any(keyword in joined for keyword in lowered):
            return node
    return None


def _parse_datetime(raw: str) -> datetime | None:
    try:
        normalized = raw.strip()
        if normalized.endswith("Z"):
            normalized = normalized.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        logger.debug("Failed to parse datetime from %s", raw)
        return None


def _fallback_title(url: str) -> str:
    parsed = urlparse(url)
    slug = parsed.path.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").replace("_", " ").title() or "Job Posting"


def _fallback_company(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.hostname or "Unknown Company"
    domain = hostname.split(".")
    if len(domain) > 2:
        domain = domain[-2:]
    return " ".join(part.capitalize() for part in domain if part)


def _truncate(value: str) -> str:
    limit = max(0, settings.scraper_raw_html_preview_limit)
    if limit and len(value) > limit:
        return value[:limit - 3] + "..."
    return value
