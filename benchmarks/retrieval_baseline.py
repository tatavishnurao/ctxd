import argparse
import json
import math
import platform
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import median

from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import DocumentSourceType
from ctxd.app.retrieval.index import tokenize_lexical
from ctxd.app.storage.documents import InMemoryDocumentStore


def percentile(samples: list[float], percentile_value: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile_value)))
    return ordered[index]


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
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


def legacy_rebuilding_search(
    store: InMemoryDocumentStore,
    query: str,
    tenant_id: str,
) -> None:
    """Reproduce the Phase 2 full-corpus rebuild and score path."""
    chunks = store.list_chunks(tenant_id)
    tokenized = [tokenize_lexical(chunk.content) for chunk in chunks]
    average_length = sum(len(terms) for terms in tokenized) / len(tokenized)
    document_frequency: Counter[str] = Counter()
    for terms in tokenized:
        document_frequency.update(set(terms))
    query_frequency = Counter(tokenize_lexical(query))
    corpus_size = len(chunks)
    scores = []
    for terms in tokenized:
        frequencies = Counter(terms)
        length_normalization = 1 - 0.75 + 0.75 * len(terms) / max(average_length, 1.0)
        score = 0.0
        for term, query_count in query_frequency.items():
            frequency = frequencies.get(term, 0)
            if frequency == 0:
                continue
            df = document_frequency[term]
            inverse_document_frequency = math.log(
                1 + (corpus_size - df + 0.5) / (df + 0.5)
            )
            score += (
                inverse_document_frequency
                * (frequency * 2.5 / (frequency + 1.5 * length_normalization))
                * query_count
            )
        if score > 0:
            scores.append(score)
    sorted(scores, reverse=True)[:10]


def run_size(document_count: int, warmup: int, samples: int) -> dict[str, int | float]:
    store = InMemoryDocumentStore()
    ingestion = IngestionService(
        store,
        StructureAwareChunker(ChunkingConfig(target_tokens=35, max_tokens=50, overlap_tokens=0)),
    )
    start = time.perf_counter()
    for index in range(document_count):
        ingestion.ingest_content(
            content=generated_document(index),
            source_path=f"generated/doc-{index}.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id="benchmark",
        )
    ingestion_seconds = time.perf_counter() - start
    chunk_count = len(store.list_chunks("benchmark"))

    queries = [f"marker_{index % document_count} category_{index % 20}" for index in range(samples)]
    for query in queries[:warmup]:
        legacy_rebuilding_search(store, query, "benchmark")
    latencies: list[float] = []
    retrieval_start = time.perf_counter()
    for query in queries:
        query_start = time.perf_counter()
        legacy_rebuilding_search(store, query, "benchmark")
        latencies.append(time.perf_counter() - query_start)
    retrieval_seconds = time.perf_counter() - retrieval_start

    return {
        "document_count": document_count,
        "chunk_count": chunk_count,
        "ingestion_seconds": ingestion_seconds,
        "ingestion_documents_per_second": document_count / ingestion_seconds,
        "ingestion_chunks_per_second": chunk_count / ingestion_seconds,
        "retrieval_query_count": samples,
        "retrieval_p50_ms": median(latencies) * 1_000,
        "retrieval_p95_ms": percentile(latencies, 0.95) * 1_000,
        "retrieval_p99_ms": percentile(latencies, 0.99) * 1_000,
        "retrieval_queries_per_second": samples / retrieval_seconds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproducible Phase 2 rebuilding BM25 baseline")
    parser.add_argument("--sizes", type=int, nargs="+", default=[100, 1_000])
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "commit": git_commit(),
        "warmup_queries": args.warmup,
        "measured_queries_per_size": args.samples,
        "methodology": (
            "Sequential in-process ingestion and Phase 2 per-query corpus-statistics rebuild. "
            "Retrieval latency uses perf_counter wall time and nearest-rank percentiles."
        ),
        "results": [run_size(size, args.warmup, args.samples) for size in args.sizes],
    }
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
