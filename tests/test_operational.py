"""Configuration validation, readiness, deadlines, failure mapping and telemetry bounds."""

import json
import logging
import time
from collections.abc import Sequence

import pytest
from ctxd.app.config.settings import Settings
from ctxd.app.main import create_app
from ctxd.app.models.domain import ContextCandidate
from ctxd.app.observability.logging import JsonFormatter, request_id_var
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.semantic import (
    FakeHashEmbeddingProvider,
    SemanticRetriever,
    SemanticSearchResult,
)
from ctxd.app.runtime import create_runtime
from ctxd.app.storage.documents import InMemoryDocumentStore
from ctxd.app.storage.errors import RetrievalTimeoutError, StorageUnavailableError
from fastapi.testclient import TestClient
from pydantic import ValidationError

HEADERS = {"x-tenant-id": "t"}


def document(content: str = "The cache evicts entries under memory pressure.") -> dict[str, str]:
    return {
        "tenant_id": "t",
        "source_path": "cache.md",
        "source_type": "markdown",
        "content": content,
    }


# --- C2: configuration validation and effective-config banner ------------------------


def test_postgres_with_fake_embeddings_is_refused_without_opt_in() -> None:
    with pytest.raises(ValidationError, match="CTXD_ALLOW_FAKE_EMBEDDINGS"):
        Settings(storage_backend="postgres", embedding_provider="fake")
    allowed = Settings(storage_backend="postgres", allow_fake_embeddings=True)
    assert allowed.effective_configuration()["embedding_semantic"] is False


def test_postgres_fake_refusal_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CTXD_STORAGE_BACKEND", "postgres")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.setenv("CTXD_ALLOW_FAKE_EMBEDDINGS", "true")
    assert Settings().storage_backend == "postgres"


def test_deadline_must_exceed_database_query_timeout() -> None:
    with pytest.raises(ValidationError, match="request_deadline_ms"):
        Settings(request_deadline_ms=5_000, database_query_timeout_ms=5_000)


def test_effective_configuration_is_logged_as_structured_fields() -> None:
    record = logging.LogRecord(
        "ctxd", logging.INFO, __file__, 1, "effective_configuration", (), None
    )
    record.fields = Settings().effective_configuration()
    payload = json.loads(JsonFormatter().format(record))
    assert payload["fields"]["storage_backend"] == "memory"
    assert payload["fields"]["embedding_semantic"] is False
    assert payload["fields"]["default_retrieval_mode"] == "lexical"


# --- C3: server-side default retrieval mode -----------------------------------------


def test_default_mode_resolves_hybrid_only_with_a_real_model() -> None:
    assert Settings().resolved_retrieval_mode == "lexical"
    assert Settings(embedding_provider="model2vec").resolved_retrieval_mode == "hybrid"
    assert (
        Settings(
            embedding_provider="model2vec", default_retrieval_mode="lexical"
        ).resolved_retrieval_mode
        == "lexical"
    )


def test_query_without_mode_uses_server_default() -> None:
    store = InMemoryDocumentStore()
    app = create_app(store)
    app.state.services = create_runtime(store, Settings(default_retrieval_mode="hybrid"))
    client = TestClient(app)
    assert client.post("/v1/documents", headers=HEADERS, json=document()).status_code == 201
    response = client.post("/v1/query", headers=HEADERS, json={"tenant_id": "t", "query": "cache"})
    assert response.json()["context"]["metadata"]["requested_mode"] == "hybrid"
    assert response.json()["context"]["metadata"]["retrieval_type"] == "hybrid"


# --- C4: readiness, deadline, ingest limits, embedder failures ----------------------


class BrokenEmbedder(FakeHashEmbeddingProvider):
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise OSError("model artifact missing")


def broken_model_client() -> TestClient:
    store = InMemoryDocumentStore()
    app = create_app(store)
    services = create_runtime(store, Settings())
    services.semantic_retriever.model = BrokenEmbedder()
    services.ingestion.embedding_model = BrokenEmbedder()
    app.state.services = services
    return TestClient(app)


def test_ready_reports_ok_when_storage_and_model_respond() -> None:
    response = TestClient(create_app(InMemoryDocumentStore())).get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"storage": "ok", "embedding_model": "ok"},
    }


def test_ready_is_503_when_embedding_model_fails() -> None:
    response = broken_model_client().get("/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["embedding_model"] == "EmbeddingError"


def test_ready_is_503_when_storage_ping_fails() -> None:
    class DownStore(InMemoryDocumentStore):
        def ping(self) -> None:
            raise StorageUnavailableError("down")

    response = TestClient(create_app(DownStore())).get("/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["storage"] == "StorageUnavailableError"


def test_embedder_failures_map_to_503_for_ingest_and_query() -> None:
    client = broken_model_client()
    ingest = client.post("/v1/documents", headers=HEADERS, json=document())
    assert ingest.status_code == 503
    assert ingest.json()["detail"] == "embedding model is unavailable"
    query = client.post(
        "/v1/query",
        headers=HEADERS,
        json={"tenant_id": "t", "query": "cache", "retrieval_mode": "semantic"},
    )
    assert query.status_code == 503


def test_oversized_document_is_rejected_with_413() -> None:
    store = InMemoryDocumentStore()
    app = create_app(store)
    app.state.services = create_runtime(store, Settings(max_document_chars=10))
    response = TestClient(app).post("/v1/documents", headers=HEADERS, json=document("x" * 11))
    assert response.status_code == 413
    assert store.get_document("cache.md", "t") is None


class SlowSemantic(SemanticRetriever):
    def search_detailed(self, query: str, tenant_id: str, top_k: int) -> SemanticSearchResult:
        time.sleep(1.0)
        return SemanticSearchResult([])


def test_hybrid_deadline_raises_timeout_without_waiting_for_slow_branch() -> None:
    store = InMemoryDocumentStore()
    services = create_runtime(store, Settings())
    slow = HybridRetriever(services.retriever, SlowSemantic(store, FakeHashEmbeddingProvider()))
    started = time.perf_counter()
    with pytest.raises(RetrievalTimeoutError):
        slow.search_detailed("cache", "t", 5, timeout=0.05)
    assert time.perf_counter() - started < 0.5


def test_request_deadline_maps_to_504() -> None:
    store = InMemoryDocumentStore()
    app = create_app(store)
    services = create_runtime(store, Settings())
    assert services.assembler.hybrid is not None
    services.assembler.hybrid.semantic = SlowSemantic(store, FakeHashEmbeddingProvider())
    app.state.services = type(services)(**{**services.__dict__, "request_deadline_seconds": 0.05})
    response = TestClient(app).post(
        "/v1/query",
        headers=HEADERS,
        json={"tenant_id": "t", "query": "cache", "retrieval_mode": "hybrid"},
    )
    assert response.status_code == 504


# --- C5: context propagation and bounded metric labels -------------------------------


def test_hybrid_branches_inherit_request_context() -> None:
    seen: list[str | None] = []

    class Recorder:
        def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]:
            seen.append(request_id_var.get())
            return []

    class RecordingSemantic(SemanticRetriever):
        def search_detailed(self, query: str, tenant_id: str, top_k: int) -> SemanticSearchResult:
            seen.append(request_id_var.get())
            return SemanticSearchResult([])

    store = InMemoryDocumentStore()
    retriever = HybridRetriever(Recorder(), RecordingSemantic(store, FakeHashEmbeddingProvider()))
    token = request_id_var.set("req-propagated")
    try:
        retriever.search("anything", "t", 3)
    finally:
        request_id_var.reset(token)
    assert seen == ["req-propagated", "req-propagated"]


def test_metric_path_label_uses_route_template_not_raw_url() -> None:
    client = TestClient(create_app(InMemoryDocumentStore()))
    client.get("/scanner-probe-8f2c1")
    client.get("/health")
    metrics = client.get("/metrics").text
    assert "scanner-probe-8f2c1" not in metrics
    assert 'path="unmatched"' in metrics
    assert 'path="/health"' in metrics


def test_retrieval_mode_errors_are_counted() -> None:
    client = broken_model_client()
    client.post(
        "/v1/query",
        headers=HEADERS,
        json={"tenant_id": "t", "query": "cache", "retrieval_mode": "semantic"},
    )
    metrics = client.get("/metrics").text
    assert 'ctxd_retrieval_mode_requests_total{mode="semantic",status="error"}' in metrics
