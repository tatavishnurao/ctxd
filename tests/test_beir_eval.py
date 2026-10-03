"""Metric, ranking and uncertainty helpers of the BEIR evaluation."""

import math

import pytest
from benchmarks.beir_eval import (
    boundary_tie,
    cluster_bootstrap,
    document_ranking,
    mrr_at_10,
    ndcg_at_10,
    query_clusters,
    recall_at_100,
)
from ctxd.app.models.domain import ContextCandidate, SourceType


def chunk(doc_id: str, score: float = 1.0) -> ContextCandidate:
    return ContextCandidate(
        source_id=f"{doc_id}-chunk",
        source_type=SourceType.DOCUMENT,
        content="x",
        token_cost=1,
        relevance_score=score,
        metadata={"source_path": f"beir/{doc_id}"},
    )


def test_document_rank_is_best_chunk_rank() -> None:
    assert document_ranking([chunk("a"), chunk("b"), chunk("a"), chunk("c")]) == ["a", "b", "c"]


def test_ndcg_uses_linear_graded_gain_and_ideal_ordering() -> None:
    relevant = {"a": 2, "b": 1}
    assert ndcg_at_10(["a", "b"], relevant) == pytest.approx(1.0)
    swapped = (1 + 2 / math.log2(3)) / (2 + 1 / math.log2(3))
    assert ndcg_at_10(["b", "a"], relevant) == pytest.approx(swapped)
    assert ndcg_at_10(["z"] * 10 + ["a"], relevant) == 0.0


def test_recall_and_mrr_cutoffs() -> None:
    relevant = {"a": 1, "b": 1}
    assert recall_at_100(["a", "x"], relevant) == 0.5
    assert mrr_at_10(["x", "x2", "b"], relevant) == pytest.approx(1 / 3)
    assert mrr_at_10([f"x{i}" for i in range(10)] + ["a"], relevant) == 0.0


def test_boundary_tie_detects_equal_scores_at_cutoff() -> None:
    tied = [chunk(str(i), 1.0 - i / 100) for i in range(9)] + [chunk("9", 0.5), chunk("10", 0.5)]
    assert boundary_tie(tied)
    assert not boundary_tie([chunk(str(i), 1.0 - i / 100) for i in range(11)])
    assert not boundary_tie([chunk("a")])


def test_queries_sharing_relevant_documents_form_one_cluster() -> None:
    qrels = {"q1": {"d1": 1}, "q2": {"d1": 1, "d2": 1}, "q3": {"d2": 1}, "q4": {"d9": 1}}
    assert query_clusters(qrels) == [["q1", "q2", "q3"], ["q4"]]


def test_cluster_bootstrap_is_deterministic_and_brackets_estimate() -> None:
    clusters = [[f"q{i}"] for i in range(40)]
    values = {f"q{i}": float(i % 2) for i in range(40)}
    first = cluster_bootstrap(clusters, values.__getitem__, resamples=500, seed=7)
    assert first == cluster_bootstrap(clusters, values.__getitem__, resamples=500, seed=7)
    assert first["estimate"] == 0.5
    assert first["ci95_low"] < 0.5 < first["ci95_high"]
