from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralize runtime policy so framework adapters do not read process state directly."""

    app_name: str = "Information Retrieval API"
    environment: str = "development"
    ui_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        frozen=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Reuse one validated configuration to keep every adapter on the same runtime contract."""
    return Settings()
