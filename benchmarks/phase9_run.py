"""PostgreSQL production-path baseline and offline evidence evaluation.

Separate development and holdout commands. Exclusive output creation guards replay.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from ctxd.app.context.assembler import ContextAssembler
from ctxd.app.evals.context_selection import Packing, SelectionCandidate, pack, should_rerank
from ctxd.app.evals.evidence import (
    EvidenceCase,
    EvidenceCorpus,
    clustered_bootstrap,
    digest,
    evaluate_evidence,
    validate_split,
)
from ctxd.app.evals.phase7 import apply_rank_guardrail, lexical_protection_ids, tokens
from ctxd.app.ingestion.chunking import StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import RetrievalMode
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.postgres import PostgresDocumentStore
from phase7_models import MINILM_L6, LocalOnnxReranker

BUDGETS = (256, 512, 1024, 2048, 4096)
POLICIES: tuple[Packing, ...] = ("greedy", "density", "unique_source", "exact_duplicate")


def save(path: str, data: object) -> None:
    with Path(path).open("x") as file:
        json.dump(data, file, indent=2)


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, float]]] = defaultdict(list)
    for row in rows:
        grouped[f"{row['mode']}/{row['policy']}/{row['budget']}"].append(row["metrics"])
    return {
        key: {name: mean(v[name] for v in values) for name in values[0]}
        for key, values in grouped.items()
    }


def oracle_cost(case: EvidenceCase, costs: dict[str, int]) -> int | None:
    """Label-only upper bound; NEVER used by a selection policy."""
    states: set[frozenset[str]] = {frozenset()}
    for group in case.evidence_groups:
        if group.requirement != "REQUIRED":
            continue
        alternatives = [frozenset(s.chunk_id for s in a.spans) for a in group.alternatives]
        states = {old | new for old in states for new in alternatives if new <= costs.keys()}
    return min((sum(costs[i] for i in state) for state in states), default=None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("development", "holdout"))
    parser.add_argument("--database-url", default=os.getenv("CTXD_DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        raise ValueError("a dedicated migrated database URL is required")
    output = f"benchmarks/phase9_{'packing_dev' if args.stage == 'development' else 'holdout'}.json"
    if Path(output).exists():
        raise FileExistsError(output)
    corpus_data = json.loads(Path("evals/phase9_evidence_cases.json").read_text())
    corpus = EvidenceCorpus.model_validate(corpus_data)
    split = json.loads(Path("evals/phase9_split_manifest.json").read_text())
    expected_hash = split.pop("sha256")
    if digest(split) != expected_hash or digest(corpus_data) != split["dataset_sha256"]:
        raise ValueError("frozen dataset or split checksum mismatch")
    validate_split(corpus.cases, split["assignments"])
    selected_config = None
    if args.stage == "holdout":
        selected_config = json.loads(Path("benchmarks/phase9_selected_config.json").read_text())
        config_hash = selected_config.pop("sha256")
        if digest(selected_config) != config_hash:
            raise ValueError("selected configuration changed")
        if selected_config["dataset_sha256"] != split["dataset_sha256"]:
            raise ValueError("dataset changed after selection")
        if selected_config["split_sha256"] != expected_hash:
            raise ValueError("split changed after selection")
    # Durable start marker: failed holdout runs require explicit review, not silent repeats.
    save(
        f"benchmarks/phase9_{args.stage}_started.json",
        {
            "dataset_sha256": split["dataset_sha256"],
            "split_sha256": expected_hash,
            "stage": args.stage,
            "holdout_config": selected_config,
        },
    )
    cases = [
        c
        for c in corpus.cases
        if split["assignments"][c.case_id] == args.stage and c.status == "VERIFIED_FIXTURE"
    ]
    tenants = {c.tenant_id for c in cases}
    model = RealEmbeddingProvider(offline=True)
    store = PostgresDocumentStore(args.database_url, pool_min_size=1, pool_max_size=8)
    store.start()
    rows: list[dict[str, Any]] = []
    retrieval = []
    pressure = []
    pools = []
    rerank_timings = []
    chunks = {c.chunk_id: c for c in corpus.chunks}
    reranker = (
        LocalOnnxReranker(
            MINILM_L6,
            cache_dir=Path.home() / ".cache/ctxd/phase7",
            intra_op_threads=4,
            offline=True,
        )
        if args.stage == "development"
        else None
    )
    try:
        ingestion = IngestionService(store, StructureAwareChunker(), model)
        for document in corpus.documents:
            if document.tenant_id in tenants:
                _, actual, _ = ingestion.ingest_content(
                    content=document.content,
                    source_path=document.source_path,
                    source_type=document.source_type,
                    tenant_id=document.tenant_id,
                    metadata=document.metadata,
                )
                if any(chunks.get(c.chunk_id) != c for c in actual):
                    raise ValueError("ingested chunk differs from frozen evidence corpus")
        lexical = BM25Retriever(store)
        semantic = SemanticRetriever(store, model)
        hybrid = HybridRetriever(lexical, semantic, candidate_depth=20)
        assembler = ContextAssembler(lexical, semantic)
        for case in cases:
            start = perf_counter()
            pool = hybrid.search(case.query, case.tenant_id, 20)
            retrieval_ms = (perf_counter() - start) * 1000
            base = [
                SelectionCandidate(
                    c.source_id,
                    str(c.metadata["source_path"]),
                    c.content,
                    c.token_cost,
                    c.metadata.get("lexical_rank"),
                    c.metadata.get("semantic_rank"),
                )
                for c in pool
            ]
            retrieval.append(
                {
                    "case_id": case.case_id,
                    "latency_ms": retrieval_ms,
                    "metrics": evaluate_evidence(case, base[:10], base[:10], chunks),
                }
            )
            pools.append(
                {"case_id": case.case_id, "candidates": [c.model_dump(mode="json") for c in pool]}
            )
            orders = {"hybrid": base}
            if reranker is not None:
                scores = reranker.score_pairs(case.query, [c.content for c in base], batch_size=16)
                features = [
                    {
                        "source_id": c.identity,
                        "rrf_rank": i,
                        "lexical_rank": c.lexical_rank,
                        "exact_query_token_overlap": sorted(
                            set(tokens(case.query)) & set(tokens(c.content))
                        ),
                    }
                    for i, c in enumerate(base, 1)
                ]
                protected = lexical_protection_ids(features, "protect_exact_overlap_top1")
                ordered = apply_rank_guardrail(
                    features,
                    {c.identity: score for c, score in zip(base, scores, strict=True)},
                    protected,
                )
                by_id = {c.identity: c for c in base}
                always = [by_id[r["source_id"]] for r in ordered]
                decision = should_rerank(base, "no_lexical_winner")
                orders.update(always=always, selective=always if decision else base)
                rerank_timings.append(
                    {
                        "case_id": case.case_id,
                        "selective_decision": decision,
                        "timings_ms": dict(reranker.last_timings_ms),
                        "scores": scores,
                        "candidate_ids": [c.identity for c in base],
                    }
                )
            for budget in BUDGETS:
                production = assembler.assemble(
                    query=case.query,
                    tenant_id=case.tenant_id,
                    top_k=10,
                    max_context_tokens=budget,
                    retrieval_mode=RetrievalMode.HYBRID,
                )
                expected = pack(base[:10], budget)
                if [c.source_id for c in production.candidates] != [c.identity for c in expected]:
                    raise ValueError(
                        "offline greedy differs from actual production ContextAssembler"
                    )
                pressure.append(
                    {
                        "case_id": case.case_id,
                        "budget": budget,
                        "all_chunk_oracle_tokens": oracle_cost(
                            case, {c.chunk_id: c.token_count for c in corpus.chunks}
                        ),
                        "retrieved_top10_oracle_tokens": oracle_cost(
                            case, {c.identity: c.tokens for c in base[:10]}
                        ),
                        "retrieved_tokens": sum(c.tokens for c in base[:10]),
                        "dropped_count": production.metadata["dropped_due_to_budget"],
                    }
                )
                for mode, order in orders.items():
                    policies = (
                        POLICIES
                        if args.stage == "development" and mode == "hybrid"
                        else ("greedy",)
                    )
                    if selected_config is not None:
                        policies = tuple(dict.fromkeys(("greedy", selected_config["policy"])))
                    for policy in policies:
                        start = perf_counter()
                        selected = pack(order[:10], budget, policy)
                        packing_ms = (perf_counter() - start) * 1000
                        metrics = evaluate_evidence(case, order[:10], selected, chunks)
                        rows.append(
                            {
                                "case_id": case.case_id,
                                "template_group": case.template_group,
                                "query": case.query,
                                "mode": mode,
                                "policy": policy,
                                "budget": budget,
                                "metrics": metrics,
                                "packing_ms": packing_ms,
                                "selected_chunks": [c.identity for c in selected],
                                "selected_ordinals": [chunks[c.identity].ordinal for c in selected],
                                "required_groups": [
                                    g.model_dump(mode="json")
                                    for g in case.evidence_groups
                                    if g.requirement == "REQUIRED"
                                ],
                            }
                        )
        result = {
            "stage": args.stage,
            "dataset_sha256": split["dataset_sha256"],
            "split_sha256": expected_hash,
            "embedding_version": model.version,
            "protocol": "production defaults: branch depth20, return top10, whole-chunk packing",
            "summary": summary(rows),
            "rows": rows,
            "retrieval": retrieval,
            "case_count": len(cases),
            "template_count": len({c.template_group for c in cases}),
        }
        save(output, result)
        save(f"benchmarks/phase9_{args.stage}_pools.json", pools)
        save(f"benchmarks/phase9_{args.stage}_budget_pressure.json", pressure)
        if args.stage == "development":
            save(
                "benchmarks/phase9_baseline.json",
                {
                    "retrieval": retrieval,
                    "summary": summary(
                        [r for r in rows if r["mode"] == "hybrid" and r["policy"] == "greedy"]
                    ),
                },
            )
            save(
                "benchmarks/phase9_reranker_replay.json",
                {
                    "identity": reranker.identity() if reranker else None,
                    "timings": rerank_timings,
                    "summary": summary([r for r in rows if r["mode"] != "hybrid"]),
                    "rows": [r for r in rows if r["mode"] != "hybrid"],
                },
            )
        else:
            assert selected_config is not None
            intervals = {}
            changes = []
            for budget in BUDGETS:
                baseline = {
                    r["case_id"]: r
                    for r in rows
                    if r["budget"] == budget and r["policy"] == "greedy"
                }
                candidate = {
                    r["case_id"]: r
                    for r in rows
                    if r["budget"] == budget and r["policy"] == selected_config["policy"]
                }
                for metric in (
                    "full_answerability",
                    "required_recall",
                    "selected_tokens",
                    "ndcg_at_5",
                ):
                    deltas: dict[str, list[float]] = defaultdict(list)
                    for case_id, base_row in baseline.items():
                        new = candidate[case_id]
                        deltas[new["template_group"]].append(
                            new["metrics"][metric] - base_row["metrics"][metric]
                        )
                    intervals[f"{budget}/{metric}"] = clustered_bootstrap(deltas)
                for case_id, base_row in baseline.items():
                    new = candidate[case_id]
                    if base_row["selected_chunks"] != new["selected_chunks"]:
                        changes.append(
                            {
                                "case_id": case_id,
                                "budget": budget,
                                "baseline": base_row,
                                "candidate": new,
                                "lost_chunk_ids": sorted(
                                    set(base_row["selected_chunks"]) - set(new["selected_chunks"])
                                ),
                                "reason": (
                                    "deterministic policy selection; "
                                    "causal semantic reason not inferred"
                                ),
                            }
                        )
            save(
                "benchmarks/phase9_bootstrap.json",
                {
                    "method": "paired template-cluster resampling, 2000 draws",
                    "intervals": intervals,
                    "case_changes": changes,
                },
            )
        print(json.dumps({"stage": args.stage, "summary": result["summary"]}, indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
