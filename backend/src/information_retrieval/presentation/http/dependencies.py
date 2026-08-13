from functools import lru_cache
from threading import Lock

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from information_retrieval.application.crawl_article import CrawlArticle
from information_retrieval.application.get_health import GetHealth
from information_retrieval.application.search_articles import SearchArticles
from information_retrieval.domain.embedding import SentenceEmbeddingError
from information_retrieval.domain.search import SearchUnavailableError
from information_retrieval.domain.segmentation import ArticleSegmentationError
from information_retrieval.infrastructure.article_writer import Utf8ArticleFileStorage
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.crawl_repository import PostgresCrawlUrlRepository
from information_retrieval.infrastructure.database import create_database_engine
from information_retrieval.infrastructure.http_source import HttpxArticleSource
from information_retrieval.infrastructure.system_health import SystemHealthProbe
from information_retrieval.infrastructure.vnexpress_parser import VnExpressParser

_search_build_lock = Lock()


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


@lru_cache(maxsize=1)
def _build_search_articles_use_case() -> SearchArticles:
    """Load heavy model adapters only after a search request reaches the HTTP boundary."""
    try:
        from information_retrieval.application.encode_sentence_texts import EncodeSentenceTexts
        from information_retrieval.application.segment_normalized_text_parts import (
            SegmentNormalizedTextParts,
        )
        from information_retrieval.infrastructure.article_search_repository import (
            PostgresArticleSearchRepository,
        )
        from information_retrieval.infrastructure.model_paths import resolve_model_dir
        from information_retrieval.infrastructure.phobert_sentence_encoder import (
            PhoBertSentenceEncoder,
        )
        from information_retrieval.infrastructure.vncorenlp_segmenter import (
            VnCoreNlpWordSegmenter,
        )

        settings = get_settings()
        segment_parts = SegmentNormalizedTextParts(
            VnCoreNlpWordSegmenter(resolve_model_dir(settings.segmenter_model_dir))
        )
        encode_sentences = EncodeSentenceTexts(
            PhoBertSentenceEncoder(
                model_name=settings.phobert_model_name,
                cache_dir=resolve_model_dir(settings.phobert_model_dir),
                max_length=settings.embedding_max_length,
            ),
            settings.embedding_batch_size,
        )
        return SearchArticles(
            segment_parts=segment_parts,
            encode_sentences=encode_sentences,
            repository=PostgresArticleSearchRepository(get_crawl_engine()),
            model_name=settings.phobert_model_name,
        )
    except (
        ArticleSegmentationError,
        ImportError,
        SentenceEmbeddingError,
        SQLAlchemyError,
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        raise SearchUnavailableError("search model initialization failed") from error


def get_search_articles_use_case() -> SearchArticles:
    """Serialize the first cache miss so concurrent requests cannot duplicate model memory."""
    with _search_build_lock:
        return _build_search_articles_use_case()
