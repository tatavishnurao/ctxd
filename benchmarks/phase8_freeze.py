"""Freeze a development-selected diagnostic policy before holdout replay."""

import hashlib
import json
from pathlib import Path


def main() -> None:
    evidence_path = Path("benchmarks/phase8_audit.json")
    evidence = json.loads(evidence_path.read_text())
    chosen = evidence["development_ranking"]["no_lexical_winner"]
    if chosen["mrr_regressed"] or chosen["fraction_reranked"] > 0.10:
        raise ValueError("selected policy does not meet development cost/regression criteria")
    config = {
        "policy": "no_lexical_winner",
        "reason": "development: zero first-relevant-rank regressions and <10% model calls",
        "model_config": "benchmarks/phase7_selected_config.json",
        "model_config_file_sha256": hashlib.sha256(
            Path("benchmarks/phase7_selected_config.json").read_bytes()
        ).hexdigest(),
        "development_evidence_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        "ranking_metric": "unique-source credit at original chunk positions; binary judgments",
        "holdout_method": "one replay of stored Phase 7 scores, no inference or parameter changes",
        "holdout_limitation": "previously observed Phase 7 holdout, not an independent fresh test",
        "production_gate": (
            "positive 95% paired intervals for Recall@1, MRR, nDCG@5; "
            "zero rank regressions; independent evidence required"
        ),
        "packing_decision": (
            "retain greedy; dev budgets mostly inactive; no evidence-span judgments"
        ),
        "production_enabled": False,
    }
    config["sha256"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    with Path("benchmarks/phase8_selected_config.json").open("x") as file:
        json.dump(config, file, indent=2)
    print(config["sha256"])


if __name__ == "__main__":
    main()
