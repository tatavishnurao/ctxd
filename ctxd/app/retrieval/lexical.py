import time
from typing import Protocol

from opentelemetry import trace

from ctxd.app.models.domain import ContextCandidate, LexicalIndexStatistics, SourceType
from ctxd.app.observability.metrics import (
    LEXICAL_SEARCH_LATENCY_SECONDS,
    RETRIEVAL_CANDIDATES_RETURNED,
    RETRIEVAL_LATENCY_SECONDS,
    RETRIEVAL_REQUESTS_TOTAL,
)
from ctxd.app.retrieval.index import LexicalIndex

tracer = trace.get_tracer(__name__)


class Retriever(Protocol):
    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]: ...


class BM25Retriever:
    def __init__(
        self,
        index: LexicalIndex,
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("BM25 requires k1 > 0 and 0 <= b <= 1")
        self.index = index
        self.k1 = k1
        self.b = b

    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        start = time.perf_counter()
        status = "success"
        try:
            with tracer.start_as_current_span("lexical.search") as span:
                span.set_attribute("retrieval.top_k", top_k)
                hits = self.index.search_lexical(
                    query,
                    tenant_id,
                    top_k,
                    k1=self.k1,
                    b=self.b,
                )
                results = [
                    ContextCandidate(
                        source_id=hit.chunk.chunk_id,
                        source_type=SourceType.DOCUMENT,
                        content=hit.chunk.content,
                        token_cost=hit.chunk.token_count,
                        relevance_score=hit.score,
                        metadata={
                            "document_id": hit.chunk.document_id,
                            "chunk_id": hit.chunk.chunk_id,
                            "source_path": hit.chunk.metadata.get("source_path", ""),
                            "start_line": hit.chunk.start_line,
                            "end_line": hit.chunk.end_line,
                            "ordinal": hit.chunk.ordinal,
                        },
                    )
                    for hit in hits
                ]
                span.set_attribute("retrieval.result_count", len(results))
                RETRIEVAL_CANDIDATES_RETURNED.observe(len(results))
                return results
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - start
            RETRIEVAL_REQUESTS_TOTAL.labels(status).inc()
            RETRIEVAL_LATENCY_SECONDS.observe(elapsed)
            LEXICAL_SEARCH_LATENCY_SECONDS.observe(elapsed)

    def statistics(self, tenant_id: str) -> LexicalIndexStatistics:
        return self.index.lexical_statistics(tenant_id)
