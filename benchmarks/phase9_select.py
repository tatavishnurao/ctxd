"""Development-only selection; no reading holdout results or labels."""

import json
from pathlib import Path

from ctxd.app.evals.evidence import digest


def main() -> None:
    development = json.loads(Path("benchmarks/phase9_packing_dev.json").read_text())
    baseline = {
        (r["case_id"], r["budget"]): r
        for r in development["rows"]
        if r["mode"] == "hybrid" and r["policy"] == "greedy"
    }
    eligible = []
    reasons = {}
    for policy in ("density", "unique_source", "exact_duplicate"):
        rows = [r for r in development["rows"] if r["mode"] == "hybrid" and r["policy"] == policy]
        regressions = sum(
            any(
                r["metrics"][key] < baseline[r["case_id"], r["budget"]]["metrics"][key]
                for key in ("full_answerability", "required_recall", "supporting_recall")
            )
            for r in rows
        )
        tokens = sum(r["metrics"]["selected_tokens"] for r in rows)
        base_tokens = sum(r["metrics"]["selected_tokens"] for r in baseline.values())
        answerability = sum(r["metrics"]["full_answerability"] for r in rows)
        base_answerability = sum(r["metrics"]["full_answerability"] for r in baseline.values())
        passes = (
            regressions == 0
            and tokens <= base_tokens
            and (tokens <= 0.95 * base_tokens or answerability > base_answerability)
        )
        reasons[policy] = {
            "regressing_case_budget_cells": regressions,
            "selected_tokens_sum": tokens,
            "base_tokens_sum": base_tokens,
            "full_answerability_sum": answerability,
            "passes": passes,
        }
        if passes:
            eligible.append((-answerability, tokens, policy))
    chosen = sorted(eligible)[0][2] if eligible else "greedy"
    config = {
        "policy": chosen,
        "mode": "hybrid",
        "top_k": 10,
        "candidate_depth": 20,
        "dataset_sha256": development["dataset_sha256"],
        "split_sha256": development["split_sha256"],
        "development_sha256": digest(development),
        "reasons": reasons,
        "rule": "zero per-case-budget evidence regressions, no aggregate token increase; "
        "at least 5% token reduction or answerability increase; "
        "maximize answerability then minimize tokens then lexical policy name",
        "production_enabled": False,
        "promotion_caveat": "synthetic fixtures alone cannot justify production promotion",
    }
    config["sha256"] = digest(config)
    with Path("benchmarks/phase9_selected_config.json").open("x") as file:
        json.dump(config, file, indent=2)
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    main()
