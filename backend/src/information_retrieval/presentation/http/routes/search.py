import logging
from time import perf_counter
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, HTTPException, status

from information_retrieval.domain.search import (
    ArticleSearchResult,
    InvalidSearchQueryError,
    SearchUnavailableError,
)
from information_retrieval.presentation.http.dependencies import (
    get_search_articles_use_case,
)
from information_retrieval.presentation.http.schemas import (
    MatchedArticleSentenceResponse,
    RelatedArticleResponse,
    SearchArticlesRequest,
    SearchArticlesResponse,
    SearchQueryResponse,
)

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger("uvicorn.error")


def _sentence_preview(text: str) -> str:
    """Bound one-line previews so useful matches cannot flood or forge terminal log lines."""
    return " ".join(text.split())[:160]


def _url_preview(url: str) -> str:
    """Strip userinfo at the log edge because persisted canonical URLs may retain credentials."""
    parts = urlsplit(url)
    host_and_port = parts.netloc.rsplit("@", maxsplit=1)[-1]
    safe_url = urlunsplit((parts.scheme, host_and_port, parts.path, parts.query, parts.fragment))
    return _sentence_preview(safe_url)


def _to_response(result: ArticleSearchResult) -> SearchArticlesResponse:
    """Round only at the wire boundary so ranking always uses the full database score."""
    articles = [
        RelatedArticleResponse(
            rank=article.rank,
            crawl_url_id=article.crawl_url_id,
            title=article.title,
            url=article.url,
            score=round(article.score, 6),
            matched_query_sentence=article.matched_query_sentence,
            matched_article_sentence=MatchedArticleSentenceResponse(
                id=article.matched_article_sentence.id,
                text=article.matched_article_sentence.text,
                paragraph_num=article.matched_article_sentence.paragraph_num,
                paragraph_part_num=article.matched_article_sentence.paragraph_part_num,
                segment_num=article.matched_article_sentence.segment_num,
            ),
        )
        for article in result.articles
    ]
    return SearchArticlesResponse(
        top_k=result.requested_top_k,
        returned_count=len(articles),
        query=SearchQueryResponse(
            segment_count=len(result.query_sentences),
            segmented_sentences=result.query_sentences,
        ),
        articles=articles,
    )


@router.post("/articles", response_model=SearchArticlesResponse)
def search_articles(request: SearchArticlesRequest) -> SearchArticlesResponse:
    """Keep search failures local so crawler and health response contracts remain untouched."""
    started_at = perf_counter()
    try:
        result = get_search_articles_use_case().execute(request.text, request.top_k)
    except InvalidSearchQueryError as error:
        logger.warning('SEARCH status=failed category=validation reason="%s"', error)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except SearchUnavailableError as error:
        logger.error(
            'SEARCH status=failed category=unavailable reason="%s"',
            error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is temporarily unavailable",
        ) from error

    response = _to_response(result)
    duration_ms = round((perf_counter() - started_at) * 1000)
    logger.info(
        "SEARCH status=success query_segments=%d requested_top_k=%d returned=%d duration_ms=%d",
        response.query.segment_count,
        response.top_k,
        response.returned_count,
        duration_ms,
    )
    for article in response.articles:
        logger.info(
            'SEARCH_RESULT rank=%d crawl_url_id=%d score=%.6f sentence_id=%d url="%s" preview="%s"',
            article.rank,
            article.crawl_url_id,
            article.score,
            article.matched_article_sentence.id,
            _url_preview(article.url),
            _sentence_preview(article.matched_article_sentence.text),
        )
    return response
