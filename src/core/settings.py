from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path

from pydantic import Field, field_validator

ENV_FILES = (".env", ".env.local")


def _load_env_files(paths: tuple[str, ...]) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        env_path = Path(path)
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            values[key] = value
    return values


try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:  # pragma: no cover - fallback for minimal environments
    from pydantic import BaseModel

    class BaseSettings(BaseModel):
        def __init__(self, **data):
            merged = _load_env_files(ENV_FILES)
            merged.update({k: v for k, v in os.environ.items()})

            normalized = {}
            for key, value in merged.items():
                normalized[key] = value
                normalized[key.lower()] = value

            normalized.update(data)
            super().__init__(**normalized)

    def SettingsConfigDict(**kwargs):
        return kwargs


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "data-ghost-api"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    data_dir: Path = Path("data")
    docs_dir: Path = Path("docs")
    db_path: Path = Path("data/data_ghost.db")

    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_default_model: str = Field(default="mock-default", alias="LLM_DEFAULT_MODEL")
    llm_cheap_model: str = Field(default="mock-cheap", alias="LLM_CHEAP_MODEL")
    llm_expensive_model: str = Field(default="mock-expensive", alias="LLM_EXPENSIVE_MODEL")

    llm_openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_stt_model: str = Field(default="gpt-4o-mini-transcribe", alias="OPENAI_STT_MODEL")

    llm_price_prompt_per_1k: float = 0.001
    llm_price_completion_per_1k: float = 0.002

    query_timeout_seconds: float = 5.0
    query_max_rows: int = 5000
    query_max_per_request: int = 10

    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 100
    rag_top_k: int = 5

    elevenlabs_api_key: str | None = Field(default=None, alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str | None = Field(default=None, alias="ELEVENLABS_VOICE_ID")
    elevenlabs_model_id: str = Field(default="eleven_multilingual_v2", alias="ELEVENLABS_MODEL_ID")
    elevenlabs_output_format: str = Field(default="mp3_44100_128", alias="ELEVENLABS_OUTPUT_FORMAT")
    voice_max_upload_mb: int = Field(default=15, alias="VOICE_MAX_UPLOAD_MB")
    voice_max_tts_chars: int = Field(default=3000, alias="VOICE_MAX_TTS_CHARS")

    max_upload_mb: int = 20
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_origin_regex: str | None = Field(default=None, alias="CORS_ALLOW_ORIGIN_REGEX")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _parse_cors_allow_origins(cls, value):
        if value is None:
            return value
        if isinstance(value, str):
            parsed = value.strip()
            if not parsed:
                return []
            if parsed.startswith("["):
                try:
                    loaded = json.loads(parsed)
                    if isinstance(loaded, list):
                        return [str(item).strip() for item in loaded if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in parsed.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
