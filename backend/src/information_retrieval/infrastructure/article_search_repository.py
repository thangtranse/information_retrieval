from sqlalchemy import Engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from information_retrieval.domain.search import (
    ArticleSearchCandidate,
    SearchUnavailableError,
)
from information_retrieval.infrastructure.database import (
    CrawlUrlRow,
    ProcessedParagraphRow,
    SegmentedSentenceRow,
    SentenceEmbeddingRow,
)


class PostgresArticleSearchRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find_best_articles(
        self,
        query_embedding: list[float],
        model_name: str,
        limit: int,
    ) -> list[ArticleSearchCandidate]:
        """Rank distinct articles inside a read-only transaction before applying the limit."""
        cosine_distance = SentenceEmbeddingRow.embedding.cosine_distance(query_embedding)
        first_title = (
            select(ProcessedParagraphRow.source_text)
            .where(
                ProcessedParagraphRow.crawl_url_id == SegmentedSentenceRow.crawl_url_id,
                ProcessedParagraphRow.block_type == "title",
            )
            .order_by(
                ProcessedParagraphRow.paragraph_num,
                ProcessedParagraphRow.paragraph_part_num,
                ProcessedParagraphRow.id,
            )
            .limit(1)
            .correlate(SegmentedSentenceRow)
            .scalar_subquery()
        )
        per_article = (
            select(
                SegmentedSentenceRow.crawl_url_id.label("crawl_url_id"),
                CrawlUrlRow.url.label("url"),
                first_title.label("title"),
                SegmentedSentenceRow.id.label("sentence_id"),
                SegmentedSentenceRow.segmented_text.label("sentence_text"),
                SegmentedSentenceRow.paragraph_num.label("paragraph_num"),
                SegmentedSentenceRow.paragraph_part_num.label("paragraph_part_num"),
                SegmentedSentenceRow.segment_num.label("segment_num"),
                cosine_distance.label("cosine_distance"),
            )
            .join(
                SentenceEmbeddingRow,
                SentenceEmbeddingRow.segmented_sentence_id == SegmentedSentenceRow.id,
            )
            .join(CrawlUrlRow, CrawlUrlRow.id == SegmentedSentenceRow.crawl_url_id)
            .where(
                SentenceEmbeddingRow.model_name == model_name,
                CrawlUrlRow.status == "completed",
                cosine_distance.is_not(None),
            )
            .distinct(SegmentedSentenceRow.crawl_url_id)
            .order_by(
                SegmentedSentenceRow.crawl_url_id,
                cosine_distance,
                SegmentedSentenceRow.id,
            )
            .subquery()
        )
        statement = (
            select(per_article)
            .order_by(
                per_article.c.cosine_distance,
                per_article.c.crawl_url_id,
                per_article.c.sentence_id,
            )
            .limit(limit)
        )

        try:
            with Session(self._engine) as session:
                session.execute(text("SET TRANSACTION READ ONLY"))
                rows = session.execute(statement).mappings().all()
        except SQLAlchemyError as error:
            raise SearchUnavailableError("article similarity query failed") from error

        return [
            ArticleSearchCandidate(
                crawl_url_id=row["crawl_url_id"],
                title=row["title"],
                url=row["url"],
                cosine_distance=float(row["cosine_distance"]),
                sentence_id=row["sentence_id"],
                sentence_text=row["sentence_text"],
                paragraph_num=row["paragraph_num"],
                paragraph_part_num=row["paragraph_part_num"],
                segment_num=row["segment_num"],
            )
            for row in rows
        ]
