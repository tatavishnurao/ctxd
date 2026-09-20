import argparse
import json
import platform
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
from threading import Barrier

from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.models.domain import DocumentSourceType
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.storage.postgres import PostgresDocumentStore
from postgres_retrieval_baseline import (
    generated_document,
    percentile,
    postgres_version,
    reset_database,
)


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def prepare_corpus(database_url: str, document_count: int, pool_max: int) -> tuple[str, int]:
    tenant_id = "concurrent-benchmark"
    reset_database(database_url)
    store = PostgresDocumentStore(database_url, pool_min_size=1, pool_max_size=pool_max)
    store.start()
    try:
        chunker = StructureAwareChunker(
            ChunkingConfig(target_tokens=35, max_tokens=50, overlap_tokens=0)
        )
        for index in range(document_count):
            document = document_from_content(
                content=generated_document(index),
                source_path=f"concurrent/doc-{index}.txt",
                source_type=DocumentSourceType.TEXT,
                tenant_id=tenant_id,
            )
            store.replace_document(document, chunker.chunk(document))
        return tenant_id, store.lexical_statistics(tenant_id).indexed_chunks
    finally:
        store.close()


def run_concurrency(
    store: PostgresDocumentStore,
    tenant_id: str,
    document_count: int,
    concurrency: int,
    query_count: int,
    warmup: int,
) -> dict[str, int | float | dict[str, int]]:
    retriever = BM25Retriever(store)
    queries = [
        f"marker_{index % document_count} category_{index % 20}" for index in range(query_count)
    ]
    for query in queries[:warmup]:
        retriever.search(query, tenant_id, 10)

    barrier = Barrier(concurrency)

    def worker(worker_index: int) -> tuple[list[float], int]:
        local_latencies: list[float] = []
        errors = 0
        barrier.wait()
        for query_index in range(worker_index, query_count, concurrency):
            started = time.perf_counter()
            try:
                retriever.search(queries[query_index], tenant_id, 10)
            except Exception:
                errors += 1
            local_latencies.append(time.perf_counter() - started)
        return local_latencies, errors

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        outputs = list(executor.map(worker, range(concurrency)))
    elapsed = time.perf_counter() - started
    latencies = [latency for worker_latencies, _ in outputs for latency in worker_latencies]
    errors = sum(error_count for _, error_count in outputs)
    return {
        "concurrency": concurrency,
        "query_count": query_count,
        "errors": errors,
        "queries_per_second": query_count / elapsed,
        "p50_ms": median(latencies) * 1_000,
        "p95_ms": percentile(latencies, 0.95) * 1_000,
        "p99_ms": percentile(latencies, 0.99) * 1_000,
        "pool_statistics": store.pool_statistics(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlled PostgreSQL BM25 concurrency baseline")
    parser.add_argument(
        "--database-url",
        default="postgresql://ctxd:ctxd@localhost:5432/ctxd",
    )
    parser.add_argument("--documents", type=int, default=1_000)
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 4, 8, 16, 32])
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--queries", type=int, default=320)
    parser.add_argument("--pool-min", type=int, default=1)
    parser.add_argument("--pool-max", type=int, default=32)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    tenant_id, chunk_count = prepare_corpus(args.database_url, args.documents, args.pool_max)
    store = PostgresDocumentStore(
        args.database_url,
        pool_min_size=args.pool_min,
        pool_max_size=args.pool_max,
        query_timeout_ms=30_000,
    )
    store.start()
    try:
        result = {
            "python_version": sys.version.split()[0],
            "postgresql_version": postgres_version(args.database_url),
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
            "commit": git_commit(),
            "document_count": args.documents,
            "chunk_count": chunk_count,
            "warmup_queries_per_level": args.warmup,
            "measured_queries_per_level": args.queries,
            "pool_min_size": args.pool_min,
            "pool_max_size": args.pool_max,
            "methodology": (
                "One shared bounded psycopg pool, synchronized worker start, fixed total queries "
                "per concurrency level, perf_counter wall latency, no think time."
            ),
            "results": [
                run_concurrency(
                    store,
                    tenant_id,
                    args.documents,
                    concurrency,
                    args.queries,
                    args.warmup,
                )
                for concurrency in args.concurrency
            ],
        }
    finally:
        store.close()
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
