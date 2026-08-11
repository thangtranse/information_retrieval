import argparse
import sys

from information_retrieval.application.preprocess_crawled_articles import (
    PreprocessCrawledArticles,
)
from information_retrieval.infrastructure.article_paragraph_reader import (
    Utf8ArticleParagraphReader,
)
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.crawl_repository import PostgresCrawlUrlRepository
from information_retrieval.infrastructure.database import create_database_engine
from information_retrieval.infrastructure.processed_paragraph_repository import (
    PostgresProcessedParagraphRepository,
)


def _positive_crawl_id(value: str) -> int:
    """Reject invalid identifiers before they can turn a focused run into a silent no-op."""
    crawl_id = int(value)
    if crawl_id <= 0:
        raise argparse.ArgumentTypeError("crawl id must be greater than zero")
    return crawl_id


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Keep preprocessing limited to normalization with one optional document filter."""
    parser = argparse.ArgumentParser(description="Normalize completed crawled articles")
    parser.add_argument(
        "--crawl-id",
        type=_positive_crawl_id,
        help="process one completed crawl_urls row instead of the full completed corpus",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    """Run normalization without importing or initializing the VnCoreNLP runtime."""
    args = _parse_args(argv)
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    crawl_repository = PostgresCrawlUrlRepository(engine)
    processed_repository = PostgresProcessedParagraphRepository(engine)
    processed_repository.initialize_schema()
    preprocess = PreprocessCrawledArticles(
        crawl_repository=crawl_repository,
        reader=Utf8ArticleParagraphReader(),
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
    for split in summary.splits:
        print(
            f"PREPROCESS_SPLIT id={split.crawl_url_id} "
            f"paragraph={split.paragraph_num} words={split.original_word_count} "
            f"parts={split.generated_parts}"
        )
    print(
        f"SUMMARY selected={summary.selected_documents} "
        f"processed={summary.processed_documents} paragraphs={summary.stored_paragraphs} "
        f"split_paragraphs={summary.split_paragraphs} "
        f"generated_parts={summary.generated_parts} "
        f"failed={len(summary.failures)}"
    )
    return 1 if summary.failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
