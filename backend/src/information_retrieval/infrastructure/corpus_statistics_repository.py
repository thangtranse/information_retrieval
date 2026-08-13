from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError

from information_retrieval.domain.corpus import (
    CorpusDistributions,
    CorpusStatistics,
    CorpusStatisticsUnavailableError,
    Distribution,
    TopWord,
    count_special_characters,
)

_DISTRIBUTIONS_SQL = text(
    """
    WITH corpus AS (
        SELECT
            normalized.word_count AS normalized_word_count,
            normalized.sentence_count AS normalized_sentence_count,
            segmented.word_count AS segmented_word_count,
            segmented.sentence_count AS segmented_sentence_count
        FROM normalized_corpus_documents AS normalized
        JOIN segmented_corpus_documents AS segmented USING (crawl_url_id)
    )
    SELECT
        count(*) AS document_count,
        min(normalized_word_count) AS normalized_word_min,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY normalized_word_count)
            AS normalized_word_p25,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY normalized_word_count)
            AS normalized_word_median,
        avg(normalized_word_count) AS normalized_word_mean,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY normalized_word_count)
            AS normalized_word_p75,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY normalized_word_count)
            AS normalized_word_p95,
        max(normalized_word_count) AS normalized_word_max,
        min(normalized_sentence_count) AS normalized_sentence_min,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY normalized_sentence_count)
            AS normalized_sentence_p25,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY normalized_sentence_count)
            AS normalized_sentence_median,
        avg(normalized_sentence_count) AS normalized_sentence_mean,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY normalized_sentence_count)
            AS normalized_sentence_p75,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY normalized_sentence_count)
            AS normalized_sentence_p95,
        max(normalized_sentence_count) AS normalized_sentence_max,
        min(segmented_word_count) AS segmented_word_min,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY segmented_word_count)
            AS segmented_word_p25,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY segmented_word_count)
            AS segmented_word_median,
        avg(segmented_word_count) AS segmented_word_mean,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY segmented_word_count)
            AS segmented_word_p75,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY segmented_word_count)
            AS segmented_word_p95,
        max(segmented_word_count) AS segmented_word_max,
        min(segmented_sentence_count) AS segmented_sentence_min,
        percentile_cont(0.25) WITHIN GROUP (ORDER BY segmented_sentence_count)
            AS segmented_sentence_p25,
        percentile_cont(0.50) WITHIN GROUP (ORDER BY segmented_sentence_count)
            AS segmented_sentence_median,
        avg(segmented_sentence_count) AS segmented_sentence_mean,
        percentile_cont(0.75) WITHIN GROUP (ORDER BY segmented_sentence_count)
            AS segmented_sentence_p75,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY segmented_sentence_count)
            AS segmented_sentence_p95,
        max(segmented_sentence_count) AS segmented_sentence_max
    FROM corpus
    """
)

_TOP_WORDS_SQL = text(
    """
    SELECT token.word, count(*) AS count
    FROM segmented_corpus_documents AS segmented
    JOIN normalized_corpus_documents AS normalized USING (crawl_url_id)
    CROSS JOIN LATERAL unnest(segmented.underscore_words) AS token(word)
    GROUP BY token.word
    ORDER BY count DESC, token.word COLLATE "C" ASC
    LIMIT :top_words_limit
    """
)

_SEGMENTED_TEXTS_SQL = text(
    """
    SELECT sentence.segmented_text
    FROM segmented_sentences AS sentence
    JOIN normalized_corpus_documents AS normalized
        ON normalized.crawl_url_id = sentence.crawl_url_id
    JOIN segmented_corpus_documents AS segmented
        ON segmented.crawl_url_id = sentence.crawl_url_id
    ORDER BY sentence.crawl_url_id, sentence.paragraph_num,
        sentence.paragraph_part_num, sentence.segment_num
    """
)


class PostgresCorpusStatisticsRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_statistics(self, top_words_limit: int) -> CorpusStatistics:
        """Use one repeatable-read snapshot so every section describes the same corpus version."""
        try:
            connection = self._engine.connect().execution_options(isolation_level="REPEATABLE READ")
            with connection, connection.begin():
                metrics = connection.execute(_DISTRIBUTIONS_SQL).mappings().one()
                top_words = [
                    TopWord(word=str(row["word"]), count=int(row["count"]))
                    for row in connection.execute(
                        _TOP_WORDS_SQL, {"top_words_limit": top_words_limit}
                    ).mappings()
                ]
                segmented_texts = [
                    str(value) for value in connection.execute(_SEGMENTED_TEXTS_SQL).scalars()
                ]
        except SQLAlchemyError as error:
            raise CorpusStatisticsUnavailableError(
                "corpus statistics persistence is unavailable"
            ) from error

        return CorpusStatistics(
            document_count=int(metrics["document_count"]),
            normalized=CorpusDistributions(
                word_count=_distribution(metrics, "normalized_word"),
                sentence_count=_distribution(metrics, "normalized_sentence"),
            ),
            segmented=CorpusDistributions(
                word_count=_distribution(metrics, "segmented_word"),
                sentence_count=_distribution(metrics, "segmented_sentence"),
            ),
            top_words=top_words,
            special_characters=count_special_characters(segmented_texts),
        )


def _distribution(row: RowMapping, prefix: str) -> Distribution:
    """Normalize driver numeric types at the persistence boundary for a stable domain contract."""
    return Distribution(
        min=_optional_float(row[f"{prefix}_min"]),
        p25=_optional_float(row[f"{prefix}_p25"]),
        median=_optional_float(row[f"{prefix}_median"]),
        mean=_optional_float(row[f"{prefix}_mean"]),
        p75=_optional_float(row[f"{prefix}_p75"]),
        p95=_optional_float(row[f"{prefix}_p95"]),
        max=_optional_float(row[f"{prefix}_max"]),
    )


def _optional_float(value: Any) -> float | None:
    """Preserve SQL NULL for an empty corpus while standardizing populated numeric values."""
    return None if value is None else float(value)
