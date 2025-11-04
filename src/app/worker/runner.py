from __future__ import annotations

from rq import Worker

from app.core.deps import get_redis_connection, get_scrape_queue


def main() -> None:
    redis = get_redis_connection()
    queue = get_scrape_queue()

    worker = Worker([queue], connection=redis)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
