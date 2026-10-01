"""Read-only result analysis; no policy tuning, retrieval, or holdout rerun."""

import json
from pathlib import Path
from statistics import mean

from ctxd.app.evals.evidence import EvidenceCase, EvidenceCorpus
from ctxd.app.evals.phase7 import tokens


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def main() -> None:
    corpus = EvidenceCorpus.model_validate(load("evals/phase9_evidence_cases.json"))
    cases = {c.case_id: c for c in corpus.cases}
    dev = load("benchmarks/phase9_packing_dev.json")
    holdout = load("benchmarks/phase9_holdout.json")
    config = load("benchmarks/phase9_selected_config.json")
    changes = []
    reranker = {}
    for budget in (256, 512, 1024, 2048, 4096):
        baseline = {
            r["case_id"]: r
            for r in holdout["rows"]
            if r["budget"] == budget and r["policy"] == "greedy"
        }
        selected = {
            r["case_id"]: r
            for r in holdout["rows"]
            if r["budget"] == budget and r["policy"] == config["policy"]
        }
        for case_id, old in baseline.items():
            new = selected[case_id]
            case = cases[case_id]

            def covered(ids: list[str], evidence_case: EvidenceCase = case) -> set[str]:
                return {
                    g.group_id
                    for g in evidence_case.evidence_groups
                    if g.requirement == "REQUIRED"
                    and any({s.chunk_id for s in a.spans} <= set(ids) for a in g.alternatives)
                }

            lost = covered(old["selected_chunks"]) - covered(new["selected_chunks"])
            gained = covered(new["selected_chunks"]) - covered(old["selected_chunks"])
            if old["selected_chunks"] != new["selected_chunks"]:
                changes.append(
                    {
                        "case_id": case_id,
                        "query": case.query,
                        "budget": budget,
                        "required_groups": [
                            g.model_dump()
                            for g in case.evidence_groups
                            if g.requirement == "REQUIRED"
                        ],
                        "baseline_chunks": old["selected_chunks"],
                        "candidate_chunks": new["selected_chunks"],
                        "evidence_groups_lost": sorted(lost),
                        "evidence_groups_gained": sorted(gained),
                        "tokens_saved": old["metrics"]["selected_tokens"]
                        - new["metrics"]["selected_tokens"],
                        "reason": (
                            "exact duplicate skipped; later fitting chunks admitted; "
                            "no semantic cause inferred"
                        ),
                    }
                )
        base_dev = {
            r["case_id"]: r
            for r in dev["rows"]
            if r["budget"] == budget and r["mode"] == "hybrid" and r["policy"] == "greedy"
        }
        for mode in ("always", "selective"):
            new_dev = {
                r["case_id"]: r for r in dev["rows"] if r["budget"] == budget and r["mode"] == mode
            }
            regressions = []
            improvements = []
            exact_demotions = []
            for case_id, old in base_dev.items():
                new = new_dev[case_id]
                if new["metrics"]["required_recall"] < old["metrics"]["required_recall"]:
                    regressions.append(case_id)
                if new["metrics"]["required_recall"] > old["metrics"]["required_recall"]:
                    improvements.append(case_id)
                case = cases[case_id]
                exact = set(tokens(case.query)) & set().union(
                    *[
                        set(tokens(s.excerpt))
                        for g in case.evidence_groups
                        if g.requirement == "REQUIRED"
                        for a in g.alternatives
                        for s in a.spans
                    ]
                )
                if exact and new["metrics"]["mrr"] < old["metrics"]["mrr"]:
                    exact_demotions.append(case_id)
            reranker[f"{mode}/{budget}"] = {
                "evidence_regressions": regressions,
                "evidence_improvements": improvements,
                "exact_token_overlap_mrr_demotions": exact_demotions,
            }
    positions = {}
    for stage, result in (("development", dev), ("holdout", holdout)):
        for budget in (256, 512, 1024, 2048, 4096):
            rows = [
                r
                for r in result["rows"]
                if r["mode"] == "hybrid" and r["policy"] == "greedy" and r["budget"] == budget
            ]
            buckets = {name: [0, 0] for name in ("first", "later")}
            for row in rows:
                case = cases[row["case_id"]]
                for g in case.evidence_groups:
                    if g.requirement != "REQUIRED":
                        continue
                    # Groups can have alternate chunks at different ordinals: classify by minimum.
                    ids = {s.chunk_id for a in g.alternatives for s in a.spans}
                    ordinal = min(c.ordinal for c in corpus.chunks if c.chunk_id in ids)
                    bucket = buckets["first" if ordinal == 0 else "later"]
                    bucket[0] += 1
                    bucket[1] += any(
                        {s.chunk_id for s in a.spans} <= set(row["selected_chunks"])
                        for a in g.alternatives
                    )
            positions[f"{stage}/{budget}"] = buckets
    pressure = {}
    for stage in ("development", "holdout"):
        values = json.loads(Path(f"benchmarks/phase9_{stage}_budget_pressure.json").read_text())
        for budget in (256, 512, 1024, 2048, 4096):
            rows = [r for r in values if r["budget"] == budget]
            pressure[f"{stage}/{budget}"] = {
                "whole_corpus_feasible_fraction": mean(
                    r["all_chunk_oracle_tokens"] <= budget for r in rows
                ),
                "top10_feasible_fraction": mean(
                    r["retrieved_top10_oracle_tokens"] is not None
                    and r["retrieved_top10_oracle_tokens"] <= budget
                    for r in rows
                ),
                "budget_drops_fraction": mean(r["dropped_count"] > 0 for r in rows),
            }
    with Path("benchmarks/phase9_case_analysis.json").open("x") as file:
        json.dump(
            {
                "holdout_changes": changes,
                "development_reranker": reranker,
                "position_counts_total_then_selected": positions,
                "pressure": pressure,
                "challenge": "not run; current corpus itself is an authored stress fixture",
            },
            file,
            indent=2,
        )

    chunks = {c.chunk_id: c for c in corpus.chunks}
    gaps = []
    for stage, result in (("development", dev), ("holdout", holdout)):
        for row in result["rows"]:
            if row["mode"] != "hybrid" or row["policy"] != "greedy":
                continue
            sources = {str(chunks[i].metadata["source_path"]) for i in row["selected_chunks"]}
            groups = [
                g for g in cases[row["case_id"]].evidence_groups if g.requirement == "REQUIRED"
            ]
            proxy = all(
                any({s.source for s in a.spans} <= sources for a in g.alternatives) for g in groups
            )
            if proxy and not row["metrics"]["full_answerability"]:
                gaps.append(
                    {
                        "stage": stage,
                        "case_id": row["case_id"],
                        "budget": row["budget"],
                        "selected_chunks": row["selected_chunks"],
                        "required_recall": row["metrics"]["required_recall"],
                    }
                )
    with Path("benchmarks/phase9_source_proxy_gap.json").open("x") as file:
        json.dump(
            {
                "definition": (
                    "source-only group coverage says full, exact-span group coverage does not"
                ),
                "cases": gaps,
            },
            file,
            indent=2,
        )


if __name__ == "__main__":
    main()
