import re
from dataclasses import dataclass

from information_retrieval.domain.article import BlockType

MAX_PARAGRAPH_WORDS = 200

CHAR_MAP = {
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "-": " ",
    "–": " ",
    "—": " ",
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
    paragraph_part_num: int
    source_word_count: int
    block_type: BlockType
    source_text: str
    normalized_text: str


@dataclass(frozen=True, slots=True)
class PreprocessingFailure:
    crawl_url_id: int
    reason: str


@dataclass(frozen=True, slots=True)
class ParagraphSplit:
    crawl_url_id: int
    paragraph_num: int
    original_word_count: int
    generated_parts: int


@dataclass(frozen=True, slots=True)
class PreprocessingSummary:
    selected_documents: int
    processed_documents: int
    stored_paragraphs: int
    split_paragraphs: int
    generated_parts: int
    splits: list[ParagraphSplit]
    failures: list[PreprocessingFailure]


@dataclass(frozen=True, slots=True)
class ArticleTextPart:
    source_text: str
    normalized_text: str
    source_word_count: int


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


def split_article_text(
    source_text: str, max_words: int = MAX_PARAGRAPH_WORDS
) -> list[ArticleTextPart]:
    """Prefer source punctuation boundaries while guaranteeing safe normalized model input."""
    if max_words <= 0:
        raise ValueError("max_words must be greater than zero")

    normalized_text = normalize_article_text(source_text)
    if not normalized_text:
        return []
    if len(normalized_text.split()) <= max_words:
        return [_build_text_part(source_text)]

    chunks: list[str] = []
    current = ""
    for clause in _split_source_clauses(source_text):
        candidate = _join_source_text(current, clause)
        if len(normalize_article_text(candidate).split()) <= max_words:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        clause_parts = _hard_split_source_text(clause, max_words)
        chunks.extend(clause_parts[:-1])
        current = clause_parts[-1]

    if current:
        chunks.append(current)
    return [_build_text_part(chunk) for chunk in chunks]


def _split_source_clauses(source_text: str) -> list[str]:
    """Keep terminal punctuation with the preceding clause so source meaning remains auditable."""
    clauses: list[str] = []
    start = 0
    for match in re.finditer(r"""[.?!:]["'”’)]*(?:\s+|$)""", source_text):
        clause = source_text[start : match.end()].strip()
        if clause:
            clauses.append(clause)
        start = match.end()
    remainder = source_text[start:].strip()
    if remainder:
        clauses.append(remainder)
    return clauses or [source_text.strip()]


def _hard_split_source_text(source_text: str, max_words: int) -> list[str]:
    """Fall back to source word boundaries when one punctuation-delimited clause is oversized."""
    chunks: list[str] = []
    current_words: list[str] = []
    for source_word in source_text.split():
        candidate_words = [*current_words, source_word]
        candidate = " ".join(candidate_words)
        if len(normalize_article_text(candidate).split()) <= max_words:
            current_words = candidate_words
            continue

        if current_words:
            chunks.append(" ".join(current_words))
            current_words = []

        if len(normalize_article_text(source_word).split()) > max_words:
            raise ArticlePreprocessingError(
                "one source word expands beyond the normalized paragraph word limit"
            )
        current_words.append(source_word)

    if current_words:
        chunks.append(" ".join(current_words))
    return chunks


def _join_source_text(left: str, right: str) -> str:
    """Use one stable separator because parsed source blocks do not preserve layout whitespace."""
    return f"{left} {right}".strip()


def _build_text_part(source_text: str) -> ArticleTextPart:
    """Derive both stored representations from one raw chunk to prevent metadata drift."""
    clean_source = source_text.strip()
    return ArticleTextPart(
        source_text=clean_source,
        normalized_text=normalize_article_text(clean_source),
        source_word_count=len(clean_source.split()),
    )
