from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from information_retrieval.domain.corpus import CorpusDocumentSnapshot
from information_retrieval.domain.segmentation import (
    ArticleSegmentationError,
    SegmentedSentence,
)
from information_retrieval.infrastructure.database import (
    NormalizedCorpusDocumentRow,
    SegmentedCorpusDocumentRow,
    SegmentedSentenceRow,
    initialize_schema,
)


class PostgresSegmentedSentenceRepository:
    """Persist sentence rows as complete per-document snapshots."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def initialize_schema(self) -> None:
        """Reuse shared metadata so a fresh database receives both pipeline tables."""
        initialize_schema(self._engine)

    def replace_for_crawl_url(
        self,
        crawl_url_id: int,
        sentences: list[SegmentedSentence],
        corpus_snapshot: CorpusDocumentSnapshot,
    ) -> None:
        """Persist sentences and their metrics together so readers never observe mixed versions."""
        if not sentences:
            raise ArticleSegmentationError(
                f"refusing to persist empty segmentation for crawl_urls.id {crawl_url_id}"
            )

        if corpus_snapshot.crawl_url_id != crawl_url_id:
            raise ArticleSegmentationError(
                f"corpus snapshot id does not match crawl_urls.id {crawl_url_id}"
            )

        with Session(self._engine) as session, session.begin():
            session.execute(
                delete(SegmentedSentenceRow).where(
                    SegmentedSentenceRow.crawl_url_id == crawl_url_id
                )
            )
            session.add_all(
                [
                    SegmentedSentenceRow(
                        processed_paragraph_id=sentence.processed_paragraph_id,
                        crawl_url_id=sentence.crawl_url_id,
                        docid=sentence.docid,
                        paragraph_num=sentence.paragraph_num,
                        paragraph_part_num=sentence.paragraph_part_num,
                        block_type=sentence.block_type,
                        source_word_count=sentence.source_word_count,
                        segment_num=sentence.segment_num,
                        segmented_text=sentence.segmented_text,
                        segment_word_count=sentence.segment_word_count,
                    )
                    for sentence in sentences
                ]
            )
            session.merge(
                NormalizedCorpusDocumentRow(
                    crawl_url_id=crawl_url_id,
                    word_count=corpus_snapshot.normalized_word_count,
                    sentence_count=corpus_snapshot.normalized_sentence_count,
                )
            )
            session.merge(
                SegmentedCorpusDocumentRow(
                    crawl_url_id=crawl_url_id,
                    word_count=corpus_snapshot.segmented_word_count,
                    sentence_count=corpus_snapshot.segmented_sentence_count,
                    underscore_words=corpus_snapshot.underscore_words,
                    underscore_word_count=len(corpus_snapshot.underscore_words),
                )
            )
