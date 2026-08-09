import sys

from information_retrieval.application.crawl_article import ArticleCrawlFailed, CrawlArticle
from information_retrieval.application.discover_articles import DiscoverArticles
from information_retrieval.domain.crawl import CrawlUrl
from information_retrieval.domain.errors import UpstreamFetchError
from information_retrieval.infrastructure.article_writer import Utf8ArticleFileStorage
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.crawl_repository import PostgresCrawlUrlRepository
from information_retrieval.infrastructure.database import create_database_engine
from information_retrieval.infrastructure.http_source import HttpxArticleSource
from information_retrieval.infrastructure.vnexpress_discovery import VnExpressDiscoverer
from information_retrieval.infrastructure.vnexpress_parser import VnExpressParser


def run() -> int:
    """Discover then sequentially crawl newly found articles, returning a process exit code.

    The two-phase order (discover every seed, then crawl only URLs inserted this run) is what
    prevents each run from re-downloading the entire historical backlog while still processing
    everything genuinely new. Any seed or article failure is isolated so one bad URL never
    aborts the batch, and the exit code reflects whether the whole run was clean.
    """
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    repository = PostgresCrawlUrlRepository(engine)
    repository.initialize_schema()

    discover = DiscoverArticles(
        base_domain=settings.crawler_base_domain,
        source=HttpxArticleSource(),
        discoverer=VnExpressDiscoverer(settings.crawler_base_domain),
        repository=repository,
    )
    crawl = CrawlArticle(
        base_domain=settings.crawler_base_domain,
        source=HttpxArticleSource(),
        parser=VnExpressParser(),
        repository=repository,
        storage=Utf8ArticleFileStorage(),
    )

    discovered = 0
    # Carry the freshly inserted rows in discovery order so the crawl phase touches only what
    # this run queued, never the pre-existing backlog.
    queued: list[CrawlUrl] = []
    had_failure = False

    for seed in settings.crawler_seed_urls:
        try:
            result = discover.execute(seed)
        except (UpstreamFetchError, ValueError) as error:
            # A seed that cannot be fetched is a run failure, but the remaining seeds must
            # still be attempted, so we log and keep going rather than aborting.
            had_failure = True
            print(f"DISCOVER seed={seed} error={error}", file=sys.stderr)
            continue
        if result.found == 0:
            # A successfully fetched category with no eligible links is usually selector
            # drift, not a clean no-op. Existing-only pages still have `found > 0`, so this
            # check does not turn an ordinary repeat run into a failure.
            had_failure = True
            print(
                f"DISCOVER seed={result.seed_url} found=0 inserted=0 existing=0 "
                'error="no eligible article URLs found"',
                file=sys.stderr,
            )
            continue
        discovered += result.found
        queued.extend(result.inserted)
        print(
            f"DISCOVER seed={seed} found={result.found} "
            f"inserted={len(result.inserted)} existing={result.existing}"
        )

    completed = 0
    failed = 0
    for row in queued:
        try:
            # Crawling by URL reuses the existing row, keeping a single code path shared with
            # the API rather than a CLI-only variant that could drift from it.
            crawled = crawl.execute(row.url)
            completed += 1
            print(f"CRAWL id={crawled.id} status={crawled.status} path={crawled.file_path}")
        except ArticleCrawlFailed as failure:
            failed += 1
            had_failure = True
            print(f'CRAWL id={failure.row.id} status=failed reason="{failure.row.error_reason}"')

    print(
        f"SUMMARY seeds={len(settings.crawler_seed_urls)} discovered={discovered} "
        f"inserted={len(queued)} completed={completed} failed={failed}"
    )
    return 1 if had_failure else 0


if __name__ == "__main__":
    raise SystemExit(run())
