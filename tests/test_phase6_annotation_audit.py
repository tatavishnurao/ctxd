from copy import deepcopy

from benchmarks.phase6_evaluation_audit import create_annotation_audit


def test_annotation_audit_is_deterministic_and_preserves_source() -> None:
    source = {
        "documents": [],
        "cases": [
            {
                "id": "a",
                "question": "Ambiguous?",
                "expected_sources": ["left.md"],
                "task_type": "ambiguous",
            },
            {
                "id": "b",
                "question": "Ambiguous?",
                "expected_sources": ["right.md"],
                "task_type": "ambiguous",
            },
            {
                "id": "c",
                "question": "Confirmed?",
                "expected_sources": ["answer.md"],
                "task_type": "exact",
            },
        ],
    }
    original = deepcopy(source)

    first_audit, first_corpus = create_annotation_audit(source)
    second_audit, second_corpus = create_annotation_audit(source)

    assert source == original
    assert first_audit == second_audit
    assert first_corpus == second_corpus
    assert first_audit["status_counts"] == {
        "confirmed": 1,
        "corrected": 0,
        "expanded": 0,
        "ambiguous": 2,
    }
    assert first_corpus["cases"][0]["expected_sources"] == ["left.md", "right.md"]
    assert first_corpus["cases"][1]["expected_sources"] == ["left.md", "right.md"]
