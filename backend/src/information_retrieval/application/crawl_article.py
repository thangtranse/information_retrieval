from information_retrieval.application.crawler_ports import (
    ArticleFileStorage,
    ArticleParser,
    ArticleSource,
    CrawlUrlRepository,
)
from information_retrieval.domain.article import serialize_article
from information_retrieval.domain.crawl import CrawlUrl
from information_retrieval.domain.errors import ArticleParseError, UpstreamFetchError
from information_retrieval.domain.url_policy import require_article_url


class ArticleCrawlFailed(Exception):
    """Carry the persisted failed row and a coarse category out of the use case so the HTTP
    boundary can build the failure response and pick 502 vs 422 without re-touching the DB.

    The use case guarantees the row is already `failed` before this is raised, which is why
    delivery code can trust `row` reflects the latest attempt.
    """

    def __init__(self, row: CrawlUrl, category: str) -> None:
        self.row = row
        self.category = category
        super().__init__(row.error_reason or "article crawl failed")


class CrawlArticle:
    def __init__(
        self,
        base_domain: str,
        source: ArticleSource,
        parser: ArticleParser,
        repository: CrawlUrlRepository,
        storage: ArticleFileStorage,
    ) -> None:
        """One use case shared by CLI and API so both paths canonicalize, persist and fail
        by exactly the same rules; divergence here would break the reuse-same-id guarantee."""
        self._base_domain = base_domain
        self._source = source
        self._parser = parser
        self._repository = repository
        self._storage = storage

    def execute(self, url: str) -> CrawlUrl:
        """Fetch, parse and persist one article, reusing the existing row for a known URL.

        A URL that fails policy is rejected before any row exists. Once a row exists, every
        downstream failure is recorded as `failed` (never leaving a stale `pending`) and a
        prior successful file is kept, because losing valid data is worse than a stale flag.
        """
        canonical = require_article_url(self._base_domain, url)

        existing = self._repository.get_by_url(canonical)
        row = existing if existing is not None else self._repository.insert_pending(canonical)

        try:
            final_url, html = self._source.fetch_article(canonical)
            # Re-assert the host contract on the post-redirect URL so an off-host redirect
            # cannot turn a completed crawl into content from an unintended origin.
            require_article_url(self._base_domain, final_url)
        except (UpstreamFetchError, ValueError) as error:
            failed = self._repository.mark_failed(row.id, str(error))
            raise ArticleCrawlFailed(failed, "upstream") from error

        try:
            blocks = self._parser.extract(html)
            serialized = serialize_article(row.id, blocks)
        except ArticleParseError as error:
            failed = self._repository.mark_failed(row.id, str(error))
            raise ArticleCrawlFailed(failed, "parse") from error

        # File write and the completed flag are ordered so the row only claims completion
        # after the durable artifact exists. Persisting storage failures prevents new rows
        # from remaining pending and lets the sequential CLI continue with the next article.
        try:
            file_path = self._storage.write(row.id, serialized)
        except OSError as error:
            failed = self._repository.mark_failed(row.id, str(error))
            raise ArticleCrawlFailed(failed, "storage") from error
        return self._repository.mark_completed(row.id, file_path)
