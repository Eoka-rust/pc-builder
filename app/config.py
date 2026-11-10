from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфиг сервиса. Значения читаются из окружения и из .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PC Builder API"
    app_version: str = Field(default="0.0.0-dev")

    database_url: str = "postgresql+psycopg://pcbuilder:pcbuilder@localhost:5432/pcbuilder"
    db_echo: bool = False

    seed_on_start: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
