import math
from itertools import groupby

from information_retrieval.application.embedding_ports import (
    SegmentedSentenceSource,
    SentenceEmbeddingRepository,
    SentenceEncoder,
)
from information_retrieval.domain.embedding import (
    EMBEDDING_DIMENSIONS,
    EmbeddingFailure,
    EmbeddingSummary,
    SentenceEmbedding,
    SentenceEmbeddingError,
    StoredSegmentedSentence,
)


class EmbedSegmentedSentences:
    def __init__(
        self,
        sentence_source: SegmentedSentenceSource,
        encoder: SentenceEncoder,
        embedding_repository: SentenceEmbeddingRepository,
        model_name: str,
        batch_size: int,
    ) -> None:
        self._sentence_source = sentence_source
        self._encoder = encoder
        self._embedding_repository = embedding_repository
        self._model_name = model_name
        self._batch_size = batch_size

    def execute(self, crawl_id: int | None = None) -> EmbeddingSummary:
        """Isolate failures by document so one malformed article does not block the corpus."""
        rows = self._sentence_source.list_for_embedding(crawl_id)
        documents = [
            (document_id, list(document_rows))
            for document_id, document_rows in groupby(
                rows, key=lambda sentence: sentence.crawl_url_id
            )
        ]
        embedded_documents = 0
        stored_embeddings = 0
        failures: list[EmbeddingFailure] = []

        for document_id, sentences in documents:
            try:
                embeddings = self._encode_document(sentences)
                self._embedding_repository.upsert_for_crawl_url(
                    document_id, self._model_name, embeddings
                )
            except SentenceEmbeddingError as error:
                failures.append(EmbeddingFailure(document_id, str(error)))
                continue

            embedded_documents += 1
            stored_embeddings += len(embeddings)

        return EmbeddingSummary(
            selected_documents=len(documents),
            embedded_documents=embedded_documents,
            selected_sentences=len(rows),
            stored_embeddings=stored_embeddings,
            failures=failures,
        )

    def _encode_document(self, sentences: list[StoredSegmentedSentence]) -> list[SentenceEmbedding]:
        """Validate complete model output before replacing any durable vector for a document."""
        if self._batch_size <= 0:
            raise SentenceEmbeddingError("embedding batch size must be greater than zero")

        records: list[SentenceEmbedding] = []
        for start in range(0, len(sentences), self._batch_size):
            batch = sentences[start : start + self._batch_size]
            vectors = self._encoder.encode([sentence.segmented_text for sentence in batch])
            if len(vectors) != len(batch):
                raise SentenceEmbeddingError(
                    f"model returned {len(vectors)} vectors for {len(batch)} sentences"
                )

            for sentence, vector in zip(batch, vectors, strict=True):
                if len(vector) != EMBEDDING_DIMENSIONS:
                    raise SentenceEmbeddingError(
                        f"sentence {sentence.id} has {len(vector)} dimensions; "
                        f"expected {EMBEDDING_DIMENSIONS}"
                    )
                if not all(math.isfinite(value) for value in vector):
                    raise SentenceEmbeddingError(
                        f"sentence {sentence.id} embedding contains a non-finite value"
                    )
                if not any(value != 0.0 for value in vector):
                    raise SentenceEmbeddingError(
                        f"sentence {sentence.id} embedding is a zero vector"
                    )
                records.append(SentenceEmbedding(sentence.id, vector))

        if not records:
            raise SentenceEmbeddingError("refusing to persist an empty document embedding")
        return records
