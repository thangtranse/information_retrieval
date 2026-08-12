from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from information_retrieval.domain.embedding import (
    SentenceEmbedding,
    SentenceEmbeddingError,
    StoredSegmentedSentence,
)
from information_retrieval.infrastructure.database import (
    SegmentedSentenceRow,
    SentenceEmbeddingRow,
    ensure_sentence_embedding_cosine_index,
    initialize_schema,
)


class PostgresSentenceEmbeddingRepository:
    """Read segmented inputs and own durable pgvector writes at the infrastructure boundary."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def initialize_schema(self) -> None:
        """Reuse shared metadata so vector storage follows the existing schema lifecycle."""
        try:
            initialize_schema(self._engine)
        except SQLAlchemyError as error:
            raise SentenceEmbeddingError(
                f"database schema initialization failed: {error}"
            ) from error

    def ensure_cosine_index(self) -> None:
        """Build HNSW after writes so existing databases gain the index without recreation."""
        try:
            ensure_sentence_embedding_cosine_index(self._engine)
        except SQLAlchemyError as error:
            raise SentenceEmbeddingError(f"cosine index creation failed: {error}") from error

    def list_for_embedding(self, crawl_id: int | None = None) -> list[StoredSegmentedSentence]:
        """Use stable document and sentence ordering for reproducible model batches."""
        statement = select(
            SegmentedSentenceRow.id,
            SegmentedSentenceRow.crawl_url_id,
            SegmentedSentenceRow.segmented_text,
        ).order_by(
            SegmentedSentenceRow.crawl_url_id,
            SegmentedSentenceRow.paragraph_num,
            SegmentedSentenceRow.paragraph_part_num,
            SegmentedSentenceRow.segment_num,
            SegmentedSentenceRow.id,
        )
        if crawl_id is not None:
            statement = statement.where(SegmentedSentenceRow.crawl_url_id == crawl_id)

        with Session(self._engine) as session:
            return [StoredSegmentedSentence(*row) for row in session.execute(statement).tuples()]

    def upsert_for_crawl_url(
        self,
        crawl_url_id: int,
        model_name: str,
        embeddings: list[SentenceEmbedding],
    ) -> None:
        """Upsert a whole document in one transaction so reruns remain duplicate-free."""
        if not embeddings:
            raise SentenceEmbeddingError(
                f"refusing to persist empty embeddings for crawl_urls.id {crawl_url_id}"
            )

        values = [
            {
                "segmented_sentence_id": record.segmented_sentence_id,
                "model_name": model_name,
                "embedding": record.embedding,
            }
            for record in embeddings
        ]
        statement = insert(SentenceEmbeddingRow).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=[SentenceEmbeddingRow.segmented_sentence_id],
            set_={
                "model_name": statement.excluded.model_name,
                "embedding": statement.excluded.embedding.cast(VECTOR(768)),
                "updated_at": func.now(),
            },
        )

        try:
            with Session(self._engine) as session, session.begin():
                session.execute(statement)
        except SQLAlchemyError as error:
            raise SentenceEmbeddingError(f"database write failed: {error}") from error
