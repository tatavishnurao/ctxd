"""Offline, exact-span evidence evaluation; never imported by production retrieval."""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ctxd.app.evals.context_selection import SelectionCandidate, validate_candidates
from ctxd.app.evals.retrieval import ndcg_at_k, recall_at_k, reciprocal_rank
from ctxd.app.ingestion.chunking import ApproximateTokenCounter, StructureAwareChunker
from ctxd.app.models.domain import Chunk, Document


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSpan(StrictModel):
    source: str
    chunk_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    excerpt: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_range(self) -> Self:
        if self.end <= self.start:
            raise ValueError("span must be nonempty, half-open character offsets")
        return self


class EvidenceAlternative(StrictModel):
    # Every span in ONE alternative must survive; alternatives are interchangeable.
    spans: list[EvidenceSpan] = Field(min_length=1)


class EvidenceGroup(StrictModel):
    group_id: str
    requirement: Literal["REQUIRED", "SUPPORTING", "OPTIONAL"]
    alternatives: list[EvidenceAlternative] = Field(min_length=1)


class EvidenceCase(StrictModel):
    case_id: str
    query: str = Field(min_length=1)
    tenant_id: str
    template_group: str
    evidence_groups: list[EvidenceGroup] = Field(default_factory=list)
    status: Literal["VERIFIED_FIXTURE", "NEEDS_HUMAN_REVIEW"]
    answerability_notes: str
    budget_pressure_class: str

    @model_validator(mode="after")
    def group_contract(self) -> Self:
        ids = [g.group_id for g in self.evidence_groups]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate group ID")
        if self.status != "NEEDS_HUMAN_REVIEW" and not any(
            g.requirement == "REQUIRED" for g in self.evidence_groups
        ):
            raise ValueError("at least one required group; no vacuous answerability")
        return self


class EvidenceCorpus(StrictModel):
    provenance: str
    documents: list[Document]
    chunks: list[Chunk]
    cases: list[EvidenceCase]

    @model_validator(mode="after")
    def validate_locators(self) -> Self:
        chunks = {c.chunk_id: c for c in self.chunks}
        if len(chunks) != len(self.chunks):
            raise ValueError("duplicate chunk identity")
        regenerated = [c for d in self.documents for c in StructureAwareChunker().chunk(d)]
        if {c.chunk_id: c for c in regenerated} != chunks:
            raise ValueError("chunks do not match production chunking of corpus documents")
        if len({c.case_id for c in self.cases}) != len(self.cases):
            raise ValueError("duplicate case ID")
        document_keys = [(d.tenant_id, d.source_path) for d in self.documents]
        if len(set(document_keys)) != len(document_keys):
            raise ValueError("duplicate tenant/source document")
        for case in self.cases:
            for group in case.evidence_groups:
                for alternative in group.alternatives:
                    for span in alternative.spans:
                        chunk = chunks.get(span.chunk_id)
                        if chunk is None or chunk.tenant_id != case.tenant_id:
                            raise ValueError("unknown or cross-tenant evidence chunk")
                        if chunk.metadata["source_path"] != span.source:
                            raise ValueError("source locator mismatch")
                        if (
                            span.end > len(chunk.content)
                            or chunk.content[span.start : span.end] != span.excerpt
                        ):
                            raise ValueError("evidence span does not match corpus text")
        return self


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def grouped_split(cases: Sequence[EvidenceCase], seed: int) -> dict[str, str]:
    groups = sorted({c.template_group for c in cases})
    if len(groups) < 3:
        raise ValueError("need at least three template groups")
    random.Random(seed).shuffle(groups)
    holdout = set(groups[: max(1, len(groups) // 3)])
    result = {c.case_id: "holdout" if c.template_group in holdout else "development" for c in cases}
    validate_split(cases, result)
    return result


def validate_split(cases: Sequence[EvidenceCase], assignments: Mapping[str, str]) -> None:
    if set(assignments) != {c.case_id for c in cases}:
        raise ValueError("split case identities differ")
    groups: dict[str, set[str]] = defaultdict(set)
    queries: dict[str, set[str]] = defaultdict(set)
    sources: dict[tuple[str, str], set[str]] = defaultdict(set)
    for case in cases:
        partition = assignments[case.case_id]
        if partition not in {"development", "holdout"}:
            raise ValueError("unknown partition")
        groups[case.template_group].add(partition)
        queries[" ".join(case.query.casefold().split())].add(partition)
        for group in case.evidence_groups:
            for alternative in group.alternatives:
                for span in alternative.spans:
                    sources[case.tenant_id, span.source].add(partition)
    if any(len(v) > 1 for v in [*groups.values(), *queries.values(), *sources.values()]):
        raise ValueError("template, duplicate-query or evidence-source leakage")


def evaluate_evidence(
    case: EvidenceCase,
    retrieved: Sequence[SelectionCandidate],
    selected: Sequence[SelectionCandidate],
    chunks: Mapping[str, Chunk],
) -> dict[str, float]:
    """CTXD metrics use production approximate tokens, not model/BPE tokens.

    Precision counts the union of labeled span tokens. Redundancy counts labeled
    span tokens beyond the cheapest complete alternative per group; it does not
    infer semantic redundancy in unlabeled prose. Distractor tokens belong to
    chunks with no labeled span. These fractions are not a disjoint partition.
    """
    if case.status != "VERIFIED_FIXTURE":
        raise ValueError("unreviewed case cannot receive an answerability score")
    validate_candidates(retrieved)
    validate_candidates(selected)
    original = {c.identity: c for c in retrieved}
    if any(original.get(c.identity) != c for c in selected):
        raise ValueError("selection changed candidates")
    for candidate in retrieved:
        chunk = chunks[candidate.identity]
        if (
            chunk.tenant_id != case.tenant_id
            or candidate.content != chunk.content
            or candidate.tokens != chunk.token_count
            or candidate.source != chunk.metadata["source_path"]
        ):
            raise ValueError("candidate provenance or tenant mismatch")
    counter = ApproximateTokenCounter()
    selected_ids = {c.identity for c in selected}
    retrieved_ids = set(original)
    covered: dict[str, bool] = {}
    retrieved_covered: dict[str, bool] = {}
    labeled: set[tuple[str, int]] = set()
    necessary: set[tuple[str, int]] = set()
    relevant_chunks: set[str] = set()
    required_chunks: set[str] = set()
    for group in case.evidence_groups:
        covered[group.group_id] = False
        retrieved_covered[group.group_id] = False
        complete: list[set[tuple[str, int]]] = []
        group_labeled: set[tuple[str, int]] = set()
        for alternative in group.alternatives:
            ids = {s.chunk_id for s in alternative.spans}
            relevant_chunks.update(ids)
            if group.requirement == "REQUIRED":
                required_chunks.update(ids)
            retrieved_covered[group.group_id] |= ids <= retrieved_ids
            all_tokens: set[tuple[str, int]] = set()
            for span in alternative.spans:
                chunk = chunks[span.chunk_id]
                # Recheck at evaluation boundary; annotations may not have come from Corpus.
                if (
                    chunk.tenant_id != case.tenant_id
                    or chunk.metadata["source_path"] != span.source
                    or span.end > len(chunk.content)
                    or chunk.content[span.start : span.end] != span.excerpt
                ):
                    raise ValueError("span drift or provenance mismatch")
                all_tokens.update(
                    (span.chunk_id, i)
                    for i, (start, end) in enumerate(counter.spans(chunk.content))
                    if start < span.end and end > span.start
                )
            group_labeled.update(t for t in all_tokens if t[0] in selected_ids)
            if ids <= selected_ids:
                covered[group.group_id] = True
                complete.append(all_tokens)
        labeled.update(group_labeled)
        if complete:
            cheapest = sorted(complete, key=lambda s: (len(s), sorted(s)))[0]
            necessary.update(cheapest)
        else:
            # Partial evidence is useful progress, not redundant solely for being incomplete.
            necessary.update(group_labeled)
    required = [g.group_id for g in case.evidence_groups if g.requirement == "REQUIRED"]
    supporting = [g.group_id for g in case.evidence_groups if g.requirement == "SUPPORTING"]
    total = sum(c.tokens for c in selected)
    paths = [c.identity for c in selected]
    result = {
        "required_recall": sum(covered[g] for g in required) / len(required),
        "full_answerability": float(all(covered[g] for g in required)),
        "supporting_recall": sum(covered[g] for g in supporting) / len(supporting)
        if supporting
        else 0.0,
        "supporting_applicable": float(bool(supporting)),
        "retrieved_required_recall": sum(retrieved_covered[g] for g in required) / len(required),
        "selected_tokens": float(total),
        "span_token_precision": len(labeled) / total if total else 0.0,
        "redundant_span_tokens": float(len(labeled - necessary)),
        "redundant_token_fraction": len(labeled - necessary) / total if total else 0.0,
        "distractor_tokens": float(
            sum(c.tokens for c in selected if c.identity not in relevant_chunks)
        ),
        "required_groups_per_1k_tokens": sum(covered[g] for g in required) * 1000 / total
        if total
        else 0.0,
        "selected_count": float(len(selected)),
        "mrr": reciprocal_rank(paths, required_chunks),
        "ndcg_at_5": ndcg_at_k(paths, required_chunks, 5),
        "ndcg_at_10": ndcg_at_k(paths, required_chunks, 10),
    }
    result["distractor_token_fraction"] = result["distractor_tokens"] / total if total else 0.0
    for k in (1, 5, 10):
        result[f"recall_at_{k}"] = recall_at_k(paths, required_chunks, k)
    return result


def clustered_bootstrap(
    deltas: Mapping[str, Sequence[float]], seed: int = 902026, resamples: int = 2000
) -> dict[str, float]:
    """Resample whole template groups; return case-weighted mean delta interval."""
    if not deltas or any(not values for values in deltas.values()) or resamples < 2000:
        raise ValueError("nonempty clusters and >=2000 resamples required")
    groups = sorted(deltas)
    rng = random.Random(seed)
    samples = []
    for _ in range(resamples):
        values = [v for _ in groups for v in deltas[rng.choice(groups)]]
        samples.append(sum(values) / len(values))
    samples.sort()
    values = [v for g in groups for v in deltas[g]]
    return {
        "point": sum(values) / len(values),
        "low": samples[int(0.025 * (resamples - 1))],
        "high": samples[int(0.975 * (resamples - 1))],
        "clusters": float(len(groups)),
        "resamples": float(resamples),
    }
