import hashlib
import json
from pathlib import Path

from ctxd.app.evals.evidence import EvidenceCorpus, digest, validate_split


def test_phase8_freeze_and_phase9_dataset_integrity() -> None:
    freeze = json.loads(Path("benchmarks/phase9_phase8_freeze.json").read_text())
    for name, checksum in freeze["sha256"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == checksum
    data = json.loads(Path("evals/phase9_evidence_cases.json").read_text())
    corpus = EvidenceCorpus.model_validate(data)
    split = json.loads(Path("evals/phase9_split_manifest.json").read_text())
    checksum = split.pop("sha256")
    assert digest(split) == checksum
    assert digest(data) == split["dataset_sha256"]
    validate_split(corpus.cases, split["assignments"])
    assert len(corpus.cases) == 24
    assert len(set(c.template_group for c in corpus.cases)) == 12
    # All identical chunk texts, including mirrors, stay in one source family/partition.
    tenant_partition = {c.tenant_id: split["assignments"][c.case_id] for c in corpus.cases}
    seen: dict[str, set[str]] = {}
    for chunk in corpus.chunks:
        seen.setdefault(chunk.content, set()).add(tenant_partition[chunk.tenant_id])
    assert all(len(partitions) == 1 for partitions in seen.values())


def test_frozen_policy_matches_development_and_holdout() -> None:
    config = json.loads(Path("benchmarks/phase9_selected_config.json").read_text())
    checksum = config.pop("sha256")
    assert digest(config) == checksum
    dev = json.loads(Path("benchmarks/phase9_packing_dev.json").read_text())
    holdout = json.loads(Path("benchmarks/phase9_holdout.json").read_text())
    assert digest(dev) == config["development_sha256"]
    assert holdout["dataset_sha256"] == config["dataset_sha256"]
    assert holdout["split_sha256"] == config["split_sha256"]
    assert set(r["policy"] for r in holdout["rows"]) == {"greedy", config["policy"]}
    assert {r["case_id"] for r in dev["rows"]}.isdisjoint(r["case_id"] for r in holdout["rows"])
    assert {r["template_group"] for r in dev["rows"]}.isdisjoint(
        r["template_group"] for r in holdout["rows"]
    )
    assert len({r["case_id"] for r in holdout["rows"]}) == 8
    for row in holdout["rows"]:
        assert row["metrics"]["selected_tokens"] <= row["budget"]
        assert len(row["selected_chunks"]) == len(set(row["selected_chunks"]))
        assert 0 <= row["metrics"]["required_recall"] <= 1
        assert 0 <= row["metrics"]["ndcg_at_5"] <= 1
