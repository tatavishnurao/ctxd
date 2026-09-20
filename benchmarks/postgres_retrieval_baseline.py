import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from statistics import median

import psycopg
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.models.domain import DocumentSourceType
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.storage.postgres import PostgresDocumentStore


def percentile(samples: list[float], value: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * value)))
    return ordered[index]


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def generated_document(index: int) -> str:
    paragraphs = []
    for section in range(12):
        paragraphs.append(
            f"Document {index} section {section} describes topic_{index}_{section}. "
            f"The deterministic retrieval corpus includes marker_{index} "
            f"and category_{index % 20}. "
            "Operational guidance covers validation, recovery, monitoring, ownership, and testing."
        )
    return "\n\n".join(paragraphs)


def reset_database(database_url: str) -> None:
    """Destructively reset all corpus tables; benchmarks require a dedicated database."""
    with psycopg.connect(database_url) as connection, connection.transaction():
        connection.execute(
            "TRUNCATE lexical_postings, lexical_terms, lexical_corpus_stats, chunks, documents"
        )


def postgres_version(database_url: str) -> str:
    with psycopg.connect(database_url) as connection:
        row = connection.execute("SHOW server_version").fetchone()
        return str(row[0]) if row else "unknown"


def run_size(
    database_url: str,
    document_count: int,
    warmup: int,
    samples: int,
    pool_min: int,
    pool_max: int,
) -> dict[str, int | float]:
    tenant_id = f"benchmark-{document_count}"
    reset_database(database_url)
    store = PostgresDocumentStore(
        database_url,
        pool_min_size=pool_min,
        pool_max_size=pool_max,
        query_timeout_ms=30_000,
    )
    store.start()
    try:
        chunker = StructureAwareChunker(
            ChunkingConfig(target_tokens=35, max_tokens=50, overlap_tokens=0)
        )
        index_latencies: list[float] = []
        ingestion_start = time.perf_counter()
        for index in range(document_count):
            document = document_from_content(
                content=generated_document(index),
                source_path=f"generated/doc-{index}.txt",
                source_type=DocumentSourceType.TEXT,
                tenant_id=tenant_id,
            )
            chunks = chunker.chunk(document)
            update_start = time.perf_counter()
            store.replace_document(document, chunks)
            index_latencies.append(time.perf_counter() - update_start)
        ingestion_seconds = time.perf_counter() - ingestion_start
        statistics = store.lexical_statistics(tenant_id)
        retriever = BM25Retriever(store)
        queries = [
            f"marker_{index % document_count} category_{index % 20}"
            for index in range(samples)
        ]
        for query in queries[:warmup]:
            retriever.search(query, tenant_id, 10)

        retrieval_latencies: list[float] = []
        index_search_latencies: list[float] = []
        retrieval_start = time.perf_counter()
        for query in queries:
            query_start = time.perf_counter()
            retriever.search(query, tenant_id, 10)
            retrieval_latencies.append(time.perf_counter() - query_start)
        retrieval_seconds = time.perf_counter() - retrieval_start
        for query in queries:
            query_start = time.perf_counter()
            store.search_lexical(query, tenant_id, 10, k1=1.5, b=0.75)
            index_search_latencies.append(time.perf_counter() - query_start)

        return {
            "document_count": document_count,
            "chunk_count": statistics.indexed_chunks,
            "vocabulary_size": statistics.vocabulary_size,
            "ingestion_seconds": ingestion_seconds,
            "ingestion_documents_per_second": document_count / ingestion_seconds,
            "ingestion_chunks_per_second": statistics.indexed_chunks / ingestion_seconds,
            "index_update_p50_ms": median(index_latencies) * 1_000,
            "index_update_p95_ms": percentile(index_latencies, 0.95) * 1_000,
            "index_update_p99_ms": percentile(index_latencies, 0.99) * 1_000,
            "retrieval_query_count": samples,
            "retrieval_p50_ms": median(retrieval_latencies) * 1_000,
            "retrieval_p95_ms": percentile(retrieval_latencies, 0.95) * 1_000,
            "retrieval_p99_ms": percentile(retrieval_latencies, 0.99) * 1_000,
            "retrieval_queries_per_second": samples / retrieval_seconds,
            "index_search_p50_ms": median(index_search_latencies) * 1_000,
            "index_search_p95_ms": percentile(index_search_latencies, 0.95) * 1_000,
            "index_search_p99_ms": percentile(index_search_latencies, 0.99) * 1_000,
        }
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="PostgreSQL incremental BM25 baseline")
    parser.add_argument(
        "--database-url",
        default="postgresql://ctxd:ctxd@localhost:5432/ctxd",
    )
    parser.add_argument("--document-counts", type=int, nargs="+", default=[100, 1_000, 4_167])
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--pool-min", type=int, default=1)
    parser.add_argument("--pool-max", type=int, default=32)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {
        "python_version": sys.version.split()[0],
        "postgresql_version": postgres_version(args.database_url),
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "commit": git_commit(),
        "warmup_queries": args.warmup,
        "measured_queries_per_size": args.samples,
        "concurrency": 1,
        "pool_min_size": args.pool_min,
        "pool_max_size": args.pool_max,
        "methodology": (
            "Sequential document construction, chunking, transactional PostgreSQL replacement, "
            "against destructively reset corpus tables, then warm and measured BM25 queries "
            "over persisted postings. Wall time uses "
            "perf_counter and the same percentile method as Phase 2."
        ),
        "results": [
            run_size(
                args.database_url,
                count,
                args.warmup,
                args.samples,
                args.pool_min,
                args.pool_max,
            )
            for count in args.document_counts
        ],
    }
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
