from typing import Protocol

from information_retrieval.domain.corpus import CorpusDocumentSnapshot
from information_retrieval.domain.segmentation import (
    SegmentedSentence,
    StoredProcessedParagraph,
)


class NormalizedParagraphRepository(Protocol):
    def list_for_segmentation(self, crawl_id: int | None = None) -> list[StoredProcessedParagraph]:
        """Return normalized rows in document and paragraph order for reproducible batches."""
        ...


class WordSegmenter(Protocol):
    def segment(self, text: str) -> list[str]:
        """Hide the Java-backed NLP runtime behind an application-owned boundary."""
        ...


class SegmentedSentenceRepository(Protocol):
    def initialize_schema(self) -> None:
        """Create the segmentation table idempotently for a freshly recreated database."""
        ...

    def replace_for_crawl_url(
        self,
        crawl_url_id: int,
        sentences: list[SegmentedSentence],
        corpus_snapshot: CorpusDocumentSnapshot,
    ) -> None:
        """Replace sentences and corpus summaries as one durable document snapshot."""
        ...
