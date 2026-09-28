"""Audit frozen evidence and run development-only source-proxy diagnostics.

No holdout policy selection/evaluation and no model calls. Historical artifacts are read-only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from ctxd.app.evals.context_selection import (
    Packing,
    SelectionCandidate,
    budget_metrics,
    pack,
    should_rerank,
    source_metrics,
)
from ctxd.app.evals.phase7 import apply_rank_guardrail, partition_metrics
from ctxd.app.evals.retrieval import ndcg_at_k


def candidates(rows: list[dict[str, Any]]) -> list[SelectionCandidate]:
    return [
        SelectionCandidate(
            str(r["source_id"]),
            str(r["source_path"]),
            str(r["content"]),
            int(r["token_cost"]),
            r["lexical_rank"],
            r["semantic_rank"],
        )
        for r in rows
    ]


def average(rows: list[dict[str, float]]) -> dict[str, float]:
    return {key: mean(row[key] for row in rows) for key in rows[0]}


def main() -> None:
    output = Path("benchmarks/phase8_audit.json")
    if output.exists():
        raise FileExistsError(output)
    initial = json.loads(Path("benchmarks/phase8_initial_manifest.json").read_text())
    for name, checksum in initial["historical_artifacts"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f"historical evidence changed: {name}")
    pools = json.loads(Path("benchmarks/phase7_candidate_pools.json").read_text())["cases"]
    model = json.loads(Path("benchmarks/phase7_dev_model_comparison.json").read_text())["models"][
        "minilm_l6"
    ]
    scores = {
        r["case_id"]: {c["source_id"]: c["reranker_score"] for c in r["ranked_candidates"]}
        for r in model["per_query_development_records"]
    }
    guard = json.loads(Path("benchmarks/phase7_guardrail_dev.json").read_text())["models"][
        "minilm_l6"
    ]["protect_exact_overlap_top1"]
    # Use frozen protection decisions, not a newly tuned protection function.
    protected = {r["case_id"]: set(r["protected_candidate_ids"]) for r in guard["per_query"]}
    dev = [r for r in pools if r["partition"] == "development"]
    ranking_rows: dict[str, list[dict[str, float]]] = {
        name: []
        for name in ("hybrid", "always", "disagreement", "no_lexical_winner", "top_rrf_not_lexical")
    }
    decisions: dict[str, int] = dict.fromkeys(ranking_rows, 0)
    packing_rows: dict[str, list[dict[str, float]]] = {}
    per_query = []
    policies: tuple[Packing, ...] = ("greedy", "density", "unique_source", "exact_duplicate")
    for case in dev:
        pool = case["candidate_sources"]
        base = candidates(pool)
        ordered = apply_rank_guardrail(pool, scores[case["case_id"]], protected[case["case_id"]])
        reranked = candidates(ordered)
        relevant = set(case["expected_sources"])
        query_record: dict[str, Any] = {"case_id": case["case_id"], "ranking": {}, "packing": {}}
        for policy in ranking_rows:
            decision = policy == "always" or (policy != "hybrid" and should_rerank(base, policy))
            decisions[policy] += decision
            selected = reranked if decision else base
            metrics = source_metrics([c.source for c in selected], relevant)
            ranking_rows[policy].append(metrics)
            query_record["ranking"][policy] = {"reranked": decision, **metrics}
        # Separate top10 production-return-size proxy and N20 candidate-pool experiment.
        for width in (10, 20):
            for budget in (256, 512, 1024, 2048, 4096):
                for policy in policies:
                    key = f"n{width}/b{budget}/{policy}"
                    selected = pack(base[:width], budget, policy)
                    metrics = budget_metrics(base[:width], selected, relevant)
                    packing_rows.setdefault(key, []).append(metrics)
                    query_record["packing"][key] = metrics
        per_query.append(query_record)
    ranking = {
        name: {
            "metrics": average(rows),
            "fraction_reranked": decisions[name] / len(dev),
            "mrr_improved": sum(
                r["mrr"] > b["mrr"] for r, b in zip(rows, ranking_rows["hybrid"], strict=True)
            ),
            "mrr_regressed": sum(
                r["mrr"] < b["mrr"] for r, b in zip(rows, ranking_rows["hybrid"], strict=True)
            ),
        }
        for name, rows in ranking_rows.items()
    }
    historical_metric_comparison = {}
    for partition in ("development", "holdout"):
        cases = [r for r in pools if r["partition"] == partition]
        historical_metric_comparison[partition] = {
            "duplicate_source_pools": sum(
                len({c["source_path"] for c in r["candidate_sources"]})
                < len(r["candidate_sources"])
                for r in cases
            ),
            "collapsed_source_metrics": partition_metrics(
                [
                    (
                        list(dict.fromkeys(c["source_path"] for c in r["candidate_sources"])),
                        set(r["expected_sources"]),
                    )
                    for r in cases
                ]
            ),
            "chunk_position_source_metrics": average(
                [
                    source_metrics(
                        [c["source_path"] for c in r["candidate_sources"]],
                        set(r["expected_sources"]),
                    )
                    for r in cases
                ]
            ),
        }
    result = {
        "status": "correctness-first diagnostic; no policy frozen or promoted",
        "historical_artifacts_verified": len(initial["historical_artifacts"]),
        "ndcg_duplicate_counterexample": ndcg_at_k(["a", "a"], {"a"}, 5),
        "corrected_duplicate_counterexample": source_metrics(["a", "a"], {"a"})["ndcg_at_5"],
        "historical_baseline_audit": historical_metric_comparison,
        "development_ranking": ranking,
        "development_packing": {key: average(rows) for key, rows in packing_rows.items()},
        "limitations": [
            "binary source labels, not graded or chunk evidence judgments",
            "holdout already observed in Phase 7; not fresh confirmatory evidence",
            "top10 proxy uses prefix of cached N20, not a new production request",
            "policy latency not estimated from unrelated aggregate p95s",
            "unique-source suppression can discard complementary evidence",
        ],
        "per_query_development": per_query,
    }
    with output.open("x") as file:
        json.dump(result, file, indent=2)
    print(json.dumps({"ranking": ranking, "audit": historical_metric_comparison}, indent=2))


if __name__ == "__main__":
    main()
