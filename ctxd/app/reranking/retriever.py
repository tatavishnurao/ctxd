from __future__ import annotations

from opentelemetry import trace

from ctxd.app.models.domain import ContextCandidate
from ctxd.app.observability.metrics import RERANKER_REQUESTS_TOTAL
from ctxd.app.reranking.base import Reranker
from ctxd.app.retrieval.lexical import Retriever

tracer = trace.get_tracer(__name__)


class RerankingRetriever:
    """Reorder a fixed upstream candidate set, falling back to its original order."""

    def __init__(
        self, upstream: Retriever, reranker: Reranker, *, candidate_count: int = 20
    ) -> None:
        if candidate_count <= 0:
            raise ValueError("candidate_count must be positive")
        self.upstream = upstream
        self.reranker = reranker
        self.candidate_count = candidate_count

    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        candidates = self.upstream.search(query, tenant_id, self.candidate_count)
        if not candidates:
            return []
        with tracer.start_as_current_span("retrieval.rerank") as span:
            span.set_attribute("reranker.model", self.reranker.model_id)
            span.set_attribute("reranker.candidate_count", len(candidates))
            try:
                reranked = self.reranker.rerank(query, candidates, top_k)
                if not self._same_candidate_set(candidates, reranked, top_k):
                    raise ValueError("reranker changed the candidate set")
                span.set_attribute("reranker.result_count", len(reranked))
                RERANKER_REQUESTS_TOTAL.labels(self.reranker.model_id, "success").inc()
                return reranked
            except Exception:
                RERANKER_REQUESTS_TOTAL.labels(self.reranker.model_id, "fallback").inc()
                return candidates[:top_k]

    @staticmethod
    def _same_candidate_set(
        original: list[ContextCandidate], reranked: list[ContextCandidate], top_k: int
    ) -> bool:
        original_ids = {candidate.source_id for candidate in original}
        reranked_ids = [candidate.source_id for candidate in reranked]
        return (
            len(reranked_ids) == min(len(original), top_k)
            and len(reranked_ids) == len(set(reranked_ids))
            and set(reranked_ids) <= original_ids
        )
