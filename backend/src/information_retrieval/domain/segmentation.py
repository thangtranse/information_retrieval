from dataclasses import dataclass

from information_retrieval.domain.article import BlockType

MAX_PARAGRAPH_WORDS = 200


class ArticleSegmentationError(Exception):
    """Expose expected per-document failures so one invalid article does not stop a batch."""


@dataclass(frozen=True, slots=True)
class StoredProcessedParagraph:
    id: int
    crawl_url_id: int
    docid: int
    paragraph_num: int
    block_type: BlockType
    source_word_count: int
    normalized_text: str


@dataclass(frozen=True, slots=True)
class SegmentedSentence:
    processed_paragraph_id: int
    crawl_url_id: int
    docid: int
    paragraph_num: int
    block_type: BlockType
    source_word_count: int
    segment_num: int
    segmented_text: str
    segment_word_count: int


@dataclass(frozen=True, slots=True)
class SegmentationFailure:
    crawl_url_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class SegmentationSummary:
    selected_documents: int
    segmented_documents: int
    processed_paragraphs: int
    stored_segments: int
    failures: list[SegmentationFailure]
