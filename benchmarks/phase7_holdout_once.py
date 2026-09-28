"""One-shot evaluation of the already-frozen Phase 7 configuration on holdout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ctxd.app.evals.phase7 import (
    apply_rank_guardrail,
    bootstrap_deltas,
    canonical_manifest_hash,
    lexical_protection_ids,
    partition_metrics,
    query_features,
    rank_delta_buckets,
    tokens,
    transition_counts,
)
from phase7_models import MINILM_L6, LocalOnnxReranker

OUTPUT = Path("benchmarks/phase7_holdout.json")
BOOTSTRAP_OUTPUT = Path("benchmarks/phase7_bootstrap.json")


def unique_paths(rows: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(str(row["source_path"]) for row in rows))


def rank_of(paths: list[str], expected: set[str]) -> int | None:
    return next((rank for rank, path in enumerate(paths, 1) if path in expected), None)


def exact_match_class(base: int | None, candidate: int | None) -> str:
    if base is None:
        return "relevant source absent from baseline candidate set"
    if candidate is None:
        return "relevant source absent after selected configuration"
    if base <= 3 and candidate > 10:
        return "catastrophically demoted"
    if candidate < base:
        return "improved"
    if candidate == base:
        return "preserved"
    return "demoted"


def main() -> None:
    if OUTPUT.exists() or BOOTSTRAP_OUTPUT.exists():
        raise FileExistsError("holdout evaluation has already run; do not rerun or tune on it")
    split = json.loads(Path("evals/phase7_split_manifest.json").read_text(encoding="utf-8"))
    config_bytes = Path("benchmarks/phase7_selected_config.json").read_bytes()
    config = json.loads(config_bytes)
    config_payload = {key: value for key, value in config.items() if key != "configuration_sha256"}
    if canonical_manifest_hash(config_payload) != config["configuration_sha256"]:
        raise ValueError("selected configuration checksum mismatch")
    pools = json.loads(Path("benchmarks/phase7_candidate_pools.json").read_text(encoding="utf-8"))
    if config["status"] != "frozen before holdout reranker evaluation":
        raise ValueError("selected configuration is not frozen")
    if config["split_manifest_sha256"] != split["split_manifest_sha256"]:
        raise ValueError("configuration split hash does not match holdout split")
    if pools["protocol"]["split_manifest_sha256"] != split["split_manifest_sha256"]:
        raise ValueError("candidate pools split hash does not match frozen split")
    if (
        config["selected_model"]["model_id"] != MINILM_L6.model_id
        or config["selected_model"]["revision"] != MINILM_L6.revision
    ):
        raise ValueError("selected model provenance does not match the local runner")
    if config["candidate_depth"] != 20:
        raise ValueError("the fixed candidate depth must remain 20")

    model = LocalOnnxReranker(
        MINILM_L6,
        cache_dir=Path.home() / ".cache/ctxd/phase7",
        intra_op_threads=int(config["threads"]),
        offline=True,
    )
    identity = model.identity()
    frozen_identity = config["selected_model"]
    for key in (
        "revision",
        "license",
        "onnx_artifact",
        "tokenizer_artifact",
        "maximum_input_length",
        "model_cache_total_bytes",
    ):
        if identity.get(key) != frozen_identity.get(key):
            raise ValueError(f"local model identity differs from frozen config: {key}")

    holdout = [case for case in pools["cases"] if case["partition"] == "holdout"]
    if len(holdout) != split["partition_counts"]["holdout"]:
        raise ValueError("holdout size does not match frozen split")
    if any(case["partition"] != "holdout" for case in holdout):
        raise AssertionError("development case entered holdout evaluation")
    strategy = str(config["guardrail"]["name"])
    result_cases: list[dict[str, Any]] = []
    paired_all: list[tuple[dict[str, float], dict[str, float]]] = []
    paired_nonambiguous: list[tuple[dict[str, float], dict[str, float]]] = []
    baselines_all: list[tuple[list[str], set[str]]] = []
    selected_all: list[tuple[list[str], set[str]]] = []
    baselines_nonambiguous: list[tuple[list[str], set[str]]] = []
    selected_nonambiguous: list[tuple[list[str], set[str]]] = []
    baseline_ranks: list[int | None] = []
    selected_ranks: list[int | None] = []
    exact_records: list[dict[str, Any]] = []
    inversion_cases: list[str] = []
    score_pairs: list[dict[str, Any]] = []
    regression_by_category: dict[str, list[str]] = {}
    for case in holdout:
        candidates = case["candidate_sources"]
        scores = model.score_pairs(
            str(case["query"]),
            [str(item["content"]) for item in candidates],
            batch_size=int(config["batch_size"]),
        )
        rrf_ordered = sorted(candidates, key=lambda item: int(item["rrf_rank"]))
        scored_by_id = {
            str(item["source_id"]): float(scores[index]) for index, item in enumerate(candidates)
        }
        score_by_id = dict(scored_by_id)
        feature_rows: list[dict[str, Any]] = []
        for item in rrf_ordered:
            overlap = sorted(set(tokens(case["query"])) & set(tokens(item["content"])))
            identifier_overlap = sorted(
                token
                for token in overlap
                if "_" in token or any(character.isdigit() for character in token)
            )
            feature_rows.append(
                {
                    "source_id": item["source_id"],
                    "source_path": item["source_path"],
                    "lexical_rank": item["lexical_rank"],
                    "lexical_raw_score": item["lexical_score"],
                    "exact_query_token_overlap": overlap,
                    "rare_identifier_overlap": identifier_overlap,
                    "rrf_rank": item["rrf_rank"],
                    "reranker_score": scored_by_id[str(item["source_id"])],
                }
            )
        protected = lexical_protection_ids(feature_rows, strategy)
        selected_rows = apply_rank_guardrail(feature_rows, score_by_id, protected)
        expected = set(case["expected_sources"])
        baseline_paths = unique_paths(rrf_ordered)
        selected_paths = unique_paths(selected_rows)
        base_rank = rank_of(baseline_paths, expected)
        selected_rank = rank_of(selected_paths, expected)
        baseline_ranks.append(base_rank)
        selected_ranks.append(selected_rank)
        baselines_all.append((baseline_paths, expected))
        selected_all.append((selected_paths, expected))
        ambiguous = case["annotation_status"] == "ambiguous"
        if not ambiguous:
            baselines_nonambiguous.append((baseline_paths, expected))
            selected_nonambiguous.append((selected_paths, expected))

        base_metrics = partition_metrics([(baseline_paths, expected)])
        selected_metrics = partition_metrics([(selected_paths, expected)])
        paired_all.append((base_metrics, selected_metrics))
        if not ambiguous:
            paired_nonambiguous.append((base_metrics, selected_metrics))
        transition = (
            "fixed"
            if base_rank != 1 and selected_rank == 1
            else "unchanged_correct"
            if base_rank == 1 and selected_rank == 1
            else "regressed"
            if base_rank is not None and (selected_rank is None or selected_rank > base_rank)
            else "unchanged_incorrect"
        )
        category = str(case["category"])
        if transition == "regressed":
            regression_by_category.setdefault(category, []).append(str(case["case_id"]))
        positive_scores: list[float] = []
        negative_scores: list[float] = []
        relevant_paths_seen: set[str] = set()
        for row in feature_rows:
            source_path = str(row["source_path"])
            if source_path in expected:
                if source_path not in relevant_paths_seen:
                    positive_scores.append(float(row["reranker_score"]))
                    relevant_paths_seen.add(source_path)
            else:
                negative_scores.append(float(row["reranker_score"]))
        inverted = bool(
            positive_scores and negative_scores and max(negative_scores) >= max(positive_scores)
        )
        if inverted:
            inversion_cases.append(str(case["case_id"]))
        score_pairs.append(
            {
                "case_id": case["case_id"],
                "relevant_proxy_scores": positive_scores,
                "nonrelevant_candidate_count": len(negative_scores),
                "score_inversion": inverted,
            }
        )
        query_info = query_features(
            str(case["query"]),
            [str(item["content"]) for item in candidates if item["source_path"] in expected],
        )
        if query_info["has_exact_term"]:
            exact_records.append(
                {
                    "case_id": case["case_id"],
                    "category": category,
                    "baseline_relevant_rank": base_rank,
                    "selected_relevant_rank": selected_rank,
                    "query_exact_tokens": query_info["exact_query_tokens"],
                    "identifier_overlap": query_info["exact_identifier_overlap"],
                    "classification": exact_match_class(base_rank, selected_rank),
                }
            )
        delta = (base_rank if base_rank is not None else 21) - (
            selected_rank if selected_rank is not None else 21
        )
        result_cases.append(
            {
                "case_id": case["case_id"],
                "category": category,
                "annotation_status": case["annotation_status"],
                "query": case["query"],
                "expected_sources": sorted(expected),
                "baseline_rank": base_rank,
                "selected_rank": selected_rank,
                "rank_delta_baseline_minus_selected": delta,
                "transition": transition,
                "protected_candidate_ids": sorted(protected),
                "baseline_metrics": base_metrics,
                "selected_metrics": selected_metrics,
                "model_scores_and_candidate_features": feature_rows,
            }
        )

    ambiguous_count = sum(case["annotation_status"] == "ambiguous" for case in holdout)
    if ambiguous_count != 2:
        raise ValueError("the two ambiguous cases must remain explicit in holdout")
    transition = transition_counts(baseline_ranks, selected_ranks)
    metrics_all = {
        "hybrid_rrf": partition_metrics(baselines_all),
        "selected_configuration": partition_metrics(selected_all),
    }
    metrics_nonambiguous = {
        "hybrid_rrf": partition_metrics(baselines_nonambiguous),
        "selected_configuration": partition_metrics(selected_nonambiguous),
    }
    bootstrap_all = bootstrap_deltas(
        [baseline for baseline, _ in paired_all],
        [selected for _, selected in paired_all],
        seed=7312026,
        resamples=1000,
    )
    bootstrap_nonambiguous = bootstrap_deltas(
        [baseline for baseline, _ in paired_nonambiguous],
        [selected for _, selected in paired_nonambiguous],
        seed=7312027,
        resamples=1000,
    )
    exact_summary = {
        key: sum(row["classification"] == key for row in exact_records)
        for key in (
            "preserved",
            "improved",
            "demoted",
            "catastrophically demoted",
            "relevant source absent from baseline candidate set",
            "relevant source absent after selected configuration",
        )
    }
    severe = [
        row
        for row in result_cases
        if row["baseline_rank"] is not None
        and row["baseline_rank"] <= 3
        and (row["selected_rank"] is None or row["selected_rank"] > 10)
    ]
    rank_buckets = rank_delta_buckets(
        [row["rank_delta_baseline_minus_selected"] for row in result_cases]
    )
    payload = {
        "evaluation": "one-shot frozen holdout; no model/threshold/feature retuning",
        "configuration_sha256": config["configuration_sha256"],
        "split_manifest_sha256": split["split_manifest_sha256"],
        "model_identity": identity,
        "partition_size": len(holdout),
        "ambiguous_case_ids": [
            case["case_id"] for case in holdout if case["annotation_status"] == "ambiguous"
        ],
        "metrics_including_ambiguous": metrics_all,
        "metrics_excluding_ambiguous": metrics_nonambiguous,
        "transitions_including_ambiguous": transition,
        "exact_match_classifications": exact_summary,
        "score_inversion_case_count": len(inversion_cases),
        "score_inversion_case_ids": inversion_cases,
        "semantic_paraphrase_improvements": [
            row["case_id"]
            for row in result_cases
            if row["category"] == "semantic paraphrase" and row["transition"] == "fixed"
        ],
        "near_duplicate_regressions": regression_by_category.get("near duplicate", []),
        "multiple_relevant_regressions": regression_by_category.get("multiple relevant", []),
        "severe_regressions_baseline_rank_le_3_to_selected_gt_10": severe,
        "rank_delta_distribution": rank_buckets,
        "rank_delta_convention": (
            "delta=baseline rank-selected rank; missing relevant source is assigned rank 21, "
            "one worse than the 20-candidate pool"
        ),
        "per_query": result_cases,
        "raw_score_pair_audit": score_pairs,
    }
    bootstrap = {
        "method": "paired query-level percentile bootstrap over per-case metric deltas",
        "resamples": 1000,
        "interval": "two-sided 95%, empirical 2.5th and 97.5th percentiles",
        "including_ambiguous": bootstrap_all,
        "excluding_ambiguous": bootstrap_nonambiguous,
        "interpretation": (
            "Small holdout; intervals quantify query-sample uncertainty, not corpus shift."
        ),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    BOOTSTRAP_OUTPUT.write_text(json.dumps(bootstrap, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "metrics_including_ambiguous": metrics_all,
                "metrics_excluding_ambiguous": metrics_nonambiguous,
                "transitions": transition,
                "exact": exact_summary,
                "rank_delta_distribution": rank_buckets,
                "severe_regressions": severe,
                "bootstrap": bootstrap_all,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
