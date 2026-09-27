from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from statistics import median
from typing import Literal

LengthBucket = Literal["0-64", "65-128", "129-256", "257-384", "385-512", ">512"]


def normalized_tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9_]+", text.casefold()))


def normalized_content(text: str) -> str:
    return " ".join(normalized_tokens(text))


def token_jaccard(left: str, right: str) -> float:
    left_tokens = set(normalized_tokens(left))
    right_tokens = set(normalized_tokens(right))
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 1.0


def overlap_ratio(query: str, candidate: str) -> float:
    query_tokens = set(normalized_tokens(query))
    if not query_tokens:
        return 0.0
    return len(query_tokens & set(normalized_tokens(candidate))) / len(query_tokens)


def length_bucket(token_count: int) -> LengthBucket:
    if token_count <= 64:
        return "0-64"
    if token_count <= 128:
        return "65-128"
    if token_count <= 256:
        return "129-256"
    if token_count <= 384:
        return "257-384"
    if token_count <= 512:
        return "385-512"
    return ">512"


def distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "std": None,
            "p10": None,
            "p50": None,
            "p90": None,
        }
    ordered = sorted(values)
    mean = sum(values) / len(values)

    def percentile(q: float) -> float:
        return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * q))]

    return {
        "count": len(values),
        "mean": mean,
        "median": median(values),
        "std": math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)),
        "p10": percentile(0.10),
        "p50": percentile(0.50),
        "p90": percentile(0.90),
    }


def pairwise_accuracy(relevant: Iterable[float], nonrelevant: Iterable[float]) -> float | None:
    relevant_values = list(relevant)
    nonrelevant_values = list(nonrelevant)
    comparisons = [
        relevant_score > nonrelevant_score
        for relevant_score in relevant_values
        for nonrelevant_score in nonrelevant_values
    ]
    return sum(comparisons) / len(comparisons) if comparisons else None


def robust_outlier_indices(values: Sequence[float], deviations: float = 3.0) -> list[int]:
    """Return indices above median + deviations * median absolute deviation."""
    if len(values) < 3:
        return []
    center = median(values)
    mad = median([abs(value - center) for value in values])
    if mad == 0:
        return [index for index, value in enumerate(values) if value > center]
    threshold = center + deviations * mad
    return [index for index, value in enumerate(values) if value > threshold]


def aggregate_run_metric(values: Sequence[float]) -> dict[str, float | int | None]:
    """Summarize independent-run values without pooling their query samples."""
    result = distribution(values)
    return {
        "runs": result["count"],
        "median": result["median"],
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "std": result["std"],
    }


def rare_terms(documents: Iterable[str], maximum_document_frequency: int = 2) -> set[str]:
    frequencies: Counter[str] = Counter()
    for document in documents:
        frequencies.update(set(normalized_tokens(document)))
    return {
        token for token, frequency in frequencies.items() if frequency <= maximum_document_frequency
    }


def query_features(query: str, corpus_rare_terms: set[str]) -> dict[str, bool | int]:
    tokens = normalized_tokens(query)
    return {
        "token_count": len(tokens),
        "exact_identifier": any(
            "_" in token or any(char.isdigit() for char in token) for token in tokens
        ),
        "code_like": any(marker in query for marker in ("_", "::", "()", "{", "}", "/", "--")),
        "rare_term": any(token in corpus_rare_terms for token in tokens),
        "natural_language": len(tokens) >= 5 and query.rstrip().endswith("?"),
        "multiple_concept": len({token for token in tokens if len(token) > 4}) >= 3,
        "morphological_variation": any(
            token.endswith(suffix) for token in tokens for suffix in ("ing", "ed", "tion", "ity")
        ),
    }
