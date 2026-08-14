import asyncio

from information_retrieval.application.article_catalog_ports import (
    ArticlePreviewParser,
    ArticlePreviewSource,
    CrawledArticleCatalog,
)
from information_retrieval.domain.article_preview import ArticlePreview


class CrawledArticleNotFound(LookupError):
    """Hide whether a row is absent or merely not completed from public callers."""


class GetArticlePreview:
    def __init__(
        self,
        catalog: CrawledArticleCatalog,
        source: ArticlePreviewSource,
        parser: ArticlePreviewParser,
    ) -> None:
        self._catalog = catalog
        self._source = source
        self._parser = parser

    async def execute(self, crawl_id: int) -> ArticlePreview:
        """Fetch only persisted completed URLs so callers cannot turn preview into an SSRF proxy."""
        # WHY: The preview route is cancellation-aware; synchronous SQL and HTML parsing move off
        # its event loop so one slow operation cannot stall unrelated API requests.
        row = await asyncio.to_thread(self._catalog.get_completed_by_id, crawl_id)
        if row is None:
            raise CrawledArticleNotFound(f"completed crawl URL {crawl_id} was not found")
        if row.source_kind == "manual":
            return ArticlePreview(
                title=row.display_title,
                description=None,
                image_url=None,
                site_name="Nhập thủ công",
            )
        final_url, html = await self._source.fetch(row.url)
        return await asyncio.to_thread(self._parser.parse, final_url, html)
