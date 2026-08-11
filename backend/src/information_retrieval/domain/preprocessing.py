import re
from dataclasses import dataclass

from information_retrieval.domain.article import BlockType

CHAR_MAP = {
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "–": "-",
    "—": "-",
}


class ArticlePreprocessingError(Exception):
    """Expose expected per-document failures so a batch can continue without hiding bugs."""


@dataclass(frozen=True, slots=True)
class SourceParagraph:
    docid: int
    num: int
    source_word_count: int
    block_type: BlockType
    text: str


@dataclass(frozen=True, slots=True)
class ProcessedParagraph:
    docid: int
    num: int
    source_word_count: int
    block_type: BlockType
    source_text: str
    normalized_text: str
    segmented_sentences: list[str]


@dataclass(frozen=True, slots=True)
class PreprocessingFailure:
    crawl_url_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class PreprocessingSummary:
    selected_documents: int
    processed_documents: int
    stored_paragraphs: int
    failures: list[PreprocessingFailure]


def normalize_article_text(raw_text: str) -> str:
    """Keep model input stable across typographic variants and invisible crawl artifacts."""
    normalized = raw_text.replace("&gt;", "")
    for source, target in CHAR_MAP.items():
        normalized = normalized.replace(source, target)
    normalized = normalized.replace("\u200b", "")
    normalized = normalized.replace("\ufeff", "")
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()
