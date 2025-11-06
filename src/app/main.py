from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.job_postings import router as job_postings_router
from app.api.v1.endpoints.scrape import router as scrape_router


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name)
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(scrape_router, prefix="/api/v1")
    app.include_router(job_postings_router, prefix="/api/v1")
    return app


app = create_app()
