# Engineering consolidation audit

## Repository boundary

Initial base `83352ac` on main; `git status --short` and `git diff --stat` empty. The inspected last 30 commits contain the Phase 10 foundation, incomplete Phase 10B candidate work and lint repair. No dirty/untracked accumulated code existed at the start. Consolidation edits documentation only; no algorithms, API behavior, historical reports, candidate labels or review state were changed. No commits/pushes.

## Reachability and code disposition

- **KEEP — production reachable:** main/lifespan, runtime, API/middleware, ingestion, storage, retrieval, context, models/config and observability. Runtime imports BM25 and semantic retrieval; assembler constructs hybrid. No runtime/API import of reranking or offline evaluation was found.
- **KEEP — offline rejected experiment:** `ctxd/app/reranking/{base,fake,flashrank,retriever}.py`. TinyBERT adapter/wrapper unused by production, but benchmarks/tests preserve forensic evidence and fallback contracts. Not dead merely because rejected.
- **KEEP — offline evaluation:** `ctxd/app/evals/{retrieval,analysis,phase7,context_selection,evidence,review}.py`; evidence/review tests. These support reproducibility, not public modes.
- **KEEP — offline model helpers:** `benchmarks/phase7_models.py`, profiling and frozen-study scripts. MiniLM/BGE artifacts remain optional external dependencies; no runtime promotion.
- **KEEP — separate integration evaluator:** `ctxd/app/integrations/synapse/` and docs/SYNAPSE_EVAL.md. Synthetic tool-invocation schema/result evaluation; no sandbox or tool runtime.
- **ARCHIVE LATER:** immutable old phase benchmark scripts/artifacts can move only with an explicit manifest/link/test migration. Scripts use sibling imports and hard-coded phase paths; moving files blindly would break replay. Leave in place now.
- **UNCERTAIN — forward-looking schemas:** ModelDecision, ToolCall, ToolResult in domain.py are placeholders; QueryResponse still references them. Removing them may change API schemas. They do not prove implementation.
- **REMOVED — dormant configuration:** `Settings.redis_url` had no runtime consumer and was removed with the unused Compose Redis service (Phase C). Settings ignore unknown `CTXD_` variables, so an old `CTXD_REDIS_URL` is harmless.
- **KEEP — unfinished candidate helpers:** `phase10b_fetch.py` pins sources; `phase10b_build.py` only constructs/prints drafts; exclusive-write `save()` currently has no caller. Do not advertise a completed export/review workflow.
- **SAFE TO REMOVE (generated only):** ignored `__pycache__` and temporary `/tmp/phase10b_catalogs` diagnostic catalogs, if not needed locally. They are not durable benchmark evidence and are not removed here.

Ruff reports no flagged dead imports. This is import/reference inspection, not formal whole-program dead-code proof. No source code deleted.

## Documentation drift resolved

README formerly described universal depth20 and overemphasized production maturity. ARCHITECTURE mixed future runtime blocks and old phase snapshots. Replaced both with current scope/defaults and separate experimental/future boundaries. PERFORMANCE and BENCHMARKS retain every historical measurement while gaining current navigation/status sections. Phase reports, including their measurement-time base SHAs, remain unchanged; consolidation does not rewrite historical circumstances.

## Top five technical risks

1. Zero independent review and incomplete case/leakage/provenance audit: benchmark cannot justify promotion.
2. Client-supplied tenant identity is not authentication; deployment trust/authorization is external.
3. Fake embedding/memory/lexical defaults can be mistaken for the real persistent hybrid path; model provisioning must be explicit.
4. Shared-host/synthetic performance and unresolved tails cannot establish production capacity/SLOs; large postings and exact vector scans remain scaling costs.
5. Approximate token budgets and text-based dedup assumptions can violate downstream model budget/evidence requirements; preserve whole-chunk/provenance semantics until reviewed evidence exists.

## Validation distinction

Full current code suite passed with zero PostgreSQL skips. Candidate builder successfully regenerated exact corpus objects and costs. Neither is equivalent to complete semantic annotation audit, independent review, leakage validation or canonical readiness. Configured mypy covers 51 application files, not all benchmark/test scripts. Dependency deprecations are retained in validation record.
