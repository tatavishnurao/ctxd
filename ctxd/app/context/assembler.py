import logging
import time
from typing import Any

from opentelemetry import trace

from ctxd.app.models.domain import ContextCandidate, ContextPacket, RetrievalMode
from ctxd.app.observability.metrics import (
    CONTEXT_CANDIDATES_DROPPED_TOTAL,
    CONTEXT_TOKENS_SELECTED,
    EMBEDDING_VERSION_MISMATCH_TOTAL,
    RETRIEVAL_MODE_REQUESTS_TOTAL,
)
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import Retriever
from ctxd.app.retrieval.semantic import SemanticRetriever
from ctxd.app.storage.errors import RetrievalTimeoutError

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def executed_retrieval_type(counts: dict[str, int]) -> str:
    """Name only the branches that actually contributed candidates."""
    contributing = [branch for branch in ("lexical", "semantic") if counts.get(branch, 0) > 0]
    if len(contributing) == 2:
        return "hybrid"
    return contributing[0] if contributing else "none"


class ContextAssembler:
    def __init__(self, retriever: Retriever, semantic: SemanticRetriever | None = None) -> None:
        self.retriever = retriever
        self.semantic = semantic
        self.hybrid = HybridRetriever(retriever, semantic) if semantic else None

    def assemble(
        self,
        *,
        query: str,
        tenant_id: str,
        top_k: int,
        max_context_tokens: int,
        retrieval_mode: RetrievalMode = RetrievalMode.LEXICAL,
        deadline_seconds: float | None = None,
    ) -> ContextPacket:
        with tracer.start_as_current_span("context_assembly") as span:
            span.set_attribute("context.token_budget", max_context_tokens)
            started = time.perf_counter()
            try:
                candidates, retrieval = self._retrieve(
                    query, tenant_id, top_k, retrieval_mode, deadline_seconds
                )
                if (
                    deadline_seconds is not None
                    and time.perf_counter() - started > deadline_seconds
                ):
                    raise RetrievalTimeoutError("retrieval exceeded request deadline")
            except RetrievalTimeoutError:
                RETRIEVAL_MODE_REQUESTS_TOTAL.labels(retrieval_mode.value, "timeout").inc()
                raise
            except Exception:
                RETRIEVAL_MODE_REQUESTS_TOTAL.labels(retrieval_mode.value, "error").inc()
                raise
            RETRIEVAL_MODE_REQUESTS_TOTAL.labels(retrieval_mode.value, "success").inc()
            selected = []
            selected_tokens = 0
            dropped = 0
            for candidate in candidates:
                if selected_tokens + candidate.token_cost > max_context_tokens:
                    dropped += 1
                    continue
                selected.append(candidate)
                selected_tokens += candidate.token_cost

            candidate_tokens = sum(candidate.token_cost for candidate in candidates)
            span.set_attribute("context.selected_tokens", selected_tokens)
            span.set_attribute("context.selected_count", len(selected))
            CONTEXT_TOKENS_SELECTED.observe(selected_tokens)
            CONTEXT_CANDIDATES_DROPPED_TOTAL.inc(dropped)
            return ContextPacket(
                candidates=selected,
                token_budget=max_context_tokens,
                context_tokens=selected_tokens,
                metadata={
                    "retrieved_candidate_count": len(candidates),
                    "selected_candidate_count": len(selected),
                    "candidate_tokens": candidate_tokens,
                    "selected_tokens": selected_tokens,
                    "dropped_due_to_budget": dropped,
                    **retrieval,
                },
            )

    def _retrieve(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
        mode: RetrievalMode,
        deadline_seconds: float | None = None,
    ) -> tuple[list[ContextCandidate], dict[str, Any]]:
        warnings: list[str] = []
        stale = 0
        counts: dict[str, int]
        if mode == RetrievalMode.HYBRID and self.hybrid is not None:
            hybrid = self.hybrid.search_detailed(query, tenant_id, top_k, timeout=deadline_seconds)
            candidates = hybrid.candidates
            counts = {"lexical": hybrid.lexical_count, "semantic": hybrid.semantic_count}
            stale = hybrid.stale_chunks
        elif mode == RetrievalMode.SEMANTIC and self.semantic is not None:
            semantic = self.semantic.search_detailed(query, tenant_id, top_k)
            candidates = semantic.candidates
            counts = {"semantic": len(candidates)}
            stale = semantic.stale_chunks
        else:
            if mode != RetrievalMode.LEXICAL:
                warnings.append("semantic_retriever_unavailable")
            candidates = self.retriever.search(query, tenant_id, top_k)
            counts = {"lexical": len(candidates)}
        metadata: dict[str, Any] = {
            "requested_mode": mode.value,
            "retrieval_type": executed_retrieval_type(counts),
            "branch_candidate_counts": counts,
        }
        if "semantic" in counts and self.semantic is not None:
            metadata["embedding_version"] = self.semantic.model.version
        if stale:
            warnings.append("embedding_version_mismatch")
            metadata["stale_embedding_chunks"] = stale
            EMBEDDING_VERSION_MISMATCH_TOTAL.inc()
            logger.warning("embedding_version_mismatch", extra={"fields": {"stale_chunks": stale}})
        if warnings:
            metadata["warnings"] = warnings
        return candidates, metadata
