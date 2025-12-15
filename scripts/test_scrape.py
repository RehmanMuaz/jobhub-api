"""Quick reusable CLI to run a single scrape end-to-end.

Run inside the worker/api container so it shares env + DB:
  docker compose exec worker python scripts/test_scrape.py https://example.com/job
"""

from __future__ import annotations

import argparse
from typing import Any

from app.schemas.scrape import ScrapeJobCreate
from app.worker.tasks import run_scrape_job


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a single scrape job and print the result.")
    parser.add_argument("url", help="Job posting URL to scrape")
    parser.add_argument(
        "--source",
        default="other",
        help="Source label (optional, default: other)",
    )
    args = parser.parse_args(argv)

    request = ScrapeJobCreate(url=args.url, source=args.source)
    result = run_scrape_job(request.model_dump())

    # run_scrape_job returns a dict (model_dump), not a Pydantic object
    warnings = result.get("warnings") or []
    error = result.get("error")
    job = result.get("job_posting") or {}

    print("Scrape status: ok" if not error else "Scrape status: error")
    if warnings:
        print(f"Warnings: {warnings}")
    if error:
        print(f"Error: {error}")

    if job:
        print("--- Job ---")
        summary: dict[str, Any] = {
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "url": job.get("url"),
            "salary": job.get("salary"),
            "salary_predicted": job.get("salary_predicted"),
            "score": job.get("score"),
        }
        for key, value in summary.items():
            print(f"{key}: {value}")
    else:
        print("No job_posting returned")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
