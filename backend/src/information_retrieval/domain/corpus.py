import unicodedata
from collections import Counter
from dataclasses import dataclass

from information_retrieval.domain.segmentation import (
    SegmentedSentence,
    StoredProcessedParagraph,
)

ALLOWED_CORPUS_PUNCTUATION = frozenset(
    {".", ",", ":", ";", "?", "!", "-", "_", "(", ")", "[", "]", "{", "}", "'", '"', "/", "%"}
)


class CorpusStatisticsUnavailableError(Exception):
    """Keep persistence failures behind a stable application-facing error boundary."""


@dataclass(frozen=True, slots=True)
class CorpusDocumentSnapshot:
    crawl_url_id: int
    normalized_word_count: int
    normalized_sentence_count: int
    segmented_word_count: int
    segmented_sentence_count: int
    underscore_words: list[str]


@dataclass(frozen=True, slots=True)
class Distribution:
    min: float | None
    p25: float | None
    median: float | None
    mean: float | None
    p75: float | None
    p95: float | None
    max: float | None


@dataclass(frozen=True, slots=True)
class CorpusDistributions:
    word_count: Distribution
    sentence_count: Distribution


@dataclass(frozen=True, slots=True)
class TopWord:
    word: str
    count: int


@dataclass(frozen=True, slots=True)
class SpecialCharacter:
    character: str
    code_point: str
    unicode_name: str
    count: int


@dataclass(frozen=True, slots=True)
class CorpusStatistics:
    document_count: int
    normalized: CorpusDistributions
    segmented: CorpusDistributions
    top_words: list[TopWord]
    special_characters: list[SpecialCharacter]


def extract_underscore_words(segmented_texts: list[str]) -> list[str]:
    """Preserve every VnCoreNLP token occurrence so corpus frequency remains reproducible."""
    return [
        token
        for segmented_text in segmented_texts
        for token in segmented_text.split()
        if "_" in token
    ]


def build_corpus_document_snapshot(
    paragraphs: list[StoredProcessedParagraph],
    sentences: list[SegmentedSentence],
) -> CorpusDocumentSnapshot:
    """Reuse the validated segmentation output so corpus metrics never invoke NLP twice."""
    if not paragraphs or not sentences:
        raise ValueError("corpus snapshots require normalized paragraphs and segmented sentences")
    crawl_url_id = paragraphs[0].crawl_url_id
    if any(paragraph.crawl_url_id != crawl_url_id for paragraph in paragraphs) or any(
        sentence.crawl_url_id != crawl_url_id for sentence in sentences
    ):
        raise ValueError("corpus snapshots cannot combine multiple documents")

    segmented_texts = [sentence.segmented_text for sentence in sentences]
    return CorpusDocumentSnapshot(
        crawl_url_id=crawl_url_id,
        normalized_word_count=sum(
            len(paragraph.normalized_text.split()) for paragraph in paragraphs
        ),
        normalized_sentence_count=len(sentences),
        segmented_word_count=sum(sentence.segment_word_count for sentence in sentences),
        segmented_sentence_count=len(sentences),
        underscore_words=extract_underscore_words(segmented_texts),
    )


def count_special_characters(texts: list[str]) -> list[SpecialCharacter]:
    """Share the notebook's Unicode policy so exploratory and API results use one definition."""
    counter = Counter(
        character
        for text in texts
        for character in text
        if not character.isspace()
        and not character.isalnum()
        and character not in ALLOWED_CORPUS_PUNCTUATION
    )
    return [
        SpecialCharacter(
            character=character,
            code_point=f"U+{ord(character):04X}",
            unicode_name=unicodedata.name(character, "UNKNOWN"),
            count=count,
        )
        for character, count in sorted(counter.items(), key=lambda item: (-item[1], ord(item[0])))
    ]
