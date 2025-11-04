from __future__ import annotations

from .base_class import Base

# Import models so Alembic can discover them
from app.models.job_posting import JobPosting, RawSnapshot  # noqa: F401

__all__ = ["Base", "JobPosting", "RawSnapshot"]
