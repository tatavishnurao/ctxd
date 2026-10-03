"""Lexical vs semantic vs hybrid retrieval quality on public BEIR datasets.

Runs the production code path: StructureAwareChunker ingestion, BM25Retriever,
SemanticRetriever with the pinned Model2Vec model and HybridRetriever (RRF k=60,
default depth), over the in-memory store (exact search; PostgreSQL returns the
same rankings and is only a storage choice). Chunks are mapped back to their
BEIR document; a document's rank is its best chunk's rank.

Metrics follow BEIR conventions: nDCG@10 with linear graded gain, Recall@100
and MRR@10 against the dataset's human ``test`` qrels. Uncertainty uses a
paired cluster bootstrap where a cluster is a connected component of queries
that share any relevant document, so queries about the same evidence are
resampled together. When that graph collapses into fewer than
``MIN_INFORMATIVE_CLUSTERS`` components (NFCorpus: one component holds almost
every query), the cluster interval is reported but flagged uninformative, and a
query-level interval is reported alongside it; that interval understates
dependence and must be read as optimistic.

Usage:
    uv run python benchmarks/beir_eval.py --datasets scifact nfcorpus \
        --output benchmarks/results/beir_eval.json

Datasets download once to ``--cache`` (default ~/.cache/ctxd/beir) and are not
committed; the result records each archive's SHA-256.
"""

import argparse
import hashlib
import json
import math
import platform
import random
import subprocess
import time
import urllib.request
import zipfile
from collections import defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ctxd.app.config.settings import Settings
from ctxd.app.models.domain import ContextCandidate, DocumentSourceType
from ctxd.app.retrieval.hybrid import HybridRetriever
from ctxd.app.retrieval.semantic import RealEmbeddingProvider
from ctxd.app.runtime import create_runtime
from ctxd.app.storage.documents import InMemoryDocumentStore

URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{name}.zip"
TENANT = "beir"
PREFIX = "beir/"
DEPTH = 100
MODES = ("lexical", "semantic", "hybrid")
PAIRS = (("hybrid", "lexical"), ("hybrid", "semantic"), ("semantic", "lexical"))
METRICS = ("ndcg@10", "recall@100", "mrr@10")
MIN_INFORMATIVE_CLUSTERS = 30
# Published BEIR BM25 (Anserini, multifield) nDCG@10, Thakur et al. 2021, Table 2.
# Context only: that BM25 uses stemming and stopwords; ctxd's tokenizer does not.
PUBLISHED_BM25_NDCG10 = {"scifact": 0.665, "nfcorpus": 0.325}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(name: str, cache: Path) -> tuple[Path, str]:
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"{name}.zip"
    if not archive.exists():
        partial = archive.with_suffix(".part")
        urllib.request.urlretrieve(URL.format(name=name), partial)
        partial.rename(archive)
    if not (cache / name).exists():
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(cache)
    return cache / name, sha256(archive)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load(directory: Path) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, int]]]:
    corpus = {}
    for row in read_jsonl(directory / "corpus.jsonl"):
        title, text = row.get("title", "").strip(), row.get("text", "").strip()
        corpus[str(row["_id"])] = f"{title}\n\n{text}".strip() if title else text
    queries = {str(row["_id"]): row["text"] for row in read_jsonl(directory / "queries.jsonl")}
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    with (directory / "qrels" / "test.tsv").open(encoding="utf-8") as handle:
        next(handle)
        for line in handle:
            query_id, doc_id, score = line.rstrip("\n").split("\t")
            if int(score) > 0:
                qrels[query_id][doc_id] = int(score)
    return corpus, queries, {qid: rels for qid, rels in qrels.items() if qid in queries}


def document_ranking(candidates: Sequence[ContextCandidate]) -> list[str]:
    ranking: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        doc_id = str(candidate.metadata["source_path"]).removeprefix(PREFIX)
        if doc_id not in seen:
            seen.add(doc_id)
            ranking.append(doc_id)
    return ranking


def ndcg_at_10(ranking: Sequence[str], relevant: dict[str, int]) -> float:
    dcg = sum(relevant.get(doc, 0) / math.log2(rank + 2) for rank, doc in enumerate(ranking[:10]))
    ideal = sorted(relevant.values(), reverse=True)[:10]
    idcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def recall_at_100(ranking: Sequence[str], relevant: dict[str, int]) -> float:
    return len(set(ranking[:100]) & relevant.keys()) / len(relevant)


def mrr_at_10(ranking: Sequence[str], relevant: dict[str, int]) -> float:
    for rank, doc in enumerate(ranking[:10], 1):
        if doc in relevant:
            return 1.0 / rank
    return 0.0


def boundary_tie(candidates: Sequence[ContextCandidate], k: int = 10) -> bool:
    """True when the chunk at rank k and rank k+1 have equal scores.

    Ties are broken deterministically by chunk ID, so such cutoffs are decided
    by identifier order rather than by relevance.
    """
    if len(candidates) <= k:
        return False
    return math.isclose(
        candidates[k - 1].relevance_score, candidates[k].relevance_score, rel_tol=0, abs_tol=1e-12
    )


def query_clusters(qrels: dict[str, dict[str, int]]) -> list[list[str]]:
    parent = {query_id: query_id for query_id in qrels}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    by_document: dict[str, list[str]] = defaultdict(list)
    for query_id, relevant in qrels.items():
        for doc_id in relevant:
            by_document[doc_id].append(query_id)
    for query_ids in by_document.values():
        for other in query_ids[1:]:
            parent[find(other)] = find(query_ids[0])
    groups: dict[str, list[str]] = defaultdict(list)
    for query_id in sorted(qrels):
        groups[find(query_id)].append(query_id)
    return sorted(groups.values())


def cluster_bootstrap(
    clusters: list[list[str]],
    value: Callable[[str], float],
    *,
    resamples: int,
    seed: int,
) -> dict[str, float]:
    sums = [(sum(value(q) for q in cluster), len(cluster)) for cluster in clusters]
    total = sum(s for s, _ in sums) / sum(n for _, n in sums)
    rng = random.Random(seed)
    estimates = []
    for _ in range(resamples):
        draw = [sums[rng.randrange(len(sums))] for _ in sums]
        estimates.append(sum(s for s, _ in draw) / sum(n for _, n in draw))
    estimates.sort()
    return {
        "estimate": total,
        "ci95_low": estimates[int(0.025 * resamples)],
        "ci95_high": estimates[int(0.975 * resamples) - 1],
    }


def evaluate(name: str, cache: Path, offline: bool, resamples: int, seed: int) -> dict[str, Any]:
    directory, archive_sha256 = fetch(name, cache)
    corpus, queries, qrels = load(directory)
    services = create_runtime(
        InMemoryDocumentStore(),
        Settings(embedding_provider="model2vec", embedding_offline=offline),
    )
    started = time.perf_counter()
    for doc_id in sorted(corpus):
        if corpus[doc_id]:
            services.ingestion.ingest_content(
                content=corpus[doc_id],
                source_path=PREFIX + doc_id,
                source_type=DocumentSourceType.TEXT,
                tenant_id=TENANT,
            )
    ingest_seconds = time.perf_counter() - started
    chunks = services.retriever.statistics(TENANT).indexed_chunks

    hybrid = HybridRetriever(services.retriever, services.semantic_retriever)
    retrievers = {
        "lexical": services.retriever.search,
        "semantic": services.semantic_retriever.search,
        "hybrid": hybrid.search,
    }
    per_query: dict[str, dict[str, dict[str, float]]] = {mode: {} for mode in MODES}
    ties = dict.fromkeys(MODES, 0)
    seconds = dict.fromkeys(MODES, 0.0)
    for query_id in sorted(qrels):
        for mode in MODES:
            begin = time.perf_counter()
            candidates = retrievers[mode](queries[query_id], TENANT, DEPTH)
            seconds[mode] += time.perf_counter() - begin
            ties[mode] += boundary_tie(candidates)
            ranking = document_ranking(candidates)
            relevant = qrels[query_id]
            per_query[mode][query_id] = {
                "ndcg@10": ndcg_at_10(ranking, relevant),
                "recall@100": recall_at_100(ranking, relevant),
                "mrr@10": mrr_at_10(ranking, relevant),
            }

    clusters = query_clusters(qrels)
    units = {"cluster": clusters, "query": [[query_id] for query_id in sorted(qrels)]}

    def intervals(value: Callable[[str], float]) -> dict[str, dict[str, float]]:
        return {
            level: cluster_bootstrap(groups, value, resamples=resamples, seed=seed)
            for level, groups in units.items()
        }

    def metric_of(mode: str, metric: str) -> Callable[[str], float]:
        return lambda query_id: per_query[mode][query_id][metric]

    def delta_of(a: str, b: str, metric: str) -> Callable[[str], float]:
        return lambda query_id: per_query[a][query_id][metric] - per_query[b][query_id][metric]

    summary = {
        mode: {metric: intervals(metric_of(mode, metric)) for metric in METRICS} for mode in MODES
    }
    deltas = {
        f"{a}-{b}": {metric: intervals(delta_of(a, b, metric)) for metric in METRICS}
        for a, b in PAIRS
    }
    return {
        "dataset": name,
        "source_url": URL.format(name=name),
        "archive_sha256": archive_sha256,
        "documents": len(corpus),
        "empty_documents_skipped": sum(1 for text in corpus.values() if not text),
        "chunks": chunks,
        "queries_evaluated": len(qrels),
        "relevant_judgments": sum(len(r) for r in qrels.values()),
        "query_clusters": len(clusters),
        "largest_cluster": max(len(c) for c in clusters),
        "cluster_interval_informative": len(clusters) >= MIN_INFORMATIVE_CLUSTERS,
        "ingest_seconds": round(ingest_seconds, 2),
        "mean_query_ms": {m: round(1000 * seconds[m] / len(qrels), 2) for m in MODES},
        "rank10_boundary_ties": ties,
        "published_bm25_ndcg@10": PUBLISHED_BM25_NDCG10.get(name),
        "metrics": summary,
        "paired_deltas": deltas,
        "per_query": per_query,
    }


def git_commit() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD"], check=False).returncode != 0
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return sha + ("+dirty" if dirty else "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--datasets", nargs="+", default=["scifact", "nfcorpus"])
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache/ctxd/beir")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results/beir_eval.json"))
    parser.add_argument("--resamples", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--offline", action="store_true", help="forbid model downloads")
    args = parser.parse_args()

    results = {
        "protocol": {
            "code_path": "production chunker, BM25Retriever, SemanticRetriever, "
            "HybridRetriever(rrf_k=60, default depth); exact in-memory search",
            "embedding_model": RealEmbeddingProvider.version,
            "retrieval_depth": DEPTH,
            "document_rank": "best-ranked chunk of each BEIR document",
            "metrics": "nDCG@10 (linear graded gain), Recall@100, MRR@10 on test qrels",
            "uncertainty": "paired bootstrap at two levels: clusters (connected "
            "components of queries sharing a relevant document) and single queries; "
            f"cluster level flagged uninformative below {MIN_INFORMATIVE_CLUSTERS} clusters",
            "resamples": args.resamples,
            "seed": args.seed,
            "tuning": "none: production defaults, no parameter was fitted to these datasets",
        },
        "environment": {
            "commit": git_commit(),
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "datasets": {
            name: evaluate(name, args.cache, args.offline, args.resamples, args.seed)
            for name in args.datasets
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    for name, data in results["datasets"].items():
        level = "cluster" if data["cluster_interval_informative"] else "query"
        print(
            f"\n{name}: {data['documents']} docs, {data['queries_evaluated']} queries, "
            f"{data['query_clusters']} clusters; showing {level}-level 95% intervals"
        )
        for label, rows in (
            *((m, data["metrics"][m]) for m in MODES),
            *data["paired_deltas"].items(),
        ):
            print(
                f"  {label:16s} "
                + "  ".join(
                    f"{m} {rows[m][level]['estimate']:+.3f} [{rows[m][level]['ci95_low']:+.3f},"
                    f"{rows[m][level]['ci95_high']:+.3f}]"
                    for m in METRICS
                )
            )


if __name__ == "__main__":
    main()
