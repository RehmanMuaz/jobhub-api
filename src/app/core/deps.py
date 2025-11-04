from functools import lru_cache
from typing import Generator

from loguru import logger
from redis import Redis
from rq import Queue

from app.core.config import settings
from app.core.services.scrape_service import ScrapeService

# Settings Provider (Singleton)
@lru_cache
def get_settings():
    return settings


# Logger Provider (simple, shared)
def get_logger():
    return logger

# Database Session Provider - PLACEHOLDER
def get_db() -> Generator[None, None, None]:
    # Example for future:
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()
    yield None

# Service Factories
@lru_cache
def get_redis_connection() -> Redis:
    return Redis.from_url(settings.redis_url)


@lru_cache
def get_scrape_queue() -> Queue:
    return Queue(name=settings.redis_queue_name, connection=get_redis_connection())


def get_scrape_service() -> ScrapeService:
    return ScrapeService(queue=get_scrape_queue())
