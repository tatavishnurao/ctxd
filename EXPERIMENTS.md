# Experiment and decision index

Historical measurements below are scoped experiments, not deployment certification. Reports and raw artifacts are retained. No new experiment was run in consolidation; candidate construction and tests are validation only.

| Phase | Question | Main implementation | Key evidence | Decision | Report / artifact location |
|---|---|---|---|---|---|
| 1 | Establish service foundation? | FastAPI, schemas, telemetry, fixture evaluation | Initial scaffolding; no inference/runtime performance conclusion | Keep foundation; do not equate schemas with execution | Early git history; `ctxd/app/main.py`, `evals/golden.example.jsonl` |
| 2 | Deterministic lexical context retrieval? | Chunking, memory BM25, greedy assembly | 22-case fixture; per-query corpus rebuild dominated latency | Keep semantics; remove rebuild bottleneck later | `benchmarks/phase2_baseline.json`, `phase2_rebuild_analysis.json`; PERFORMANCE.md |
| 3 | Persistent incremental retrieval? | PostgreSQL postings, transactions, pool | 12k p50 7.96 ms vs historical 351.64 ms; saturation around 8–16 workers | Keep incremental storage; shared-host results only | `benchmarks/phase3_postgres_baseline.json`, `phase3_concurrent_load.json` |
| 4 / 4B | Add real semantic/hybrid; use ANN? | Pinned Model2Vec, exact pgvector, parallel RRF; isolated HNSW | Historical hybrid R@1/5/10 .680/.907/.973, MRR .861, nDCG@5/10 .844/.869; tested ANN recall unacceptable | Keep exact hybrid support; reject tested HNSW as default | `evals/retrieval_semantic_model2vec_results.json`; `benchmarks/phase4b_postgres_exact.json`, `phase4b_hnsw*.json`; BENCHMARKS.md |
| 5 | Does oracle headroom justify TinyBERT? | Offline FlashRank cross-encoder | N20: 9 fixes, 36 regressions; MRR .771 vs .861 | Reject TinyBERT, never production-wired | `benchmarks/phase5_*.json`, `phase5_artifact_manifest.json`; BENCHMARKS.md |
| 6 | Labels/input/truncation explain regressions? | Judgment audit, forensics, five-run performance | 148/150 confirmed, 2 ambiguous; 26 exact demotions, 23 compression, 16 inversions (overlapping); no tested truncation explanation | TinyBERT remains rejected; latency cause unresolved | PHASE6_REPORT.md; `evals/phase6_annotation_audit.json`, `benchmarks/phase6_*.json` |
| 7 | Controlled new reranker improves holdout? | Frozen 103/47 split; MiniLM-L6 + lexical protection | nDCG@5 delta +.100, CI [.041,.166]; MRR/R@1 CI cross zero; 12k p95 117 vs 1022 ms | Interesting but inconclusive; offline only | PHASE7_REPORT.md; `benchmarks/phase7_holdout.json`, `phase7_bootstrap.json`, `phase7_frontier.json` |
| 8 | Selective rerank / packing promotion? | Offline policies; duplicate-source nDCG fix | 5/47 reranked, 2 fixes/2 regressions; delta MRR .01099 CI [-.03936,.06277]; 9.4% proxy token saving lacks evidence guarantee | Keep reranking offline and greedy packing | PHASE8_REPORT.md; `benchmarks/phase8_audit.json`, `phase8_profile.json`, `phase8_holdout.json` |
| 9 | Evidence-level budget evaluation stronger? | Exact spans, AND/OR groups, provenance, bootstrap | 13 source-proxy false-answerability cells; identical-text dedup loses independently required provenance, answerability 1→0 | Keep evaluator; synthetic data insufficient for promotion | PHASE9_REPORT.md; `benchmarks/phase9_source_proxy_gap.json`, `phase9_challenge.json`, `phase9_experiment_manifest.json` |
| 10 / 10B | Build realistic reviewable benchmark? | Pinned sources, review gates, exact feasibility, candidate authoring | Original 121 drafts; current build 106 (25E/33M/36H/12VH/0I); zero independent reviews | PRE-REVIEW, NON-CANONICAL, BLOCKED; audit/tooling unfinished | PHASE10_REPORT.md, PHASE10_REVIEW_PACKET.md; `benchmarks/phase10_*.json`, `phase10b_build.py`; `evals/phase10b_authoring*.tsv`, `phase10b_external_sources.json` |
| E1 (v0.1) | Does hybrid beat lexical on real, human-judged text? | `benchmarks/beir_eval.py`: production path, no tuning, SciFact + NFCorpus | SciFact hybrid−lexical nDCG@10 −0.059 [−0.094,−0.026], Recall@100 +0.069 [+0.036,+0.108]; NFCorpus nDCG@10 −0.001 [−0.015,+0.012], Recall@100 +0.033 [+0.019,+0.048] | Hybrid is a recall/candidate-generation win, not a top-10 win; the default-mode choice needs revisiting | docs/BEIR_EVAL.md; `benchmarks/results/beir_eval.json` |

## Interpretation guardrails

- Phase 7 nDCG uses binary **source** judgments, not graded evidence-span labels. Its gain is top-list ranking quality; general retrieval improvement is not established.
- Phase 8 reused holdout; do not treat it as fresh independent confirmation.
- Phase 9 is synthetic and author verified, not independently reviewed deployment ground truth.
- Historical Phase 4–7 numbers differ with label audits and evaluation fixes; do not silently relabel earlier measurements as corrected metrics.
- No Phase 10 canonical score exists. Phase 10B has no completed final revision/split/review batch artifacts.
- Environment and measurement definitions are in PERFORMANCE.md; file-level inventory is `docs/evidence_inventory.json`.
