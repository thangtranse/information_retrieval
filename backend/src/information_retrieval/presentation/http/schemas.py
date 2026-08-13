from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str
    environment: str


class CrawlArticleRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str


class CrawlArticleResponse(BaseModel):
    """Mirror the persisted crawl row so success and failure responses share one shape and a
    client can always read the id, canonical url and latest status from the same fields."""

    model_config = ConfigDict(frozen=True)

    id: int
    url: str
    status: str
    file_path: str | None
    error_reason: str | None
    updated_at: datetime


class CrawledArticleItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    url: str
    updated_at: datetime


class CrawledArticlePageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[CrawledArticleItemResponse]
    next_cursor: str | None


class ArticlePreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str | None
    description: str | None
    image_url: str | None
    site_name: str | None
