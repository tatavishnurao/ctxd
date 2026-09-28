"""Offline chunk-position evaluation. Source judgments are not evidence-span labels."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Packing = Literal["greedy", "density", "unique_source", "exact_duplicate"]


@dataclass(frozen=True)
class SelectionCandidate:
    """Runtime-only inputs: deliberately excludes judgments, categories and case IDs."""

    identity: str
    source: str
    content: str
    tokens: int
    lexical_rank: int | None = None
    semantic_rank: int | None = None


def validate_candidates(candidates: Sequence[SelectionCandidate]) -> None:
    if len({c.identity for c in candidates}) != len(candidates):
        raise ValueError("candidate identities must be unique")
    if any(c.tokens <= 0 for c in candidates):
        raise ValueError("candidate token costs must be positive")


def pack(
    candidates: Sequence[SelectionCandidate], budget: int, policy: Packing = "greedy"
) -> list[SelectionCandidate]:
    """Select whole chunks, then restore input rank order; never mutate inputs.

    Density uses reciprocal rank/token cost, not uncalibrated model logits.
    Unique-source is intentionally experimental: disjoint chunks may both be needed.
    Exact-duplicate suppression only compares whitespace-normalized text.
    """
    validate_candidates(candidates)
    if budget < 0:
        raise ValueError("budget must be nonnegative")
    if policy not in ("greedy", "density", "unique_source", "exact_duplicate"):
        raise ValueError("unknown packing policy")
    order = list(range(len(candidates)))
    if policy == "density":
        order.sort(key=lambda i: ((i + 1) * candidates[i].tokens, i))
    chosen: set[int] = set()
    seen: set[str] = set()
    remaining = budget
    for index in order:
        candidate = candidates[index]
        key = candidate.source if policy == "unique_source" else " ".join(candidate.content.split())
        if policy in ("unique_source", "exact_duplicate") and key in seen:
            continue
        if candidate.tokens <= remaining:
            remaining -= candidate.tokens
            chosen.add(index)
            seen.add(key)
    return [candidate for i, candidate in enumerate(candidates) if i in chosen]


def source_metrics(paths: Sequence[str], relevant: set[str]) -> dict[str, float]:
    """Unique-source credit at original chunk positions; repeats consume ranks.

    This is binary source-coverage nDCG, not chunk relevance or graded evidence.
    """
    if not relevant:
        raise ValueError("nonempty source judgments required")
    seen: set[str] = set()
    hits: list[int] = []
    for rank, path in enumerate(paths, 1):
        if path in relevant and path not in seen:
            hits.append(rank)
        seen.add(path)
    result = {f"recall_at_{k}": sum(r <= k for r in hits) / len(relevant) for k in (1, 5, 10)}
    result["mrr"] = 1 / hits[0] if hits else 0.0
    for k in (5, 10):
        dcg = sum(1 / math.log2(r + 1) for r in hits if r <= k)
        ideal = sum(1 / math.log2(r + 1) for r in range(1, min(k, len(relevant)) + 1))
        result[f"ndcg_at_{k}"] = dcg / ideal
    return result


def budget_metrics(
    retrieved: Sequence[SelectionCandidate],
    selected: Sequence[SelectionCandidate],
    relevant: set[str],
) -> dict[str, float]:
    """Source-token proxies only; no assertion that every token answers the query."""
    validate_candidates(retrieved)
    validate_candidates(selected)
    originals = {c.identity: c for c in retrieved}
    if any(originals.get(c.identity) != c for c in selected):
        raise ValueError("selection must preserve candidate identity and contents")
    if not relevant:
        raise ValueError("nonempty source judgments required")
    retrieved_sources = {c.source for c in retrieved} & relevant
    selected_sources = {c.source for c in selected} & relevant
    total = sum(c.tokens for c in selected)
    nonrelevant = sum(c.tokens for c in selected if c.source not in relevant)
    seen: set[str] = set()
    repeated = 0
    for candidate in selected:
        content = " ".join(candidate.content.split())
        if content in seen:
            repeated += candidate.tokens
        seen.add(content)
    return {
        "retrieved_relevant_sources": float(len(retrieved_sources)),
        "selected_relevant_sources": float(len(selected_sources)),
        "dropped_relevant_sources": float(len(retrieved_sources - selected_sources)),
        "source_recall": len(selected_sources) / len(relevant),
        "selected_tokens": float(total),
        "selected_candidates": float(len(selected)),
        "nonrelevant_source_tokens": float(nonrelevant),
        "nonrelevant_source_token_fraction": nonrelevant / total if total else 0.0,
        "exact_duplicate_tokens": float(repeated),
        "relevant_sources_per_1k_tokens": len(selected_sources) * 1000 / total if total else 0.0,
    }


def should_rerank(candidates: Sequence[SelectionCandidate], policy: str) -> bool:
    """Three fixed diagnostic policies; missing top-1 signals count as disagreement."""
    validate_candidates(candidates)
    lexical = next((c.identity for c in candidates if c.lexical_rank == 1), None)
    semantic = next((c.identity for c in candidates if c.semantic_rank == 1), None)
    agreement = lexical is not None and lexical == semantic
    if policy == "disagreement":
        return bool(candidates) and not agreement
    if policy == "no_lexical_winner":
        return bool(candidates) and lexical is None
    if policy == "top_rrf_not_lexical":
        return bool(candidates) and candidates[0].identity != lexical
    raise ValueError("unknown reranking policy")
