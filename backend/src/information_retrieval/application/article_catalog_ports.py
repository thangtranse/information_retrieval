from datetime import datetime
from typing import Protocol

from information_retrieval.domain.article_preview import ArticlePreview
from information_retrieval.domain.crawl import CrawlUrl


class CrawledArticleCatalog(Protocol):
    """Keep read-optimized catalog queries separate from crawler write operations."""

    def list_completed_after(
        self,
        *,
        limit: int,
        updated_before: datetime | None,
        id_before: int | None,
    ) -> list[CrawlUrl]: ...

    def get_completed_by_id(self, crawl_id: int) -> CrawlUrl | None: ...


class ArticlePreviewSource(Protocol):
    """Hide outbound HTTP policy from the application preview use case."""

    async def fetch(self, url: str) -> tuple[str, str]: ...


class ArticlePreviewParser(Protocol):
    """Allow metadata extraction to evolve without coupling it to transport or routing."""

    def parse(self, page_url: str, html: str) -> ArticlePreview: ...
