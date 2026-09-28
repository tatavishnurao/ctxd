"""Post-selection standalone and PostgreSQL performance measurements for Phase 7."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ctxd.app.evals.phase7 import lexical_protection_ids, tokens
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import ContextCandidate, DocumentSourceType
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.postgres import PostgresDocumentStore
from phase4b_postgres_closure import CHUNKER as PERF_CHUNKER
from phase4b_postgres_closure import generated_document, queries
from phase7_models import MINILM_L6, LocalOnnxReranker


class SelectedOfflineReranker:
    def __init__(self, model: LocalOnnxReranker, batch_size: int = 16) -> None:
        self.model = model
        self.batch_size = batch_size
        self.timings: dict[str, float] = {}

    def rerank(
        self, query: str, candidates: list[ContextCandidate], top_k: int
    ) -> list[ContextCandidate]:
        scores = self.model.score_pairs(
            query, [candidate.content for candidate in candidates], batch_size=self.batch_size
        )
        score_by_id = {
            candidate.source_id: score for candidate, score in zip(candidates, scores, strict=True)
        }
        feature_rows = []
        for rrf_rank, candidate in enumerate(candidates, 1):
            query_tokens = set(tokens(query))
            content_tokens = set(tokens(candidate.content))
            overlap = sorted(query_tokens & content_tokens)
            identifiers = sorted(
                token
                for token in overlap
                if "_" in token or any(character.isdigit() for character in token)
            )
            feature_rows.append(
                {
                    "source_id": candidate.source_id,
                    "source_path": str(candidate.metadata.get("source_path", "")),
                    "lexical_rank": candidate.metadata.get("lexical_rank"),
                    "lexical_raw_score": candidate.metadata.get("raw_lexical_score"),
                    "exact_query_token_overlap": overlap,
                    "rare_identifier_overlap": identifiers,
                    "rrf_rank": rrf_rank,
                    "candidate": candidate,
                }
            )
        protected = lexical_protection_ids(feature_rows, "protect_exact_overlap_top1")
        protected_candidates = [row for row in feature_rows if row["source_id"] in protected]
        remaining = [row for row in feature_rows if row["source_id"] not in protected]
        remaining.sort(key=lambda row: (-score_by_id[row["source_id"]], row["rrf_rank"]))
        ordered = [row["candidate"] for row in protected_candidates + remaining]
        return ordered[:top_k]


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * quantile))]


def distribution(values: list[float], wall_seconds: float | None = None) -> dict[str, float]:
    return {
        "p50_ms": statistics.median(values),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "qps": len(values) / wall_seconds if wall_seconds is not None else 0.0,
    }


def ingest_perf_corpus(
    store: PostgresDocumentStore,
    model: RealEmbeddingProvider,
    count: int,
    tenant: str,
) -> list[tuple[str, str]]:
    ingestion = IngestionService(store, PERF_CHUNKER, model)
    documents: list[tuple[str, str]] = []
    for index in range(count):
        document, chunks, _ = ingestion.ingest_content(
            content=generated_document(index),
            source_path=f"generated/doc-{index}.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id=tenant,
        )
        if len(chunks) != 12:
            raise ValueError(f"expected 12 chunks/document, got {len(chunks)}")
        documents.append((tenant, document.document_id))
    return documents


def memory_available_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "cpu_model": platform.processor(),
        "memory_available_bytes_at_start": memory_available_bytes(),
        "model_device": "CPU",
        "onnx_intra_op_threads": 4,
        "database_url_variable_set": bool(os.getenv("CTXD_DATABASE_URL")),
    }


def standalone_measurement(
    pools: list[dict[str, Any]],
    model: LocalOnnxReranker,
    *,
    rounds: int,
    batch_size: int,
) -> dict[str, Any]:
    development = [case for case in pools if case["partition"] == "development"]
    samples: dict[str, list[float]] = defaultdict(list)
    # Warm model/runtime once using development candidates only.
    for case in development[:5]:
        model.score_pairs(
            case["query"],
            [candidate["content"] for candidate in case["candidate_sources"]],
            batch_size=batch_size,
        )
    for _ in range(rounds):
        for case in development:
            model.score_pairs(
                case["query"],
                [candidate["content"] for candidate in case["candidate_sources"]],
                batch_size=batch_size,
            )
            for key in ("tokenization", "inference", "total"):
                samples[key].append(model.last_timings_ms[key])
    return {
        "model_id": model.spec.model_id,
        "revision": model.spec.revision,
        "candidate_count": 20,
        "development_queries": len(development),
        "rounds": rounds,
        "total_samples": len(samples["total"]),
        "batch_size": batch_size,
        "timings": {key: distribution(values) for key, values in samples.items()},
        "model_identity": model.identity(),
    }


def sequential_runs(
    store: PostgresDocumentStore,
    model: LocalOnnxReranker,
    documents: int,
    tenant: str,
    *,
    runs: int,
    samples_per_run: int,
) -> dict[str, Any]:
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, RealEmbeddingProvider())
    hybrid = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=True)
    reranker = SelectedOfflineReranker(model)
    workload = queries(documents, samples_per_run)
    metrics: dict[str, dict[str, list[float]]] = {
        mode: {"latency": [], "wall": []} for mode in ("hybrid", "selected")
    }
    raw: dict[str, list[dict[str, Any]]] = {"hybrid": [], "selected": []}
    # Warm each path once without using its result for quality evaluation.
    for query in workload[:10]:
        hybrid.search(query, tenant, 5)
        pool = hybrid.search(query, tenant, 20)
        reranker.rerank(query, pool, 5)
    for run in range(1, runs + 1):
        for mode in ("hybrid", "selected") if run % 2 else ("selected", "hybrid"):
            retriever_started = time.perf_counter()
            for query_index, query in enumerate(workload):
                started = time.perf_counter()
                if mode == "hybrid":
                    selected = hybrid.search(query, tenant, 5)
                else:
                    candidates = hybrid.search(query, tenant, 20)
                    selected = reranker.rerank(query, candidates, 5)
                latency = (time.perf_counter() - started) * 1000
                raw[mode].append(
                    {
                        "run": run,
                        "query_index": query_index,
                        "latency_ms": latency,
                        "selected_count": len(selected),
                    }
                )
                metrics[mode]["latency"].append(latency)
            metrics[mode]["wall"].append(time.perf_counter() - retriever_started)
    return {
        mode: {
            "runs": runs,
            "queries_per_run": samples_per_run,
            "summary": distribution(metrics[mode]["latency"], sum(metrics[mode]["wall"])),
            "per_run": [
                distribution(
                    [row["latency_ms"] for row in raw[mode] if row["run"] == run],
                    metrics[mode]["wall"][run - 1],
                )
                for run in range(1, runs + 1)
            ],
            "raw": raw[mode],
        }
        for mode in ("hybrid", "selected")
    }


def concurrent_runs(
    store: PostgresDocumentStore,
    model: LocalOnnxReranker,
    documents: int,
    tenant: str,
    *,
    queries_per_level: int,
    levels: tuple[int, ...] = (1, 4, 8, 16),
) -> dict[str, Any]:
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, RealEmbeddingProvider())
    hybrid = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=True)
    reranker = SelectedOfflineReranker(model)
    workload = queries(documents, queries_per_level)
    results: dict[str, Any] = {}
    for mode in ("hybrid", "selected"):
        retriever = hybrid
        for level in levels:
            before = store.pool_statistics()
            latencies: list[float] = []
            errors = 0
            barrier = __import__("threading").Barrier(level)

            def one(
                index: int,
                selected_mode: str = mode,
                start_barrier: Any = barrier,
                selected_retriever: HybridRetriever = retriever,
            ) -> tuple[float, int]:
                start_barrier.wait()
                started = time.perf_counter()
                try:
                    if selected_mode == "hybrid":
                        selected_retriever.search(workload[index], tenant, 5)
                    else:
                        pool = selected_retriever.search(workload[index], tenant, 20)
                        reranker.rerank(workload[index], pool, 5)
                    return (time.perf_counter() - started) * 1000, 0
                except Exception:
                    return (time.perf_counter() - started) * 1000, 1

            wall_started = time.perf_counter()
            cpu_started = time.process_time()
            with ThreadPoolExecutor(max_workers=level) as executor:
                futures = [executor.submit(one, index) for index in range(queries_per_level)]
                for future in as_completed(futures):
                    latency, error = future.result()
                    latencies.append(latency)
                    errors += error
            wall = time.perf_counter() - wall_started
            cpu = time.process_time() - cpu_started
            after = store.pool_statistics()
            results.setdefault(mode, {})[str(level)] = {
                **distribution(latencies, wall),
                "errors": errors,
                "pool_wait_ms": after.get("requests_wait_ms", 0)
                - before.get("requests_wait_ms", 0),
                "pool_queued": after.get("requests_queued", 0) - before.get("requests_queued", 0),
                "client_cpu_seconds": cpu,
                "client_cpu_percent_of_one_core": cpu / wall * 100,
                "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "memory_available_bytes_after": memory_available_bytes(),
            }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url",
        default=os.getenv("CTXD_DATABASE_URL", "postgresql://ctxd:ctxd@localhost:5432/ctxd"),
    )
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--samples-per-run", type=int, default=50)
    parser.add_argument("--standalone-rounds", type=int, default=5)
    parser.add_argument("--concurrency-queries", type=int, default=32)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/phase7_latency.json"))
    parser.add_argument(
        "--concurrency-output", type=Path, default=Path("benchmarks/phase7_concurrency.json")
    )
    parser.add_argument("--model-cache", type=Path, default=Path.home() / ".cache/ctxd/phase7")
    args = parser.parse_args()
    if args.output.exists() or args.concurrency_output.exists():
        raise FileExistsError("Phase 7 performance outputs exist; refusing overwrite")
    split = json.loads(Path("evals/phase7_split_manifest.json").read_text(encoding="utf-8"))
    config = json.loads(Path("benchmarks/phase7_selected_config.json").read_text(encoding="utf-8"))
    holdout = json.loads(Path("benchmarks/phase7_holdout.json").read_text(encoding="utf-8"))
    if holdout["configuration_sha256"] != config["configuration_sha256"]:
        raise ValueError("performance benchmark config differs from one-shot holdout config")
    model = LocalOnnxReranker(
        MINILM_L6, cache_dir=args.model_cache, intra_op_threads=int(config["threads"]), offline=True
    )
    standalone = standalone_measurement(
        json.loads(Path("benchmarks/phase7_candidate_pools.json").read_text(encoding="utf-8"))[
            "cases"
        ],
        model,
        rounds=args.standalone_rounds,
        batch_size=int(config["batch_size"]),
    )
    model_provider = RealEmbeddingProvider()
    store = PostgresDocumentStore(args.database_url, pool_min_size=1, pool_max_size=32)
    store.start()
    end_to_end: dict[str, Any] = {}
    concurrency: dict[str, Any] = {}
    for documents in (100, 1000, 4167):
        corpus_size = documents * 12
        tenant = f"phase7-performance-{corpus_size}"
        ingested: list[tuple[str, str]] = []
        try:
            ingested = ingest_perf_corpus(store, model_provider, documents, tenant)
            end_to_end[str(corpus_size)] = sequential_runs(
                store,
                model,
                documents,
                tenant,
                runs=args.runs,
                samples_per_run=args.samples_per_run,
            )
            if corpus_size in (12000, 50004):
                concurrency[str(corpus_size)] = concurrent_runs(
                    store,
                    model,
                    documents,
                    tenant,
                    queries_per_level=args.concurrency_queries,
                )
        finally:
            for item_tenant, document_id in ingested:
                store.delete_document(document_id, item_tenant)
    store.close()
    args.output.write_text(
        json.dumps(
            {
                "protocol": {
                    "configuration_sha256": config["configuration_sha256"],
                    "split_manifest_sha256": split["split_manifest_sha256"],
                    "selected_config_only": True,
                    "candidate_depth": 20,
                    "candidate_set_for_reranker": "parallel exact BM25 + exact pgvector RRF",
                    "model_warmup": 10,
                    "independent_runs": args.runs,
                    "queries_per_run_per_mode": args.samples_per_run,
                    "concurrency_cpu_measurement": "client process only; not PostgreSQL server CPU",
                },
                "environment": environment(),
                "model_identity": model.identity(),
                "standalone_n20": standalone,
                "end_to_end": end_to_end,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    args.concurrency_output.write_text(
        json.dumps(
            {
                "protocol": {
                    "configuration_sha256": config["configuration_sha256"],
                    "queries_per_level": args.concurrency_queries,
                    "levels": [1, 4, 8, 16],
                    "same_fixed_depth_20_candidate_generation": True,
                },
                "environment": environment(),
                "results": concurrency,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "standalone_n20": standalone["timings"],
                "end_to_end": {
                    size: {mode: value["summary"] for mode, value in modes.items()}
                    for size, modes in end_to_end.items()
                },
                "concurrency": concurrency,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
