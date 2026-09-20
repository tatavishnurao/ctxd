from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CTXD_", env_file=".env", extra="ignore")

    app_name: str = "ctxd"
    environment: str = "development"
    log_level: str = "INFO"
    service_version: str = "0.1.0"

    storage_backend: Literal["memory", "postgres"] = "memory"
    database_url: str = Field(
        default="postgresql://ctxd:ctxd@localhost:5432/ctxd",
        description="PostgreSQL connection string used when storage_backend=postgres.",
    )
    database_pool_min_size: int = Field(default=1, ge=0)
    database_pool_max_size: int = Field(default=10, ge=1)
    database_connection_timeout_seconds: float = Field(default=5.0, gt=0)
    database_query_timeout_ms: int = Field(default=5_000, gt=0)
    embedding_version: str = "hash-v1"
    embedding_dimension: int = Field(default=128, gt=0)
    redis_url: str = "redis://localhost:6379/0"

    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
