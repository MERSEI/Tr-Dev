from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")

    # OpenAI
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(None, alias="OPENAI_BASE_URL")

    # PostgreSQL
    postgres_dsn: str = Field(
        "postgresql+asyncpg://bot:bot@localhost:5432/botdb",
        alias="POSTGRES_DSN",
    )

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # Collector
    collector_provider: Literal["instagram", "mock"] = Field(
        "mock", alias="COLLECTOR_PROVIDER"
    )
    instagram_session_file: str | None = Field(None, alias="INSTAGRAM_SESSION_FILE")

    # STT
    whisper_model: str = Field("small", alias="WHISPER_MODEL")
    whisper_device: str = Field("cpu", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field("int8", alias="WHISPER_COMPUTE_TYPE")

    # OCR
    ocr_languages: list[str] = Field(["ru", "en"], alias="OCR_LANGUAGES")

    # Media storage
    media_root: Path = Field(Path("/data/media"), alias="MEDIA_ROOT")
    media_ttl_days: int = Field(7, alias="MEDIA_TTL_DAYS")

    # Cache
    cache_ttl_seconds: int = Field(3600, alias="CACHE_TTL_SECONDS")

    # Analysis window
    analysis_window_hours: int = Field(24, alias="ANALYSIS_WINDOW_HOURS")

    # Worker
    worker_concurrency: int = Field(4, alias="WORKER_CONCURRENCY")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
