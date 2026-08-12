from typing import Protocol

from information_retrieval.domain.embedding import SentenceEmbedding, StoredSegmentedSentence


class SegmentedSentenceSource(Protocol):
    def list_for_embedding(self, crawl_id: int | None = None) -> list[StoredSegmentedSentence]:
        """Return sentences in document order so batching never changes result attribution."""
        ...


class SentenceEncoder(Protocol):
    def encode(self, sentences: list[str]) -> list[list[float]]:
        """Keep model-specific tokenization outside the application workflow."""
        ...


class SentenceEmbeddingRepository(Protocol):
    def initialize_schema(self) -> None:
        """Create vector storage idempotently for a freshly initialized database."""
        ...

    def upsert_for_crawl_url(
        self,
        crawl_url_id: int,
        model_name: str,
        embeddings: list[SentenceEmbedding],
    ) -> None:
        """Persist one document atomically so partial model output is never searchable."""
        ...
