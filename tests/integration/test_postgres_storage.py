import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import psycopg
import pytest
from ctxd.app.evals.retrieval import load_corpus, run_retrieval_eval
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import DocumentSourceType
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.storage.errors import (
    StorageDataError,
    StorageError,
    StorageUnavailableError,
)
from ctxd.app.storage.postgres import PostgresDocumentStore

DATABASE_URL = os.getenv("CTXD_TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not DATABASE_URL, reason="CTXD_TEST_DATABASE_URL is not configured"),
]


@pytest.fixture(autouse=True)
def clean_database() -> None:
    assert DATABASE_URL is not None
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        connection.execute(
            "TRUNCATE lexical_postings, lexical_terms, lexical_corpus_stats, chunks, documents"
        )


def make_store(*, pool_max_size: int = 12) -> PostgresDocumentStore:
    assert DATABASE_URL is not None
    store = PostgresDocumentStore(DATABASE_URL, pool_min_size=1, pool_max_size=pool_max_size)
    store.start()
    return store


def make_ingestion(store: PostgresDocumentStore) -> IngestionService:
    return IngestionService(
        store,
        StructureAwareChunker(ChunkingConfig(target_tokens=20, max_tokens=30, overlap_tokens=0)),
    )


def ingest(service: IngestionService, tenant: str, path: str, content: str) -> str:
    document, _, _ = service.ingest_content(
        content=content,
        source_path=path,
        source_type=DocumentSourceType.TEXT,
        tenant_id=tenant,
    )
    return document.document_id


def test_database_unavailable_at_startup_is_explicit() -> None:
    store = PostgresDocumentStore(
        "postgresql://ctxd:ctxd@127.0.0.1:1/ctxd",
        pool_min_size=1,
        pool_max_size=1,
        connection_timeout_seconds=0.1,
    )
    with pytest.raises(StorageUnavailableError):
        store.start()


def test_postgres_preserves_original_retrieval_evaluation() -> None:
    store = make_store()
    try:
        result = run_retrieval_eval(load_corpus(Path("evals/retrieval_corpus.json")), store)
        assert result.case_count == 22
        assert result.recall_at_k == pytest.approx(0.9545454545454546)
        assert result.mrr == pytest.approx(0.9545454545454546)
        assert result.ndcg_at_k == pytest.approx(0.9545454545454546)
    finally:
        store.close()


def test_restart_persistence_and_cross_runtime_visibility() -> None:
    first = make_store()
    try:
        document_id = ingest(make_ingestion(first), "tenant-a", "persistent.txt", "nebula restart")
    finally:
        first.close()

    second = make_store()
    try:
        result = BM25Retriever(second).search("nebula", "tenant-a", 5)
        assert [candidate.metadata["source_path"] for candidate in result] == ["persistent.txt"]
        assert second.get_document(document_id, "tenant-a") is not None
        assert second.lexical_statistics("tenant-a").indexed_documents == 1
    finally:
        second.close()


def test_atomic_changed_reingestion_and_idempotent_replay() -> None:
    store = make_store()
    try:
        service = make_ingestion(store)
        document, first_chunks, created = service.ingest_content(
            content="old marker paragraph",
            source_path="changing.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id="tenant-a",
        )
        replay, replay_chunks, replay_created = service.ingest_content(
            content="old marker paragraph",
            source_path="changing.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id="tenant-a",
        )
        assert created is True
        assert replay_created is False
        assert replay.document_id == document.document_id
        assert replay_chunks == first_chunks

        _, new_chunks, changed_created = service.ingest_content(
            content="new replacement marker",
            source_path="changing.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id="tenant-a",
        )
        assert changed_created is False
        assert {chunk.chunk_id for chunk in first_chunks}.isdisjoint(
            {chunk.chunk_id for chunk in new_chunks}
        )
        assert BM25Retriever(store).search("old", "tenant-a", 5) == []
        assert len(BM25Retriever(store).search("replacement", "tenant-a", 5)) == 1
        assert store.lexical_statistics("tenant-a").indexed_chunks == len(new_chunks)
    finally:
        store.close()


def test_transaction_failure_rolls_back_document_chunks_and_index() -> None:
    assert DATABASE_URL is not None
    store = make_store()
    try:
        service = make_ingestion(store)
        document_id = ingest(service, "tenant-a", "rollback.txt", "stable original marker")
        before = store.lexical_statistics("tenant-a")
        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute(
                """
                CREATE FUNCTION reject_rollback_marker() RETURNS trigger AS $$
                BEGIN
                    IF NEW.content LIKE '%ROLLBACK_MARKER%' THEN
                        RAISE EXCEPTION 'forced chunk failure';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                CREATE TRIGGER reject_rollback_chunk
                    BEFORE INSERT ON chunks
                    FOR EACH ROW EXECUTE FUNCTION reject_rollback_marker();
                """
            )
        with pytest.raises(StorageError):
            ingest(service, "tenant-a", "rollback.txt", "ROLLBACK_MARKER changed content")
        persisted = store.get_document(document_id, "tenant-a")
        assert persisted is not None
        assert persisted.content == "stable original marker"
        assert len(BM25Retriever(store).search("original", "tenant-a", 5)) == 1
        assert BM25Retriever(store).search("changed", "tenant-a", 5) == []
        assert store.lexical_statistics("tenant-a") == before
    finally:
        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute("DROP TRIGGER IF EXISTS reject_rollback_chunk ON chunks")
            connection.execute("DROP FUNCTION IF EXISTS reject_rollback_marker()")
        store.close()


def test_tenant_isolation_covers_lookup_statistics_search_and_delete() -> None:
    store = make_store()
    try:
        service = make_ingestion(store)
        a_id = ingest(service, "tenant-a", "same.txt", "shared shared alpha private")
        a_score_before = BM25Retriever(store).search("shared", "tenant-a", 1)[0].relevance_score
        b_id = ingest(service, "tenant-b", "same.txt", "shared shared beta private")
        for index in range(4):
            ingest(service, "tenant-b", f"distractor-{index}.txt", f"shared distractor {index}")

        assert store.get_document(a_id, "tenant-b") is None
        assert store.get_document(b_id, "tenant-a") is None
        a_chunks = store.list_chunks("tenant-a")
        b_chunks = store.list_chunks("tenant-b")
        assert store.get_chunk(a_chunks[0].chunk_id, "tenant-b") is None
        isolated_results = BM25Retriever(store).search("shared beta", "tenant-a", 5)
        assert all("beta" not in hit.content for hit in isolated_results)
        assert store.lexical_statistics("tenant-a").indexed_documents == 1
        assert store.lexical_statistics("tenant-b").indexed_documents == 5

        a_score = BM25Retriever(store).search("shared", "tenant-a", 1)[0].relevance_score
        b_score = BM25Retriever(store).search("shared", "tenant-b", 1)[0].relevance_score
        assert a_score == pytest.approx(a_score_before)
        assert a_score != b_score
        b_stats = store.lexical_statistics("tenant-b")
        assert store.delete_document(a_id, "tenant-a") is True
        assert store.lexical_statistics("tenant-a").indexed_chunks == 0
        assert store.lexical_statistics("tenant-b") == b_stats
        assert b_chunks == store.list_chunks("tenant-b")
    finally:
        store.close()


def test_simultaneous_ingestion_of_different_documents() -> None:
    store = make_store(pool_max_size=8)
    try:
        service = make_ingestion(store)
        barrier = Barrier(8)

        def write(index: int) -> None:
            barrier.wait()
            ingest(service, "tenant-a", f"doc-{index}.txt", f"concurrent marker_{index}")

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(write, range(8)))
        stats = store.lexical_statistics("tenant-a")
        assert stats.indexed_documents == 8
        assert stats.indexed_chunks == 8
        assert len(store.list_chunks("tenant-a")) == 8
        for index in range(8):
            assert BM25Retriever(store).search(f"marker_{index}", "tenant-a", 1)
    finally:
        store.close()


def test_simultaneous_reingestion_of_same_document_is_never_mixed() -> None:
    store = make_store(pool_max_size=8)
    try:
        service = make_ingestion(store)
        barrier = Barrier(8)
        versions = [f"version_{index} unique_{index}" for index in range(8)]

        def write(content: str) -> None:
            barrier.wait()
            ingest(service, "tenant-a", "same.txt", content)

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(write, versions))
        chunks = store.list_chunks("tenant-a")
        assert len(chunks) == 1
        document = store.get_document(chunks[0].document_id, "tenant-a")
        assert document is not None
        assert chunks[0].content == document.content
        assert document.content in versions
        stats = store.lexical_statistics("tenant-a")
        assert stats.indexed_documents == 1
        assert stats.indexed_chunks == 1
    finally:
        store.close()


def test_queries_remain_consistent_during_unrelated_ingestion() -> None:
    store = make_store(pool_max_size=8)
    try:
        service = make_ingestion(store)
        ingest(service, "tenant-a", "baseline.txt", "permanent baseline signal")
        barrier = Barrier(5)

        def read_many() -> list[str]:
            barrier.wait()
            paths = []
            for _ in range(20):
                result = BM25Retriever(store).search("permanent baseline", "tenant-a", 5)
                paths.append(str(result[0].metadata["source_path"]))
            return paths

        def write_unrelated() -> list[str]:
            barrier.wait()
            ingest(service, "tenant-a", "unrelated.txt", "other independent content")
            return []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_many) for _ in range(4)]
            futures.append(executor.submit(write_unrelated))
            observed = [path for future in futures for path in future.result()]
        assert observed and set(observed) == {"baseline.txt"}
        assert store.lexical_statistics("tenant-a").indexed_documents == 2
    finally:
        store.close()


def test_delete_query_race_has_before_or_after_semantics() -> None:
    store = make_store(pool_max_size=4)
    try:
        service = make_ingestion(store)
        document_id = ingest(service, "tenant-a", "race.txt", "race deletion marker")
        barrier = Barrier(2)

        def query_many() -> list[int]:
            barrier.wait()
            retriever = BM25Retriever(store)
            return [
                len(retriever.search("deletion marker", "tenant-a", 5))
                for _ in range(20)
            ]

        def delete() -> bool:
            barrier.wait()
            return store.delete_document(document_id, "tenant-a")

        with ThreadPoolExecutor(max_workers=2) as executor:
            query_future = executor.submit(query_many)
            delete_future = executor.submit(delete)
            counts = query_future.result()
            assert delete_future.result() is True
        assert set(counts) <= {0, 1}
        assert BM25Retriever(store).search("deletion marker", "tenant-a", 5) == []
        assert store.lexical_statistics("tenant-a").indexed_documents == 0
    finally:
        store.close()


def test_malformed_persisted_metadata_is_reported() -> None:
    assert DATABASE_URL is not None
    store = make_store()
    try:
        document_id = ingest(make_ingestion(store), "tenant-a", "bad.txt", "valid content")
        with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
            connection.execute(
                "UPDATE documents SET metadata = '[]'::jsonb WHERE tenant_id = %s",
                ("tenant-a",),
            )
        with pytest.raises(StorageDataError, match="metadata"):
            store.get_document(document_id, "tenant-a")
    finally:
        store.close()
