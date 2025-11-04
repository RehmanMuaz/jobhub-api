from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_scrape_service
from app.core.services.scrape_service import (
    ScrapeJobNotFoundError,
    ScrapeJobResultNotReadyError,
    ScrapeService,
)
from app.schemas.scrape import (
    ScrapeJobCreate,
    ScrapeJobDetail,
    ScrapeJobResponse,
    ScrapeJobResult,
)

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post(
    "/jobs",
    response_model=ScrapeJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_scrape_job(
    payload: ScrapeJobCreate,
    service: ScrapeService = Depends(get_scrape_service),
) -> ScrapeJobResponse:
    return service.enqueue_job(payload)


@router.get("/jobs/{job_id}", response_model=ScrapeJobDetail)
def get_scrape_job(
    job_id: str,
    service: ScrapeService = Depends(get_scrape_service),
) -> ScrapeJobDetail:
    try:
        return service.get_job(job_id)
    except ScrapeJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scrape job not found") from exc


@router.get("/jobs/{job_id}/result", response_model=ScrapeJobResult)
def get_scrape_job_result(
    job_id: str,
    service: ScrapeService = Depends(get_scrape_service),
) -> ScrapeJobResult:
    try:
        return service.get_job_result(job_id)
    except ScrapeJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scrape job not found") from exc
    except ScrapeJobResultNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="scrape job is not yet complete",
        ) from exc
