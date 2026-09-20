from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ctxd.app.config.settings import Settings, get_settings
from ctxd.app.context.assembler import ContextAssembler
from ctxd.app.ingestion.chunking import StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.retrieval.index import LexicalIndex, SemanticIndex
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import HashEmbeddingModel, SemanticRetriever
from ctxd.app.storage.documents import DocumentStore, InMemoryDocumentStore
from ctxd.app.storage.postgres import PostgresDocumentStore


class CorpusBackend(DocumentStore, LexicalIndex, SemanticIndex, Protocol):
    pass


@runtime_checkable
class ManagedBackend(Protocol):
    def start(self) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class RuntimeServices:
    store: CorpusBackend
    ingestion: IngestionService
    retriever: BM25Retriever
    semantic_retriever: SemanticRetriever
    assembler: ContextAssembler

    def start(self) -> None:
        if isinstance(self.store, ManagedBackend):
            self.store.start()

    def close(self) -> None:
        if isinstance(self.store, ManagedBackend):
            self.store.close()


def create_runtime(
    store: CorpusBackend | None = None,
    settings: Settings | None = None,
) -> RuntimeServices:
    resolved_settings = settings or get_settings()
    resolved_store: CorpusBackend
    if store is not None:
        resolved_store = store
    elif resolved_settings.storage_backend == "postgres":
        resolved_store = PostgresDocumentStore(
            resolved_settings.database_url,
            pool_min_size=resolved_settings.database_pool_min_size,
            pool_max_size=resolved_settings.database_pool_max_size,
            connection_timeout_seconds=resolved_settings.database_connection_timeout_seconds,
            query_timeout_ms=resolved_settings.database_query_timeout_ms,
        )
    else:
        resolved_store = InMemoryDocumentStore()
    embedding_model = HashEmbeddingModel(
        dimension=resolved_settings.embedding_dimension,
        version=resolved_settings.embedding_version,
    )
    ingestion = IngestionService(resolved_store, StructureAwareChunker(), embedding_model)
    retriever = BM25Retriever(resolved_store)
    semantic_retriever = SemanticRetriever(resolved_store, embedding_model)
    return RuntimeServices(
        store=resolved_store,
        ingestion=ingestion,
        retriever=retriever,
        semantic_retriever=semantic_retriever,
        assembler=ContextAssembler(retriever, semantic_retriever),
    )
