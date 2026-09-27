from __future__ import annotations

import math
from pathlib import Path

import pytest
from ctxd.app.models.domain import ContextCandidate, SourceType
from ctxd.app.reranking import FakeReranker, FlashRankReranker, RerankingRetriever
from ctxd.app.reranking.base import apply_scores


def candidate(name: str, score: float = 0.1) -> ContextCandidate:
    return ContextCandidate(
        source_id=name,
        source_type=SourceType.DOCUMENT,
        content=f"content {name}",
        token_cost=2,
        relevance_score=score,
        metadata={
            "tenant_marker": "preserved",
            "lexical_rank": 1,
            "semantic_rank": 2,
            "raw_lexical_score": 3.0,
            "raw_vector_score": 0.8,
            "fused_score": score,
        },
    )


class Upstream:
    def __init__(self, values: list[ContextCandidate]) -> None:
        self.values = values
        self.requested_top_k: int | None = None

    def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]:
        self.requested_top_k = top_k
        return self.values[:top_k]


class BrokenReranker:
    model_id = "broken"

    def rerank(
        self, query: str, candidates: list[ContextCandidate], top_k: int
    ) -> list[ContextCandidate]:
        raise RuntimeError("model unavailable")


class InvalidCountReranker:
    model_id = "invalid-count"

    def rerank(
        self, query: str, candidates: list[ContextCandidate], top_k: int
    ) -> list[ContextCandidate]:
        return []


class InvalidSetReranker:
    model_id = "invalid-set"

    def rerank(
        self, query: str, candidates: list[ContextCandidate], top_k: int
    ) -> list[ContextCandidate]:
        return [candidate("outside")]


def test_fake_reranker_preserves_identity_provenance_and_stable_ties() -> None:
    values = [candidate("a"), candidate("b"), candidate("c")]
    reranker = FakeReranker(lambda _query, item: 2.0 if item.source_id == "c" else 1.0)
    result = reranker.rerank("query", values, 3)
    assert [item.source_id for item in result] == ["c", "a", "b"]
    assert result[1].metadata["tenant_marker"] == "preserved"
    assert result[1].metadata["raw_lexical_score"] == 3.0
    assert result[1].metadata["raw_vector_score"] == 0.8
    assert result[1].metadata["fused_score"] == 0.1
    assert result[1].metadata["pre_rerank_rank"] == 1
    assert result[1].metadata["reranked_rank"] == 2
    assert result[1].metadata["reranker_model"] == FakeReranker.model_id


def test_fake_reranker_top_k_and_empty_candidates() -> None:
    reranker = FakeReranker()
    assert reranker.rerank("query", [], 2) == []
    assert len(reranker.rerank("query", [candidate("a"), candidate("b")], 1)) == 1
    with pytest.raises(ValueError, match="top_k"):
        reranker.rerank("query", [candidate("a")], 0)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_invalid_scores_fall_back_to_rrf(value: float) -> None:
    values = [candidate("a"), candidate("b")]
    retriever = RerankingRetriever(
        Upstream(values), FakeReranker(lambda _query, _candidate: value), candidate_count=2
    )
    assert retriever.search("query", "tenant-a", 2) == values


def test_invalid_score_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="score count"):
        apply_scores([candidate("a")], [], top_k=1, model_id="broken")


def test_model_exception_falls_back_to_rrf() -> None:
    values = [candidate("a"), candidate("b")]
    assert (
        RerankingRetriever(Upstream(values), BrokenReranker()).search("query", "tenant-a", 2)
        == values
    )


def test_candidate_count_mismatch_falls_back() -> None:
    values = [candidate("a"), candidate("b")]
    result = RerankingRetriever(Upstream(values), InvalidCountReranker()).search(
        "query", "tenant-a", 2
    )
    assert result == values


def test_candidate_set_change_falls_back_and_upstream_is_fixed_depth() -> None:
    values = [candidate("a"), candidate("b")]
    upstream = Upstream(values)
    result = RerankingRetriever(upstream, InvalidSetReranker(), candidate_count=20).search(
        "query", "tenant-a", 1
    )
    assert result == values[:1]
    assert upstream.requested_top_k == 20


def test_empty_upstream_does_not_call_reranker() -> None:
    assert RerankingRetriever(Upstream([]), BrokenReranker()).search("query", "tenant-a", 5) == []


def test_offline_model_unavailable_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="offline cache"):
        FlashRankReranker(cache_dir=tmp_path, offline=True)
