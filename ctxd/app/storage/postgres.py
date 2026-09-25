import time
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any, cast

import psycopg
from opentelemetry import trace
from psycopg import Connection, sql
from psycopg.errors import QueryCanceled, UndefinedTable
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool
from pydantic import ValidationError

from ctxd.app.models.domain import (
    Chunk,
    Document,
    DocumentSourceType,
    LexicalIndexStatistics,
    SemanticIndexStatistics,
)
from ctxd.app.observability.metrics import DATABASE_OPERATION_LATENCY_SECONDS
from ctxd.app.retrieval.index import LexicalHit, tokenize_lexical
from ctxd.app.retrieval.semantic import SemanticHit
from ctxd.app.storage.errors import (
    MigrationRequiredError,
    RetrievalTimeoutError,
    StorageDataError,
    StorageError,
    StorageUnavailableError,
)

_REQUIRED_REVISION = "0002_phase4"
tracer = trace.get_tracer(__name__)
Metadata = dict[str, str | int | float | bool | None]
ChunkMetadata = dict[str, str | int | float | bool | None | list[str]]


class PostgresDocumentStore:
    """Pooled PostgreSQL document store and tenant-scoped BM25 inverted index."""

    def __init__(
        self,
        database_url: str,
        *,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
        connection_timeout_seconds: float = 5.0,
        query_timeout_ms: int = 5_000,
        use_hnsw: bool = False,
        hnsw_ef_search: int = 40,
    ) -> None:
        if pool_min_size < 0 or pool_max_size < 1 or pool_min_size > pool_max_size:
            raise ValueError("invalid PostgreSQL pool bounds")
        if connection_timeout_seconds <= 0 or query_timeout_ms <= 0:
            raise ValueError("database timeouts must be positive")
        self._connection_timeout_seconds = connection_timeout_seconds
        self._query_timeout_ms = query_timeout_ms
        # Experimental only: the default exact path remains unchanged. HNSW requires
        # a fixed-dimension expression index because the schema also supports fixtures.
        if hnsw_ef_search <= 0:
            raise ValueError("HNSW ef_search must be positive")
        self._use_hnsw = use_hnsw
        self._hnsw_ef_search = hnsw_ef_search
        self._pool = ConnectionPool[Connection[dict[str, Any]]](
            conninfo=database_url,
            min_size=pool_min_size,
            max_size=pool_max_size,
            timeout=connection_timeout_seconds,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        try:
            self._pool.open(wait=True, timeout=self._connection_timeout_seconds)
            with self._pool.connection() as connection:
                try:
                    row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
                except UndefinedTable as exc:
                    raise MigrationRequiredError(
                        f"database migration {_REQUIRED_REVISION} is required"
                    ) from exc
                if row is None or row["version_num"] != _REQUIRED_REVISION:
                    raise MigrationRequiredError(
                        f"database migration {_REQUIRED_REVISION} is required"
                    )
            self._started = True
        except MigrationRequiredError:
            self._pool.close()
            raise
        except (psycopg.Error, TimeoutError) as exc:
            self._pool.close()
            raise StorageUnavailableError("PostgreSQL is unavailable during startup") from exc

    def close(self) -> None:
        self._pool.close()
        self._started = False

    def pool_statistics(self) -> dict[str, int]:
        return dict(self._pool.get_stats())

    @contextmanager
    def _connection(self, operation: str) -> Iterator[Connection[dict[str, Any]]]:
        started = time.perf_counter()
        status = "success"
        try:
            with self._pool.connection(timeout=self._connection_timeout_seconds) as connection:
                yield connection
        except QueryCanceled as exc:
            status = "timeout"
            raise RetrievalTimeoutError(f"database operation timed out: {operation}") from exc
        except (psycopg.OperationalError, TimeoutError) as exc:
            status = "unavailable"
            raise StorageUnavailableError(f"database unavailable during {operation}") from exc
        except psycopg.Error as exc:
            status = "error"
            raise StorageError(f"database operation failed: {operation}") from exc
        except StorageError:
            status = "error"
            raise
        except Exception:
            status = "error"
            raise
        finally:
            DATABASE_OPERATION_LATENCY_SECONDS.labels(operation, status).observe(
                time.perf_counter() - started
            )

    @staticmethod
    def _validate_chunks(document_id: str, tenant_id: str, chunks: Sequence[Chunk]) -> None:
        if any(
            chunk.document_id != document_id or chunk.tenant_id != tenant_id for chunk in chunks
        ):
            raise ValueError("all chunks must belong to the requested document and tenant")

    @staticmethod
    def _executemany(
        connection: Connection[dict[str, Any]],
        statement: str,
        parameters: Sequence[Sequence[object]],
    ) -> None:
        with connection.cursor() as cursor:
            cursor.executemany(statement, parameters)

    @staticmethod
    def _document_lock_key(tenant_id: str, document_id: str) -> str:
        return f"{len(tenant_id)}:{tenant_id}{document_id}"

    def replace_document(
        self,
        document: Document,
        chunks: Sequence[Chunk],
        *,
        embedding_version: str | None = None,
        embeddings: dict[str, list[float]] | None = None,
    ) -> bool:
        self._validate_chunks(document.document_id, document.tenant_id, chunks)
        return self._replace_document(
            document,
            chunks,
            skip_if_unchanged=True,
            embedding_version=embedding_version,
            embeddings=embeddings,
        )

    def _replace_document(
        self,
        document: Document,
        chunks: Sequence[Chunk],
        *,
        skip_if_unchanged: bool,
        embedding_version: str | None = None,
        embeddings: dict[str, list[float]] | None = None,
    ) -> bool:
        with self._connection("document_replace") as connection, connection.transaction():
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (self._document_lock_key(document.tenant_id, document.document_id),),
            )
            connection.execute(
                """
                    INSERT INTO lexical_corpus_stats
                        (tenant_id, indexed_documents, chunk_count, total_chunk_length)
                    VALUES (%s, 0, 0, 0)
                    ON CONFLICT (tenant_id) DO NOTHING
                    """,
                (document.tenant_id,),
            )
            connection.execute(
                "SELECT tenant_id FROM lexical_corpus_stats WHERE tenant_id = %s FOR UPDATE",
                (document.tenant_id,),
            )
            previous = connection.execute(
                """
                    SELECT content_hash FROM documents
                    WHERE tenant_id = %s AND document_id = %s
                    FOR UPDATE
                    """,
                (document.tenant_id, document.document_id),
            ).fetchone()
            created = previous is None
            if (
                skip_if_unchanged
                and previous is not None
                and previous["content_hash"] == document.content_hash
            ):
                return False

            with tracer.start_as_current_span("database.document_upsert"):
                connection.execute(
                    """
                        INSERT INTO documents (
                            document_id, tenant_id, source_path, source_type,
                            content, content_hash, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (tenant_id, document_id) DO UPDATE SET
                            source_path = EXCLUDED.source_path,
                            source_type = EXCLUDED.source_type,
                            content = EXCLUDED.content,
                            content_hash = EXCLUDED.content_hash,
                            metadata = EXCLUDED.metadata,
                            updated_at = now()
                        """,
                    (
                        document.document_id,
                        document.tenant_id,
                        document.source_path,
                        document.source_type.value,
                        document.content,
                        document.content_hash,
                        Jsonb(document.metadata),
                    ),
                )
            self._replace_chunks_and_index(
                connection,
                document.document_id,
                document.tenant_id,
                chunks,
                document_delta=1 if created else 0,
                embedding_version=embedding_version,
                embeddings=embeddings,
            )
            return created

    def _replace_chunks_and_index(
        self,
        connection: Connection[dict[str, Any]],
        document_id: str,
        tenant_id: str,
        chunks: Sequence[Chunk],
        *,
        document_delta: int,
        embedding_version: str | None = None,
        embeddings: dict[str, list[float]] | None = None,
    ) -> None:
        with tracer.start_as_current_span("database.chunk_replace") as span:
            old = connection.execute(
                """
                SELECT chunk_id, lexical_length FROM chunks
                WHERE tenant_id = %s AND document_id = %s
                """,
                (tenant_id, document_id),
            ).fetchall()
            old_ids = [str(row["chunk_id"]) for row in old]
            old_total_length = sum(int(row["lexical_length"]) for row in old)
            old_term_counts: dict[str, int] = {}
            if old_ids:
                term_rows = connection.execute(
                    """
                    SELECT term, count(*) AS chunk_frequency
                    FROM lexical_postings
                    WHERE tenant_id = %s AND chunk_id = ANY(%s)
                    GROUP BY term
                    """,
                    (tenant_id, old_ids),
                ).fetchall()
                old_term_counts = {
                    str(row["term"]): int(row["chunk_frequency"]) for row in term_rows
                }
            connection.execute(
                "DELETE FROM chunks WHERE tenant_id = %s AND document_id = %s",
                (tenant_id, document_id),
            )
            if old_term_counts:
                self._executemany(
                    connection,
                    """
                    UPDATE lexical_terms
                    SET document_frequency = document_frequency - %s
                    WHERE tenant_id = %s AND term = %s
                    """,
                    [(frequency, tenant_id, term) for term, frequency in old_term_counts.items()],
                )
                connection.execute(
                    "DELETE FROM lexical_terms WHERE tenant_id = %s AND document_frequency <= 0",
                    (tenant_id,),
                )

            posting_rows: list[tuple[str, str, str, int]] = []
            added_document_frequency: Counter[str] = Counter()
            total_new_length = 0
            chunk_rows: list[tuple[object, ...]] = []
            for chunk in chunks:
                frequencies = Counter(tokenize_lexical(chunk.content))
                lexical_length = sum(frequencies.values())
                total_new_length += lexical_length
                chunk_rows.append(
                    (
                        chunk.chunk_id,
                        chunk.document_id,
                        chunk.tenant_id,
                        chunk.ordinal,
                        chunk.content,
                        chunk.content_hash,
                        chunk.token_count,
                        lexical_length,
                        chunk.start_line,
                        chunk.end_line,
                        Jsonb(chunk.metadata),
                    )
                )
                for term, frequency in frequencies.items():
                    posting_rows.append((tenant_id, term, chunk.chunk_id, frequency))
                    added_document_frequency[term] += 1

            if chunk_rows:
                self._executemany(
                    connection,
                    """
                    INSERT INTO chunks (
                        chunk_id, document_id, tenant_id, ordinal, content,
                        content_hash, token_count, lexical_length, start_line,
                        end_line, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    chunk_rows,
                )
            if posting_rows:
                self._executemany(
                    connection,
                    """
                    INSERT INTO lexical_terms (tenant_id, term, document_frequency)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (tenant_id, term) DO UPDATE SET
                        document_frequency = lexical_terms.document_frequency
                            + EXCLUDED.document_frequency
                    """,
                    [
                        (tenant_id, term, frequency)
                        for term, frequency in added_document_frequency.items()
                    ],
                )
                self._executemany(
                    connection,
                    """
                    INSERT INTO lexical_postings
                        (tenant_id, term, chunk_id, term_frequency)
                    VALUES (%s, %s, %s, %s)
                    """,
                    posting_rows,
                )
            connection.execute(
                """
                UPDATE lexical_corpus_stats SET
                    indexed_documents = indexed_documents + %s,
                    chunk_count = chunk_count + %s,
                    total_chunk_length = total_chunk_length + %s,
                    updated_at = now()
                WHERE tenant_id = %s
                """,
                (
                    document_delta,
                    len(chunks) - len(old),
                    total_new_length - old_total_length,
                    tenant_id,
                ),
            )
            if embedding_version and embeddings is not None:
                if old_ids:
                    connection.execute(
                        "DELETE FROM chunk_embeddings WHERE tenant_id = %s AND chunk_id = ANY(%s)",
                        (tenant_id, old_ids),
                    )
                self._executemany(
                    connection,
                    "INSERT INTO chunk_embeddings (tenant_id, chunk_id, "
                    "embedding_version, embedding, dimension) "
                    "VALUES (%s, %s, %s, %s::vector, %s)",
                    [
                        (
                            tenant_id,
                            chunk.chunk_id,
                            embedding_version,
                            embeddings[chunk.chunk_id],
                            len(embeddings[chunk.chunk_id]),
                        )
                        for chunk in chunks
                    ],
                )
            span.set_attribute("indexing.chunk_count", len(chunks))

    def upsert_document(self, document: Document) -> bool:
        return self._replace_document(document, [], skip_if_unchanged=True)

    def replace_chunks(
        self,
        document_id: str,
        tenant_id: str,
        chunks: Sequence[Chunk],
    ) -> None:
        self._validate_chunks(document_id, tenant_id, chunks)
        document = self.get_document(document_id, tenant_id)
        if document is None:
            raise KeyError(f"document not found for tenant: {document_id}")
        self._replace_document(document, chunks, skip_if_unchanged=False)

    @staticmethod
    def _document_from_row(row: Mapping[str, Any]) -> Document:
        metadata = row["metadata"]
        if not isinstance(metadata, dict):
            raise StorageDataError("persisted document metadata is not an object")
        try:
            return Document(
                document_id=str(row["document_id"]),
                tenant_id=str(row["tenant_id"]),
                source_path=str(row["source_path"]),
                source_type=DocumentSourceType(str(row["source_type"])),
                content=str(row["content"]),
                content_hash=str(row["content_hash"]),
                metadata=cast(Metadata, metadata),
            )
        except (ValueError, ValidationError) as exc:
            raise StorageDataError("persisted document is malformed") from exc

    @staticmethod
    def _chunk_from_row(row: Mapping[str, Any]) -> Chunk:
        metadata = row["metadata"]
        if not isinstance(metadata, dict):
            raise StorageDataError("persisted chunk metadata is not an object")
        try:
            return Chunk(
                chunk_id=str(row["chunk_id"]),
                document_id=str(row["document_id"]),
                tenant_id=str(row["tenant_id"]),
                content=str(row["content"]),
                content_hash=str(row["content_hash"]),
                start_line=int(row["start_line"]),
                end_line=int(row["end_line"]),
                token_count=int(row["token_count"]),
                ordinal=int(row["ordinal"]),
                metadata=cast(ChunkMetadata, metadata),
            )
        except (ValueError, ValidationError) as exc:
            raise StorageDataError("persisted chunk is malformed") from exc

    def get_document(self, document_id: str, tenant_id: str) -> Document | None:
        with self._connection("document_get") as connection:
            row = connection.execute(
                """
                SELECT document_id, tenant_id, source_path, source_type,
                       content, content_hash, metadata
                FROM documents WHERE tenant_id = %s AND document_id = %s
                """,
                (tenant_id, document_id),
            ).fetchone()
            return self._document_from_row(row) if row else None

    def get_chunk(self, chunk_id: str, tenant_id: str) -> Chunk | None:
        with self._connection("chunk_get") as connection:
            row = connection.execute(
                """
                SELECT chunk_id, document_id, tenant_id, ordinal, content,
                       content_hash, token_count, start_line, end_line, metadata
                FROM chunks WHERE tenant_id = %s AND chunk_id = %s
                """,
                (tenant_id, chunk_id),
            ).fetchone()
            return self._chunk_from_row(row) if row else None

    def list_chunks(self, tenant_id: str, document_id: str | None = None) -> list[Chunk]:
        with self._connection("chunk_list") as connection:
            if document_id is None:
                rows = connection.execute(
                    """
                    SELECT chunk_id, document_id, tenant_id, ordinal, content,
                           content_hash, token_count, start_line, end_line, metadata
                    FROM chunks WHERE tenant_id = %s
                    ORDER BY document_id, ordinal, chunk_id
                    """,
                    (tenant_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT chunk_id, document_id, tenant_id, ordinal, content,
                           content_hash, token_count, start_line, end_line, metadata
                    FROM chunks WHERE tenant_id = %s AND document_id = %s
                    ORDER BY document_id, ordinal, chunk_id
                    """,
                    (tenant_id, document_id),
                ).fetchall()
            return [self._chunk_from_row(row) for row in rows]

    def delete_document(self, document_id: str, tenant_id: str) -> bool:
        with self._connection("document_delete") as connection, connection.transaction():
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (self._document_lock_key(tenant_id, document_id),),
            )
            connection.execute(
                """
                    INSERT INTO lexical_corpus_stats
                        (tenant_id, indexed_documents, chunk_count, total_chunk_length)
                    VALUES (%s, 0, 0, 0)
                    ON CONFLICT (tenant_id) DO NOTHING
                    """,
                (tenant_id,),
            )
            connection.execute(
                "SELECT tenant_id FROM lexical_corpus_stats WHERE tenant_id = %s FOR UPDATE",
                (tenant_id,),
            )
            existing = connection.execute(
                "SELECT 1 FROM documents WHERE tenant_id = %s AND document_id = %s FOR UPDATE",
                (tenant_id, document_id),
            ).fetchone()
            if existing is None:
                return False
            self._replace_chunks_and_index(
                connection,
                document_id,
                tenant_id,
                [],
                document_delta=-1,
            )
            connection.execute(
                "DELETE FROM documents WHERE tenant_id = %s AND document_id = %s",
                (tenant_id, document_id),
            )
            return True

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
        value_placeholders = sql.SQL(", ").join(sql.SQL("(%s, %s)") for _ in query_frequency)
        statement = sql.SQL(
            """
            WITH query_terms(term, query_frequency) AS (VALUES {values}),
            scored AS (
                SELECT p.chunk_id,
                    sum(
                        ln(1.0 + (s.chunk_count - t.document_frequency + 0.5)
                            / (t.document_frequency + 0.5))
                        * (p.term_frequency * (%s + 1.0)
                            / (p.term_frequency + %s * (1.0 - %s + %s
                                * c.lexical_length
                                / greatest(s.total_chunk_length::double precision
                                    / greatest(s.chunk_count, 1), 1.0))))
                        * q.query_frequency
                    ) AS score
                FROM query_terms q
                JOIN lexical_postings p
                    ON p.tenant_id = %s AND p.term = q.term
                JOIN lexical_terms t
                    ON t.tenant_id = p.tenant_id AND t.term = p.term
                JOIN chunks c
                    ON c.tenant_id = p.tenant_id AND c.chunk_id = p.chunk_id
                JOIN lexical_corpus_stats s ON s.tenant_id = p.tenant_id
                GROUP BY p.chunk_id
            )
            SELECT c.chunk_id, c.document_id, c.tenant_id, c.ordinal, c.content,
                   c.content_hash, c.token_count, c.start_line, c.end_line,
                   c.metadata, scored.score
            FROM scored
            JOIN chunks c ON c.tenant_id = %s AND c.chunk_id = scored.chunk_id
            WHERE scored.score > 0
            ORDER BY scored.score DESC, c.chunk_id
            LIMIT %s
            """
        ).format(values=value_placeholders)
        parameters: list[object] = []
        for term, frequency in query_frequency.items():
            parameters.extend((term, frequency))
        parameters.extend((k1, k1, b, b, tenant_id, tenant_id, top_k))
        with self._connection("lexical_search") as connection, connection.transaction():
            connection.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (f"{self._query_timeout_ms}ms",),
            )
            rows = connection.execute(statement, parameters).fetchall()
            return [
                LexicalHit(chunk=self._chunk_from_row(row), score=float(row["score"]))
                for row in rows
            ]

    def search_semantic(
        self, query_vector: list[float], tenant_id: str, top_k: int, *, version: str
    ) -> list[SemanticHit]:
        if not query_vector:
            return []
        # Exact pgvector cosine search. No ANN index is used: at the currently
        # measured scales an ANN quality/maintenance tradeoff is not justified.
        with self._connection("semantic_search") as connection, connection.transaction():
            connection.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                (f"{self._query_timeout_ms}ms",),
            )
            if self._use_hnsw:
                connection.execute(
                    "SELECT set_config('hnsw.ef_search', %s, true)",
                    (str(self._hnsw_ef_search),),
                )
            vector_expression = "e.embedding::vector(256)" if self._use_hnsw else "e.embedding"
            statement = f"""
                SELECT 1.0 - ({vector_expression} <=> %s::vector) AS score,
                       c.chunk_id, c.document_id, c.tenant_id, c.ordinal, c.content,
                       c.content_hash, c.token_count, c.start_line, c.end_line, c.metadata
                FROM chunk_embeddings e JOIN chunks c USING (tenant_id, chunk_id)
                WHERE e.tenant_id = %s AND e.embedding_version = %s
                  AND e.dimension = %s
                ORDER BY {vector_expression} <=> %s::vector, c.chunk_id
                LIMIT %s
            """
            rows = connection.execute(
                statement,
                (query_vector, tenant_id, version, len(query_vector), query_vector, top_k),
            ).fetchall()
            return [SemanticHit(self._chunk_from_row(row), float(row["score"])) for row in rows]

    def semantic_statistics(self, tenant_id: str) -> SemanticIndexStatistics:
        with self._connection("semantic_statistics") as connection:
            row = connection.execute(
                "SELECT count(*) AS count, max(embedding_version) AS version, "
                "max(dimension) AS dimension FROM chunk_embeddings WHERE tenant_id = %s",
                (tenant_id,),
            ).fetchone()
            if row is None:
                return SemanticIndexStatistics(
                    indexed_chunks=0, embedding_version="", embedding_dimension=1
                )
            return SemanticIndexStatistics(
                indexed_chunks=int(row["count"]),
                embedding_version=str(row["version"] or ""),
                embedding_dimension=int(row["dimension"] or 1),
            )

    def lexical_statistics(self, tenant_id: str) -> LexicalIndexStatistics:
        with self._connection("lexical_statistics") as connection:
            row = connection.execute(
                """
                SELECT s.indexed_documents, s.chunk_count, s.total_chunk_length,
                       count(t.term) AS vocabulary_size
                FROM lexical_corpus_stats s
                LEFT JOIN lexical_terms t ON t.tenant_id = s.tenant_id
                WHERE s.tenant_id = %s
                GROUP BY s.indexed_documents, s.chunk_count, s.total_chunk_length
                """,
                (tenant_id,),
            ).fetchone()
            if row is None:
                return LexicalIndexStatistics(
                    indexed_documents=0,
                    indexed_chunks=0,
                    vocabulary_size=0,
                    average_chunk_length=0.0,
                )
            chunk_count = int(row["chunk_count"])
            return LexicalIndexStatistics(
                indexed_documents=int(row["indexed_documents"]),
                indexed_chunks=chunk_count,
                vocabulary_size=int(row["vocabulary_size"]),
                average_chunk_length=(
                    int(row["total_chunk_length"]) / chunk_count if chunk_count else 0.0
                ),
            )
