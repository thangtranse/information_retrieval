from information_retrieval.application.segmentation_ports import WordSegmenter
from information_retrieval.domain.preprocessing import (
    MAX_PARAGRAPH_WORDS,
    normalize_segmented_text,
)
from information_retrieval.domain.segmentation import (
    ArticleSegmentationError,
    NormalizedTextPart,
    TextSegment,
)


class SegmentNormalizedTextParts:
    def __init__(self, segmenter: WordSegmenter) -> None:
        self._segmenter = segmenter

    def execute(self, parts: list[NormalizedTextPart]) -> list[TextSegment]:
        """Validate every part before model calls so a failure cannot produce partial output."""
        for part in parts:
            normalized_word_count = len(part.normalized_text.split())
            if normalized_word_count > MAX_PARAGRAPH_WORDS:
                raise ArticleSegmentationError(
                    f"paragraph num {part.paragraph_num} "
                    f"part {part.paragraph_part_num} has {normalized_word_count} "
                    f"normalized words; maximum is {MAX_PARAGRAPH_WORDS}"
                )

        segments: list[TextSegment] = []
        for part in parts:
            segmented_texts = self._segmenter.segment(part.normalized_text)
            if not segmented_texts:
                raise ArticleSegmentationError(
                    f"no segmented sentences at paragraph num {part.paragraph_num} "
                    f"part {part.paragraph_part_num}"
                )
            for segment_num, raw_segmented_text in enumerate(segmented_texts, start=1):
                segmented_text = normalize_segmented_text(raw_segmented_text)
                if not segmented_text:
                    raise ArticleSegmentationError(
                        f"empty segmented sentence after normalization at paragraph num "
                        f"{part.paragraph_num} part {part.paragraph_part_num}"
                    )
                segments.append(
                    TextSegment(
                        paragraph_num=part.paragraph_num,
                        paragraph_part_num=part.paragraph_part_num,
                        segment_num=segment_num,
                        segmented_text=segmented_text,
                        segment_word_count=len(segmented_text.split()),
                    )
                )
        return segments
