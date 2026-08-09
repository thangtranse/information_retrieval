from dataclasses import dataclass

from information_retrieval.application.crawler_ports import (
    ArticleDiscoverer,
    ArticleSource,
    CrawlUrlRepository,
)
from information_retrieval.domain.crawl import CrawlUrl
from information_retrieval.domain.url_policy import require_seed_url


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Report one seed's outcome so the CLI can log and summarize without re-deriving counts
    from repository state that other seeds may have concurrently changed within the run.

    Inserted rows are carried in discovery order so the caller can crawl exactly the URLs it
    just queued, without a second lookup and without touching pre-existing backlog rows.
    """

    seed_url: str
    found: int
    inserted: list[CrawlUrl]
    existing: int


class DiscoverArticles:
    def __init__(
        self,
        base_domain: str,
        source: ArticleSource,
        discoverer: ArticleDiscoverer,
        repository: CrawlUrlRepository,
    ) -> None:
        """Depend only on ports so the same discovery flow works against any source/parser."""
        self._base_domain = base_domain
        self._source = source
        self._discoverer = discoverer
        self._repository = repository

    def execute(self, seed_url: str) -> DiscoveryResult:
        """Discover eligible article URLs on one seed page and insert only the unseen ones.

        Existing rows are left untouched on purpose: re-running seeds must not re-queue the
        entire historical backlog, so discovery's only side effect is inserting new pending
        URLs while preserving discovery order for the sequential crawl that follows.
        """
        canonical_seed = require_seed_url(self._base_domain, seed_url)
        html = self._source.fetch_page(canonical_seed)
        canonical_urls = self._discoverer.discover(canonical_seed, html)

        inserted: list[CrawlUrl] = []
        existing = 0
        # De-duplicate within the page first so a URL linked twice is counted and inserted
        # once, keeping first-seen order for deterministic downstream processing.
        seen: set[str] = set()
        for url in canonical_urls:
            if url in seen:
                continue
            seen.add(url)
            if self._repository.get_by_url(url) is not None:
                existing += 1
                continue
            inserted.append(self._repository.insert_pending(url))

        return DiscoveryResult(
            seed_url=canonical_seed,
            found=len(seen),
            inserted=inserted,
            existing=existing,
        )
