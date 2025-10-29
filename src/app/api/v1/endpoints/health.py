from fastapi import APIRouter
from typing import Dict

router = APIRouter()

@router.get("/health", tags=["health"])  # GET /api/v1/health
async def health() -> Dict[str, str]:
    return {"status": "ok"}
