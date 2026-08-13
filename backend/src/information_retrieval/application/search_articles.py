from dataclasses import dataclass
from math import isfinite
from threading import Lock

from information_retrieval.application.encode_sentence_texts import EncodeSentenceTexts
from information_retrieval.application.search_ports import ArticleSearchRepository
from information_retrieval.application.segment_normalized_text_parts import (
    SegmentNormalizedTextParts,
)
from information_retrieval.domain.embedding import (
    EncodedSentence,
    SentenceEmbeddingError,
    SentenceText,
)
from information_retrieval.domain.preprocessing import (
    ArticlePreprocessingError,
    split_article_text,
)
from information_retrieval.domain.search import (
    ArticleSearchCandidate,
    ArticleSearchResult,
    InvalidSearchQueryError,
    MatchedArticleSentence,
    RelatedArticle,
    SearchUnavailableError,
)
from information_retrieval.domain.segmentation import (
    ArticleSegmentationError,
    NormalizedTextPart,
)


@dataclass(frozen=True, slots=True)
class _ScoredPair:
    query_index: int
    score: float
    candidate: ArticleSearchCandidate


class SearchArticles:
    def __init__(
        self,
        segment_parts: SegmentNormalizedTextParts,
        encode_sentences: EncodeSentenceTexts,
        repository: ArticleSearchRepository,
        model_name: str,
    ) -> None:
        self._segment_parts = segment_parts
        self._encode_sentences = encode_sentences
        self._repository = repository
        self._model_name = model_name
        self._inference_lock = Lock()

    def execute(self, text: str, top_k: int) -> ArticleSearchResult:
        """Keep model work serialized while releasing the lock before read-only database search."""
        query_text = text.strip()
        if not query_text:
            raise InvalidSearchQueryError("text must not be blank")
        if not 1 <= top_k <= 50:
            raise InvalidSearchQueryError("top_k must be between 1 and 50")

        try:
            split_parts = split_article_text(query_text)
        except ArticlePreprocessingError as error:
            raise InvalidSearchQueryError(str(error)) from error
        if not split_parts:
            raise InvalidSearchQueryError("text has no searchable content after preprocessing")

        try:
            with self._inference_lock:
                segments = self._segment_parts.execute(
                    [
                        NormalizedTextPart(1, part_number, part.normalized_text)
                        for part_number, part in enumerate(split_parts, start=1)
                    ]
                )
                if not segments:
                    raise SearchUnavailableError("segmenter returned no usable query sentence")
                query_sentences = [segment.segmented_text for segment in segments]
                encoded = self._encode_sentences.execute(
                    [
                        SentenceText(query_index, sentence)
                        for query_index, sentence in enumerate(query_sentences)
                    ]
                )
        except SearchUnavailableError:
            raise
        except (ArticleSegmentationError, SentenceEmbeddingError) as error:
            raise SearchUnavailableError("query vectorization failed") from error

        if any(not any(value != 0.0 for value in item.embedding) for item in encoded):
            raise SearchUnavailableError("query vectorization produced a zero vector")

        articles = self._rank_articles(encoded, query_sentences, top_k)
        return ArticleSearchResult(top_k, query_sentences, articles)

    def _rank_articles(
        self,
        encoded: list[EncodedSentence],
        query_sentences: list[str],
        top_k: int,
    ) -> list[RelatedArticle]:
        """Union per-query top-k sets because an omitted article already has k ahead of it."""
        best_by_article: dict[int, _ScoredPair] = {}
        for encoded_sentence in encoded:
            query_index = encoded_sentence.sentence_id
            candidates = self._repository.find_best_articles(
                encoded_sentence.embedding,
                model_name=self._model_name,
                limit=top_k,
            )
            for candidate in candidates:
                if not isfinite(candidate.cosine_distance):
                    raise SearchUnavailableError(
                        "article similarity query returned a non-finite distance"
                    )
                pair = _ScoredPair(
                    query_index=query_index,
                    score=1.0 - candidate.cosine_distance,
                    candidate=candidate,
                )
                current = best_by_article.get(candidate.crawl_url_id)
                pair_key = (-pair.score, pair.query_index, candidate.sentence_id)
                if current is None:
                    best_by_article[candidate.crawl_url_id] = pair
                    continue
                current_key = (
                    -current.score,
                    current.query_index,
                    current.candidate.sentence_id,
                )
                if pair_key < current_key:
                    best_by_article[candidate.crawl_url_id] = pair

        ordered_pairs = sorted(
            best_by_article.values(),
            key=lambda pair: (-pair.score, pair.candidate.crawl_url_id),
        )[:top_k]
        return [
            RelatedArticle(
                rank=rank,
                crawl_url_id=pair.candidate.crawl_url_id,
                title=pair.candidate.title,
                url=pair.candidate.url,
                score=pair.score,
                matched_query_sentence=query_sentences[pair.query_index],
                matched_article_sentence=MatchedArticleSentence(
                    id=pair.candidate.sentence_id,
                    text=pair.candidate.sentence_text,
                    paragraph_num=pair.candidate.paragraph_num,
                    paragraph_part_num=pair.candidate.paragraph_part_num,
                    segment_num=pair.candidate.segment_num,
                ),
            )
            for rank, pair in enumerate(ordered_pairs, start=1)
        ]
