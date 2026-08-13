from functools import lru_cache

from sqlalchemy import Engine

from information_retrieval.application.crawl_article import CrawlArticle
from information_retrieval.application.get_article_preview import GetArticlePreview
from information_retrieval.application.get_health import GetHealth
from information_retrieval.application.list_crawled_articles import ListCrawledArticles
from information_retrieval.infrastructure.article_preview_source import HttpxArticlePreviewSource
from information_retrieval.infrastructure.article_writer import Utf8ArticleFileStorage
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.crawl_repository import PostgresCrawlUrlRepository
from information_retrieval.infrastructure.database import create_database_engine
from information_retrieval.infrastructure.http_source import HttpxArticleSource
from information_retrieval.infrastructure.open_graph_parser import OpenGraphArticlePreviewParser
from information_retrieval.infrastructure.system_health import SystemHealthProbe
from information_retrieval.infrastructure.vnexpress_parser import VnExpressParser


def get_health_use_case() -> GetHealth:
    """Keep concrete dependency construction at the HTTP edge instead of leaking it inward."""
    return GetHealth(SystemHealthProbe(get_settings()))


@lru_cache(maxsize=1)
def get_crawl_engine() -> Engine:
    """Share one connection pool across requests. A per-request engine would rebuild the pool
    on every call and exhaust database connections under load."""
    return create_database_engine(get_settings().database_url)


def get_crawl_article_use_case() -> CrawlArticle:
    """Wire the shared crawl use case with concrete adapters at the HTTP edge. The same use
    case backs the CLI, so both paths obey identical canonicalization and persistence rules."""
    settings = get_settings()
    return CrawlArticle(
        base_domain=settings.crawler_base_domain,
        source=HttpxArticleSource(),
        parser=VnExpressParser(),
        repository=PostgresCrawlUrlRepository(get_crawl_engine()),
        storage=Utf8ArticleFileStorage(),
    )


def get_list_crawled_articles_use_case() -> ListCrawledArticles:
    """Reuse the shared pool while exposing a read-only catalog boundary to the use case."""
    return ListCrawledArticles(PostgresCrawlUrlRepository(get_crawl_engine()))


def get_article_preview_use_case() -> GetArticlePreview:
    """Keep outbound preview fetching at the composition edge with the configured host policy."""
    settings = get_settings()
    return GetArticlePreview(
        catalog=PostgresCrawlUrlRepository(get_crawl_engine()),
        source=HttpxArticlePreviewSource(settings.crawler_base_domain),
        parser=OpenGraphArticlePreviewParser(),
    )
