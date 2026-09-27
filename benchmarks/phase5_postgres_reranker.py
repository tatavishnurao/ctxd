"""Phase 5 PostgreSQL end-to-end reranker, concurrency, and goodput benchmark."""

from __future__ import annotations

import argparse
import json
import os
import resource
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median
from threading import Barrier
from typing import Any

from ctxd.app.reranking import FlashRankReranker, RerankingRetriever
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.postgres import PostgresDocumentStore
from phase4b_postgres_closure import TENANT, ingest_corpus, queries

CANDIDATES = 10
BATCH_SIZE = 8


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))]


def summary(values: list[float], elapsed: float | None = None) -> dict[str, float]:
    return {
        "p50_ms": median(values),
        "p90_ms": percentile(values, 0.90),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "qps": len(values) / (elapsed if elapsed is not None else sum(values) / 1000),
    }


def build_retrievers(
    store: PostgresDocumentStore, model: RealEmbeddingProvider, reranker: FlashRankReranker
) -> tuple[HybridRetriever, RerankingRetriever]:
    hybrid = HybridRetriever(
        BM25Retriever(store),
        SemanticRetriever(store, model),
        candidate_depth=CANDIDATES,
        parallel=True,
    )
    return hybrid, RerankingRetriever(hybrid, reranker, candidate_count=CANDIDATES)


def sequential(
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    reranker: FlashRankReranker,
    documents: int,
    samples: int,
) -> dict[str, Any]:
    hybrid, reranked = build_retrievers(store, model, reranker)
    workload = queries(documents, samples + 20)
    for query in workload[:20]:
        hybrid.search(query, TENANT, 5)
        reranked.search(query, TENANT, 5)
    output: dict[str, Any] = {}
    raw: dict[str, list[dict[str, Any]]] = {"hybrid": [], "hybrid_reranked": []}
    for mode, retriever in (("hybrid", hybrid), ("hybrid_reranked", reranked)):
        elapsed_started = time.perf_counter()
        for index, query in enumerate(workload[20:]):
            started = time.perf_counter()
            result = retriever.search(query, TENANT, 5)
            latency_ms = (time.perf_counter() - started) * 1000
            expected = f"generated/doc-{(index + 20) % documents}.txt"
            raw[mode].append(
                {
                    "query_index": index,
                    "latency_ms": latency_ms,
                    "quality_pass": any(
                        candidate.metadata.get("source_path") == expected for candidate in result
                    ),
                }
            )
        elapsed = time.perf_counter() - elapsed_started
        output[mode] = summary([row["latency_ms"] for row in raw[mode]], elapsed)
    output["raw"] = raw
    return output


def component_breakdown(
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    reranker: FlashRankReranker,
    documents: int,
    samples: int,
) -> dict[str, Any]:
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, model)
    fusion = HybridRetriever(lexical, semantic, candidate_depth=CANDIDATES, parallel=False)
    names = (
        "query_embedding",
        "bm25",
        "vector_search_materialization",
        "rrf",
        "reranker_preparation",
        "reranker_tokenization",
        "reranker_inference",
        "context_assembler",
        "total",
    )
    values: dict[str, list[float]] = {name: [] for name in names}
    for query in queries(documents, samples):
        total_started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=2) as executor:
            lexical_started = time.perf_counter()
            lexical_future = executor.submit(lexical.search, query, TENANT, CANDIDATES)
            embedding_started = time.perf_counter()
            vector = model.embed_query(query)
            values["query_embedding"].append((time.perf_counter() - embedding_started) * 1000)
            vector_started = time.perf_counter()
            semantic_hits = store.search_semantic(vector, TENANT, CANDIDATES, version=model.version)
            values["vector_search_materialization"].append(
                (time.perf_counter() - vector_started) * 1000
            )
            lexical_candidates = lexical_future.result()
            values["bm25"].append((time.perf_counter() - lexical_started) * 1000)
        from ctxd.app.retrieval.semantic import semantic_candidate

        semantic_candidates = [semantic_candidate(hit) for hit in semantic_hits]
        started = time.perf_counter()
        fused = fusion.fuse(lexical_candidates, semantic_candidates, CANDIDATES)
        values["rrf"].append((time.perf_counter() - started) * 1000)
        reranked = reranker.rerank(query, fused, 5)
        values["reranker_preparation"].append(reranker.last_timings_ms["preparation"])
        values["reranker_tokenization"].append(reranker.last_timings_ms["tokenization"])
        values["reranker_inference"].append(reranker.last_timings_ms["inference"])
        started = time.perf_counter()
        selected_tokens = 0
        for candidate in reranked:
            if selected_tokens + candidate.token_cost <= 1_000:
                selected_tokens += candidate.token_cost
        values["context_assembler"].append((time.perf_counter() - started) * 1000)
        values["total"].append((time.perf_counter() - total_started) * 1000)
    return {name: summary(samples) for name, samples in values.items()}


def concurrency(
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    reranker: FlashRankReranker,
    documents: int,
    level: int,
    query_count: int,
    use_reranker: bool,
) -> dict[str, Any]:
    hybrid, reranked = build_retrievers(store, model, reranker)
    retriever: Any = reranked if use_reranker else hybrid
    workload = queries(documents, query_count)
    barrier = Barrier(level)
    before = store.pool_statistics()

    def one(index: int) -> tuple[float, int]:
        barrier.wait()
        started = time.perf_counter()
        try:
            retriever.search(workload[index], TENANT, 5)
            return (time.perf_counter() - started) * 1000, 0
        except Exception:
            return (time.perf_counter() - started) * 1000, 1

    cpu_started = time.process_time()
    wall_started = time.perf_counter()
    latencies: list[float] = []
    errors = 0
    with ThreadPoolExecutor(max_workers=level) as executor:
        futures = [executor.submit(one, index) for index in range(query_count)]
        for future in as_completed(futures):
            latency_ms, error = future.result()
            latencies.append(latency_ms)
            errors += error
    wall = time.perf_counter() - wall_started
    client_cpu = time.process_time() - cpu_started
    after = store.pool_statistics()
    return {
        **summary(latencies, wall),
        "concurrency": level,
        "errors": errors,
        "pool_wait_ms": after.get("requests_wait_ms", 0) - before.get("requests_wait_ms", 0),
        "pool_queued": after.get("requests_queued", 0) - before.get("requests_queued", 0),
        "client_cpu_seconds": client_cpu,
        "client_cpu_percent_of_one_core": client_cpu / wall * 100,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def goodput(raw: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for mode, rows in raw.items():
        elapsed = sum(float(row["latency_ms"]) for row in rows) / 1000
        raw_qps = len(rows) / elapsed
        result[mode] = {}
        for budget in (100, 150, 250):
            quality = [bool(row["quality_pass"]) for row in rows]
            timely = [float(row["latency_ms"]) <= budget for row in rows]
            joint = [quality[index] and timely[index] for index in range(len(rows))]
            result[mode][str(budget)] = {
                "raw_qps": raw_qps,
                "quality_pass_rate": sum(quality) / len(rows),
                "latency_pass_rate": sum(timely) / len(rows),
                "joint_pass_rate": sum(joint) / len(rows),
                "good_requests_per_second": raw_qps * sum(joint) / len(rows),
            }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url",
        default=os.getenv("CTXD_DATABASE_URL", "postgresql://ctxd:ctxd@localhost:5432/ctxd"),
    )
    parser.add_argument("--document-counts", type=int, nargs="+", default=[100, 1000, 4167])
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--concurrency-queries", type=int, default=160)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cache" / "ctxd" / "rerankers"
    )
    parser.add_argument(
        "--latency-output", type=Path, default=Path("benchmarks/phase5_end_to_end_latency.json")
    )
    parser.add_argument(
        "--concurrency-output", type=Path, default=Path("benchmarks/phase5_concurrency.json")
    )
    parser.add_argument(
        "--goodput-output", type=Path, default=Path("benchmarks/phase5_goodput.json")
    )
    args = parser.parse_args()
    model = RealEmbeddingProvider()
    reranker = FlashRankReranker(cache_dir=args.cache_dir, offline=True, batch_size=BATCH_SIZE)
    end_to_end: dict[str, Any] = {}
    concurrent: dict[str, Any] = {}
    goodput_results: dict[str, Any] = {}
    for documents in args.document_counts:
        ingest_corpus(args.database_url, documents, model)
        store = PostgresDocumentStore(
            args.database_url, pool_min_size=1, pool_max_size=32, query_timeout_ms=30_000
        )
        store.start()
        try:
            measured = sequential(store, model, reranker, documents, args.samples)
            size = str(documents * 12)
            end_to_end[size] = {
                "candidate_count": CANDIDATES,
                "batch_size": BATCH_SIZE,
                "summary": {key: value for key, value in measured.items() if key != "raw"},
                "components": component_breakdown(store, model, reranker, documents, args.samples),
            }
            goodput_results[size] = goodput(measured["raw"])
            if documents >= 1000:
                concurrent[size] = {
                    mode: {
                        str(level): concurrency(
                            store,
                            model,
                            reranker,
                            documents,
                            level,
                            args.concurrency_queries,
                            mode == "hybrid_reranked",
                        )
                        for level in (1, 4, 8, 16, 32)
                    }
                    for mode in ("hybrid", "hybrid_reranked")
                }
        finally:
            store.close()
    artifacts = (
        (args.latency_output, {"results": end_to_end}),
        (args.concurrency_output, {"results": concurrent}),
        (
            args.goodput_output,
            {
                "experimental_metric": True,
                "definition": (
                    "Good requires a relevant generated source in top 5 and latency within budget."
                ),
                "results": goodput_results,
            },
        ),
    )
    for path, artifact in artifacts:
        path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"end_to_end": end_to_end, "concurrency": concurrent, "goodput": goodput_results},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
