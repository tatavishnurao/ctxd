import math
from collections import Counter
from collections.abc import Sequence
from threading import RLock
from typing import Protocol

from ctxd.app.models.domain import Chunk, Document, LexicalIndexStatistics, SemanticIndexStatistics
from ctxd.app.retrieval.index import LexicalHit, tokenize_lexical
from ctxd.app.retrieval.semantic import SemanticHit


class DocumentStore(Protocol):
    def replace_document(
        self,
        document: Document,
        chunks: Sequence[Chunk],
        *,
        embedding_version: str | None = None,
        embeddings: dict[str, list[float]] | None = None,
    ) -> bool:
        """Atomically upsert a document, replace chunks, and update its indexes."""
        ...

    def upsert_document(self, document: Document) -> bool: ...

    def replace_chunks(self, document_id: str, tenant_id: str, chunks: Sequence[Chunk]) -> None: ...

    def get_document(self, document_id: str, tenant_id: str) -> Document | None: ...

    def get_chunk(self, chunk_id: str, tenant_id: str) -> Chunk | None: ...

    def list_chunks(self, tenant_id: str, document_id: str | None = None) -> list[Chunk]: ...

    def delete_document(self, document_id: str, tenant_id: str) -> bool: ...
    def search_semantic(
        self, query_vector: list[float], tenant_id: str, top_k: int, *, version: str
    ) -> list[SemanticHit]: ...
    def semantic_statistics(self, tenant_id: str) -> SemanticIndexStatistics: ...


class InMemoryDocumentStore:
    """Thread-safe document store with an incrementally maintained BM25 index."""

    def __init__(self) -> None:
        self._documents: dict[tuple[str, str], Document] = {}
        self._chunks: dict[tuple[str, str], Chunk] = {}
        self._terms_by_chunk: dict[tuple[str, str], Counter[str]] = {}
        self._postings: dict[tuple[str, str], dict[str, int]] = {}
        self._document_frequency: Counter[tuple[str, str]] = Counter()
        self._chunk_count: Counter[str] = Counter()
        self._total_lexical_length: Counter[str] = Counter()
        self._embeddings: dict[tuple[str, str], tuple[str, list[float]]] = {}
        self._lock = RLock()

    @staticmethod
    def _validate_chunks(document_id: str, tenant_id: str, chunks: Sequence[Chunk]) -> None:
        if any(
            chunk.document_id != document_id or chunk.tenant_id != tenant_id for chunk in chunks
        ):
            raise ValueError("all chunks must belong to the requested document and tenant")

    def replace_document(
        self,
        document: Document,
        chunks: Sequence[Chunk],
        *,
        embedding_version: str | None = None,
        embeddings: dict[str, list[float]] | None = None,
    ) -> bool:
        self._validate_chunks(document.document_id, document.tenant_id, chunks)
        key = (document.tenant_id, document.document_id)
        with self._lock:
            previous = self._documents.get(key)
            if previous is not None and previous.content_hash == document.content_hash:
                return False
            self._documents[key] = document.model_copy(deep=True)
            self._replace_chunks_locked(document.document_id, document.tenant_id, chunks)
            if embedding_version and embeddings is not None:
                for chunk in chunks:
                    self._embeddings[(document.tenant_id, chunk.chunk_id)] = (
                        embedding_version,
                        list(embeddings[chunk.chunk_id]),
                    )
            return previous is None

    def upsert_document(self, document: Document) -> bool:
        return self.replace_document(document, [])

    def replace_chunks(
        self,
        document_id: str,
        tenant_id: str,
        chunks: Sequence[Chunk],
    ) -> None:
        self._validate_chunks(document_id, tenant_id, chunks)
        with self._lock:
            if (tenant_id, document_id) not in self._documents:
                raise KeyError(f"document not found for tenant: {document_id}")
            self._replace_chunks_locked(document_id, tenant_id, chunks)

    def _remove_chunk_locked(self, tenant_id: str, chunk_id: str) -> None:
        key = (tenant_id, chunk_id)
        terms = self._terms_by_chunk.pop(key, Counter())
        for term in terms:
            postings_key = (tenant_id, term)
            postings = self._postings[postings_key]
            postings.pop(chunk_id, None)
            self._document_frequency[postings_key] -= 1
            if not postings:
                del self._postings[postings_key]
                del self._document_frequency[postings_key]
        self._chunk_count[tenant_id] -= 1
        self._total_lexical_length[tenant_id] -= sum(terms.values())
        self._chunks.pop(key, None)

    def _replace_chunks_locked(
        self,
        document_id: str,
        tenant_id: str,
        chunks: Sequence[Chunk],
    ) -> None:
        stale_ids = [
            chunk.chunk_id
            for (owner, _), chunk in self._chunks.items()
            if owner == tenant_id and chunk.document_id == document_id
        ]
        for chunk_id in stale_ids:
            self._remove_chunk_locked(tenant_id, chunk_id)
            self._embeddings.pop((tenant_id, chunk_id), None)

        for chunk in chunks:
            chunk_copy = chunk.model_copy(deep=True)
            key = (tenant_id, chunk.chunk_id)
            terms = Counter(tokenize_lexical(chunk.content))
            self._chunks[key] = chunk_copy
            self._terms_by_chunk[key] = terms
            self._chunk_count[tenant_id] += 1
            self._total_lexical_length[tenant_id] += sum(terms.values())
            for term, frequency in terms.items():
                postings_key = (tenant_id, term)
                self._postings.setdefault(postings_key, {})[chunk.chunk_id] = frequency
                self._document_frequency[postings_key] += 1

    def get_document(self, document_id: str, tenant_id: str) -> Document | None:
        with self._lock:
            document = self._documents.get((tenant_id, document_id))
            return document.model_copy(deep=True) if document else None

    def get_chunk(self, chunk_id: str, tenant_id: str) -> Chunk | None:
        with self._lock:
            chunk = self._chunks.get((tenant_id, chunk_id))
            return chunk.model_copy(deep=True) if chunk else None

    def list_chunks(self, tenant_id: str, document_id: str | None = None) -> list[Chunk]:
        with self._lock:
            chunks = [
                chunk.model_copy(deep=True)
                for (owner, _), chunk in self._chunks.items()
                if owner == tenant_id and (document_id is None or chunk.document_id == document_id)
            ]
        return sorted(chunks, key=lambda chunk: (chunk.document_id, chunk.ordinal, chunk.chunk_id))

    def delete_document(self, document_id: str, tenant_id: str) -> bool:
        with self._lock:
            removed = self._documents.pop((tenant_id, document_id), None)
            stale_ids = [
                chunk.chunk_id
                for (owner, _), chunk in self._chunks.items()
                if owner == tenant_id and chunk.document_id == document_id
            ]
            for chunk_id in stale_ids:
                self._remove_chunk_locked(tenant_id, chunk_id)
                self._embeddings.pop((tenant_id, chunk_id), None)
            return removed is not None

    def search_semantic(
        self, query_vector: list[float], tenant_id: str, top_k: int, *, version: str
    ) -> list[SemanticHit]:
        with self._lock:
            scored: list[tuple[float, str]] = []
            for (owner, chunk_id), (stored_version, vector) in self._embeddings.items():
                if owner != tenant_id or stored_version != version:
                    continue
                score = sum(a * b for a, b in zip(query_vector, vector, strict=False))
                scored.append((score, chunk_id))
            scored.sort(key=lambda item: (-item[0], item[1]))
            return [
                SemanticHit(self._chunks[(tenant_id, chunk_id)].model_copy(deep=True), score)
                for score, chunk_id in scored[:top_k]
            ]

    def semantic_statistics(self, tenant_id: str) -> SemanticIndexStatistics:
        with self._lock:
            versions = [
                version
                for (owner, _), (version, _) in self._embeddings.items()
                if owner == tenant_id
            ]
            dimension = len(
                next(
                    (
                        vector
                        for (owner, _), (_, vector) in self._embeddings.items()
                        if owner == tenant_id
                    ),
                    [],
                )
            )
            return SemanticIndexStatistics(
                indexed_chunks=len(versions),
                embedding_version=versions[0] if versions else "",
                embedding_dimension=dimension or 1,
            )

    def search_lexical(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
        *,
        k1: float,
        b: float,
    ) -> list[LexicalHit]:
        query_frequency = Counter(tokenize_lexical(query))
        if not query_frequency:
            return []
        with self._lock:
            corpus_size = self._chunk_count[tenant_id]
            if corpus_size == 0:
                return []
            average_length = self._total_lexical_length[tenant_id] / corpus_size
            candidate_ids: set[str] = set()
            for term in query_frequency:
                candidate_ids.update(self._postings.get((tenant_id, term), {}))

            scored: list[tuple[float, str]] = []
            for chunk_id in candidate_ids:
                terms = self._terms_by_chunk[(tenant_id, chunk_id)]
                length_normalization = 1 - b + b * sum(terms.values()) / max(average_length, 1.0)
                score = 0.0
                for term, query_count in query_frequency.items():
                    frequency = terms.get(term, 0)
                    if frequency == 0:
                        continue
                    df = self._document_frequency[(tenant_id, term)]
                    inverse_document_frequency = math.log(1 + (corpus_size - df + 0.5) / (df + 0.5))
                    score += (
                        inverse_document_frequency
                        * (frequency * (k1 + 1) / (frequency + k1 * length_normalization))
                        * query_count
                    )
                if score > 0:
                    scored.append((score, chunk_id))
            scored.sort(key=lambda item: (-item[0], item[1]))
            return [
                LexicalHit(
                    chunk=self._chunks[(tenant_id, chunk_id)].model_copy(deep=True),
                    score=score,
                )
                for score, chunk_id in scored[:top_k]
            ]

    def lexical_statistics(self, tenant_id: str) -> LexicalIndexStatistics:
        with self._lock:
            chunk_count = self._chunk_count[tenant_id]
            document_count = sum(owner == tenant_id for owner, _ in self._documents)
            vocabulary_size = sum(owner == tenant_id for owner, _ in self._postings)
            average_length = (
                self._total_lexical_length[tenant_id] / chunk_count if chunk_count else 0.0
            )
            return LexicalIndexStatistics(
                indexed_documents=document_count,
                indexed_chunks=chunk_count,
                vocabulary_size=vocabulary_size,
                average_chunk_length=average_length,
            )
