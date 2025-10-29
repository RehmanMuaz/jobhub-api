from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.v1.endpoints.health import router as health_router



def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()