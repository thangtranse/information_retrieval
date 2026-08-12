from dataclasses import dataclass

EMBEDDING_DIMENSIONS = 768


class SentenceEmbeddingError(Exception):
    """Expose per-document model or persistence failures without stopping the corpus batch."""


@dataclass(frozen=True, slots=True)
class SentenceText:
    sentence_id: int
    text: str


@dataclass(frozen=True, slots=True)
class EncodedSentence:
    sentence_id: int
    embedding: list[float]


@dataclass(frozen=True, slots=True)
class StoredSegmentedSentence:
    id: int
    crawl_url_id: int
    segmented_text: str


@dataclass(frozen=True, slots=True)
class SentenceEmbedding:
    segmented_sentence_id: int
    embedding: list[float]


@dataclass(frozen=True, slots=True)
class EmbeddingFailure:
    crawl_url_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class EmbeddingSummary:
    selected_documents: int
    embedded_documents: int
    selected_sentences: int
    stored_embeddings: int
    failures: list[EmbeddingFailure]
