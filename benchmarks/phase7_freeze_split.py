"""Freeze the Phase 7 development/holdout split before reranker evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ctxd.app.evals.phase7 import (
    canonical_manifest_hash,
    normalized_category,
    query_features,
    stratified_partitions,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus", type=Path, default=Path("evals/retrieval_semantic_phase6_audited.json")
    )
    parser.add_argument("--output", type=Path, default=Path("evals/phase7_split_manifest.json"))
    parser.add_argument("--seed", type=int, default=731)
    parser.add_argument("--holdout-fraction", type=float, default=0.30)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"split is already frozen: {args.output}; do not overwrite it")

    corpus_bytes = args.corpus.read_bytes()
    corpus = json.loads(corpus_bytes)
    partitions = stratified_partitions(
        corpus["cases"], seed=args.seed, holdout_fraction=args.holdout_fraction
    )
    if len(partitions) != len(corpus["cases"]):
        raise AssertionError("each source case must occur exactly once")
    questions_by_partition: dict[str, set[str]] = {"development": set(), "holdout": set()}
    for case in corpus["cases"]:
        questions_by_partition[partitions[case["id"]]].add(
            " ".join(case["question"].casefold().split())
        )
    if questions_by_partition["development"] & questions_by_partition["holdout"]:
        raise AssertionError("identical queries crossed the partition boundary")

    document_contents: dict[tuple[str, str], str] = {
        (document.get("tenant_id", "eval"), document["source_path"]): document["content"]
        for document in corpus["documents"]
    }
    case_records = []
    distribution: dict[str, dict[str, int]] = {
        "development": Counter(),
        "holdout": Counter(),
    }
    ambiguous: list[dict[str, str]] = []
    for case in corpus["cases"]:
        partition = partitions[case["id"]]
        category = normalized_category(case)
        distribution[partition][category] += 1
        contents = [
            document_contents[(case.get("tenant_id", "eval"), path)]
            for path in case["expected_sources"]
            if (case.get("tenant_id", "eval"), path) in document_contents
        ]
        record: dict[str, Any] = {
            "case_id": case["id"],
            "partition": partition,
            "category": category,
            "relevance_count": len(case["expected_sources"]),
            **query_features(case["question"], contents),
            "annotation_status": case.get("metadata", {}).get(
                "phase6_annotation_status", "unspecified"
            ),
        }
        case_records.append(record)
        if record["annotation_status"] == "ambiguous":
            ambiguous.append({"case_id": case["id"], "partition": partition})

    manifest: dict[str, Any] = {
        "manifest_version": 1,
        "phase": "Phase 7 frozen split",
        "seed": args.seed,
        "holdout_fraction_target": args.holdout_fraction,
        "grouping_policy": "identical normalized query strings stay in one partition",
        "stratification_policy": (
            "seeded shuffling within primary annotation category; ambiguous duplicate-query "
            "group kept intact and assigned to holdout"
        ),
        "source_corpus": str(args.corpus),
        "source_corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_base_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "case_count": len(case_records),
        "partition_counts": dict(Counter(record["partition"] for record in case_records)),
        "category_distribution": {
            partition: dict(sorted(counts.items())) for partition, counts in distribution.items()
        },
        "ambiguous_cases": ambiguous,
        "identical_query_leakage_count": 0,
        "cases": case_records,
    }
    manifest["split_manifest_sha256"] = canonical_manifest_hash(manifest)
    args.output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in (
                    "partition_counts",
                    "category_distribution",
                    "ambiguous_cases",
                    "source_corpus_sha256",
                    "split_manifest_sha256",
                    "git_base_sha",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
