import argparse
import json
import math
from pathlib import Path
from typing import Any, Protocol

from ctxd.app.evals.schemas import (
    RetrievalEvalCorpus,
    RetrievalEvalResult,
    RetrievalMetrics,
    RetrievalModeEvalResult,
)
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import ContextCandidate
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import (
    EmbeddingModel,
    FakeHashEmbeddingProvider,
    RealEmbeddingProvider,
    SemanticRetriever,
)
from ctxd.app.runtime import CorpusBackend
from ctxd.app.storage.documents import InMemoryDocumentStore
from ctxd.app.storage.postgres import PostgresDocumentStore


class Searcher(Protocol):
    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]: ...


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for rank, source in enumerate(retrieved, start=1):
        if source in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, source in enumerate(retrieved[:k], start=1)
        if source in relevant
    )
    ideal_count = min(k, len(relevant))
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal_dcg


def _metrics(rows: list[tuple[list[str], set[str]]]) -> RetrievalMetrics:
    denominator = max(len(rows), 1)
    return RetrievalMetrics(
        recall_at_1=sum(recall_at_k(got, expected, 1) for got, expected in rows) / denominator,
        recall_at_5=sum(recall_at_k(got, expected, 5) for got, expected in rows) / denominator,
        recall_at_10=sum(recall_at_k(got, expected, 10) for got, expected in rows) / denominator,
        mrr=sum(reciprocal_rank(got, expected) for got, expected in rows) / denominator,
        ndcg_at_5=sum(ndcg_at_k(got, expected, 5) for got, expected in rows) / denominator,
        ndcg_at_10=sum(ndcg_at_k(got, expected, 10) for got, expected in rows) / denominator,
    )


def _result_rows(candidates: list[ContextCandidate]) -> list[dict[str, Any]]:
    return [
        {
            "source": candidate.metadata.get("source_path"),
            "chunk_id": candidate.source_id,
            "score": candidate.relevance_score,
            "lexical_rank": candidate.metadata.get("lexical_rank"),
            "semantic_rank": candidate.metadata.get("semantic_rank"),
            "raw_lexical_score": candidate.metadata.get("raw_lexical_score"),
            "raw_vector_score": candidate.metadata.get("raw_vector_score"),
            "fused_score": candidate.metadata.get("fused_score"),
        }
        for candidate in candidates
    ]


def _rank(paths: list[str], expected: set[str]) -> int | None:
    return next((rank for rank, path in enumerate(paths, 1) if path in expected), None)


def _classify_failure(
    lexical_rank: int | None, semantic_rank: int | None, hybrid_rank: int | None, category: str
) -> str:
    if category == "ambiguous":
        return "annotation ambiguity"
    if category == "near duplicate":
        return "near-duplicate confusion"
    if lexical_rank is None and semantic_rank is not None:
        return "lexical mismatch"
    if semantic_rank is None and lexical_rank is not None:
        return "semantic miss"
    if semantic_rank is not None and semantic_rank > 1:
        return "semantic overgeneralization"
    if hybrid_rank is None and (lexical_rank is not None or semantic_rank is not None):
        return "fusion demotion"
    if lexical_rank is None and semantic_rank is None:
        return "insufficient candidate depth"
    return "other"


def run_mode_evaluation(
    corpus: RetrievalEvalCorpus,
    store: CorpusBackend | None = None,
    embedding_model: EmbeddingModel | None = None,
    *,
    candidate_depth: int = 20,
    rrf_k: int = 60,
    parallel_hybrid: bool = True,
) -> RetrievalModeEvalResult:
    resolved_store = store or InMemoryDocumentStore()
    model = embedding_model or FakeHashEmbeddingProvider()
    ingestion = IngestionService(
        resolved_store,
        StructureAwareChunker(ChunkingConfig(target_tokens=80, max_tokens=120, overlap_tokens=10)),
        model,
    )
    for document in corpus.documents:
        ingestion.ingest_content(
            content=document.content,
            source_path=document.source_path,
            source_type=document.source_type,
            tenant_id=document.tenant_id,
            metadata=document.metadata,
        )

    lexical = BM25Retriever(resolved_store)
    semantic = SemanticRetriever(resolved_store, model)
    retrievers: dict[str, Searcher] = {
        "lexical": lexical,
        "semantic": semantic,
        "hybrid": HybridRetriever(
            lexical,
            semantic,
            rrf_k=rrf_k,
            candidate_depth=candidate_depth,
            parallel=parallel_hybrid,
        ),
    }
    observations: dict[str, list[tuple[list[str], set[str]]]] = {
        mode: [] for mode in retrievers
    }
    category_observations: dict[str, dict[str, list[tuple[list[str], set[str]]]]] = {}
    failures: list[dict[str, Any]] = []

    for case in corpus.cases:
        expected = set(case.expected_sources)
        category = str(case.metadata.get("category", case.task_type)).replace("_", " ")
        category_rows = category_observations.setdefault(
            category, {mode: [] for mode in retrievers}
        )
        result_by_mode: dict[str, list[ContextCandidate]] = {}
        paths_by_mode: dict[str, list[str]] = {}
        for mode, retriever in retrievers.items():
            candidates = retriever.search(case.question, case.tenant_id, 10)
            paths = [str(candidate.metadata["source_path"]) for candidate in candidates]
            result_by_mode[mode] = candidates
            paths_by_mode[mode] = paths
            row = (paths, expected)
            observations[mode].append(row)
            category_rows[mode].append(row)
        ranks = {mode: _rank(paths, expected) for mode, paths in paths_by_mode.items()}
        if any(rank != 1 for rank in ranks.values()):
            failures.append(
                {
                    "case_id": case.id,
                    "category": category,
                    "expected_sources": sorted(expected),
                    "lexical_top_results": _result_rows(result_by_mode["lexical"]),
                    "semantic_top_results": _result_rows(result_by_mode["semantic"]),
                    "hybrid_top_results": _result_rows(result_by_mode["hybrid"]),
                    "lexical_rank": ranks["lexical"],
                    "semantic_rank": ranks["semantic"],
                    "hybrid_rank": ranks["hybrid"],
                    "failure_class": _classify_failure(
                        ranks["lexical"], ranks["semantic"], ranks["hybrid"], category
                    ),
                }
            )

    return RetrievalModeEvalResult(
        case_count=len(corpus.cases),
        model_version=model.version,
        modes={mode: _metrics(rows) for mode, rows in observations.items()},
        categories={
            category: {mode: _metrics(rows) for mode, rows in modes.items()}
            for category, modes in category_observations.items()
        },
        failures=failures,
    )


def run_retrieval_eval(
    corpus: RetrievalEvalCorpus,
    store: CorpusBackend | None = None,
) -> RetrievalEvalResult:
    """Preserved Phase 3 lexical evaluator and output contract."""
    resolved_store = store or InMemoryDocumentStore()
    ingestion = IngestionService(
        resolved_store,
        StructureAwareChunker(ChunkingConfig(target_tokens=80, max_tokens=120, overlap_tokens=10)),
    )
    for document in corpus.documents:
        ingestion.ingest_content(
            content=document.content,
            source_path=document.source_path,
            source_type=document.source_type,
            tenant_id=document.tenant_id,
            metadata=document.metadata,
        )
    retriever = BM25Retriever(resolved_store)
    per_case: dict[str, dict[str, float]] = {}
    rows: list[tuple[list[str], set[str]]] = []
    for case in corpus.cases:
        candidates = retriever.search(case.question, case.tenant_id, case.top_k)
        paths = [str(candidate.metadata["source_path"]) for candidate in candidates]
        relevant = set(case.expected_sources)
        rows.append((paths, relevant))
        per_case[case.id] = {
            "recall_at_k": recall_at_k(paths, relevant, case.top_k),
            "reciprocal_rank": reciprocal_rank(paths, relevant),
            "ndcg_at_k": ndcg_at_k(paths, relevant, case.top_k),
        }
    count = len(rows)
    denominator = max(count, 1)
    return RetrievalEvalResult(
        case_count=count,
        recall_at_k=sum(
            recall_at_k(got, rel, corpus.cases[i].top_k)
            for i, (got, rel) in enumerate(rows)
        )
        / denominator,
        mrr=sum(reciprocal_rank(got, rel) for got, rel in rows) / denominator,
        ndcg_at_k=sum(
            ndcg_at_k(got, rel, corpus.cases[i].top_k)
            for i, (got, rel) in enumerate(rows)
        )
        / denominator,
        per_case=per_case,
    )


def load_corpus(path: Path) -> RetrievalEvalCorpus:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    return RetrievalEvalCorpus.model_validate(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ctxd retrieval evaluation")
    parser.add_argument("corpus", type=Path, nargs="?", default=Path("evals/retrieval_corpus.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database-url", help="Use a migrated PostgreSQL index")
    parser.add_argument("--all-modes", action="store_true")
    parser.add_argument("--real-embeddings", action="store_true")
    parser.add_argument("--candidate-depth", type=int, default=20, choices=(5, 10, 20, 50))
    parser.add_argument("--sequential-hybrid", action="store_true")
    args = parser.parse_args()
    postgres_store: PostgresDocumentStore | None = None
    try:
        if args.database_url:
            postgres_store = PostgresDocumentStore(args.database_url)
            postgres_store.start()
        corpus = load_corpus(args.corpus)
        if args.all_modes:
            model: EmbeddingModel = (
                RealEmbeddingProvider() if args.real_embeddings else FakeHashEmbeddingProvider()
            )
            result: RetrievalEvalResult | RetrievalModeEvalResult = run_mode_evaluation(
                corpus,
                postgres_store,
                model,
                candidate_depth=args.candidate_depth,
                parallel_hybrid=not args.sequential_hybrid,
            )
        else:
            result = run_retrieval_eval(corpus, postgres_store)
        rendered = result.model_dump_json(indent=2)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
    finally:
        if postgres_store is not None:
            postgres_store.close()


if __name__ == "__main__":
    main()
