"""Curate a new draft revision from exact pinned paragraphs; no ranking/model access."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import re
from pathlib import Path

from ctxd.app.evals.evidence import (
    EvidenceAlternative, EvidenceCase, EvidenceCorpus, EvidenceGroup, EvidenceSpan, digest,
)
from ctxd.app.evals.review import feasibility
from ctxd.app.ingestion.chunking import StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.models.domain import DocumentSourceType

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = (256, 512, 1024, 2048, 4096)
RETAIN = {1, 2, 4, 8, 9, 14, 18, 23, 24, 27, 30, 31, 36, 37, 52, 53, 58, 67, 74, 101,
          38, 42, 44, 50, 51, 60, 61, 79, 91, 92, 34, 63, 64, 72}


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")


def budget_class(tokens: int) -> str:
    if tokens <= 512:
        return "EASY"
    if tokens <= 1024:
        return "MEDIUM"
    if tokens <= 2048:
        return "HARD"
    if tokens <= 4096:
        return "VERY_HARD"
    return "INFEASIBLE"


def build() -> tuple[EvidenceCorpus, dict, list, dict]:
    legacy = EvidenceCorpus.model_validate_json((ROOT / "evals/phase10_evidence_cases.json").read_text())
    old_meta = json.loads((ROOT / "evals/phase10_case_metadata.json").read_text())
    old_sources = {s["source"]: s for s in json.loads((ROOT / "evals/phase10_source_manifest.json").read_text())}
    retained = [c for c in legacy.cases if int(c.case_id.rsplit("-", 1)[1]) in RETAIN]
    needed = {s.source for c in retained for g in c.evidence_groups for a in g.alternatives for s in a.spans}
    documents = []
    sources = []
    for document in legacy.documents:
        if document.source_path not in needed:
            continue
        documents.append(document_from_content(content=document.content, source_path=document.source_path,
            source_type=document.source_type, tenant_id="phase10b-technical", metadata=document.metadata))
        old = old_sources[document.source_path]
        sources.append({"source_path": document.source_path, "source_id": document.source_path,
            "revision": old["git_revision"], "sha256": old["sha256"], "url": old["url"],
            "version": old["git_revision"], "source_type": old["source_type"],
            "license": old["license"], "permission_basis": old["permission_basis"],
            "snapshot": "evals/phase10_evidence_cases.json (embedded document)"})
    external = json.loads((ROOT / "evals/phase10b_external_sources.json").read_text())
    text_by_alias = {}
    for source in external["sources"]:
        raw = (ROOT / source["snapshot"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("pinned source checksum mismatch")
        text = raw.decode("utf-8")
        text_by_alias[source["source_id"]] = (source, text)
        documents.append(document_from_content(content=text, source_path=source["source_path"],
            source_type=DocumentSourceType.TEXT, tenant_id="phase10b-technical",
            metadata={"revision": source["revision"], "source_sha256": source["sha256"]}))
        sources.append(source)
    chunks = [c for d in documents for c in StructureAwareChunker().chunk(d)]
    by_id = {c.chunk_id: c for c in chunks}
    by_path_ordinal = {(str(c.metadata["source_path"]), c.ordinal): c for c in chunks}
    old_chunks = {c.chunk_id: c for c in legacy.chunks}
    cases = []
    metadata = {}
    for old in retained:
        data = old.model_dump(mode="json")
        data["case_id"] = old.case_id.replace("phase10-", "phase10b-legacy-")
        data["tenant_id"] = "phase10b-technical"
        data["template_group"] = "ctxd-" + old.template_group
        for group in data["evidence_groups"]:
            for alternative in group["alternatives"]:
                for span in alternative["spans"]:
                    previous = old_chunks[span["chunk_id"]]
                    current = by_path_ordinal[(span["source"], previous.ordinal)]
                    if previous.content != current.content:
                        raise ValueError("legacy evidence representation changed")
                    span["chunk_id"] = current.chunk_id
        case = EvidenceCase.model_validate(data)
        cases.append(case)
        metadata[case.case_id] = {"origin_case_id": old.case_id, "change": "RETAINED",
            "author_id": "phase10b-assistant", "author_status": "DRAFT",
            "query_type": old_meta[old.case_id]["query_kind"],
            "paraphrase_family": case.template_group,
            "why": "Retained concrete runtime/diagnostic control; balances larger documentation tasks.",
            "provenance_reason": "", "challenge": False,
            "fact_keys": sorted({digest((s.source, s.excerpt)) for g in case.evidence_groups
                                  if g.requirement == "REQUIRED" for a in g.alternatives for s in a.spans})}
    locators = {}

    def locate(atom: str) -> list[EvidenceSpan]:
        alias, number = atom.rsplit(":", 1)
        source, text = text_by_alias[alias]
        blocks = re.split(r"\n[ \t]*\n", text)
        index = int(number)
        excerpt = blocks[index].strip()
        separators = list(re.finditer(r"\n[ \t]*\n", text))
        block_start = separators[index - 1].end() if index else 0
        absolute = block_start + blocks[index].index(excerpt)
        line = text.count("\n", 0, absolute) + 1
        matches = []
        for chunk in chunks:
            if (chunk.metadata["source_path"] == source["source_path"]
                    and chunk.start_line <= line <= chunk.end_line and excerpt in chunk.content):
                start = chunk.content.index(excerpt)
                matches.append(EvidenceSpan(source=source["source_path"], chunk_id=chunk.chunk_id,
                    start=start, end=start + len(excerpt), excerpt=excerpt))
        if not matches:
            raise ValueError(f"paragraph cannot be located intact in production chunks: {atom}")
        locators[atom] = {"source": source["source_path"], "paragraph_index": index,
                          "start": absolute, "end": absolute + len(excerpt), "line": line}
        return matches

    specs = []
    for path in sorted((ROOT / "evals").glob("phase10b_authoring*.tsv")):
        with path.open() as stream:
            specs.extend(csv.DictReader(stream, delimiter="\t"))
    for index, spec in enumerate(specs, 1):
        groups = []
        for requirement, column in (("REQUIRED", "required"), ("SUPPORTING", "supporting")):
            for ordinal, expression in enumerate(filter(None, spec[column].split(";")), 1):
                alternatives = []
                for expression_path in expression.split("|"):
                    atoms = [locate(atom) for atom in expression_path.split("&")]
                    alternatives.extend(EvidenceAlternative(spans=list(spans))
                                        for spans in itertools.product(*atoms))
                groups.append(EvidenceGroup(group_id=f"{requirement.lower()}-{ordinal}",
                                            requirement=requirement, alternatives=alternatives))
        case = EvidenceCase(case_id=f"phase10b-new-{index:03}",
            query="Under the pinned CPython 3.13.0 documentation: " + spec["query"],
            tenant_id="phase10b-technical", template_group="python-" + spec["family"],
            evidence_groups=groups, status="NEEDS_HUMAN_REVIEW",
            answerability_notes="DRAFT. Every REQUIRED group is necessary; spans within an alternative "
                "are jointly required. Alternatives are OR. Human review must check minimality, "
                "missing alternatives and paragraph sufficiency. Not a claim about newer Python versions.",
            budget_pressure_class="PENDING")
        cases.append(case)
        metadata[case.case_id] = {"origin_case_id": None, "change": "NEW",
            "author_id": "phase10b-assistant", "author_status": "DRAFT",
            "query_type": spec["query_type"], "paraphrase_family": case.template_group,
            "why": spec["why"], "provenance_reason": spec["provenance_reason"], "challenge": False,
            "fact_keys": sorted({atom for group in spec["required"].split(";")
                                 for path in group.split("|") for atom in path.split("&")})}
    for case in cases:
        measured = feasibility(case, by_id)
        cost = int(measured["whole_chunk_tokens"])
        case.budget_pressure_class = budget_class(cost)
        metadata[case.case_id]["budget"] = {"span_only_minimum": measured["span_tokens"],
            "chunk_realizable_minimum": cost, "stratum": case.budget_pressure_class,
            "first_feasible_budget": next((b for b in BUDGETS if cost <= b), None)}
    corpus = EvidenceCorpus(provenance="PROVISIONAL — PRE-REVIEW. Authentic pinned sources; "
        "agent-authored DRAFT questions and labels. Zero independent review or retrieval scoring.",
        documents=documents, chunks=chunks, cases=cases)
    return corpus, metadata, sources, locators


if __name__ == "__main__":
    from collections import Counter
    corpus, metadata, _, _ = build()
    print(Counter(c.budget_pressure_class for c in corpus.cases))
    for case in corpus.cases:
        if case.case_id.startswith("phase10b-new"):
            print(case.case_id, case.template_group, metadata[case.case_id]["budget"])
