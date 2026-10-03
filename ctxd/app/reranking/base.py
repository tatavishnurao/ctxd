from __future__ import annotations

import math
from typing import Protocol

from ctxd.app.models.domain import ContextCandidate


class Reranker(Protocol):
    model_id: str

    def rerank(
        self, query: str, candidates: list[ContextCandidate], top_k: int
    ) -> list[ContextCandidate]: ...


def apply_scores(
    candidates: list[ContextCandidate],
    scores: list[float],
    *,
    top_k: int,
    model_id: str,
) -> list[ContextCandidate]:
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if len(scores) != len(candidates):
        raise ValueError("reranker score count does not match candidate count")
    if any(not math.isfinite(score) for score in scores):
        raise ValueError("reranker scores must be finite")
    ranked = sorted(
        enumerate(zip(candidates, scores, strict=True)),
        key=lambda item: (-item[1][1], item[0]),
    )
    return [
        candidate.model_copy(
            update={
                "metadata": {
                    **candidate.metadata,
                    "reranker_score": score,
                    "pre_rerank_rank": original_index + 1,
                    "reranked_rank": reranked_index,
                    "reranker_model": model_id,
                },
            }
        )
        for reranked_index, (original_index, (candidate, score)) in enumerate(ranked[:top_k], 1)
    ]
