from information_retrieval.application.ports import HealthProbe
from information_retrieval.domain.health import HealthStatus


class GetHealth:
    def __init__(self, probe: HealthProbe) -> None:
        """Accept a port so alternate probes can be introduced without changing business flow."""
        self._probe = probe

    def execute(self) -> HealthStatus:
        """Expose one application operation shared by every future delivery mechanism."""
        return self._probe.read()
