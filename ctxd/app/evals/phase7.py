from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from ctxd.app.evals.retrieval import ndcg_at_k, recall_at_k, reciprocal_rank

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


def tokens(text: str) -> tuple[str, ...]:
    return tuple(TOKEN_PATTERN.findall(text.casefold()))


def query_features(query: str, expected_contents: Sequence[str]) -> dict[str, Any]:
    query_tokens = set(tokens(query))
    expected_tokens = set().union(*(set(tokens(text)) for text in expected_contents))
    exact_overlap = sorted(query_tokens & expected_tokens)
    identifiers = sorted(
        token
        for token in query_tokens
        if "_" in token or any(character.isdigit() for character in token)
    )
    identifier_overlap = sorted(set(identifiers) & expected_tokens)
    length = len(tokens(query))
    bucket = "1-3" if length <= 3 else "4-7" if length <= 7 else "8+"
    return {
        "query_length": length,
        "query_length_bucket": bucket,
        "has_exact_term": bool(exact_overlap),
        "exact_query_tokens": exact_overlap,
        "has_identifier": bool(identifiers),
        "has_exact_identifier_overlap": bool(identifier_overlap),
        "exact_identifier_overlap": identifier_overlap,
    }


def normalized_category(case: Mapping[str, Any]) -> str:
    return str(case.get("metadata", {}).get("category", case.get("task_type", "unknown"))).replace(
        "_", " "
    )


def canonical_manifest_hash(manifest: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "split_manifest_sha256"}
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def stratified_partitions(
    cases: Sequence[Mapping[str, Any]], *, seed: int, holdout_fraction: float = 0.30
) -> dict[str, str]:
    """Seeded category-stratified split; identical query strings stay in one partition."""
    if not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be between zero and one")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[" ".join(tokens(str(case["question"])))].append(case)

    by_category: dict[str, list[list[Mapping[str, Any]]]] = defaultdict(list)
    for group in grouped.values():
        counts = Counter(normalized_category(case) for case in group)
        category = sorted(counts, key=lambda value: (-counts[value], value))[0]
        by_category[category].append(group)

    rng = random.Random(seed)
    assignments: dict[str, str] = {}
    for category, groups in sorted(by_category.items()):
        rng.shuffle(groups)
        category_cases = [case for group in groups for case in group]
        target = len(category_cases) * holdout_fraction
        selected_count = 0
        # Keep all repeated-query cases together. For two-case ambiguity strata, put
        # the whole group in holdout rather than silently excluding ambiguity.
        for group in groups:
            size = len(group)
            if category == "ambiguous" and len(category_cases) <= 4:
                selected = True
            else:
                selected = abs(selected_count + size - target) < abs(selected_count - target)
            if selected:
                selected_count += size
                partition = "holdout"
            else:
                partition = "development"
            for case in group:
                assignments[str(case["id"])] = partition
    if set(assignments) != {str(case["id"]) for case in cases}:
        raise ValueError("split did not assign every case exactly once")
    return assignments


def partition_metrics(rows: Sequence[tuple[list[str], set[str]]]) -> dict[str, float]:
    if not rows:
        raise ValueError("cannot compute retrieval metrics for an empty partition")
    count = len(rows)
    return {
        "recall_at_1": sum(recall_at_k(got, relevant, 1) for got, relevant in rows) / count,
        "recall_at_5": sum(recall_at_k(got, relevant, 5) for got, relevant in rows) / count,
        "recall_at_10": sum(recall_at_k(got, relevant, 10) for got, relevant in rows) / count,
        "mrr": sum(reciprocal_rank(got, relevant) for got, relevant in rows) / count,
        "ndcg_at_5": sum(ndcg_at_k(got, relevant, 5) for got, relevant in rows) / count,
        "ndcg_at_10": sum(ndcg_at_k(got, relevant, 10) for got, relevant in rows) / count,
        "candidate_recall_at_20": sum(
            len(set(got[:20]) & relevant) / len(relevant) for got, relevant in rows
        )
        / count,
    }


def transition_counts(
    baseline_ranks: Sequence[int | None], candidate_ranks: Sequence[int | None]
) -> dict[str, int]:
    if len(baseline_ranks) != len(candidate_ranks):
        raise ValueError("rank arrays must have equal length")
    counts: Counter[str] = Counter()
    for baseline, candidate in zip(baseline_ranks, candidate_ranks, strict=True):
        if baseline != 1 and candidate == 1:
            counts["fixed"] += 1
        elif baseline == 1 and candidate == 1:
            counts["unchanged_correct"] += 1
        elif baseline == 1 and candidate != 1:
            counts["regressed"] += 1
        else:
            counts["unchanged_incorrect"] += 1
    return {
        key: counts[key]
        for key in ("fixed", "regressed", "unchanged_correct", "unchanged_incorrect")
    }


def rank_delta_buckets(deltas: Sequence[int]) -> dict[str, int]:
    buckets = {
        "+10 or more": 0,
        "+5 to +9": 0,
        "+1 to +4": 0,
        "0": 0,
        "-1 to -4": 0,
        "-5 to -9": 0,
        "-10 or worse": 0,
    }
    for delta in deltas:
        if delta >= 10:
            key = "+10 or more"
        elif delta >= 5:
            key = "+5 to +9"
        elif delta > 0:
            key = "+1 to +4"
        elif delta == 0:
            key = "0"
        elif delta >= -4:
            key = "-1 to -4"
        elif delta >= -9:
            key = "-5 to -9"
        else:
            key = "-10 or worse"
        buckets[key] += 1
    return buckets


def bootstrap_deltas(
    baseline: Sequence[Mapping[str, float]],
    candidate: Sequence[Mapping[str, float]],
    *,
    seed: int,
    resamples: int = 1000,
) -> dict[str, dict[str, float]]:
    if len(baseline) != len(candidate) or not baseline:
        raise ValueError("paired non-empty metric rows are required")
    if resamples < 1000:
        raise ValueError("at least 1000 bootstrap resamples are required")
    rng = random.Random(seed)
    metrics = {
        "mrr": "delta_mrr",
        "ndcg_at_5": "delta_ndcg_at_5",
        "recall_at_1": "delta_recall_at_1",
    }
    output: dict[str, dict[str, float]] = {}
    for source_key, result_key in metrics.items():
        paired = [
            float(new[source_key]) - float(old[source_key])
            for old, new in zip(baseline, candidate, strict=True)
        ]
        point = sum(paired) / len(paired)
        sampled = []
        for _ in range(resamples):
            sample = [paired[rng.randrange(len(paired))] for _ in paired]
            sampled.append(sum(sample) / len(sample))
        sampled.sort()
        output[result_key] = {
            "point_estimate": point,
            "ci_95_low": sampled[int(0.025 * (resamples - 1))],
            "ci_95_high": sampled[int(0.975 * (resamples - 1))],
            "resamples": resamples,
            "seed": seed,
        }
    return output


def apply_lexical_guardrail(
    candidates: Sequence[Any], scores: Mapping[str, float], *, protected_lexical_rank: int = 1
) -> list[Any]:
    """Preserve candidates in protected lexical ranks; rerank only the remainder."""
    if protected_lexical_rank < 0:
        raise ValueError("protected_lexical_rank cannot be negative")
    protected = [
        candidate
        for candidate in candidates
        if int(candidate.metadata.get("lexical_rank") or 10**9) <= protected_lexical_rank
    ]
    protected_ids = {candidate.source_id for candidate in protected}
    rest = [candidate for candidate in candidates if candidate.source_id not in protected_ids]
    rest.sort(key=lambda candidate: (-scores[candidate.source_id], candidate.source_id))
    return protected + rest


def candidate_identity_preserved(before: Sequence[Any], after: Sequence[Any]) -> bool:
    before_ids = [candidate.source_id for candidate in before]
    after_ids = [candidate.source_id for candidate in after]
    return len(after_ids) == len(set(after_ids)) and set(before_ids) == set(after_ids)
