"""Phase 5 candidate-recall and oracle-reranking feasibility audit.

This is offline evaluation only. It does not add a production reranker.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ctxd.app.evals.retrieval import (
    load_corpus,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.documents import InMemoryDocumentStore

DEPTHS = (5, 10, 20, 50)


def unique_sources(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(paths))


def metrics(rows: list[tuple[list[str], set[str]]]) -> dict[str, float]:
    normalized = [(unique_sources(got), expected) for got, expected in rows]
    count = max(len(normalized), 1)
    return {
        "recall_at_1": sum(recall_at_k(got, expected, 1) for got, expected in normalized) / count,
        "recall_at_5": sum(recall_at_k(got, expected, 5) for got, expected in normalized) / count,
        "recall_at_10": sum(recall_at_k(got, expected, 10) for got, expected in normalized) / count,
        "mrr": sum(reciprocal_rank(got, expected) for got, expected in normalized) / count,
        "ndcg_at_5": sum(ndcg_at_k(got, expected, 5) for got, expected in normalized) / count,
        "ndcg_at_10": sum(ndcg_at_k(got, expected, 10) for got, expected in normalized) / count,
    }


def rank(paths: list[str], expected: set[str]) -> int | None:
    return next((index for index, path in enumerate(paths, 1) if path in expected), None)


def source(candidate: Any) -> str:
    return str(candidate.metadata.get("source_path", ""))


def oracle_order(paths: list[str], expected: set[str]) -> list[str]:
    # Python's stable sort preserves deterministic RRF order inside both groups.
    return sorted(paths, key=lambda path: path not in expected)


def token_evidence(query: str, content: str) -> list[str]:
    query_tokens = {token.casefold().strip(".,?!:;()[]{}") for token in query.split()}
    content_tokens = {token.casefold().strip(".,?!:;()[]{}") for token in content.split()}
    return sorted((query_tokens & content_tokens) - {"", "the", "a", "an", "is", "of", "to"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("evals/retrieval_semantic.json"))
    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=Path("benchmarks/phase5_candidate_recall.json"),
    )
    parser.add_argument(
        "--oracle-output", type=Path, default=Path("benchmarks/phase5_oracle_reranker.json")
    )
    parser.add_argument(
        "--overgeneralization-output",
        type=Path,
        default=Path("benchmarks/phase5_semantic_overgeneralization.json"),
    )
    args = parser.parse_args()

    corpus = load_corpus(args.corpus)
    store = InMemoryDocumentStore()
    model = RealEmbeddingProvider()
    ingestion = IngestionService(
        store,
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

    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, model)
    cases: list[dict[str, Any]] = []
    rows_by_depth: dict[int, list[tuple[list[str], set[str]]]] = {depth: [] for depth in DEPTHS}
    oracle_rows: dict[int, list[tuple[list[str], set[str]]]] = {depth: [] for depth in (10, 20, 50)}

    for case in corpus.cases:
        expected = set(case.expected_sources)
        lexical_candidates = lexical.search(case.question, case.tenant_id, 50)
        semantic_candidates = semantic.search(case.question, case.tenant_id, 50)
        lexical_paths = [source(candidate) for candidate in lexical_candidates]
        semantic_paths = [source(candidate) for candidate in semantic_candidates]
        depth_rows: dict[str, Any] = {}
        for depth in DEPTHS:
            fusion = HybridRetriever(lexical, semantic, candidate_depth=depth, parallel=False)
            fused = fusion.fuse(lexical_candidates[:depth], semantic_candidates[:depth], depth)
            paths = [source(candidate) for candidate in fused]
            rows_by_depth[depth].append((paths, expected))
            if depth in oracle_rows:
                oracle_rows[depth].append((oracle_order(paths, expected), expected))
            relevant = [path for path in paths if path in expected]
            first = next((candidate for candidate in fused if source(candidate) in expected), None)
            depth_rows[str(depth)] = {
                "candidate_recall": len(set(paths) & expected) / max(len(expected), 1),
                "relevant_entered_pool": bool(relevant),
                "first_relevant_candidate_position": rank(paths, expected),
                "rrf_rank": rank(paths, expected),
                "relevant_sources_in_pool": sorted(set(relevant)),
                "first_relevant_metadata": first.metadata if first else None,
            }
        cases.append(
            {
                "case_id": case.id,
                "query": case.question,
                "category": str(case.metadata.get("category", case.task_type)),
                "relevant_source_ids": sorted(expected),
                "lexical_rank": rank(lexical_paths, expected),
                "semantic_rank": rank(semantic_paths, expected),
                "depths": depth_rows,
            }
        )

    candidate_summary = {
        str(depth): {
            "candidate_recall_at_n": metrics(rows)[f"recall_at_{depth}"]
            if depth in (5, 10)
            else sum(len(set(paths) & expected) / max(len(expected), 1) for paths, expected in rows)
            / len(rows),
            "cases_with_any_relevant": sum(bool(set(paths) & expected) for paths, expected in rows),
            "case_count": len(rows),
        }
        for depth, rows in rows_by_depth.items()
    }
    candidate_artifact = {
        "model_version": model.version,
        "corpus": str(args.corpus),
        "methodology": (
            "For each N, union lexical top-N and semantic top-N with deterministic RRF, "
            "then retain the first N candidates. Candidate recall is distinct from final Recall@K."
        ),
        "summary": candidate_summary,
        "cases": cases,
    }

    oracle_depths: dict[str, Any] = {}
    for depth, oracle in oracle_rows.items():
        baseline = rows_by_depth[depth]
        baseline_metrics = metrics(baseline)
        oracle_metrics = metrics(oracle)
        oracle_depths[str(depth)] = {
            "hybrid_rrf": baseline_metrics,
            "oracle": oracle_metrics,
            "delta": {
                key: oracle_metrics[key] - baseline_metrics[key]
                for key in ("mrr", "ndcg_at_5", "ndcg_at_10")
            },
            "top_1_failures_fixable": sum(
                rank(paths, expected) not in (None, 1) for paths, expected in baseline
            ),
            "top_5_failures_fixable": sum(
                rank(paths, expected) is not None and rank(paths, expected) > 5
                for paths, expected in baseline
            ),
            "candidate_missing": sum(rank(paths, expected) is None for paths, expected in baseline),
        }
    oracle_artifact = {
        "offline_evaluation_only": True,
        "invariant": "Oracle only reorders the existing fixed candidate set.",
        "note": (
            "Reranking cannot improve recall at candidate depth; it can only reorder present items."
        ),
        "depths": oracle_depths,
    }

    prior = json.loads(
        Path("evals/retrieval_semantic_model2vec_results.json").read_text(encoding="utf-8")
    )
    prior_overgeneralization = {
        failure["case_id"]: failure
        for failure in prior["failures"]
        if failure["failure_class"] == "semantic overgeneralization"
    }
    by_id = {row["case_id"]: row for row in cases}
    documents = {document.source_path: document.content for document in corpus.documents}
    overgeneralization_cases: list[dict[str, Any]] = []
    for case_id, failure in prior_overgeneralization.items():
        row = by_id[case_id]
        expected = row["relevant_source_ids"]
        top_wrong = next(
            (
                result["source"]
                for result in failure["hybrid_top_results"]
                if result["source"] not in expected
            ),
            None,
        )
        position_10 = row["depths"]["10"]["first_relevant_candidate_position"]
        position_20 = row["depths"]["20"]["first_relevant_candidate_position"]
        position_50 = row["depths"]["50"]["first_relevant_candidate_position"]
        classification = (
            "A"
            if position_10 is not None
            else "B"
            if position_20 is not None
            else "C"
            if position_50 is not None
            else "D"
        )
        query = row["query"]
        wrong_content = documents.get(str(top_wrong), "")
        overgeneralization_cases.append(
            {
                "case_id": case_id,
                "query": query,
                "expected_source": expected,
                "lexical_rank": row["lexical_rank"],
                "semantic_rank": row["semantic_rank"],
                "hybrid_rank": failure["hybrid_rank"],
                "candidate_set_position": {"10": position_10, "20": position_20, "50": position_50},
                "classification": classification,
                "top_competing_incorrect_source": top_wrong,
                "plausibility_evidence": {
                    "shared_query_tokens": token_evidence(query, wrong_content),
                    "competing_content_excerpt": wrong_content[:300],
                },
            }
        )
    overgeneralization_artifact = {
        "source_taxonomy_artifact": "evals/retrieval_semantic_model2vec_results.json",
        "total": len(overgeneralization_cases),
        "classification_counts": {
            letter: sum(case["classification"] == letter for case in overgeneralization_cases)
            for letter in "ABCDEF"
        },
        "candidate_present_at_50": sum(
            case["classification"] in "ABC" for case in overgeneralization_cases
        ),
        "candidate_missing_at_50": sum(
            case["classification"] == "D" for case in overgeneralization_cases
        ),
        "reranker_fixable": sum(
            case["classification"] in "ABC" and case["hybrid_rank"] != 1
            for case in overgeneralization_cases
        ),
        "cases": overgeneralization_cases,
    }

    for path, artifact in (
        (args.candidate_output, candidate_artifact),
        (args.oracle_output, oracle_artifact),
        (args.overgeneralization_output, overgeneralization_artifact),
    ):
        path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "candidate": candidate_summary,
                "oracle": oracle_depths,
                "overgeneralization": overgeneralization_artifact,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
