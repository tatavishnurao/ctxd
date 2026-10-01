"""Author a synthetic, exact-span-verifiable corpus BEFORE running any retriever."""

from __future__ import annotations

import json
from pathlib import Path

from ctxd.app.evals.evidence import EvidenceCorpus, digest, grouped_split
from ctxd.app.ingestion.chunking import ApproximateTokenCounter, StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.models.domain import DocumentSourceType

# Each family has its own source facts and query construction. Paraphrases never split.
FAMILIES = [
    (
        "timeout",
        ["The amber RPC deadline is 37 seconds."],
        ["What is the amber RPC deadline?", "How many seconds may an amber RPC run?"],
        80,
    ),
    (
        "rollback",
        [
            "Cedar rollback requires a sealed snapshot.",
            "Cedar rollback requires two operator approvals.",
        ],
        [
            "Which two prerequisites must Cedar rollback satisfy?",
            "What must be ready before a Cedar rollback can proceed?",
        ],
        380,
    ),
    (
        "error_contract",
        [
            "Birch returns HTTP 409 for an active lease conflict.",
            "Birch returns HTTP 422 for an invalid lease shape.",
        ],
        [
            "How does Birch distinguish conflicting and malformed leases in HTTP responses?",
            "Map active lease conflict and invalid lease shape to Birch response codes.",
        ],
        250,
    ),
    (
        "retention",
        [
            "Elm retains live audit records for 19 days.",
            "Elm retains archived audit records for 73 days.",
        ],
        [
            "Compare Elm live and archived audit retention periods.",
            "How long are live versus archived Elm audit records kept?",
        ],
        550,
    ),
    (
        "credential",
        [
            "Fir signing key K7 is scoped to tenant north.",
            "Fir signing key K7 cannot authorize tenant south.",
        ],
        [
            "Can Fir key K7 authorize tenant south, and what scope does it have?",
            "State the tenant scope and cross-tenant restriction of Fir signing key K7.",
        ],
        550,
    ),
    (
        "range",
        ["Hazel workers must number at least 3.", "Hazel workers must number at most 11."],
        [
            "What is the allowed Hazel worker count range?",
            "Give both bounds on the Hazel worker pool.",
        ],
        380,
    ),
    (
        "procedure",
        [
            f"Iris recovery step {i} is {action}."
            for i, action in enumerate(
                [
                    "isolate traffic",
                    "seal journals",
                    "copy checkpoint",
                    "verify checksum",
                    "replay journal",
                    "probe reads",
                    "enable writes",
                    "restore traffic",
                ],
                1,
            )
        ],
        [
            "List all eight Iris recovery steps in order.",
            "What is the complete ordered Iris recovery procedure?",
        ],
        550,
    ),
    (
        "event",
        [
            "Juniper emits ready only after quorum acknowledges.",
            "Juniper suppresses ready while maintenance is active.",
        ],
        [
            "Under what condition does Juniper emit ready and when is it suppressed?",
            "Explain the acknowledgement trigger and maintenance exception for Juniper ready.",
        ],
        550,
    ),
    (
        "schema",
        [
            f"Larch audit field {name} is mandatory."
            for name in ["actor", "action", "resource", "timestamp", "outcome", "signature"]
        ],
        [
            "Which six fields must a Larch audit record contain?",
            "Enumerate the mandatory Larch audit schema fields.",
        ],
        380,
    ),
    (
        "precedence",
        [
            "Maple chooses the command line region before the environment region.",
            "Maple chooses the environment region before the file region.",
        ],
        [
            "Order the three Maple region configuration sources by precedence.",
            "How do command line, environment, and file regions override one another in Maple?",
        ],
        250,
    ),
    (
        "idempotency",
        [
            "Oak deduplicates requests using operation_key.",
            "Oak deduplication expires after 23 hours.",
        ],
        [
            "Identify the Oak request deduplication key and its validity duration.",
            "Which identifier prevents repeated Oak operations, and for how long?",
        ],
        80,
    ),
    (
        "compatibility",
        ["Pine client v4 accepts wire revision 6.", "Pine client v4 rejects wire revision 5."],
        [
            "Which of wire revisions 5 and 6 can Pine client v4 accept?",
            "State Pine v4 compatibility and incompatibility with wire revisions 6 and 5.",
        ],
        550,
    ),
]


def main() -> None:
    dataset_path = Path("evals/phase9_evidence_cases.json")
    split_path = Path("evals/phase9_split_manifest.json")
    if dataset_path.exists() or split_path.exists():
        raise FileExistsError("Phase 9 dataset/split already frozen")
    counter = ApproximateTokenCounter()
    documents = []
    cases = []
    facts_by_family = {}
    for family, facts, queries, size in FAMILIES:
        tenant = f"phase9-{family}"
        support = f"The {family} specification is maintained by the reliability team."
        blocks = []
        for index, fact in enumerate(facts):
            text = fact + (" " + support if index == 0 else "")
            sentence = (
                f" The {family} operational review records routine maintenance observations "
                "and scheduling context without changing the normative requirement above."
            )
            while counter.count(text + sentence) <= size:
                text += sentence
            blocks.append(text)
        # Same-source complementary evidence; production chunking determines boundaries.
        documents.append(
            document_from_content(
                content="\n\n".join(blocks),
                source_path=f"{family}/spec.txt",
                source_type=DocumentSourceType.TEXT,
                tenant_id=tenant,
            )
        )
        # Exact copy of first section is a valid independent alternative, not a new fact.
        documents.append(
            document_from_content(
                content=blocks[0],
                source_path=f"{family}/mirror.txt",
                source_type=DocumentSourceType.TEXT,
                tenant_id=tenant,
            )
        )
        # Vocabulary overlap with explicitly non-normative, wrong environment/details.
        topic = " ".join(queries)
        for index in range(8):
            text = (
                f"Archived unapproved {family} discussion {index}. {topic} "
                "This is a retired sandbox proposal, not the active specification. "
                "No operational setting should be inferred from this historical discussion. "
            )
            prose = (
                f" The {family} discussion considers migration planning, monitoring, "
                "and historical experiments without establishing the active contract."
            )
            while counter.count(text + prose) <= 550:
                text += prose
            documents.append(
                document_from_content(
                    content=text,
                    source_path=f"{family}/archive-{index}.txt",
                    source_type=DocumentSourceType.TEXT,
                    tenant_id=tenant,
                )
            )
        facts_by_family[family] = (facts, support, queries, size)
    chunks = [chunk for document in documents for chunk in StructureAwareChunker().chunk(document)]
    for family, (facts, support, queries, size) in facts_by_family.items():

        def locators(excerpt: str, selected_family: str = family) -> list[dict[str, object]]:
            found = []
            for chunk in chunks:
                if chunk.tenant_id != f"phase9-{selected_family}":
                    continue
                start = chunk.content.find(excerpt)
                if start >= 0:
                    found.append(
                        {
                            "spans": [
                                {
                                    "source": chunk.metadata["source_path"],
                                    "chunk_id": chunk.chunk_id,
                                    "start": start,
                                    "end": start + len(excerpt),
                                    "excerpt": excerpt,
                                }
                            ]
                        }
                    )
            if not found:
                raise ValueError(f"authoring locator failed: {excerpt}")
            return found

        groups = [
            {"group_id": f"fact-{i}", "requirement": "REQUIRED", "alternatives": locators(fact)}
            for i, fact in enumerate(facts)
        ]
        groups.append(
            {
                "group_id": "ownership",
                "requirement": "SUPPORTING",
                "alternatives": locators(support),
            }
        )
        for variant, query in enumerate(queries):
            cases.append(
                {
                    "case_id": f"{family}-{variant}",
                    "query": query,
                    "tenant_id": f"phase9-{family}",
                    "template_group": family,
                    "evidence_groups": groups,
                    "status": "VERIFIED_FIXTURE",
                    "answerability_notes": (
                        "All stated facts must survive; mirrors are alternatives. "
                        "Authored synthetic specification, not independently human-judged."
                    ),
                    "budget_pressure_class": (
                        f"{len(facts)} required facts, ~{size}-token sections; "
                        "eight long archived distractors; exact normative source required"
                    ),
                }
            )
    corpus = EvidenceCorpus.model_validate(
        {
            "provenance": (
                "Deterministically authored synthetic contracts. Labels located from corpus facts "
                "before retrieval. VERIFIED_FIXTURE means exact authoring contract, "
                "not independent review."
            ),
            "documents": [d.model_dump(mode="json") for d in documents],
            "chunks": [c.model_dump(mode="json") for c in chunks],
            "cases": cases,
        }
    )
    assignments = grouped_split(corpus.cases, seed=902026)
    data = corpus.model_dump(mode="json")
    split = {
        "seed": 902026,
        "dataset_sha256": digest(data),
        "assignments": assignments,
        "template_groups": {c.template_group: assignments[c.case_id] for c in corpus.cases},
        "training": "none",
        "grouping_policy": "source/specification family and all query paraphrases",
    }
    split["sha256"] = digest(split)
    with dataset_path.open("x") as file:
        json.dump(data, file, indent=2)
    with split_path.open("x") as file:
        json.dump(split, file, indent=2)
    print(
        json.dumps(
            {
                "cases": len(cases),
                "documents": len(documents),
                "chunks": len(chunks),
                "groups": len(FAMILIES),
                "split": split["template_groups"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
