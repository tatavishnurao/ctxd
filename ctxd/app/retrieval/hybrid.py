from ctxd.app.models.domain import ContextCandidate
from ctxd.app.retrieval.lexical import Retriever
from ctxd.app.retrieval.semantic import SemanticRetriever


class HybridRetriever:
    """Deterministic reciprocal-rank fusion of lexical and semantic results."""

    def __init__(self, lexical: Retriever, semantic: SemanticRetriever, rrf_k: int = 60) -> None:
        if rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        self.lexical = lexical
        self.semantic = semantic
        self.rrf_k = rrf_k

    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        # Retrieve a bounded working set, then sort by score and stable chunk id.
        width = max(top_k, min(100, top_k * 2))
        lexical = self.lexical.search(query, tenant_id, width)
        semantic = self.semantic.search(query, tenant_id, width)
        scores: dict[str, float] = {}
        candidates: dict[str, ContextCandidate] = {}
        for rank, candidate in enumerate(lexical, 1):
            scores[candidate.source_id] = scores.get(candidate.source_id, 0.0) + 1 / (
                self.rrf_k + rank
            )
            candidates[candidate.source_id] = candidate
        for rank, candidate in enumerate(semantic, 1):
            scores[candidate.source_id] = scores.get(candidate.source_id, 0.0) + 1 / (
                self.rrf_k + rank
            )
            candidates.setdefault(candidate.source_id, candidate)
        ordered = sorted(scores, key=lambda item: (-scores[item], item))[:top_k]
        return [
            candidates[item].model_copy(update={"relevance_score": scores[item]})
            for item in ordered
        ]
