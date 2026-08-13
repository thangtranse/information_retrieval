from itertools import groupby

from information_retrieval.application.segment_normalized_text_parts import (
    SegmentNormalizedTextParts,
)
from information_retrieval.application.segmentation_ports import (
    NormalizedParagraphRepository,
    SegmentedSentenceRepository,
    WordSegmenter,
)
from information_retrieval.domain.segmentation import (
    ArticleSegmentationError,
    NormalizedTextPart,
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
        self._segment_parts = SegmentNormalizedTextParts(segmenter)
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
        """Restore metadata after the shared service has built a complete valid document."""
        text_segments = self._segment_parts.execute(
            [
                NormalizedTextPart(
                    paragraph_num=paragraph.paragraph_num,
                    paragraph_part_num=paragraph.paragraph_part_num,
                    normalized_text=paragraph.normalized_text,
                )
                for paragraph in paragraphs
            ]
        )
        paragraph_by_key = {
            (paragraph.paragraph_num, paragraph.paragraph_part_num): paragraph
            for paragraph in paragraphs
        }
        sentences: list[SegmentedSentence] = []
        for segment in text_segments:
            paragraph = paragraph_by_key[(segment.paragraph_num, segment.paragraph_part_num)]
            sentences.append(
                SegmentedSentence(
                    processed_paragraph_id=paragraph.id,
                    crawl_url_id=paragraph.crawl_url_id,
                    docid=paragraph.docid,
                    paragraph_num=segment.paragraph_num,
                    paragraph_part_num=segment.paragraph_part_num,
                    block_type=paragraph.block_type,
                    source_word_count=paragraph.source_word_count,
                    segment_num=segment.segment_num,
                    segmented_text=segment.segmented_text,
                    segment_word_count=segment.segment_word_count,
                )
            )
        return sentences
