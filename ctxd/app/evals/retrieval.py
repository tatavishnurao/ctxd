import argparse
import json
import math
from pathlib import Path
from typing import Any

from ctxd.app.evals.schemas import RetrievalEvalCorpus, RetrievalEvalResult
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.runtime import CorpusBackend
from ctxd.app.storage.documents import InMemoryDocumentStore
from ctxd.app.storage.postgres import PostgresDocumentStore


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


def run_retrieval_eval(
    corpus: RetrievalEvalCorpus,
    store: CorpusBackend | None = None,
) -> RetrievalEvalResult:
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
    recall_values: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcg_values: list[float] = []
    for case in corpus.cases:
        candidates = retriever.search(case.question, case.tenant_id, case.top_k)
        retrieved_paths = [str(candidate.metadata["source_path"]) for candidate in candidates]
        relevant = set(case.expected_sources)
        recall = recall_at_k(retrieved_paths, relevant, case.top_k)
        rr = reciprocal_rank(retrieved_paths, relevant)
        ndcg = ndcg_at_k(retrieved_paths, relevant, case.top_k)
        per_case[case.id] = {"recall_at_k": recall, "reciprocal_rank": rr, "ndcg_at_k": ndcg}
        recall_values.append(recall)
        reciprocal_ranks.append(rr)
        ndcg_values.append(ndcg)

    count = len(corpus.cases)
    denominator = max(count, 1)
    return RetrievalEvalResult(
        case_count=count,
        recall_at_k=sum(recall_values) / denominator,
        mrr=sum(reciprocal_ranks) / denominator,
        ndcg_at_k=sum(ndcg_values) / denominator,
        per_case=per_case,
    )


def load_corpus(path: Path) -> RetrievalEvalCorpus:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    return RetrievalEvalCorpus.model_validate(raw)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run deterministic ctxd lexical retrieval evaluation"
    )
    parser.add_argument("corpus", type=Path, nargs="?", default=Path("evals/retrieval_corpus.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database-url", help="Use a migrated PostgreSQL lexical index")
    args = parser.parse_args()
    postgres_store: PostgresDocumentStore | None = None
    try:
        if args.database_url:
            postgres_store = PostgresDocumentStore(args.database_url)
            postgres_store.start()
        result = run_retrieval_eval(load_corpus(args.corpus), postgres_store)
        rendered = result.model_dump_json(indent=2)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
    finally:
        if postgres_store is not None:
            postgres_store.close()


if __name__ == "__main__":
    main()
