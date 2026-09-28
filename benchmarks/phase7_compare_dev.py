"""Development-only, fixed-depth comparison. This script intentionally excludes holdout rows."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from ctxd.app.evals.phase7 import (
    partition_metrics,
    query_features,
    tokens,
    transition_counts,
    transition_label,
)
from ctxd.app.models.domain import ContextCandidate, SourceType
from ctxd.app.reranking.flashrank import FlashRankReranker
from phase7_models import BGE_RERANKER_BASE, MINILM_L6, LocalOnnxReranker, rerank_order

MODEL_LABELS = {
    "tinybert_negative_control": "cross-encoder/ms-marco-TinyBERT-L-2-v2",
    "minilm_l6": MINILM_L6.model_id,
    "bge_reranker_base": BGE_RERANKER_BASE.model_id,
}
CATEGORIES = (
    "exact lexical",
    "rare term",
    "morphology",
    "semantic paraphrase",
    "near duplicate",
    "multiple relevant",
    "long chunk",
)


def unique_paths(candidates: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(str(candidate["source_path"]) for candidate in candidates))


def first_relevant_ranks(candidates: list[dict[str, Any]], relevant: set[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for index, candidate in enumerate(candidates, 1):
        path = str(candidate["source_path"])
        if path in relevant:
            result.setdefault(path, index)
    return result


def classify_exact(baseline_rank: int | None, reranked_rank: int | None) -> str:
    if baseline_rank is None:
        return "relevant source absent from fixed candidate set"
    if reranked_rank is None:
        return "relevant source absent after reranking"
    if baseline_rank <= 3 and reranked_rank > 10:
        return "catastrophically demoted"
    if reranked_rank < baseline_rank:
        return "improved"
    if reranked_rank == baseline_rank:
        return "preserved"
    return "demoted"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pools", type=Path, default=Path("benchmarks/phase7_candidate_pools.json")
    )
    parser.add_argument("--split", type=Path, default=Path("evals/phase7_split_manifest.json"))
    parser.add_argument(
        "--output", type=Path, default=Path("benchmarks/phase7_dev_model_comparison.json")
    )
    parser.add_argument(
        "--pairwise-output", type=Path, default=Path("benchmarks/phase7_pairwise_analysis.json")
    )
    parser.add_argument(
        "--exact-output", type=Path, default=Path("benchmarks/phase7_exact_match_analysis.json")
    )
    parser.add_argument("--model-cache", type=Path, default=Path.home() / ".cache/ctxd/phase7")
    parser.add_argument(
        "--tinybert-cache", type=Path, default=Path.home() / ".cache/ctxd/rerankers"
    )
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    if any(path.exists() for path in (args.output, args.pairwise_output, args.exact_output)):
        raise FileExistsError("development comparison output exists; refusing overwrite")
    pool_artifact = json.loads(args.pools.read_text(encoding="utf-8"))
    split = json.loads(args.split.read_text(encoding="utf-8"))
    if pool_artifact["protocol"]["split_manifest_sha256"] != split["split_manifest_sha256"]:
        raise ValueError("candidate pools do not match frozen split")
    development = [row for row in pool_artifact["cases"] if row["partition"] == "development"]
    if any(row["partition"] != "development" for row in development):
        raise AssertionError("holdout leakage")
    if len(development) != split["partition_counts"]["development"]:
        raise ValueError("development candidate pool count mismatch")

    tinybert = FlashRankReranker(cache_dir=args.tinybert_cache, offline=True, batch_size=8)
    minilm = LocalOnnxReranker(MINILM_L6, cache_dir=args.model_cache, intra_op_threads=args.threads)
    bge = LocalOnnxReranker(
        BGE_RERANKER_BASE, cache_dir=args.model_cache, intra_op_threads=args.threads
    )
    scorers: dict[str, Any] = {
        "tinybert_negative_control": tinybert,
        "minilm_l6": minilm,
        "bge_reranker_base": bge,
    }
    model_identity = {
        "tinybert_negative_control": {
            "model_id": tinybert.model_id,
            "revision": tinybert.source_revision,
            "license": tinybert.license,
            "backend": "FlashRank ONNX Runtime CPU",
            "artifact_sha256": "7384e127005ead4f2c975419dccd885987e22d0ede93e903601ccdae5f2ce974",
            "max_input_tokens": 512,
            "batch_size": tinybert.batch_size,
            "threads": "ONNX Runtime default; see Phase 5 evidence",
            "new_dependencies": [],
        },
        "minilm_l6": minilm.identity(),
        "bge_reranker_base": bge.identity(),
    }
    result_cases: dict[str, list[dict[str, Any]]] = {key: [] for key in scorers}
    pair_data: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(
            lambda: {"relevant": [], "nonrelevant": [], "pairwise": [], "near_ties": []}
        )
    )
    exact_records: dict[str, list[dict[str, Any]]] = {key: [] for key in scorers}
    latency_samples: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"tokenization": [], "inference": [], "total": []}
    )
    baseline_rows: list[tuple[list[str], set[str]]] = []
    baseline_rows_no_ambiguous: list[tuple[list[str], set[str]]] = []

    for case in development:
        candidates = case["candidate_sources"]
        relevant = set(case["expected_sources"])
        base_paths = unique_paths(candidates)
        baseline_rows.append((base_paths, relevant))
        if case["annotation_status"] != "ambiguous":
            baseline_rows_no_ambiguous.append((base_paths, relevant))
        base_rank_by_source = {
            path: index for index, path in enumerate(base_paths, 1) if path in relevant
        }
        source_contents = [
            item["content"] for item in candidates if item["source_path"] in relevant
        ]
        query_info = query_features(case["query"], source_contents)
        per_model_paths: dict[str, list[str]] = {}
        per_model_scores: dict[str, list[float]] = {}
        per_model_ordered: dict[str, list[dict[str, Any]]] = {}
        for name, scorer in scorers.items():
            if name == "tinybert_negative_control":
                context_candidates = [
                    ContextCandidate(
                        source_id=item["source_id"],
                        source_type=SourceType.DOCUMENT,
                        content=item["content"],
                        token_cost=item["token_cost"],
                        relevance_score=float(item["rrf_score"]),
                        metadata=item["metadata"],
                    )
                    for item in candidates
                ]
                scored_candidates = scorer.rerank(
                    case["query"], context_candidates, len(candidates)
                )
                score_by_id = {
                    str(item.source_id): float(item.metadata["reranker_score"])
                    for item in scored_candidates
                }
                scores = [score_by_id[str(item["source_id"])] for item in candidates]
                timings = scorer.last_timings_ms
                latency_samples[name]["tokenization"].append(timings["tokenization"])
                latency_samples[name]["inference"].append(timings["inference"])
                latency_samples[name]["total"].append(timings["total"])
            else:
                scores = scorer.score_pairs(
                    case["query"],
                    [str(item["content"]) for item in candidates],
                    batch_size=args.batch_size,
                )
                timings = scorer.last_timings_ms
                for key in ("tokenization", "inference", "total"):
                    latency_samples[name][key].append(timings[key])
            order = rerank_order(scores)
            ordered_candidates = [candidates[index] for index in order]
            rank_by_id = {
                str(item["source_id"]): rank for rank, item in enumerate(ordered_candidates, 1)
            }
            score_by_id = {
                str(item["source_id"]): scores[index] for index, item in enumerate(candidates)
            }
            ordered_paths = unique_paths(ordered_candidates)
            per_model_paths[name] = ordered_paths
            per_model_scores[name] = scores
            per_model_ordered[name] = ordered_candidates

            rerank_source_ranks = {
                path: index for index, path in enumerate(ordered_paths, 1) if path in relevant
            }
            positives: list[float] = []
            used_relevant_paths: set[str] = set()
            negatives: list[float] = []
            for index, candidate in enumerate(candidates):
                path = str(candidate["source_path"])
                if path in relevant and path not in used_relevant_paths:
                    positives.append(scores[index])
                    used_relevant_paths.add(path)
                elif path not in relevant:
                    negatives.append(scores[index])
            pair_data[name]["overall"]["relevant"].extend(positives)
            pair_data[name]["overall"]["nonrelevant"].extend(negatives)
            pair_comparisons = [
                (positive > negative, abs(positive - negative) <= 0.01)
                for positive in positives
                for negative in negatives
            ]
            pair_data[name]["overall"]["pairwise"].extend(
                [1.0 if win else 0.0 for win, _ in pair_comparisons]
            )
            pair_data[name]["overall"]["near_ties"].extend(
                [1.0 if near else 0.0 for _, near in pair_comparisons]
            )
            category = str(case["category"])
            if category in CATEGORIES:
                pair_data[name][category]["relevant"].extend(positives)
                pair_data[name][category]["nonrelevant"].extend(negatives)
                pair_data[name][category]["pairwise"].extend(
                    [1.0 if win else 0.0 for win, _ in pair_comparisons]
                )
                pair_data[name][category]["near_ties"].extend(
                    [1.0 if near else 0.0 for _, near in pair_comparisons]
                )

            case_metrics = partition_metrics([(ordered_paths, relevant)])
            baseline_rank = min(base_rank_by_source.values(), default=None)
            candidate_rank = min(rerank_source_ranks.values(), default=None)
            record = {
                "case_id": case["case_id"],
                "category": category,
                "annotation_status": case["annotation_status"],
                "metrics": case_metrics,
                "baseline_relevant_rank": baseline_rank,
                "reranked_relevant_rank": candidate_rank,
                "transition": "",
                "relevant_candidate_scores": positives,
                "nonrelevant_candidate_score_count": len(negatives),
                "score_inversion": bool(
                    positives and negatives and max(negatives) >= max(positives)
                ),
                "ranked_candidates": [
                    {
                        "source_id": item["source_id"],
                        "source_path": item["source_path"],
                        "relevant_source": item["source_path"] in relevant,
                        "rrf_rank": item["rrf_rank"],
                        "lexical_rank": item["lexical_rank"],
                        "lexical_raw_score": item["lexical_score"],
                        "semantic_rank": item["semantic_rank"],
                        "exact_query_token_overlap": sorted(
                            set(tokens(case["query"])) & set(tokens(item["content"]))
                        ),
                        "rare_identifier_overlap": sorted(
                            token
                            for token in set(tokens(case["query"])) & set(tokens(item["content"]))
                            if ("_" in token or any(char.isdigit() for char in token))
                        ),
                        "reranker_score": score_by_id[str(item["source_id"])],
                        "reranked_rank": rank_by_id[str(item["source_id"])],
                    }
                    for item in ordered_candidates
                ],
            }
            result_cases[name].append(record)
            if query_info["has_exact_term"]:
                exact_records[name].append(
                    {
                        "case_id": case["case_id"],
                        "category": category,
                        "query": case["query"],
                        "query_exact_tokens": query_info["exact_query_tokens"],
                        "identifier_overlap": query_info["exact_identifier_overlap"],
                        "baseline_relevant_rank": baseline_rank,
                        "reranked_relevant_rank": candidate_rank,
                        "classification": classify_exact(baseline_rank, candidate_rank),
                        "relevant_source_ranks": rerank_source_ranks,
                    }
                )

    for name, rows in result_cases.items():
        ranks_base = [row["baseline_relevant_rank"] for row in rows]
        ranks_candidate = [row["reranked_relevant_rank"] for row in rows]
        counts = transition_counts(ranks_base, ranks_candidate)
        for row in rows:
            row["transition"] = transition_label(
                row["baseline_relevant_rank"], row["reranked_relevant_rank"]
            )
        grouped: dict[str, list[tuple[list[str], set[str]]]] = defaultdict(list)
        for row, case in zip(rows, development, strict=True):
            relevant = set(case["expected_sources"])
            ordered_paths = list(
                dict.fromkeys(str(item["source_path"]) for item in row["ranked_candidates"])
            )
            grouped["all"].append((ordered_paths, relevant))
            if case["annotation_status"] != "ambiguous":
                grouped["excluding_ambiguous"].append((ordered_paths, relevant))
        rows_by_category: dict[str, list[tuple[list[str], set[str]]]] = defaultdict(list)
        for row, case in zip(rows, development, strict=True):
            rows_by_category[str(case["category"])].append(
                (
                    list(
                        dict.fromkeys(str(item["source_path"]) for item in row["ranked_candidates"])
                    ),
                    set(case["expected_sources"]),
                )
            )
        summary = {
            "model_id": MODEL_LABELS[name],
            "development_metrics": {
                key: partition_metrics(value) for key, value in grouped.items()
            },
            "category_metrics": {
                category: partition_metrics(observations)
                for category, observations in rows_by_category.items()
            },
            "transitions": counts,
            "category_regression_counts": {
                category: sum(
                    row["category"] == category and row["transition"] == "regressed" for row in rows
                )
                for category in CATEGORIES
            },
            "score_inversion_case_count": sum(row["score_inversion"] for row in rows),
            "standalone_n20_latency_ms": {
                key: {
                    "p50": statistics.median(values),
                    "p95": sorted(values)[int((len(values) - 1) * 0.95)],
                    "p99": sorted(values)[int((len(values) - 1) * 0.99)],
                }
                for key, values in latency_samples[name].items()
            },
            "exact_match_classifications": {
                classification: sum(
                    row["classification"] == classification for row in exact_records[name]
                )
                for classification in (
                    "preserved",
                    "improved",
                    "demoted",
                    "catastrophically demoted",
                    "relevant source absent from fixed candidate set",
                    "relevant source absent after reranking",
                )
            },
            "per_query_development_records": rows,
        }
        result_cases[name] = summary  # type: ignore[assignment]

    pairwise_summary: dict[str, Any] = {}
    for name, categories in pair_data.items():
        pairwise_summary[name] = {}
        for category, values in categories.items():
            positive = values["relevant"]
            negative = values["nonrelevant"]
            pairwise = values["pairwise"]
            near = values["near_ties"]
            pairwise_summary[name][category] = {
                "relevant_count": len(positive),
                "nonrelevant_count": len(negative),
                "relevant_score_median": statistics.median(positive) if positive else None,
                "nonrelevant_score_median": statistics.median(negative) if negative else None,
                "median_score_separation": (
                    statistics.median(positive) - statistics.median(negative)
                    if positive and negative
                    else None
                ),
                "pairwise_accuracy": sum(pairwise) / len(pairwise) if pairwise else None,
                "strict_win_pairs": int(sum(pairwise)),
                "pair_count": len(pairwise),
                "tie_or_near_tie_rate_abs_delta_le_0_01": (sum(near) / len(near) if near else None),
            }
    args.output.write_text(
        json.dumps(
            {
                "protocol": pool_artifact["protocol"]
                | {
                    "partition_evaluated": "development only",
                    "holdout_rows_read_for_metrics": 0,
                    "candidate_set": (
                        "same fixed depth-20 hybrid RRF chunk candidates for all models"
                    ),
                },
                "model_identity": model_identity,
                "models": result_cases,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    args.pairwise_output.write_text(
        json.dumps(
            {
                "protocol": (
                    "development only; first-RRF source-level proxy per relevant source; "
                    "within-query positive-negative score pairs"
                ),
                "models": pairwise_summary,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    args.exact_output.write_text(
        json.dumps(
            {
                "definition": {
                    "exact_match_query": (
                        "query has a normalized token in expected-source content"
                    ),
                    "catastrophic_demotion": (
                        "baseline relevant rank <= 3 and reranked relevant rank > 10"
                    ),
                    "classification_order": "catastrophic, improved, preserved, demoted",
                },
                "models": exact_records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                name: {
                    "metrics": summary["development_metrics"]["all"],
                    "transitions": summary["transitions"],
                    "inversions": summary["score_inversion_case_count"],
                    "exact": summary["exact_match_classifications"],
                    "latency": summary["standalone_n20_latency_ms"],
                }
                for name, summary in result_cases.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
