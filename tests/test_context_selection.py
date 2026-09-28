import pytest
from ctxd.app.evals.context_selection import (
    SelectionCandidate,
    budget_metrics,
    pack,
    should_rerank,
    source_metrics,
)
from ctxd.app.evals.retrieval import ndcg_at_k


def candidates() -> list[SelectionCandidate]:
    return [
        SelectionCandidate("1", "a", "first evidence", 10, 1, 1),
        SelectionCandidate("2", "a", "different evidence", 5, 2, 2),
        SelectionCandidate("3", "b", "third evidence", 5, 3, 3),
    ]


def test_chunk_position_metrics_do_not_reward_duplicates() -> None:
    metrics = source_metrics(["a", "a", "b"], {"a"})
    assert metrics["ndcg_at_5"] == 1
    assert ndcg_at_k(["a", "a"], {"a"}, 5) == 1
    assert (
        ndcg_at_k(["a", "a", "b"], {"a", "b"}, 5)
        == source_metrics(["a", "a", "b"], {"a", "b"})["ndcg_at_5"]
    )
    assert source_metrics(["x", "x", "a"], {"a"})["mrr"] == 1 / 3
    assert source_metrics(["x"] * 5 + ["a"], {"a"})["recall_at_5"] == 0
    assert source_metrics(["a", "a", "b"], {"a", "b"})["ndcg_at_5"] < 1


@pytest.mark.parametrize("policy", ["greedy", "density", "unique_source", "exact_duplicate"])
@pytest.mark.parametrize("budget", [0, 5, 10, 15, 20, 4096])
def test_packing_is_deterministic_bounded_and_identity_preserving(policy: str, budget: int) -> None:
    original = candidates()
    result = pack(original, budget, policy)  # type: ignore[arg-type]
    assert sum(c.tokens for c in result) <= budget
    assert result == pack(original, budget, policy)  # type: ignore[arg-type]
    assert len({c.identity for c in result}) == len(result)
    assert all(c in original for c in result)
    assert original == candidates()
    assert [original.index(c) for c in result] == sorted(original.index(c) for c in result)


def test_source_suppression_is_not_content_deduplication() -> None:
    assert len(pack(candidates(), 20, "unique_source")) == 2
    assert len(pack(candidates(), 20, "exact_duplicate")) == 3
    assert budget_metrics(candidates(), pack(candidates(), 15), {"b"})["source_recall"] == 0
    assert (
        budget_metrics(candidates(), pack(candidates(), 15, "unique_source"), {"b"})[
            "source_recall"
        ]
        == 1
    )


def test_invalid_inputs_fail_explicitly() -> None:
    with pytest.raises(ValueError):
        pack(candidates(), -1)
    with pytest.raises(ValueError):
        pack(candidates() * 2, 100)
    with pytest.raises(ValueError):
        pack([SelectionCandidate("bad", "a", "", 0)], 1)
    with pytest.raises(ValueError):
        source_metrics([], set())
    with pytest.raises(ValueError):
        budget_metrics(candidates(), [SelectionCandidate("1", "alien", "changed", 1)], {"a"})


def test_runtime_signals_and_missing_lexical_top1() -> None:
    assert not should_rerank(candidates(), "disagreement")
    assert not should_rerank(candidates(), "no_lexical_winner")
    assert should_rerank(candidates()[1:], "disagreement")
    assert should_rerank(candidates()[1:], "no_lexical_winner")
    assert not should_rerank([], "disagreement")
    with pytest.raises(ValueError):
        should_rerank(candidates(), "unknown")
