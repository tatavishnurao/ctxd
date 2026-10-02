"""Export human packets and apply explicit, hash-bound human review submissions.

No command fabricates reviewer identities, approves batches automatically, runs
retrieval, or modifies an existing review artifact.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

from ctxd.app.evals.evidence import EvidenceCorpus, StrictModel, digest, validate_split
from ctxd.app.evals.review import ReviewState, ReviewStatus, transition_review

ROOT = Path(__file__).resolve().parents[1]


class Submission(StrictModel):
    dataset_sha256: str
    previous_review_sha256: str
    case_id: str
    case_sha256: str
    status: ReviewStatus
    reviewer_id: str
    human_attestation: bool
    reviewed_at: datetime
    notes: str


def load(state_path: Path, root: Path = ROOT) -> tuple[EvidenceCorpus, dict[str, str], ReviewState]:
    data = json.loads((root / "evals/phase10_evidence_cases.json").read_text())
    corpus = EvidenceCorpus.model_validate(data)
    split = json.loads((root / "evals/phase10_split_manifest.json").read_text())
    state = ReviewState.model_validate_json(state_path.read_text())
    if digest(data) != split["dataset_sha256"] or digest(data) != state.dataset_sha256:
        raise ValueError("dataset/review revision mismatch")
    if digest(split["assignments"]) != split["split_sha256"]:
        raise ValueError("split hash changed")
    validate_split(corpus.cases, split["assignments"])
    if {r.case_id for r in state.records} != {c.case_id for c in corpus.cases}:
        raise ValueError("review case coverage differs")
    by_id = {r.case_id: r for r in state.records}
    for case in corpus.cases:
        if by_id[case.case_id].case_sha256 != digest(case.model_dump(mode="json")):
            raise ValueError("case changed after review")
    return corpus, split["assignments"], state


def apply_submission(state: ReviewState, submission: Submission) -> ReviewState:
    if (
        submission.dataset_sha256 != state.dataset_sha256
        or submission.previous_review_sha256 != digest(state.model_dump(mode="json"))
    ):
        raise ValueError("submission is stale or belongs to another dataset")
    records = {r.case_id: r for r in state.records}
    record = records[submission.case_id]
    if record.case_sha256 != submission.case_sha256:
        raise ValueError("submission is bound to another case revision")
    records[record.case_id] = transition_review(
        record,
        submission.status,
        reviewer_id=submission.reviewer_id,
        human_attestation=submission.human_attestation,
        reviewed_at=submission.reviewed_at,
        notes=submission.notes,
    )
    return ReviewState(
        dataset_sha256=state.dataset_sha256,
        parent_review_sha256=digest(state.model_dump(mode="json")),
        records=list(records.values()),
    )


def render(
    corpus: EvidenceCorpus, assignments: dict[str, str], state: ReviewState, root: Path = ROOT
) -> str:
    metadata = json.loads((root / "evals/phase10_case_metadata.json").read_text())
    sources = json.loads((root / "evals/phase10_source_manifest.json").read_text())
    urls = {s["source"]: s["url"] for s in sources}
    chunks = {c.chunk_id: c for c in corpus.chunks}
    records = {r.case_id: r for r in state.records}
    dev_count = sum(p == "development" for p in assignments.values())
    banner = (
        "PROVISIONAL — NOT INDEPENDENTLY REVIEWED"
        if any(r.reviewer_status != "APPROVED" for r in state.records)
        else "REVIEW RECORDS PRESENT — check canonical design eligibility separately"
    )
    lines = [
        "# Phase 10 independent review packet",
        "",
        f"**{banner}**",
        "",
        "Authentic pinned repository text; agent-authored questions and proposed labels. "
        "This packet alone does NOT establish canonical eligibility or holdout blinding.",
        "",
        "## Reviewer instructions",
        "",
        f"Review every holdout case and at least 50% of development "
        f"({math.ceil(dev_count / 2)} of {dev_count}), covering every "
        "development family. Prefer all cases. Review source context, not merely matching strings. "
        "Do not inspect retrieval/ranking outcomes while authoring or correcting labels.",
        "",
        "For EACH case: check question clarity/version scope; exact span/source/tenant; "
        "sufficiency and minimality; AND spans versus OR alternatives; optional/supporting "
        "roles; independently required provenance; missing valid alternative chunks; and measured "
        "whole-chunk feasibility. Identical text at different resources is not interchangeable.",
        "",
        "Author status is DRAFT, not VERIFIED_BY_AUTHOR. Exact-string checks are mechanical "
        "and do not certify sufficiency. Repeated snippet occurrences use the first source "
        "occurrence; verify that it is the intended function/branch. Mark CORRECTED or DISPUTED "
        "if labels are overbroad, underspecified or attached to the wrong occurrence.",
        "",
        "APPROVED requires a real independent human's identity, timezone-aware timestamp, explicit "
        "human attestation and substantive notes. Self-review is rejected. The tool checks the "
        "attestation contract; it does NOT authenticate people or prove they read a case. "
        "Retain externally verifiable review evidence. Never have an assistant invent approval.",
        "",
        "CORRECTED requires a versioned revision and fresh review; it is not scoring approval. "
        "Preserve old dataset/review files and assignments. Recompute locators, costs, "
        "split hashes and packets. Do not select corrections using holdout outcomes. "
        "DISPUTED blocks that case until an explicit, documented resolution. Corrections cannot be "
        "laundered through status transitions into approval of unchanged labels.",
        "",
        "## Apply one human submission",
        "",
        "Create a JSON object with these exact keys: dataset_sha256, previous_review_sha256, "
        "case_id, case_sha256, status (APPROVED/CORRECTED/DISPUTED), reviewer_id, "
        "human_attestation, reviewed_at, notes. Copy hashes below; use your real identity, actual "
        "review date and findings. No prefilled approval example is supplied.",
        "",
        "Run `uv run python benchmarks/phase10_review.py apply --submission /path/to/human.json "
        "--state evals/phase10_review_state.json --output evals/phase10_review_round1.json`. "
        "For the next submission use the previous round as --state and a fresh output path. "
        "The parent hash prevents stale/parallel submissions from silently overwriting a review. "
        "Render a new packet with `render --state ... --output /new/packet.md`.",
        "",
        f"Dataset SHA-256: `{state.dataset_sha256}`",
        "",
        f"Review state SHA-256: `{digest(state.model_dump(mode='json'))}`",
        "",
        "Full immutable documents and chunks: `evals/phase10_evidence_cases.json`. "
        "Original-source character and line locators: `evals/phase10_source_locators.json`. "
        "Source provenance/permission notes: `evals/phase10_source_manifest.json`.",
        "",
        "## Cases",
        "",
    ]
    for case in corpus.cases:
        record = records[case.case_id]
        cost = metadata[case.case_id]["feasibility"]
        lines.extend(
            [
                f"### {case.case_id} — {case.query}",
                "",
                f"Partition: {assignments[case.case_id]}; family: {case.template_group}; "
                f"kind: {metadata[case.case_id]['query_kind']}.",
                "",
                f"Author: {record.author_id} / {record.author_status}; "
                f"review: {record.reviewer_status}; reviewer: {record.reviewer_id or 'none'}.",
                "",
                f"Case SHA-256: `{record.case_sha256}`",
                "",
                f"Proposed stratum: {cost['stratum']}; minimum whole chunks: "
                f"{cost['whole_chunk_tokens']} approximate tokens; "
                f"span lower bound: {cost['span_tokens']}.",
                "",
                case.answerability_notes,
                "",
            ]
        )
        for group in case.evidence_groups:
            lines.append(f"**{group.requirement} {group.group_id}** (OR alternatives below)")
            for index, alternative in enumerate(group.alternatives, 1):
                lines.extend(
                    ["", f"Alternative {index}: ALL listed spans are jointly required.", ""]
                )
                for span in alternative.spans:
                    chunk = chunks[span.chunk_id]
                    lines.extend(
                        [
                            f"- [{span.source}]({urls[span.source]}"
                            f"#L{chunk.start_line}-L{chunk.end_line}) "
                            f"— chunk `{span.chunk_id}`, "
                            f"half-open characters [{span.start}, {span.end}).",
                            "",
                            "````text",
                            span.excerpt,
                            "````",
                            "",
                        ]
                    )
        findings = record.notes or "pending. Do not score this proposed annotation as approved."
        lines.extend([f"Reviewer findings: {findings}", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("render", "apply"))
    parser.add_argument("--revision-root", type=Path, default=ROOT)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus, assignments, state = load(
        args.state or args.revision_root / "evals/phase10_review_state.json", args.revision_root
    )
    if args.action == "apply":
        if args.submission is None:
            parser.error("apply requires a human-authored --submission file")
        submission = Submission.model_validate_json(args.submission.read_text())
        result = apply_submission(state, submission).model_dump_json(indent=2) + "\n"
    else:
        result = render(corpus, assignments, state, args.revision_root)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(result)


if __name__ == "__main__":
    main()
