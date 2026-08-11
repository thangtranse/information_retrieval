from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from information_retrieval.application.segment_processed_paragraphs import (
    SegmentProcessedParagraphs,
)
from information_retrieval.domain.segmentation import ArticleSegmentationError
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.database import create_database_engine
from information_retrieval.infrastructure.processed_paragraph_repository import (
    PostgresProcessedParagraphRepository,
)
from information_retrieval.infrastructure.segmented_sentence_repository import (
    PostgresSegmentedSentenceRepository,
)

if TYPE_CHECKING:
    from information_retrieval.infrastructure.vncorenlp_segmenter import (
        VnCoreNlpWordSegmenter,
    )

_BACKEND_ROOT = Path(__file__).resolve().parents[4]


def _positive_crawl_id(value: str) -> int:
    """Reject invalid identifiers before they can broaden or silently empty a focused run."""
    crawl_id = int(value)
    if crawl_id <= 0:
        raise argparse.ArgumentTypeError("crawl id must be greater than zero")
    return crawl_id


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Separate explicit model installation from normal offline segmentation runs."""
    parser = argparse.ArgumentParser(description="Segment normalized article paragraphs")
    parser.add_argument(
        "--download-model-only",
        action="store_true",
        help="download VnCoreNLP only when the configured cache is incomplete",
    )
    parser.add_argument(
        "--crawl-id",
        type=_positive_crawl_id,
        help="segment one processed crawl_urls row instead of the full corpus",
    )
    args = parser.parse_args(argv)
    if args.download_model_only and args.crawl_id is not None:
        parser.error("--crawl-id cannot be combined with --download-model-only")
    return args


def _resolve_model_dir(configured_path: Path) -> Path:
    """Anchor relative model caches to backend regardless of the caller's directory."""
    if configured_path.is_absolute():
        return configured_path.resolve()
    return (_BACKEND_ROOT / configured_path).resolve()


def _load_vncorenlp_adapter() -> type[VnCoreNlpWordSegmenter]:
    """Delay Java-backed imports until the segmentation-specific CLI actually needs them."""
    from information_retrieval.infrastructure.vncorenlp_segmenter import (
        VnCoreNlpWordSegmenter,
    )

    return VnCoreNlpWordSegmenter


def run(argv: list[str] | None = None) -> int:
    """Download the model explicitly or run a failure-isolated segmentation batch."""
    args = _parse_args(argv)
    settings = get_settings()
    adapter = _load_vncorenlp_adapter()
    model_dir = _resolve_model_dir(settings.segmenter_model_dir)

    if args.download_model_only:
        try:
            downloaded = adapter.download_model(model_dir)
        except ArticleSegmentationError as error:
            print(f'MODEL status=failed reason="{error}"', file=sys.stderr)
            return 1
        state = "downloaded" if downloaded else "cached"
        print(f"MODEL {state} path={model_dir}")
        return 0

    try:
        segmenter = adapter(model_dir)
    except ArticleSegmentationError as error:
        print(f'SEGMENT status=failed reason="{error}"', file=sys.stderr)
        return 1

    engine = create_database_engine(settings.database_url)
    paragraph_repository = PostgresProcessedParagraphRepository(engine)
    sentence_repository = PostgresSegmentedSentenceRepository(engine)
    sentence_repository.initialize_schema()
    segment = SegmentProcessedParagraphs(
        paragraph_repository=paragraph_repository,
        segmenter=segmenter,
        sentence_repository=sentence_repository,
    )
    summary = segment.execute(args.crawl_id)

    if args.crawl_id is not None and summary.selected_documents == 0:
        print(f"SEGMENT id={args.crawl_id} status=not-found", file=sys.stderr)
        return 1

    for failure in summary.failures:
        print(
            f'SEGMENT id={failure.crawl_url_id} status=failed reason="{failure.reason}"',
            file=sys.stderr,
        )
    print(
        f"SUMMARY selected={summary.selected_documents} "
        f"segmented={summary.segmented_documents} "
        f"paragraphs={summary.processed_paragraphs} segments={summary.stored_segments} "
        f"failed={len(summary.failures)}"
    )
    return 1 if summary.failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
