from typing import Protocol

from information_retrieval.domain.health import HealthStatus


class HealthProbe(Protocol):
    """Invert the system-probe dependency so the use case remains independent of infrastructure."""

    def read(self) -> HealthStatus: ...
