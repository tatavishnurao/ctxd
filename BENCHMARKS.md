# Benchmarks

Measured on the working tree based on commit `806d670` with Python 3.13.15, Linux 6.6.87.2 WSL2 x86_64, and PostgreSQL 17.11. Sequential runs used 10 warmups and 100 measured queries. See `PERFORMANCE.md` for methodology and limitations.

## Phase 2 versus Phase 3 retrieval

| Chunks | Phase 2 p50 | Phase 2 p95 | Phase 2 p99 | Phase 2 QPS | Phase 3 p50 | Phase 3 p95 | Phase 3 p99 | Phase 3 QPS |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,200 | 43.52 ms | 78.60 ms | 101.19 ms | 20.18 | 1.83 ms | 2.08 ms | 2.16 ms | 540.36 |
| 12,000 | 351.64 ms | 514.06 ms | 925.54 ms | 2.61 | 7.96 ms | 9.53 ms | 10.02 ms | 122.01 |
| 50,004 | — | — | — | — | 36.30 ms | 45.53 ms | 50.38 ms | 26.75 |

Phase 2 used process-local storage and rebuilt/tokenized the full corpus per query. Phase 3 used persisted postings and SQL BM25 with a bounded pool.

## Phase 3 ingestion and incremental index cost

| Documents | Chunks | Docs/s | Chunks/s | Index update p50 | p95 | p99 |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 1,200 | 68.75 | 825.03 | 13.92 ms | 15.77 ms | 16.62 ms |
| 1,000 | 12,000 | 64.02 | 768.26 | 15.12 ms | 17.13 ms | 18.31 ms |
| 4,167 | 50,004 | 58.23 | 698.78 | 16.39 ms | 19.12 ms | 22.24 ms |

## PostgreSQL index-search latency

| Chunks | Vocabulary | Index search p50 | p95 | p99 |
|---:|---:|---:|---:|---:|
| 1,200 | 1,437 | 1.77 ms | 2.06 ms | 2.26 ms |
| 12,000 | 14,037 | 8.06 ms | 9.64 ms | 10.41 ms |
| 50,004 | 58,375 | 33.69 ms | 40.61 ms | 41.95 ms |

## Concurrent PostgreSQL retrieval

Corpus: 1,000 documents / 12,000 chunks. Each level used 20 warmups and 320 measured queries with pool max 32.

| Concurrency | QPS | p50 | p95 | p99 | Errors | Cumulative queued requests | Cumulative pool wait |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 118.96 | 8.31 ms | 9.73 ms | 10.16 ms | 0 | 0 | 0 ms |
| 4 | 329.38 | 11.66 ms | 13.60 ms | 15.06 ms | 0 | 6 | 46 ms |
| 8 | 491.56 | 15.34 ms | 20.26 ms | 24.64 ms | 0 | 20 | 133 ms |
| 16 | 427.68 | 36.75 ms | 50.61 ms | 56.88 ms | 0 | 102 | 1,031 ms |
| 32 | 399.57 | 78.11 ms | 101.34 ms | 114.06 ms | 0 | 316 | 5,525 ms |

Throughput peaked at concurrency 8 in this run. The first sharp latency/throughput deterioration occurred at concurrency 16.

## Phase 2 rebuild decomposition

| Chunks | Rebuild p50 | Rebuild p95 | Scoring p50 | Reproduced total p50 | Rebuild share |
|---:|---:|---:|---:|---:|---:|
| 1,200 | 20.83 ms | 22.11 ms | 2.60 ms | 23.52 ms | 88.5% |
| 12,000 | 214.90 ms | 251.95 ms | 23.29 ms | 238.54 ms | 90.1% |

Machine-readable artifacts:

- `benchmarks/phase2_baseline.json`
- `benchmarks/phase2_rebuild_analysis.json`
- `benchmarks/phase3_postgres_baseline.json`
- `benchmarks/phase3_concurrent_load.json`

These are measured baselines, not generalized production performance claims.
