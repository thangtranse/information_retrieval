import math

from information_retrieval.application.embedding_ports import SentenceEncoder
from information_retrieval.domain.embedding import (
    EMBEDDING_DIMENSIONS,
    EncodedSentence,
    SentenceEmbeddingError,
    SentenceText,
)


class EncodeSentenceTexts:
    def __init__(self, encoder: SentenceEncoder, batch_size: int) -> None:
        self._encoder = encoder
        self._batch_size = batch_size

    def execute(self, sentences: list[SentenceText]) -> list[EncodedSentence]:
        """Validate complete ordered batches so callers never consume partial model output."""
        if self._batch_size <= 0:
            raise SentenceEmbeddingError("embedding batch size must be greater than zero")

        encoded_sentences: list[EncodedSentence] = []
        for start in range(0, len(sentences), self._batch_size):
            batch = sentences[start : start + self._batch_size]
            vectors = self._encoder.encode([sentence.text for sentence in batch])
            if len(vectors) != len(batch):
                raise SentenceEmbeddingError(
                    f"model returned {len(vectors)} vectors for {len(batch)} sentences"
                )
            for sentence, vector in zip(batch, vectors, strict=True):
                if len(vector) != EMBEDDING_DIMENSIONS:
                    raise SentenceEmbeddingError(
                        f"sentence {sentence.sentence_id} has {len(vector)} dimensions; "
                        f"expected {EMBEDDING_DIMENSIONS}"
                    )
                if not all(math.isfinite(value) for value in vector):
                    raise SentenceEmbeddingError(
                        f"sentence {sentence.sentence_id} embedding contains a non-finite value"
                    )
                if not any(value != 0.0 for value in vector):
                    raise SentenceEmbeddingError(
                        f"sentence {sentence.sentence_id} embedding is a zero vector"
                    )
                encoded_sentences.append(EncodedSentence(sentence.sentence_id, vector))

        if not encoded_sentences:
            raise SentenceEmbeddingError("refusing to encode an empty sentence list")
        return encoded_sentences
