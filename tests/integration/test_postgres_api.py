"""Every retrieval mode through the API on PostgreSQL + exact pgvector."""

import os
from collections.abc import Iterator

import psycopg
import pytest
from ctxd.app.main import create_app
from ctxd.app.storage.postgres import PostgresDocumentStore
from fastapi.testclient import TestClient

DATABASE_URL = os.getenv("CTXD_TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not DATABASE_URL, reason="CTXD_TEST_DATABASE_URL is not configured"),
]

DOCUMENTS = {
    "cache.md": "# Cache\n\nThe cache evicts least recently used entries under memory pressure.",
    "auth.md": "# Auth\n\nTokens rotate signing keys every seven days.",
}


@pytest.fixture
def client() -> Iterator[TestClient]:
    assert DATABASE_URL is not None
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        connection.execute(
            "TRUNCATE chunk_embeddings, lexical_postings, lexical_terms, "
            "lexical_corpus_stats, chunks, documents"
        )
    store = PostgresDocumentStore(DATABASE_URL, pool_min_size=1, pool_max_size=4)
    with TestClient(create_app(store)) as test_client:
        for path, content in DOCUMENTS.items():
            response = test_client.post(
                "/v1/documents",
                headers={"x-tenant-id": "t"},
                json={
                    "tenant_id": "t",
                    "source_path": path,
                    "source_type": "markdown",
                    "content": content,
                },
            )
            assert response.status_code == 201
        yield test_client


@pytest.mark.parametrize("mode", ["lexical", "semantic", "hybrid"])
def test_every_retrieval_mode_on_postgres(client: TestClient, mode: str) -> None:
    response = client.post(
        "/v1/query",
        headers={"x-tenant-id": "t"},
        json={"tenant_id": "t", "query": "cache memory", "retrieval_mode": mode},
    )
    assert response.status_code == 200
    context = response.json()["context"]
    assert context["metadata"]["requested_mode"] == mode
    assert context["metadata"]["retrieval_type"] == mode
    assert context["candidates"][0]["metadata"]["source_path"] == "cache.md"


def test_semantic_isolation_and_statistics_on_postgres(client: TestClient) -> None:
    other = client.post(
        "/v1/query",
        headers={"x-tenant-id": "other"},
        json={"tenant_id": "other", "query": "cache memory", "retrieval_mode": "hybrid"},
    )
    assert other.status_code == 200
    assert other.json()["context"]["candidates"] == []
    assert other.json()["context"]["metadata"]["retrieval_type"] == "none"

    stats = client.get("/v1/index/semantic-statistics", headers={"x-tenant-id": "t"}).json()
    assert stats["indexed_chunks"] == 2
    assert stats["stale_chunks"] == 0
