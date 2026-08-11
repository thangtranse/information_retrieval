from itertools import groupby

from information_retrieval.application.segmentation_ports import (
    NormalizedParagraphRepository,
    SegmentedSentenceRepository,
    WordSegmenter,
)
from information_retrieval.domain.segmentation import (
    MAX_PARAGRAPH_WORDS,
    ArticleSegmentationError,
    SegmentationFailure,
    SegmentationSummary,
    SegmentedSentence,
    StoredProcessedParagraph,
)


class SegmentProcessedParagraphs:
    def __init__(
        self,
        paragraph_repository: NormalizedParagraphRepository,
        segmenter: WordSegmenter,
        sentence_repository: SegmentedSentenceRepository,
    ) -> None:
        self._paragraph_repository = paragraph_repository
        self._segmenter = segmenter
        self._sentence_repository = sentence_repository

    def execute(self, crawl_id: int | None = None) -> SegmentationSummary:
        """Validate and build a full document before replacing its durable snapshot."""
        rows = self._paragraph_repository.list_for_segmentation(crawl_id)
        grouped_rows = [
            (document_id, list(document_rows))
            for document_id, document_rows in groupby(
                rows, key=lambda paragraph: paragraph.crawl_url_id
            )
        ]
        segmented_documents = 0
        processed_paragraphs = 0
        stored_segments = 0
        failures: list[SegmentationFailure] = []

        for document_id, paragraphs in grouped_rows:
            try:
                sentences = self._segment_document(paragraphs)
                self._sentence_repository.replace_for_crawl_url(document_id, sentences)
            except ArticleSegmentationError as error:
                failures.append(SegmentationFailure(document_id, str(error)))
                continue

            segmented_documents += 1
            processed_paragraphs += len(paragraphs)
            stored_segments += len(sentences)

        return SegmentationSummary(
            selected_documents=len(grouped_rows),
            segmented_documents=segmented_documents,
            processed_paragraphs=processed_paragraphs,
            stored_segments=stored_segments,
            failures=failures,
        )

    def _segment_document(
        self, paragraphs: list[StoredProcessedParagraph]
    ) -> list[SegmentedSentence]:
        """Reject an oversized row before model calls so the old document remains untouched."""
        for paragraph in paragraphs:
            normalized_word_count = len(paragraph.normalized_text.split())
            if normalized_word_count > MAX_PARAGRAPH_WORDS:
                raise ArticleSegmentationError(
                    f"paragraph num {paragraph.paragraph_num} has {normalized_word_count} "
                    f"normalized words; maximum is {MAX_PARAGRAPH_WORDS}"
                )

        sentences: list[SegmentedSentence] = []
        for paragraph in paragraphs:
            segmented_texts = self._segmenter.segment(paragraph.normalized_text)
            if not segmented_texts:
                raise ArticleSegmentationError(
                    f"no segmented sentences at paragraph num {paragraph.paragraph_num}"
                )
            for segment_num, segmented_text in enumerate(segmented_texts, start=1):
                if not segmented_text.strip():
                    raise ArticleSegmentationError(
                        f"empty segmented sentence at paragraph num {paragraph.paragraph_num}"
                    )
                sentences.append(
                    SegmentedSentence(
                        processed_paragraph_id=paragraph.id,
                        crawl_url_id=paragraph.crawl_url_id,
                        docid=paragraph.docid,
                        paragraph_num=paragraph.paragraph_num,
                        block_type=paragraph.block_type,
                        source_word_count=paragraph.source_word_count,
                        segment_num=segment_num,
                        segmented_text=segmented_text,
                        segment_word_count=len(segmented_text.split()),
                    )
                )
        return sentences
