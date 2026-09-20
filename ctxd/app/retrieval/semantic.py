"""Deterministic, versioned semantic retrieval.

The default model is deliberately local and dependency-free.  It is a stable
baseline for production wiring; replacing it does not change the index API.
"""

import math
import re
from dataclasses import dataclass
from hashlib import blake2b
from typing import Any, Protocol, cast

from ctxd.app.models.domain import Chunk, ContextCandidate, SemanticIndexStatistics, SourceType


@dataclass(frozen=True)
class SemanticHit:
    chunk: Chunk
    score: float


class EmbeddingModel(Protocol):
    version: str
    dimension: int

    def embed(self, text: str) -> list[float]: ...


class HashEmbeddingModel:
    """Deterministic signed feature hashing model, suitable for a reproducible baseline."""

    def __init__(self, dimension: int = 128, version: str = "hash-v1") -> None:
        if dimension <= 0 or not version:
            raise ValueError("embedding dimension must be positive")
        self.dimension = dimension
        self.version = version

    def embed(self, text: str) -> list[float]:
        values = [0.0] * self.dimension
        for token in re.findall(r"\w+", text.casefold()):
            digest = blake2b(token.encode(), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            index = number % self.dimension
            values[index] += 1.0 if (number >> 8) & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in values))
        return [value / norm for value in values] if norm else values


def semantic_candidate(hit: SemanticHit) -> ContextCandidate:
    return ContextCandidate(
        source_id=hit.chunk.chunk_id,
        source_type=SourceType.DOCUMENT,
        content=hit.chunk.content,
        token_cost=hit.chunk.token_count,
        relevance_score=max(0.0, hit.score),
        metadata={
            "document_id": hit.chunk.document_id,
            "chunk_id": hit.chunk.chunk_id,
            "source_path": hit.chunk.metadata.get("source_path", ""),
            "start_line": hit.chunk.start_line,
            "end_line": hit.chunk.end_line,
            "ordinal": hit.chunk.ordinal,
        },
    )


class SemanticRetriever:
    def __init__(self, index: object, model: EmbeddingModel) -> None:
        self.index = cast(Any, index)
        self.model = model

    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        hits = self.index.search_semantic(
            self.model.embed(query), tenant_id, top_k, version=self.model.version
        )
        return [semantic_candidate(hit) for hit in hits]

    def statistics(self, tenant_id: str) -> SemanticIndexStatistics:
        return cast(SemanticIndexStatistics, self.index.semantic_statistics(tenant_id))
