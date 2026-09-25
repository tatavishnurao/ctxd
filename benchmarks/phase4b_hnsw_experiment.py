"""Small, documented HNSW experiment against the 50k exact benchmark corpus.
Run only after phase4b_postgres_closure.py and on its dedicated database."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
from threading import Barrier
from typing import Any

import psycopg
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.postgres import PostgresDocumentStore

TENANT = "phase4b-closure"
VERSION = RealEmbeddingProvider.version


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))]


def summary(values: list[float]) -> dict[str, float]:
    return {
        "p50_ms": median(values) * 1000,
        "p95_ms": percentile(values, 0.95) * 1000,
        "p99_ms": percentile(values, 0.99) * 1000,
        "qps": len(values) / sum(values),
    }


def qs(samples: int) -> list[str]:
    return [f"marker_{i % 4167} category_{i % 20}" for i in range(samples)]


def storage(db: str) -> int:
    with psycopg.connect(db) as c:
        return int(c.execute("SELECT pg_relation_size('chunk_embeddings_hnsw')").fetchone()[0])


def plan(db: str, model: RealEmbeddingProvider) -> str:
    vector = "[" + ",".join(str(x) for x in model.embed_query("marker_0 category_0")) + "]"
    statement = f"""EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
    SELECT chunk_id FROM chunk_embeddings
    WHERE tenant_id='{TENANT}' AND embedding_version='{VERSION}' AND dimension=256
    ORDER BY (embedding::vector(256)) <=> '{vector}'::vector LIMIT 20"""
    with psycopg.connect(db) as c:
        return "\n".join(str(row[0]) for row in c.execute(statement).fetchall())


def run_queries(
    store: PostgresDocumentStore, model: RealEmbeddingProvider, samples: int
) -> tuple[dict[str, Any], list[list[str]]]:

    retriever = SemanticRetriever(store, model)
    latencies: list[float] = []
    results: list[list[str]] = []
    for query in qs(samples):
        started = time.perf_counter()
        hits = retriever.search(query, TENANT, 10)
        latencies.append(time.perf_counter() - started)
        results.append([hit.source_id for hit in hits])
    return summary(latencies), results


def concurrency(
    store: PostgresDocumentStore, model: RealEmbeddingProvider, level: int, samples: int
) -> dict[str, Any]:
    retriever = SemanticRetriever(store, model)
    run_samples = ((samples + level - 1) // level) * level
    queries = qs(run_samples)
    barrier = Barrier(level)

    def one(index: int) -> float:
        barrier.wait()
        started = time.perf_counter()
        retriever.search(queries[index], TENANT, 10)
        return time.perf_counter() - started

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=level) as pool:
        latencies = list(pool.map(one, range(run_samples)))
    result = summary(latencies)
    result.update(
        {
            "concurrency": level,
            "query_count": run_samples,
            "wall_qps": run_samples / (time.perf_counter() - started),
            "pool_statistics": store.pool_statistics(),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default="postgresql://ctxd:ctxd@localhost:5432/ctxd")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--ef-search", type=int, default=40)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/phase4b_hnsw.json"))
    args = parser.parse_args()
    model = RealEmbeddingProvider()
    store = PostgresDocumentStore(
        args.database_url, pool_min_size=1, pool_max_size=32, query_timeout_ms=30_000
    )
    store.start()
    try:
        # Capture exact ground truth before creating the ANN index.
        with psycopg.connect(args.database_url, autocommit=True) as c:
            c.execute("DROP INDEX IF EXISTS chunk_embeddings_hnsw")
        exact_latency, exact = run_queries(store, model, args.samples)
        exact_hybrid_retriever = HybridRetriever(
            BM25Retriever(store), SemanticRetriever(store, model), candidate_depth=20
        )
        exact_hybrid = [
            [candidate.source_id for candidate in exact_hybrid_retriever.search(query, TENANT, 10)]
            for query in qs(args.samples)
        ]
        started = time.perf_counter()
        with psycopg.connect(args.database_url, autocommit=True) as c:
            c.execute("""CREATE INDEX chunk_embeddings_hnsw ON chunk_embeddings
                        USING hnsw ((embedding::vector(256)) vector_cosine_ops)
                        WITH (m=16, ef_construction=64)""")
        build_seconds = time.perf_counter() - started
        with psycopg.connect(args.database_url, autocommit=True) as c:
            c.execute("ANALYZE chunk_embeddings")
        store.close()
        store = PostgresDocumentStore(
            args.database_url,
            pool_min_size=1,
            pool_max_size=32,
            query_timeout_ms=30_000,
            use_hnsw=True,
            hnsw_ef_search=args.ef_search,
        )
        store.start()
        ann_latency, ann = run_queries(store, model, args.samples)
        ann_hybrid_retriever = HybridRetriever(
            BM25Retriever(store), SemanticRetriever(store, model), candidate_depth=20
        )
        ann_hybrid = [
            [candidate.source_id for candidate in ann_hybrid_retriever.search(query, TENANT, 10)]
            for query in qs(args.samples)
        ]
        recalls = {
            str(k): sum(len(set(a[:k]) & set(e[:k])) / k for e, a in zip(exact, ann, strict=True))
            / len(exact)
            for k in (1, 5, 10)
        }
        # Updating an existing vector exercises index maintenance without changing corpus quality.
        update_times: list[float] = []
        vector = model.embed_query("marker_0 category_0")
        with psycopg.connect(args.database_url, autocommit=True) as c:
            for _ in range(10):
                started = time.perf_counter()
                c.execute(
                    "UPDATE chunk_embeddings SET embedding=%s::vector, updated_at=now() "
                    "WHERE tenant_id=%s AND chunk_id=(SELECT chunk_id FROM chunk_embeddings "
                    "WHERE tenant_id=%s LIMIT 1)",
                    (vector, TENANT, TENANT),
                )
                update_times.append(time.perf_counter() - started)
        result = {
            "corpus_chunks": 50004,
            "index": {
                "m": 16,
                "ef_construction": 64,
                "ef_search": args.ef_search,
                "size_bytes": storage(args.database_url),
                "build_seconds": build_seconds,
            },
            "exact": exact_latency,
            "hnsw": ann_latency,
            "ann_recall_vs_exact": recalls,
            "query_plan": plan(args.database_url, model),
            "incremental_update": summary(update_times),
            "concurrency": {
                str(level): concurrency(store, model, level, args.samples)
                for level in (1, 4, 8, 16, 32)
            },
            "hybrid_reference": {
                "hybrid_recall_vs_exact": {
                    str(k): sum(
                        len(set(a[:k]) & set(e[:k])) / k
                        for e, a in zip(exact_hybrid, ann_hybrid, strict=True)
                    )
                    / len(exact_hybrid)
                    for k in (1, 5, 10)
                },
                "note": (
                    "Synthetic marker/category queries; end-to-end semantic relevance "
                    "evaluation was not rerun because this experiment is ANN retrieval "
                    "recall, not a new quality model."
                ),
            },
        }
    finally:
        store.close()
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
