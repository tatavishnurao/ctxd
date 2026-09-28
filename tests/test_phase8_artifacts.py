"""Read-only regression checks; never rerun a holdout/model benchmark in tests."""

import hashlib
import json
from pathlib import Path

from ctxd.app.context.assembler import ContextAssembler
from ctxd.app.evals.context_selection import SelectionCandidate, pack
from ctxd.app.models.domain import ContextCandidate, SourceType


def test_historical_evidence_remains_unchanged() -> None:
    initial = json.loads(Path("benchmarks/phase8_initial_manifest.json").read_text())
    for name, digest in initial["historical_artifacts"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name


def test_frozen_config_and_replay_evidence_match() -> None:
    config = json.loads(Path("benchmarks/phase8_selected_config.json").read_text())
    digest = config.pop("sha256")
    assert hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest() == digest
    result = json.loads(Path("benchmarks/phase8_holdout.json").read_text())
    assert result["config_sha256"] == digest
    assert len(result["per_query"]) == 47
    assert len({r["case_id"] for r in result["per_query"]}) == 47
    assert sum(r["reranked"] for r in result["per_query"]) == 5
    for row in result["per_query"]:
        chosen = "always" if row["reranked"] else "hybrid"
        assert row["metrics"]["selective"] == row["metrics"][chosen]


def test_offline_greedy_matches_assembler_at_same_candidate_boundary() -> None:
    rows = [
        ContextCandidate(
            source_id=str(i), source_type=SourceType.DOCUMENT, content=f"chunk {i}", token_cost=cost
        )
        for i, cost in enumerate([8, 4, 7, 3])
    ]

    class Retriever:
        def search(self, query: str, tenant_id: str, top_k: int) -> list[ContextCandidate]:
            assert tenant_id == "test"
            return rows[:top_k]

    assembler = ContextAssembler(Retriever())
    for budget in (1, 5, 10, 12, 30):
        packet = assembler.assemble(
            query="test", tenant_id="test", top_k=4, max_context_tokens=budget
        )
        experiment = pack(
            [SelectionCandidate(r.source_id, r.source_id, r.content, r.token_cost) for r in rows],
            budget,
        )
        assert [r.source_id for r in packet.candidates] == [r.identity for r in experiment]
        assert packet.context_tokens == sum(r.tokens for r in experiment)
