from itertools import groupby

from information_retrieval.application.embedding_ports import (
    SegmentedSentenceSource,
    SentenceEmbeddingRepository,
    SentenceEncoder,
)
from information_retrieval.application.encode_sentence_texts import EncodeSentenceTexts
from information_retrieval.domain.embedding import (
    EmbeddingFailure,
    EmbeddingSummary,
    SentenceEmbedding,
    SentenceEmbeddingError,
    SentenceText,
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
        self._sentence_encoder = EncodeSentenceTexts(encoder, batch_size)
        self._embedding_repository = embedding_repository
        self._model_name = model_name

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
        if not sentences:
            raise SentenceEmbeddingError("refusing to persist an empty document embedding")
        encoded = self._sentence_encoder.execute(
            [SentenceText(sentence.id, sentence.segmented_text) for sentence in sentences]
        )
        return [SentenceEmbedding(item.sentence_id, item.embedding) for item in encoded]
