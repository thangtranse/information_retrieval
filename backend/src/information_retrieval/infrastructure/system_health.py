from information_retrieval.domain.health import HealthStatus
from information_retrieval.infrastructure.config import Settings


class SystemHealthProbe:
    def __init__(self, settings: Settings) -> None:
        """Bind runtime metadata at composition time to keep probe output deterministic."""
        self._settings = settings

    def read(self) -> HealthStatus:
        """Report process readiness through the domain contract expected by the application."""
        return HealthStatus(
            status="ok",
            service=self._settings.app_name,
            environment=self._settings.environment,
        )
