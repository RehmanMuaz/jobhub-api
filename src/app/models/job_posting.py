from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class JobPosting(TimestampMixin, Base):
    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description_md: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    salary: Mapped[str] = mapped_column(nullable=True)
    salary_predicted: Mapped[str] = mapped_column(nullable=True)
    score: Mapped[float | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="New")

    snapshots: Mapped[list["RawSnapshot"]] = relationship(
        "RawSnapshot",
        back_populates="job_posting",
        cascade="all, delete-orphan",
        order_by="desc(RawSnapshot.fetched_at)",
    )


class RawSnapshot(TimestampMixin, Base):
    __tablename__ = "raw_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_posting_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=True,
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="text/html")
    bytes_location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    headers: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
    raw_html_preview: Mapped[str | None] = mapped_column(Text, nullable=True)

    job_posting: Mapped[JobPosting | None] = relationship(
        "JobPosting",
        back_populates="snapshots",
    )
