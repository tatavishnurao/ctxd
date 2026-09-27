# Phase 6 report: evaluation hardening, reranker forensics, and reproducibility

1. **Scope.** Phase 6 audited Phase 5 evidence, relevance judgments, TinyBERT failures, and benchmark repeatability. It did not add a model, production mode, API behavior, ANN work, or Phase 7 work.

2. **Base state.** Measurements use base SHA `aa900dd9eef79b0a39cae30dbd553605aa36c1ef` with the already-uncommitted Phase 4/5 working tree retained.

3. **Phase 5 freeze.** `benchmarks/phase5_artifact_manifest.json` records SHA-256, byte count, description, environment, and model identity for all ten Phase 5 JSON artifacts. `tests/test_phase5_artifact_manifest.py` fails if one changes.

4. **Environment.** Python 3.13.15, PostgreSQL 17.11, WSL2 kernel 6.6.87.2, 24 logical CPUs, and 8,020,120 KiB guest memory were recorded. PostgreSQL used `en_US.utf8` and emitted the known collation-version warning during validation.

5. **Corpus preservation.** `evals/retrieval_semantic.json` remains unchanged. The separate audited corpus is `evals/retrieval_semantic_phase6_audited.json`.

6. **Judgment policy.** The audit uses binary relevance. The fixture has no independent assessor evidence that would support defensible 0/1/2 grades, so subjective graded labels were not invented.

7. **Annotation result.** Of 150 cases, 148 were confirmed, zero corrected, zero independently expanded, and two marked ambiguous. Every audit record has the query, old sources, audited sources, binary grades, notes, and status in `evals/phase6_annotation_audit.json`.

8. **Ambiguous labels.** `semantic-031` and `semantic-032` ask the identical question, “What does Java use here?”, but originally had mutually exclusive language and coffee labels. Both plausible sources are relevant in the audited copy; the cases remain explicitly `ambiguous` pending human intent clarification.

9. **Exact duplicates.** Normalized-content hashing found zero exact duplicate document clusters.

10. **Near duplicates.** Same-tenant normalized-token Jaccard at the declared 0.70 threshold found zero near-duplicate document pairs. This is distinct from evaluation cases intentionally testing semantically adjacent documents.

11. **Equivalent evidence.** Eight label-derived clusters capture sources that independently support the same evaluation fact: five four-document shared-group clusters and three paraphrased semantic pairs.

12. **Semantic similarity is not duplication.** The embedding audit flags 100 same-tenant pairs above cosine 0.80 as different facts with similar language. Most are templated generated service documents. They are analysis signals, not automatic duplicate labels.

13. **Duplicate/equivalence impact.** Ninety-six queries explicitly accept equivalent sources. Twelve TinyBERT regressions occur in the multiple-relevant category, while one RRF ordering was penalized by labels despite returning equivalent evidence. Duplicate-aware evaluation matters, but it does not explain most TinyBERT regressions.

14. **Original-label baseline reproduction.** Hybrid exactly reproduces Phase 5: R@1 0.680, R@5 0.907, R@10 0.973, MRR 0.86135, nDCG@5 0.84415, and nDCG@10 0.86886.

15. **Audited-label baseline.** Hybrid remains R@1 0.680, R@5 0.907, and R@10 0.973. MRR rises to 0.86468, nDCG@5 to 0.84662, and nDCG@10 to 0.87132 because the two Java cases now accept both plausible answers.

16. **Candidate recall.** Audited hybrid candidate recall remains 0.893/0.973/0.987/1.000 at depths 5/10/20/50. Annotation changes did not alter the candidate-depth conclusion.

17. **Oracle headroom.** At depth 20, the audited deterministic oracle reaches MRR 1.000 and nDCG@5/nDCG@10 0.98968/0.98968. The theoretical reorder-only headroom remains material.

18. **Upper-bound decomposition.** Of 150 queries: 119 are already RRF top-1 correct, four have a relevant candidate present but low, two are annotation-ambiguous, one is duplicate/equivalent-sensitive, and 24 are difficult in both component rankings. No depth-20 query lacks every relevant source.

19. **TinyBERT input contract.** FlashRank receives `[raw query, raw chunk content]` pairs with BERT `[CLS]/[SEP]` handling, lowercase tokenization, right padding, and no prompt. Paths and metadata are omitted. No empty or malformed pair was found.

20. **Model metadata.** The audited package is `cross-encoder/ms-marco-TinyBERT-L-2-v2`, a BERT sequence classifier with a 512-position limit. Input construction matches FlashRank's pairwise implementation; no formatting defect was found.

21. **Truncation policy.** FlashRank applies right-directed `longest_first` pair truncation at 512 tokens. The source-level relevance audit uses the first RRF chunk per labeled source as its chunk proxy and excludes additional same-source chunks from both score classes.

22. **Truncation result.** Sixty-four of 2,881 candidate pairs exceeded 512 tokens, but none was a relevant proxy. The ten answer-bearing long-chunk candidates were 314 tokens, had 0.444 pairwise accuracy, regressed 10/10 times, and moved down by 10 ranks on average. Their failures are long-input/domain failures, not labeled-evidence truncation.

23. **Relevant score distribution.** Across 214 relevant proxies, mean score was 0.6780, median 0.99957, and standard deviation 0.4553. This strongly bimodal distribution makes one global score threshold unsuitable.

24. **Nonrelevant score distribution.** Across 2,656 wrong-source candidates, mean score was 0.2793, median 0.000485, standard deviation 0.4194, and p90 0.99978. Many nonrelevant candidates saturate near one, producing severe overlap with relevant scores.

25. **Score separation.** Within-query pairwise score accuracy was 0.9227. Exact, tenant-isolation, and distractor-heavy cases separate well; long-chunk cases are worst, while morphology and semantic-paraphrase cases expose weaker separation. Full category distributions are in `benchmarks/phase6_score_distribution.json`.

26. **Reranker quality and transitions.** Audited N20 TinyBERT scores R@1/R@5/R@10 `0.613/0.867/0.880`, MRR `0.77429`, and nDCG@10 `0.80214`, all below audited hybrid. It has nine fixes, 93 unchanged-correct, 12 unchanged-incorrect, and 36 rank regressions. The original-label Phase 5 result remains frozen in its manifest.

27. **Regression taxonomy.** Overlapping evidence labels identify 26 lexical exact-match demotions, 23 score-compression cases, 16 score inversions, 12 multi-relevant evaluation sensitivities, and two near-duplicate confusions. Counts overlap and therefore do not sum to 36.

28. **Regression concentration.** The 36 regressions comprise 12 multiple-relevant, ten long-chunk, seven morphology, three semantic-paraphrase, two near-duplicate, one exact, and one distractor-heavy case.

29. **Query-type signal.** Exact-identifier/code-like queries regress at 23/80 (28.8%); multiple-concept queries at 16/65 (24.6%); morphological-variation queries at 9/40 (22.5%); and natural-language questions at 6/49 (12.2%). Regressed queries are shorter on average: 2.89 versus 3.66 tokens overall.

30. **RRF true failures.** After audited labels, 29 queries have a relevant depth-20 candidate but not at rank one. Diagnosis yields 23 component-rank interactions, three semantic-rank overweighting cases, two lexical-rank overweighting cases, and one duplicate/equivalence case. This is diagnostic decomposition, not evidence for retuning RRF.

31. **Strict performance protocol.** Each corpus/mode has five independent measured runs, 20 warmups per run, 100 queries per run, model preload, stable corpus, alternating mode order, component timings, raw samples, and robust outlier marking. Cold model and first-query timings are separated.

32. **Sequential reproducibility.** Median-of-run p50/p95/p99 was 26.57/30.82/32.13 ms for 1.2k hybrid and 40.63/50.23/52.38 ms reranked; 24.28/26.88/27.74 versus 39.44/49.51/51.17 ms at 12k; and 57.00/64.91/70.73 versus 85.03/96.02/100.34 ms at 50k. Reranking remains slower at every size.

33. **Run variability and outliers.** Hybrid p95 ranges were 28.53–31.14 ms at 1.2k, 26.02–28.22 ms at 12k, and 64.82–68.81 ms at 50k. The old clustered 1.2k cross-component spikes did not recur: 1.2k robust outliers were BM25-dominant and no same-run/query outlier appeared in both modes. The previous root cause is still **UNRESOLVED**, not proven environmental.

34. **Concurrency and goodput.** Throughput plateaus around concurrency 8–16 and latency rises sharply beyond it; reranking does not improve the knee. At 50k/concurrency 8, median-run QPS is 30.3 hybrid versus 21.9 reranked, with p95 288.8 versus 370.9 ms. Median 100 ms goodput is 17.32 versus 11.29 requests/s at 50k; synthetic top-5 quality remains 100% for both and is not semantic quality evidence.

35. **Validation and artifacts.** Reusable analysis code covers normalization, duplicate overlap, score distributions, pairwise accuracy, token buckets, query features, robust outliers, and run aggregation. New tests cover these utilities and the frozen Phase 5 manifest. Phase 6 JSON artifacts use new filenames and retain raw evidence where needed.

36. **Decision gates.** Evaluation is materially harder and trustworthy enough for the current binary fixture, with two explicit ambiguities and a documented source-to-chunk proxy limitation. TinyBERT failure is best explained by score/domain behavior and lexical demotion—not an input-format bug or relevant-evidence truncation. **TinyBERT remains REJECTED; reranking remains non-production and unexposed.** The 1.2k historical tail cause remains **UNRESOLVED**. Keep exact pgvector, parallel RRF, and candidate depth 20. Before any future reranker experiment, add independently judged candidate-level relevance and preregister category-level non-regression gates; do not begin Phase 7 from this result.
