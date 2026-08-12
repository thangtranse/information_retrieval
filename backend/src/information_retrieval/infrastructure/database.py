from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Engine,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Keep schema ownership explicit without introducing a generic persistence framework."""


class CrawlUrlRow(Base):
    __tablename__ = "crawl_urls"

    # A monotonic BIGINT id doubles as the file docid, so the artifact on disk is always
    # traceable to its row without a second identifier.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Uniqueness on the canonical URL is the last-resort guard against duplicate records
    # even if application-level checks race.
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(16),
        # The check constraint pins the same closed vocabulary the domain enforces, so a bad
        # write is rejected by the database and cannot corrupt downstream status logic.
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="crawl_urls_status_check",
        ),
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ProcessedParagraphRow(Base):
    __tablename__ = "processed_paragraphs"
    __table_args__ = (
        UniqueConstraint(
            "crawl_url_id",
            "paragraph_num",
            "paragraph_part_num",
            name="processed_paragraphs_crawl_num_part_key",
        ),
        CheckConstraint(
            "docid = crawl_url_id",
            name="processed_paragraphs_docid_matches_crawl_check",
        ),
        CheckConstraint(
            "paragraph_num > 0",
            name="processed_paragraphs_num_positive_check",
        ),
        CheckConstraint(
            "paragraph_part_num > 0",
            name="processed_paragraphs_part_num_positive_check",
        ),
        CheckConstraint(
            "source_word_count >= 0",
            name="processed_paragraphs_word_count_check",
        ),
        CheckConstraint(
            "block_type IN ('title', 'description', 'paragraph')",
            name="processed_paragraphs_type_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    crawl_url_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_urls.id", ondelete="CASCADE"), nullable=False
    )
    docid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paragraph_num: Mapped[int] = mapped_column(Integer, nullable=False)
    paragraph_part_num: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SegmentedSentenceRow(Base):
    __tablename__ = "segmented_sentences"
    __table_args__ = (
        UniqueConstraint(
            "processed_paragraph_id",
            "segment_num",
            name="segmented_sentences_paragraph_num_key",
        ),
        Index(
            "segmented_sentences_crawl_paragraph_part_segment_idx",
            "crawl_url_id",
            "paragraph_num",
            "paragraph_part_num",
            "segment_num",
        ),
        CheckConstraint(
            "docid = crawl_url_id",
            name="segmented_sentences_docid_matches_crawl_check",
        ),
        CheckConstraint(
            "paragraph_num > 0",
            name="segmented_sentences_paragraph_num_positive_check",
        ),
        CheckConstraint(
            "paragraph_part_num > 0",
            name="segmented_sentences_paragraph_part_num_positive_check",
        ),
        CheckConstraint(
            "source_word_count >= 0",
            name="segmented_sentences_source_word_count_check",
        ),
        CheckConstraint(
            "segment_num > 0",
            name="segmented_sentences_segment_num_positive_check",
        ),
        CheckConstraint(
            "segment_word_count > 0",
            name="segmented_sentences_word_count_positive_check",
        ),
        CheckConstraint(
            "block_type IN ('title', 'description', 'paragraph')",
            name="segmented_sentences_type_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    processed_paragraph_id: Mapped[int] = mapped_column(
        ForeignKey("processed_paragraphs.id", ondelete="CASCADE"), nullable=False
    )
    crawl_url_id: Mapped[int] = mapped_column(
        ForeignKey("crawl_urls.id", ondelete="CASCADE"), nullable=False
    )
    docid: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paragraph_num: Mapped[int] = mapped_column(Integer, nullable=False)
    paragraph_part_num: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    segment_num: Mapped[int] = mapped_column(Integer, nullable=False)
    segmented_text: Mapped[str] = mapped_column(Text, nullable=False)
    segment_word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SentenceEmbeddingRow(Base):
    __tablename__ = "sentence_embeddings"

    # The sentence id is also the primary key because v1 intentionally keeps exactly one
    # active embedding per segmented sentence; model_name records how it was produced.
    segmented_sentence_id: Mapped[int] = mapped_column(
        ForeignKey("segmented_sentences.id", ondelete="CASCADE"), primary_key=True
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(768), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


_SENTENCE_EMBEDDING_COSINE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS sentence_embeddings_embedding_cosine_hnsw_idx "
    "ON sentence_embeddings USING hnsw (embedding vector_cosine_ops) "
    "WITH (m = 16, ef_construction = 64)"
)


def create_database_engine(database_url: str) -> Engine:
    """Build one engine per process. `pool_pre_ping` is enabled because the crawler and the
    Compose Postgres can outlive idle connections, and a stale socket must not fail a crawl."""
    return create_engine(database_url, pool_pre_ping=True, future=True)


def initialize_schema(engine: Engine) -> None:
    """Create missing tables idempotently without adding migration machinery to this scope."""
    Base.metadata.create_all(engine)


def ensure_sentence_embedding_cosine_index(engine: Engine) -> None:
    """Create the ANN index explicitly because create_all cannot upgrade an existing table."""
    with engine.begin() as connection:
        connection.exec_driver_sql(_SENTENCE_EMBEDDING_COSINE_INDEX_SQL)
