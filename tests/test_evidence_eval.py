import pytest
from ctxd.app.evals.context_selection import SelectionCandidate, pack
from ctxd.app.evals.evidence import (
    EvidenceCase,
    EvidenceCorpus,
    clustered_bootstrap,
    evaluate_evidence,
    grouped_split,
    validate_split,
)
from ctxd.app.ingestion.chunking import StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.models.domain import DocumentSourceType


def fixture() -> EvidenceCorpus:
    docs = [
        document_from_content(
            content=text,
            source_path=f"{i}.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id="evidence",
        )
        for i, text in enumerate(
            [
                "Alpha value is 7. Background material.",
                "Beta value is 9.",
                "Alpha value is 7. Background material.",
            ]
        )
    ]
    chunks = [c for d in docs for c in StructureAwareChunker().chunk(d)]

    def span(index: int, excerpt: str) -> dict[str, object]:
        c = chunks[index]
        start = c.content.index(excerpt)
        return {
            "source": f"{index}.txt",
            "chunk_id": c.chunk_id,
            "start": start,
            "end": start + len(excerpt),
            "excerpt": excerpt,
        }

    case = {
        "case_id": "test",
        "query": "What are alpha and beta?",
        "tenant_id": "evidence",
        "template_group": "pair",
        "status": "VERIFIED_FIXTURE",
        "answerability_notes": "Both values needed",
        "budget_pressure_class": "joint",
        "evidence_groups": [
            {
                "group_id": "alpha",
                "requirement": "REQUIRED",
                "alternatives": [
                    {"spans": [span(0, "Alpha value is 7.")]},
                    {"spans": [span(2, "Alpha value is 7.")]},
                ],
            },
            {
                "group_id": "beta",
                "requirement": "REQUIRED",
                "alternatives": [{"spans": [span(1, "Beta value is 9.")]}],
            },
        ],
    }
    return EvidenceCorpus.model_validate(
        {"provenance": "unit fixture", "documents": docs, "chunks": chunks, "cases": [case]}
    )


def selection(corpus: EvidenceCorpus) -> list[SelectionCandidate]:
    return [
        SelectionCandidate(c.chunk_id, str(c.metadata["source_path"]), c.content, c.token_count)
        for c in corpus.chunks
    ]


def test_required_group_recall_alternatives_and_answerability() -> None:
    corpus = fixture()
    rows = selection(corpus)
    mapping = {c.chunk_id: c for c in corpus.chunks}
    score = evaluate_evidence(corpus.cases[0], rows, rows[:1], mapping)
    assert score["required_recall"] == 0.5
    assert score["full_answerability"] == 0
    assert score["retrieved_required_recall"] == 1
    assert evaluate_evidence(corpus.cases[0], rows, rows[1:], mapping)["full_answerability"] == 1
    assert evaluate_evidence(corpus.cases[0], rows, [], mapping)["span_token_precision"] == 0


def test_joint_spans_are_and_not_or() -> None:
    corpus = fixture()
    case = corpus.cases[0].model_copy(deep=True)
    first = case.evidence_groups[0].alternatives[0].spans[0]
    second = case.evidence_groups[1].alternatives[0].spans[0]
    case.evidence_groups = case.evidence_groups[:1]
    case.evidence_groups[0].alternatives = case.evidence_groups[0].alternatives[:1]
    case.evidence_groups[0].alternatives[0].spans = [first, second]
    rows = selection(corpus)
    mapping = {c.chunk_id: c for c in corpus.chunks}
    assert evaluate_evidence(case, rows, rows[:1], mapping)["required_recall"] == 0
    assert evaluate_evidence(case, rows, rows[:2], mapping)["required_recall"] == 1


def test_redundancy_precision_and_efficiency_count_span_token_unions() -> None:
    corpus = fixture()
    rows = selection(corpus)
    score = evaluate_evidence(corpus.cases[0], rows, rows, {c.chunk_id: c for c in corpus.chunks})
    assert score["redundant_span_tokens"] == 5
    assert score["span_token_precision"] == 15 / sum(c.tokens for c in rows)
    assert score["required_groups_per_1k_tokens"] == 2000 / sum(c.tokens for c in rows)
    assert score["distractor_tokens"] == 0


@pytest.mark.parametrize("mutation", ["offset", "excerpt", "source", "tenant", "identity"])
def test_invalid_span_locators_fail(mutation: str) -> None:
    data = fixture().model_dump(mode="json")
    case = data["cases"][0]
    span = case["evidence_groups"][0]["alternatives"][0]["spans"][0]
    if mutation == "offset":
        span["start"] += 1
    elif mutation == "excerpt":
        span["excerpt"] = "fabricated"
    elif mutation == "source":
        span["source"] = "wrong"
    elif mutation == "tenant":
        case["tenant_id"] = "other"
    else:
        span["chunk_id"] = "missing"
    with pytest.raises(ValueError):
        EvidenceCorpus.model_validate(data)


def test_end_offset_past_chunk_end_is_rejected() -> None:
    data = fixture().model_dump(mode="json")
    span = data["cases"][0]["evidence_groups"][0]["alternatives"][0]["spans"][0]
    span["excerpt"] = data["chunks"][0]["content"]
    span["end"] = len(span["excerpt"]) + 100
    with pytest.raises(ValueError):
        EvidenceCorpus.model_validate(data)


def test_review_and_vacuous_answerability_are_rejected() -> None:
    corpus = fixture()
    case = corpus.cases[0].model_copy(update={"status": "NEEDS_HUMAN_REVIEW"})
    with pytest.raises(ValueError):
        evaluate_evidence(case, [], [], {})
    data = corpus.cases[0].model_dump()
    data["evidence_groups"] = []
    with pytest.raises(ValueError):
        EvidenceCase.model_validate(data)
    data["status"] = "NEEDS_HUMAN_REVIEW"
    assert EvidenceCase.model_validate(data).evidence_groups == []


def test_grouped_split_and_query_leakage_validation() -> None:
    base = fixture().cases[0]
    cases = [
        base.model_copy(
            update={
                "case_id": str(i),
                "template_group": str(i // 2),
                "query": f"question {i // 2}",
                "tenant_id": f"independent-family-{i // 2}",
            }
        )
        for i in range(12)
    ]
    first = grouped_split(cases, 9)
    assert first == grouped_split(cases, 9)
    assert len(set(first.values())) == 2
    broken = dict(first)
    broken["0"] = "holdout" if first["1"] == "development" else "development"
    with pytest.raises(ValueError):
        validate_split(cases, broken)


def test_cluster_bootstrap_is_reproducible_and_handles_constant_deltas() -> None:
    values = {"a": [1.0, 1.0], "b": [1.0]}
    result = clustered_bootstrap(values)
    assert result == clustered_bootstrap(values)
    assert result["low"] == result["high"] == result["point"] == 1
    with pytest.raises(ValueError):
        clustered_bootstrap({}, resamples=2000)


def test_identical_text_at_distinct_sources_can_be_jointly_required() -> None:
    corpus = fixture()
    case = corpus.cases[0].model_copy(deep=True)
    # Two source-specific obligations; text equality is NOT an alternative label.
    first = case.evidence_groups[0].model_copy(deep=True)
    second = case.evidence_groups[0].model_copy(deep=True)
    first.alternatives = first.alternatives[:1]
    second.group_id = "other-source"
    second.alternatives = second.alternatives[1:]
    case.evidence_groups = [first, second]
    rows = [selection(corpus)[0], selection(corpus)[2]]
    mapping = {c.chunk_id: c for c in corpus.chunks}
    assert evaluate_evidence(case, rows, rows, mapping)["full_answerability"] == 1
    deduplicated = pack(rows, 256, "exact_duplicate")
    assert evaluate_evidence(case, rows, deduplicated, mapping)["full_answerability"] == 0
    assert evaluate_evidence(case, rows, rows, mapping)["redundant_span_tokens"] == 0


def test_optional_and_overlapping_spans_do_not_inflate_precision() -> None:
    corpus = fixture()
    case = corpus.cases[0].model_copy(deep=True)
    optional = case.evidence_groups[0].model_copy(deep=True)
    optional.group_id = "optional"
    optional.requirement = "OPTIONAL"
    case.evidence_groups.append(optional)
    rows = selection(corpus)
    mapping = {c.chunk_id: c for c in corpus.chunks}
    assert (
        evaluate_evidence(case, rows, rows[:2], mapping)["span_token_precision"]
        == (evaluate_evidence(corpus.cases[0], rows, rows[:2], mapping)["span_token_precision"])
    )
    assert evaluate_evidence(case, rows, rows[:2], mapping)["full_answerability"] == 1


def test_duplicate_query_across_distinct_groups_is_rejected() -> None:
    base = fixture().cases[0]
    cases = [
        base.model_copy(update={"case_id": "a", "template_group": "a"}),
        base.model_copy(update={"case_id": "b", "template_group": "b"}),
    ]
    with pytest.raises(ValueError):
        validate_split(cases, {"a": "development", "b": "holdout"})
    cases[1].query = "A different question about the same evidence source"
    with pytest.raises(ValueError, match="evidence-source"):
        validate_split(cases, {"a": "development", "b": "holdout"})


def test_budget_pressure_and_candidate_tampering() -> None:
    corpus = fixture()
    rows = selection(corpus)
    mapping = {c.chunk_id: c for c in corpus.chunks}
    selected = pack(rows, rows[0].tokens)
    assert evaluate_evidence(corpus.cases[0], rows, selected, mapping)["full_answerability"] == 0
    assert evaluate_evidence(corpus.cases[0], rows, rows[:2], mapping)["full_answerability"] == 1
    forged = SelectionCandidate(rows[0].identity, rows[0].source, "wrong", rows[0].tokens)
    with pytest.raises(ValueError):
        evaluate_evidence(corpus.cases[0], rows, [forged], mapping)
