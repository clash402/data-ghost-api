from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:  # pragma: no cover - fallback for minimal environments
    from pydantic import BaseModel

    class BaseSettings(BaseModel):
        def __init__(self, **data):
            merged = {k: v for k, v in os.environ.items()}
            merged.update(data)
            super().__init__(**merged)

    def SettingsConfigDict(**kwargs):
        return kwargs


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "data-ghost-api"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    data_dir: Path = Path("backend/data")
    docs_dir: Path = Path("backend/docs")
    db_path: Path = Path("backend/data/data_ghost.db")

    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_default_model: str = Field(default="mock-default", alias="LLM_DEFAULT_MODEL")
    llm_cheap_model: str = Field(default="mock-cheap", alias="LLM_CHEAP_MODEL")
    llm_expensive_model: str = Field(default="mock-expensive", alias="LLM_EXPENSIVE_MODEL")

    llm_openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    llm_price_prompt_per_1k: float = 0.001
    llm_price_completion_per_1k: float = 0.002

    query_timeout_seconds: float = 5.0
    query_max_rows: int = 5000
    query_max_per_request: int = 10

    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 100
    rag_top_k: int = 5

    max_upload_mb: int = 20


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
