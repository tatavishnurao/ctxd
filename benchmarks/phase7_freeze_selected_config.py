"""Freeze exactly one Phase 7 configuration from development-only evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ctxd.app.evals.phase7 import canonical_manifest_hash


def main() -> None:
    destination = Path("benchmarks/phase7_selected_config.json")
    if destination.exists():
        raise FileExistsError(f"selected configuration already frozen: {destination}")
    comparison = json.loads(
        Path("benchmarks/phase7_dev_model_comparison.json").read_text(encoding="utf-8")
    )
    guardrails = json.loads(
        Path("benchmarks/phase7_guardrail_dev.json").read_text(encoding="utf-8")
    )
    split = json.loads(Path("evals/phase7_split_manifest.json").read_text(encoding="utf-8"))
    if comparison["protocol"]["partition_evaluated"] != "development only":
        raise ValueError("model selection artifact is not development-only")
    if guardrails["partition"] != "development only":
        raise ValueError("guardrail selection artifact is not development-only")
    if comparison["protocol"]["split_manifest_sha256"] != split["split_manifest_sha256"]:
        raise ValueError("split manifest mismatch")

    selected_model = "minilm_l6"
    strategy = "protect_exact_overlap_top1"
    model_metrics = comparison["models"][selected_model]["development_metrics"]["all"]
    guarded = guardrails["models"][selected_model][strategy]
    bge = comparison["models"]["bge_reranker_base"]
    config: dict[str, object] = {
        "configuration_version": 1,
        "status": "frozen before holdout reranker evaluation",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "split_manifest_sha256": split["split_manifest_sha256"],
        "selection_partition": "development only",
        "selected_model": comparison["model_identity"][selected_model],
        "candidate_depth": 20,
        "candidate_pool": "parallel BM25 + exact pgvector + deterministic RRF, RRF k=60",
        "batch_size": 16,
        "threads": 4,
        "guardrail": {
            "name": strategy,
            "rule": (
                "If a candidate in the fixed RRF-20 pool has lexical_rank == 1 and its "
                "content shares at least one normalized query token, place that candidate "
                "first. Rerank every remaining candidate by model score descending; stable "
                "RRF rank breaks exact score ties. Otherwise rerank all 20."
            ),
            "signals": ["BM25 rank", "exact normalized query-token overlap"],
            "uses_ground_truth_or_category": False,
            "uses_query_rewrite_or_threshold_tuning": False,
        },
        "development_evidence": {
            "hybrid_baseline": json.loads(
                Path("benchmarks/phase7_development_baseline.json").read_text(encoding="utf-8")
            )["metrics"]["hybrid"]["all"],
            "selected_model_ungarded_metrics": model_metrics,
            "selected_model_guarded_metrics": guarded["metrics"],
            "selected_model_guarded_transitions": guarded["transitions"],
            "selected_model_guarded_exact_match": guarded["exact_match_classifications"],
            "selected_model_standalone_n20_latency": comparison["models"][selected_model][
                "standalone_n20_latency_ms"
            ],
            "competing_bge_development_mrr": bge["development_metrics"]["all"]["mrr"],
            "competing_bge_standalone_n20_latency": bge["standalone_n20_latency_ms"],
            "guardrail_sort_cost_ms_p50": guarded["guardrail_sort_cost_ms_p50"],
            "development_score_inversion_cases": comparison["models"][selected_model][
                "score_inversion_case_count"
            ],
            "holdout_metrics_read_for_selection": False,
        },
        "selection_rationale": (
            "MiniLM-L6 substantially improves development quality over TinyBERT and hybrid, "
            "has only two exact-match demotions and zero catastrophic demotions with the "
            "exact-overlap guard, adds no Python dependencies, and is far less costly than "
            "BGE-reranker-base. BGE's modest additional development gain does not justify "
            "its measured multi-second per-query CPU cost. This is an offline holdout-test "
            "configuration, not a production recommendation."
        ),
    }
    config["configuration_sha256"] = canonical_manifest_hash(config)
    destination.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "configuration_sha256": config["configuration_sha256"],
                "model": comparison["model_identity"][selected_model]["model_id"],
                "revision": comparison["model_identity"][selected_model]["revision"],
                "strategy": strategy,
                "development_metrics": guarded["metrics"],
                "transitions": guarded["transitions"],
                "exact_match": guarded["exact_match_classifications"],
                "holdout_results_read": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
