"""Build a qualitative Phase 7 quality/latency frontier from frozen evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def main() -> None:
    comparison = json.loads(
        Path("benchmarks/phase7_dev_model_comparison.json").read_text(encoding="utf-8")
    )
    config = json.loads(Path("benchmarks/phase7_selected_config.json").read_text(encoding="utf-8"))
    holdout = json.loads(Path("benchmarks/phase7_holdout.json").read_text(encoding="utf-8"))
    performance = json.loads(Path("benchmarks/phase7_latency.json").read_text(encoding="utf-8"))
    dev_baseline = json.loads(
        Path("benchmarks/phase7_development_baseline.json").read_text(encoding="utf-8")
    )
    models: dict[str, Any] = {}
    for key, row in comparison["models"].items():
        models[key] = {
            "model_id": row["model_id"],
            "development_metrics": row["development_metrics"],
            "development_transitions": row["transitions"],
            "standalone_n20_latency_ms": row["standalone_n20_latency_ms"],
            "latency_scope": "development model comparison; N=20 standalone scorer timing",
        }
    mini = models["minilm_l6"]
    mini["selected_guarded_development_metrics"] = config["development_evidence"][
        "selected_model_guarded_metrics"
    ]
    mini["selected_guarded_development_transitions"] = config["development_evidence"][
        "selected_model_guarded_transitions"
    ]
    mini["selected_guarded_exact_match"] = config["development_evidence"][
        "selected_model_guarded_exact_match"
    ]
    mini["repeated_standalone_n20_latency_ms"] = performance["standalone_n20"]["timings"]["total"]
    mini["selected_guarded_end_to_end_12k_latency_ms"] = performance["end_to_end"]["12000"][
        "selected"
    ]["summary"]
    selected = holdout["metrics_including_ambiguous"]["selected_configuration"]
    rrf = holdout["metrics_including_ambiguous"]["hybrid_rrf"]
    payload = {
        "purpose": "qualitative quality/latency frontier; no scalar score or model retuning",
        "configuration_sha256": config["configuration_sha256"],
        "split_manifest_sha256": holdout["split_manifest_sha256"],
        "hybrid_rrf_development_metrics": dev_baseline["metrics"]["hybrid"]["all"],
        "hybrid_rrf_end_to_end_12k_latency_ms": performance["end_to_end"]["12000"]["hybrid"][
            "summary"
        ],
        "hybrid_rrf_holdout_metrics": rrf,
        "selected_configuration_holdout_metrics": selected,
        "models": models,
        "latency_comparability_warning": (
            "The original model-survey standalone timings, repeated MiniLM standalone timing, "
            "and PostgreSQL end-to-end timings have different scopes and observed host variance. "
            "Use them as separate coordinates, not as a strict apples-to-apples ranking."
        ),
        "decision": (
            "MiniLM exact-overlap guard is promising on nDCG@5 but uncertain on MRR and Recall@1; "
            "CPU latency/throughput cost is large. Keep offline and unexposed."
        ),
    }
    Path("benchmarks/phase7_frontier.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote benchmarks/phase7_frontier.json")


if __name__ == "__main__":
    main()
