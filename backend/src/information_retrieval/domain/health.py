from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Keep service readiness immutable so boundary adapters cannot corrupt probe results."""

    status: str
    service: str
    environment: str
