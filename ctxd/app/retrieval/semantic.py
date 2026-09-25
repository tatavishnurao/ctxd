"""Versioned embedding providers and tenant-scoped semantic retrieval.

``FakeHashEmbeddingProvider`` is a lexical hash fixture: it is deterministic and
useful in tests, but it is not a semantic model. ``RealEmbeddingProvider`` uses
the pinned, local Model2Vec Potion model. Both providers emit L2-normalized
vectors, so retrieval uses cosine similarity (equivalent to dot product for
normalized vectors).
"""

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Any, Protocol, cast

from ctxd.app.models.domain import Chunk, ContextCandidate, SemanticIndexStatistics, SourceType


@dataclass(frozen=True)
class SemanticHit:
    chunk: Chunk
    score: float


class EmbeddingModel(Protocol):
    version: str
    dimension: int
    normalized: bool
    distance_metric: str

    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...


class FakeHashEmbeddingProvider:
    """Deterministic signed feature hash fixture; not a semantic embedding model."""

    normalized = True
    distance_metric = "cosine"

    def __init__(self, dimension: int = 128, version: str = "fake-hash-v1") -> None:
        if dimension <= 0 or not version:
            raise ValueError("embedding dimension must be positive and version non-empty")
        self.dimension = dimension
        self.version = version

    def embed_query(self, text: str) -> list[float]:
        values = [0.0] * self.dimension
        for token in re.findall(r"\w+", text.casefold()):
            digest = blake2b(token.encode(), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            values[number % self.dimension] += 1.0 if (number >> 8) & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in values))
        return [value / norm for value in values] if norm else values

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    # Kept as a narrow compatibility shim for Phase 4A callers.
    def embed(self, text: str) -> list[float]:
        return self.embed_query(text)


# Backward-compatible name. New code and documentation use the explicit fixture name.
HashEmbeddingModel = FakeHashEmbeddingProvider


class RealEmbeddingProvider:
    """Local semantic baseline using pinned ``minishlab/potion-base-8M``.

    Model artifact: Hugging Face commit
    ``bf8b056651a2c21b8d2565580b8569da283cab23``. Inference is local, batched,
    CPU-compatible, normalized, and has no hosted inference/API dependency.
    Set ``offline=True`` after pre-populating the Hugging Face cache.
    """

    model_id = "minishlab/potion-base-8M"
    revision = "bf8b056651a2c21b8d2565580b8569da283cab23"
    dimension = 256
    normalized = True
    distance_metric = "cosine"
    version = f"model2vec:{model_id}@{revision}:normalized"

    def __init__(
        self,
        *,
        cache_dir: str | Path | None = None,
        offline: bool = False,
        batch_size: int = 256,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        from huggingface_hub import snapshot_download
        from model2vec import StaticModel

        path = snapshot_download(
            repo_id=self.model_id,
            revision=self.revision,
            cache_dir=str(cache_dir) if cache_dir else None,
            local_files_only=offline,
        )
        self._model = StaticModel.from_pretrained(path, normalize=True)
        if self._model.dim != self.dimension:
            raise RuntimeError(
                f"model dimension changed: expected {self.dimension}, got {self._model.dim}"
            )
        self.batch_size = batch_size

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            batch_size=self.batch_size,
            show_progress_bar=False,
            use_multiprocessing=False,
        )
        return [[float(value) for value in vector] for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed(self, text: str) -> list[float]:
        return self.embed_query(text)


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
            "raw_vector_score": hit.score,
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
            self.model.embed_query(query), tenant_id, top_k, version=self.model.version
        )
        return [semantic_candidate(hit) for hit in hits]

    def statistics(self, tenant_id: str) -> SemanticIndexStatistics:
        return cast(SemanticIndexStatistics, self.index.semantic_statistics(tenant_id))
