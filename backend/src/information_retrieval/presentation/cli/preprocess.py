import argparse
import sys
from pathlib import Path

from information_retrieval.application.preprocess_crawled_articles import (
    PreprocessCrawledArticles,
)
from information_retrieval.domain.preprocessing import ArticlePreprocessingError
from information_retrieval.infrastructure.article_paragraph_reader import (
    Utf8ArticleParagraphReader,
)
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.crawl_repository import PostgresCrawlUrlRepository
from information_retrieval.infrastructure.database import create_database_engine
from information_retrieval.infrastructure.processed_paragraph_repository import (
    PostgresProcessedParagraphRepository,
)
from information_retrieval.infrastructure.vncorenlp_segmenter import VnCoreNlpWordSegmenter

_BACKEND_ROOT = Path(__file__).resolve().parents[4]


def _positive_crawl_id(value: str) -> int:
    """Reject invalid identifiers before they can turn a focused run into a silent no-op."""
    crawl_id = int(value)
    if crawl_id <= 0:
        raise argparse.ArgumentTypeError("crawl id must be greater than zero")
    return crawl_id


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Keep model download explicit so ordinary processing stays offline-repeatable."""
    parser = argparse.ArgumentParser(description="Preprocess completed crawled articles")
    parser.add_argument(
        "--download-model-only",
        action="store_true",
        help="download VnCoreNLP only when the configured cache is incomplete",
    )
    parser.add_argument(
        "--crawl-id",
        type=_positive_crawl_id,
        help="process one completed crawl_urls row instead of the full completed corpus",
    )
    args = parser.parse_args(argv)
    if args.download_model_only and args.crawl_id is not None:
        parser.error("--crawl-id cannot be combined with --download-model-only")
    return args


def _resolve_model_dir(configured_path: Path) -> Path:
    """Anchor a relative model cache to backend regardless of the caller's working directory."""
    if configured_path.is_absolute():
        return configured_path.resolve()
    return (_BACKEND_ROOT / configured_path).resolve()


def run(argv: list[str] | None = None) -> int:
    """Run an explicit model download or a sequential, failure-isolated preprocessing batch."""
    args = _parse_args(argv)
    settings = get_settings()
    model_dir = _resolve_model_dir(settings.segmenter_model_dir)

    if args.download_model_only:
        try:
            downloaded = VnCoreNlpWordSegmenter.download_model(model_dir)
        except ArticlePreprocessingError as error:
            print(f'MODEL status=failed reason="{error}"', file=sys.stderr)
            return 1
        state = "downloaded" if downloaded else "cached"
        print(f"MODEL {state} path={model_dir}")
        return 0

    try:
        segmenter = VnCoreNlpWordSegmenter(model_dir)
    except ArticlePreprocessingError as error:
        print(f'PREPROCESS status=failed reason="{error}"', file=sys.stderr)
        return 1

    engine = create_database_engine(settings.database_url)
    crawl_repository = PostgresCrawlUrlRepository(engine)
    processed_repository = PostgresProcessedParagraphRepository(engine)
    processed_repository.initialize_schema()
    preprocess = PreprocessCrawledArticles(
        crawl_repository=crawl_repository,
        reader=Utf8ArticleParagraphReader(),
        segmenter=segmenter,
        processed_repository=processed_repository,
    )
    summary = preprocess.execute(args.crawl_id)

    if args.crawl_id is not None and summary.selected_documents == 0:
        print(f"PREPROCESS id={args.crawl_id} status=not-found", file=sys.stderr)
        return 1

    for failure in summary.failures:
        print(
            f'PREPROCESS id={failure.crawl_url_id} status=failed reason="{failure.reason}"',
            file=sys.stderr,
        )
    print(
        f"SUMMARY selected={summary.selected_documents} "
        f"processed={summary.processed_documents} paragraphs={summary.stored_paragraphs} "
        f"failed={len(summary.failures)}"
    )
    return 1 if summary.failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
