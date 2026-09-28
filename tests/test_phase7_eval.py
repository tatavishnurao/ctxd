from types import SimpleNamespace

from ctxd.app.evals.phase7 import (
    apply_lexical_guardrail,
    apply_rank_guardrail,
    bootstrap_deltas,
    candidate_identity_preserved,
    canonical_manifest_hash,
    lexical_protection_ids,
    query_features,
    rank_delta_buckets,
    stratified_partitions,
    transition_counts,
    transition_label,
)


def _case(case_id: str, question: str, category: str) -> dict[str, object]:
    return {
        "id": case_id,
        "question": question,
        "task_type": category,
        "expected_sources": ["answer.md"],
        "metadata": {},
    }


def test_split_is_deterministic_stratified_and_groups_duplicate_queries() -> None:
    cases = [
        _case("a", "same query", "exact"),
        _case("b", "same query", "exact"),
        _case("c", "another", "morphology"),
        _case("d", "third", "morphology"),
        _case("e", "fourth", "morphology"),
    ]
    split = stratified_partitions(cases, seed=731)
    assert split == stratified_partitions(cases, seed=731)
    assert split["a"] == split["b"]
    assert set(split) == {case["id"] for case in cases}


def test_split_manifest_hash_ignores_only_its_own_digest() -> None:
    manifest = {"seed": 1, "cases": [{"case_id": "a"}]}
    digest = canonical_manifest_hash(manifest)
    assert canonical_manifest_hash(manifest | {"split_manifest_sha256": digest}) == digest


def test_exact_overlap_and_identifier_features() -> None:
    features = query_features(
        "Which flag controls subject_12?", ["The subject_12 flag is enabled."]
    )
    assert features["has_exact_term"] is True
    assert features["has_exact_identifier_overlap"] is True
    assert features["query_length_bucket"] == "4-7"


def test_guardrail_is_deterministic_and_preserves_candidate_identity() -> None:
    lexical = SimpleNamespace(source_id="lex", metadata={"lexical_rank": 1})
    semantic = SimpleNamespace(source_id="sem", metadata={"semantic_rank": 1})
    other = SimpleNamespace(source_id="other", metadata={})
    candidates = [semantic, lexical, other]
    scores = {"lex": 0.1, "sem": 0.9, "other": 0.8}
    guarded = apply_lexical_guardrail(candidates, scores)
    assert [candidate.source_id for candidate in guarded] == ["lex", "sem", "other"]
    assert candidate_identity_preserved(candidates, guarded)
    assert [x.source_id for x in guarded] == [
        x.source_id for x in apply_lexical_guardrail(candidates, scores)
    ]


def test_lexical_guardrails_use_only_runtime_candidate_signals() -> None:
    candidates = [
        {
            "source_id": "a",
            "lexical_rank": 1,
            "lexical_raw_score": 10.0,
            "exact_query_token_overlap": ["token_9"],
            "rare_identifier_overlap": ["token_9"],
            "rrf_rank": 2,
        },
        {
            "source_id": "b",
            "lexical_rank": 2,
            "lexical_raw_score": 4.0,
            "exact_query_token_overlap": [],
            "rare_identifier_overlap": [],
            "rrf_rank": 1,
        },
    ]
    protected = lexical_protection_ids(candidates, "protect_strong_identifier_winner")
    assert protected == {"a"}
    result = apply_rank_guardrail(candidates, {"a": -1.0, "b": 2.0}, protected)
    assert [item["source_id"] for item in result] == ["a", "b"]
    assert set(item["source_id"] for item in result) == {"a", "b"}


def test_bootstrap_is_reproducible_and_transition_accounting_exact() -> None:
    baseline = [{"mrr": 0.0, "ndcg_at_5": 0.2, "recall_at_1": 0.0} for _ in range(8)]
    candidate = [{"mrr": 0.1, "ndcg_at_5": 0.3, "recall_at_1": 1.0} for _ in range(8)]
    first = bootstrap_deltas(baseline, candidate, seed=99, resamples=1000)
    assert first == bootstrap_deltas(baseline, candidate, seed=99, resamples=1000)
    assert first["delta_mrr"]["ci_95_low"] == 0.1
    assert transition_label(2, 5) == "regressed"
    assert transition_label(1, 4) == "regressed"
    assert transition_label(None, 1) == "fixed"
    assert transition_label(None, None) == "unchanged_incorrect"
    assert transition_counts([1, 2, 1, None], [2, 1, 1, None]) == {
        "fixed": 1,
        "regressed": 1,
        "unchanged_correct": 1,
        "unchanged_incorrect": 1,
    }


def test_rank_delta_buckets_cover_all_values() -> None:
    values = [12, 5, 2, 0, -2, -6, -15]
    result = rank_delta_buckets(values)
    assert result == {
        "+10 or more": 1,
        "+5 to +9": 1,
        "+1 to +4": 1,
        "0": 1,
        "-1 to -4": 1,
        "-5 to -9": 1,
        "-10 or worse": 1,
    }
