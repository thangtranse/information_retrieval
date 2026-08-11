from information_retrieval.application.preprocessing_ports import (
    ArticleParagraphReader,
    CompletedCrawlRepository,
    ProcessedParagraphRepository,
)
from information_retrieval.domain.preprocessing import (
    ArticlePreprocessingError,
    ParagraphSplit,
    PreprocessingFailure,
    PreprocessingSummary,
    ProcessedParagraph,
    normalize_article_text,
    split_article_text,
)


class PreprocessCrawledArticles:
    def __init__(
        self,
        crawl_repository: CompletedCrawlRepository,
        reader: ArticleParagraphReader,
        processed_repository: ProcessedParagraphRepository,
    ) -> None:
        self._crawl_repository = crawl_repository
        self._reader = reader
        self._processed_repository = processed_repository

    def execute(
        self,
        crawl_id: int | None = None,
    ) -> PreprocessingSummary:
        """Isolate expected document failures while preserving prior successful snapshots."""
        crawl_rows = self._crawl_repository.list_completed(crawl_id)
        processed_documents = 0
        stored_paragraphs = 0
        split_paragraphs = 0
        generated_parts = 0
        splits: list[ParagraphSplit] = []
        failures: list[PreprocessingFailure] = []

        for crawl_row in crawl_rows:
            assert crawl_row.file_path is not None
            try:
                source_paragraphs = self._reader.read(crawl_row.id, crawl_row.file_path)
                processed: list[ProcessedParagraph] = []
                document_splits: list[ParagraphSplit] = []
                for source in source_paragraphs:
                    parts = split_article_text(source.text)
                    if not parts:
                        raise ArticlePreprocessingError(
                            f"empty normalized text at paragraph num {source.num}"
                        )
                    if len(parts) > 1:
                        document_splits.append(
                            ParagraphSplit(
                                crawl_url_id=crawl_row.id,
                                paragraph_num=source.num,
                                original_word_count=len(
                                    normalize_article_text(source.text).split()
                                ),
                                generated_parts=len(parts),
                            )
                        )
                    processed.extend(
                        ProcessedParagraph(
                            docid=source.docid,
                            num=source.num,
                            paragraph_part_num=part_num,
                            source_word_count=part.source_word_count,
                            block_type=source.block_type,
                            source_text=part.source_text,
                            normalized_text=part.normalized_text,
                        )
                        for part_num, part in enumerate(parts, start=1)
                    )
                self._processed_repository.replace_for_crawl_url(crawl_row.id, processed)
            except ArticlePreprocessingError as error:
                failures.append(PreprocessingFailure(crawl_url_id=crawl_row.id, reason=str(error)))
                continue

            processed_documents += 1
            stored_paragraphs += len(processed)
            split_paragraphs += len(document_splits)
            generated_parts += sum(item.generated_parts for item in document_splits)
            splits.extend(document_splits)

        return PreprocessingSummary(
            selected_documents=len(crawl_rows),
            processed_documents=processed_documents,
            stored_paragraphs=stored_paragraphs,
            split_paragraphs=split_paragraphs,
            generated_parts=generated_parts,
            splits=splits,
            failures=failures,
        )
