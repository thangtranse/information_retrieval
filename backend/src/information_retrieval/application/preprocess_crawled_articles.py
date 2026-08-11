from information_retrieval.application.preprocessing_ports import (
    ArticleParagraphReader,
    CompletedCrawlRepository,
    ProcessedParagraphRepository,
    WordSegmenter,
)
from information_retrieval.domain.preprocessing import (
    ArticlePreprocessingError,
    PreprocessingFailure,
    PreprocessingMode,
    PreprocessingSummary,
    ProcessedParagraph,
    normalize_article_text,
)


class PreprocessCrawledArticles:
    def __init__(
        self,
        crawl_repository: CompletedCrawlRepository,
        reader: ArticleParagraphReader,
        segmenter: WordSegmenter | None,
        processed_repository: ProcessedParagraphRepository,
    ) -> None:
        self._crawl_repository = crawl_repository
        self._reader = reader
        self._segmenter = segmenter
        self._processed_repository = processed_repository

    def execute(
        self,
        crawl_id: int | None = None,
        mode: PreprocessingMode = "normalize_and_segment",
    ) -> PreprocessingSummary:
        """Isolate expected document failures while preserving prior successful snapshots."""
        if mode == "normalize_and_segment" and self._segmenter is None:
            raise ArticlePreprocessingError(
                "word segmenter is required for normalize_and_segment mode"
            )

        crawl_rows = self._crawl_repository.list_completed(crawl_id)
        processed_documents = 0
        stored_paragraphs = 0
        failures: list[PreprocessingFailure] = []

        for crawl_row in crawl_rows:
            assert crawl_row.file_path is not None
            try:
                source_paragraphs = self._reader.read(crawl_row.id, crawl_row.file_path)
                processed: list[ProcessedParagraph] = []
                for source in source_paragraphs:
                    normalized_text = normalize_article_text(source.text)
                    if not normalized_text:
                        raise ArticlePreprocessingError(
                            f"empty normalized text at paragraph num {source.num}"
                        )
                    if mode == "normalize_only":
                        segmented_sentences: list[str] = []
                    else:
                        assert self._segmenter is not None
                        segmented_sentences = self._segmenter.segment(normalized_text)
                        if not segmented_sentences:
                            raise ArticlePreprocessingError(
                                f"no segmented sentences at paragraph num {source.num}"
                            )
                    processed.append(
                        ProcessedParagraph(
                            docid=source.docid,
                            num=source.num,
                            source_word_count=source.source_word_count,
                            block_type=source.block_type,
                            source_text=source.text,
                            normalized_text=normalized_text,
                            segmented_sentences=segmented_sentences,
                        )
                    )
                self._processed_repository.replace_for_crawl_url(crawl_row.id, processed)
            except ArticlePreprocessingError as error:
                failures.append(PreprocessingFailure(crawl_url_id=crawl_row.id, reason=str(error)))
                continue

            processed_documents += 1
            stored_paragraphs += len(processed)

        return PreprocessingSummary(
            selected_documents=len(crawl_rows),
            processed_documents=processed_documents,
            stored_paragraphs=stored_paragraphs,
            failures=failures,
        )
