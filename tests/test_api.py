from types import SimpleNamespace

from ctxd.app.main import create_app
from ctxd.app.storage.errors import RetrievalTimeoutError, StorageUnavailableError
from fastapi.testclient import TestClient


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get(
        "/health",
        headers={"x-request-id": "req-test", "x-tenant-id": "tenant-a"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "req-test"
    assert "x-trace-id" in response.headers


def test_ingestion_and_query_api_return_real_context() -> None:
    client = TestClient(create_app())
    headers = {"x-request-id": "req-query", "x-tenant-id": "tenant-a"}
    ingestion = client.post(
        "/v1/documents",
        headers=headers,
        json={
            "tenant_id": "tenant-a",
            "source_path": "docs/ctxd.md",
            "source_type": "markdown",
            "content": "# ctxd\n\nThe nebula runtime assembles deterministic context packets.",
            "metadata": {"owner": "platform"},
        },
    )
    assert ingestion.status_code == 201
    ingested = ingestion.json()
    assert ingested["created"] is True
    assert ingested["chunks"]

    response = client.post(
        "/v1/query",
        headers=headers,
        json={
            "query": "nebula deterministic context",
            "tenant_id": "tenant-a",
            "task_type": "qa",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-query"
    assert len(body["context"]["candidates"]) == 1
    candidate = body["context"]["candidates"][0]
    assert candidate["metadata"]["source_path"] == "docs/ctxd.md"
    assert candidate["source_type"] == "document"
    assert body["context"]["metadata"]["retrieval_type"] == "lexical"
    assert body["model_decision"] is None
    assert body["answer"] == "Inference is not implemented yet."

    statistics = client.get("/v1/index/statistics", headers=headers)
    assert statistics.status_code == 200
    assert statistics.json()["indexed_documents"] == 1
    assert statistics.json()["indexed_chunks"] == 1
    assert statistics.json()["vocabulary_size"] > 0


def test_identical_api_reingestion_is_idempotent() -> None:
    client = TestClient(create_app())
    headers = {"x-tenant-id": "tenant-a"}
    payload = {
        "tenant_id": "tenant-a",
        "source_path": "same.txt",
        "source_type": "text",
        "content": "identical content",
    }
    first = client.post("/v1/documents", headers=headers, json=payload)
    second = client.post("/v1/documents", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert first.json()["chunks"] == second.json()["chunks"]


def test_api_rejects_tenant_override_and_never_leaks_other_tenant() -> None:
    client = TestClient(create_app())
    shared = "shared overlapping words private marker"
    for tenant in ("tenant-a", "tenant-b"):
        response = client.post(
            "/v1/documents",
            headers={"x-tenant-id": tenant},
            json={
                "tenant_id": tenant,
                "source_path": f"{tenant}.txt",
                "source_type": "text",
                "content": f"{shared} {tenant}",
            },
        )
        assert response.status_code == 201

    mismatch = client.post(
        "/v1/query",
        headers={"x-tenant-id": "tenant-a"},
        json={"tenant_id": "tenant-b", "query": shared},
    )
    assert mismatch.status_code == 403

    response = client.post(
        "/v1/query",
        headers={"x-tenant-id": "tenant-a"},
        json={"tenant_id": "tenant-a", "query": shared},
    )
    candidates = response.json()["context"]["candidates"]
    paths = {candidate["metadata"]["source_path"] for candidate in candidates}
    assert paths == {"tenant-a.txt"}


def test_ingestion_rejects_empty_content_and_missing_tenant_header() -> None:
    client = TestClient(create_app())
    payload = {
        "tenant_id": "tenant-a",
        "source_path": "empty.txt",
        "source_type": "text",
        "content": "   ",
    }
    empty_response = client.post(
        "/v1/documents", headers={"x-tenant-id": "tenant-a"}, json=payload
    )
    assert empty_response.status_code == 422
    payload["content"] = "valid"
    assert client.post("/v1/documents", json=payload).status_code == 400


def test_query_distinguishes_timeout_and_unavailable_from_empty_results() -> None:
    class FailingAssembler:
        def __init__(self, error: Exception) -> None:
            self.error = error

        def assemble(self, **_: object) -> None:
            raise self.error

    app = create_app()
    client = TestClient(app)
    payload = {"tenant_id": "tenant-a", "query": "anything"}
    headers = {"x-tenant-id": "tenant-a"}

    app.state.services = SimpleNamespace(
        assembler=FailingAssembler(RetrievalTimeoutError("timeout"))
    )
    assert client.post("/v1/query", headers=headers, json=payload).status_code == 504

    app.state.services = SimpleNamespace(
        assembler=FailingAssembler(StorageUnavailableError("unavailable"))
    )
    assert client.post("/v1/query", headers=headers, json=payload).status_code == 503


def test_metrics_endpoint_contains_phase_two_metrics() -> None:
    client = TestClient(create_app())
    response = client.get("/metrics")
    assert response.status_code == 200
    for metric in (
        "ctxd_requests_total",
        "ctxd_ingested_documents_total",
        "ctxd_ingested_chunks_total",
        "ctxd_retrieval_requests_total",
        "ctxd_retrieval_latency_seconds",
        "ctxd_retrieval_candidates_returned",
        "ctxd_context_tokens_selected",
        "ctxd_context_candidates_dropped_total",
        "ctxd_database_operation_latency_seconds",
        "ctxd_lexical_index_update_latency_seconds",
        "ctxd_lexical_search_latency_seconds",
    ):
        assert metric in response.text
