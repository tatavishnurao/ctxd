# Phase 8: correctness-first context-selection investigation

## Status and decisions

**R2: selective reranking remains offline. C1: retain greedy packing. Production behavior changed: NO.**

This is a bounded investigation, not completion of every proposed milestone. A correctness audit, scorer decomposition, three development selective policies, one frozen holdout replay, and three development packing alternatives were completed. No new runtime mode, API, embedding backend, query rewriting, remote inference, caching service, or production telemetry was added. No commit or push was made.

The higher-value blocker is the mismatch between source-level ranking judgments and the chunk-level evidence consumed under a token budget. A concrete duplicate-gain metric bug was repaired. The selected selective policy then failed its holdout gate. Consequently the combined-path and survivor-only large-scale/concurrency experiments were not run. Full database-path latency attribution remains incomplete; the scorer-only investigation does not explain the historical 12k p95 causally.

## Ground truth — VERIFIED FACT

- Base commit: `474ad98`. Phase 7 Python code was committed; its JSON evidence, report, and four documentation changes were dirty/untracked. Those changes were preserved.
- `benchmarks/phase8_initial_manifest.json` captures initial Git status, CPU topology, OS, Python, PostgreSQL, pinned model identity, environment variables and hashes of 68 historical artifacts/reports. Phase 2–7 evidence was not overwritten.
- Production assembly calls a retriever with request `top_k`, then walks returned chunks in rank order, skipping chunks that do not fit. It neither summarizes nor truncates a selected chunk.
- **Architecture correction:** runtime does not unconditionally set candidate depth 20. `ContextAssembler` creates `HybridRetriever` without an explicit depth. Its branch width is `max(top_k, min(100, top_k * 2))`: default API top_k=10 yields 20, but other request sizes differ. This investigation does not change it.
- No reranker is wired into `create_runtime`, `ContextAssembler`, or `RetrievalMode`.
- Phase 7 selected MiniLM-L6 revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`, quantized AVX2 ONNX, four intra-op threads, batch 16, maximum pair length 512, plus exact-overlap lexical protection. Its file hashes are captured in the manifest.
- Historical holdout nDCG@5 delta +0.09988 and its positive interval are present in the artifacts; MRR and Recall@1 intervals cross zero. **These were binary source judgments, not graded evidence labels.** nDCG supports grades in principle, but none were used here.
- The 12k historical p95 values are 117.43 ms hybrid and 1,021.93 ms selected. These are retrieved-result timings, not a full API/context-packet benchmark.

## Evaluation correction — VERIFIED FACT / MEASURED RESULT

The shared `ndcg_at_k` helper counted every repeated occurrence of a relevant source. Before repair, `[a, a]` with relevant set `{a}` produced nDCG@5 = 1.63093. The helper now awards each source once while preserving chunk rank positions. Unique-source inputs retain their original results. Runtime retrieval is unaffected.

Phase 7 first collapsed duplicate source paths before evaluating ranks, so its stored nDCG@5 is **not invalidated by this counterexample**. The problem is that its source-list ranking is not a direct measure of chunk placement. There are duplicate-source chunks in 18/103 development pools and 6/47 holdout pools. Replaying baseline with source credit at original chunk positions changes development MRR from 0.86292 to 0.86275; holdout baseline metrics are effectively unchanged. This is a small measured metric difference, not an explanation of the model's quality gains.

`ctxd/app/evals/context_selection.py` adds an explicitly offline evaluation boundary:

- immutable candidate records without relevance labels, query categories, or case IDs;
- unique-source gain at original chunk positions;
- bounded whole-chunk packing with deterministic input-order output;
- source coverage, selected/dropped sources, token cost, nonrelevant-source token proxy, exact duplicate tokens, and relevant sources per 1k tokens;
- validation rejecting duplicate identities, invalid costs, and changed candidate contents.

Source relevance cannot tell whether a specific chunk contains the answer. Tokens from a relevant document are therefore **not called relevant evidence tokens**. Exact text duplication is also distinguished from complementary chunks of the same source. No unsupported semantic redundancy score is claimed.

The audit JSON records the pre-repair counterexample. Re-running the audit against the repaired helper would report 1.0; the existing artifact is retained as the initial observation and tests verify the repaired behavior.

## Scorer investigation — MEASURED RESULT

`benchmarks/phase8_profile.py` ran 243 local scorer calls on three development pools chosen by aggregate chunk-token length: shortest, middle, longest. Grid: N=5/10/20, threads=4/1/2, batch=16/8/1, three repeats/cell. The first repeat is separate from subsequent warm observations. No quality labels chose these inputs. Raw logits, ranks, actual/padded token counts, and component times are retained.

Measured stages: pair construction, tokenization, tensor construction, session inference, output conversion, sorting, total scorer wall time. Cached model/session construction was measured separately. Construction values were 2,189.84 / 91.30 / 105.96 ms in execution order (4/1/2 threads); initialization order/cache effects confound comparison, so these are **not** a thread-count speedup claim or OS-cold measurements.

For N20/four threads/batch16, the six warm observations had median total 84.37 ms and maximum 1,349.77 ms. Component medians: pairs 0.0015 ms, tokenization 5.31 ms, tensors 0.206 ms, inference 78.67 ms, conversion 0.078 ms, sorting 0.013 ms. Medians of components need not sum to median total. This is a small length-stratified probe, not an estimated workload p95.

At N20/four threads/batch1, warm median was 100.16 ms and maximum 455.68 ms. Padding ratio fell from 2.289 to 1.0. **Rejected as a transparent optimization:** changing batches changed candidate ranking in sampled calls. Across the entire grid 54/243 calls differed from the corresponding initial four-thread/batch16 ranking; repeated calls within a fixed configuration were rank-stable. One-thread and two-thread batch16 configurations preserved sampled orders but were slower in this grid.

**VERIFIED FACT:** Phase 7 constructs model/tokenizer/session outside query loops. The hybrid retriever does construct a short-lived executor per search. This experiment does not attribute its overhead.

**INFERENCE:** inference is the dominant sampled scorer cost; reducing padded computation is worth investigating, but a batch change must be treated as a ranking configuration change, not a free semantics-preserving speed fix.

**UNRESOLVED:** historical 12k total p95 cause; database retrieval/materialization decomposition; executor overhead; metadata copying; OS-cold load; isolated PostgreSQL/client CPU attribution; interaction of dynamic quantization and batching. No new end-to-end latency or concurrency improvement is claimed.

## Development selective reranking — MEASURED RESULT

The three deterministic policies consume candidate component ranks only:

1. `disagreement`: rerank unless lexical and semantic top1 agree; absent top1 counts as disagreement.
2. `no_lexical_winner`: rerank only if BM25 rank1 is absent from the fixed pool.
3. `top_rrf_not_lexical`: rerank if the first RRF candidate is not lexical rank1.

Existing Phase 7 MiniLM scores and frozen protection IDs were replayed; no new model was selected. All remaining candidates retain score ordering and RRF tie order. No label enters a runtime decision.

Development baseline MRR/nDCG@5: 0.86275/0.84734. Always-rerank: 0.90195/0.90514, 15 first-relevant-rank improvements and 5 regressions. Disagreement: 38.83% reranked, 0.89659/0.89749, 10 improvements/4 regressions. No-lexical-winner: 7.77% reranked, 0.88985/0.87398, 5 improvements/0 regressions. Top-RRF-not-lexical: 25.24% reranked, 0.89503/0.89555, 9 improvements/3 regressions. All six requested ranking metrics and per-query outcomes are in `phase8_audit.json`.

`no_lexical_winner` was selected for its conservative development cost/regression tradeoff, not maximum quality. The config was written before replay, SHA-256 `76f7439c29864dd9bea7b0efa0c9e0848f980fbad35e90acc931023322c655b1`. It binds the model-config file and development artifact hashes. Runtime cost is reported as model-call fraction, **not** a fabricated p95 estimate obtained by multiplying unrelated aggregate timings.

## Frozen holdout — MEASURED RESULT, gate FAILED

Exactly one Phase 8 replay used stored Phase 7 scores. There was no model inference rerun or post-result retuning. The result is a **reused-holdout diagnostic**, not an independent fresh confirmatory trial; Phase 7 outcomes were already visible before this task.

Including ambiguous cases, selective reranking called the model for 5/47 queries (10.64%). Hybrid / always / selective:

- Recall@1: 0.63830 / 0.70213 / 0.65957.
- Recall@5: 0.85106 / 0.95745 / 0.87234.
- Recall@10: 0.97872 / 1.00000 / 0.97872.
- MRR: 0.85162 / 0.89914 / 0.86261.
- nDCG@5: 0.80885 / 0.90873 / 0.82346.
- nDCG@10: 0.85547 / 0.92340 / 0.86393.

Selective transitions: 2 fixed, 2 regressed, 36 unchanged-correct, 7 unchanged-incorrect. Zero exact-overlap demotions. Paired 2,000-resample bootstrap, seed 812026:

- ΔRecall@1 +0.02128, 95% interval [-0.04255, 0.08511].
- ΔMRR +0.01099, [-0.03936, 0.06277].
- ΔnDCG@5 +0.01461, [-0.02942, 0.06104].

Excluding the two ambiguous cases does not change the conclusion; all intervals still cross zero. Full metrics and per-query evidence are in `phase8_holdout.json`. Individual-query resampling does not account for related template families; intervals are not deployment uncertainty bounds.

**REJECTED APPROACH:** promote the selective policy based on development improvements or reduced model-call count. It failed both the uncertainty and regression gates.

## Packing and token efficiency — DEVELOPMENT ONLY

Compared greedy with exactly three alternatives: reciprocal-rank/token density, one chunk per source, and whitespace-normalized exact-text deduplication. Each preserves whole chunks, input identity, deterministic ties, final input-rank order, and budget. Budgets: 256/512/1024/2048/4096. Results separately cover first 10 cached RRF candidates (default return-size proxy) and all 20; neither is misrepresented as a fresh database/API measurement.

At top10, every policy/budget has source recall 0.95146. At budget256, greedy uses mean 212.92 tokens and density approximately 211 tokens. At budgets≥512, greedy uses mean 225.38 tokens and unique-source uses 222.62. This tiny source-proxy saving does not prove preservation of answer-bearing evidence. Exact deduplication has no measured effect.

At N20/budget2048, unique-source uses 448.00 versus greedy 494.49 tokens with equal source recall 0.98058 (about 9.4% fewer tokens). **Not a production gain:** this policy may remove different answer-bearing chunks from the same source. Labels cannot detect that loss. It was rejected for promotion, not hidden as a failure.

Budgets above512 are inactive for most top10 cases; a budget-aware policy cannot demonstrate a useful quality improvement when relevant evidence already fits and relevance is only judged at source level. No packing configuration was selected for holdout. No combined-path trial was performed. This deliberately avoids spending a holdout test on an inadequately measured development improvement.

## Safety, validation, and scope limits

- No changes to tenant semantics, BM25, exact pgvector, production RRF, candidate depth logic, ContextAssembler, or API.
- No Phase 2–7 artifact/report overwritten; tests verify all 68 initial hashes.
- Offline records contain case-level evidence but are not exported as metric labels. No raw query/text/tenant/path added to telemetry labels.
- `uv sync --python 3.13`, Ruff and mypy passed. Alembic upgrade on `ctxd` and dedicated `ctxd_test` passed.
- Tests use `CTXD_TEST_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test`, not the requested existing `ctxd` database: integration fixtures truncate tables, and `ctxd` contained an existing tenant-a document. This deviation preserves existing data.
- Full PostgreSQL suite: **104 passed, 0 skipped**, including all PostgreSQL integration tests. Two dependency deprecation warnings are unrelated to this change.
- Scorer-only profiling is partial Milestone 1, not complete full-path instrumentation. Packing is development-only; milestones requiring successful quality gates were not run. No fresh service p50/p90/p95/p99, QPS or concurrency results were manufactured.

## Reproduction

Existing outputs use exclusive creation and are not overwritten. Read artifacts to reproduce analysis; use a separate disposable checkout/output location for any independent rerun. Do not erase the selected config or holdout output to retune.

Commands executed:

- `uv run python benchmarks/phase8_profile.py`
- `uv run python benchmarks/phase8_audit.py` (pre shared-helper repair)
- `uv run python benchmarks/phase8_freeze.py`
- `uv run python benchmarks/phase8_holdout.py`
- `uv sync --python 3.13`
- `uv run ruff check .`
- `uv run mypy`
- `CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd uv run alembic upgrade head`
- `CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test uv run alembic upgrade head`
- `CTXD_TEST_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test uv run pytest`

## Exact next recommendation — FUTURE, not started

Create independently judged, tenant-scoped **chunk/span evidence** cases with complementary same-source chunks and realistic token pressure. Split by query/template family before selection. Include natural technical queries and several evidence lengths that straddle each context budget. Pre-register source coverage and evidence coverage separately, then repeat packing selection on development and one fresh holdout. Do not reuse Phase 7 holdout for further selection.

In parallel only if separately authorized, finish full-path profiling on controlled fixed workloads. Treat any batch/quantization change as a new model configuration with output-equivalence tests and a new quality gate. The current limiting factors are evidence granularity/budget realism for packing and inference cost plus weak generalization for selective reranking.
