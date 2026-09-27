from __future__ import annotations

from collections.abc import Callable

from ctxd.app.models.domain import ContextCandidate
from ctxd.app.reranking.base import apply_scores


class FakeReranker:
    """Deterministic test reranker with injectable candidate scoring."""

    model_id = "fake-reranker-v1"

    def __init__(self, score: Callable[[str, ContextCandidate], float] | None = None) -> None:
        self._score = score or (lambda _query, candidate: candidate.relevance_score)

    def rerank(
        self, query: str, candidates: list[ContextCandidate], top_k: int
    ) -> list[ContextCandidate]:
        return apply_scores(
            candidates,
            [self._score(query, candidate) for candidate in candidates],
            top_k=top_k,
            model_id=self.model_id,
        )
