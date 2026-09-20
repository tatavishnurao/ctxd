import time
from pathlib import Path

from opentelemetry import trace

from ctxd.app.ingestion.chunking import StructureAwareChunker
from ctxd.app.ingestion.loaders import Metadata, TextFileLoader, document_from_content
from ctxd.app.models.domain import Chunk, Document, DocumentSourceType
from ctxd.app.observability.metrics import (
    INGESTED_CHUNKS_TOTAL,
    INGESTED_DOCUMENTS_TOTAL,
    LEXICAL_INDEX_UPDATE_LATENCY_SECONDS,
)
from ctxd.app.retrieval.semantic import EmbeddingModel
from ctxd.app.storage.documents import DocumentStore

tracer = trace.get_tracer(__name__)


class IngestionService:
    def __init__(
        self,
        store: DocumentStore,
        chunker: StructureAwareChunker,
        embedding_model: EmbeddingModel | None = None,
    ) -> None:
        self.store = store
        self.chunker = chunker
        self.file_loader = TextFileLoader()
        self.embedding_model = embedding_model

    def ingest_file(
        self,
        source_path: Path,
        tenant_id: str,
        metadata: Metadata | None = None,
    ) -> tuple[Document, list[Chunk], bool]:
        with tracer.start_as_current_span("ingestion"):
            document = self.file_loader.load(source_path, tenant_id, metadata)
            return self._store_document(document)

    def ingest_content(
        self,
        *,
        content: str,
        source_path: str,
        source_type: DocumentSourceType,
        tenant_id: str,
        metadata: Metadata | None = None,
    ) -> tuple[Document, list[Chunk], bool]:
        with tracer.start_as_current_span("ingestion"):
            document = document_from_content(
                content=content,
                source_path=source_path,
                source_type=source_type,
                tenant_id=tenant_id,
                metadata=metadata,
            )
            return self._store_document(document)

    def _store_document(self, document: Document) -> tuple[Document, list[Chunk], bool]:
        existing = self.store.get_document(document.document_id, document.tenant_id)
        if existing is not None and existing.content_hash == document.content_hash:
            return existing, self.store.list_chunks(document.tenant_id, document.document_id), False

        with tracer.start_as_current_span("chunking") as span:
            chunks = self.chunker.chunk(document)
            span.set_attribute("chunking.chunk_count", len(chunks))
        with tracer.start_as_current_span("lexical.index_update") as span:
            index_start = time.perf_counter()
            embeddings = None
            version = None
            if self.embedding_model is not None:
                version = self.embedding_model.version
                embeddings = {
                    chunk.chunk_id: self.embedding_model.embed(chunk.content) for chunk in chunks
                }
            created = self.store.replace_document(
                document, chunks, embedding_version=version, embeddings=embeddings
            )
            LEXICAL_INDEX_UPDATE_LATENCY_SECONDS.observe(time.perf_counter() - index_start)
            span.set_attribute("indexing.chunk_count", len(chunks))

        INGESTED_DOCUMENTS_TOTAL.labels(document.source_type.value).inc()
        INGESTED_CHUNKS_TOTAL.labels(document.source_type.value).inc(len(chunks))
        return document, chunks, created
