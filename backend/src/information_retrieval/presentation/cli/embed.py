from __future__ import annotations

import argparse
import sys
from pathlib import Path

from information_retrieval.application.embed_segmented_sentences import (
    EmbedSegmentedSentences,
)
from information_retrieval.domain.embedding import SentenceEmbeddingError
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.database import create_database_engine
from information_retrieval.infrastructure.phobert_sentence_encoder import PhoBertSentenceEncoder
from information_retrieval.infrastructure.sentence_embedding_repository import (
    PostgresSentenceEmbeddingRepository,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[4]


def _positive_crawl_id(value: str) -> int:
    """Reject invalid identifiers before they can accidentally broaden a focused run."""
    crawl_id = int(value)
    if crawl_id <= 0:
        raise argparse.ArgumentTypeError("crawl id must be greater than zero")
    return crawl_id


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Keep the CLI contract aligned with preprocessing and segmentation commands."""
    parser = argparse.ArgumentParser(description="Embed segmented sentences with PhoBERT")
    parser.add_argument(
        "--crawl-id",
        type=_positive_crawl_id,
        help="embed one segmented crawl_urls row instead of the full corpus",
    )
    return parser.parse_args(argv)


def _resolve_model_dir(configured_path: Path) -> Path:
    """Anchor relative model caches to backend regardless of the caller's directory."""
    if configured_path.is_absolute():
        return configured_path.resolve()
    return (_BACKEND_ROOT / configured_path).resolve()


def run(argv: list[str] | None = None) -> int:
    """Run failure-isolated sentence embedding for one article or the complete corpus."""
    args = _parse_args(argv)
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    repository = PostgresSentenceEmbeddingRepository(engine)

    try:
        repository.initialize_schema()
        encoder = PhoBertSentenceEncoder(
            model_name=settings.phobert_model_name,
            cache_dir=_resolve_model_dir(settings.phobert_model_dir),
            max_length=settings.embedding_max_length,
        )
    except (OSError, RuntimeError, SentenceEmbeddingError) as error:
        print(f'EMBED status=failed reason="{error}"', file=sys.stderr)
        return 1

    summary = EmbedSegmentedSentences(
        sentence_source=repository,
        encoder=encoder,
        embedding_repository=repository,
        model_name=settings.phobert_model_name,
        batch_size=settings.embedding_batch_size,
    ).execute(args.crawl_id)

    if args.crawl_id is not None and summary.selected_documents == 0:
        print(f"EMBED id={args.crawl_id} status=not-found", file=sys.stderr)
        return 1

    index_failed = False
    try:
        repository.ensure_cosine_index()
    except SentenceEmbeddingError as error:
        print(f'EMBED status=failed reason="{error}"', file=sys.stderr)
        index_failed = True

    for failure in summary.failures:
        print(
            f'EMBED id={failure.crawl_url_id} status=failed reason="{failure.reason}"',
            file=sys.stderr,
        )
    print(
        f"SUMMARY selected_documents={summary.selected_documents} "
        f"embedded_documents={summary.embedded_documents} "
        f"selected_sentences={summary.selected_sentences} "
        f"stored_embeddings={summary.stored_embeddings} failed={len(summary.failures)}"
    )
    return 1 if summary.failures or index_failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
