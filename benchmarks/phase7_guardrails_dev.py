"""Development-only analysis of three deterministic lexical-preservation rules."""

from __future__ import annotations

import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from ctxd.app.evals.phase7 import (
    apply_rank_guardrail,
    lexical_protection_ids,
    partition_metrics,
    rank_delta_buckets,
    transition_counts,
)

STRATEGIES = (
    "protect_lexical_top1",
    "protect_exact_overlap_top1",
    "protect_strong_identifier_winner",
)


def unique_paths(candidates: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(str(row["source_path"]) for row in candidates))


def relevant_rank(candidates: list[dict[str, Any]], expected: set[str]) -> int | None:
    return next(
        (index for index, path in enumerate(unique_paths(candidates), 1) if path in expected),
        None,
    )


def exact_class(base: int | None, guarded: int | None) -> str:
    if base is None:
        return "relevant source absent from candidate set"
    if guarded is None:
        return "relevant source absent after guardrail"
    if base <= 3 and guarded > 10:
        return "catastrophically demoted"
    if guarded < base:
        return "improved"
    if guarded == base:
        return "preserved"
    return "demoted"


def main() -> None:
    comparison_path = Path("benchmarks/phase7_dev_model_comparison.json")
    pool_path = Path("benchmarks/phase7_candidate_pools.json")
    split_path = Path("evals/phase7_split_manifest.json")
    output = Path("benchmarks/phase7_guardrail_dev.json")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite frozen dev artifact: {output}")
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    pools = json.loads(pool_path.read_text(encoding="utf-8"))
    split = json.loads(split_path.read_text(encoding="utf-8"))
    if comparison["protocol"]["split_manifest_sha256"] != split["split_manifest_sha256"]:
        raise ValueError("split manifest mismatch")
    development = [row for row in pools["cases"] if row["partition"] == "development"]
    if len(development) != split["partition_counts"]["development"]:
        raise ValueError("development set size mismatch")

    output_models: dict[str, Any] = {}
    for model_name, model_data in comparison["models"].items():
        model_rows = model_data["per_query_development_records"]
        if [row["case_id"] for row in model_rows] != [row["case_id"] for row in development]:
            raise ValueError("model rows are not aligned to frozen development set")
        model_output: dict[str, Any] = {}
        for strategy in STRATEGIES:
            metric_rows: list[tuple[list[str], set[str]]] = []
            category_rows: dict[str, list[tuple[list[str], set[str]]]] = defaultdict(list)
            transitions_base: list[int | None] = []
            transitions_new: list[int | None] = []
            exact_records: list[dict[str, Any]] = []
            case_regressions: list[dict[str, Any]] = []
            guardrail_costs: list[float] = []
            rank_deltas: list[int] = []
            query_model_ranks: list[dict[str, Any]] = []
            for pool_case, result_case in zip(development, model_rows, strict=True):
                original_rows = sorted(
                    result_case["ranked_candidates"], key=lambda row: row["rrf_rank"]
                )
                score_by_id = {
                    str(row["source_id"]): float(row["reranker_score"]) for row in original_rows
                }
                feature_rows = [
                    {
                        "source_id": row["source_id"],
                        "source_path": row["source_path"],
                        "lexical_rank": row["lexical_rank"],
                        "lexical_raw_score": row["lexical_raw_score"],
                        "exact_query_token_overlap": row["exact_query_token_overlap"],
                        "rare_identifier_overlap": row["rare_identifier_overlap"],
                        "rrf_rank": row["rrf_rank"],
                    }
                    for row in original_rows
                ]
                start = time.perf_counter()
                protected_ids = lexical_protection_ids(feature_rows, strategy)
                guarded_rows = apply_rank_guardrail(original_rows, score_by_id, protected_ids)
                guardrail_costs.append((time.perf_counter() - start) * 1000)
                expected = set(pool_case["expected_sources"])
                base_rank = result_case["baseline_relevant_rank"]
                new_rank = relevant_rank(guarded_rows, expected)
                paths = unique_paths(guarded_rows)
                metric_rows.append((paths, expected))
                category_rows[str(pool_case["category"])].append((paths, expected))
                transitions_base.append(base_rank)
                transitions_new.append(new_rank)
                if base_rank is not None and new_rank is not None:
                    rank_deltas.append(base_rank - new_rank)
                if pool_case["annotation_status"] != "ambiguous" and any(
                    row["exact_query_token_overlap"]
                    for row in feature_rows
                    if row["source_path"] in expected
                ):
                    exact_records.append(
                        {
                            "case_id": pool_case["case_id"],
                            "baseline_rank": base_rank,
                            "guarded_rank": new_rank,
                            "classification": exact_class(base_rank, new_rank),
                        }
                    )
                transition = (
                    "fixed"
                    if base_rank != 1 and new_rank == 1
                    else "unchanged_correct"
                    if base_rank == 1 and new_rank == 1
                    else "regressed"
                    if base_rank is not None and (new_rank is None or new_rank > base_rank)
                    else "unchanged_incorrect"
                )
                if transition == "regressed":
                    case_regressions.append(
                        {
                            "case_id": pool_case["case_id"],
                            "category": pool_case["category"],
                            "baseline_rank": base_rank,
                            "guarded_rank": new_rank,
                        }
                    )
                query_model_ranks.append(
                    {
                        "case_id": pool_case["case_id"],
                        "protected_candidate_ids": sorted(protected_ids),
                        "baseline_relevant_rank": base_rank,
                        "guarded_relevant_rank": new_rank,
                        "transition": transition,
                    }
                )
            exact_counts = {
                key: sum(row["classification"] == key for row in exact_records)
                for key in (
                    "preserved",
                    "improved",
                    "demoted",
                    "catastrophically demoted",
                    "relevant source absent from candidate set",
                    "relevant source absent after guardrail",
                )
            }
            model_output[strategy] = {
                "signals_used": {
                    "protect_lexical_top1": ["BM25 rank"],
                    "protect_exact_overlap_top1": ["BM25 rank", "exact query-token overlap"],
                    "protect_strong_identifier_winner": [
                        "BM25 rank",
                        "exact query-token overlap",
                        "identifier overlap",
                        "relative BM25 top1-to-top2 margin >= 0.50",
                    ],
                }[strategy],
                "metrics": partition_metrics(metric_rows),
                "category_metrics": {
                    category: partition_metrics(rows) for category, rows in category_rows.items()
                },
                "transitions": transition_counts(transitions_base, transitions_new),
                "exact_match_classifications": exact_counts,
                "regression_categories": {
                    category: sum(row["category"] == category for row in case_regressions)
                    for category in sorted({str(row["category"]) for row in case_regressions})
                },
                "rank_delta_buckets": rank_delta_buckets(rank_deltas),
                "guardrail_sort_cost_ms_p50": statistics.median(guardrail_costs),
                "regression_cases": case_regressions,
                "per_query": query_model_ranks,
            }
        output_models[model_name] = model_output
    output.write_text(
        json.dumps(
            {
                "partition": "development only",
                "split_manifest_sha256": split["split_manifest_sha256"],
                "catastrophic_demotion_definition": (
                    "baseline relevant rank <= 3 and guarded rank > 10"
                ),
                "ground_truth_or_category_features_used_by_guardrail": False,
                "models": output_models,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                model: {
                    strategy: {
                        "metrics": result["metrics"],
                        "transitions": result["transitions"],
                        "exact": result["exact_match_classifications"],
                        "guard_ms_p50": result["guardrail_sort_cost_ms_p50"],
                    }
                    for strategy, result in strategies.items()
                }
                for model, strategies in output_models.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
