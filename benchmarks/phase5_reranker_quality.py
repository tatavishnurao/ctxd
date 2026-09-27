"""Phase 5 real-reranker quality, depth, batching, and regression experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from pathlib import Path
from statistics import median
from typing import Any

from ctxd.app.evals.retrieval import load_corpus, ndcg_at_k, recall_at_k, reciprocal_rank
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.reranking import FlashRankReranker
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.documents import InMemoryDocumentStore

DEPTHS = (10, 20, 50)
BATCHES = (1, 4, 8, 16)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))]


def latency(values: list[float]) -> dict[str, float]:
    return {
        "p50_ms": median(values),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "pairs_per_second": 0.0,
    }


def unique(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(paths))


def metrics(rows: list[tuple[list[str], set[str]]]) -> dict[str, float]:
    normalized = [(unique(paths), expected) for paths, expected in rows]
    count = max(len(normalized), 1)
    return {
        "recall_at_1": sum(recall_at_k(paths, expected, 1) for paths, expected in normalized)
        / count,
        "recall_at_5": sum(recall_at_k(paths, expected, 5) for paths, expected in normalized)
        / count,
        "recall_at_10": sum(recall_at_k(paths, expected, 10) for paths, expected in normalized)
        / count,
        "mrr": sum(reciprocal_rank(paths, expected) for paths, expected in normalized) / count,
        "ndcg_at_5": sum(ndcg_at_k(paths, expected, 5) for paths, expected in normalized) / count,
        "ndcg_at_10": sum(ndcg_at_k(paths, expected, 10) for paths, expected in normalized) / count,
    }


def rank(paths: list[str], expected: set[str]) -> int | None:
    return next((index for index, path in enumerate(paths, 1) if path in expected), None)


def source(candidate: Any) -> str:
    return str(candidate.metadata.get("source_path", ""))


def artifact_digest(path: Path) -> tuple[int, str]:
    files = sorted(file for file in path.rglob("*") if file.is_file())
    digest = hashlib.sha256()
    size = 0
    for file in files:
        data = file.read_bytes()
        size += len(data)
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(data)
    return size, digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("evals/retrieval_semantic.json"))
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cache" / "ctxd" / "rerankers"
    )
    parser.add_argument(
        "--quality-output", type=Path, default=Path("benchmarks/phase5_reranker_quality.json")
    )
    parser.add_argument(
        "--depth-output", type=Path, default=Path("benchmarks/phase5_candidate_depth.json")
    )
    parser.add_argument(
        "--latency-output", type=Path, default=Path("benchmarks/phase5_reranker_latency.json")
    )
    args = parser.parse_args()
    corpus = load_corpus(args.corpus)
    store = InMemoryDocumentStore()
    embedding = RealEmbeddingProvider()
    ingestion = IngestionService(
        store,
        StructureAwareChunker(ChunkingConfig(target_tokens=80, max_tokens=120, overlap_tokens=10)),
        embedding,
    )
    for document in corpus.documents:
        ingestion.ingest_content(
            content=document.content,
            source_path=document.source_path,
            source_type=document.source_type,
            tenant_id=document.tenant_id,
            metadata=document.metadata,
        )
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, embedding)
    reranker = FlashRankReranker(cache_dir=args.cache_dir, batch_size=16)
    model_path = args.cache_dir / reranker.flashrank_model_name
    model_bytes, model_sha256 = artifact_digest(model_path)

    mode_rows: dict[str, list[tuple[list[str], set[str]]]] = {
        "lexical": [],
        "semantic": [],
        "hybrid": [],
        **{f"reranked_{depth}": [] for depth in DEPTHS},
    }
    categories: dict[str, dict[str, list[tuple[list[str], set[str]]]]] = {}
    case_results: list[dict[str, Any]] = []
    depth_latencies: dict[int, list[float]] = {depth: [] for depth in DEPTHS}

    for case in corpus.cases:
        expected = set(case.expected_sources)
        category = str(case.metadata.get("category", case.task_type)).replace("_", " ")
        lexical_candidates = lexical.search(case.question, case.tenant_id, 50)
        semantic_candidates = semantic.search(case.question, case.tenant_id, 50)
        lexical_paths = [source(item) for item in lexical_candidates[:10]]
        semantic_paths = [source(item) for item in semantic_candidates[:10]]
        hybrid_candidates = HybridRetriever(
            lexical, semantic, candidate_depth=20, parallel=False
        ).fuse(lexical_candidates[:20], semantic_candidates[:20], 10)
        hybrid_paths = [source(item) for item in hybrid_candidates]
        paths_by_mode = {
            "lexical": lexical_paths,
            "semantic": semantic_paths,
            "hybrid": hybrid_paths,
        }
        reranked_candidates_by_depth: dict[int, list[Any]] = {}
        candidate_present_by_depth: dict[int, bool] = {}
        for depth in DEPTHS:
            pool = HybridRetriever(lexical, semantic, candidate_depth=depth, parallel=False).fuse(
                lexical_candidates[:depth], semantic_candidates[:depth], depth
            )
            candidate_present_by_depth[depth] = any(source(item) in expected for item in pool)
            started = time.perf_counter()
            reranked = reranker.rerank(case.question, pool, 10)
            depth_latencies[depth].append((time.perf_counter() - started) * 1000)
            reranked_candidates_by_depth[depth] = reranked
            paths_by_mode[f"reranked_{depth}"] = [source(item) for item in reranked]
        category_rows = categories.setdefault(category, {mode: [] for mode in mode_rows})
        for mode, paths in paths_by_mode.items():
            row = (paths, expected)
            mode_rows[mode].append(row)
            category_rows[mode].append(row)
        selected = reranked_candidates_by_depth[20]
        reranked_paths = paths_by_mode["reranked_20"]
        rrf_rank = rank(hybrid_paths, expected)
        reranked_rank = rank(reranked_paths, expected)
        candidate_present = candidate_present_by_depth[20]
        transition = (
            "candidate missing"
            if not candidate_present
            else "fixed"
            if rrf_rank != 1 and reranked_rank == 1
            else "unchanged correct"
            if rrf_rank == 1 and reranked_rank == 1
            else "regressed"
            if rrf_rank is not None and (reranked_rank is None or reranked_rank > rrf_rank)
            else "unchanged incorrect"
        )
        top_wrong = next((item for item in selected if source(item) not in expected), None)
        relevant = next((item for item in selected if source(item) in expected), None)
        case_results.append(
            {
                "case_id": case.id,
                "query": case.question,
                "category": category,
                "expected_sources": sorted(expected),
                "rrf_rank": rrf_rank,
                "reranked_rank": reranked_rank,
                "transition": transition,
                "reranker_score": relevant.metadata.get("reranker_score") if relevant else None,
                "top_incorrect_candidate": source(top_wrong) if top_wrong else None,
            }
        )

    aggregate = {mode: metrics(rows) for mode, rows in mode_rows.items()}
    category_metrics = {
        category: {mode: metrics(rows) for mode, rows in modes.items()}
        for category, modes in categories.items()
    }
    transitions = {
        name: sum(row["transition"] == name for row in case_results)
        for name in (
            "fixed",
            "unchanged correct",
            "unchanged incorrect",
            "regressed",
            "candidate missing",
        )
    }
    regressions = [row for row in case_results if row["transition"] == "regressed"]
    protected_categories = {"exact", "exact lexical", "rare term"}
    protected = [row for row in case_results if row["category"] in protected_categories]
    protected_indices = [
        index for index, row in enumerate(case_results) if row["category"] in protected_categories
    ]
    lexical_top_1_indices = [
        index
        for index in protected_indices
        if rank(mode_rows["lexical"][index][0], mode_rows["lexical"][index][1]) == 1
    ]
    exact_protection = {
        "lexical_top_1_correct": len(lexical_top_1_indices),
        "preserved_by_reranker": sum(
            case_results[index]["reranked_rank"] == 1 for index in lexical_top_1_indices
        ),
        "demoted_by_reranker": sum(
            case_results[index]["reranked_rank"] != 1 for index in lexical_top_1_indices
        ),
        "regressions": [row for row in protected if row["transition"] == "regressed"],
    }

    depth_result = {
        str(depth): {
            "quality": aggregate[f"reranked_{depth}"],
            "latency": {
                **latency(depth_latencies[depth]),
                "pairs_per_second": depth
                * len(depth_latencies[depth])
                / (sum(depth_latencies[depth]) / 1000),
            },
        }
        for depth in DEPTHS
    }

    representative_pools: list[tuple[str, list[Any]]] = []
    for case in corpus.cases[:100]:
        lexical_candidates = lexical.search(case.question, case.tenant_id, 20)
        semantic_candidates = semantic.search(case.question, case.tenant_id, 20)
        pool = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=False).fuse(
            lexical_candidates, semantic_candidates, 20
        )
        representative_pools.append((case.question, pool))
    batch_result: dict[str, Any] = {}
    for batch in BATCHES:
        measured = FlashRankReranker(cache_dir=args.cache_dir, offline=True, batch_size=batch)
        totals: list[float] = []
        preparation: list[float] = []
        tokenization: list[float] = []
        inference: list[float] = []
        for query, pool in representative_pools:
            measured.rerank(query, pool, 10)
            totals.append(measured.last_timings_ms["total"])
            preparation.append(measured.last_timings_ms["preparation"])
            tokenization.append(measured.last_timings_ms["tokenization"])
            inference.append(measured.last_timings_ms["inference"])
        batch_result[str(batch)] = {
            "total": latency(totals),
            "preparation": latency(preparation),
            "tokenization": latency(tokenization),
            "inference": latency(inference),
            "pairs_per_second": sum(len(pool) for _, pool in representative_pools)
            / (sum(totals) / 1000),
        }

    quality_artifact = {
        "model": {
            "identifier": reranker.model_id,
            "source_revision": reranker.source_revision,
            "flashrank_model_name": reranker.flashrank_model_name,
            "input_limit": reranker.max_length,
            "license": reranker.license,
            "local_artifact_bytes": model_bytes,
            "local_artifact_sha256": model_sha256,
            "scoring": "positive-class probability from pairwise cross-encoder logits",
        },
        "candidate_selection": [
            {
                "model": "cross-encoder/ms-marco-TinyBERT-L-2-v2",
                "reason": "selected: smallest CPU ONNX option, Apache-2.0, batched",
            },
            {
                "model": "cross-encoder/ms-marco-MiniLM-L-2-v2",
                "reason": "not selected: larger model and latency footprint",
            },
            {
                "model": "mixedbread-ai/mxbai-rerank-xsmall-v1",
                "reason": "not selected: materially larger model for feasibility gate",
            },
        ],
        "metrics": aggregate,
        "categories": category_metrics,
        "transitions": transitions,
        "regressions": regressions,
        "exact_match_protection": exact_protection,
        "cases": case_results,
    }
    latency_artifact = {
        "candidate_depths": depth_result,
        "batch_sizes_at_20_candidates": batch_result,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "note": "Model initialization/download excluded; all runs are local CPU inference.",
    }
    depth_artifact = {
        "hybrid_baseline": aggregate["hybrid"],
        "depths": depth_result,
        "selection_rule": (
            "Choose the smallest depth retaining most measured quality gain after "
            "considering latency."
        ),
    }
    for path, artifact in (
        (args.quality_output, quality_artifact),
        (args.depth_output, depth_artifact),
        (args.latency_output, latency_artifact),
    ):
        path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "metrics": aggregate,
                "transitions": transitions,
                "exact_match_protection": exact_protection,
                "depths": depth_result,
                "batches": batch_result,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
