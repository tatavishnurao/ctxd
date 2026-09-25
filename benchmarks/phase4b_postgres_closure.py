"""Phase 4B PostgreSQL exact-vector closure benchmark.

This is a destructive benchmark for a dedicated database.  It measures the
production Postgres store/retrievers, not a direct-SQL microbenchmark.  HNSW is
intentionally not created here; the exact results are the decision gate.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median
from threading import Barrier
from typing import Any

import psycopg
from ctxd.app.context.assembler import ContextAssembler
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import DocumentSourceType, RetrievalMode
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever, semantic_candidate
from ctxd.app.storage.postgres import PostgresDocumentStore

DB_DEFAULT = "postgresql://ctxd:ctxd@localhost:5432/ctxd"
TENANT = "phase4b-closure"
CHUNKER = StructureAwareChunker(ChunkingConfig(target_tokens=35, max_tokens=50, overlap_tokens=0))


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * q)))]


def stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "qps": 0.0}
    return {
        "p50_ms": median(values) * 1000,
        "p95_ms": percentile(values, 0.95) * 1000,
        "p99_ms": percentile(values, 0.99) * 1000,
        "qps": len(values) / sum(values),
    }


def generated_document(index: int) -> str:
    return "\n\n".join(
        f"Document {index} section {section} describes topic_{index}_{section}. "
        f"The deterministic retrieval corpus includes marker_{index} "
        f"and category_{index % 20}. "
        "Operational guidance covers validation, recovery, monitoring, ownership, and testing."
        for section in range(12)
    )


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def reset(db: str) -> None:
    with psycopg.connect(db, autocommit=True) as c:
        c.execute(
            "TRUNCATE chunk_embeddings, lexical_postings, lexical_terms, "
            "lexical_corpus_stats, chunks, documents"
        )


def version(db: str) -> str:
    with psycopg.connect(db) as c:
        row = c.execute("SHOW server_version").fetchone()
        return str(row[0])


def queries(count: int, samples: int) -> list[str]:
    return [f"marker_{i % count} category_{i % 20}" for i in range(samples)]


def make_store(db: str, pool_max: int) -> PostgresDocumentStore:
    store = PostgresDocumentStore(
        db, pool_min_size=1, pool_max_size=pool_max, query_timeout_ms=30_000
    )
    store.start()
    return store


def ingest_corpus(db: str, documents: int, model: RealEmbeddingProvider) -> dict[str, Any]:
    reset(db)
    store = make_store(db, 32)
    embedding_times: list[float] = []
    persistence_times: list[float] = []
    total_times: list[float] = []
    lexical_only_times: list[float] = []
    chunks_total = 0
    try:
        for index in range(documents):
            started = time.perf_counter()
            document = document_from_content(
                content=generated_document(index),
                source_path=f"generated/doc-{index}.txt",
                source_type=DocumentSourceType.TEXT,
                tenant_id=TENANT,
            )
            chunks = CHUNKER.chunk(document)
            chunks_total += len(chunks)
            embed_started = time.perf_counter()
            vectors = model.embed_documents([chunk.content for chunk in chunks])
            embedding_times.append(time.perf_counter() - embed_started)
            embeddings = {
                chunk.chunk_id: vector for chunk, vector in zip(chunks, vectors, strict=True)
            }
            persist_started = time.perf_counter()
            store.replace_document(
                document, chunks, embedding_version=model.version, embeddings=embeddings
            )
            persistence_times.append(time.perf_counter() - persist_started)
            total_times.append(time.perf_counter() - started)
        # A paired no-vector write provides a measured lexical/postgres baseline.
        probe = document_from_content(
            content=generated_document(documents + 1),
            source_path="generated/lexical-probe.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id=TENANT,
        )
        probe_chunks = CHUNKER.chunk(probe)
        for _ in range(10):
            started = time.perf_counter()
            store.replace_document(probe, probe_chunks)
            lexical_only_times.append(time.perf_counter() - started)
            store.delete_document(probe.document_id, TENANT)
        return {
            "documents": documents,
            "chunks": chunks_total,
            "embedding_computation": stats(embedding_times),
            "postgres_persistence_with_embeddings": stats(persistence_times),
            "lexical_postgres_probe": stats(lexical_only_times),
            "production_ingest_total": stats(total_times),
            "chunks_per_second": chunks_total / sum(total_times),
            "documents_per_second": documents / sum(total_times),
        }
    finally:
        store.close()


def reingest_reuse(db: str, documents: int, model: RealEmbeddingProvider) -> dict[str, Any]:
    store = make_store(db, 32)
    service = IngestionService(store, CHUNKER, model)
    before = store.semantic_statistics(TENANT).indexed_chunks
    durations: list[float] = []
    skipped = 0
    recomputed = 0
    try:
        for index in range(documents):
            started = time.perf_counter()
            _, chunks, created = service.ingest_content(
                content=generated_document(index),
                source_path=f"generated/doc-{index}.txt",
                source_type=DocumentSourceType.TEXT,
                tenant_id=TENANT,
            )
            durations.append(time.perf_counter() - started)
            if not created:
                skipped += len(chunks)
            else:
                recomputed += len(chunks)
        after = store.semantic_statistics(TENANT).indexed_chunks
        return {
            "documents_replayed": documents,
            "embedded_chunks_before": before,
            "embedded_chunks_after": after,
            "skipped_embeddings": skipped,
            "recomputed_embeddings": recomputed,
            "reingestion": stats(durations),
        }
    finally:
        store.close()


def storage_audit(db: str) -> dict[str, Any]:
    with psycopg.connect(db) as c:
        rows = c.execute(
            """
            SELECT c.relname AS relation, pg_table_size(c.oid) AS table_bytes,
                   pg_indexes_size(c.oid) AS index_bytes,
                   pg_total_relation_size(c.oid) AS total_bytes
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind IN ('r','m') ORDER BY c.relname
            """
        ).fetchall()
        db_size = int(c.execute("SELECT pg_database_size(current_database())").fetchone()[0])
        counts = {
            row[0]: int(row[1])
            for row in c.execute(
                "SELECT 'chunks', count(*) FROM chunks UNION ALL "
                "SELECT 'embeddings', count(*) FROM chunk_embeddings"
            )
        }
    relation = {
        str(r[0]): {"table_bytes": int(r[1]), "index_bytes": int(r[2]), "total_bytes": int(r[3])}
        for r in rows
    }
    embeddings = relation.get("chunk_embeddings", {}).get("total_bytes", 0)
    chunks = counts.get("chunks", 0)
    return {
        "relations": relation,
        "database_bytes": db_size,
        "counts": counts,
        "bytes_per_chunk": db_size / chunks if chunks else 0,
        "bytes_per_embedding": embeddings / counts.get("embeddings", 1)
        if counts.get("embeddings")
        else 0,
        "embedding_percent_database": embeddings / db_size * 100 if db_size else 0,
        "lexical_index_bytes": sum(
            v["index_bytes"]
            for k, v in relation.items()
            if k.startswith("lexical") or k == "chunks"
        ),
        "lexical_index_percent_database": sum(
            v["index_bytes"]
            for k, v in relation.items()
            if k.startswith("lexical") or k == "chunks"
        )
        / db_size
        * 100
        if db_size
        else 0,
    }


def plans(db: str, model: RealEmbeddingProvider, tenant: str = TENANT) -> str:
    vector = "[" + ",".join(str(x) for x in model.embed_query("marker_0 category_0")) + "]"
    statement = f"""
        EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
        SELECT 1.0-(e.embedding <=> '{vector}'::vector) AS score, c.chunk_id
        FROM chunk_embeddings e JOIN chunks c USING (tenant_id, chunk_id)
        WHERE e.tenant_id='{tenant}' AND e.embedding_version='{model.version}'
          AND e.dimension=256
        ORDER BY e.embedding <=> '{vector}'::vector, c.chunk_id LIMIT 20
    """
    with psycopg.connect(db) as c:
        return "\n".join(str(row[0]) for row in c.execute(statement).fetchall())


def sequential(
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    documents: int,
    samples: int,
    warmup: int,
) -> dict[str, Any]:
    lexical, semantic = BM25Retriever(store), SemanticRetriever(store, model)
    qs = queries(documents, samples + warmup)
    for q in qs[:warmup]:
        lexical.search(q, TENANT, 10)
        semantic.search(q, TENANT, 10)
    modes: dict[str, list[float]] = {
        "lexical": [],
        "semantic": [],
        "hybrid_parallel": [],
        "hybrid_sequential": [],
        "context_assembler": [],
    }
    parallel = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=True)
    serial = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=False)
    assembler = ContextAssembler(lexical, semantic)
    for q in qs[warmup:]:
        operations = {
            "lexical": lambda q=q: lexical.search(q, TENANT, 10),
            "semantic": lambda q=q: semantic.search(q, TENANT, 10),
            "hybrid_parallel": lambda q=q: parallel.search(q, TENANT, 10),
            "hybrid_sequential": lambda q=q: serial.search(q, TENANT, 10),
            "context_assembler": lambda q=q: assembler.assemble(
                query=q,
                tenant_id=TENANT,
                top_k=10,
                max_context_tokens=1_000,
                retrieval_mode=RetrievalMode.HYBRID,
            ),
        }
        for name, operation in operations.items():
            started = time.perf_counter()
            operation()
            modes[name].append(time.perf_counter() - started)
    return {name: stats(values) for name, values in modes.items()}


def components(
    store: PostgresDocumentStore, model: RealEmbeddingProvider, documents: int, samples: int
) -> dict[str, Any]:
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, model)
    fusion = HybridRetriever(lexical, semantic, candidate_depth=20)
    qs = queries(documents, samples)
    embedding: list[float] = []
    bm25: list[float] = []
    vector: list[float] = []
    rrf: list[float] = []
    assembly: list[float] = []
    for q in qs:
        started = time.perf_counter()
        vector_query = model.embed_query(q)
        embedding.append(time.perf_counter() - started)
        started = time.perf_counter()
        lexical_candidates = lexical.search(q, TENANT, 20)
        bm25.append(time.perf_counter() - started)
        started = time.perf_counter()
        semantic_hits = store.search_semantic(vector_query, TENANT, 20, version=model.version)
        vector.append(time.perf_counter() - started)
        semantic_candidates = [semantic_candidate(hit) for hit in semantic_hits]
        started = time.perf_counter()
        fused = fusion.fuse(lexical_candidates, semantic_candidates, 10)
        rrf.append(time.perf_counter() - started)
        started = time.perf_counter()
        selected_tokens = 0
        for candidate in fused:
            if selected_tokens + candidate.token_cost <= 1_000:
                selected_tokens += candidate.token_cost
        assembly.append(time.perf_counter() - started)
    return {
        "query_embedding": stats(embedding),
        "bm25": stats(bm25),
        "vector_search_and_materialization": stats(vector),
        "rrf": stats(rrf),
        "context_assembler_selection": stats(assembly),
        "note": "vector timings include SQL row materialization and Chunk Pydantic conversion",
    }


def concurrent(
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    documents: int,
    mode: str,
    level: int,
    samples: int,
) -> dict[str, Any]:
    lexical, semantic = BM25Retriever(store), SemanticRetriever(store, model)
    retriever: Any = (
        semantic
        if mode == "semantic"
        else HybridRetriever(lexical, semantic, candidate_depth=20, parallel=True)
    )
    qs = queries(documents, samples)
    barrier = Barrier(level)

    def one(i: int) -> tuple[float, int]:
        barrier.wait()
        started = time.perf_counter()
        try:
            retriever.search(qs[i], TENANT, 10)
            return time.perf_counter() - started, 0
        except Exception:
            return time.perf_counter() - started, 1

    started = time.perf_counter()
    latencies: list[float] = []
    errors = 0
    with ThreadPoolExecutor(max_workers=level) as pool:
        futures = [pool.submit(one, i) for i in range(samples)]
        for f in as_completed(futures):
            latency, error = f.result()
            latencies.append(latency)
            errors += error
    result = stats(latencies)
    result.update(
        {
            "concurrency": level,
            "errors": errors,
            "wall_qps": samples / (time.perf_counter() - started),
            "pool_statistics": store.pool_statistics(),
        }
    )
    return result


def run_size(
    db: str,
    documents: int,
    model: RealEmbeddingProvider,
    samples: int,
    concurrency_samples: int,
    levels: list[int],
    pool_max: int,
) -> dict[str, Any]:
    ingestion = ingest_corpus(db, documents, model)
    reuse = reingest_reuse(db, documents, model)
    store = make_store(db, pool_max)
    try:
        sizes = {
            "documents": documents,
            "chunks": store.lexical_statistics(TENANT).indexed_chunks,
            "average_chunk_length": store.lexical_statistics(TENANT).average_chunk_length,
            "vocabulary_size": store.lexical_statistics(TENANT).vocabulary_size,
            "embedding_dimension": model.dimension,
        }
        result: dict[str, Any] = {
            "corpus": sizes,
            "ingestion": ingestion,
            "reingestion": reuse,
            "sequential": sequential(store, model, documents, samples, 20),
            "components": components(store, model, documents, samples),
            "concurrency": {
                mode: {
                    str(level): concurrent(
                        store, model, documents, mode, level, concurrency_samples
                    )
                    for level in levels
                }
                for mode in ("semantic", "hybrid")
            },
            "storage": storage_audit(db),
            "query_plan": plans(db, model),
        }
        return result
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("CTXD_DATABASE_URL", DB_DEFAULT))
    parser.add_argument("--document-counts", type=int, nargs="+", default=[100, 1000, 4167])
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--concurrency-samples", type=int, default=160)
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 4, 8, 16, 32])
    parser.add_argument(
        "--output", type=Path, default=Path("benchmarks/phase4b_postgres_exact.json")
    )
    args = parser.parse_args()
    model = RealEmbeddingProvider()
    result: dict[str, Any] = {
        "python_version": sys.version.split()[0],
        "postgresql_version": version(args.database_url),
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "commit": git_commit(),
        "model_version": model.version,
        "embedding_dimension": model.dimension,
        "normalized": model.normalized,
        "similarity": model.distance_metric,
        "warmups": 20,
        "samples": args.samples,
        "concurrency_samples": args.concurrency_samples,
        "pool_max": 32,
        "methodology": (
            "Production PostgresDocumentStore, BM25Retriever, SemanticRetriever, "
            "HybridRetriever(candidate_depth=20), and ContextAssembler; exact cosine "
            "pgvector; destructive dedicated DB."
        ),
        "results": {
            str(count * 12): run_size(
                args.database_url,
                count,
                model,
                args.samples,
                args.concurrency_samples,
                args.concurrency,
                32,
            )
            for count in args.document_counts
        },
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
