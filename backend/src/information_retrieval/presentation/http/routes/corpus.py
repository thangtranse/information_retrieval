from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from information_retrieval.application.get_corpus_statistics import GetCorpusStatistics
from information_retrieval.domain.corpus import (
    CorpusDistributions,
    CorpusStatistics,
    CorpusStatisticsUnavailableError,
    Distribution,
)
from information_retrieval.presentation.http.dependencies import (
    get_corpus_statistics_use_case,
)
from information_retrieval.presentation.http.schemas import (
    CorpusDistributionsResponse,
    CorpusStatisticsResponse,
    DistributionResponse,
    SpecialCharacterResponse,
    TopWordResponse,
)

router = APIRouter(prefix="/corpus", tags=["corpus"])


def _distribution_response(distribution: Distribution) -> DistributionResponse:
    """Keep wire projection explicit so persistence types cannot leak through the controller."""
    return DistributionResponse(
        min=distribution.min,
        p25=distribution.p25,
        median=distribution.median,
        mean=distribution.mean,
        p75=distribution.p75,
        p95=distribution.p95,
        max=distribution.max,
    )


def _distributions_response(
    distributions: CorpusDistributions,
) -> CorpusDistributionsResponse:
    """Apply the same stable response shape to normalized and segmented metric groups."""
    return CorpusDistributionsResponse(
        word_count=_distribution_response(distributions.word_count),
        sentence_count=_distribution_response(distributions.sentence_count),
    )


def _to_response(statistics: CorpusStatistics) -> CorpusStatisticsResponse:
    """Map immutable domain results at the HTTP edge instead of coupling them to Pydantic."""
    return CorpusStatisticsResponse(
        document_count=statistics.document_count,
        normalized=_distributions_response(statistics.normalized),
        segmented=_distributions_response(statistics.segmented),
        top_words=[
            TopWordResponse(word=item.word, count=item.count) for item in statistics.top_words
        ],
        special_characters=[
            SpecialCharacterResponse(
                character=item.character,
                code_point=item.code_point,
                unicode_name=item.unicode_name,
                count=item.count,
            )
            for item in statistics.special_characters
        ],
    )


@router.get("/statistics", response_model=CorpusStatisticsResponse)
def get_corpus_statistics(
    use_case: Annotated[GetCorpusStatistics, Depends(get_corpus_statistics_use_case)],
    top_words_limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CorpusStatisticsResponse:
    """Return a read-only corpus snapshot while keeping database failures non-sensitive."""
    try:
        return _to_response(use_case.execute(top_words_limit))
    except CorpusStatisticsUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Corpus statistics are temporarily unavailable",
        ) from error
