from opentelemetry import trace

from ctxd.app.models.domain import ContextPacket, RetrievalMode
from ctxd.app.observability.metrics import (
    CONTEXT_CANDIDATES_DROPPED_TOTAL,
    CONTEXT_TOKENS_SELECTED,
    RETRIEVAL_MODE_REQUESTS_TOTAL,
)
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import Retriever
from ctxd.app.retrieval.semantic import SemanticRetriever

tracer = trace.get_tracer(__name__)


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
    ) -> ContextPacket:
        with tracer.start_as_current_span("context_assembly") as span:
            span.set_attribute("context.token_budget", max_context_tokens)
            selected_retriever: Retriever = self.retriever
            if retrieval_mode == RetrievalMode.SEMANTIC and self.semantic is not None:
                selected_retriever = self.semantic
            elif retrieval_mode == RetrievalMode.HYBRID and self.hybrid is not None:
                selected_retriever = self.hybrid
            candidates = selected_retriever.search(query, tenant_id, top_k)
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
                    "retrieval_type": retrieval_mode.value,
                },
            )
