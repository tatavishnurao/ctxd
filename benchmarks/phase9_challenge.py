"""Post-freeze provenance challenge; fixed candidate order, no retrieval/tuning."""

import json
from pathlib import Path

from ctxd.app.evals.context_selection import SelectionCandidate, pack
from ctxd.app.evals.evidence import EvidenceCorpus, evaluate_evidence
from ctxd.app.ingestion.chunking import StructureAwareChunker
from ctxd.app.ingestion.loaders import document_from_content
from ctxd.app.models.domain import DocumentSourceType


def main() -> None:
    if Path("benchmarks/phase9_challenge.json").exists():
        raise FileExistsError("challenge already evaluated")
    config = json.loads(Path("benchmarks/phase9_selected_config.json").read_text())
    docs = [
        document_from_content(
            content="The request limit is 7.",
            source_path=f"{region}/policy.txt",
            source_type=DocumentSourceType.TEXT,
            tenant_id="phase9-challenge",
        )
        for region in ("east", "west")
    ]
    chunks = [c for d in docs for c in StructureAwareChunker().chunk(d)]
    corpus = EvidenceCorpus.model_validate(
        {
            "provenance": (
                "Authored post-freeze counterexample; identical statements "
                "belong to distinct resources. "
                "Fixed order, not a production retrieval measurement or independent holdout."
            ),
            "documents": docs,
            "chunks": chunks,
            "cases": [
                {
                    "case_id": "distinct-resource-identical-text",
                    "query": (
                        "What request limit is documented for EACH of "
                        "east/policy.txt and west/policy.txt?"
                    ),
                    "tenant_id": "phase9-challenge",
                    "template_group": "provenance-not-equivalence",
                    "status": "VERIFIED_FIXTURE",
                    "answerability_notes": (
                        "Both independent resource documents are required; "
                        "neither proves the other's limit."
                    ),
                    "budget_pressure_class": "all evidence fits; deduplication can lose provenance",
                    "evidence_groups": [
                        {
                            "group_id": f"resource-{i}",
                            "requirement": "REQUIRED",
                            "alternatives": [
                                {
                                    "spans": [
                                        {
                                            "source": c.metadata["source_path"],
                                            "chunk_id": c.chunk_id,
                                            "start": 0,
                                            "end": len(c.content),
                                            "excerpt": c.content,
                                        }
                                    ]
                                }
                            ],
                        }
                        for i, c in enumerate(chunks)
                    ],
                }
            ],
        }
    )
    candidates = [
        SelectionCandidate(c.chunk_id, str(c.metadata["source_path"]), c.content, c.token_count)
        for c in chunks
    ]
    result = {"scope": corpus.provenance, "frozen_config_sha256": config["sha256"], "metrics": {}}
    for policy in dict.fromkeys(("greedy", config["policy"])):
        result["metrics"][policy] = evaluate_evidence(
            corpus.cases[0],
            candidates,
            pack(candidates, 256, policy),
            {c.chunk_id: c for c in chunks},
        )
    with Path("evals/phase9_challenge_cases.json").open("x") as file:
        json.dump(corpus.model_dump(mode="json"), file, indent=2)
    with Path("benchmarks/phase9_challenge.json").open("x") as file:
        json.dump(result, file, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
