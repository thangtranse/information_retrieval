from information_retrieval.application.get_health import GetHealth
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.system_health import SystemHealthProbe


def get_health_use_case() -> GetHealth:
    """Keep concrete dependency construction at the HTTP edge instead of leaking it inward."""
    return GetHealth(SystemHealthProbe(get_settings()))
