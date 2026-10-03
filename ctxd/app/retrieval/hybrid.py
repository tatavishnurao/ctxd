import contextvars
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass

from ctxd.app.models.domain import ContextCandidate
from ctxd.app.retrieval.lexical import Retriever
from ctxd.app.retrieval.semantic import SemanticRetriever, SemanticSearchResult
from ctxd.app.storage.errors import RetrievalTimeoutError


@dataclass(frozen=True)
class HybridSearchResult:
    candidates: list[ContextCandidate]
    lexical_count: int
    semantic_count: int
    stale_chunks: int


class HybridRetriever:
    """Reciprocal-rank fusion preserving both component rankings and scores.

    For each candidate ``d`` this computes exactly
    ``RRF(d) = sum(1 / (k + rank_i(d)))``. Component scores are deliberately
    not normalized or mixed.
    """

    def __init__(
        self,
        lexical: Retriever,
        semantic: SemanticRetriever,
        rrf_k: int = 60,
        candidate_depth: int | None = None,
        parallel: bool = True,
    ) -> None:
        if rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        if candidate_depth is not None and candidate_depth <= 0:
            raise ValueError("candidate_depth must be positive")
        self.lexical = lexical
        self.semantic = semantic
        self.rrf_k = rrf_k
        self.candidate_depth = candidate_depth
        self.parallel = parallel

    @staticmethod
    def _component_metadata(
        candidate: ContextCandidate, rank: int, component: str
    ) -> dict[str, object]:
        score_key = "raw_lexical_score" if component == "lexical" else "raw_vector_score"
        return {f"{component}_rank": rank, score_key: candidate.relevance_score}

    def fuse(
        self,
        lexical: list[ContextCandidate],
        semantic: list[ContextCandidate],
        top_k: int,
    ) -> list[ContextCandidate]:
        scores: dict[str, float] = {}
        candidates: dict[str, ContextCandidate] = {}
        metadata: dict[str, dict[str, object]] = {}
        for component, results in (("lexical", lexical), ("semantic", semantic)):
            for rank, candidate in enumerate(results, 1):
                item = candidate.source_id
                scores[item] = scores.get(item, 0.0) + 1.0 / (self.rrf_k + rank)
                candidates.setdefault(item, candidate)
                metadata.setdefault(item, {}).update(
                    self._component_metadata(candidate, rank, component)
                )
        # chunk id is the deterministic tie-breaker. Union semantics preserve
        # lexical-only and semantic-only candidates.
        ordered = sorted(scores, key=lambda item: (-scores[item], item))[:top_k]
        return [
            candidates[item].model_copy(
                update={
                    "relevance_score": scores[item],
                    "metadata": {
                        **candidates[item].metadata,
                        **metadata[item],
                        "fused_score": scores[item],
                    },
                }
            )
            for item in ordered
        ]

    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]:
        return self.search_detailed(query, tenant_id, top_k).candidates

    def depth(self, top_k: int) -> int:
        return self.candidate_depth or max(top_k, min(100, top_k * 2))

    def search_detailed(
        self, query: str, tenant_id: str, top_k: int, *, timeout: float | None = None
    ) -> HybridSearchResult:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        width = self.depth(top_k)
        semantic: SemanticSearchResult
        if self.parallel:
            # Each branch runs in a copy of the caller's context so trace spans and
            # request/tenant log fields stay attached to the originating request.
            executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ctxd-hybrid")
            try:
                lexical_future = executor.submit(
                    contextvars.copy_context().run,
                    self.lexical.search,
                    query,
                    tenant_id,
                    width,
                )
                semantic_future = executor.submit(
                    contextvars.copy_context().run,
                    self.semantic.search_detailed,
                    query,
                    tenant_id,
                    width,
                )
                try:
                    lexical = lexical_future.result(timeout=timeout)
                    semantic = semantic_future.result(timeout=timeout)
                except FutureTimeoutError as exc:
                    raise RetrievalTimeoutError("hybrid retrieval exceeded deadline") from exc
            finally:
                # Never block the request on an abandoned branch past its deadline.
                executor.shutdown(wait=False, cancel_futures=True)
        else:
            lexical = self.lexical.search(query, tenant_id, width)
            semantic = self.semantic.search_detailed(query, tenant_id, width)
        return HybridSearchResult(
            candidates=self.fuse(lexical, semantic.candidates, top_k),
            lexical_count=len(lexical),
            semantic_count=len(semantic.candidates),
            stale_chunks=semantic.stale_chunks,
        )
