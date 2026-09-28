"""Compute frozen-partition retrieval baselines and exact PostgreSQL RRF pools."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from ctxd.app.evals.phase7 import normalized_category, partition_metrics
from ctxd.app.ingestion.chunking import ChunkingConfig, StructureAwareChunker
from ctxd.app.ingestion.service import IngestionService
from ctxd.app.models.domain import DocumentSourceType
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.lexical import BM25Retriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider, SemanticRetriever
from ctxd.app.storage.postgres import PostgresDocumentStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("CTXD_DATABASE_URL"))
    parser.add_argument(
        "--corpus", type=Path, default=Path("evals/retrieval_semantic_phase6_audited.json")
    )
    parser.add_argument("--split", type=Path, default=Path("evals/phase7_split_manifest.json"))
    parser.add_argument(
        "--output", type=Path, default=Path("benchmarks/phase7_partition_baselines.json")
    )
    parser.add_argument(
        "--pools-output", type=Path, default=Path("benchmarks/phase7_candidate_pools.json")
    )
    args = parser.parse_args()
    if not args.database_url:
        raise ValueError("--database-url or CTXD_DATABASE_URL is required")
    if args.output.exists() or args.pools_output.exists():
        raise FileExistsError("Phase 7 baseline outputs already exist; refusing overwrite")
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    split = json.loads(args.split.read_text(encoding="utf-8"))
    records = {row["case_id"]: row for row in split["cases"]}
    if set(records) != {case["id"] for case in corpus["cases"]}:
        raise ValueError("split manifest and audited corpus case sets differ")

    model = RealEmbeddingProvider()
    store = PostgresDocumentStore(args.database_url, pool_min_size=1, pool_max_size=8)
    store.start()
    source_tenants: dict[str, str] = {}
    ingested_documents: list[tuple[str, str]] = []
    try:
        ingestion = IngestionService(
            store,
            StructureAwareChunker(
                ChunkingConfig(target_tokens=80, max_tokens=120, overlap_tokens=10)
            ),
            model,
        )
        for document in corpus["documents"]:
            original_tenant = str(document.get("tenant_id", "eval"))
            tenant = f"phase7-{original_tenant}"
            source_tenants[original_tenant] = tenant
            stored, _, _ = ingestion.ingest_content(
                content=document["content"],
                source_path=document["source_path"],
                source_type=DocumentSourceType(document.get("source_type", "text")),
                tenant_id=tenant,
                metadata=document.get("metadata", {}),
            )
            ingested_documents.append((tenant, stored.document_id))

        lexical = BM25Retriever(store)
        semantic = SemanticRetriever(store, model)
        hybrid = HybridRetriever(lexical, semantic, candidate_depth=20, parallel=True)
        rows: dict[str, dict[str, dict[str, list[tuple[list[str], set[str]]]]]] = {
            partition: {
                mode: {"all": [], "excluding_ambiguous": []}
                for mode in ("lexical", "semantic", "hybrid")
            }
            for partition in ("development", "holdout")
        }
        by_category: dict[str, dict[str, dict[str, list[tuple[list[str], set[str]]]]]] = (
            defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        )
        pools: list[dict[str, Any]] = []
        for case in corpus["cases"]:
            split_row = records[case["id"]]
            partition = split_row["partition"]
            tenant = source_tenants[str(case.get("tenant_id", "eval"))]
            expected = set(case["expected_sources"])
            candidates = {
                "lexical": lexical.search(case["question"], tenant, 20),
                "semantic": semantic.search(case["question"], tenant, 20),
                "hybrid": hybrid.search(case["question"], tenant, 20),
            }
            paths = {
                mode: list(dict.fromkeys(str(item.metadata["source_path"]) for item in values))
                for mode, values in candidates.items()
            }
            ambiguous = split_row["annotation_status"] == "ambiguous"
            category = normalized_category(case)
            for mode in candidates:
                rows[partition][mode]["all"].append((paths[mode], expected))
                by_category[partition][category][mode].append((paths[mode], expected))
                if not ambiguous:
                    rows[partition][mode]["excluding_ambiguous"].append((paths[mode], expected))
            pools.append(
                {
                    "case_id": case["id"],
                    "partition": partition,
                    "category": category,
                    "annotation_status": split_row["annotation_status"],
                    "query": case["question"],
                    "tenant_id": tenant,
                    "expected_sources": sorted(expected),
                    "candidate_sources": [
                        {
                            "source_id": item.source_id,
                            "source_path": str(item.metadata["source_path"]),
                            "content": item.content,
                            "token_cost": item.token_cost,
                            "rrf_rank": index,
                            "rrf_score": item.metadata.get("fused_score"),
                            "lexical_rank": item.metadata.get("lexical_rank"),
                            "lexical_score": item.metadata.get("raw_lexical_score"),
                            "semantic_rank": item.metadata.get("semantic_rank"),
                            "semantic_score": item.metadata.get("raw_vector_score"),
                            "metadata": item.metadata,
                        }
                        for index, item in enumerate(candidates["hybrid"], 1)
                    ],
                }
            )
        baseline = {
            "protocol": {
                "store": "PostgreSQL exact pgvector",
                "candidate_generation": "parallel BM25 + exact pgvector -> deterministic RRF",
                "candidate_depth": 20,
                "embedding_model": model.version,
                "RRF_k": 60,
                "split_manifest_sha256": split["split_manifest_sha256"],
                "ambiguous_policy": "primary includes both; secondary excludes ambiguous queries",
            },
            "partitions": {
                partition: {
                    mode: {
                        key: partition_metrics(observations)
                        for key, observations in mode_rows.items()
                    }
                    for mode, mode_rows in modes.items()
                }
                for partition, modes in rows.items()
            },
            "by_category": {
                partition: {
                    category: {
                        mode: partition_metrics(observations)
                        for mode, observations in modes.items()
                        if observations
                    }
                    for category, modes in categories.items()
                }
                for partition, categories in by_category.items()
            },
        }
        args.output.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        args.pools_output.write_text(
            json.dumps({"protocol": baseline["protocol"], "cases": pools}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "protocol": baseline["protocol"],
                    "development": baseline["partitions"]["development"],
                    "holdout_case_count": sum(row["partition"] == "holdout" for row in pools),
                },
                indent=2,
            )
        )
    finally:
        for tenant, document_id in ingested_documents:
            store.delete_document(document_id, tenant)
        store.close()


if __name__ == "__main__":
    main()
