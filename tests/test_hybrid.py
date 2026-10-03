"""Reciprocal-rank fusion, hybrid retrieval and semantic/hybrid API coverage."""

import pytest
from ctxd.app.config.settings import Settings
from ctxd.app.main import create_app
from ctxd.app.models.domain import ContextCandidate, DocumentSourceType, SourceType
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import FakeHashEmbeddingProvider, SemanticRetriever
from ctxd.app.runtime import create_runtime
from ctxd.app.storage.documents import InMemoryDocumentStore
from fastapi.testclient import TestClient


def candidate(source_id: str, score: float = 1.0) -> ContextCandidate:
    return ContextCandidate(
        source_id=source_id,
        source_type=SourceType.DOCUMENT,
        content=f"content {source_id}",
        token_cost=3,
        relevance_score=score,
        metadata={"origin": source_id},
    )


def hybrid(**kwargs: object) -> HybridRetriever:
    store = InMemoryDocumentStore()
    return HybridRetriever(
        BM25Retriever(store),
        SemanticRetriever(store, FakeHashEmbeddingProvider()),
        **kwargs,  # type: ignore[arg-type]
    )


# --- B1: fusion math, union, ties, depth ---------------------------------------------


def test_rrf_score_is_exact_sum_of_reciprocal_ranks() -> None:
    fused = hybrid(rrf_k=60).fuse(
        [candidate("a", 9.0), candidate("b", 5.0)],
        [candidate("b", 0.9), candidate("c", 0.8)],
        top_k=10,
    )
    scores = {item.source_id: item.relevance_score for item in fused}
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert scores["a"] == pytest.approx(1 / 61)
    assert scores["c"] == pytest.approx(1 / 62)
    assert [item.source_id for item in fused] == ["b", "a", "c"]
    assert fused[0].metadata["fused_score"] == fused[0].relevance_score


def test_rrf_union_keeps_single_branch_candidates_and_component_metadata() -> None:
    fused = hybrid().fuse([candidate("lex", 7.5)], [candidate("sem", 0.4)], top_k=10)
    by_id = {item.source_id: item.metadata for item in fused}
    assert by_id["lex"]["lexical_rank"] == 1
    assert by_id["lex"]["raw_lexical_score"] == 7.5
    assert "semantic_rank" not in by_id["lex"]
    assert by_id["sem"]["semantic_rank"] == 1
    assert by_id["sem"]["raw_vector_score"] == 0.4
    assert "lexical_rank" not in by_id["sem"]
    assert by_id["lex"]["origin"] == "lex"


def test_rrf_ties_break_by_chunk_id_regardless_of_input_order() -> None:
    first = hybrid().fuse([candidate("z")], [candidate("a")], top_k=10)
    second = hybrid().fuse([candidate("a")], [candidate("z")], top_k=10)
    assert [item.source_id for item in first] == ["a", "z"]
    assert [item.source_id for item in second] == ["a", "z"]


def test_rrf_truncates_to_top_k_after_fusion() -> None:
    lexical = [candidate(f"l{index}") for index in range(5)]
    semantic = [candidate(f"s{index}") for index in range(5)]
    assert len(hybrid().fuse(lexical, semantic, top_k=3)) == 3
    assert hybrid().fuse([], [], top_k=3) == []


@pytest.mark.parametrize(
    ("top_k", "expected"), [(1, 2), (10, 20), (50, 100), (60, 100), (100, 100)]
)
def test_default_depth_formula(top_k: int, expected: int) -> None:
    assert hybrid().depth(top_k) == expected


def test_explicit_candidate_depth_overrides_formula() -> None:
    assert hybrid(candidate_depth=7).depth(10) == 7


@pytest.mark.parametrize("kwargs", [{"rrf_k": 0}, {"candidate_depth": 0}])
def test_invalid_hybrid_configuration_is_rejected(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        hybrid(**kwargs)


def test_parallel_and_sequential_hybrid_are_identical_and_deterministic() -> None:
    services = create_runtime(InMemoryDocumentStore(), Settings())
    for index in range(6):
        services.ingestion.ingest_content(
            content=f"Document {index} covers cache eviction and token budgets {index}.",
            source_path=f"doc-{index}.md",
            source_type=DocumentSourceType.MARKDOWN,
            tenant_id="t",
        )
    lexical, semantic = services.retriever, services.semantic_retriever
    parallel = HybridRetriever(lexical, semantic, parallel=True)
    sequential = HybridRetriever(lexical, semantic, parallel=False)
    query = "cache eviction budgets"
    first = parallel.search(query, "t", 4)
    assert first == sequential.search(query, "t", 4)
    assert first == parallel.search(query, "t", 4)
    detailed = parallel.search_detailed(query, "t", 4)
    assert detailed.lexical_count == 6
    assert detailed.semantic_count == 6


# --- B2: semantic and hybrid through the API -----------------------------------------


def client_with_corpus() -> TestClient:
    client = TestClient(create_app(InMemoryDocumentStore()))
    for path, content in {
        "cache.md": "# Cache\n\nThe cache evicts least recently used entries on memory pressure.",
        "auth.md": "# Auth\n\nTokens rotate signing keys every seven days.",
    }.items():
        response = client.post(
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
    return client


@pytest.mark.parametrize("mode", ["lexical", "semantic", "hybrid"])
def test_every_retrieval_mode_through_the_api(mode: str) -> None:
    client = client_with_corpus()
    response = client.post(
        "/v1/query",
        headers={"x-tenant-id": "t"},
        json={"tenant_id": "t", "query": "cache memory", "retrieval_mode": mode},
    )
    assert response.status_code == 200
    metadata = response.json()["context"]["metadata"]
    assert metadata["requested_mode"] == mode
    assert metadata["retrieval_type"] == mode
    candidates = response.json()["context"]["candidates"]
    assert candidates[0]["metadata"]["source_path"] == "cache.md"
    if mode == "hybrid":
        assert "fused_score" in candidates[0]["metadata"]


def test_semantic_statistics_endpoint_reports_configured_version() -> None:
    client = client_with_corpus()
    response = client.get("/v1/index/semantic-statistics", headers={"x-tenant-id": "t"})
    assert response.status_code == 200
    body = response.json()
    assert body["embedding_version"] == Settings().embedding_version
    assert body["indexed_chunks"] == 2
    assert body["stale_chunks"] == 0


# --- B3: version mismatch through the API --------------------------------------------


def test_api_reports_embedding_version_mismatch_and_recovers_on_reingest() -> None:
    store = InMemoryDocumentStore()
    app = create_app(store)
    client = TestClient(app)
    document = {
        "tenant_id": "t",
        "source_path": "cache.md",
        "source_type": "markdown",
        "content": "# Cache\n\nThe cache evicts entries under memory pressure.",
    }
    headers = {"x-tenant-id": "t"}
    assert client.post("/v1/documents", headers=headers, json=document).status_code == 201

    app.state.services = create_runtime(store, Settings(embedding_version="fake-hash-v2"))
    query = {"tenant_id": "t", "query": "cache memory", "retrieval_mode": "hybrid"}
    stale = client.post("/v1/query", headers=headers, json=query).json()["context"]["metadata"]
    assert stale["retrieval_type"] == "lexical"
    assert stale["warnings"] == ["embedding_version_mismatch"]

    assert client.post("/v1/documents", headers=headers, json=document).status_code == 200
    fresh = client.post("/v1/query", headers=headers, json=query).json()["context"]["metadata"]
    assert fresh["retrieval_type"] == "hybrid"
    assert "warnings" not in fresh
