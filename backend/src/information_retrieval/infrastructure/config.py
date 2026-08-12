from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralize runtime policy so framework adapters do not read process state directly."""

    app_name: str = "Information Retrieval API"
    environment: str = "development"
    ui_origin: str = "http://localhost:5173"

    # Crawler runtime policy. The seed list is a JSON array so Pydantic parses it into a
    # real list without a home-grown delimiter, and every crawl URL is scoped to this host.
    database_url: str = (
        "postgresql+psycopg://information_retrieval:information_retrieval"
        "@localhost:54322/information_retrieval"
    )
    crawler_base_domain: str = "https://vnexpress.net/"
    crawler_seed_urls: list[str] = ["https://vnexpress.net/kinh-doanh"]
    segmenter_model_dir: Path = Path("data/models/py_vncorenlp")
    phobert_model_name: str = "vinai/phobert-base"
    phobert_model_dir: Path = Path("data/models/vinai-phobert")
    embedding_batch_size: int = 16
    embedding_max_length: int = 256

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
