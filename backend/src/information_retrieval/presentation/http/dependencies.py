from __future__ import annotations

from functools import lru_cache
from threading import Lock
from typing import TYPE_CHECKING

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from information_retrieval.application.crawl_article import CrawlArticle
from information_retrieval.application.embed_segmented_sentences import EmbedSegmentedSentences
from information_retrieval.application.get_article_preview import GetArticlePreview
from information_retrieval.application.get_corpus_statistics import GetCorpusStatistics
from information_retrieval.application.get_health import GetHealth
from information_retrieval.application.import_manual_article import ImportManualArticle
from information_retrieval.application.list_crawled_articles import ListCrawledArticles
from information_retrieval.application.preprocess_crawled_articles import PreprocessCrawledArticles
from information_retrieval.application.search_articles import SearchArticles
from information_retrieval.application.segment_processed_paragraphs import (
    SegmentProcessedParagraphs,
)
from information_retrieval.domain.embedding import SentenceEmbeddingError
from information_retrieval.domain.search import SearchUnavailableError
from information_retrieval.domain.segmentation import ArticleSegmentationError
from information_retrieval.infrastructure.article_preview_source import HttpxArticlePreviewSource
from information_retrieval.infrastructure.article_writer import Utf8ArticleFileStorage
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.corpus_statistics_repository import (
    PostgresCorpusStatisticsRepository,
)
from information_retrieval.infrastructure.crawl_repository import PostgresCrawlUrlRepository
from information_retrieval.infrastructure.database import create_database_engine
from information_retrieval.infrastructure.http_source import HttpxArticleSource
from information_retrieval.infrastructure.open_graph_parser import OpenGraphArticlePreviewParser
from information_retrieval.infrastructure.system_health import SystemHealthProbe
from information_retrieval.infrastructure.vnexpress_parser import VnExpressParser

_search_build_lock = Lock()
_pipeline_build_lock = Lock()
_model_build_lock = Lock()

if TYPE_CHECKING:
    from information_retrieval.infrastructure.phobert_sentence_encoder import (
        PhoBertSentenceEncoder,
    )
    from information_retrieval.infrastructure.vncorenlp_segmenter import VnCoreNlpWordSegmenter


@lru_cache(maxsize=1)
def _build_shared_segmenter() -> VnCoreNlpWordSegmenter:
    """Load one Java segmenter for search and ingestion to avoid duplicate model processes."""
    from information_retrieval.infrastructure.model_paths import resolve_model_dir
    from information_retrieval.infrastructure.vncorenlp_segmenter import VnCoreNlpWordSegmenter

    settings = get_settings()
    return VnCoreNlpWordSegmenter(resolve_model_dir(settings.segmenter_model_dir))


def _get_shared_segmenter() -> VnCoreNlpWordSegmenter:
    """Serialize the cache miss because lru_cache may invoke concurrent misses twice."""
    with _model_build_lock:
        return _build_shared_segmenter()


@lru_cache(maxsize=1)
def _build_shared_encoder() -> PhoBertSentenceEncoder:
    """Load one PhoBERT instance so ingestion cannot exhaust memory before search starts."""
    from information_retrieval.infrastructure.model_paths import resolve_model_dir
    from information_retrieval.infrastructure.phobert_sentence_encoder import (
        PhoBertSentenceEncoder,
    )

    settings = get_settings()
    return PhoBertSentenceEncoder(
        model_name=settings.phobert_model_name,
        cache_dir=resolve_model_dir(settings.phobert_model_dir),
        max_length=settings.embedding_max_length,
    )


def _get_shared_encoder() -> PhoBertSentenceEncoder:
    """Serialize the heavy encoder cache miss across search and pipeline dependencies."""
    with _model_build_lock:
        return _build_shared_encoder()


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


def get_import_manual_article_use_case() -> ImportManualArticle:
    """Give manual input the same repository and atomic file storage as fetched articles."""
    return ImportManualArticle(
        repository=PostgresCrawlUrlRepository(get_crawl_engine()),
        storage=Utf8ArticleFileStorage(),
    )


def get_preprocess_article_use_case() -> PreprocessCrawledArticles:
    """Compose focused HTTP preprocessing without changing the corpus-wide CLI boundary."""
    from information_retrieval.infrastructure.article_paragraph_reader import (
        Utf8ArticleParagraphReader,
    )
    from information_retrieval.infrastructure.processed_paragraph_repository import (
        PostgresProcessedParagraphRepository,
    )

    return PreprocessCrawledArticles(
        crawl_repository=PostgresCrawlUrlRepository(get_crawl_engine()),
        reader=Utf8ArticleParagraphReader(),
        processed_repository=PostgresProcessedParagraphRepository(get_crawl_engine()),
    )


@lru_cache(maxsize=1)
def _build_segment_article_use_case() -> SegmentProcessedParagraphs:
    """Cache the Java-backed segmenter so stage requests do not reload its model files."""
    from information_retrieval.infrastructure.processed_paragraph_repository import (
        PostgresProcessedParagraphRepository,
    )
    from information_retrieval.infrastructure.segmented_sentence_repository import (
        PostgresSegmentedSentenceRepository,
    )

    return SegmentProcessedParagraphs(
        paragraph_repository=PostgresProcessedParagraphRepository(get_crawl_engine()),
        segmenter=_get_shared_segmenter(),
        sentence_repository=PostgresSegmentedSentenceRepository(get_crawl_engine()),
        min_source_word_count=get_settings().segmentation_min_source_word_count,
    )


def get_segment_article_use_case() -> SegmentProcessedParagraphs:
    """Serialize the first segmenter build so concurrent imports share one initialized model."""
    with _pipeline_build_lock:
        return _build_segment_article_use_case()


@lru_cache(maxsize=1)
def _build_embed_article_use_case() -> EmbedSegmentedSentences:
    """Cache PhoBERT because loading it for every imported article would dominate processing."""
    from information_retrieval.infrastructure.sentence_embedding_repository import (
        PostgresSentenceEmbeddingRepository,
    )

    settings = get_settings()
    repository = PostgresSentenceEmbeddingRepository(get_crawl_engine())
    repository.ensure_cosine_index()
    return EmbedSegmentedSentences(
        sentence_source=repository,
        encoder=_get_shared_encoder(),
        embedding_repository=repository,
        model_name=settings.phobert_model_name,
        batch_size=settings.embedding_batch_size,
    )


def get_embed_article_use_case() -> EmbedSegmentedSentences:
    """Serialize the first encoder build while retaining the cached model for later imports."""
    with _pipeline_build_lock:
        return _build_embed_article_use_case()


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

        settings = get_settings()
        segment_parts = SegmentNormalizedTextParts(_get_shared_segmenter())
        encode_sentences = EncodeSentenceTexts(
            _get_shared_encoder(),
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


def get_corpus_statistics_use_case() -> GetCorpusStatistics:
    """Wire corpus reads to the shared pool without exposing SQLAlchemy to the route."""
    return GetCorpusStatistics(PostgresCorpusStatisticsRepository(get_crawl_engine()))
