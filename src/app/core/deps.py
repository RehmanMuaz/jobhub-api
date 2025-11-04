from functools import lru_cache
from typing import Generator

from loguru import logger
from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.services.scrape_service import ScrapeService
from app.db.session import get_db_session


@lru_cache
def get_settings():
    return settings


def get_logger():
    return logger


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


@lru_cache
def get_redis_connection() -> Redis:
    return Redis.from_url(settings.redis_url)


@lru_cache
def get_scrape_queue() -> Queue:
    return Queue(name=settings.redis_queue_name, connection=get_redis_connection())


def get_scrape_service() -> ScrapeService:
    return ScrapeService(queue=get_scrape_queue())
