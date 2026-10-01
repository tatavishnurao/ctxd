# Benchmarks

## Phase 9 evidence-grounded evaluation (synthetic; no promotion)

A fresh 24-case, 12-family corpus supplies exact chunk/span locators, alternate evidence, and complementary required facts. The split is 16 development / 8 holdout. Greedy selections were checked against production `ContextAssembler` for every measured budget (256/512/1024/2048/4096).

Frozen exact-text deduplication had the same holdout full answerability as greedy: 0/0/0/0/0.25 across those budgets. Required-evidence recall was also identical: 0/0.29167/0.29167/0.375/0.41667. At 4096 tokens, the candidate spent **39.25 more tokens per query**, with paired template-bootstrap 95% interval [0.25, 78.25]; only four holdout template clusters exist, so uncertainty remains poorly resolved. Zero observed evidence delta is not proof of deployment equivalence.

A separate post-freeze, fixed-order challenge required identical statements from two distinct resource documents. Greedy preserved both; deduplication lost one requirement (answerability 1→0). Decision: **P3 / R2**, no production change. Full definitions, development results, per-case evidence and limitations: `PHASE9_REPORT.md`, `benchmarks/phase9_*.json`.

## Phase 8 status (experimental; no production promotion)

The frozen selective policy reranked 5/47 reused-holdout queries, with 2 fixes and 2 regressions. Its ΔMRR was +0.01099 (95% interval −0.03936 to +0.06277); ΔnDCG@5 +0.01461 (−0.02942 to +0.06104). Neither supports promotion. Phase 7 nDCG used binary source judgments, not graded chunk evidence.

Development packing compares greedy and three alternatives at budgets 256/512/1024/2048/4096. Source suppression saves about 9.4% mean tokens in the N20/budget2048 proxy at equal source recall, but may discard complementary evidence; it is not recommended for production. No packing holdout or combined-path trial was run. See `PHASE8_REPORT.md` and `benchmarks/phase8_audit.json` for scope and all metrics. Historical entries below remain unchanged.

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

## Phase 4B evaluation summary

Corpus: `evals/retrieval_semantic.json` (150 cases, including 50 semantic/paraphrase-oriented additions). Model: `model2vec:minishlab/potion-base-8M@bf8b056651a2c21b8d2565580b8569da283cab23:normalized`.

Overall metrics from `evals/retrieval_semantic_model2vec_results.json`:

| mode | R@1 | R@5 | R@10 | MRR | nDCG@5 | nDCG@10 |
|---|---:|---:|---:|---:|---:|---:|
| lexical | 0.667 | 0.813 | 0.813 | 0.803 | 0.799 | 0.799 |
| semantic | 0.540 | 0.780 | 0.847 | 0.702 | 0.692 | 0.716 |
| hybrid | 0.680 | 0.907 | 0.973 | 0.861 | 0.844 | 0.869 |

Candidate-depth experiment (hybrid RRF, final top 10): depth 20 had the best measured balance on this corpus: R@10 0.973, MRR 0.861, nDCG@10 0.869. Depths 5/10/50 were close but not better overall.

Failure taxonomy counts: semantic overgeneralization 27, lexical mismatch 24, semantic miss 11, insufficient candidate depth 2, near-duplicate confusion 1, annotation ambiguity 1, other 1.

Synthetic MCP evaluator fixture (`evals/synapse_synthetic_fixture_results.json`): 50 synthetic cases, tool selection accuracy 0.96, schema validity 0.92, argument validity 0.92, task success 0.84, p95 latency 35 ms. These are synthetic fixture results, not real Synapse results.

## Phase 4B PostgreSQL exact-vector closure

Artifact: `benchmarks/phase4b_postgres_exact.json`. The benchmark uses the production PostgreSQL retrievers and exact cosine pgvector path, not direct SQL alone. Corpus sizes are 1,200, 12,000, and 50,004 chunks with 256-dimensional normalized Potion embeddings. It records ingestion, re-ingestion reuse, full retrieval, component timings, concurrency 1/4/8/16/32 at 12k and 50k, storage audits, and `EXPLAIN (ANALYZE, BUFFERS)` plans.

| Chunks | Semantic p50 | p95 | p99 | QPS | Hybrid parallel p50 | p95 | p99 | QPS |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,200 | 3.83 ms | 167.17 ms | 185.98 ms | 31.22 | 4.80 ms | 177.55 ms | 186.83 ms | 28.95 |
| 12,000 | 21.87 ms | 25.94 ms | 29.99 ms | 45.22 | 22.80 ms | 28.54 ms | 34.84 ms | 42.47 |
| 50,004 | 43.86 ms | 53.06 ms | 56.91 ms | 22.28 | 48.53 ms | 59.93 ms | 65.34 ms | 20.03 |

The 50k component p50 was query embedding 0.33 ms, BM25 39.89 ms, vector search plus row/Chunk materialization 41.46 ms, RRF 0.10 ms, and context selection 0.003 ms. Parallel hybrid was faster than sequential at all three measured sizes; at 50k it was 48.53 ms versus 84.60 ms p50. The concurrent saturation knee was approximately 8–16 workers; no errors occurred.

Storage at 50,004 chunks: total 373,495,475 bytes; documents 3,252,224; chunks 46,628,864; lexical postings 233,267,200; lexical terms 8,896,512; lexical corpus stats 65,536; chunk embeddings 73,228,288; bytes/chunk 7,469.31; bytes/embedding 1,464.45. The exact plan used a parallel sequential scan, parallel hash join, and top-N sort.

Embedding ingestion at 50k was 518.34 chunks/s for embedding computation and 376.07 chunks/s end-to-end production ingestion. Re-ingestion replayed 50,004 chunks with 50,004 skipped embeddings and zero recomputations.

## HNSW experiment

Artifacts: `benchmarks/phase4b_hnsw.json` and `benchmarks/phase4b_hnsw_ef200.json`. HNSW was tested only as an experiment on 50,004 chunks using an expression index for the fixed 256-dimensional baseline (`m=16`, `ef_construction=64`). The recorded `ef_search=40` run produced 2.53/3.15/3.60 ms p50/p95/p99 versus exact 36.74/41.97/46.66 ms, but ANN recall was 0.060/0.052/0.396 at K=1/5/10; hybrid top-10 overlap recall was 0.550. The index was 68.30 MB and built in 6.08 s. This material, variable recall loss means HNSW remains disabled and exact search remains the default at the measured scale.

## Phase 5 reranking feasibility

Machine-readable artifacts use the `phase5_` prefix. Candidate recall was 0.893/0.973/0.987/1.000 at N=5/10/20/50. The N=20 oracle improved MRR from 0.862 to 1.000 and nDCG@5 from 0.844 to 0.990, establishing theoretical headroom. It could move 30 non-top-1 relevant candidates to the front. All 27 semantic-overgeneralization records had a relevant top-10 candidate, but only four had hybrid rank below one and were actually fixable by reranking the hybrid order.

The selected feasibility model was `cross-encoder/ms-marco-TinyBERT-L-2-v2` at source revision `81d1926f67cb8eee2c2be17ca9f793c7c3bd20cc`, Apache-2.0, 512-token limit. The local FlashRank ONNX artifact measured 4,954,219 bytes with SHA-256 `7384e127005ead4f2c975419dccd885987e22d0ede93e903601ccdae5f2ce974`. Added packages were FlashRank, ONNX Runtime, and FlatBuffers.

Actual quality regressed. Hybrid RRF scored R@1 0.680, R@5 0.907, R@10 0.973, MRR 0.861, and nDCG@10 0.869. The best reranked depth by aggregate quality was N=10: R@1 0.627, R@5 0.867, R@10 0.973, MRR 0.796, nDCG@10 0.835. N=20 was worse: MRR 0.771 and nDCG@10 0.800. At N=20 there were 9 fixed, 92 unchanged-correct, 13 unchanged-incorrect, 36 regressed, and zero candidate-missing transitions. Of 44 exact/rare lexical top-1 cases, 43 were preserved and one was demoted; near-duplicate and multiple-relevant quality also regressed.

Decision: **RERANKER REJECTED FOR NOW**. The implementation remains an internal experiment with deterministic fallback and telemetry; it is not wired into `RetrievalMode`, runtime, or API. See `PERFORMANCE.md` for latency, concurrency, and goodput.

## Phase 6 evaluation and reproducibility audit

Phase 5 evidence is frozen by `benchmarks/phase5_artifact_manifest.json` and a checksum test. The original 150-case corpus is unchanged; the separate audited corpus confirms 148 judgments and marks two contradictory Java-query judgments ambiguous. Binary labels are retained because the fixture does not provide defensible graded-assessment evidence.

Original-label hybrid metrics reproduce Phase 5 exactly. Under audited labels, hybrid remains R@1/R@5/R@10 `0.680/0.907/0.973`; MRR becomes `0.86468` and nDCG@10 `0.87132`. Candidate recall remains `0.893/0.973/0.987/1.000` at N=5/10/20/50. The N20 oracle remains MRR `1.000` and nDCG@10 `0.98968`.

TinyBERT still produces 36 rank regressions. The dominant overlapping forensic signals are 26 lexical exact-match demotions, 23 score-compression cases, and 16 score inversions. No relevant-proxy candidate exceeds 512 reranker tokens. In particular, all ten answer-bearing long-chunk candidates are 314 tokens and regress without truncation. The input format matches FlashRank's implementation, so no formatting defect was found.

The strict PostgreSQL protocol uses five independent runs, 20 warmups plus 100 measured queries per run/mode, model preload, alternating mode order, raw component timings, and separate cold-start records. Median-of-run hybrid versus reranked p50/p95/p99 results were:

- 1,200 chunks: `26.57/30.82/32.13` versus `40.63/50.23/52.38 ms`
- 12,000 chunks: `24.28/26.88/27.74` versus `39.44/49.51/51.17 ms`
- 50,004 chunks: `57.00/64.91/70.73` versus `85.03/96.02/100.34 ms`

The earlier clustered 1.2k cross-component spikes did not recur under this protocol, but this does not prove an environmental cause. **CAUSE REMAINS UNRESOLVED.** Reranking remains rejected and unexposed. Full findings and decision gates are in `PHASE6_REPORT.md`; machine-readable evidence uses the `phase6_` prefix.

## Phase 7 frozen holdout reranker evaluation

The original 150 judgments were split before reranker selection into 103 development and 47 holdout cases. Candidate generation remained parallel BM25 + exact pgvector + deterministic RRF at depth 20. At most two new local CPU ONNX models were evaluated on development; MiniLM-L6 plus `protect_exact_overlap_top1` was then checksummed before one holdout evaluation.

On holdout, hybrid versus frozen selected config MRR was `0.85162/0.89914`, nDCG@5 `0.80885/0.90873`, and Recall@1 `0.638/0.702`. Paired-bootstrap 95% intervals were ΔMRR `[-0.0124,0.1117]`, ΔnDCG@5 `[0.0412,0.1660]`, and ΔRecall@1 `[-0.0213,0.1702]`. There were 4 fixed and 2 regressed cases, no catastrophic regressions, and no exact-match demotions.

The selected scorer's standalone N20 p50/p95/p99 was `142/1,857/2,179 ms`. At 12k chunks end-to-end hybrid versus selected p95 was `117/1,022 ms`; at 50k it was `80/247 ms`. At concurrency 16, selected QPS was `10.64` at 12k and `9.53` at 50k, with p95 `1,665/1,770 ms` and zero errors. These are shared-host WSL2 CPU results; the model did not improve latency/throughput.

Decision: **B — interesting but inconclusive; keep reranking offline and unexposed.** See `PHASE7_REPORT.md`, `benchmarks/phase7_frontier.json`, `phase7_holdout.json`, `phase7_bootstrap.json`, `phase7_latency.json`, and `phase7_concurrency.json`. These are not production performance claims.
