import argparse
import json
import platform
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median
from typing import Protocol

from ctxd.app.evals.retrieval import load_corpus
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import ContextCandidate
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.documents import InMemoryDocumentStore


class Searcher(Protocol):
    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]: ...


def percentile(samples: list[float], value: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * value)))
    return ordered[index]


def summarize(samples: list[float]) -> dict[str, float]:
    return {
        "p50_ms": median(samples) * 1000,
        "p95_ms": percentile(samples, 0.95) * 1000,
        "p99_ms": percentile(samples, 0.99) * 1000,
        "qps": len(samples) / sum(samples),
    }


def build_index(
    corpus_path: Path, copies: int
) -> tuple[InMemoryDocumentStore, RealEmbeddingProvider, int]:
    corpus = load_corpus(corpus_path)
    store = InMemoryDocumentStore()
    model = RealEmbeddingProvider()
    service = IngestionService(
        store,
        StructureAwareChunker(ChunkingConfig(target_tokens=80, max_tokens=120, overlap_tokens=10)),
        model,
    )
    for copy in range(copies):
        for document in corpus.documents:
            service.ingest_content(
                content=document.content,
                source_path=f"copy-{copy}/{document.source_path}",
                source_type=document.source_type,
                tenant_id=document.tenant_id,
                metadata=document.metadata,
            )
    stats = store.lexical_statistics("eval")
    return store, model, stats.indexed_chunks


def measure(searcher: Searcher, queries: list[str], concurrency: int) -> dict[str, float | int]:
    latencies: list[float] = []
    errors = 0
    def one(query: str) -> float:
        start = time.perf_counter()
        searcher.search(query, "eval", 10)
        return time.perf_counter() - start
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(one, query) for query in queries]
        for future in as_completed(futures):
            try:
                latencies.append(future.result())
            except Exception:
                errors += 1
    return {**summarize(latencies), "errors": errors, "concurrency": concurrency}


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 semantic/hybrid in-memory benchmark")
    parser.add_argument("--corpus", type=Path, default=Path("evals/retrieval_semantic.json"))
    parser.add_argument("--copies", type=int, default=16)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    corpus = load_corpus(args.corpus)
    store, model, chunks = build_index(args.corpus, args.copies)
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, model)
    hybrid_parallel = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=True)
    hybrid_sequential = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=False)
    queries = [corpus.cases[index % len(corpus.cases)].question for index in range(args.samples)]
    embed_samples: list[float] = []
    for query in queries:
        start = time.perf_counter()
        model.embed_query(query)
        embed_samples.append(time.perf_counter() - start)
    result = {
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "model_version": model.version,
        "chunk_count": chunks,
        "methodology": (
            "In-memory exact lexical/vector scan; use PostgreSQL benchmark for DB claims."
        ),
        "embedding_query_latency": summarize(embed_samples),
        "retrieval": {
            "lexical": measure(lexical, queries, 1),
            "semantic": measure(semantic, queries, 1),
            "hybrid_parallel": measure(hybrid_parallel, queries, 1),
            "hybrid_sequential": measure(hybrid_sequential, queries, 1),
        },
        "concurrency": {
            str(c): {
                "lexical": measure(lexical, queries, c),
                "semantic": measure(semantic, queries, c),
                "hybrid": measure(hybrid_parallel, queries, c),
            }
            for c in [1, 4, 8, 16, 32]
        },
    }
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
