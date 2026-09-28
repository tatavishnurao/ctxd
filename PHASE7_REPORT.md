# Phase 7 report: frozen holdout reranker evaluation

1. **Scope.** Phase 7 froze a development/holdout split, compared candidate rerankers only on development, tested label-free lexical protections, froze one configuration, and evaluated it once on holdout. Reranking remains an offline experiment. Production BM25, exact pgvector, parallel RRF, N=20 candidates, ContextAssembler, retrieval modes, and API behavior are unchanged. Phase 8 was not started.

2. **Base and environment.** Split source is corpus SHA `e9486b0a339d5df1830251e1ec3eb6e81e005d35502877b6ccd1ea085192c164`, based on `c00d75132c0b2a22958692d7b58d7fb79cfd7e82`. Evaluation ran on Python 3.13.15, PostgreSQL 17, WSL2 Linux 6.6.87.2, 24 logical CPUs, CPU-only ONNX Runtime, with 4 intra-op threads for selected inference.

3. **Split freeze.** `evals/phase7_split_manifest.json` contains a deterministic, stratified 103-development/47-holdout partition, SHA-256 `66bce2d758247004dd2a57225ef049d7a6117a98b4981d30e55526895a15cc92`. Exact duplicate-query leakage is zero. The two ambiguous Java cases remain together in holdout and are never used to choose the model or protection rule.

4. **Candidate protocol.** Candidate pools are fixed before reranking: parallel BM25 plus exact pgvector, deterministic RRF (`k=60`), depth 20. Model comparisons reorder this same pool; they do not add/remove candidates. Candidate recall@20 is 0.981 development and 1.000 holdout for hybrid.

5. **Baseline blinding caveat.** Partition baseline artifacts (including holdout RRF) were materialized before reranker selection as fixed retrieval references. The selection script and frozen config consume development-only model/guardrail evidence; no holdout reranker/guardrail output was read before freeze. Because holdout baseline summaries existed, this was not complete baseline-metric blinding; treat the holdout comparison as a small confirmatory check, not a pristine sealed challenge set.

6. **Judgments.** The original 150-case corpus and binary labels are preserved. The two contradictory identical “What does Java use here?” judgments remain ambiguous; holdout metrics are reported both including and excluding them. No graded labels or LLM judge were introduced.

7. **Candidate survey.** TinyBERT remained a negative control. The two new measured candidates were `cross-encoder/ms-marco-MiniLM-L-6-v2` and `BAAI/bge-reranker-base`. `mixedbread-ai/mxbai-rerank-xsmall-v1` was held as an unrun alternate; BGE-reranker-v2-m3 was excluded before evaluation because no pinned efficient ONNX path was available and its heavyweight backend/dependency footprint was disproportionate. Survey/provenance: `benchmarks/phase7_model_survey.json`.

8. **Pinned model identities.** TinyBERT revision `81d1926f67cb8eee2c2be17ca9f793c7c3bd20cc` (Apache-2.0); MiniLM revision `233902d25c440f23af6f7d6e94d2946bac0bee0a` (Apache-2.0); BGE-base revision `2cfc18c9415c912f9d8155881c133215df768a70` (MIT). Their pinned ONNX/tokenizer hashes and byte sizes are recorded in the survey, development output, and selected-config manifest.

9. **Footprint and compatibility.** The selected MiniLM AVX2 quantized ONNX file is 23,200,716 bytes; tokenizer is 711,396 bytes; total cached model files are 23,912,112 bytes. Maximum input is 512 tokens. The BGE ONNX file is 1,112,459,588 bytes and its cached footprint is about 1.13 GB. The selected experiments added zero Python dependencies; all model files were pinned and loaded locally/offline. No PyTorch model path was added.

10. **Development baseline.** Hybrid RRF achieved R@1/R@5/R@10 `0.680/0.913/0.951`, MRR `0.86292`, nDCG@5 `0.84734`, nDCG@10 `0.86255`. Lexical and semantic baselines, including category metrics, are in `benchmarks/phase7_development_baseline.json`.

11. **Development model quality.** TinyBERT: MRR `0.77687`, nDCG@5 `0.7903`, 5 fixed and 24 regressed. MiniLM: MRR `0.90114`, nDCG@5 `0.89768`, 9 fixed and 6 regressed. BGE-base: MRR `0.91497`, nDCG@5 `0.91105`, 10 fixed and 5 regressed. Full per-query ranks, categories, model scores, latency, and inversions are in `benchmarks/phase7_dev_model_comparison.json`.

12. **Category results.** Pairwise accuracy was TinyBERT/MiniLM/BGE: morphology `.878/.964/.953`; multiple relevant `.952/.996/.987`; long chunk `.444/.810/1.000`; semantic paraphrase `.908/.890/.965`; near duplicate `.987/1.000/1.000`. The small category samples are descriptive, not independent confirmatory tests. Detailed evidence: `benchmarks/phase7_pairwise_analysis.json`.

13. **Score inversions.** Using the declared per-query check that the highest nonrelevant candidate score is at least the highest relevant candidate score, inversion counts were TinyBERT 35, MiniLM 15, and BGE 15. They are overlapping forensic indicators, not additive failure categories.

14. **Exact-match losses before protection.** The development exact-match audit found TinyBERT 13 ordinary and 7 catastrophic demotions; MiniLM 2 ordinary and 2 catastrophic demotions; BGE 3 ordinary and zero catastrophic demotions. Exact-match analysis is in `benchmarks/phase7_exact_match_analysis.json`.

15. **Protection rules.** Tested only on development: protect lexical top-1; protect lexical top-1 with exact normalized query-token overlap; and protect a strong lexical/identifier winner using a predeclared relative-score margin of 0.50. Signals are runtime candidate/query text only—no ground-truth source, case category, labels, or query rewriting.

16. **Development guardrail outcomes.** MiniLM with exact-overlap top-1 protection had MRR `0.90215`, nDCG@5 `0.90514`, 6 fixed and 5 regressed. Its exact-match cases were 79 preserved, 5 improved, 2 demoted, zero catastrophic demotions, and zero relevant sources lost from the fixed pool. Guardrail costs and alternative-rule results are in `benchmarks/phase7_guardrail_dev.json`.

17. **Frozen configuration.** Before any holdout reranker scoring, configuration SHA-256 `4e8ffdf7877ce452774445ef3d71182dd0f0c024ed29cb35e7fa991d30688049` selected pinned MiniLM-L6, CPU ONNX, N=20, batch size 16, four intra-op threads, plus `protect_exact_overlap_top1`. Its checksummed rule puts a BM25-rank-1 candidate with at least one exact normalized query-token overlap first; the remaining fixed candidates sort by model score with RRF rank as a stable tie-breaker. It never uses labels, query categories, or a tuned score threshold.

18. **Holdout protocol.** `benchmarks/phase7_holdout_once.py` refuses to overwrite existing output, validates the frozen configuration and split hashes, checks local model artifact identity, and scores only holdout candidate pools. It writes per-query ranks/scores and 1,000-resample paired bootstrap evidence. No model, feature, rule, threshold, or metric was retuned after looking at holdout.

19. **Holdout baseline.** Hybrid RRF: R@1/R@5/R@10 `0.638/0.851/0.979`, MRR `0.85162`, nDCG@5 `0.80885`, nDCG@10 `0.85547`, candidate recall@20 `1.000`.

20. **Holdout selected result.** Frozen MiniLM+guard: R@1/R@5/R@10 `0.702/0.957/1.000`, MRR `0.89914`, nDCG@5 `0.90873`, nDCG@10 `0.92340`, candidate recall@20 `1.000`. Point deltas: Recall@1 `+0.06383`, MRR `+0.04752`, nDCG@5 `+0.09988`.

21. **Ambiguity sensitivity.** Excluding the two ambiguous cases, baseline/selected MRR is `0.84503/0.89466`, nDCG@5 `0.80035/0.90467`, and Recall@1 `0.64444/0.71111`. The selected point estimate remains higher on all three.

22. **Uncertainty.** Paired query-level percentile bootstrap, 1,000 resamples, including ambiguous cases: ΔMRR 95% CI `[-0.0124, 0.1117]`; ΔnDCG@5 `[0.0412, 0.1660]`; ΔRecall@1 `[-0.0213, 0.1702]`. Excluding ambiguous cases: ΔMRR `[-0.0115, 0.1123]`; ΔnDCG@5 `[0.0370, 0.1711]`; ΔRecall@1 `[-0.0222, 0.1778]`. Only nDCG@5 has a positive interval in both views; MRR and Recall@1 uncertainty crosses zero. These intervals reflect this small query sample, not corpus shift.

23. **Rank transitions.** Including both ambiguous cases: 4 fixed, 2 regressed, 36 unchanged-correct, 5 unchanged-incorrect. Fixed cases: `exact-subject-05`, `exact-subject-07`, `morphology-12`, `morphology-19`. Regressions: `morphology-06` (rank 1→4), `morphology-17` (2→5).

24. **Regression guardrails.** No baseline rank≤3 result fell below rank 10; no catastrophic regression occurred. Rank delta (baseline minus selected; missing source treated as rank 21): +10 or more 0; +5–9 2; +1–4 7; unchanged 36; −1 to −4 2; −5 to −9 0; −10 or worse 0.

25. **Exact-match holdout.** Of 39 exact-overlap cases, 36 were preserved and 3 improved. There were zero ordinary or catastrophic exact-match demotions and no relevant source disappeared from the fixed candidate set or after protection.

26. **Semantic and difficult cases.** Semantic/paraphrase improvements: zero. Near-duplicate regressions: zero. Multiple-relevant regressions: zero. The two rank regressions were morphology cases. Full case-level evidence is in `benchmarks/phase7_holdout.json`.

27. **Bootstrap artifact.** `benchmarks/phase7_bootstrap.json` records the paired method, both ambiguity policies, seeds, resamples, point estimates, and interval endpoints. The per-query holdout file is the audit trail; neither is a model-selection input.

28. **Standalone N=20 timing.** Repeated selected-MiniLM timing over 515 development query/candidate-set evaluations: tokenization p50/p95/p99 `8.07/11.66/15.27 ms`; inference `133.80/1,843.53/2,164.68 ms`; total `142.32/1,857.31/2,179.32 ms`. The long tail was observed on this shared WSL2 CPU and is retained, not trimmed.

29. **Sequential benchmark protocol.** `benchmarks/phase7_performance.py` used only the frozen configuration, 10 warmups, five independent runs, 50 queries per run/mode, alternating mode order, fixed candidate depth 20, and generated 12-chunk documents. It compared the production hybrid path to hybrid-20 plus local rerank and top-5 selection. These are end-to-end retrieval timings, not API/server latencies.

30. **1,200 chunks.** Hybrid p50/p95/p99 `10.40/13.58/16.88 ms`, 85.87 QPS. Selected config `177.71/218.49/240.98 ms`, 5.57 QPS.

31. **12,000 chunks.** Hybrid `64.41/117.43/169.73 ms`, 15.92 QPS. Selected config `324.59/1,021.93/1,334.22 ms`, 2.36 QPS.

32. **50,004 chunks.** Hybrid `66.42/79.87/101.62 ms`, 14.68 QPS. Selected config `204.77/247.06/278.67 ms`, 4.75 QPS. The nonmonotonic 12k/50k results and large observed tails are a shared-host caveat, not a causal diagnosis.

33. **Concurrency protocol.** Since the frozen selected configuration had higher holdout point estimates, both paths were measured at concurrency 1/4/8/16 on 12k and 50,004 chunks, 32 queries per level, one shared PostgreSQL pool (max 32), synchronized batches. Each cell completed with zero errors. CPU is client-process CPU, not PostgreSQL server CPU; RSS is process maximum.

34. **12k concurrency.** Hybrid QPS at 1/4/8/16: `15.76/30.61/39.04/47.29`; p95 `79/153/212/319 ms`. Selected QPS: `3.49/6.24/8.48/10.64`; p95 `322/685/1,091/1,665 ms`. At concurrency 16 selected client CPU was about 14.7 core-equivalents; pool wait was 12 ms.

35. **50k concurrency.** Hybrid QPS: `15.15/24.75/27.44/29.57`; p95 `70/164/292/529 ms`. Selected QPS: `4.76/7.44/8.48/9.53`; p95 `243/572/967/1,770 ms`. At concurrency 16 selected client CPU was about 13.4 core-equivalents; pool wait was 644 ms. No errors occurred.

36. **Quality/latency frontier.** Development MRR rises from hybrid `.863` to TinyBERT `.777`, MiniLM `.901`, and BGE `.915`; MiniLM+guard is `.902`. The paired development scorer p95s were about 75 ms TinyBERT, 2,175 ms MiniLM, and 13,871 ms BGE. The repeated selected-MiniLM N20 p95 was 1,857 ms; selected 12k end-to-end p95 was 1,022 ms. These timings have different scopes and substantial host variance, so they are separate frontier coordinates—not a strict apples-to-apples scalar ranking. `benchmarks/phase7_frontier.json` captures the comparison and caveat.

37. **Goodput and bottleneck.** Goodput was not used as a decision metric: available generated marker workloads have a 100% top-5 quality pass and cannot provide a quality-varying good-request rate. CPU inference dominates added latency and worsens concurrent throughput; this benchmark does not establish a general hardware-independent bottleneck or service capacity.

38. **Decision — B, interesting but inconclusive.** Keep reranking offline and unexposed. The frozen result materially improves nDCG@5 with a positive bootstrap interval and has no exact-match demotions, but MRR/Recall@1 uncertainty crosses zero, only four cases are fixed versus two regressed, and CPU latency/throughput costs are substantial. No production reranking mode, flag, endpoint, or default was added.

39. **Phase 8 recommendation (not started).** If separately authorized, build a larger independently judged technical-query set and obtain repeated isolated CPU/GPU measurements under a declared latency budget. Require confirmatory gains in primary ranking metrics, tighter uncertainty, zero catastrophic/exact-match regressions, and acceptable concurrent cost before any production proposal. Do not use this holdout for another selection cycle.

40. **Validation.** Ruff and mypy passed. The full PostgreSQL-backed test suite passed: 73 passed, 0 skipped (including all integration tests); two pre-existing dependency deprecation warnings were reported.

41. **Reproduction and artifacts.** Split: `benchmarks/phase7_freeze_split.py`; baselines/pools: `benchmarks/phase7_baselines.py`; development comparison: `benchmarks/phase7_compare_dev.py`; protections: `benchmarks/phase7_guardrails_dev.py`; frozen config: `benchmarks/phase7_freeze_selected_config.py`; one-shot holdout: `benchmarks/phase7_holdout_once.py`; latency/concurrency: `benchmarks/phase7_performance.py`. Machine-readable evidence uses `phase7_` prefixes. The one-shot evaluator refuses to overwrite holdout artifacts; do not clear them to retune or rerun the selected configuration.
