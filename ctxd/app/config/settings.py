from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RetrievalModeName = Literal["lexical", "semantic", "hybrid"]


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
    embedding_provider: Literal["fake", "model2vec"] = "fake"
    embedding_version: str = "fake-hash-v1"
    embedding_dimension: int = Field(default=128, gt=0)
    embedding_batch_size: int = Field(default=256, gt=0)
    embedding_cache_dir: str | None = None
    embedding_offline: bool = False
    # Persisting fake hash vectors makes the stored corpus look semantically
    # indexed when it is not, so PostgreSQL + fake requires explicit opt-in.
    allow_fake_embeddings: bool = False

    # None resolves to hybrid with a real embedding model and lexical otherwise.
    default_retrieval_mode: RetrievalModeName | None = None
    request_deadline_ms: int = Field(default=10_000, gt=0)
    max_document_chars: int = Field(default=2_000_000, gt=0)

    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str | None = None

    @model_validator(mode="after")
    def _reject_misleading_combinations(self) -> "Settings":
        if (
            self.storage_backend == "postgres"
            and self.embedding_provider == "fake"
            and not self.allow_fake_embeddings
        ):
            raise ValueError(
                "storage_backend=postgres with embedding_provider=fake would persist "
                "non-semantic hash vectors; set CTXD_EMBEDDING_PROVIDER=model2vec, or "
                "CTXD_ALLOW_FAKE_EMBEDDINGS=true for fixtures"
            )
        if self.request_deadline_ms <= self.database_query_timeout_ms:
            raise ValueError("request_deadline_ms must exceed database_query_timeout_ms")
        return self

    @property
    def resolved_retrieval_mode(self) -> RetrievalModeName:
        if self.default_retrieval_mode is not None:
            return self.default_retrieval_mode
        return "hybrid" if self.embedding_provider == "model2vec" else "lexical"

    def effective_configuration(self) -> dict[str, Any]:
        """Non-secret settings that decide which retrieval path actually runs."""
        return {
            "environment": self.environment,
            "storage_backend": self.storage_backend,
            "embedding_provider": self.embedding_provider,
            "embedding_semantic": self.embedding_provider != "fake",
            "default_retrieval_mode": self.resolved_retrieval_mode,
            "request_deadline_ms": self.request_deadline_ms,
            "database_query_timeout_ms": self.database_query_timeout_ms,
            "max_document_chars": self.max_document_chars,
            "embedding_offline": self.embedding_offline,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
