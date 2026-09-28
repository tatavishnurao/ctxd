"""One-shot frozen-policy replay; never calls a model or tunes on holdout."""

import hashlib
import json
from pathlib import Path
from statistics import mean

from ctxd.app.evals.context_selection import SelectionCandidate, should_rerank, source_metrics
from ctxd.app.evals.phase7 import apply_rank_guardrail, bootstrap_deltas, tokens, transition_counts


def main() -> None:
    output = Path("benchmarks/phase8_holdout.json")
    if output.exists():
        raise FileExistsError(output)
    config = json.loads(Path("benchmarks/phase8_selected_config.json").read_text())
    digest = config.pop("sha256")
    if hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest() != digest:
        raise ValueError("configuration checksum mismatch")
    if (
        hashlib.sha256(Path(config["model_config"]).read_bytes()).hexdigest()
        != config["model_config_file_sha256"]
    ):
        raise ValueError("model config changed")
    if (
        hashlib.sha256(Path("benchmarks/phase8_audit.json").read_bytes()).hexdigest()
        != config["development_evidence_sha256"]
    ):
        raise ValueError("development evidence changed")
    pools = json.loads(Path("benchmarks/phase7_candidate_pools.json").read_text())["cases"]
    stored = json.loads(Path("benchmarks/phase7_holdout.json").read_text())["per_query"]
    records = {r["case_id"]: r for r in stored}
    results = []
    for case in pools:
        if case["partition"] != "holdout":
            continue
        pool = case["candidate_sources"]
        row = records[case["case_id"]]
        scores = {
            r["source_id"]: r["reranker_score"] for r in row["model_scores_and_candidate_features"]
        }
        always = apply_rank_guardrail(pool, scores, set(row["protected_candidate_ids"]))
        candidates = [
            SelectionCandidate(
                r["source_id"],
                r["source_path"],
                r["content"],
                r["token_cost"],
                r["lexical_rank"],
                r["semantic_rank"],
            )
            for r in pool
        ]
        decision = should_rerank(candidates, config["policy"])
        relevant = set(case["expected_sources"])
        orders = {"hybrid": pool, "always": always, "selective": always if decision else pool}
        metrics = {
            name: source_metrics([r["source_path"] for r in order], relevant)
            for name, order in orders.items()
        }
        ranks = {
            name: next((i for i, r in enumerate(order, 1) if r["source_path"] in relevant), None)
            for name, order in orders.items()
        }
        exact = bool(
            set(tokens(case["query"]))
            & set().union(
                *[set(tokens(r["content"])) for r in pool if r["source_path"] in relevant]
            )
        )
        results.append(
            {
                "case_id": case["case_id"],
                "ambiguous": case["annotation_status"] == "ambiguous",
                "reranked": decision,
                "metrics": metrics,
                "ranks": ranks,
                "exact_overlap": exact,
            }
        )
    summary = {}
    for sensitivity in ("all", "excluding_ambiguous"):
        rows = [r for r in results if sensitivity == "all" or not r["ambiguous"]]
        baseline = [r["metrics"]["hybrid"] for r in rows]
        modes = {}
        for mode in ("hybrid", "always", "selective"):
            metrics = [r["metrics"][mode] for r in rows]
            transitions = transition_counts(
                [r["ranks"]["hybrid"] for r in rows], [r["ranks"][mode] for r in rows]
            )
            modes[mode] = {
                "metrics": {key: mean(r[key] for r in metrics) for key in metrics[0]},
                "transitions": transitions,
                "bootstrap_vs_hybrid": bootstrap_deltas(
                    baseline, metrics, seed=812026, resamples=2000
                ),
                "exact_overlap_demotions": sum(
                    r["exact_overlap"] and r["metrics"][mode]["mrr"] < r["metrics"]["hybrid"]["mrr"]
                    for r in rows
                ),
            }
        summary[sensitivity] = {
            "count": len(rows),
            "fraction_reranked": mean(r["reranked"] for r in rows),
            "modes": modes,
        }
    with output.open("x") as file:
        json.dump(
            {
                "config_sha256": digest,
                "scope": config["holdout_method"],
                "limitation": config["holdout_limitation"],
                "summary": summary,
                "per_query": results,
            },
            file,
            indent=2,
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
