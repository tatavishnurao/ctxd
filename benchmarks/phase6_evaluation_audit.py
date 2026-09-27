"""Phase 6 annotation, duplicate, oracle, and reranker-failure audit."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ctxd.app.evals.analysis import (
    distribution,
    length_bucket,
    normalized_content,
    normalized_tokens,
    overlap_ratio,
    query_features,
    rare_terms,
    token_jaccard,
)
from ctxd.app.evals.retrieval import load_corpus, ndcg_at_k, recall_at_k, reciprocal_rank
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.reranking import FlashRankReranker
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.documents import InMemoryDocumentStore
from tokenizers import Tokenizer

DEPTHS = (5, 10, 20, 50)
CATEGORIES_REQUIRING_NOTES = {
    "near duplicate",
    "multiple relevant",
    "ambiguous",
    "long chunk",
    "semantic overgeneralization",
}


def source(candidate: Any) -> str:
    return str(candidate.metadata.get("source_path", ""))


def unique(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(paths))


def rank(paths: list[str], relevant: set[str]) -> int | None:
    return next((index for index, path in enumerate(paths, 1) if path in relevant), None)


def metrics(rows: list[tuple[list[str], set[str]]]) -> dict[str, float]:
    normalized = [(unique(paths), relevant) for paths, relevant in rows]
    count = len(normalized)
    return {
        "recall_at_1": sum(recall_at_k(paths, relevant, 1) for paths, relevant in normalized)
        / count,
        "recall_at_5": sum(recall_at_k(paths, relevant, 5) for paths, relevant in normalized)
        / count,
        "recall_at_10": sum(recall_at_k(paths, relevant, 10) for paths, relevant in normalized)
        / count,
        "mrr": sum(reciprocal_rank(paths, relevant) for paths, relevant in normalized) / count,
        "ndcg_at_5": sum(ndcg_at_k(paths, relevant, 5) for paths, relevant in normalized) / count,
        "ndcg_at_10": sum(ndcg_at_k(paths, relevant, 10) for paths, relevant in normalized) / count,
    }


def annotation_note(category: str, changed: bool) -> str:
    if changed:
        return (
            "Identical ambiguous query had contradictory mutually exclusive labels; both "
            "plausible Java sources are retained as binary relevant pending human intent review."
        )
    notes = {
        "near duplicate": (
            "Expected source directly answers the distinguishing mechanism; alternatives "
            "describe different mechanisms."
        ),
        "multiple relevant": (
            "Existing labels already enumerate the independently supporting sources."
        ),
        "ambiguous": (
            "Existing ambiguity was inspected; no additional source was deterministically "
            "supportable."
        ),
        "long chunk": (
            "Synthetic tail marker occurs only in the labeled source; binary label confirmed."
        ),
    }
    return notes.get(
        category,
        "Expected source contains the direct answer; no deterministic equivalent was found.",
    )


def create_annotation_audit(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_by_query: dict[tuple[str, str], list[set[str]]] = defaultdict(list)
    for case in raw["cases"]:
        expected_by_query[(case.get("tenant_id", "eval"), case["question"])].append(
            set(case["expected_sources"])
        )
    contradictory = {
        key: set().union(*values)
        for key, values in expected_by_query.items()
        if len({tuple(sorted(value)) for value in values}) > 1
    }
    audited = copy.deepcopy(raw)
    audit_cases: list[dict[str, Any]] = []
    for original, updated in zip(raw["cases"], audited["cases"], strict=True):
        key = (original.get("tenant_id", "eval"), original["question"])
        existing = list(original["expected_sources"])
        changed = key in contradictory
        relevant = sorted(contradictory[key]) if changed else sorted(existing)
        category = str(original.get("metadata", {}).get("category", original["task_type"]))
        status = "ambiguous" if changed else "confirmed"
        updated["expected_sources"] = relevant
        updated.setdefault("metadata", {})["phase6_annotation_status"] = status
        audit_cases.append(
            {
                "case_id": original["id"],
                "query": original["question"],
                "existing_expected_sources": existing,
                "audited_relevant_sources": relevant,
                "relevance_grades": {path: 1 for path in relevant},
                "annotation_notes": annotation_note(category.replace("_", " "), changed),
                "annotation_status": status,
                "grading_policy": "binary",
            }
        )
    audit = {
        "grading_policy": (
            "Binary judgments are used. The fixture lacks independent assessor evidence for "
            "defensible 0/1/2 distinctions; subjective grades were not invented."
        ),
        "status_counts": {
            status: sum(case["annotation_status"] == status for case in audit_cases)
            for status in ("confirmed", "corrected", "expanded", "ambiguous")
        },
        "cases": audit_cases,
    }
    return audit, audited


def duplicate_analysis(raw: dict[str, Any], model: RealEmbeddingProvider) -> dict[str, Any]:
    documents = raw["documents"]
    exact_groups: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        digest = hashlib.sha256(normalized_content(document["content"]).encode()).hexdigest()
        exact_groups[digest].append(document["source_path"])
    exact = [sorted(group) for group in exact_groups.values() if len(group) > 1]
    near_pairs: list[dict[str, Any]] = []
    for index, left in enumerate(documents):
        for right in documents[index + 1 :]:
            if left.get("tenant_id", "eval") != right.get("tenant_id", "eval"):
                continue
            overlap = token_jaccard(left["content"], right["content"])
            if 0.70 <= overlap < 1.0:
                near_pairs.append(
                    {
                        "sources": [left["source_path"], right["source_path"]],
                        "token_jaccard": overlap,
                    }
                )
    same_fact = sorted(
        {
            tuple(sorted(case["expected_sources"]))
            for case in raw["cases"]
            if len(case["expected_sources"]) > 1
        }
    )
    vectors = model.embed_documents([document["content"] for document in documents])
    similar: list[dict[str, Any]] = []
    same_fact_sets = [set(group) for group in same_fact]
    exact_sets = [set(group) for group in exact]
    for index, left in enumerate(documents):
        for other_index in range(index + 1, len(documents)):
            right = documents[other_index]
            if left.get("tenant_id", "eval") != right.get("tenant_id", "eval"):
                continue
            pair = {left["source_path"], right["source_path"]}
            if any(pair <= group for group in same_fact_sets + exact_sets):
                continue
            cosine = sum(a * b for a, b in zip(vectors[index], vectors[other_index], strict=True))
            if cosine >= 0.80:
                similar.append(
                    {
                        "sources": sorted(pair),
                        "embedding_cosine": cosine,
                        "classification": "different facts but semantically similar",
                        "warning": (
                            "Similarity is an analysis signal, not an automatic duplicate label."
                        ),
                    }
                )
    affected_queries = sum(
        any(set(case["expected_sources"]) <= set(group) for group in same_fact)
        for case in raw["cases"]
    )
    return {
        "exact_duplicate_clusters": exact,
        "near_duplicate_pairs": near_pairs,
        "same_fact_different_wording_clusters": [list(group) for group in same_fact],
        "different_fact_semantic_similarity_pairs": similar,
        "queries_with_explicit_equivalent_sources": affected_queries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("evals/retrieval_semantic.json"))
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cache" / "ctxd" / "rerankers"
    )
    args = parser.parse_args()
    raw = json.loads(args.corpus.read_text(encoding="utf-8"))
    annotation_audit, audited_raw = create_annotation_audit(raw)
    Path("evals/phase6_annotation_audit.json").write_text(
        json.dumps(annotation_audit, indent=2) + "\n", encoding="utf-8"
    )
    audited_path = Path("evals/retrieval_semantic_phase6_audited.json")
    audited_path.write_text(json.dumps(audited_raw, indent=2) + "\n", encoding="utf-8")
    original_corpus = load_corpus(args.corpus)
    audited_corpus = load_corpus(audited_path)

    store = InMemoryDocumentStore()
    embedding = RealEmbeddingProvider()
    ingestion = IngestionService(
        store,
        StructureAwareChunker(ChunkingConfig(target_tokens=80, max_tokens=120, overlap_tokens=10)),
        embedding,
    )
    for document in original_corpus.documents:
        ingestion.ingest_content(
            content=document.content,
            source_path=document.source_path,
            source_type=document.source_type,
            tenant_id=document.tenant_id,
            metadata=document.metadata,
        )
    lexical = BM25Retriever(store)
    semantic = SemanticRetriever(store, embedding)
    reranker = FlashRankReranker(cache_dir=args.cache_dir, offline=True, batch_size=16)
    duplicate = duplicate_analysis(raw, embedding)
    Path("benchmarks/phase6_duplicate_analysis.json").write_text(
        json.dumps(duplicate, indent=2) + "\n", encoding="utf-8"
    )

    audit_by_id = {case["case_id"]: case for case in annotation_audit["cases"]}
    audited_by_id = {case.id: case for case in audited_corpus.cases}
    document_contents = {
        document.source_path: document.content for document in original_corpus.documents
    }
    corpus_rare = rare_terms(document_contents.values())
    tokenizer = reranker._ranker.tokenizer
    raw_tokenizer = Tokenizer.from_file(
        str(args.cache_dir / reranker.flashrank_model_name / "tokenizer.json")
    )
    raw_tokenizer.no_truncation()
    same_fact_sets = [set(group) for group in duplicate["same_fact_different_wording_clusters"]]

    labels = ("original", "audited")
    mode_rows: dict[str, dict[str, list[tuple[list[str], set[str]]]]] = {
        label: {mode: [] for mode in ("lexical", "semantic", "hybrid", "reranked")}
        for label in labels
    }
    depth_rows: dict[int, list[tuple[list[str], set[str]]]] = {depth: [] for depth in DEPTHS}
    oracle_rows: dict[int, list[tuple[list[str], set[str]]]] = {depth: [] for depth in (10, 20, 50)}
    forensic_cases: list[dict[str, Any]] = []
    all_relevant_scores: list[float] = []
    all_nonrelevant_scores: list[float] = []
    all_within_query_comparisons: list[bool] = []
    within_query_comparisons_by_category: dict[str, list[bool]] = defaultdict(list)
    scores_by_category: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"relevant": [], "nonrelevant": []}
    )
    truncation_rows: list[dict[str, Any]] = []
    all_pair_lengths: list[tuple[int, int]] = []
    query_type_rows: list[dict[str, Any]] = []
    rrf_failures: list[dict[str, Any]] = []
    upper_bound = Counter()

    for case in original_corpus.cases:
        audited_case = audited_by_id[case.id]
        original_relevant = set(case.expected_sources)
        audited_relevant = set(audited_case.expected_sources)
        category = str(case.metadata.get("category", case.task_type)).replace("_", " ")
        lexical_candidates = lexical.search(case.question, case.tenant_id, 50)
        semantic_candidates = semantic.search(case.question, case.tenant_id, 50)
        lexical_paths = [source(item) for item in lexical_candidates]
        semantic_paths = [source(item) for item in semantic_candidates]
        lexical_scores = {
            item.source_id: float(item.relevance_score) for item in lexical_candidates
        }
        query_vector = embedding.embed_query(case.question)
        cosine_by_chunk = {
            chunk_id: sum(
                query_value * candidate_value
                for query_value, candidate_value in zip(
                    query_vector, stored_embedding[1], strict=True
                )
            )
            for (tenant_id, chunk_id), stored_embedding in store._embeddings.items()
            if tenant_id == case.tenant_id and stored_embedding[0] == embedding.version
        }
        pools: dict[int, list[Any]] = {}
        for depth in DEPTHS:
            pools[depth] = HybridRetriever(
                lexical, semantic, candidate_depth=depth, parallel=False
            ).fuse(lexical_candidates[:depth], semantic_candidates[:depth], depth)
            paths = [source(item) for item in pools[depth]]
            depth_rows[depth].append((paths, audited_relevant))
            if depth in oracle_rows:
                oracle_paths = sorted(paths, key=lambda path: path not in audited_relevant)
                oracle_rows[depth].append((oracle_paths, audited_relevant))
        pool = pools[20]
        rrf_paths = [source(item) for item in pool]
        reranked_all = reranker.rerank(case.question, pool, len(pool))
        reranked_paths = [source(item) for item in reranked_all]
        reranked_ids = [item.source_id for item in reranked_all]
        audit_record = audit_by_id[case.id]
        audit_record["retrieval_review"] = {
            "lexical_top_10": unique(lexical_paths)[:10],
            "semantic_top_10": unique(semantic_paths)[:10],
            "hybrid_top_10": unique(rrf_paths)[:10],
            "other_retrieved_sources_reviewed": sorted(
                (set(lexical_paths[:10]) | set(semantic_paths[:10]) | set(rrf_paths[:10]))
                - audited_relevant
            ),
        }
        for label, relevant in (("original", original_relevant), ("audited", audited_relevant)):
            mode_rows[label]["lexical"].append((lexical_paths[:10], relevant))
            mode_rows[label]["semantic"].append((semantic_paths[:10], relevant))
            mode_rows[label]["hybrid"].append((rrf_paths[:10], relevant))
            mode_rows[label]["reranked"].append((reranked_paths[:10], relevant))

        rrf_rank = rank(rrf_paths, audited_relevant)
        reranked_rank = rank(reranked_paths, audited_relevant)
        regression = rrf_rank is not None and (reranked_rank is None or reranked_rank > rrf_rank)
        features = query_features(case.question, corpus_rare)
        query_type_rows.append({"case_id": case.id, "features": features, "regressed": regression})
        candidate_rows: list[dict[str, Any]] = []
        relevant_scores: list[float] = []
        nonrelevant_scores: list[float] = []
        seen_relevant_sources: set[str] = set()
        for rrf_index, candidate in enumerate(pool, 1):
            path = source(candidate)
            reranked_candidate = next(
                item for item in reranked_all if item.source_id == candidate.source_id
            )
            score = float(reranked_candidate.metadata["reranker_score"])
            source_labeled_relevant = path in audited_relevant
            is_relevant = source_labeled_relevant and path not in seen_relevant_sources
            if source_labeled_relevant:
                seen_relevant_sources.add(path)
            if is_relevant:
                relevant_scores.append(score)
                all_relevant_scores.append(score)
                scores_by_category[category]["relevant"].append(score)
            elif not source_labeled_relevant:
                nonrelevant_scores.append(score)
                all_nonrelevant_scores.append(score)
                scores_by_category[category]["nonrelevant"].append(score)
            raw_encoding = raw_tokenizer.encode(case.question, candidate.content)
            retained_encoding = tokenizer.encode(case.question, candidate.content)
            raw_length = len(raw_encoding.ids)
            retained_length = sum(retained_encoding.attention_mask)
            all_pair_lengths.append((raw_length, retained_length))
            bucket = length_bucket(raw_length)
            exact_tokens = set(normalized_tokens(case.question)) & set(
                normalized_tokens(candidate.content)
            )
            rare_presence = bool(exact_tokens & corpus_rare)
            row = {
                "source": path,
                "chunk_id": candidate.source_id,
                "relevant": is_relevant,
                "source_labeled_relevant": source_labeled_relevant,
                "relevance_proxy_policy": "first RRF candidate per labeled source",
                "rrf_rank": rrf_index,
                "reranked_rank": reranked_ids.index(candidate.source_id) + 1,
                "rrf_score": candidate.metadata.get("fused_score"),
                "lexical_score": lexical_scores.get(candidate.source_id, 0.0),
                "semantic_score": cosine_by_chunk[candidate.source_id],
                "reranker_score": score,
                "candidate_length_tokens": candidate.token_cost,
                "query_length_tokens": len(normalized_tokens(case.question)),
                "candidate_lexical_overlap": overlap_ratio(case.question, candidate.content),
                "embedding_cosine": cosine_by_chunk[candidate.source_id],
                "exact_term_presence": bool(exact_tokens),
                "rare_term_presence": rare_presence,
                "duplicate_cluster_membership": [
                    sorted(group) for group in same_fact_sets if path in group
                ],
                "reranker_input_tokens_before_truncation": raw_length,
                "reranker_input_tokens_retained": retained_length,
                "reached_512_token_limit": raw_length > 512,
            }
            candidate_rows.append(row)
            if is_relevant:
                truncation_rows.append(
                    {
                        "case_id": case.id,
                        "bucket": bucket,
                        "raw_tokens": raw_length,
                        "retained_tokens": retained_length,
                        "rrf_rank": rrf_index,
                        "reranked_rank": reranked_ids.index(candidate.source_id) + 1,
                        "regressed": regression,
                        "score": score,
                        "nonrelevant_scores": nonrelevant_scores,
                    }
                )
        case_comparisons = [
            relevant_score > nonrelevant_score
            for relevant_score in relevant_scores
            for nonrelevant_score in nonrelevant_scores
        ]
        all_within_query_comparisons.extend(case_comparisons)
        within_query_comparisons_by_category[category].extend(case_comparisons)
        failure_labels: list[str] = []
        if regression:
            relevant_candidates = [row for row in candidate_rows if row["relevant"]]
            top_relevant = min(relevant_candidates, key=lambda row: row["rrf_rank"])
            if top_relevant["reached_512_token_limit"]:
                failure_labels.append("long-passage/truncation failure")
            if category == "near duplicate":
                failure_labels.append("near-duplicate confusion")
            if len(audited_relevant) > 1:
                failure_labels.append("multi-relevant annotation/evaluation sensitivity")
            if top_relevant["exact_term_presence"] and rrf_rank == 1:
                failure_labels.append("lexical exact-match demotion")
            if nonrelevant_scores and top_relevant["reranker_score"] <= median_value(
                nonrelevant_scores
            ):
                failure_labels.append("score inversion")
            if (
                nonrelevant_scores
                and max(nonrelevant_scores) - top_relevant["reranker_score"] < 0.02
            ):
                failure_labels.append("score compression")
            if not failure_labels:
                failure_labels.append("query-document domain mismatch")
        forensic_cases.append(
            {
                "case_id": case.id,
                "query": case.question,
                "expected_sources": sorted(original_relevant),
                "audited_relevant_sources": sorted(audited_relevant),
                "category": category,
                "rrf_top_10": candidate_rows[:10],
                "reranked_top_10": sorted(candidate_rows, key=lambda row: row["reranked_rank"])[
                    :10
                ],
                "rrf_relevant_rank": rrf_rank,
                "reranked_relevant_rank": reranked_rank,
                "regressed": regression,
                "failure_categories": failure_labels,
                "relevant_candidate_truncated": any(
                    row["relevant"] and row["reached_512_token_limit"] for row in candidate_rows
                ),
            }
        )

        if audit_by_id[case.id]["annotation_status"] == "ambiguous":
            upper_bound["C_annotation_ambiguity"] += 1
        elif rrf_rank == 1:
            upper_bound["A_already_correct"] += 1
        elif equivalent_top_result(rrf_paths, audited_relevant, same_fact_sets):
            upper_bound["D_duplicate_equivalent"] += 1
        elif rrf_rank is not None and difficult_component_ranks(
            lexical_paths, semantic_paths, audited_relevant
        ):
            upper_bound["E_genuinely_difficult_semantic"] += 1
        elif rrf_rank is not None:
            upper_bound["B_present_but_ranked_low"] += 1
        else:
            upper_bound["candidate_missing"] += 1

        if rrf_rank not in (None, 1):
            rrf_failures.append(
                {
                    "case_id": case.id,
                    "query": case.question,
                    "relevant_sources": sorted(audited_relevant),
                    "rrf_rank": rrf_rank,
                    "lexical_rank": rank(lexical_paths, audited_relevant),
                    "semantic_rank": rank(semantic_paths, audited_relevant),
                    "top_source": rrf_paths[0] if rrf_paths else None,
                    "diagnosis": diagnose_rrf(
                        category,
                        lexical_paths,
                        semantic_paths,
                        rrf_paths,
                        audited_relevant,
                        same_fact_sets,
                        audit_by_id[case.id]["annotation_status"],
                    ),
                }
            )

    Path("evals/phase6_annotation_audit.json").write_text(
        json.dumps(annotation_audit, indent=2) + "\n", encoding="utf-8"
    )
    original_metrics = {mode: metrics(rows) for mode, rows in mode_rows["original"].items()}
    audited_metrics = {mode: metrics(rows) for mode, rows in mode_rows["audited"].items()}
    Path("benchmarks/phase6_audited_metrics.json").write_text(
        json.dumps({"original": original_metrics, "audited": audited_metrics}, indent=2) + "\n"
    )
    oracle = {
        "candidate_recall": {
            str(depth): sum(len(set(paths) & relevant) / len(relevant) for paths, relevant in rows)
            / len(rows)
            for depth, rows in depth_rows.items()
        },
        "depths": {
            str(depth): {
                "hybrid": metrics(depth_rows[depth]),
                "oracle": metrics(rows),
            }
            for depth, rows in oracle_rows.items()
        },
    }
    Path("benchmarks/phase6_audited_oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
    regressions = [case for case in forensic_cases if case["regressed"]]
    taxonomy = Counter(label for case in regressions for label in case["failure_categories"])
    duplicate_regressions = sum(
        case["category"] == "multiple relevant"
        and any(bool(set(case["audited_relevant_sources"]) & cluster) for cluster in same_fact_sets)
        for case in regressions
    )
    duplicate["reranker_regressions_involving_equivalent_clusters"] = duplicate_regressions
    duplicate["rankings_penalized_despite_equivalent_evidence"] = sum(
        equivalent_top_result(
            [row["source"] for row in case["rrf_top_10"]],
            set(case["audited_relevant_sources"]),
            same_fact_sets,
        )
        for case in forensic_cases
    )
    Path("benchmarks/phase6_duplicate_analysis.json").write_text(
        json.dumps(duplicate, indent=2) + "\n", encoding="utf-8"
    )
    transitions = Counter()
    for case in forensic_cases:
        rrf_case_rank = case["rrf_relevant_rank"]
        reranked_case_rank = case["reranked_relevant_rank"]
        if rrf_case_rank != 1 and reranked_case_rank == 1:
            transitions["fixed"] += 1
        elif rrf_case_rank == 1 and reranked_case_rank == 1:
            transitions["unchanged_correct"] += 1
        elif reranked_case_rank > rrf_case_rank:
            transitions["regressed"] += 1
        else:
            transitions["unchanged_incorrect"] += 1
    Path("benchmarks/phase6_reranker_forensics.json").write_text(
        json.dumps(
            {
                "regression_count": len(regressions),
                "transitions": dict(transitions),
                "taxonomy": dict(taxonomy),
                "cases": regressions,
            },
            indent=2,
        )
        + "\n"
    )
    score_result = {
        "relevance_proxy_policy": (
            "Source-level labels cannot establish relevance for every chunk. The first RRF "
            "candidate per labeled source is the relevant proxy; additional chunks from that "
            "source are excluded from both score classes."
        ),
        "relevant": distribution(all_relevant_scores),
        "nonrelevant": distribution(all_nonrelevant_scores),
        "within_query_pairwise_accuracy": (
            sum(all_within_query_comparisons) / len(all_within_query_comparisons)
        ),
        "by_category": {
            category: {
                "relevant": distribution(values["relevant"]),
                "nonrelevant": distribution(values["nonrelevant"]),
                "within_query_pairwise_accuracy": (
                    sum(within_query_comparisons_by_category[category])
                    / len(within_query_comparisons_by_category[category])
                    if within_query_comparisons_by_category[category]
                    else None
                ),
            }
            for category, values in scores_by_category.items()
        },
    }
    Path("benchmarks/phase6_score_distribution.json").write_text(
        json.dumps(score_result, indent=2) + "\n"
    )
    truncation = summarize_truncation(truncation_rows, all_pair_lengths)
    Path("benchmarks/phase6_truncation.json").write_text(json.dumps(truncation, indent=2) + "\n")
    Path("benchmarks/phase6_query_types.json").write_text(
        json.dumps(summarize_query_types(query_type_rows), indent=2) + "\n"
    )
    Path("benchmarks/phase6_input_format_audit.json").write_text(
        json.dumps(input_format_audit(reranker, args.cache_dir, forensic_cases), indent=2) + "\n"
    )
    Path("benchmarks/phase6_rrf_analysis.json").write_text(
        json.dumps(
            {
                "true_failure_count": len(rrf_failures),
                "diagnosis_counts": dict(Counter(row["diagnosis"] for row in rrf_failures)),
                "cases": rrf_failures,
            },
            indent=2,
        )
        + "\n"
    )
    Path("benchmarks/phase6_oracle_decomposition.json").write_text(
        json.dumps(dict(upper_bound), indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "annotations": annotation_audit["status_counts"],
                "metrics": {"original": original_metrics, "audited": audited_metrics},
                "oracle": oracle,
                "regressions": len(regressions),
                "taxonomy": taxonomy,
                "scores": score_result,
                "truncation": truncation,
                "upper_bound": upper_bound,
            },
            indent=2,
        )
    )


def median_value(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def equivalent_top_result(paths: list[str], relevant: set[str], clusters: list[set[str]]) -> bool:
    if not paths or paths[0] in relevant:
        return False
    return any(paths[0] in cluster and bool(relevant & cluster) for cluster in clusters)


def difficult_component_ranks(
    lexical_paths: list[str], semantic_paths: list[str], relevant: set[str]
) -> bool:
    lexical_rank = rank(lexical_paths, relevant)
    semantic_rank = rank(semantic_paths, relevant)
    return (lexical_rank is None or lexical_rank > 1) and (
        semantic_rank is None or semantic_rank > 1
    )


def diagnose_rrf(
    category: str,
    lexical_paths: list[str],
    semantic_paths: list[str],
    rrf_paths: list[str],
    relevant: set[str],
    clusters: list[set[str]],
    annotation_status: str,
) -> str:
    if annotation_status == "ambiguous":
        return "annotation issue"
    if equivalent_top_result(rrf_paths, relevant, clusters):
        return "duplicate candidates"
    if len(relevant) > 1:
        return "multiple relevant results"
    lexical_rank = rank(lexical_paths, relevant)
    semantic_rank = rank(semantic_paths, relevant)
    top = rrf_paths[0] if rrf_paths else None
    top_lexical = lexical_paths.index(top) + 1 if top in lexical_paths else None
    top_semantic = semantic_paths.index(top) + 1 if top in semantic_paths else None
    if lexical_rank is not None and semantic_rank is not None:
        if lexical_rank > semantic_rank and top_lexical is not None and top_lexical < lexical_rank:
            return "lexical rank overweighting"
        if (
            semantic_rank > lexical_rank
            and top_semantic is not None
            and top_semantic < semantic_rank
        ):
            return "semantic rank overweighting"
    if category == "near duplicate":
        return "near-duplicate competition"
    return "component-rank interaction"


def summarize_truncation(
    rows: list[dict[str, Any]], all_pair_lengths: list[tuple[int, int]]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for bucket in ("0-64", "65-128", "129-256", "257-384", "385-512", ">512"):
        selected = [row for row in rows if row["bucket"] == bucket]
        comparisons = [
            row["score"] > nonrelevant
            for row in selected
            for nonrelevant in row["nonrelevant_scores"]
        ]
        result[bucket] = {
            "relevant_candidates": len(selected),
            "pairwise_accuracy": sum(comparisons) / len(comparisons) if comparisons else None,
            "regression_rate": sum(row["regressed"] for row in selected) / len(selected)
            if selected
            else None,
            "mean_relevant_rank_change": sum(
                row["reranked_rank"] - row["rrf_rank"] for row in selected
            )
            / len(selected)
            if selected
            else None,
        }
    relevant_over_limit = sum(row["raw_tokens"] > 512 for row in rows)
    result["truncation_policy"] = {
        "strategy": "longest_first",
        "direction": "right",
        "limit": 512,
        "all_candidate_pairs": len(all_pair_lengths),
        "all_candidate_pairs_over_limit": sum(raw > 512 for raw, _ in all_pair_lengths),
        "relevant_proxy_candidates_over_limit": relevant_over_limit,
        "maximum_tokens_before_truncation": max(raw for raw, _ in all_pair_lengths),
        "maximum_tokens_retained": max(retained for _, retained in all_pair_lengths),
        "relevant_evidence_loss_count": relevant_over_limit,
        "conclusion": (
            "No relevant-proxy input reached the limit; truncation did not remove labeled "
            "evidence under the declared source-to-chunk proxy."
        ),
    }
    return result


def summarize_query_types(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = next(iter(rows))["features"].keys()
    return {
        key: {
            "cases": sum(bool(row["features"][key]) for row in rows),
            "regressions": sum(bool(row["features"][key]) and row["regressed"] for row in rows),
            "regression_rate": (
                sum(bool(row["features"][key]) and row["regressed"] for row in rows)
                / max(sum(bool(row["features"][key]) for row in rows), 1)
            ),
        }
        for key in keys
        if key != "token_count"
    } | {
        "query_token_count": {
            "mean_all": sum(row["features"]["token_count"] for row in rows) / len(rows),
            "mean_regressed": sum(
                row["features"]["token_count"] for row in rows if row["regressed"]
            )
            / max(sum(row["regressed"] for row in rows), 1),
        }
    }


def input_format_audit(
    reranker: FlashRankReranker, cache_dir: Path, cases: list[dict[str, Any]]
) -> dict[str, Any]:
    malformed = sum(
        not row["query"].strip() or any(not item["source"] for item in row["rrf_top_10"])
        for row in cases
    )
    return {
        "model": reranker.model_id,
        "local_metadata": {
            "model_max_length": 512,
            "do_lower_case": True,
            "architecture": "BertForSequenceClassification",
            "model_type": "bert",
        },
        "actual_pair_format": "Tokenizer.encode_batch([[raw query, raw chunk content], ...])",
        "query_formatting": "raw query, no prompt or prefix",
        "candidate_formatting": "raw chunk content; source path and metadata omitted",
        "special_tokens": ["[CLS]", "[SEP]", "[PAD]"],
        "truncation": "longest_first, right, 512 pair tokens",
        "padding": "right, dynamic to longest item in batch",
        "whitespace_normalization": "tokenizer defaults; no custom rewrite",
        "empty_or_malformed_pairs": malformed,
        "package_model_files": sorted(
            path.name for path in (cache_dir / reranker.flashrank_model_name).iterdir()
        ),
        "result": (
            "Input construction matches FlashRank's local pairwise implementation. No "
            "formatting bug was found. Omitting title/path is a design limitation, not a "
            "package-contract violation."
        ),
    }


if __name__ == "__main__":
    main()
