"""Embedding-version idempotency and truth-in-labeling regressions.

Originally reproduced by a review probe: re-ingesting unchanged content under a
new embedding version skipped re-embedding, semantic search silently returned
nothing, and the packet was still labeled ``hybrid``.
"""

from ctxd.app.config.settings import Settings
from ctxd.app.context.assembler import executed_retrieval_type
from ctxd.app.models.domain import (
    ContextCandidate,
    ContextPacket,
    DocumentSourceType,
    RetrievalMode,
)
from ctxd.app.runtime import RuntimeServices, create_runtime
from ctxd.app.storage.documents import InMemoryDocumentStore

CONTENT = "pgvector exact cosine search over chunks."


def runtime(store: InMemoryDocumentStore, version: str) -> RuntimeServices:
    return create_runtime(store, Settings(embedding_version=version))


def ingest(services: RuntimeServices, content: str = CONTENT) -> bool:
    _, _, created = services.ingestion.ingest_content(
        content=content,
        source_path="a.md",
        source_type=DocumentSourceType.MARKDOWN,
        tenant_id="t",
    )
    return created


def hybrid(services: RuntimeServices, query: str = "cosine search") -> ContextPacket:
    return services.assembler.assemble(
        query=query,
        tenant_id="t",
        top_k=5,
        max_context_tokens=1_000,
        retrieval_mode=RetrievalMode.HYBRID,
    )


def test_reingest_under_new_version_reembeds_unchanged_content() -> None:
    store = InMemoryDocumentStore()
    assert ingest(runtime(store, "v1")) is True
    upgraded = runtime(store, "v2")

    assert ingest(upgraded) is False
    assert store.embedding_versions("t") == {"v2": 1}
    assert len(upgraded.semantic_retriever.search("cosine search", "t", 5)) == 1
    packet = hybrid(upgraded)
    assert packet.metadata["retrieval_type"] == "hybrid"
    assert packet.metadata["branch_candidate_counts"] == {"lexical": 1, "semantic": 1}
    assert "warnings" not in packet.metadata


def test_identical_reingest_under_same_version_does_not_reembed() -> None:
    store = InMemoryDocumentStore()
    services = runtime(store, "v1")
    ingest(services)
    before = dict(store._embeddings)
    assert ingest(services) is False
    assert store._embeddings == before


def test_stale_corpus_is_never_labeled_hybrid_and_reports_mismatch() -> None:
    store = InMemoryDocumentStore()
    ingest(runtime(store, "v1"))
    upgraded = runtime(store, "v2")

    packet = hybrid(upgraded)

    assert packet.metadata["requested_mode"] == "hybrid"
    assert packet.metadata["retrieval_type"] == "lexical"
    assert packet.metadata["branch_candidate_counts"] == {"lexical": 1, "semantic": 0}
    assert packet.metadata["warnings"] == ["embedding_version_mismatch"]
    assert packet.metadata["stale_embedding_chunks"] == 1
    assert packet.metadata["embedding_version"] == "v2"
    assert all("semantic_rank" not in c.metadata for c in packet.candidates)


def test_semantic_statistics_report_configured_version_and_stale_chunks() -> None:
    store = InMemoryDocumentStore()
    ingest(runtime(store, "v1"))
    stats = runtime(store, "v2").semantic_retriever.statistics("t")
    assert stats.embedding_version == "v2"
    assert stats.indexed_chunks == 0
    assert stats.stale_chunks == 1


def test_lexical_and_empty_results_are_labeled_by_what_executed() -> None:
    store = InMemoryDocumentStore()
    services = runtime(store, "v1")
    ingest(services)
    lexical = services.assembler.assemble(
        query="cosine", tenant_id="t", top_k=5, max_context_tokens=1_000
    )
    assert lexical.metadata["retrieval_type"] == "lexical"
    empty = services.assembler.assemble(
        query="nothingmatches", tenant_id="t", top_k=5, max_context_tokens=1_000
    )
    assert empty.metadata["retrieval_type"] == "none"
    assert empty.metadata["requested_mode"] == "lexical"


def test_executed_retrieval_type_names_only_contributing_branches() -> None:
    assert executed_retrieval_type({"lexical": 2, "semantic": 3}) == "hybrid"
    assert executed_retrieval_type({"lexical": 0, "semantic": 3}) == "semantic"
    assert executed_retrieval_type({"lexical": 2, "semantic": 0}) == "lexical"
    assert executed_retrieval_type({"lexical": 0, "semantic": 0}) == "none"


def test_packet_schema_has_no_uncomputed_signals() -> None:
    assert set(ContextCandidate.model_fields) == {
        "source_id",
        "source_type",
        "content",
        "token_cost",
        "relevance_score",
        "metadata",
    }
    assert "compression_ratio" not in ContextPacket.model_fields
