from typing import Annotated

from fastapi import APIRouter, Depends

from information_retrieval.application.get_health import GetHealth
from information_retrieval.presentation.http.dependencies import get_health_use_case
from information_retrieval.presentation.http.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def read_health(
    use_case: Annotated[GetHealth, Depends(get_health_use_case)],
) -> HealthResponse:
    """Translate the application result at the HTTP boundary to preserve layer ownership."""
    health = use_case.execute()
    return HealthResponse(
        status=health.status,
        service=health.service,
        environment=health.environment,
    )
