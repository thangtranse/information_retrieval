from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from information_retrieval.application.embed_segmented_sentences import EmbedSegmentedSentences
from information_retrieval.application.import_manual_article import ImportManualArticle
from information_retrieval.application.preprocess_crawled_articles import PreprocessCrawledArticles
from information_retrieval.application.segment_processed_paragraphs import (
    SegmentProcessedParagraphs,
)
from information_retrieval.domain.article import ContentBlock
from information_retrieval.domain.embedding import SentenceEmbeddingError
from information_retrieval.domain.segmentation import ArticleSegmentationError
from information_retrieval.presentation.http.dependencies import (
    get_embed_article_use_case,
    get_import_manual_article_use_case,
    get_preprocess_article_use_case,
    get_segment_article_use_case,
)
from information_retrieval.presentation.http.schemas import (
    EmbedArticleResponse,
    ImportedArticleResponse,
    ImportManualArticleRequest,
    PreprocessArticleResponse,
    SegmentArticleResponse,
)

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("/manual", response_model=ImportedArticleResponse, status_code=status.HTTP_201_CREATED)
def import_manual_article(
    request: ImportManualArticleRequest,
    use_case: Annotated[ImportManualArticle, Depends(get_import_manual_article_use_case)],
) -> ImportedArticleResponse:
    """Accept structured text while keeping final `<s>` metadata authoritative on the server."""
    row = use_case.execute(
        [ContentBlock(type=block.type, text=block.text) for block in request.blocks]
    )
    return ImportedArticleResponse(
        id=row.id,
        url=row.url,
        source_kind=row.source_kind,
        display_title=row.display_title,
        status=row.status,
        file_path=row.file_path,
        updated_at=row.updated_at,
    )


@router.post("/{crawl_id}/preprocess", response_model=PreprocessArticleResponse)
def preprocess_article(
    crawl_id: int,
    use_case: Annotated[PreprocessCrawledArticles, Depends(get_preprocess_article_use_case)],
) -> PreprocessArticleResponse:
    """Expose the existing snapshot replacement for exactly one completed article."""
    summary = use_case.execute(crawl_id)
    _require_stage_success(crawl_id, summary.selected_documents, summary.failures)
    return PreprocessArticleResponse(
        crawl_id=crawl_id,
        processed_documents=summary.processed_documents,
        stored_paragraphs=summary.stored_paragraphs,
        split_paragraphs=summary.split_paragraphs,
        generated_parts=summary.generated_parts,
    )


@router.post("/{crawl_id}/segment", response_model=SegmentArticleResponse)
def segment_article(
    crawl_id: int,
    use_case: Annotated[SegmentProcessedParagraphs, Depends(get_segment_article_use_case)],
) -> SegmentArticleResponse:
    """Require preprocessed input by treating an empty focused selection as a stage conflict."""
    try:
        summary = use_case.execute(crawl_id)
    except ArticleSegmentationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    _require_stage_success(crawl_id, summary.selected_documents, summary.failures)
    return SegmentArticleResponse(
        crawl_id=crawl_id,
        segmented_documents=summary.segmented_documents,
        processed_paragraphs=summary.processed_paragraphs,
        stored_segments=summary.stored_segments,
    )


@router.post("/{crawl_id}/embed", response_model=EmbedArticleResponse)
def embed_article(
    crawl_id: int,
    use_case: Annotated[EmbedSegmentedSentences, Depends(get_embed_article_use_case)],
) -> EmbedArticleResponse:
    """Embed only the selected article and fail honestly when segmentation has no input."""
    try:
        summary = use_case.execute(crawl_id)
    except SentenceEmbeddingError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    _require_stage_success(crawl_id, summary.selected_documents, summary.failures)
    return EmbedArticleResponse(
        crawl_id=crawl_id,
        embedded_documents=summary.embedded_documents,
        selected_sentences=summary.selected_sentences,
        stored_embeddings=summary.stored_embeddings,
    )


def _require_stage_success(crawl_id: int, selected: int, failures: Sequence[object]) -> None:
    """Distinguish missing prerequisites from a selected document that failed its stage."""
    if selected == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"crawl_id": crawl_id, "reason": "stage input was not found"},
        )
    if failures:
        reason = str(getattr(failures[0], "reason", "stage processing failed"))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"crawl_id": crawl_id, "reason": reason},
        )
