from dataclasses import dataclass
from typing import Literal


class InvalidSearchQueryError(Exception):
    """Identify client-owned input failures without exposing model or persistence details."""


class SearchUnavailableError(Exception):
    """Collapse model and database availability failures into one safe HTTP-facing category."""


@dataclass(frozen=True, slots=True)
class ArticleSearchCandidate:
    crawl_url_id: int
    title: str | None
    url: str
    source_kind: Literal["url", "manual"]
    cosine_distance: float
    sentence_id: int
    sentence_text: str
    paragraph_num: int
    paragraph_part_num: int
    segment_num: int


@dataclass(frozen=True, slots=True)
class MatchedArticleSentence:
    id: int
    text: str
    paragraph_num: int
    paragraph_part_num: int
    segment_num: int


@dataclass(frozen=True, slots=True)
class RelatedArticle:
    rank: int
    crawl_url_id: int
    title: str | None
    url: str
    source_kind: Literal["url", "manual"]
    score: float
    matched_query_sentence: str
    matched_article_sentence: MatchedArticleSentence


@dataclass(frozen=True, slots=True)
class ArticleSearchResult:
    requested_top_k: int
    query_sentences: list[str]
    articles: list[RelatedArticle]
