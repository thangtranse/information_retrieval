from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from information_retrieval.application.crawl_article import ArticleCrawlFailed, CrawlArticle
from information_retrieval.domain.crawl import CrawlUrl
from information_retrieval.domain.errors import InvalidArticleUrl
from information_retrieval.presentation.http.dependencies import get_crawl_article_use_case
from information_retrieval.presentation.http.schemas import (
    CrawlArticleRequest,
    CrawlArticleResponse,
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
