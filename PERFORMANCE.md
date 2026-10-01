# Performance Methodology

## Phase 9 context-budget methodology

Phase 9 measures evidence coverage and approximate context-token expenditure, not service capacity. Default production chunking (target400/max600/overlap40), pinned embeddings, PostgreSQL exact retrieval, branch depth20 and return top10 are retained. A dedicated `ctxd_phase9` database keeps authored fixture tenants separate from existing application data. Every offline greedy packet is compared with the actual `ContextAssembler` output.

Development policies are evaluated at 256/512/1024/2048/4096 tokens. Labels are used only by the evaluator, never packing decisions. The frozen candidate is tested once on template-grouped holdout; uncertainty uses 2,000 whole-template resamples per budget. All token metrics use `ApproximateTokenCounter`, not model-tokenizer billing units. Span precision, distractor-chunk fraction, and redundant labeled-span fraction are separate measures, not a disjoint token partition.

Per-request retrieval, scorer and packing timing observations are retained for diagnostics, but no new latency/QPS/SLO improvement is claimed. The earlier one-second reranking tail remains unresolved. See `PHASE9_REPORT.md` for evidence-preservation results and benchmark limitations.

## Phase 8 diagnostic scope

`benchmarks/phase8_profile.py` records 243 scorer calls: three development pools by input length, N=5/10/20, threads=4/1/2, batches=16/8/1, three repeats each. It separates cached initialization, pairs, tokenizer, tensors, inference, conversion, sorting and total scoring. This is not a full retrieval/API latency or load benchmark.

N20/four-thread/batch16 warm median was 84.37 ms, maximum 1,349.77 ms across six observations. Batch size 1 maximum fell to 455.68 ms but median rose to 100.16 ms and sampled ranking changed: rejected as a semantics-preserving optimization. Cached initialization timings are order/cache-confounded. Historical 12k end-to-end tail causation remains unresolved. No selective/packing policy passed the promotion gates, so no survivor-only scale/concurrency benchmark was run. Raw evidence and limitations: `benchmarks/phase8_profile.json`, `PHASE8_REPORT.md`.

No performance claims are made without measurements.

Every benchmark entry documents workload, platform, Python/PostgreSQL versions, commit, corpus size, warmup, samples, concurrency, pool settings, measurement method, results, and confounders.

## Phase 2 baseline

```bash
uv run python benchmarks/retrieval_baseline.py
```

This script preserves the Phase 2 behavior: every query lists and copies all tenant chunks, tokenizes every chunk, rebuilds average length and document frequencies, and scores the corpus in Python. The recorded baseline artifact is `benchmarks/phase2_baseline.json`.

`benchmarks/phase2_rebuild_analysis.py` separately reproduces and times the rebuild and scoring portions over 100 measured queries.

## Phase 3 sequential PostgreSQL baseline

```bash
uv run python benchmarks/postgres_retrieval_baseline.py
```

Defaults:

- PostgreSQL-backed incremental inverted index
- 100, 1,000, and 4,167 generated documents
- exactly 12 chunks per document: 1,200, 12,000, and 50,004 chunks
- 10 warmup queries per corpus size
- 100 measured queries per corpus size
- concurrency 1
- pool minimum 1, maximum 32
- `k1=1.5`, `b=0.75`

Each corpus-size run destructively truncates the corpus tables and therefore requires a dedicated benchmark database. Ingestion measures document construction, chunking, transaction, and index maintenance. Index-update latency times the atomic `replace_document` call. Query latency times the full `BM25Retriever` path. Index-search latency separately times PostgreSQL posting lookup, scoring, and row materialization.

## Phase 3 concurrent load

```bash
uv run python benchmarks/postgres_concurrent_load.py
```

Defaults:

- 1,000 documents / 12,000 chunks
- concurrency levels 1, 4, 8, 16, 32
- 20 warmups and 320 measured queries per level
- one shared psycopg pool, minimum 1 and maximum 32
- synchronized worker start
- fixed total query count, no think time
- per-request wall time via `time.perf_counter`

The benchmark destructively resets its dedicated database before corpus preparation. It reports achieved QPS, p50/p95/p99, errors, and cumulative pool statistics. Pool `requests_queued` and `requests_wait_ms` show connection acquisition pressure.

Percentiles use the sorted sample at `int((n - 1) * percentile)`; p50 uses the median.

## Critical-path analysis

The Phase 2 decomposition measured corpus-statistics rebuilding at:

- 1,200 chunks: 20.83 ms p50, 88.5% of reproduced median query time
- 12,000 chunks: 214.90 ms p50, 90.1% of reproduced median query time

Phase 3 removes that work from queries. At 12,000 chunks, full retrieval p50 fell from the recorded Phase 2 351.64 ms to 7.96 ms. The SQL index-search p50 was 8.06 ms, so row lookup, SQL BM25 aggregation, and result materialization are now the dominant sequential query costs rather than Python corpus reconstruction.

At low corpus size PostgreSQL adds connection/SQL overhead, but measured 1,200-chunk retrieval was still 1.83 ms versus 43.52 ms because the avoided rebuild was larger than that overhead.

Scaling is no longer a complete Python scan, but common query terms still produce posting sets proportional to matching chunks. Retrieval p50 increased from 1.83 ms at 1,200 chunks to 7.96 ms at 12,000 and 36.30 ms at 50,004. The next query bottleneck is SQL aggregation over large posting lists.

Concurrent throughput peaked in this run at concurrency 8 (491.56 QPS). Latency deteriorated sharply at concurrency 16: p50 rose from 15.34 ms to 36.75 ms while QPS fell. At concurrency 32, p50 reached 78.11 ms and cumulative pool wait time reached 5,525 ms. PostgreSQL CPU/query contention and connection-pool expansion/waiting—not corpus-statistics rebuild—define the measured saturation region.

Ingestion is intentionally more expensive than Phase 2 because it now persists content and updates postings transactionally. Across 1,200 to 50,004 chunks, index update p50 rose from 13.92 ms to 16.39 ms per document; ingestion throughput ranged from 825 to 699 chunks/s.

## Confounders

- Measurements ran under WSL2 on one machine, not isolated benchmark hardware.
- The PostgreSQL container and benchmark client shared host resources.
- Benchmark commit reports the base SHA because the measured working tree was uncommitted.
- PostgreSQL caches warmed during each run.
- Concurrency results are fixed-workload saturation observations, not service-level HTTP load tests.
- The explicit postings design favors deterministic Phase 2 compatibility over minimum storage size.

## Phase 4B measured baseline

Measured on this development environment with local Model2Vec embeddings and exact in-memory vector scan:

- ~1,424 chunks (`benchmarks/phase4_inmemory_1200_results.json`): lexical p50 0.33 ms / p95 0.86 ms; semantic p50 17.70 ms / p95 20.52 ms; hybrid parallel p50 18.21 ms / p95 21.02 ms; hybrid sequential p50 20.48 ms / p95 22.83 ms.
- ~12,015 chunks (`benchmarks/phase4_inmemory_12000_results.json`): lexical p50 0.70 ms / p95 6.91 ms; semantic p50 146.97 ms / p95 165.37 ms; hybrid parallel p50 150.22 ms / p95 163.57 ms; hybrid sequential p50 148.27 ms / p95 160.76 ms.

Exact vector scan is acceptable at the smaller scale but becomes the dominant cost around 12k chunks in the in-memory benchmark. PostgreSQL exact pgvector remains the default. ANN/HNSW is not enabled by default; it should only be added after a PostgreSQL exact-vs-ANN comparison shows a bottleneck and acceptable quality tradeoff.

## Phase 4B PostgreSQL closure

`benchmarks/phase4b_postgres_closure.py` is the destructive, production-path benchmark for exact pgvector. It uses the pinned Model2Vec provider, 256-dimensional normalized vectors, BM25, `SemanticRetriever`, `HybridRetriever(candidate_depth=20)`, and `ContextAssembler`. The machine-readable result is `benchmarks/phase4b_postgres_exact.json`; query plans and relation audits are included there.

On this WSL2/PostgreSQL 17.11 machine, the sequential full-path results were:

| Chunks | Lexical p50/p95/p99 | Semantic p50/p95/p99 | Hybrid parallel p50/p95/p99 | Hybrid sequential p50/p95/p99 |
|---:|---:|---:|---:|---:|
| 1,200 | 2.09/22.15/26.80 ms | 3.83/167.17/185.98 ms | 4.80/177.55/186.83 ms | 6.25/195.28/209.38 ms |
| 12,000 | 9.26/12.08/15.29 ms | 21.87/25.94/29.99 ms | 22.80/28.54/34.84 ms | 31.75/36.88/41.81 ms |
| 50,004 | 44.02/54.86/56.75 ms | 43.86/53.06/56.91 ms | 48.53/59.93/65.34 ms | 84.60/104.23/111.64 ms |

At 50,004 chunks the exact vector path is 41.46 ms p50 in component timing, versus 39.89 ms for BM25; query embedding is only 0.33 ms and RRF/assembly are below 0.1/0.01 ms. The first concurrency knee was around 8–16 workers: semantic p95 rose from 55.65 ms at 8 to 101.06 ms at 16, and hybrid p95 from 75.94 ms to 133.58 ms. All measured requests succeeded.

Storage was measured, not estimated. At 50,004 chunks the database was 373,495,475 bytes: 1,464.45 bytes/embedding and 7,469.31 bytes/chunk. `chunk_embeddings` was 19.61% of the database; lexical index bytes were 40.90%. The exact plans were sequential/parallel scans plus top-N sort (no vector index); at 50k PostgreSQL used a parallel sequential scan and Gather Merge.

The HNSW experiment is isolated in `benchmarks/phase4b_hnsw_experiment.py` and `benchmarks/phase4b_hnsw.json`. With `m=16`, `ef_construction=64`, and `ef_search=40`, the recorded run measured 2.53/3.15/3.60 ms p50/p95/p99 versus exact 36.74/41.97/46.66 ms, with a 68.30 MB index and 6.08 s build. ANN recall against exact was R@1 0.060, R@5 0.052, R@10 0.396; hybrid top-10 overlap recall was 0.550 on the fixed synthetic query set. Because the speedup came with material and variable recall loss, HNSW is not enabled by default. At the measured 50k scale, ANN is an experiment rather than a justified production default.

## Phase 5 tail-latency closure

`benchmarks/phase5_tail_latency.json` contains 300 raw per-query samples per variant at 1,200 and 12,000 chunks. The original 1.2k p95 of 177.55 ms did not reproduce consistently. The exact Phase 4 operation sequence produced hybrid p50/p95/p99 of 11.92/24.40/119.60 ms. Isolated normal-warmup hybrid measured 11.81/19.84/54.45 ms p50/p95/p99. Increased warmup, model preload, disabled GC, and a persistent executor did not eliminate intermittent clustered spikes. Slow intervals simultaneously affected embedding, BM25, and vector work, which rules out any one component as a confirmed cause. **CAUSE NOT YET CONFIRMED.** WSL/host scheduler or shared-resource noise is plausible but not proven.

## Phase 5 reranker performance

The internal TinyBERT experiment uses 10 fixed RRF candidates and batch size 8. It is not exposed through the runtime or API.

- 1,200 chunks: hybrid 7.96/10.26/10.82 ms versus reranked 19.19/21.33/22.84 ms p50/p95/p99.
- 12,000 chunks: hybrid 28.44/41.29/46.12 ms versus reranked 50.22/63.72/71.17 ms.
- 50,004 chunks: hybrid 60.64/70.20/83.63 ms versus reranked 87.02/98.95/105.78 ms.

At 50k concurrency, hybrid throughput peaked at 31.29 QPS at concurrency 8; reranked throughput peaked at 21.54 QPS at concurrency 8. Both deteriorated beyond 8, so reranking did not improve the saturation knee. Standalone reranking over 10 candidates measured 11.10/38.69/49.41 ms p50/p95/p99 in the quality run. At 20 candidates, batch size 8 had the best measured pair throughput (785 pairs/s), while batch size 1 had the best p95 (61.07 ms); neither operational result offsets the quality regression.

Experimental goodput used synthetic marker queries and therefore had a 100% top-5 quality pass rate for both modes. At 50k, 100 ms good requests/s were 16.1 for hybrid and 11.0 for reranked; at 150/250 ms they were 16.1 versus 11.5. This is an engineering workload indicator, not an industry-standard metric or semantic-evaluation result.

## Phase 6 strict reproducibility protocol

`benchmarks/phase6_reproducibility.py` destructively rebuilds each PostgreSQL corpus and then holds it stable for five runs. Each mode/run has 20 warmups and 100 measured queries. Models are preloaded, hybrid/reranked order alternates AB/BA, and cold model construction plus first-query timing are recorded separately. Every measured query records embedding, BM25, exact-vector search/materialization, RRF, reranker preparation/tokenization/inference, context selection, total latency, and synthetic quality pass. Outliers use a declared within-run rule: total latency above median plus three median absolute deviations.

Median hybrid p95 across the five runs was 30.82 ms at 1.2k, 26.88 ms at 12k, and 64.91 ms at 50k. Reranked p95 was 50.23, 49.51, and 96.02 ms. Hybrid p95 ranges were 28.53–31.14, 26.02–28.22, and 64.82–68.81 ms respectively. The inverse 1.2k/12k medians and reranked-mode shifts in retrieval components show that this shared-host run still contains system-state effects; they are measurements, not a causal diagnosis.

At 1.2k the robust outliers were BM25-dominant and no same-run/query outlier was shared by hybrid and reranked modes. The Phase 5 clustered simultaneous embedding/BM25/vector spikes therefore did not reproduce, but absence in five runs does not prove they were scheduling noise. The historical tail-latency cause remains **UNRESOLVED**.

Five runs were also collected at every concurrency point for 12k and 50k. Throughput plateaus around 8–16 workers and latency rises sharply afterward. At 50k/concurrency 8, median-run hybrid versus reranked QPS was 30.3 versus 21.9 and p95 was 288.8 versus 370.9 ms. Pool wait becomes material at concurrency 32. Client process CPU, maximum RSS, and pool wait are recorded per run; these are not PostgreSQL-server CPU profiles.

Phase 6 median 100 ms synthetic goodput at 50k was 17.32 requests/s hybrid versus 11.29 reranked. The workload still has 100% top-5 synthetic quality and must not be interpreted as semantic quality. See `benchmarks/phase6_reproducibility.json`, `phase6_concurrency.json`, `phase6_goodput.json`, and `phase6_outlier_analysis.json`.

## Phase 7 selected reranker performance (offline only)

`benchmarks/phase7_performance.py` measures only the configuration frozen before holdout: MiniLM-L6 CPU ONNX over the fixed parallel BM25 + exact pgvector RRF candidate pool (N=20), with exact-overlap top-1 protection. Sequential comparisons use five runs, 10 warmups, 50 queries/mode/run, alternating order, and the same generated 12-chunk-document workloads at 1,200, 12,000, and 50,004 chunks. Concurrency uses 32 synchronized requests per level at 1/4/8/16. The test database is separate and benchmark documents are removed afterward.

Selected standalone N20 scoring p50/p95/p99 was 142/1,857/2,179 ms. Hybrid versus selected end-to-end p95/QPS was 13.58 ms/85.87 versus 218.49 ms/5.57 at 1.2k; 117.43/15.92 versus 1,021.93/2.36 at 12k; and 79.87/14.68 versus 247.06/4.75 at 50k. At concurrency 16, selected p95/QPS reached 1,665 ms/10.64 at 12k and 1,770 ms/9.53 at 50k; all requests succeeded. Client CPU reached about 14.7 core-equivalents at 12k and 13.4 at 50k. This is CPU-heavy inference, not an improvement to the current concurrency/latency envelope.

The host is shared WSL2, so results are measurements rather than production SLO claims; nonmonotonic corpus-size tails and very broad scorer tails are retained as observed. CPU accounting is client-process only, not PostgreSQL server profiling. Goodput is not reported because the available generated workload has no quality-varying pass condition. Full per-query/raw-run evidence is in `benchmarks/phase7_latency.json` and `benchmarks/phase7_concurrency.json`; quality/latency comparison and scope caveats are in `benchmarks/phase7_frontier.json` and `PHASE7_REPORT.md`.
