from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str
    environment: str


class CrawlArticleRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str


class CrawlArticleResponse(BaseModel):
    """Mirror the persisted crawl row so success and failure responses share one shape and a
    client can always read the id, canonical url and latest status from the same fields."""

    model_config = ConfigDict(frozen=True)

    id: int
    url: str
    status: str
    file_path: str | None
    error_reason: str | None
    updated_at: datetime


ManualBlockText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50_000),
]


class ManualArticleBlockRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["title", "paragraph"]
    text: ManualBlockText


class ImportManualArticleRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    blocks: Annotated[list[ManualArticleBlockRequest], Field(min_length=2, max_length=500)]

    @model_validator(mode="after")
    def validate_block_order(self) -> ImportManualArticleRequest:
        """Require one leading title so manual records have stable catalog identity."""
        if self.blocks[0].type != "title" or any(
            block.type != "paragraph" for block in self.blocks[1:]
        ):
            raise ValueError("blocks must contain one title followed by paragraph blocks")
        return self


class ImportedArticleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    url: str
    source_kind: Literal["url", "manual"]
    display_title: str | None
    status: str
    file_path: str | None
    updated_at: datetime


class PipelineFailureResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    crawl_id: int
    reason: str


class PreprocessArticleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["completed"] = "completed"
    crawl_id: int
    processed_documents: int
    stored_paragraphs: int
    split_paragraphs: int
    generated_parts: int


class SegmentArticleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["completed"] = "completed"
    crawl_id: int
    segmented_documents: int
    processed_paragraphs: int
    stored_segments: int


class EmbedArticleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["completed"] = "completed"
    crawl_id: int
    embedded_documents: int
    selected_sentences: int
    stored_embeddings: int


SearchText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000),
]


class SearchArticlesRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: SearchText
    top_k: Annotated[int, Field(strict=True, ge=1, le=50)] = 10


class SearchQueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    segment_count: int
    segmented_sentences: list[str]


class MatchedArticleSentenceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    text: str
    paragraph_num: int
    paragraph_part_num: int
    segment_num: int


class RelatedArticleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int
    crawl_url_id: int
    title: str | None
    url: str
    source_kind: Literal["url", "manual"]
    score: float
    matched_query_sentence: str
    matched_article_sentence: MatchedArticleSentenceResponse


class SearchArticlesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["success"] = "success"
    top_k: int
    returned_count: int
    query: SearchQueryResponse
    articles: list[RelatedArticleResponse]


class CrawledArticleItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    url: str
    source_kind: Literal["url", "manual"]
    display_title: str | None
    updated_at: datetime


class CrawledArticlePageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[CrawledArticleItemResponse]
    next_cursor: str | None


class ArticlePreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str | None
    description: str | None
    image_url: str | None
    site_name: str | None


class DistributionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    min: float | None
    p25: float | None
    median: float | None
    mean: float | None
    p75: float | None
    p95: float | None
    max: float | None


class CorpusDistributionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    word_count: DistributionResponse
    sentence_count: DistributionResponse


class TopWordResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    word: str
    count: int


class SpecialCharacterResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    character: str
    code_point: str
    unicode_name: str
    count: int


class CorpusStatisticsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_count: int
    normalized: CorpusDistributionsResponse
    segmented: CorpusDistributionsResponse
    top_words: list[TopWordResponse]
    special_characters: list[SpecialCharacterResponse]
