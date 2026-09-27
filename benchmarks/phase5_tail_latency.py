"""Reproduce and diagnose the Phase 4B 1.2k tail-latency anomaly."""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
from typing import Any

from ctxd.app.context.assembler import ContextAssembler
from ctxd.app.models.domain import RetrievalMode
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.postgres import PostgresDocumentStore
from phase4b_postgres_closure import TENANT, ingest_corpus, queries


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))]


def summary(rows: list[dict[str, float]]) -> dict[str, Any]:
    totals = [row["total_ms"] for row in rows]
    return {
        "samples": len(rows),
        "p50_ms": median(totals),
        "p90_ms": percentile(totals, 0.90),
        "p95_ms": percentile(totals, 0.95),
        "p99_ms": percentile(totals, 0.99),
        "max_ms": max(totals),
        "first_20": rows[:20],
        "slowest_20": sorted(rows, key=lambda row: row["total_ms"], reverse=True)[:20],
        "raw_total_ms": totals,
    }


def measure_variant(
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    documents: int,
    samples: int,
    warmup: int,
    *,
    preload: bool,
    disable_gc: bool,
    persistent_executor: bool,
) -> dict[str, Any]:
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, model)
    fusion = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=False)
    workload = queries(documents, samples + warmup)
    if preload:
        for query in workload[:100]:
            model.embed_query(query)
    for query in workload[:warmup]:
        lexical.search(query, TENANT, 20)
        semantic.search(query, TENANT, 20)
    rows: list[dict[str, float]] = []
    executor = ThreadPoolExecutor(max_workers=2) if persistent_executor else None
    was_enabled = gc.isenabled()
    if disable_gc:
        gc.disable()
    try:
        for index, query in enumerate(workload[warmup:]):
            total_started = time.perf_counter()
            component: dict[str, float] = {"query_index": float(index)}

            def lexical_work(active_query: str = query) -> tuple[list[Any], float]:
                started = time.perf_counter()
                result = lexical.search(active_query, TENANT, 20)
                return result, (time.perf_counter() - started) * 1000

            def semantic_work(active_query: str = query) -> tuple[list[Any], float, float]:
                from ctxd.app.retrieval.semantic import semantic_candidate

                started = time.perf_counter()
                vector = model.embed_query(active_query)
                embedding_ms = (time.perf_counter() - started) * 1000
                started = time.perf_counter()
                hits = store.search_semantic(vector, TENANT, 20, version=model.version)
                search_ms = (time.perf_counter() - started) * 1000
                return [semantic_candidate(hit) for hit in hits], embedding_ms, search_ms

            if executor is None:
                with ThreadPoolExecutor(max_workers=2) as query_executor:
                    lexical_future = query_executor.submit(lexical_work)
                    semantic_future = query_executor.submit(semantic_work)
                    lexical_candidates, component["bm25_ms"] = lexical_future.result()
                    (
                        semantic_candidates,
                        component["query_embedding_ms"],
                        component["vector_search_materialization_ms"],
                    ) = semantic_future.result()
            else:
                lexical_future = executor.submit(lexical_work)
                semantic_future = executor.submit(semantic_work)
                lexical_candidates, component["bm25_ms"] = lexical_future.result()
                (
                    semantic_candidates,
                    component["query_embedding_ms"],
                    component["vector_search_materialization_ms"],
                ) = semantic_future.result()
            started = time.perf_counter()
            fused = fusion.fuse(lexical_candidates, semantic_candidates, 10)
            component["rrf_ms"] = (time.perf_counter() - started) * 1000
            started = time.perf_counter()
            selected_tokens = 0
            for candidate in fused:
                if selected_tokens + candidate.token_cost <= 1_000:
                    selected_tokens += candidate.token_cost
            component["context_assembler_ms"] = (time.perf_counter() - started) * 1000
            component["total_ms"] = (time.perf_counter() - total_started) * 1000
            rows.append(component)
    finally:
        if executor is not None:
            executor.shutdown()
        if disable_gc and was_enabled:
            gc.enable()
    return summary(rows)


def reproduce_phase4_sequence(
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    documents: int,
    samples: int,
) -> dict[str, Any]:
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, model)
    parallel = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=True)
    sequential = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=False)
    assembler = ContextAssembler(lexical, semantic)
    workload = queries(documents, samples + 20)
    for query in workload[:20]:
        lexical.search(query, TENANT, 10)
        semantic.search(query, TENANT, 10)
    names = ("lexical", "semantic", "hybrid_parallel", "hybrid_sequential", "assembler")
    values: dict[str, list[dict[str, float]]] = {name: [] for name in names}
    for index, query in enumerate(workload[20:]):
        operations = (
            ("lexical", lambda query=query: lexical.search(query, TENANT, 10)),
            ("semantic", lambda query=query: semantic.search(query, TENANT, 10)),
            ("hybrid_parallel", lambda query=query: parallel.search(query, TENANT, 10)),
            ("hybrid_sequential", lambda query=query: sequential.search(query, TENANT, 10)),
            (
                "assembler",
                lambda query=query: assembler.assemble(
                    query=query,
                    tenant_id=TENANT,
                    top_k=10,
                    max_context_tokens=1_000,
                    retrieval_mode=RetrievalMode.HYBRID,
                ),
            ),
        )
        for name, operation in operations:
            started = time.perf_counter()
            operation()
            values[name].append(
                {"query_index": float(index), "total_ms": (time.perf_counter() - started) * 1000}
            )
    return {name: summary(rows) for name, rows in values.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url",
        default=os.getenv("CTXD_DATABASE_URL", "postgresql://ctxd:ctxd@localhost:5432/ctxd"),
    )
    parser.add_argument("--document-counts", type=int, nargs="+", default=[100, 1000])
    parser.add_argument("--samples", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/phase5_tail_latency.json"))
    args = parser.parse_args()
    model = RealEmbeddingProvider()
    result: dict[str, Any] = {
        "platform": platform.platform(),
        "model": model.version,
        "methodology": (
            "Per-query production BM25 and exact Postgres vector retrieval with explicit "
            "component timing. Persistent executor is diagnostic only."
        ),
        "corpora": {},
    }
    variants = {
        "normal_warmup": dict(
            warmup=20, preload=False, disable_gc=False, persistent_executor=False
        ),
        "increased_warmup": dict(
            warmup=100, preload=False, disable_gc=False, persistent_executor=False
        ),
        "model_preloaded": dict(
            warmup=20, preload=True, disable_gc=False, persistent_executor=False
        ),
        "gc_disabled": dict(warmup=20, preload=True, disable_gc=True, persistent_executor=False),
        "persistent_hybrid_executor": dict(
            warmup=20, preload=True, disable_gc=False, persistent_executor=True
        ),
    }
    for documents in args.document_counts:
        ingestion = ingest_corpus(args.database_url, documents, model)
        store = PostgresDocumentStore(
            args.database_url, pool_min_size=1, pool_max_size=32, query_timeout_ms=30_000
        )
        store.start()
        try:
            result["corpora"][str(documents * 12)] = {
                "ingestion": ingestion,
                "phase4_sequence_reproduction": reproduce_phase4_sequence(
                    store, model, documents, args.samples
                ),
                "variants": {
                    name: measure_variant(store, model, documents, args.samples, **configuration)
                    for name, configuration in variants.items()
                },
            }
        finally:
            store.close()
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
