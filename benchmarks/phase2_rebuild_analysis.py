import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path
from statistics import median

from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import DocumentSourceType
from ctxd.app.retrieval.index import tokenize_lexical
from ctxd.app.storage.documents import InMemoryDocumentStore
from postgres_retrieval_baseline import generated_document, percentile


def legacy_search_timing(
    store: InMemoryDocumentStore,
    query: str,
    tenant_id: str,
) -> tuple[float, float]:
    rebuild_start = time.perf_counter()
    chunks = store.list_chunks(tenant_id)
    tokenized = [tokenize_lexical(chunk.content) for chunk in chunks]
    average_length = sum(len(terms) for terms in tokenized) / len(tokenized)
    document_frequency: Counter[str] = Counter()
    for terms in tokenized:
        document_frequency.update(set(terms))
    rebuild_seconds = time.perf_counter() - rebuild_start

    score_start = time.perf_counter()
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
    return rebuild_seconds, time.perf_counter() - score_start


def run_size(document_count: int, samples: int) -> dict[str, float | int]:
    tenant_id = "phase2-analysis"
    store = InMemoryDocumentStore()
    ingestion = IngestionService(
        store,
        StructureAwareChunker(ChunkingConfig(target_tokens=35, max_tokens=50, overlap_tokens=0)),
    )
    for index in range(document_count):
        ingestion.ingest_content(
            content=generated_document(index),
            source_path=f"generated/doc-{index}.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id=tenant_id,
        )
    rebuild: list[float] = []
    scoring: list[float] = []
    for index in range(samples):
        rebuild_seconds, scoring_seconds = legacy_search_timing(
            store,
            f"marker_{index % document_count} category_{index % 20}",
            tenant_id,
        )
        rebuild.append(rebuild_seconds)
        scoring.append(scoring_seconds)
    totals = [left + right for left, right in zip(rebuild, scoring, strict=True)]
    return {
        "document_count": document_count,
        "chunk_count": len(store.list_chunks(tenant_id)),
        "samples": samples,
        "rebuild_p50_ms": median(rebuild) * 1_000,
        "rebuild_p95_ms": percentile(rebuild, 0.95) * 1_000,
        "scoring_p50_ms": median(scoring) * 1_000,
        "total_p50_ms": median(totals) * 1_000,
        "rebuild_share_of_median": median(rebuild) / median(totals),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Decompose the Phase 2 query critical path")
    parser.add_argument("--document-counts", type=int, nargs="+", default=[100, 1_000])
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {
        "methodology": (
            "Reproduction of the Phase 2 per-query list/copy, tokenization, average length, "
            "document-frequency rebuild, and full chunk scoring over the deterministic corpus."
        ),
        "results": [run_size(size, args.samples) for size in args.document_counts],
    }
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
