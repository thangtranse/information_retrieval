from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from information_retrieval.domain.preprocessing import (
    ArticlePreprocessingError,
    ProcessedParagraph,
)
from information_retrieval.infrastructure.database import (
    ProcessedParagraphRow,
    initialize_schema,
)


class PostgresProcessedParagraphRepository:
    """Persist complete document snapshots without exposing ORM state to the application."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def initialize_schema(self) -> None:
        """Reuse the shared idempotent schema path so the CLI works against a fresh database."""
        initialize_schema(self._engine)

    def replace_for_crawl_url(
        self, crawl_url_id: int, paragraphs: list[ProcessedParagraph]
    ) -> None:
        """Swap a full document snapshot atomically so failures retain the previous good result."""
        if not paragraphs:
            raise ArticlePreprocessingError(
                f"refusing to persist an empty document for crawl_urls.id {crawl_url_id}"
            )

        with Session(self._engine) as session, session.begin():
            session.execute(
                delete(ProcessedParagraphRow).where(
                    ProcessedParagraphRow.crawl_url_id == crawl_url_id
                )
            )
            session.add_all(
                [
                    ProcessedParagraphRow(
                        crawl_url_id=crawl_url_id,
                        docid=paragraph.docid,
                        paragraph_num=paragraph.num,
                        block_type=paragraph.block_type,
                        source_word_count=paragraph.source_word_count,
                        source_text=paragraph.source_text,
                        normalized_text=paragraph.normalized_text,
                        segmented_sentences=paragraph.segmented_sentences,
                    )
                    for paragraph in paragraphs
                ]
            )
