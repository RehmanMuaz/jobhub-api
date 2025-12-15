from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Iterable, Tuple, Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from loguru import logger

from app.core.config import settings
from app.schemas.common import Source
from app.schemas.job_posting import JobPosting

_DESCRIPTION_MIN_LENGTH = 80

_CURRENCY_RE = re.compile(
    r"""(?ix)
    (?:\$|EUR|USD|CAD|GBP|\u20ac|\u00a3)   # currency symbol or code
    \s*
    \d[\d,\.]*                              # leading amount
    (?:\s*[\u2013-]\s*\d[\d,\.]*)?      # optional range end (dash or en dash)
    (?:\s*[kK])?                                 # optional 'k'
    (?:\s*(?:per|/)\s*(year|yr|hour|hr|month|mo|annum|week|wk))?
    """
)

def extract_job_posting(html: str, url: str, source: Source) -> Tuple[JobPosting, list[str]]:
    """Extract a best-effort job posting representation from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    warnings: list[str] = []

    # Prefer structured data (JSON-LD) when available
    jsonld = _resolve_from_json_ld(soup)

    title = jsonld.get("title") or _resolve_title(soup)
    if not title:
        title = _fallback_title(url)
        warnings.append("title_inferred_from_url")

    company = jsonld.get("company") or _resolve_company(soup)
    if not company:
        company = _fallback_company(url)
        warnings.append("company_inferred_from_domain")

    location = jsonld.get("location") or _resolve_location(soup)
    if not location:
        warnings.append("location_missing")

    description = jsonld.get("description") or _resolve_description(soup)
    if not description:
        description = "No description detected."
        warnings.append("description_missing")

    requirements = jsonld.get("requirements") or _resolve_requirements(soup)
    if not requirements:
        warnings.append("requirements_missing")

    posted_at = jsonld.get("posted_at") or _resolve_posted_at(soup)

    salary = jsonld.get("salary") or _resolve_salary_v2(soup)

    job_posting = JobPosting(
        title=title.strip(),
        company=company.strip(),
        location=location.strip() if location else None,
        description_md=_truncate(description.strip()),
        requirements=requirements,
        posted_at=posted_at,
        url=url,
        source=source,
        salary=salary.strip() if salary else None,
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


def _resolve_from_json_ld(soup: BeautifulSoup) -> dict[str, Any]:
    """Parse schema.org JSON-LD JobPosting if present.

    Returns a dict with any of: title, company, location, description, requirements, posted_at.
    """
    result: dict[str, Any] = {}

    def _nodes_from(data: Any) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        if isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                nodes.extend([n for n in data["@graph"] if isinstance(n, dict)])
            else:
                nodes.append(data)
        elif isinstance(data, list):
            nodes.extend([n for n in data if isinstance(n, dict)])
        return nodes

    def _first_jobposting(nodes: list[dict[str, Any]]) -> dict[str, Any] | None:
        for n in nodes:
            t = n.get("@type")
            if isinstance(t, list):
                if any(str(x).lower() == "jobposting" for x in t):
                    return n
            elif isinstance(t, str) and t.lower() == "jobposting":
                return n
        return None

    def _text_from_html(value: str) -> str:
        # Strip HTML to plain text while keeping line breaks for <li>/<p>
        frag = BeautifulSoup(value, "html.parser")
        for br in frag.find_all(["br", "p"]):
            br.append("\n")
        text = frag.get_text(" ", strip=True)
        # Normalize multiple spaces and line breaks
        text = re.sub(r"\s*\n\s*", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _requirements_from(node: dict[str, Any]) -> list[str]:
        req_fields = []
        for key in ("qualifications", "skills", "educationRequirements", "experienceRequirements", "responsibilities"):
            val = node.get(key)
            if not val:
                continue
            if isinstance(val, list):
                req_fields.extend([str(x) for x in val])
            elif isinstance(val, str):
                # If HTML list, extract <li> items; else split by bullets/newlines
                items: list[str] = []
                frag = BeautifulSoup(val, "html.parser")
                lis = frag.find_all("li")
                if lis:
                    items.extend(li.get_text(" ", strip=True) for li in lis)
                else:
                    text = _text_from_html(val)
                    for part in re.split(r"\n|•|-\s+", text):
                        s = part.strip(" \t-•·")
                        if len(s) > 5:
                            items.append(s)
                req_fields.extend(items)
        # Deduplicate while preserving order
        seen: set[str] = set()
        out: list[str] = []
        for it in req_fields:
            if it and it not in seen:
                seen.add(it)
                out.append(it)
        return out

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except Exception:
            # Some sites wrap multiple JSON-LD objects; try to extract the first object
            try:
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end != -1 and end > start:
                    data = json.loads(raw[start : end + 1])
                else:
                    continue
            except Exception:
                continue

        nodes = _nodes_from(data)
        job = _first_jobposting(nodes)
        if not job:
            # Some pages embed as part of a list
            for n in nodes:
                if isinstance(n, dict):
                    nested = _first_jobposting(_nodes_from(n))
                    if nested:
                        job = nested
                        break
        if not job:
            continue

        # Title/Name
        title = job.get("title") or job.get("name")
        if isinstance(title, str) and title.strip():
            result.setdefault("title", title.strip())

        # Company/Hiring organization
        org = job.get("hiringOrganization")
        company = None
        if isinstance(org, dict):
            company = org.get("name") or org.get("legalName")
        elif isinstance(org, str):
            company = org
        if isinstance(company, str) and company.strip():
            result.setdefault("company", company.strip())

        # Location
        loc = job.get("jobLocation")
        loc_text: str | None = None
        def _addr_to_text(addr: dict[str, Any]) -> str:
            parts = [
                addr.get("addressLocality"),
                addr.get("addressRegion"),
                addr.get("addressCountry"),
            ]
            return ", ".join([str(p) for p in parts if p])
        if isinstance(loc, dict):
            if "address" in loc and isinstance(loc["address"], dict):
                loc_text = _addr_to_text(loc["address"]) or loc.get("name")
        elif isinstance(loc, list) and loc:
            for entry in loc:
                if isinstance(entry, dict):
                    if "address" in entry and isinstance(entry["address"], dict):
                        loc_text = _addr_to_text(entry["address"]) or entry.get("name")
                        if loc_text:
                            break
        if not loc_text and isinstance(job.get("jobLocationType"), str):
            if "telecommute" in job["jobLocationType"].lower():
                loc_text = "Remote"
        if loc_text:
            result.setdefault("location", loc_text)

        # Description
        desc = job.get("description")
        if isinstance(desc, str) and desc.strip():
            text = _text_from_html(desc)
            if len(text) >= _DESCRIPTION_MIN_LENGTH:
                result.setdefault("description", text)

        # Posted at
        date_posted = job.get("datePosted") or job.get("datePublished")
        if isinstance(date_posted, str):
            parsed = _parse_datetime(date_posted)
            if parsed:
                result.setdefault("posted_at", parsed)

        # Requirements
        reqs = _requirements_from(job)
        if reqs:
            result.setdefault("requirements", reqs)

        # Salary / compensation
        salary_text = _salary_from_json_ld(job)
        if salary_text:
            result.setdefault("salary", salary_text)

        # We only need first valid JobPosting
        if result:
            break

    return result


def _salary_from_json_ld(job: dict[str, Any]) -> str | None:
    """Extract salary/baseSalary/estimatedSalary from a JSON-LD JobPosting node."""

    def _format_amount(val: Any) -> str | None:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return f"{val:,.0f}"
        if isinstance(val, str) and val.strip():
            return val.strip()
        return None

    def _format_salary(currency: str | None, min_val: Any, max_val: Any, unit: str | None) -> str | None:
        cur = (currency or "").strip().upper()
        min_txt = _format_amount(min_val)
        max_txt = _format_amount(max_val)
        if not min_txt and not max_txt:
            return None
        if cur and len(cur) == 3:
            cur = f"{cur} "
        prefix = cur or ""
        if min_txt and max_txt and min_txt != max_txt:
            base = f"{prefix}{min_txt}-{prefix}{max_txt}"
        else:
            base = f"{prefix}{min_txt or max_txt}"
        if unit and isinstance(unit, str) and unit.strip():
            base = f"{base} {unit.strip().lower()}"
        return base

    def _parse_salary_node(node: Any) -> str | None:
        if node is None:
            return None
        if isinstance(node, (str, int, float)):
            return _format_amount(node)
        if isinstance(node, list):
            for entry in node:
                parsed = _parse_salary_node(entry)
                if parsed:
                    return parsed
            return None
        if isinstance(node, dict):
            currency = node.get("currency") or node.get("salaryCurrency")
            unit = node.get("unitText") or node.get("unit") or node.get("timeUnit")
            # MonetaryAmount with value sub-object
            value = node.get("value") or node.get("amount")
            if isinstance(value, dict):
                min_val = value.get("minValue") or value.get("value")
                max_val = value.get("maxValue") or value.get("value")
                unit = value.get("unitText") or unit
                formatted = _format_salary(currency, min_val, max_val, unit)
                if formatted:
                    return formatted
            if value and not isinstance(value, dict):
                return _format_salary(currency, value, None, unit)
            min_val = node.get("minValue") or node.get("minimum")
            max_val = node.get("maxValue") or node.get("maximum")
            if min_val or max_val:
                formatted = _format_salary(currency, min_val, max_val, unit)
                if formatted:
                    return formatted
        return None

    for key in ("baseSalary", "estimatedSalary", "salary", "pay"):
        if key in job:
            parsed = _parse_salary_node(job.get(key))
            if parsed:
                return parsed
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
        ("itemprop", "jobLocation"),
    ]
    for attr, value in meta_keys:
        if content := _meta_content(soup, attr, value):
            return content

    # Handle twitter label/data pairs e.g. label1=Location, data1=City
    for i in range(1, 5):
        label = _meta_content(soup, "name", f"twitter:label{i}")
        if label and "location" in label.lower():
            data = _meta_content(soup, "name", f"twitter:data{i}")
            if data:
                return data

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
        # Replace <br> with line breaks for better readability
        for br in node.find_all("br"):
            br.replace_with("\n")
        text = node.get_text("\n", strip=True)
        if len(text) >= _DESCRIPTION_MIN_LENGTH:
            return text

    body_text = soup.get_text("\n", strip=True)
    if len(body_text) >= _DESCRIPTION_MIN_LENGTH:
        return body_text
    return None


def _resolve_requirements(soup: BeautifulSoup) -> list[str]:
    # Prefer lists within the detected description container to avoid nav/breadcrumbs
    desc_container = None
    for selector in (
        "[data-test*=description]",
        "[data-testid*=description]",
        "[id*=description]",
        "[class*=description]",
        "[class*=job-description]",
        "[itemprop=description]",
    ):
        desc_container = soup.select_one(selector)
        if desc_container:
            break

    def _collect_from(root: BeautifulSoup) -> list[str]:
        texts: list[str] = []
        for container in root.select("ul, ol"):
            joined_class = " ".join(container.get("class", [])).lower()
            if any(k in joined_class for k in ("breadcrumb", "nav", "menu", "pagination")):
                continue
            for li in container.find_all("li"):
                t = li.get_text(" ", strip=True)
                if t and len(t) > 5:
                    texts.append(t)
        return texts

    items: list[str] = []
    if desc_container:
        items = _collect_from(desc_container)
    if not items:
        items = _collect_from(soup)

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


def _resolve_salary_v2(soup: BeautifulSoup) -> str | None:
    """More permissive salary resolver that catches ranges and currency codes."""
    meta_keys = [
        ("itemprop", "baseSalary"),
        ("name", "job:salary"),
    ]
    for attr, value in meta_keys:
        if content := _meta_content(soup, attr, value):
            return content

    text = soup.get_text(" ", strip=True)
    raw_html = str(soup)

    salary_range_re = re.compile(
        r"""(?is)
        (?:salary|compensation)[^$0-9]{0,50}(?:range[:\s]*)?
        ((?:\$|EUR|USD|CAD|GBP|\u20ac|\u00a3)\s*\d[\d,\.]*\s*(?:[\u2013-]\s*(?:\$|EUR|USD|CAD|GBP|\u20ac|\u00a3)?\s*\d[\d,\.]*))
        """,
        re.VERBOSE,
    )
    if (m := salary_range_re.search(text) or salary_range_re.search(raw_html)):
        return m.group(1)

    if (m := _CURRENCY_RE.search(text) or _CURRENCY_RE.search(raw_html)):
        return m.group(0)

    return None


def _resolve_salary(soup: BeautifulSoup) -> str | None:
    meta_keys = [
        ("itemprop", "baseSalary"),
        ("name", "job:salary"),
    ]
    for attr, value in meta_keys:
        if content := _meta_content(soup, attr, value):
            return content

    # Fallback: scan text (and raw HTML) for currency+number patterns and common phrases
    text = soup.get_text(" ", strip=True)

    salary_range_re = re.compile(
        r"""(?ix)
        (?:salary|compensation)[^\d$€£]*(?:range[:\s]*)?
        ((?:\$|EUR|USD|CAD|GBP|\u20ac|\u00a3)\s*\d[\d,\.]*\s*[–-]\s*(?:\$|EUR|USD|CAD|GBP|\u20ac|\u00a3)?\s*\d[\d,\.]*)
        """
    )
    range_match = salary_range_re.search(text)
    if range_match:
        return range_match.group(1)

    if m := _CURRENCY_RE.search(text):
        return m.group(0)

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
