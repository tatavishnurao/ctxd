import pytest
from ctxd.app.context.assembler import ContextAssembler
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import DocumentSourceType, SourceType
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.storage.documents import InMemoryDocumentStore


def indexed_runtime() -> tuple[IngestionService, BM25Retriever]:
    store = InMemoryDocumentStore()
    ingestion = IngestionService(
        store,
        StructureAwareChunker(ChunkingConfig(target_tokens=20, max_tokens=30, overlap_tokens=0)),
    )
    return ingestion, BM25Retriever(store)


def ingest(ingestion: IngestionService, tenant: str, path: str, content: str) -> None:
    ingestion.ingest_content(
        content=content,
        source_path=path,
        source_type=DocumentSourceType.TEXT,
        tenant_id=tenant,
    )


def test_bm25_ranks_more_specific_match_first_and_preserves_provenance() -> None:
    ingestion, retriever = indexed_runtime()
    ingest(ingestion, "tenant-a", "specific.txt", "quasar quasar quasar telescope astronomy")
    ingest(ingestion, "tenant-a", "weak.txt", "quasar cooking recipe")
    results = retriever.search("quasar telescope", "tenant-a", 10)
    assert results[0].metadata["source_path"] == "specific.txt"
    assert results[0].source_type == SourceType.DOCUMENT
    assert results[0].source_id == results[0].metadata["chunk_id"]
    assert results[0].metadata["document_id"]
    assert results[0].relevance_score > results[1].relevance_score


def test_empty_query_returns_no_results() -> None:
    _, retriever = indexed_runtime()
    assert retriever.search("   !!!", "tenant-a", 5) == []


def test_top_k_is_enforced() -> None:
    ingestion, retriever = indexed_runtime()
    for index in range(5):
        ingest(ingestion, "tenant-a", f"{index}.txt", f"shared term item {index}")
    assert len(retriever.search("shared term", "tenant-a", 2)) == 2
    with pytest.raises(ValueError, match="positive"):
        retriever.search("shared", "tenant-a", 0)


def test_tenant_isolation_with_highly_overlapping_content() -> None:
    ingestion, retriever = indexed_runtime()
    ingest(
        ingestion,
        "tenant-a",
        "a.txt",
        "shared authentication policy common words tenant alpha secret",
    )
    ingest(
        ingestion,
        "tenant-b",
        "b.txt",
        "shared authentication policy common words tenant beta secret",
    )
    tenant_a_results = retriever.search("shared authentication policy beta secret", "tenant-a", 10)
    assert tenant_a_results
    assert {candidate.metadata["source_path"] for candidate in tenant_a_results} == {"a.txt"}
    assert all("beta" not in candidate.content for candidate in tenant_a_results)


def test_incremental_index_statistics_follow_replace_and_delete() -> None:
    ingestion, retriever = indexed_runtime()
    ingest(ingestion, "tenant-a", "first.txt", "alpha beta beta")
    first_stats = retriever.statistics("tenant-a")
    assert first_stats.indexed_documents == 1
    assert first_stats.indexed_chunks == 1
    assert first_stats.vocabulary_size == 2
    document = ingestion.store.list_chunks("tenant-a")[0].document_id

    ingest(ingestion, "tenant-a", "first.txt", "gamma delta")
    replaced_stats = retriever.statistics("tenant-a")
    assert replaced_stats.indexed_documents == 1
    assert replaced_stats.indexed_chunks == 1
    assert replaced_stats.vocabulary_size == 2
    assert retriever.search("alpha", "tenant-a", 5) == []
    assert ingestion.store.delete_document(document, "tenant-a") is True
    assert retriever.statistics("tenant-a").indexed_chunks == 0


def test_context_assembler_budget_does_not_truncate_candidates() -> None:
    ingestion, retriever = indexed_runtime()
    ingest(ingestion, "tenant-a", "large.txt", "target " + "large " * 12)
    ingest(ingestion, "tenant-a", "small.txt", "target small")
    packet = ContextAssembler(retriever).assemble(
        query="target large small",
        tenant_id="tenant-a",
        top_k=10,
        max_context_tokens=4,
    )
    assert [candidate.metadata["source_path"] for candidate in packet.candidates] == ["small.txt"]
    assert packet.context_tokens <= 4
    assert packet.metadata["retrieved_candidate_count"] == 2
    assert packet.metadata["selected_candidate_count"] == 1
    assert packet.metadata["dropped_due_to_budget"] == 1
    assert packet.metadata["retrieval_type"] == "lexical"
    assert packet.candidates[0].content == "target small"
