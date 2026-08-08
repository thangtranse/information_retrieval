from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from information_retrieval.infrastructure.config import get_settings
from information_retrieval.presentation.http.routes.health import router as health_router


def create_app() -> FastAPI:
    """Compose framework and adapters in one place so inner layers stay framework-agnostic."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.ui_origin],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api/v1")
    return app
