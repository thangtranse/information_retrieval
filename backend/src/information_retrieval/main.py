from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.crawl_repository import PostgresCrawlUrlRepository
from information_retrieval.presentation.http.dependencies import get_crawl_engine
from information_retrieval.presentation.http.routes.articles import router as articles_router
from information_retrieval.presentation.http.routes.corpus import router as corpus_router
from information_retrieval.presentation.http.routes.crawler import router as crawler_router
from information_retrieval.presentation.http.routes.health import router as health_router
from information_retrieval.presentation.http.routes.search import router as search_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Create the crawl table on startup so the API is usable against a fresh database without
    a separate migration step, matching the idempotent-init contract the CLI also honors."""
    PostgresCrawlUrlRepository(get_crawl_engine()).initialize_schema()
    yield


def create_app() -> FastAPI:
    """Compose framework and adapters in one place so inner layers stay framework-agnostic."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.ui_origin],
        allow_credentials=True,
        # The manual crawl endpoint is a POST, so the browser origin must be allowed to use it.
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(articles_router, prefix="/api/v1")
    app.include_router(crawler_router, prefix="/api/v1")
    app.include_router(corpus_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    return app
