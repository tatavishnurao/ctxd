from pathlib import Path

import pytest
from ctxd.app.evals.retrieval import (
    load_corpus,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
    run_retrieval_eval,
)


def test_recall_at_k() -> None:
    assert recall_at_k(["a", "x", "b"], {"a", "b"}, 2) == 0.5
    assert recall_at_k(["a", "b"], {"a", "b"}, 2) == 1.0


def test_reciprocal_rank() -> None:
    assert reciprocal_rank(["x", "relevant"], {"relevant"}) == 0.5
    assert reciprocal_rank(["x"], {"relevant"}) == 0.0


def test_ndcg_at_k_binary_relevance() -> None:
    assert ndcg_at_k(["a", "b"], {"a", "b"}, 2) == 1.0
    assert ndcg_at_k(["x", "a"], {"a"}, 2) == pytest.approx(1 / 1.584962500721156)


def test_retrieval_eval_corpus_is_deterministic_and_machine_readable() -> None:
    corpus = load_corpus(Path("evals/retrieval_corpus.json"))
    first = run_retrieval_eval(corpus)
    second = run_retrieval_eval(corpus)
    assert first == second
    assert first.case_count >= 20
    assert first.recall_at_k == pytest.approx(0.9545454545454546)
    assert first.mrr == pytest.approx(0.9545454545454546)
    assert first.ndcg_at_k == pytest.approx(0.9545454545454546)
    assert set(first.per_case) == {case.id for case in corpus.cases}


def test_expanded_retrieval_corpus_exposes_morphology_limitations() -> None:
    corpus = load_corpus(Path("evals/retrieval_expanded.json"))
    result = run_retrieval_eval(corpus)
    assert result.case_count == 100
    assert result.recall_at_k == pytest.approx(0.8)
    assert result.mrr == pytest.approx(0.8)
    assert result.ndcg_at_k == pytest.approx(0.8)
    morphology = [
        metrics
        for case_id, metrics in result.per_case.items()
        if case_id.startswith("morphology-")
    ]
    assert len(morphology) == 20
    assert all(metrics["recall_at_k"] == 0.0 for metrics in morphology)
