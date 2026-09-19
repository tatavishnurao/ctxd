from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CTXD_", env_file=".env", extra="ignore")

    app_name: str = "ctxd"
    environment: str = "development"
    log_level: str = "INFO"
    service_version: str = "0.1.0"

    database_url: str = Field(
        default="postgresql://ctxd:ctxd@localhost:5432/ctxd",
        description="PostgreSQL connection string. pgvector is expected in production.",
    )
    redis_url: str = "redis://localhost:6379/0"

    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
