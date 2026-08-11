from typing import Protocol

from information_retrieval.domain.crawl import CrawlUrl
from information_retrieval.domain.preprocessing import ProcessedParagraph, SourceParagraph


class CompletedCrawlRepository(Protocol):
    def list_completed(self, crawl_id: int | None = None) -> list[CrawlUrl]:
        """Limit preprocessing to durable article files and retain deterministic id order."""
        ...


class ArticleParagraphReader(Protocol):
    def read(self, crawl_id: int, file_path: str) -> list[SourceParagraph]:
        """Return validated source blocks without leaking file or parser details inward."""
        ...


class WordSegmenter(Protocol):
    def segment(self, text: str) -> list[str]:
        """Hide the Java-backed NLP runtime behind a deterministic application boundary."""
        ...


class ProcessedParagraphRepository(Protocol):
    def initialize_schema(self) -> None:
        """Create the processing table idempotently for CLI execution against a fresh DB."""
        ...

    def replace_for_crawl_url(
        self, crawl_url_id: int, paragraphs: list[ProcessedParagraph]
    ) -> None:
        """Replace one document atomically so stale blocks cannot survive a rerun."""
        ...
