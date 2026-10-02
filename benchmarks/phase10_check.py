"""Fail closed on review or corpus-design gaps, before any database/model access."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from benchmarks.phase10_review import ROOT, load
from ctxd.app.evals.evidence import digest
from ctxd.app.evals.review import feasibility, require_review_gate


def eligibility(state_path: Path, root: Path = ROOT) -> dict[str, object]:
    corpus, assignments, state = load(state_path, root)
    protocol = json.loads((root / "benchmarks/phase10_protocol.json").read_text())
    design = protocol["design_gate"]
    chunks = {c.chunk_id: c for c in corpus.chunks}
    review_errors = []
    try:
        require_review_gate(corpus.cases, assignments, state, state.dataset_sha256)
    except ValueError as exc:
        review_errors.append(str(exc))
    design_errors = []
    if len(corpus.cases) < design["minimum_queries"]:
        design_errors.append("fewer than minimum queries")
    if len({c.template_group for c in corpus.cases}) < design["minimum_families"]:
        design_errors.append("fewer than minimum independent source/template groups")
    if (
        len({c.template_group for c in corpus.cases if assignments[c.case_id] == "holdout"})
        < design["minimum_holdout_families"]
    ):
        design_errors.append("too few holdout source/template families")
    distributions = {}
    for partition in ("development", "holdout"):
        subset = [c for c in corpus.cases if assignments[c.case_id] == partition]
        counts = Counter(str(feasibility(c, chunks)["stratum"]) for c in subset)
        distributions[partition] = dict(counts)
        for stratum in design["strata"]:
            if counts[stratum] < design["minimum_cases_per_stratum_per_partition"]:
                design_errors.append(f"{partition}: too few {stratum} cases")
        if (
            subset
            and max(counts.values()) / len(subset)
            > design["maximum_single_stratum_fraction_per_partition"]
        ):
            design_errors.append(f"{partition}: single-stratum dominance exceeds limit")
    approved = sum(r.reviewer_status == "APPROVED" for r in state.records)
    return {
        "phase": 10,
        "canonical_eligible": not review_errors and not design_errors,
        "status": "BLOCKED" if review_errors or design_errors else "ELIGIBLE_FOR_AUTHORIZED_RUN",
        "label": "PROVISIONAL — NOT INDEPENDENTLY REVIEWED"
        if review_errors
        else "REVIEW_GATE_PASSED",
        "dataset_sha256": state.dataset_sha256,
        "split_sha256": digest(assignments),
        "protocol_sha256": digest(protocol),
        "review_sha256": digest(state.model_dump(mode="json")),
        "case_count": len(corpus.cases),
        "document_count": len(corpus.documents),
        "chunk_count": len(corpus.chunks),
        "approved_cases": approved,
        "review_status_counts": dict(Counter(r.reviewer_status for r in state.records)),
        "review_errors": review_errors,
        "design_errors": design_errors,
        "strata": distributions,
        "selected_policy": None,
        "retrieval_benchmark": "NOT_RUN",
        "packing_search": "NOT_RUN",
        "reranker_replay": "NOT_RUN",
        "holdout": "NOT_RUN",
        "bootstrap": "NOT_RUN",
        "metrics": None,
        "production_changes": False,
        "note": "Eligibility only; no holdout markers, database access or model execution.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision-root", type=Path, default=ROOT)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = eligibility(
        args.reviews or args.revision_root / "evals/phase10_review_state.json", args.revision_root
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with args.output.open("x") as output:
            output.write(rendered)
    print(rendered)
    if not result["canonical_eligible"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
