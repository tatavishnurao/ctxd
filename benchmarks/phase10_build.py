"""Build pinned real-source review candidates; never retrieves or scores a holdout."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import subprocess
from collections import Counter
from pathlib import Path

from ctxd.app.evals.evidence import (
    EvidenceAlternative,
    EvidenceCase,
    EvidenceCorpus,
    EvidenceGroup,
    EvidenceSpan,
    digest,
    grouped_split,
)
from ctxd.app.evals.review import ReviewRecord, ReviewState, feasibility
from ctxd.app.ingestion.chunking import StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.models.domain import DocumentSourceType

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = (256, 512, 1024, 2048, 4096)
LABEL = "PROVISIONAL — NOT INDEPENDENTLY REVIEWED"
SOURCES = {
    "api": "ctxd/app/api/routes.py",
    "middleware": "ctxd/app/api/middleware.py",
    "domain": "ctxd/app/models/domain.py",
    "settings": "ctxd/app/config/settings.py",
    "runtime": "ctxd/app/runtime.py",
    "loaders": "ctxd/app/ingestion/loaders.py",
    "ingest": "ctxd/app/ingestion/service.py",
    "chunking": "ctxd/app/ingestion/chunking.py",
    "hybrid": "ctxd/app/retrieval/hybrid.py",
    "lexical": "ctxd/app/retrieval/lexical.py",
    "semantic": "ctxd/app/retrieval/semantic.py",
    "postgres": "ctxd/app/storage/postgres.py",
    "memory": "ctxd/app/storage/documents.py",
    "rankbase": "ctxd/app/reranking/base.py",
    "reranker": "ctxd/app/reranking/retriever.py",
    "flash": "ctxd/app/reranking/flashrank.py",
    "logging": "ctxd/app/observability/logging.py",
    "tracing": "ctxd/app/observability/tracing.py",
    "synapse": "ctxd/app/integrations/synapse/evaluator.py",
    "migration1": "migrations/versions/0001_phase3.py",
    "migration2": "migrations/versions/0002_phase4_embeddings.py",
    "assembler": "ctxd/app/context/assembler.py",
    "evidence": "ctxd/app/evals/evidence.py",
    "evalretrieval": "ctxd/app/evals/retrieval.py",
    "readme": "README.md",
}


def write_new(path: str, value: object, root: Path = ROOT) -> None:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    with (root / path).open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True, ensure_ascii=False)
        output.write("\n")


def build(authoring: Path | None = None, author_id: str = "phase10-assistant") -> dict[str, object]:
    history = json.loads((ROOT / "benchmarks/phase10_history_freeze.json").read_text())
    base = history["base_sha"]
    documents = []
    provenance = []
    for alias, path in SOURCES.items():
        raw = subprocess.check_output(["git", "show", f"{base}:{path}"], cwd=ROOT)
        sha = hashlib.sha256(raw).hexdigest()
        if sha != history["tracked_base_sha256"][path]:
            raise ValueError(f"source hash mismatch: {path}")
        documents.append(
            document_from_content(
                content=raw.decode(),
                source_path=path,
                tenant_id="phase10-technical",
                source_type=DocumentSourceType.MARKDOWN
                if path.endswith(".md")
                else DocumentSourceType.TEXT,
                metadata={"base_sha": base, "source_sha256": sha, "source_alias": alias},
            )
        )
        provenance.append(
            {
                "source": path,
                "git_revision": base,
                "sha256": sha,
                "url": f"https://github.com/tatavishnurao/ctxd/blob/{base}/{path}",
                "source_type": "repository_documentation"
                if path.endswith(".md")
                else "repository_code",
                "permission_basis": "User-authorized local benchmark; no scraping",
                "license": "No root LICENSE at pinned revision; redistribution rights not inferred",
                "transformation": (
                    "Verbatim UTF-8; .py ingested as text content, not file-loader extension"
                ),
            }
        )
    chunks = [chunk for document in documents for chunk in StructureAwareChunker().chunk(document)]
    by_id = {c.chunk_id: c for c in chunks}
    by_source = {d.source_path: d for d in documents}
    locators = {}

    def locate(atom: str) -> list[EvidenceSpan]:
        alias, excerpt = atom.split("@", 1)
        source = SOURCES[alias]
        text = by_source[source].content
        # Prefer a complete code line, then an exact substring. Repeated physical
        # occurrences use the first occurrence, never retrieval ranks. Reviewers
        # see the source line and must check its semantic locality.
        lines = text.splitlines(keepends=True)
        offset = 0
        start = -1
        for line in lines:
            if line.strip() == excerpt:
                start = offset + line.index(excerpt)
                break
            offset += len(line)
        if start < 0:
            start = text.find(excerpt)
        if start < 0:
            raise ValueError(f"missing source excerpt: {atom}")
        line_number = text.count("\n", 0, start) + 1
        found = []
        for chunk in chunks:
            if (
                chunk.metadata["source_path"] == source
                and excerpt in chunk.content
                and chunk.start_line <= line_number <= chunk.end_line
            ):
                local = chunk.content.index(excerpt)
                found.append(
                    EvidenceSpan(
                        source=source,
                        chunk_id=chunk.chunk_id,
                        start=local,
                        end=local + len(excerpt),
                        excerpt=excerpt,
                    )
                )
        if not found:
            raise ValueError(f"excerpt crosses production chunk boundary: {atom}")
        locators[atom] = {
            "source": source,
            "original_line": line_number,
            "original_char_start": start,
            "original_char_end": start + len(excerpt),
        }
        return found

    with (authoring or ROOT / "evals/phase10_authoring.tsv").open() as stream:
        specs = list(csv.DictReader(stream, delimiter="\t"))
    cases = []
    taxonomy = {}
    for index, spec in enumerate(specs, 1):
        groups = []
        for requirement in ("REQUIRED", "SUPPORTING", "OPTIONAL"):
            expressions = spec.get(f"{requirement.lower()}_evidence")
            if not expressions:
                continue
            for ordinal, expression in enumerate(expressions.split(" ~~ "), 1):
                alternatives = []
                for alternative in expression.split(" || "):
                    atoms = [locate(atom) for atom in alternative.split(" && ")]
                    alternatives.extend(
                        EvidenceAlternative(spans=list(spans))
                        for spans in itertools.product(*atoms)
                    )
                groups.append(
                    EvidenceGroup(
                        group_id=f"{requirement.lower()}-{ordinal}",
                        requirement=requirement,
                        alternatives=alternatives,
                    )
                )
        case = EvidenceCase(
            case_id=f"phase10-{index:03}",
            query=spec["query"],
            tenant_id="phase10-technical",
            template_group=spec["family"].strip(),
            evidence_groups=groups,
            status="NEEDS_HUMAN_REVIEW",
            answerability_notes=(
                "Agent-authored proposed code/documentation evidence. Exact text verified; "
                "Semantic sufficiency, minimality, alternatives and clarity await human review. "
                "Behavior is at the pinned revision, not a claim about other versions. "
                "All spans within an alternative are jointly required; groups are ANDed. "
                "Supporting/optional labels are proposals, not human-verified judgments."
            ),
            budget_pressure_class="PENDING_MEASUREMENT",
        )
        measured = feasibility(case, by_id)
        case.budget_pressure_class = str(measured["stratum"])
        cases.append(case)
        taxonomy[case.case_id] = {
            "query_kind": spec["kind"],
            "feasibility": measured,
            "author": author_id,
            "human_review_status": "UNREVIEWED",
        }
    corpus = EvidenceCorpus(
        provenance=(
            LABEL + "; authentic pinned source text, agent-authored questions; "
            "one repository, not production traffic or externally sourced technical breadth"
        ),
        documents=documents,
        chunks=chunks,
        cases=cases,
    )
    dataset = corpus.model_dump(mode="json")
    dataset_sha = digest(dataset)
    assignments = grouped_split(cases, seed=1002026)
    reviews = ReviewState(
        dataset_sha256=dataset_sha,
        records=[
            ReviewRecord(
                case_id=c.case_id,
                case_sha256=digest(c.model_dump(mode="json")),
                author_id=author_id,
            )
            for c in cases
        ],
    )
    distributions = {}
    for partition in ("all", "development", "holdout"):
        subset = [c for c in cases if partition == "all" or assignments[c.case_id] == partition]
        costs = [int(taxonomy[c.case_id]["feasibility"]["whole_chunk_tokens"]) for c in subset]
        distributions[partition] = {
            "cases": len(subset),
            "families": sorted({c.template_group for c in subset}),
            "strata": dict(Counter(c.budget_pressure_class for c in subset)),
            "whole_chunk_min_range": [min(costs), max(costs)],
            "feasible_at_budget": {str(b): sum(cost <= b for cost in costs) for b in BUDGETS},
            "query_kinds": dict(Counter(taxonomy[c.case_id]["query_kind"] for c in subset)),
        }
    return {
        "dataset": dataset,
        "dataset_sha256": dataset_sha,
        "provenance": provenance,
        "taxonomy": taxonomy,
        "assignments": assignments,
        "reviews": reviews.model_dump(mode="json"),
        "distributions": distributions,
        "source_locators": locators,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authoring", type=Path)
    parser.add_argument("--author-id", default="phase10-assistant")
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    artifact = build(args.authoring, args.author_id)
    outputs = {
        "evals/phase10_evidence_cases.json": artifact["dataset"],
        "evals/phase10_source_manifest.json": artifact["provenance"],
        "evals/phase10_case_metadata.json": artifact["taxonomy"],
        "evals/phase10_source_locators.json": artifact["source_locators"],
        "evals/phase10_review_state.json": artifact["reviews"],
        "evals/phase10_split_manifest.json": {
            "seed": 1002026,
            "dataset_sha256": artifact["dataset_sha256"],
            "assignments": artifact["assignments"],
            "split_sha256": digest(artifact["assignments"]),
            "status": "FROZEN_PRE_REVIEW_ASSIGNMENT; canonical scoring blocked",
            "selection": "source/template-group split; no outcome access or split search",
            "holdout_exposure": "labels visible for authoring/review; zero retrieval outcomes",
        },
        "benchmarks/phase10_feasibility.json": {
            "label": LABEL,
            "definition": "Exact REQUIRED whole-chunk union costs; not retrieval scores",
            "strata": {
                "EASY": "<=512",
                "MEDIUM": "513..1024",
                "HARD": "1025..2048",
                "VERY_HARD": ">2048",
            },
            "distributions": artifact["distributions"],
        },
    }
    if args.output_root.resolve() != ROOT.resolve():
        for name in ("phase10_protocol.json", "phase10_history_freeze.json"):
            outputs[f"benchmarks/{name}"] = json.loads((ROOT / "benchmarks" / name).read_text())
    if any((args.output_root / path).exists() for path in outputs):
        raise FileExistsError(
            "Phase 10 artifacts already exist; use a versioned revision, never overwrite"
        )
    for path, value in outputs.items():
        write_new(path, value, root=args.output_root)
    print(json.dumps(artifact["distributions"], indent=2))


if __name__ == "__main__":
    main()
