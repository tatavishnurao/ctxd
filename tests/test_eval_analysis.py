import pytest
from ctxd.app.evals.analysis import (
    aggregate_run_metric,
    distribution,
    length_bucket,
    normalized_content,
    pairwise_accuracy,
    query_features,
    robust_outlier_indices,
    token_jaccard,
)


def test_normalization_and_duplicate_overlap_are_deterministic() -> None:
    assert normalized_content("Hello,  WORLD!") == "hello world"
    assert token_jaccard("alpha beta", "beta alpha") == 1.0
    assert token_jaccard("alpha beta", "beta gamma") == pytest.approx(1 / 3)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "0-64"),
        (64, "0-64"),
        (65, "65-128"),
        (129, "129-256"),
        (257, "257-384"),
        (385, "385-512"),
        (513, ">512"),
    ],
)
def test_length_buckets(count: int, expected: str) -> None:
    assert length_bucket(count) == expected


def test_score_distribution_and_pairwise_accuracy() -> None:
    result = distribution([1.0, 2.0, 3.0])
    assert result["mean"] == 2.0
    assert result["median"] == 2.0
    assert pairwise_accuracy([0.8, 0.9], [0.1, 0.85]) == 0.75
    assert pairwise_accuracy([], [0.1]) is None


def test_query_features_use_explicit_signals() -> None:
    result = query_features("How is subject_12 being updated?", {"updated"})
    assert result["exact_identifier"] is True
    assert result["code_like"] is True
    assert result["rare_term"] is True
    assert result["natural_language"] is True


def test_robust_outliers_and_run_aggregation() -> None:
    assert robust_outlier_indices([10.0, 10.5, 11.0, 40.0]) == [3]
    assert robust_outlier_indices([10.0, 10.0, 10.0, 11.0]) == [3]
    assert robust_outlier_indices([10.0, 11.0]) == []
    summary = aggregate_run_metric([9.0, 10.0, 11.0])
    assert summary == {
        "runs": 3,
        "median": 10.0,
        "min": 9.0,
        "max": 11.0,
        "std": pytest.approx(0.816496580927726),
    }
