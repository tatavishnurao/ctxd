# Phase 9 — evidence-grounded context evaluation

## Result

**P3 — EVALUATION STILL INSUFFICIENT FOR PROMOTION.**

**R2 — RERANKING REMAINS INCONCLUSIVE.**

**Production behavior changed: NO.** No commits or pushes were made. Exact pgvector, BM25, the embedding model, RRF, ContextAssembler, and API modes are unchanged. The contribution is an offline evidence evaluation foundation and a fresh, explicitly synthetic stress benchmark—not a new retrieval feature or a production-performance claim.

The frozen packing candidate preserved holdout evidence but did not save tokens. A post-freeze provenance challenge shows why even identical text cannot always be merged safely. These negative results are retained.

## Ground truth and preservation

Work began at `a18c68d` with a clean working tree. Phase 8 code/evidence had been committed, notwithstanding its historical report describing its earlier uncommitted state. `benchmarks/phase9_phase8_freeze.json` freezes the Phase 8 report and JSON artifact hashes and records the base SHA, initial dirty state, Python, PostgreSQL, OS and relevant dependency versions. Phase 2–8 artifacts and corpora were not modified.

Verified production assembly: default API top_k=10 leads to 20 candidates per retrieval branch, followed by return-top10 and rank-order greedy whole-chunk packing. Candidate depth is not a universal constant for nondefault top_k. The experiment uses the default sizes; it does not change them.

## Evaluation architecture

New module: `ctxd/app/evals/evidence.py`.

- Evidence cases contain source/template family, tenant, query, review status, budget notes and evidence groups.
- Groups can be REQUIRED, SUPPORTING or OPTIONAL. All REQUIRED groups must be covered for full answerability.
- Alternatives are OR; **every span within a chosen alternative is AND**. Thus one group can require multiple chunks, and separate groups can represent complementary facts.
- Locators specify source path, exact chunk ID, exact excerpt, and half-open Unicode character offsets in normalized **chunk text**, not bytes or original-document offsets.
- Validation regenerates chunks using production `StructureAwareChunker` and checks identity/content, source, tenant, bounds and excerpt equality. Retrieval/selection validation rejects changed candidate text/cost/provenance and duplicated identities.
- `NEEDS_HUMAN_REVIEW` cases may have no assigned spans; they cannot be scored. Unknown labels are not replaced with invented evidence or vacuous answerability.
- Policies receive the existing label-free `SelectionCandidate` structure. Evidence annotations never enter a packing decision.

Correctness defenses include a discovered Python slicing trap: an oversized end offset can silently truncate and still match an excerpt. Explicit upper-bound checks now reject that case. Duplicate/overlapping labeled spans are token-unioned, preventing double-counted precision. Empty required-group sets cannot produce a spurious answerability score. These fixes concern the new evaluation layer, not production retrieval.

The schema supports joint alternatives and optional evidence; unit tests exercise them. Main benchmark cases express complementary obligations as separate required groups. They are not a claim that every supported schema shape has broad empirical coverage.

## Corpus and label construction

Main corpus: **24 cases, 120 documents, 140 production-generated chunks, 12 source/question-template families, 66 required-group instances and 138 span locators across cases**. Counts include the two query variants per family. There are **0 NEEDS_HUMAN_REVIEW cases** and **0 independently human-reviewed cases**: `VERIFIED_FIXTURE` denotes a verifiable authored contract, not independent assessment.

The source specifications are authored fictional technical contracts covering deadlines, rollback prerequisites, HTTP error behavior, retention periods, tenant key scope, worker bounds, ordered recovery steps, event exceptions, mandatory audit fields, configuration precedence, idempotency and wire compatibility. Every labeled excerpt actually exists in the stored corpus and was located before any retriever was run. Labels were not inferred from retrieval outputs or an LLM judge. There is no answer generation.

Each family includes normative sections, a copied first section explicitly labeled as an alternate source, and eight long archived/non-normative distractors containing query vocabulary. Several required facts share a document but occupy different chunks. This makes source correctness insufficient. Two query variants remain together per family.

**Limitations:** the fixture is small and adversarial by construction. Repeated maintenance prose and archived distractor scaffolding are synthetic, not sampled deployment traffic. Cross-family question semantics differ, but the common corpus-authoring style remains shared. Group separation does not establish broad domain independence. This corpus validates and stress-tests the evaluator; it cannot by itself justify a production promotion.

## Frozen split

`evals/phase9_evidence_cases.json` and `evals/phase9_split_manifest.json` were created before retrieval/model measurements.

- Seed: **902026**.
- Development: **16 cases / 8 families**.
- Fresh holdout: **8 cases / 4 families**: rollback, range, schema, compatibility.
- Training: none.
- Dataset canonical SHA-256: `c7dc6f1f55db1d62ec0e5ab698c6edb6c74f6817f880e93146820b50ee934cda`.
- Split canonical SHA-256: `175c7802a708c6670d0c73533d2a9704d44ae9931665d64412e6d3ca365171ce`.

Tests reject template-group, normalized identical-query, or tenant-scoped evidence-source crossing, check exact duplicate chunk text stays within a partition, and verify dataset/split checksums. The split was not rebalanced after discovering its difficulty distribution. In particular, holdout contains no case whose whole required context fits at 256 or 512 tokens; that imbalance is reported rather than fixed after inspection.

## Metric contract

**CTXD-specific evidence metrics (per query, then macro-averaged):**

- Required-evidence recall: represented required groups / required groups.
- Full answerability: 1 only when all required groups have a complete selected alternative. This is labeled-evidence coverage, not a claim about generated-answer correctness, consistency resolution or reasoning.
- Supporting recall: represented supporting groups / supporting groups. Absent supporting labels use an applicability flag; a zero in such a case does not mean a missing required fact.
- Span-token precision: union of approximate token positions intersecting any labeled selected span / all selected chunk tokens.
- Distractor-token fraction: tokens in selected chunks with no labeled span / selected tokens. Unlabeled surrounding prose inside evidence-bearing chunks is not classified as distractor-chunk tokens.
- Redundant-token fraction: selected labeled-span tokens beyond the deterministic cheapest complete alternative per group / selected tokens. This is annotation-scoped redundancy, not inferred semantic equivalence or a global minimum set cover. Partial alternatives are not called redundant just because they are incomplete.
- Required groups per 1k tokens: covered required groups ×1000 / selected tokens.

All use the production approximate word/punctuation counter, **not model/BPE billing tokens**. Empty packets have zero precision/efficiency and zero answerability. Fractions above are separate views, not a disjoint token partition. Macro-average efficiency is not aggregate covered groups divided by aggregate tokens.

**Standard IR diagnostics:** Recall@1/5/10, reciprocal rank and binary nDCG@5/10 use chunk IDs with required-span labels. Distinct alternate chunks are valid relevant IR items; collecting them can improve IR scores without adding a required fact. The evidence metrics, not IR scores alone, therefore drive selection. Retrieval diagnostics before packing and packet diagnostics after packing are both retained.

## Baseline and budget pressure

The canonical development baseline uses PostgreSQL, the existing pinned local embedding provider, exact semantic retrieval, BM25, parallel RRF and default production greedy assembly. A dedicated `ctxd_phase9` database was created and migrated. Only the partition being measured was ingested. Every ingested chunk was checked against the frozen corpus, and **every greedy selection was compared with an actual ContextAssembler call** at the same query, tenant, top_k and budget.

Budgets throughout: **256, 512, 1024, 2048, 4096** (all sequences below use this order).

Development greedy:

- Full answerability: **0.2500 / 0.3750 / 0.3750 / 0.2500 / 0.3125**.
- Required recall: **0.3750 / 0.4375 / 0.4375 / 0.421875 / 0.492188**.
- Supporting recall: **0.5000 / 0.5000 / 0.5000 / 0.6250 / 0.6875**.
- Mean selected tokens: **104.50 / 164.625 / 704.625 / 1725.938 / 3883.75**.
- Mean required groups per 1k tokens: **3.0667 / 2.7942 / 0.8789 / 0.4565 / 0.2551**.

Minimum whole-chunk cost to cover all required evidence ranges from **72 to 4,376 tokens**. Oracle costs use labels only for evaluation; no policy sees them. In development, corpus-level feasibility rises from 25% at256 to87.5% at4096. The top10 retrieval set is fully answerable within4096 in75% of cases, yet greedy achieves31.25%. All measured query-budget cells drop at least one retrieved chunk.

Budget pressure is real, but so is candidate scarcity: 25% of development top10 sets lack a complete required alternative set even without a restrictive budget. At holdout4096, all cases are corpus-feasible but only50% are top10-feasible, and greedy achieves25%. A packer cannot recover evidence absent from its input.

**Nonmonotonicity is observed, not a metric error:** a larger budget may admit an earlier large distractor that a smaller budget skipped, leaving less room for later required chunks. Greedy therefore need not preserve answerability monotonically as its budget increases.

## Why source-level evaluation was insufficient

`phase9_source_proxy_gap.json` records **13 query-budget cells** where source-only group coverage would say fully answerable but exact-span coverage does not. For example, `procedure-0` at2048 selects chunks from the required source but preserves only two of eight required recovery steps (recall0.25).

Position diagnostics in `phase9_case_analysis.json` track groups classified by the minimum ordinal of their alternatives. At development4096, 13/18 first-chunk group instances are selected versus3/24 later-chunk instances. These counts are confounded by family, query and chunk length and are **not a causal position-bias estimate**. They do expose loss of later evidence that source-only metrics conceal.

## Development packing frontier and selection

Compared greedy with exactly three existing Phase 8 alternatives:

1. Reciprocal-rank/token density.
2. Unique-source suppression.
3. Whitespace-normalized exact-text deduplication.

All operate on the same return-top10 candidates and preserve whole-chunk identities; output order is restored to retrieval rank. No evidence labels, expected answers, case IDs or categories enter policy functions.

The selection script and runner hashes were recorded in `phase9_protocol.json` before development evaluation. Eligibility required zero per-case-budget regressions in full answerability, required recall and supporting recall; no aggregate token increase; and either ≥5% token reduction or increased answerability. Eligible candidates were ordered by total answerability, then tokens, then policy name. This considers evidence preservation before token reduction.

- Density: zero regressing cells; 28 answerable cells across16×5 observations, versus25 for greedy; 104,379 total selected tokens versus105,335.
- Unique-source: **two regressing cells**, 24 answerable cells; rejected despite fewer tokens.
- Exact-text deduplication: zero regressing cells; 28 answerable cells; **103,918 total selected tokens**, a development reduction of about1.35%.

Density has the best development4096 answerability (0.4375 versus greedy0.3125). Exact deduplication ties its answerability summed across budgets and spends fewer tokens, so the prewritten rule selects **exact_duplicate**. The80 case-budget observations are repeated measurements of16 queries, not80 independent examples.

Configuration SHA-256: `16baf32b1159a2095290a08cd0307d4986dd901dc51e673622492a88a73ea2e1`. It binds dataset, split and development evidence. It was frozen before holdout; no thresholds, policies, labels or split were retuned afterward.

## Existing MiniLM evidence replay — DEVELOPMENT ONLY

Only the existing Phase 7 MiniLM-L6 was used: revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`, local pinned quantized ONNX, batch16, four threads, maximum pair length512, existing lexical protection. Artifact identity, scores, scorer timings and selected candidate IDs are retained. No new model/backend was introduced, and no batch tuning was performed. Pair truncation remains the frozen model behavior; this study does not isolate its causal effect.

Always-rerank full answerability across budgets: **0.25 / 0.3125 / 0.3125 / 0.25 / 0.3125**. At512 and1024 it loses required evidence for `error_contract-0`. At4096 it regresses required recall for four queries (`procedure-0`, `event-0`, `event-1`, `precedence-1`) and improves one (`retention-1`); mean required recall is0.4375 versus hybrid0.492188. Broad exact-query-token-overlap MRR demotions occur in six4096 cases; this is not a rare-identifier-only metric.

The frozen Phase 8 selective rule (`no_lexical_winner`) fires on **0/16** development queries, so its outputs equal hybrid. This dataset provides no positive evidence for that gate's usefulness. No reranker was selected for holdout. Conclusion: **R2**, not evidence of a general model win or grounds to stop all reranking work for v1.

## Fresh holdout — one run

The holdout runner validated dataset/split/config hashes and created a durable start marker before retrieval. It compared only greedy and the frozen packing policy. Stored results were subsequently analyzed without rerunning retrieval or selecting another policy.

Both policies have identical holdout evidence results:

- Full answerability: **0 / 0 / 0 / 0 / 0.25**.
- Required recall: **0 / 0.291667 / 0.291667 / 0.375 / 0.416667**.
- Supporting recall: **0 / 0.625 / 0.625 / 0.875 / 0.5**.

Greedy mean tokens: **0 / 281.75 / 817 / 1867.875 / 3770.875**. Candidate: **0 / 281.75 / 817 / 1867.875 / 3810.125**.

**At equal full answerability, tokens saved: 0 at the first four budgets; −39.25 tokens/query at4096** (about1.04% more tokens, not savings). **At equal budget, required-evidence improvement: 0 at every budget.** At4096 the macro required-groups-per-1k-token metric declines from0.39476 to0.38570. Eliminating duplicate spans did not improve packet efficiency because later distractor chunks filled the freed space.

All requested IR metrics, token fractions and selected identities are retained in `phase9_holdout.json`; no aggregate claim substitutes for those records.

## Uncertainty and case-level findings

Paired **2,000-resample template-cluster bootstrap**, seed902026, separately for each budget, over the four holdout families. Entire groups are resampled together, preserving within-template dependence.

- Δfull answerability, Δrequired recall and ΔnDCG@5: point0 and empirical95% interval[0,0] at every budget, since every observed paired difference is zero.
- Δselected tokens: point0, interval[0,0] through2048.
- At4096: **+39.25**, interval **[+0.25, +78.25]** selected tokens.

Degenerate zero intervals do **not** establish population equivalence. Four synthetic clusters provide weak uncertainty resolution and no deployment-shift coverage. This is not a fresh human-judged production-domain holdout, despite being fresh and separated from development measurements.

No holdout evidence group was lost or gained. Three4096 packets changed: `rollback-0` added157 tokens, `schema-0` added156, `compatibility-0` added1. Required spans remained represented through valid alternatives; later fitting chunks increased cost. `phase9_case_analysis.json` includes each query, required groups, baseline/candidate chunk IDs, evidence groups lost/gained and signed token savings. There are no hidden evidence regressions in the canonical holdout.

## Optional post-freeze challenge

A separate **one-case, two-document** fixed-order synthetic challenge was authored after the main holdout. It is stress characterization, not an independent inferential sample or production retrieval run. Both resource documents contain the same sentence, but the query requires documentary evidence for **each** resource; one source cannot establish the other's setting.

At budget256:

- Greedy: 12 tokens, required recall1, full answerability1.
- Frozen exact deduplication: 6 tokens, required recall0.5, full answerability0.

This is a provenance counterexample to treating text equality as universal evidence equivalence. Nothing was tuned on it. The case and result are in `evals/phase9_challenge_cases.json` and `benchmarks/phase9_challenge.json`. The earlier case-analysis artifact's challenge status reflects its creation before this optional run.

## Validation and limitations

New tests cover schema/locator/tenant/bounds validation, required/optional/joint semantics, alternative evidence, overlap-safe token accounting, independent resource provenance, budget pressure, identity preservation, deterministic grouped splitting, duplicate-query leakage, template bootstrap reproducibility and frozen artifact consistency.

Final validation: **122 tests passed, 0 skipped**, including PostgreSQL integration tests; Ruff passed; mypy passed; `uv sync --python 3.13` passed; migrations passed.

The requested `ctxd` database was migrated. Destructive integration tests ran on `ctxd_test`, not `ctxd`, to preserve its existing document. Measurements used the separately created `ctxd_phase9` database. No application tables were truncated for benchmarks, and fixture data remains in the dedicated benchmark database for inspection. Two dependency deprecation warnings are unrelated to Phase 9.

Main limitations: synthetic repetitive distractors, twelve families/four holdout clusters, no independent human judgment, budget-difficulty imbalance across groups, and source/question-family grouping rather than proof of universal semantic independence. Timing samples are diagnostics only. The historical one-second reranker latency cause remains unresolved. No latency, capacity, production token saving, or generated-answer improvement is claimed.

## Reproduction and important files

Outputs are exclusively created; start markers prevent silent repeated holdout runs. Do not delete them to retune. Independent reruns need a disposable checkout/output workspace and a fresh migrated dedicated database. Canonical semantic hashes differ from file-byte hashes; the experiment manifest records byte checksums as well.

Execution order:

1. Freeze Phase 8 metadata/checksums.
2. `uv run python benchmarks/phase9_build.py`
3. Record premeasurement protocol/selector hashes; create and migrate dedicated database.
4. `CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_phase9 uv run python benchmarks/phase9_run.py development`
5. `uv run python benchmarks/phase9_select.py`
6. `CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_phase9 uv run python benchmarks/phase9_run.py holdout`
7. `uv run python benchmarks/phase9_analysis.py` (source-proxy gap was initially computed as a read-only posthoc command and is now included here for reproduction).
8. `uv run python benchmarks/phase9_challenge.py`
9. Validation, documentation and final experiment manifest.

Important new files:

- `ctxd/app/evals/evidence.py`
- `tests/test_evidence_eval.py`, `tests/test_phase9_artifacts.py`
- `benchmarks/phase9_build.py`, `phase9_run.py`, `phase9_select.py`, `phase9_analysis.py`, `phase9_challenge.py`, `phase9_finalize.py`
- `evals/phase9_evidence_cases.json`, `phase9_split_manifest.json`, `phase9_challenge_cases.json`
- `benchmarks/phase9_phase8_freeze.json`, `phase9_protocol.json`, development/holdout start markers
- `benchmarks/phase9_baseline.json`, `phase9_packing_dev.json`, `phase9_reranker_replay.json`
- `benchmarks/phase9_development_pools.json`, `phase9_holdout_pools.json`
- `benchmarks/phase9_development_budget_pressure.json`, `phase9_holdout_budget_pressure.json`
- `benchmarks/phase9_selected_config.json`, `phase9_holdout.json`, `phase9_bootstrap.json`
- `benchmarks/phase9_case_analysis.json`, `phase9_source_proxy_gap.json`, `phase9_challenge.json`, `phase9_experiment_manifest.json`
- `PHASE9_REPORT.md`; updates to README, ARCHITECTURE, BENCHMARKS and PERFORMANCE.

## Exact next milestone recommendation — NOT STARTED

Use the new schema to annotate an independently sourced technical corpus with a human-reviewed subset, including source-specific obligations and complementary same-source chunks. Freeze more independently authored template families and balance budget-feasibility strata **before** retrieval. Pre-register evidence-preservation and cost gates, then use a new holdout; do not recycle Phase 9 holdout for selection. Keep production greedy and reranking offline until that evidence supports a trial.
