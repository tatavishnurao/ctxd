import hashlib
import json
from pathlib import Path

import pytest
from benchmarks.phase10_build import build
from benchmarks.phase10_check import eligibility
from benchmarks.phase10_review import load, render
from ctxd.app.evals.evidence import EvidenceCorpus, digest, evaluate_evidence, validate_split
from ctxd.app.evals.review import ReviewState, feasibility

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> object:
    return json.loads((ROOT / path).read_text())


def corpus() -> EvidenceCorpus:
    return EvidenceCorpus.model_validate(read("evals/phase10_evidence_cases.json"))


def frozen_packet() -> str:
    evidence, assignments, state = load(ROOT / "evals/phase10_review_state.json")
    return render(evidence, assignments, state)


def test_source_provenance_matches_verbatim_pinned_documents() -> None:
    evidence = corpus()
    sources = {s["source"]: s for s in read("evals/phase10_source_manifest.json")}
    history = read("benchmarks/phase10_history_freeze.json")
    assert len(sources) == len(evidence.documents) == 25
    for document in evidence.documents:
        source = sources[document.source_path]
        sha = hashlib.sha256(document.content.encode()).hexdigest()
        assert sha == source["sha256"] == history["tracked_base_sha256"][document.source_path]
        assert source["git_revision"] == history["base_sha"]
        assert history["base_sha"] in source["url"]
        assert "not inferred" in source["license"]


def test_frozen_cases_and_split_are_fresh_and_honestly_unreviewed() -> None:
    evidence, split, state = load(ROOT / "evals/phase10_review_state.json")
    assert len(evidence.cases) == 121
    assert len(evidence.chunks) == 92
    assert len({c.template_group for c in evidence.cases}) == 15
    assert len({c.query.casefold() for c in evidence.cases}) == len(evidence.cases)
    assert sum(p == "development" for p in split.values()) == 82
    assert sum(p == "holdout" for p in split.values()) == 39
    assert all(c.status == "NEEDS_HUMAN_REVIEW" for c in evidence.cases)
    assert all(r.reviewer_id is None and not r.human_attestation for r in state.records)
    assert all(r.author_status == "DRAFT" for r in state.records)
    previous = EvidenceCorpus.model_validate(read("evals/phase9_evidence_cases.json"))
    assert not {c.query for c in previous.cases} & {c.query for c in evidence.cases}
    validate_split(evidence.cases, split)


def test_measured_costs_match_production_chunks_and_preserve_imbalance() -> None:
    evidence = corpus()
    chunks = {c.chunk_id: c for c in evidence.chunks}
    metadata = read("evals/phase10_case_metadata.json")
    for case in evidence.cases:
        assert metadata[case.case_id]["feasibility"] == feasibility(case, chunks)
    stats = read("benchmarks/phase10_feasibility.json")["distributions"]
    assert stats["all"]["strata"] == {"EASY": 104, "MEDIUM": 10, "HARD": 7}
    assert stats["holdout"]["strata"] == {"EASY": 35, "MEDIUM": 4}
    assert stats["all"]["feasible_at_budget"] == {
        "256": 26,
        "512": 104,
        "1024": 114,
        "2048": 121,
        "4096": 121,
    }


def test_original_source_locators_are_exact() -> None:
    evidence = corpus()
    docs = {d.source_path: d.content for d in evidence.documents}
    for atom, locator in read("evals/phase10_source_locators.json").items():
        source = docs[locator["source"]]
        excerpt = atom.split("@", 1)[1]
        assert source[locator["original_char_start"] : locator["original_char_end"]] == excerpt
        assert source.count("\n", 0, locator["original_char_start"]) + 1 == locator["original_line"]


def test_schema_contains_joint_optional_and_supporting_annotations() -> None:
    groups = [g for c in corpus().cases for g in c.evidence_groups]
    assert {g.requirement for g in groups} == {"REQUIRED", "SUPPORTING", "OPTIONAL"}
    assert any(len(a.spans) > 1 for g in groups for a in g.alternatives)
    assert any(len(g.alternatives) > 1 for g in groups)


def test_no_pending_case_can_be_scored_as_a_verified_fixture() -> None:
    evidence = corpus()
    for case in evidence.cases:
        with pytest.raises(ValueError, match="unreviewed"):
            evaluate_evidence(case, [], [], {})


def test_eligibility_is_blocked_before_database_or_holdout_access() -> None:
    result = eligibility(ROOT / "evals/phase10_review_state.json")
    assert result == read("benchmarks/phase10_blocked_status.json")
    assert not result["canonical_eligible"]
    assert result["review_errors"] and result["design_errors"]
    assert result["holdout"] == result["bootstrap"] == "NOT_RUN"
    assert result["selected_policy"] is result["metrics"] is None
    assert not (ROOT / "benchmarks/phase10_holdout_started.json").exists()
    assert not (ROOT / "benchmarks/phase10_holdout.json").exists()


def test_packet_covers_each_case_and_hash_without_inventing_approval() -> None:
    # PHASE10_REVIEW_PACKET.md is local-only (gitignored); check the rendered packet.
    packet = frozen_packet()
    state = ReviewState.model_validate(read("evals/phase10_review_state.json"))
    assert state.dataset_sha256 in packet
    assert "NOT INDEPENDENTLY REVIEWED" in packet
    for record in state.records:
        assert f"### {record.case_id} —" in packet
        assert record.case_sha256 in packet
    assert packet.count("review: UNREVIEWED; reviewer: none.") == 121


def test_builder_reproduces_snapshot_without_requiring_git_history(monkeypatch) -> None:
    evidence = corpus()
    contents = {d.source_path: d.content.encode() for d in evidence.documents}

    def pinned_blob(args, **kwargs):
        assert args[:2] == ["git", "show"]
        revision, path = args[2].split(":", 1)
        assert revision == read("benchmarks/phase10_history_freeze.json")["base_sha"]
        return contents[path]

    monkeypatch.setattr("benchmarks.phase10_build.subprocess.check_output", pinned_blob)
    rebuilt = build()
    assert rebuilt["dataset"] == evidence.model_dump(mode="json")
    assert rebuilt["reviews"] == read("evals/phase10_review_state.json")
    assert rebuilt["taxonomy"] == read("evals/phase10_case_metadata.json")
    assert rebuilt["source_locators"] == read("evals/phase10_source_locators.json")
    state = ReviewState.model_validate(rebuilt["reviews"])
    assert render(evidence, rebuilt["assignments"], state) == frozen_packet()


def test_versioned_revision_cannot_reuse_old_review_hashes(tmp_path) -> None:
    directory = tmp_path / "evals"
    directory.mkdir()
    for name in ("evidence_cases", "split_manifest", "review_state"):
        filename = f"phase10_{name}.json"
        (directory / filename).write_bytes((ROOT / "evals" / filename).read_bytes())
    state_path = directory / "phase10_review_state.json"
    load(state_path, root=tmp_path)
    path = directory / "phase10_evidence_cases.json"
    changed = json.loads(path.read_text())
    changed["cases"][0]["query"] += " Corrected by a future reviewer."
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="revision mismatch"):
        load(state_path, root=tmp_path)


def test_protocol_is_pinned_and_does_not_expand_policy_search() -> None:
    protocol = read("benchmarks/phase10_protocol.json")
    status = read("benchmarks/phase10_blocked_status.json")
    assert digest(protocol) == status["protocol_sha256"]
    assert protocol["budgets"] == [256, 512, 1024, 2048, 4096]
    assert protocol["packing"]["allowed_alternatives"] == [
        "density",
        "exact_duplicate",
        "unique_source",
    ]
    assert not protocol["reranking"]["new_models_or_algorithms"]
    assert "2000" in protocol["metrics"]["uncertainty"]
    assert "push" in protocol["prohibitions"]
