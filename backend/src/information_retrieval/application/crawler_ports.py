from typing import Protocol

from information_retrieval.domain.article import ContentBlock
from information_retrieval.domain.crawl import CrawlUrl


class ArticleSource(Protocol):
    """Invert the HTTP dependency so use cases stay independent of httpx and of whether the
    bytes came from the network, keeping the network the only thing hard to test."""

    def fetch_page(self, url: str) -> str:
        """Return the HTML of a seed/category page for link discovery."""
        ...

    def fetch_article(self, url: str) -> tuple[str, str]:
        """Return `(final_url, html)` for an article, where final_url is the post-redirect
        URL so the caller can re-assert the host policy against redirect hijacking."""
        ...


class ArticleDiscoverer(Protocol):
    """Find candidate article links on a page. Split from extraction so the anchor contract
    and the article contract can change independently and be replaced on their own."""

    def discover(self, page_url: str, html: str) -> list[str]:
        """Return eligible, already-canonical article URLs found on a page, in DOM order."""
        ...


class ArticleParser(Protocol):
    """Turn one article's HTML into ordered content blocks. Kept separate from discovery so
    extraction has a single reason to change: the article structure contract."""

    def extract(self, html: str) -> list[ContentBlock]:
        """Return ordered content blocks for an article, raising ArticleParseError on any
        contract violation (missing container, no title, no content)."""
        ...


class CrawlUrlRepository(Protocol):
    """Own persistence behind the smallest surface the use cases need; deliberately no
    generic query layer so the single-table scope is not over-abstracted."""

    def initialize_schema(self) -> None:
        """Create the table idempotently at process/script startup."""
        ...

    def get_by_url(self, url: str) -> CrawlUrl | None:
        """Look up an existing row by canonical URL for the reuse decision."""
        ...

    def insert_pending(self, url: str) -> CrawlUrl:
        """Insert a new canonical URL as pending and return the row with its assigned id."""
        ...

    def mark_completed(self, crawl_id: int, file_path: str) -> CrawlUrl:
        """Record a successful crawl: completed status, file path, cleared error, new time."""
        ...

    def mark_failed(self, crawl_id: int, error_reason: str) -> CrawlUrl:
        """Record a failure without discarding any file kept from a prior success."""
        ...


class ArticleFileStorage(Protocol):
    """Isolate file-system concerns so the atomic-write invariant lives in one adapter and
    use cases only deal in the relative path that gets persisted."""

    def write(self, crawl_id: int, serialized: str) -> str:
        """Atomically write the serialized article and return its path relative to backend/."""
        ...
