"""Strict five-run Phase 6 PostgreSQL latency and concurrency reproduction."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
from typing import Any

import psycopg
from ctxd.app.evals.analysis import aggregate_run_metric, robust_outlier_indices
from ctxd.app.reranking import FlashRankReranker
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever, semantic_candidate
from ctxd.app.storage.postgres import PostgresDocumentStore
from phase4b_postgres_closure import TENANT, ingest_corpus, queries
from phase5_postgres_reranker import concurrency

CANDIDATES = 10
TOP_K = 5
BATCH_SIZE = 8
COMPONENTS = (
    "query_embedding_ms",
    "bm25_ms",
    "vector_search_materialization_ms",
    "rrf_ms",
    "reranker_preparation_ms",
    "reranker_tokenization_ms",
    "reranker_inference_ms",
    "context_selection_ms",
)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))]


def summarize(values: list[float], elapsed: float) -> dict[str, float]:
    return {
        "p50_ms": median(values),
        "p90_ms": percentile(values, 0.90),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "qps": len(values) / elapsed,
    }


def measure_query(
    *,
    query: str,
    expected_source: str,
    tenant_id: str,
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    reranker: FlashRankReranker,
    use_reranker: bool,
) -> dict[str, Any]:
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, model)
    fusion = HybridRetriever(lexical, semantic, candidate_depth=CANDIDATES, parallel=False)
    row: dict[str, Any] = {component: 0.0 for component in COMPONENTS}
    total_started = time.perf_counter()

    def timed_lexical_search() -> tuple[list[Any], float]:
        lexical_started = time.perf_counter()
        found = lexical.search(query, tenant_id, CANDIDATES)
        return found, (time.perf_counter() - lexical_started) * 1000

    with ThreadPoolExecutor(max_workers=2) as executor:
        lexical_future = executor.submit(timed_lexical_search)
        embedding_started = time.perf_counter()
        vector = model.embed_query(query)
        row["query_embedding_ms"] = (time.perf_counter() - embedding_started) * 1000
        vector_started = time.perf_counter()
        semantic_hits = store.search_semantic(vector, tenant_id, CANDIDATES, version=model.version)
        row["vector_search_materialization_ms"] = (time.perf_counter() - vector_started) * 1000
        lexical_candidates, row["bm25_ms"] = lexical_future.result()
    semantic_candidates = [semantic_candidate(hit) for hit in semantic_hits]
    fusion_started = time.perf_counter()
    candidates = fusion.fuse(lexical_candidates, semantic_candidates, CANDIDATES)
    row["rrf_ms"] = (time.perf_counter() - fusion_started) * 1000
    if use_reranker:
        candidates = reranker.rerank(query, candidates, TOP_K)
        row["reranker_preparation_ms"] = reranker.last_timings_ms["preparation"]
        row["reranker_tokenization_ms"] = reranker.last_timings_ms["tokenization"]
        row["reranker_inference_ms"] = reranker.last_timings_ms["inference"]
    else:
        candidates = candidates[:TOP_K]
    context_started = time.perf_counter()
    selected = []
    selected_tokens = 0
    for candidate in candidates:
        if selected_tokens + candidate.token_cost <= 1_000:
            selected.append(candidate)
            selected_tokens += candidate.token_cost
    row["context_selection_ms"] = (time.perf_counter() - context_started) * 1000
    row["total_ms"] = (time.perf_counter() - total_started) * 1000
    row["quality_pass"] = any(
        candidate.metadata.get("source_path") == expected_source for candidate in selected
    )
    return row


def measure_run(
    *,
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    reranker: FlashRankReranker,
    documents: int,
    samples: int,
    run_index: int,
    mode: str,
) -> dict[str, Any]:
    workload = queries(documents, samples + 20)
    use_reranker = mode == "hybrid_reranked"
    for index, query in enumerate(workload[:20]):
        measure_query(
            query=query,
            expected_source=f"generated/doc-{index % documents}.txt",
            tenant_id=TENANT,
            store=store,
            model=model,
            reranker=reranker,
            use_reranker=use_reranker,
        )
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for offset, query in enumerate(workload[20:], 20):
        row = measure_query(
            query=query,
            expected_source=f"generated/doc-{offset % documents}.txt",
            tenant_id=TENANT,
            store=store,
            model=model,
            reranker=reranker,
            use_reranker=use_reranker,
        )
        row["query_index"] = offset
        rows.append(row)
    elapsed = time.perf_counter() - started
    latencies = [float(row["total_ms"]) for row in rows]
    outlier_indices = set(robust_outlier_indices(latencies))
    component_summary = {
        component: summarize([float(row[component]) for row in rows], elapsed)
        for component in COMPONENTS
    }
    return {
        "run": run_index,
        "mode": mode,
        "elapsed_seconds": elapsed,
        "summary": summarize(latencies, elapsed),
        "quality_pass_rate": sum(bool(row["quality_pass"]) for row in rows) / len(rows),
        "component_summary": component_summary,
        "outlier_count": len(outlier_indices),
        "raw": [
            row | {"robust_total_outlier": index in outlier_indices}
            for index, row in enumerate(rows)
        ],
    }


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        metric: aggregate_run_metric([float(run["summary"][metric]) for run in runs])
        for metric in ("p50_ms", "p90_ms", "p95_ms", "p99_ms", "qps")
    } | {
        "quality_pass_rate": aggregate_run_metric([float(run["quality_pass_rate"]) for run in runs])
    }


def goodput(runs: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for budget in (100, 150, 250):
        run_results = []
        for run in runs:
            rows = run["raw"]
            qps = len(rows) / float(run["elapsed_seconds"])
            quality = sum(bool(row["quality_pass"]) for row in rows) / len(rows)
            timely = sum(float(row["total_ms"]) <= budget for row in rows) / len(rows)
            joint = sum(
                bool(row["quality_pass"]) and float(row["total_ms"]) <= budget for row in rows
            ) / len(rows)
            run_results.append(
                {
                    "run": run["run"],
                    "raw_qps": qps,
                    "quality_pass_rate": quality,
                    "latency_pass_rate": timely,
                    "joint_pass_rate": joint,
                    "good_requests_per_second": qps * joint,
                }
            )
        output[str(budget)] = {
            "runs": run_results,
            "aggregate_good_requests_per_second": aggregate_run_metric(
                [row["good_requests_per_second"] for row in run_results]
            ),
        }
    return output


def outlier_analysis(results: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for size, modes in results.items():
        output[size] = {}
        mode_outlier_queries: dict[str, set[tuple[int, int]]] = {}
        for mode, mode_result in modes.items():
            records = []
            keys: set[tuple[int, int]] = set()
            for run in mode_result["runs"]:
                component_p95 = {
                    component: float(run["component_summary"][component]["p95_ms"])
                    for component in COMPONENTS
                }
                for row in run["raw"]:
                    if not row["robust_total_outlier"]:
                        continue
                    co_spikes = [
                        component
                        for component in COMPONENTS
                        if float(row[component]) > component_p95[component]
                    ]
                    largest = max(COMPONENTS, key=lambda component: float(row[component]))
                    records.append(
                        {
                            "run": run["run"],
                            "query_index": row["query_index"],
                            "total_ms": row["total_ms"],
                            "co_spiking_components": co_spikes,
                            "largest_component": largest,
                        }
                    )
                    keys.add((run["run"], row["query_index"]))
            mode_outlier_queries[mode] = keys
            output[size][mode] = {
                "count": len(records),
                "largest_component_counts": dict(
                    __import__("collections").Counter(row["largest_component"] for row in records)
                ),
                "records": records,
            }
        shared = mode_outlier_queries.get("hybrid", set()) & mode_outlier_queries.get(
            "hybrid_reranked", set()
        )
        output[size]["same_run_query_outliers_in_both_modes"] = len(shared)
    return output


def environment(database_url: str) -> dict[str, Any]:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute("SHOW server_version")
        postgres_version = cursor.fetchone()[0]
        cursor.execute("SELECT datcollate FROM pg_database WHERE datname = current_database()")
        collation = cursor.fetchone()[0]
    memory_kib = None
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            memory_kib = int(line.split()[1])
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "kernel": platform.release(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "memory_total_kib": memory_kib,
        "postgresql": postgres_version,
        "postgresql_lc_collate": collation,
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "relevant_environment": {
            name: os.getenv(name)
            for name in ("CTXD_DATABASE_URL", "OMP_NUM_THREADS", "ORT_NUM_THREADS")
        },
        "host_load_average_at_start": os.getloadavg(),
        "environment_note": (
            "WSL2/shared-host environment; host scheduling noise is plausible but not proven. "
            "PostgreSQL emitted a collation-version mismatch warning during validation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url",
        default=os.getenv("CTXD_DATABASE_URL", "postgresql://ctxd:ctxd@localhost:5432/ctxd"),
    )
    parser.add_argument("--document-counts", type=int, nargs="+", default=[100, 1000, 4167])
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--concurrency-queries", type=int, default=160)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cache" / "ctxd" / "rerankers"
    )
    args = parser.parse_args()
    if args.runs < 5:
        raise ValueError("strict Phase 6 protocol requires at least five runs")
    protocol = {
        "independent_runs": args.runs,
        "warmup_queries_per_mode_per_run": 20,
        "measured_queries_per_mode_per_run": args.samples,
        "candidate_count": CANDIDATES,
        "top_k": TOP_K,
        "reranker_batch_size": BATCH_SIZE,
        "model_preload": True,
        "corpus_stable_within_all_five_runs": True,
        "mode_order": "alternating AB/BA by run",
        "outlier_rule": "total > median + 3 * median absolute deviation within run/mode",
    }
    embedding_started = time.perf_counter()
    model = RealEmbeddingProvider()
    embedding_load_ms = (time.perf_counter() - embedding_started) * 1000
    reranker_started = time.perf_counter()
    reranker = FlashRankReranker(cache_dir=args.cache_dir, offline=True, batch_size=BATCH_SIZE)
    reranker_load_ms = (time.perf_counter() - reranker_started) * 1000
    env = environment(args.database_url)
    results: dict[str, Any] = {}
    concurrency_results: dict[str, Any] = {}
    goodput_results: dict[str, Any] = {}
    cold_starts: dict[str, Any] = {
        "embedding_model_load_ms": embedding_load_ms,
        "reranker_model_load_ms": reranker_load_ms,
        "note": (
            "Model construction is separated. First-query timings do not flush "
            "OS/PostgreSQL caches."
        ),
    }
    for documents in args.document_counts:
        ingest_corpus(args.database_url, documents, model)
        size = str(documents * 12)
        results[size] = {mode: {"runs": []} for mode in ("hybrid", "hybrid_reranked")}
        first_query: dict[str, float] = {}
        for mode in ("hybrid", "hybrid_reranked"):
            store = PostgresDocumentStore(
                args.database_url, pool_min_size=1, pool_max_size=32, query_timeout_ms=30_000
            )
            store.start()
            try:
                started = time.perf_counter()
                measure_query(
                    query=queries(documents, 1)[0],
                    expected_source="generated/doc-0.txt",
                    tenant_id=TENANT,
                    store=store,
                    model=model,
                    reranker=reranker,
                    use_reranker=mode == "hybrid_reranked",
                )
                first_query[mode] = (time.perf_counter() - started) * 1000
            finally:
                store.close()
        cold_starts[size] = first_query
        store = PostgresDocumentStore(
            args.database_url, pool_min_size=1, pool_max_size=32, query_timeout_ms=30_000
        )
        store.start()
        try:
            for run_index in range(1, args.runs + 1):
                order = (
                    ("hybrid", "hybrid_reranked")
                    if run_index % 2
                    else ("hybrid_reranked", "hybrid")
                )
                for mode in order:
                    measured = measure_run(
                        store=store,
                        model=model,
                        reranker=reranker,
                        documents=documents,
                        samples=args.samples,
                        run_index=run_index,
                        mode=mode,
                    )
                    results[size][mode]["runs"].append(measured)
            for mode in ("hybrid", "hybrid_reranked"):
                results[size][mode]["aggregate"] = aggregate_runs(results[size][mode]["runs"])
                goodput_results.setdefault(size, {})[mode] = goodput(results[size][mode]["runs"])
            if documents >= 1000:
                concurrency_results[size] = {}
                warm_hybrid = HybridRetriever(
                    BM25Retriever(store),
                    SemanticRetriever(store, model),
                    candidate_depth=CANDIDATES,
                    parallel=True,
                )
                for query in queries(documents, 20):
                    warm_hybrid.search(query, TENANT, TOP_K)
                for mode in ("hybrid", "hybrid_reranked"):
                    concurrency_results[size][mode] = {}
                    for level in (1, 4, 8, 16, 32):
                        runs = [
                            concurrency(
                                store,
                                model,
                                reranker,
                                documents,
                                level,
                                args.concurrency_queries,
                                mode == "hybrid_reranked",
                            )
                            | {"run": run_index}
                            for run_index in range(1, args.runs + 1)
                        ]
                        concurrency_results[size][mode][str(level)] = {
                            "runs": runs,
                            "aggregate": {
                                metric: aggregate_run_metric([float(run[metric]) for run in runs])
                                for metric in (
                                    "p50_ms",
                                    "p95_ms",
                                    "p99_ms",
                                    "qps",
                                    "pool_wait_ms",
                                    "client_cpu_seconds",
                                    "max_rss_kib",
                                )
                            },
                        }
        finally:
            store.close()
    outliers = outlier_analysis(results)
    artifacts = {
        "benchmarks/phase6_reproducibility.json": {
            "protocol": protocol,
            "environment": env,
            "cold_start": cold_starts,
            "results": results,
        },
        "benchmarks/phase6_concurrency.json": {
            "protocol": protocol,
            "environment": env,
            "results": concurrency_results,
        },
        "benchmarks/phase6_goodput.json": {
            "experimental_metric": True,
            "definition": "Good means expected source in top 5 and total latency within budget.",
            "results": goodput_results,
        },
        "benchmarks/phase6_outlier_analysis.json": {
            "rule": protocol["outlier_rule"],
            "results": outliers,
            "causality_warning": (
                "Component co-spikes are diagnostic correlations, not proof of host or "
                "database cause."
            ),
        },
    }
    for filename, payload in artifacts.items():
        Path(filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "aggregates": {
                    size: {mode: value["aggregate"] for mode, value in modes.items()}
                    for size, modes in results.items()
                },
                "outliers": outliers,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
