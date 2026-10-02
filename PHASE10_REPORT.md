# Phase 10 — Technical evidence benchmark foundation

**Status: BLOCKED / PARTIAL MILESTONE. PROVISIONAL — NOT INDEPENDENTLY REVIEWED.**

The review tooling, source-grounded draft corpus, feasibility measurements, diagnostic tests and pre-review split are implemented. The requested **independently reviewed, budget-balanced canonical benchmark is not complete**. Neither retrieval/packing experiments nor final holdout scoring were run. There are no new quality, latency or promotion claims.

## 1. Preservation and scope

- Base: `60ccda005fe0283dfd2f1443a5155baeccfe40b7` (`main`). Initial `git status --short` and `git diff --stat` were empty.
- `benchmarks/phase10_history_freeze.json` records hashes of every base-tracked file, Python/platform/dependency information and the initial-tree observation. The hash capture occurred after the first offline review-module draft, but before corpus construction or retrieval work; it does not pretend otherwise.
- All base-tracked files, including Phase 2–9 evidence, reports, production code, migrations, dependency lock and CI configuration, remain unchanged. Only new Phase 10 files and an offline evaluation module/tests were added. The finalizer verifies every base-file hash.
- No commits or pushes. No Phase 11 work. No database corpus ingestion, model loading, LLM judging/inference, answer generation, query rewriting, new ranking algorithm or runtime/API mode.
- The only database used during this phase was dedicated `ctxd_test` for existing PostgreSQL integration validation. Application `ctxd` and previous phase databases were not reset.

## 2. Corpus and provenance

`evals/phase10_evidence_cases.json` contains **121 questions, 25 authentic pinned repository files, 92 production-generated chunks and 15 source/subsystem groups**. There is one benchmark tenant. Questions and labels are newly agent-authored, not observed production traffic or independently human-authored examples.

The sources are 24 implementation/migration files and one README, copied from the base revision without synthetic padding. Python files enter the existing content-ingestion/chunking representation as TEXT; the production file loader was not extended to accept `.py`. README uses MARKDOWN. All chunks regenerate exactly under the unchanged production chunker.

`evals/phase10_source_manifest.json` records revision, SHA-256, pinned repository URL, source type, transformation and permission basis for every file. These are user-authorized repository-local materials, not scraped third-party documentation. No root LICENSE was found at the pinned revision; redistribution rights are **not inferred**.

Questions cover API contracts and failures, runtime configuration, ingestion/idempotence, chunk identity/boundaries, BM25/RRF, semantic model versions, PostgreSQL transactions/isolation, in-memory indexing, experimental reranking, tracing/logging, tool-evaluation contracts, migrations and deployment instructions. This is broader than repetitive synthetic prose, but remains a small, single-repository code-understanding corpus—not broad technical-domain coverage.

Proposed labels comprise **198 REQUIRED, 4 SUPPORTING and 4 OPTIONAL groups**, with **383 span-locator instances** across alternatives. Five groups have multiple alternatives, arising from copies of the same physical excerpt in overlapping production chunks; this is **not** a rich independently reviewed set of semantic alternatives. Only **3 questions require multiple source files**. These limitations matter more than the nominal query count.

Authoring inputs are preserved in `evals/phase10_authoring.tsv`. `evals/phase10_source_locators.json` provides original-file character/line coordinates in addition to the chunk-local half-open offsets in the corpus. Repeated snippets use the first matching physical occurrence, preferring complete code lines. This deterministic locator choice is not a semantic sufficiency check: reviewers must inspect the intended function/branch and correct misleading anchors.

## 3. Review status and workflow

- Independent human reviews: **0**.
- Author status: **121 DRAFT**, zero VERIFIED_BY_AUTHOR.
- Reviewer status: **121 UNREVIEWED**, zero APPROVED/CORRECTED/DISPUTED.
- Corpus status: **121 NEEDS_HUMAN_REVIEW**.
- Semantic ambiguity count: **unknown**, not zero. Zero DISPUTED records means no completed dispute reviews, not evidence that all labels are sound.

`PHASE10_REVIEW_PACKET.md` includes every question, partition, family, proposed feasibility, exact excerpts, source links, case checksum and pending reviewer state. Review must assess clarity, minimality, sufficiency, alternative completeness, negative claims, joint requirements and provenance—not merely literal string matches.

`benchmarks/phase10_review.py` accepts explicit human-authored submissions. They bind dataset, case and previous review-state hashes and require an independent declared identity, timezone-aware date, attestation and notes. Self-review, missing credentials and stale submissions are rejected. Each output is exclusively created; parent-state hashes retain the review chain.

**This is an attestation workflow, not identity authentication.** External evidence of genuine human review must be retained. The assistant has not supplied or simulated any benchmark approval. Synthetic reviewer names in unit tests are test fixtures only and never enter benchmark artifacts.

CORRECTED is not approval: changed labels require a separate dataset revision and fresh review. A CORRECTED record cannot be turned into approval of unchanged labels through intervening status changes. DISPUTED requires an explicit documented resolution. Source-text equality never makes independently required resources interchangeable.

Canonical eligibility requires all 39 holdout cases plus at least 41 of 82 development cases, covering every development family, independently approved. Additionally, **every case contributing to canonical metrics must be approved**; unreviewed development cases cannot silently enter a canonical average. Review completion alone would not fix the separate design failures below.

### Versioned correction commands

Retain this revision, old review rounds, external review evidence and the revised TSV. A future authorized correction can use:

```bash
uv run python benchmarks/phase10_build.py \
  --authoring /path/to/versioned-authoring.tsv \
  --author-id actual-revision-author \
  --output-root /path/to/new-phase10-revision

uv run python benchmarks/phase10_review.py render \
  --revision-root /path/to/new-phase10-revision \
  --output /path/to/new-phase10-revision/REVIEW_PACKET.md

uv run python benchmarks/phase10_check.py \
  --revision-root /path/to/new-phase10-revision
```

A different independent human must review a human-authored correction. Revisions reset reviews rather than carrying old approvals onto changed data. The builder uses the original pinned source revision; broadening the source inventory needs an explicitly documented new corpus version. Preserve earlier assignments and manifests as historical evidence; do not revise a holdout using retrieval outcomes.

## 4. Fresh pre-review split, not a completed final holdout

Seed `1002026` groups by source/subsystem family: **82 development / 39 holdout**, with ten development and five holdout groups. Holdout groups are API, context assembly, runtime, semantic retrieval and Synapse evaluation. Exact-query, template and evidence-source overlap across partitions is rejected.

Dataset hash: `59d59de6350279834c611ff9b30ee68b11e3577ba2a2db348b50d13327e91748`.

Assignment hash: `f2bcdfb47d8faac28e94732935796976584659cae56533ab8fcee401418a7ae1`.

`evals/phase10_split_manifest.json` explicitly labels this a **frozen pre-review assignment**. Labels/source text were visible during authoring and review-packet construction; retrieval outcomes have never been observed. It is not a fully blinded, independently reviewed canonical holdout. Subsystem grouping controls obvious leakage but does not prove independent authorship or statistical independence between groups from the same repository.

## 5. Measured budget feasibility

**These are annotation-based feasibility counts, not retrieval or answerability benchmark scores.** Costs use the production approximate word/punctuation counter, not model/BPE tokens.

The oracle enumerates REQUIRED alternatives, ANDs their spans, and minimizes the union of necessary whole chunks. It separately reports a union-of-span-token lower bound; exploiting that lower bound would require an unimplemented span selector. Repeated/overlapping labels do not receive duplicate cost credit. Excessive oracle state growth fails explicitly rather than guessing.

Whole-chunk minima range **89–1,608 tokens**. Proposed span minima range **7–84 tokens**. Thus these questions are predominantly small factual/code-contract questions even where the chunk representation makes their assembly expensive.

Number of corpus cases whose proposed complete evidence can fit:

- Budget 256: **26/121** overall; development 17/82, holdout 9/39.
- Budget 512: **104/121**; development 69/82, holdout 35/39.
- Budget 1024: **114/121**; development 75/82, holdout 39/39.
- Budget 2048: **121/121**; development 82/82, holdout 39/39.
- Budget 4096: **121/121**; development 82/82, holdout 39/39.

Whole-chunk strata:

- EASY (≤512): **104**, including 69 development / 35 holdout.
- MEDIUM (513–1024): **10**, including 6 development / 4 holdout.
- HARD (1025–2048): **7**, all development.
- VERY_HARD (>2048): **0**.

The distribution fails the recorded design gate: each partition needs at least two examples per stratum and no stratum above 70%. EASY represents 86.0% overall and 89.7% of holdout. Holdout has no HARD or VERY_HARD examples. We did not pad excerpts, inflate required context, invent difficult evidence, or move cases after retrieval to satisfy quotas.

The design thresholds were recorded after an initial label-only feasibility inspection and before any retrieval. This is transparent design-stage screening, **not a fully blinded preregistration**. `benchmarks/phase10_feasibility.json` retains the actual distribution and query-kind breakdowns.

## 6. Retrieval-versus-packing diagnostics

New offline `ctxd/app/evals/review.py` distinguishes:

- A: no complete required alternative retrieved (`RETRIEVAL_MISS`).
- D: relevant source retrieved but not its required chunk (`WRONG_CHUNK`, also a retrieval miss).
- Corpus evidence cannot fit at this budget (`INSUFFICIENT_BUDGET`).
- B: retrieved alternatives exceed budget (`BUDGET_DROP`), versus a feasible retrieved subset omitted by selection (`PACKING_ORDER`).
- C: all required groups selected (`SELECTED`).
- E: candidate text/cost/representation changed (`OTHER` plus `REPRESENTATION_ERROR`).
- Additional diagnostics: label-safe removable duplicate text (`DUPLICATE_WASTE`), missing independently required provenance despite matching text (`PROVENANCE_CONFLICT`), and an explicitly disputed annotation (`ANNOTATION_AMBIGUITY`).

Flags can overlap. Duplicate text is not declared waste merely because it is equal: removal must preserve labeled alternatives and useful partial evidence. These diagnoses are constrained by annotation completeness and do not infer semantic contradictions from strings. Correlated flags are not proof of causal performance effects.

Unit tests exercise these distinctions, including independently required equal-text resources. **No real-corpus failure frequencies or representative retrieval failures are reported**, because retrieval has not run. The diagnostic tests are synthetic unit fixtures, not new benchmark observations.

## 7. Experiment status and metric contract

`benchmarks/phase10_protocol.json` fixes budgets, unchanged production retrieval settings, the existing greedy baseline and at most three existing alternatives: density, exact-text deduplication and unique-source suppression. It specifies development-only selection gates, an explicit none outcome, provenance safeguards, configuration hashes before any comparative holdout, and at least **2,000 paired template-cluster bootstrap resamples** if a legitimate comparison becomes possible.

Allowed reranker replay is restricted to the existing Phase 7 MiniLM-L6 + lexical protection and Phase 8 selective rule, on development only. There are no new rerankers or learned policies. Production top_k=10 implies depth20 per branch; depth20 is not a universal runtime constant for other top_k values.

Current results are **NOT_RUN**, not zeros:

- PostgreSQL lexical/semantic/hybrid benchmark: blocked.
- Packing comparisons and candidate selection: blocked; selected policy is null.
- Reranker replay and latency measurements: blocked.
- Final holdout and bootstrap intervals: blocked; zero holdout runs and no start marker.
- Recall/MRR/nDCG, evidence recall/answerability, token precision/redundancy, packing savings and failure frequencies: unavailable.

Standard binary chunk IR metrics remain distinct from CTXD-specific evidence/group and token-budget metrics. Source coverage must not be presented as preserved answer evidence. No bootstrap was fabricated from annotation counts or synthetic unit tests.

`benchmarks/phase10_check.py` returns exit **2** with machine-readable review/design failures before database/model access. It is an eligibility checker, not an implemented end-to-end benchmark runner. Execution, selection and uncertainty reporting remain deferred work; the protocol alone is not evidence those experiments have been implemented or completed. `benchmarks/phase10_blocked_status.json` preserves this boundary explicitly.

## 8. Decisions

- **C1 — retain production greedy packing.** No reviewed Phase 10 evidence supports changing it. This is a conservative retention decision, not a finding that greedy statistically dominates alternatives.
- **R2 — reranking remains inconclusive and offline.** Phase 10 supplies no new replay result or latency resolution.
- **E3 — evaluation foundation is insufficient for canonical comparison/promotion.** Zero independent reviews, sparse multi-source requirements, one-repository scope, insufficient challenging strata and weak holdout coverage prevent a stronger decision.

Phase 9's provenance counterexample still applies. Previous TinyBERT rejection and unresolved full-path latency questions are not overturned.

## 9. Validation

Python **3.13.15**, `uv sync --python 3.13`, full-repository Ruff, strict application mypy and Alembic upgrade passed. PostgreSQL has migration `0002_phase4` and pgvector `0.8.6`.

Full PostgreSQL-enabled pytest: **154 passed, 0 failed, 0 errors, 0 skipped**, including all **11 PostgreSQL integration tests**. There are 32 new tests and two existing dependency deprecation warnings. Test validation is not benchmark validation or independent annotation review.

`benchmarks/phase10_validation.json` records command output and JUnit checksums/counts. `benchmarks/phase10_experiment_manifest.json` seals new artifact hashes and confirms preservation of base-tracked files. The artifact test also regenerates the draft from pinned source snapshots without requiring Git history in shallow CI checkouts.

## 10. Exact next-phase recommendation

**Do not start optimization or production promotion in Phase 11.** If explicitly authorized, prioritize independently authored/reviewed technical benchmark curation: realistic multi-document operational questions, genuine competing versions and provenance obligations, more independent source families, and measured HARD/VERY_HARD coverage in both partitions. Do not manufacture hardness by padding labels.

First complete a separately versioned Phase 10 corpus and genuine independent review, then implement/run the preregistered PostgreSQL baseline and diagnose retrieval versus packing failures. Freeze any development-selected policy before a newly eligible grouped holdout; use at least 2,000 template-cluster resamples and report uncertainty. Do not reuse Phase 7/9 holdout outcomes to select policies. Keep production unchanged throughout. **This recommendation has not been started.**
