from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_db
from app.models.job_posting import JobPosting as JobPostingModel
from app.schemas.job_posting import RawSnapshot, StoredJobPosting

router = APIRouter(prefix="/job-postings", tags=["job_postings"])


@router.get("/", response_model=List[StoredJobPosting])
def list_job_postings(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[StoredJobPosting]:
    stmt = (
        select(JobPostingModel)
        .options(selectinload(JobPostingModel.snapshots))
        .order_by(JobPostingModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    records = db.scalars(stmt).all()
    return [_to_stored_posting(record) for record in records]


@router.get("/{posting_id}", response_model=StoredJobPosting)
def get_job_posting(
    posting_id: UUID,
    db: Session = Depends(get_db),
) -> StoredJobPosting:
    stmt = (
        select(JobPostingModel)
        .options(selectinload(JobPostingModel.snapshots))
        .where(JobPostingModel.id == posting_id)
    )
    record = db.scalar(stmt)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job posting not found")
    return _to_stored_posting(record)


def _to_stored_posting(
    record: JobPostingModel,
) -> StoredJobPosting:
    latest_snapshot = None
    if record.snapshots:
        latest = record.snapshots[0]
        latest_snapshot = RawSnapshot.model_validate(latest, from_attributes=True)

    posting = StoredJobPosting.model_validate(record, from_attributes=True)
    posting.latest_snapshot = latest_snapshot

    return posting
