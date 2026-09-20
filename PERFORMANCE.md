# Performance Methodology

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
