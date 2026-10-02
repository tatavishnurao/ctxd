"""Offline human-review contracts, exact budget oracles and diagnostic gates."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from ctxd.app.evals.context_selection import SelectionCandidate
from ctxd.app.evals.evidence import EvidenceCase, StrictModel, digest, validate_split
from ctxd.app.ingestion.chunking import ApproximateTokenCounter
from ctxd.app.models.domain import Chunk

ReviewStatus = Literal["UNREVIEWED", "APPROVED", "CORRECTED", "DISPUTED"]


class ReviewRecord(StrictModel):
    case_id: str
    case_sha256: str
    author_id: str = Field(min_length=1)
    author_status: Literal["DRAFT", "VERIFIED_BY_AUTHOR"] = "DRAFT"
    reviewer_status: ReviewStatus = "UNREVIEWED"
    reviewer_id: str | None = None
    human_attestation: bool = False
    reviewed_at: datetime | None = None
    notes: str = ""

    @model_validator(mode="after")
    def honest_review(self) -> Self:
        if not self.author_id.strip():
            raise ValueError("author identity cannot be blank")
        if self.reviewer_status == "UNREVIEWED":
            if (
                self.reviewer_id is not None
                or self.human_attestation
                or self.reviewed_at is not None
            ):
                raise ValueError("unreviewed records cannot contain completed review credentials")
        elif (
            not self.reviewer_id
            or not self.reviewer_id.strip()
            or self.reviewer_id.strip().casefold() == self.author_id.strip().casefold()
            or not self.human_attestation
            or self.reviewed_at is None
            or not self.notes.strip()
        ):
            raise ValueError(
                "review requires independent identity, human attestation, date and notes"
            )
        if self.reviewed_at is not None and self.reviewed_at.tzinfo is None:
            raise ValueError("review timestamp must include timezone")
        return self


class ReviewState(StrictModel):
    dataset_sha256: str
    parent_review_sha256: str | None = None
    records: list[ReviewRecord]

    @model_validator(mode="after")
    def unique_records(self) -> Self:
        if len({r.case_id for r in self.records}) != len(self.records):
            raise ValueError("duplicate review record")
        return self


def transition_review(
    record: ReviewRecord,
    status: ReviewStatus,
    *,
    reviewer_id: str,
    human_attestation: bool,
    reviewed_at: datetime,
    notes: str,
) -> ReviewRecord:
    """Explicit human-supplied attestation; not authentication or automatic approval.

    CORRECTED means proposed corrections need a versioned dataset revision and
    fresh review, not permission to silently mutate the frozen corpus.
    """
    allowed = {
        "UNREVIEWED": {"APPROVED", "CORRECTED", "DISPUTED"},
        "APPROVED": {"DISPUTED"},
        "CORRECTED": set(),
        "DISPUTED": {"APPROVED", "CORRECTED"},
    }
    if status not in allowed[record.reviewer_status]:
        raise ValueError("invalid review transition; corrections require a dataset revision")
    return ReviewRecord.model_validate(
        {
            **record.model_dump(),
            "reviewer_status": status,
            "reviewer_id": reviewer_id,
            "human_attestation": human_attestation,
            "reviewed_at": reviewed_at,
            "notes": notes,
        }
    )


def require_review_gate(
    cases: Sequence[EvidenceCase],
    assignments: Mapping[str, str],
    state: ReviewState,
    dataset_sha256: str,
    dev_fraction: float = 0.5,
) -> None:
    """All holdout + >=50% development, covering every dev family, must be approved.

    This checks documented attestations; it cannot establish a person's identity.
    """
    if not 0.5 <= dev_fraction <= 1:
        raise ValueError("development review threshold cannot be weakened below 50%")
    state = ReviewState.model_validate(state.model_dump())
    validate_split(cases, assignments)
    if state.dataset_sha256 != dataset_sha256:
        raise ValueError("reviews belong to another dataset revision")
    records = {r.case_id: r for r in state.records}
    if set(records) != {c.case_id for c in cases} or set(assignments) != set(records):
        raise ValueError("review/split coverage differs from dataset")
    approved = set()
    for case in cases:
        record = records[case.case_id]
        if record.case_sha256 != digest(case.model_dump(mode="json")):
            raise ValueError("case changed after review")
        if record.reviewer_status == "APPROVED":
            approved.add(case.case_id)
    dev = [c for c in cases if assignments[c.case_id] == "development"]
    holdout = [c for c in cases if assignments[c.case_id] == "holdout"]
    if (
        not dev
        or not holdout
        or any(p not in {"development", "holdout"} for p in assignments.values())
    ):
        raise ValueError("nonempty valid development and holdout partitions required")
    if not all(c.case_id in approved for c in holdout):
        raise ValueError("BLOCKED: every holdout case needs independent human approval")
    reviewed_dev = [c for c in dev if c.case_id in approved]
    if len(reviewed_dev) < math.ceil(len(dev) * dev_fraction) or {
        c.template_group for c in reviewed_dev
    } != {c.template_group for c in dev}:
        raise ValueError("BLOCKED: substantial, family-covering development review is missing")


def feasibility(
    case: EvidenceCase, chunks: Mapping[str, Chunk], available: set[str] | None = None
) -> dict[str, int | str | None]:
    """Exact union-cost oracle over proposed REQUIRED alternatives, never a policy.

    Returns both whole-chunk minimum (applicable to current assembly) and the
    span-token lower bound (would require a different, unimplemented selector).
    """
    required = [g for g in case.evidence_groups if g.requirement == "REQUIRED"]
    if not required:
        raise ValueError("cannot classify a case without required evidence")
    counter = ApproximateTokenCounter()
    states: set[tuple[frozenset[str], frozenset[tuple[str, int]]]] = {(frozenset(), frozenset())}
    for group in required:
        options = []
        for alternative in group.alternatives:
            ids = frozenset(s.chunk_id for s in alternative.spans)
            if available is not None and not ids <= available:
                continue
            positions: set[tuple[str, int]] = set()
            for span in alternative.spans:
                c = chunks[span.chunk_id]
                if (
                    c.tenant_id != case.tenant_id
                    or c.metadata["source_path"] != span.source
                    or span.end > len(c.content)
                    or c.content[span.start : span.end] != span.excerpt
                ):
                    raise ValueError("invalid evidence locator in feasibility oracle")
                positions.update(
                    (c.chunk_id, i)
                    for i, (start, end) in enumerate(counter.spans(c.content))
                    if start < span.end and end > span.start
                )
            options.append((ids, frozenset(positions)))
        if len(states) * len(options) > 100_000:
            raise ValueError(
                "oracle state bound exceeded; do not replace exact counts with guesses"
            )
        states = {
            (old_ids | ids, old_tokens | positions)
            for old_ids, old_tokens in states
            for ids, positions in options
        }
    if not states:
        return {"whole_chunk_tokens": None, "span_tokens": None, "stratum": "UNAVAILABLE"}
    cost = min(sum(chunks[i].token_count for i in ids) for ids, _ in states)
    span_cost = min(len(positions) for _, positions in states)
    stratum = (
        "EASY"
        if cost <= 512
        else "MEDIUM"
        if cost <= 1024
        else "HARD"
        if cost <= 2048
        else "VERY_HARD"
    )
    return {"whole_chunk_tokens": cost, "span_tokens": span_cost, "stratum": stratum}


def failure_decomposition(
    case: EvidenceCase,
    chunks: Mapping[str, Chunk],
    retrieved: Sequence[SelectionCandidate],
    selected: Sequence[SelectionCandidate],
    budget: int,
    *,
    disputed: bool = False,
) -> dict[str, object]:
    """Conservative, overlapping diagnoses; never infer semantic conflict from text alone."""
    if budget < 0:
        raise ValueError("negative budget")
    if disputed:
        return {"primary": "ANNOTATION_AMBIGUITY", "flags": ["ANNOTATION_AMBIGUITY"]}
    corpus_cost = feasibility(case, chunks)["whole_chunk_tokens"]
    original = {c.identity: c for c in retrieved}
    if len(original) != len(retrieved) or len({c.identity for c in selected}) != len(selected):
        raise ValueError("duplicate candidate identity")
    for candidate in selected:
        if candidate.identity not in original:
            raise ValueError("selected identity was not retrieved")
        chunk = chunks[candidate.identity]
        if (
            candidate != original[candidate.identity]
            or candidate.content != chunk.content
            or candidate.tokens != chunk.token_count
        ):
            return {"primary": "OTHER", "flags": ["REPRESENTATION_ERROR"], "dimension": "E"}
    for candidate in retrieved:
        chunk = chunks[candidate.identity]
        if chunk.tenant_id != case.tenant_id or candidate.source != chunk.metadata["source_path"]:
            raise ValueError("cross-tenant or source provenance mismatch")
        if candidate.content != chunk.content or candidate.tokens != chunk.token_count:
            return {"primary": "OTHER", "flags": ["REPRESENTATION_ERROR"], "dimension": "E"}
    if sum(c.tokens for c in selected) > budget:
        raise ValueError("selected packet exceeds budget")
    selected_ids = {c.identity for c in selected}
    retrieved_ids = set(original)
    required = [g for g in case.evidence_groups if g.requirement == "REQUIRED"]
    missing = [
        g
        for g in required
        if not any({s.chunk_id for s in a.spans} <= selected_ids for a in g.alternatives)
    ]
    if not missing:
        return {"primary": "SELECTED", "flags": [], "dimension": "C"}
    retrieval_cost = feasibility(case, chunks, retrieved_ids)["whole_chunk_tokens"]
    sources = {c.source for c in retrieved}
    wrong_chunk = any(
        any(
            all(s.source in sources for s in a.spans)
            and not {s.chunk_id for s in a.spans} <= retrieved_ids
            for a in g.alternatives
        )
        for g in missing
    )
    texts = {c.content for c in selected}
    provenance_loss = any(
        any(all(chunks[s.chunk_id].content in texts for s in a.spans) for a in g.alternatives)
        for g in missing
    )
    if corpus_cost is not None and int(corpus_cost) > budget:
        primary = "INSUFFICIENT_BUDGET"
    elif retrieval_cost is None:
        primary = "WRONG_CHUNK" if wrong_chunk else "RETRIEVAL_MISS"
    elif int(retrieval_cost) > budget:
        primary = "BUDGET_DROP"
    else:
        primary = "PACKING_ORDER"
    flags = [primary]
    if retrieval_cost is None and "RETRIEVAL_MISS" not in flags:
        flags.append("RETRIEVAL_MISS")
    if wrong_chunk and "WRONG_CHUNK" not in flags:
        flags.append("WRONG_CHUNK")
    if provenance_loss:
        flags.append("PROVENANCE_CONFLICT")
    retained = set(selected_ids)
    duplicate_waste = 0
    for candidate in reversed(selected):
        same_text = any(
            c.identity != candidate.identity
            and c.identity in retained
            and c.content == candidate.content
            for c in selected
        )
        remaining = retained - {candidate.identity}
        involved = [
            g
            for g in case.evidence_groups
            if any(s.chunk_id == candidate.identity for a in g.alternatives for s in a.spans)
        ]
        # Preserve complete alternatives AND never throw away useful partial labels.
        safe = all(
            any({s.chunk_id for s in a.spans} <= remaining for a in g.alternatives)
            for g in involved
        )
        if same_text and safe:
            duplicate_waste += candidate.tokens
            retained = remaining
    if duplicate_waste:
        flags.append("DUPLICATE_WASTE")
    return {
        "safe_duplicate_tokens": duplicate_waste,
        "primary": primary,
        "flags": flags,
        "missing_groups": [g.group_id for g in missing],
        "corpus_min_tokens": corpus_cost,
        "retrieved_min_tokens": retrieval_cost,
        "dimension": "A/D" if retrieval_cost is None else "B",
    }
