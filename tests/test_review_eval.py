"""Unit fixtures only: reviewer identities below are NOT benchmark human reviews."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from benchmarks.phase10_review import Submission, apply_submission
from ctxd.app.evals.context_selection import SelectionCandidate, pack
from ctxd.app.evals.evidence import EvidenceCase, EvidenceCorpus, digest
from ctxd.app.evals.review import (
    ReviewRecord,
    ReviewState,
    failure_decomposition,
    feasibility,
    require_review_gate,
    transition_review,
)
from ctxd.app.ingestion.chunking import StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.models.domain import DocumentSourceType


def fixture() -> EvidenceCorpus:
    docs = [
        document_from_content(
            content=text,
            source_path=f"{i}.txt",
            tenant_id="unit-test",
            source_type=DocumentSourceType.TEXT,
        )
        for i, text in enumerate(
            (
                "Alpha is required. Context follows.",
                "Beta is required.",
                "Alpha is required. Context follows.",
                "Irrelevant noise.",
                "Alpha is required. " + "Background filler. " * 12,
            )
        )
    ]
    chunks = [c for d in docs for c in StructureAwareChunker().chunk(d)]

    def span(i: int) -> dict[str, object]:
        c = chunks[i]
        excerpt = c.content.split(".")[0] + "."
        return {
            "source": c.metadata["source_path"],
            "chunk_id": c.chunk_id,
            "start": 0,
            "end": len(excerpt),
            "excerpt": excerpt,
        }

    case = EvidenceCase.model_validate(
        {
            "case_id": "unit",
            "query": "Which alpha and beta?",
            "tenant_id": "unit-test",
            "template_group": "unit",
            "status": "VERIFIED_FIXTURE",
            "answerability_notes": "Synthetic test only",
            "budget_pressure_class": "unit",
            "evidence_groups": [
                {
                    "group_id": "alpha",
                    "requirement": "REQUIRED",
                    "alternatives": [{"spans": [span(i)]} for i in (0, 2, 4)],
                },
                {
                    "group_id": "beta",
                    "requirement": "REQUIRED",
                    "alternatives": [{"spans": [span(1)]}],
                },
            ],
        }
    )
    return EvidenceCorpus(
        provenance="unit test, not benchmark evidence", documents=docs, chunks=chunks, cases=[case]
    )


def candidates(corpus: EvidenceCorpus) -> list[SelectionCandidate]:
    return [
        SelectionCandidate(c.chunk_id, str(c.metadata["source_path"]), c.content, c.token_count)
        for c in corpus.chunks
    ]


def test_exact_oracle_counts_unions_and_alternatives() -> None:
    corpus = fixture()
    chunks = {c.chunk_id: c for c in corpus.chunks}
    case = corpus.cases[0]
    cost = feasibility(case, chunks)
    assert cost["whole_chunk_tokens"] == corpus.chunks[0].token_count + corpus.chunks[1].token_count
    assert cost["span_tokens"] == 8
    assert feasibility(case, chunks, set())["stratum"] == "UNAVAILABLE"
    duplicate = case.evidence_groups[0].model_copy(deep=True)
    duplicate.group_id = "same-obligation"
    case.evidence_groups.append(duplicate)
    assert feasibility(case, chunks) == cost


def test_oracle_checks_locators_and_empty_requirements() -> None:
    corpus = fixture()
    chunks = {c.chunk_id: c for c in corpus.chunks}
    case = corpus.cases[0].model_copy(deep=True)
    case.evidence_groups[0].alternatives[0].spans[0].end += 1000
    with pytest.raises(ValueError, match="locator"):
        feasibility(case, chunks)
    case.evidence_groups = []
    with pytest.raises(ValueError, match="without required"):
        failure_decomposition(case, chunks, [], [], 100)


@pytest.mark.parametrize(
    ("pool", "chosen", "budget", "expected"),
    [
        ([0, 1], [0, 1], 100, "SELECTED"),
        ([0], [0], 100, "RETRIEVAL_MISS"),
        ([0, 1], [0], 100, "PACKING_ORDER"),
        ([0, 1], [], 0, "INSUFFICIENT_BUDGET"),
        ([4, 1], [1], 20, "BUDGET_DROP"),
    ],
)
def test_failure_dimensions(pool: list[int], chosen: list[int], budget: int, expected: str) -> None:
    corpus = fixture()
    rows = candidates(corpus)
    result = failure_decomposition(
        corpus.cases[0],
        {c.chunk_id: c for c in corpus.chunks},
        [rows[i] for i in pool],
        [rows[i] for i in chosen],
        budget,
    )
    assert result["primary"] == expected


def test_right_source_wrong_chunk_is_not_retrieval_success() -> None:
    corpus = fixture()
    chunks = {c.chunk_id: c for c in corpus.chunks}
    noise = corpus.chunks[3].model_copy(deep=True)
    noise.metadata["source_path"] = "1.txt"
    chunks[noise.chunk_id] = noise
    rows = candidates(corpus)
    wrong = replace(rows[3], source="1.txt")
    result = failure_decomposition(corpus.cases[0], chunks, [rows[0], wrong], [rows[0]], 100)
    assert result["primary"] == "WRONG_CHUNK"
    assert "RETRIEVAL_MISS" in result["flags"]


def test_duplicate_text_does_not_satisfy_independent_provenance() -> None:
    corpus = fixture()
    case = corpus.cases[0].model_copy(deep=True)
    other = case.evidence_groups[0].model_copy(deep=True)
    other.group_id = "independent-resource"
    other.alternatives = [other.alternatives[1]]
    case.evidence_groups[0].alternatives = case.evidence_groups[0].alternatives[:1]
    case.evidence_groups = [case.evidence_groups[0], other]
    rows = [candidates(corpus)[i] for i in (0, 2)]
    chunks = {c.chunk_id: c for c in corpus.chunks}
    result = failure_decomposition(case, chunks, rows, pack(rows, 100, "exact_duplicate"), 100)
    assert "PROVENANCE_CONFLICT" in result["flags"]
    assert "DUPLICATE_WASTE" not in result["flags"]
    # Both duplicated resources are needed; neither is safely removable.
    case.evidence_groups.append(corpus.cases[0].evidence_groups[1])
    assert failure_decomposition(case, chunks, rows, rows, 100)["safe_duplicate_tokens"] == 0


def test_safe_duplicate_waste_is_a_secondary_diagnostic() -> None:
    corpus = fixture()
    rows = [candidates(corpus)[i] for i in (0, 2)]
    result = failure_decomposition(
        corpus.cases[0], {c.chunk_id: c for c in corpus.chunks}, rows, rows, 100
    )
    assert result["primary"] == "RETRIEVAL_MISS"
    assert result["safe_duplicate_tokens"] == rows[0].tokens
    assert "DUPLICATE_WASTE" in result["flags"]


@pytest.mark.parametrize("field", ["content", "tokens"])
def test_changed_representation_is_distinct_from_packing(field: str) -> None:
    corpus = fixture()
    rows = candidates(corpus)
    changed = replace(rows[0], **{field: "truncated" if field == "content" else 1})
    result = failure_decomposition(
        corpus.cases[0], {c.chunk_id: c for c in corpus.chunks}, [changed, rows[1]], [], 100
    )
    assert result["dimension"] == "E"


def test_diagnostics_reject_identity_tenant_and_budget_errors() -> None:
    corpus = fixture()
    rows = candidates(corpus)
    chunks = {c.chunk_id: c for c in corpus.chunks}
    case = corpus.cases[0]
    for pool, selected, budget in [
        ([rows[0], rows[0]], [], 100),
        ([rows[0]], [rows[1]], 100),
        (rows, rows, 1),
        (rows, [], -1),
    ]:
        with pytest.raises(ValueError):
            failure_decomposition(case, chunks, pool, selected, budget)
    with pytest.raises(ValueError, match="provenance"):
        failure_decomposition(case, chunks, [replace(rows[0], source="other")], [], 100)
    assert (
        failure_decomposition(case, chunks, [], [], 100, disputed=True)["primary"]
        == "ANNOTATION_AMBIGUITY"
    )


def records() -> tuple[list[EvidenceCase], dict[str, str], ReviewState]:
    base = fixture().cases[0]
    cases = [
        base.model_copy(
            deep=True,
            update={
                "case_id": str(i),
                "query": f"unit query {i}",
                "tenant_id": f"test-family-{i // 2}",
                "template_group": f"family-{i // 2}",
            },
        )
        for i in range(6)
    ]
    assignments = {c.case_id: "development" if int(c.case_id) < 4 else "holdout" for c in cases}
    state = ReviewState(
        dataset_sha256=digest("unit-only"),
        records=[
            ReviewRecord(
                case_id=c.case_id,
                case_sha256=digest(c.model_dump(mode="json")),
                author_id="fixture-author",
            )
            for c in cases
        ],
    )
    return cases, assignments, state


def approve(record: ReviewRecord) -> ReviewRecord:
    # Test data, never written into benchmark review records.
    return transition_review(
        record,
        "APPROVED",
        reviewer_id="unit-fixture-reviewer",
        human_attestation=True,
        reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        notes="Unit fixture.",
    )


def test_review_gate_needs_all_holdout_and_half_family_covering_development() -> None:
    cases, split, state = records()
    with pytest.raises(ValueError, match="every holdout"):
        require_review_gate(cases, split, state, state.dataset_sha256)
    state.records = [approve(r) if r.case_id in {"0", "1", "4", "5"} else r for r in state.records]
    with pytest.raises(ValueError, match="family-covering"):
        require_review_gate(cases, split, state, state.dataset_sha256)
    state.records[2] = approve(state.records[2])
    require_review_gate(cases, split, state, state.dataset_sha256)
    with pytest.raises(ValueError, match="weakened"):
        require_review_gate(cases, split, state, state.dataset_sha256, dev_fraction=0.1)
    with pytest.raises(ValueError, match="revision"):
        require_review_gate(cases, split, state, "changed")
    cases[0].query = "edited"
    with pytest.raises(ValueError, match="changed after review"):
        require_review_gate(cases, split, state, state.dataset_sha256)


@pytest.mark.parametrize("mutation", ["self", "machine", "no-notes", "no-date", "duplicate"])
def test_review_contract_rejects_false_approval(mutation: str) -> None:
    _, _, state = records()
    data = approve(state.records[0]).model_dump(mode="json")
    if mutation == "self":
        data["reviewer_id"] = " FIXTURE-AUTHOR "
    elif mutation == "machine":
        data["human_attestation"] = False
    elif mutation == "no-notes":
        data["notes"] = " "
    elif mutation == "no-date":
        data["reviewed_at"] = None
    else:
        with pytest.raises(ValueError, match="duplicate"):
            ReviewState(dataset_sha256=state.dataset_sha256, records=state.records * 2)
        return
    with pytest.raises(ValueError):
        ReviewRecord.model_validate(data)


def test_corrected_is_not_approved_and_cannot_be_laundered() -> None:
    _, _, state = records()
    record = transition_review(
        state.records[0],
        "CORRECTED",
        reviewer_id="unit-reviewer",
        human_attestation=True,
        reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        notes="Fix locator.",
    )
    for status in ("APPROVED", "DISPUTED"):
        with pytest.raises(ValueError, match="transition"):
            transition_review(
                record,
                status,
                reviewer_id="unit-reviewer",
                human_attestation=True,
                reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
                notes="Do not bypass revision.",
            )


def test_submission_is_hash_bound_and_preserves_parent_state() -> None:
    _, _, state = records()
    before = state.model_dump(mode="json")
    submission = Submission(
        dataset_sha256=state.dataset_sha256,
        previous_review_sha256=digest(before),
        case_id="0",
        case_sha256=state.records[0].case_sha256,
        status="APPROVED",
        reviewer_id="unit-reviewer",
        human_attestation=True,
        reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
        notes="Synthetic submission test only.",
    )
    after = apply_submission(state, submission)
    assert state.model_dump(mode="json") == before
    assert after.parent_review_sha256 == digest(before)
    assert after.records[0].reviewer_status == "APPROVED"
    with pytest.raises(ValueError, match="stale"):
        apply_submission(after, submission)
