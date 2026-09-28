"""Repair development record labels from frozen rank evidence; no model rerun."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ctxd.app.evals.phase7 import transition_label

PATH = Path("benchmarks/phase7_dev_model_comparison.json")


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    for model in payload["models"].values():
        rows = model["per_query_development_records"]
        for row in rows:
            row["transition"] = transition_label(
                row["baseline_relevant_rank"], row["reranked_relevant_rank"]
            )
        counts = Counter(row["transition"] for row in rows)
        counts = {
            key: counts[key]
            for key in ("fixed", "regressed", "unchanged_correct", "unchanged_incorrect")
        }
        if counts != model["transitions"]:
            raise ValueError("record labels do not reconcile with frozen transition totals")
        categories = sorted({row["category"] for row in rows})
        model["category_regression_counts"] = {
            category: sum(
                row["category"] == category and row["transition"] == "regressed" for row in rows
            )
            for category in categories
        }
    PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("corrected per-query development transition labels from stored ranks")


if __name__ == "__main__":
    main()
