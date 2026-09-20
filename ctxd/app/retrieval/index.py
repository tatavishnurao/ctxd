import re
from dataclasses import dataclass
from typing import Protocol

from ctxd.app.models.domain import Chunk, LexicalIndexStatistics, SemanticIndexStatistics
from ctxd.app.retrieval.semantic import SemanticHit

_TERM_RE = re.compile(r"\w+", re.UNICODE)


def tokenize_lexical(text: str) -> list[str]:
    return [term.casefold() for term in _TERM_RE.findall(text)]


@dataclass(frozen=True)
class LexicalHit:
    chunk: Chunk
    score: float


class SemanticIndex(Protocol):
    def search_semantic(
        self, query_vector: list[float], tenant_id: str, top_k: int, *, version: str
    ) -> list[SemanticHit]: ...
    def semantic_statistics(self, tenant_id: str) -> SemanticIndexStatistics: ...


class LexicalIndex(Protocol):
    """Tenant-scoped lexical query and bounded introspection interface.

    Index mutation is owned by DocumentStore.replace_document/delete_document so
    persisted content and index statistics can share one atomic transaction.
    """

    def search_lexical(
        self,
        query: str,
        tenant_id: str,
        top_k: int,
        *,
        k1: float,
        b: float,
    ) -> list[LexicalHit]: ...

    def lexical_statistics(self, tenant_id: str) -> LexicalIndexStatistics: ...
