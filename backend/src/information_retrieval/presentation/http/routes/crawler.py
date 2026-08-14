from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from information_retrieval.application.crawl_article import ArticleCrawlFailed, CrawlArticle
from information_retrieval.application.get_article_preview import (
    CrawledArticleNotFound,
    GetArticlePreview,
)
from information_retrieval.application.list_crawled_articles import (
    InvalidCrawledArticleCursor,
    ListCrawledArticles,
)
from information_retrieval.domain.crawl import CrawlUrl
from information_retrieval.domain.errors import InvalidArticleUrl, UpstreamFetchError
from information_retrieval.presentation.http.dependencies import (
    get_article_preview_use_case,
    get_crawl_article_use_case,
    get_list_crawled_articles_use_case,
)
from information_retrieval.presentation.http.schemas import (
    ArticlePreviewResponse,
    CrawlArticleRequest,
    CrawlArticleResponse,
    CrawledArticleItemResponse,
    CrawledArticlePageResponse,
)

router = APIRouter(prefix="/crawler", tags=["crawler"])

# Map the coarse failure category the use case attaches to the HTTP status the spec assigns:
# upstream problems are gateway errors, structural problems are unprocessable content.
_CATEGORY_STATUS = {
    "upstream": status.HTTP_502_BAD_GATEWAY,
    "parse": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "storage": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _to_response(row: CrawlUrl) -> CrawlArticleResponse:
    """Project the persisted row onto the wire schema so success and failure share one shape."""
    return CrawlArticleResponse(
        id=row.id,
        url=row.url,
        status=row.status,
        file_path=row.file_path,
        error_reason=row.error_reason,
        updated_at=row.updated_at,
    )


@router.get("/articles", response_model=CrawledArticlePageResponse)
def list_crawled_articles(
    use_case: Annotated[ListCrawledArticles, Depends(get_list_crawled_articles_use_case)],
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    cursor: str | None = None,
) -> CrawledArticlePageResponse:
    """Expose stable keyset pages without a count query that grows with the corpus."""
    try:
        page = use_case.execute(limit=limit, cursor=cursor)
    except InvalidCrawledArticleCursor as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid article cursor",
        ) from error
    return CrawledArticlePageResponse(
        items=[
            CrawledArticleItemResponse(
                id=row.id,
                url=row.url,
                source_kind=row.source_kind,
                display_title=row.display_title,
                updated_at=row.updated_at,
            )
            for row in page.items
        ],
        next_cursor=page.next_cursor,
    )


@router.get("/articles/{crawl_id}/preview", response_model=ArticlePreviewResponse)
async def get_article_preview(
    crawl_id: int,
    use_case: Annotated[GetArticlePreview, Depends(get_article_preview_use_case)],
) -> ArticlePreviewResponse:
    """Keep preview failures isolated so the lightweight catalog remains available."""
    try:
        preview = await use_case.execute(crawl_id)
    except CrawledArticleNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except UpstreamFetchError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to load article preview",
        ) from error
    return ArticlePreviewResponse(
        title=preview.title,
        description=preview.description,
        image_url=preview.image_url,
        site_name=preview.site_name,
    )


@router.post("/articles", response_model=CrawlArticleResponse)
def crawl_article(
    request: CrawlArticleRequest,
    use_case: Annotated[CrawlArticle, Depends(get_crawl_article_use_case)],
) -> CrawlArticleResponse | JSONResponse:
    """Crawl one article on demand, always re-fetching even a previously completed URL.

    Policy rejections happen before any row exists (422, no row). Once a row exists, upstream
    and parse failures are already persisted as `failed` by the use case, so the error body
    carries the real row; database/file failures propagate as 500 without claiming success.
    """
    try:
        row = use_case.execute(request.url)
    except InvalidArticleUrl as error:
        # No row was created, so there is no persisted id to report — a plain 422 is honest.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except ArticleCrawlFailed as failure:
        # Return the persisted row at the response root so failed and successful crawl
        # attempts keep the same wire shape instead of hiding failures under `detail`.
        return JSONResponse(
            status_code=_CATEGORY_STATUS[failure.category],
            content=_to_response(failure.row).model_dump(mode="json"),
        )
    return _to_response(row)
