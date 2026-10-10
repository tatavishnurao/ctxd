# Current engineering state

Checked against `main` at `59099df` on 2026-10-10. Maturity: **research checkpoint with a tested retrieval prototype**, not a production-certified agent runtime. Start with this file, README and ARCHITECTURE; then EXPERIMENTS and ROADMAP (approximately 30 minutes).

## What ctxd is

A context-retrieval and assembly system intended for AI-agent workloads. It returns a ContextPacket, not generated answers. No agent loop, LLM inference, model router, tool sandbox or SSE is implemented; the only frontend is the local inspector dashboard in `tools/dashboard/`.

## Implemented and retained

- Deterministic text/Markdown ingestion and structure-aware chunking.
- Tenant-scoped in-memory storage or transactional PostgreSQL documents, postings and embeddings; migrations, restart persistence and connection pooling.
- BM25, semantic retrieval and parallel deterministic reciprocal-rank fusion.
- Real pinned Model2Vec embeddings and exact pgvector search when explicitly configured.
- Greedy whole-chunk budget assembly; oversized candidates are dropped, not truncated.
- FastAPI ingestion/query/statistics/metrics endpoints; bounded metrics, tracing and explicit storage/timeout errors.

**Actual out-of-box defaults:** memory storage, fake hash embeddings, lexical query mode. `docker compose up` instead runs PostgreSQL + Model2Vec with lexical as the server default (hybrid per request), and PostgreSQL + fake embeddings is refused unless explicitly allowed. Fake embeddings are fixtures, not meaningful semantic retrieval. Production-style deployment must explicitly select PostgreSQL, `CTXD_EMBEDDING_PROVIDER=model2vec`; hybrid is opt-in per request or via `CTXD_DEFAULT_RETRIEVAL_MODE`. Hybrid branch depth is explicit constructor configuration or `max(top_k, min(100, top_k * 2))`; it is not universally 20.

Tenant-scoped SQL enforces namespaces. Outside development the tenant is derived from an API key or JWT (header-only access is refused at startup); in development the client-supplied `x-tenant-id` header is trusted and labeled `auth_mode=none`. `/health` is static liveness; `/ready` probes storage and the embedding model.

## Experimental and rejected

Offline-only: `ctxd/app/reranking/`, `ctxd/app/evals/`, benchmark model helpers and Synapse/MCP fixture evaluation. None is wired into the production request path.

TinyBERT is rejected for measured quality regression. Tested HNSW is rejected as a default because recall degraded. MiniLM-L6 improved one holdout ranking metric, not general retrieval; selective reranking remains inconclusive. Alternative packing is not ready for promotion. Keep exact retrieval, deterministic RRF and greedy assembly. Details: EXPERIMENTS.md.

## Blocked benchmark

**PHASE 10: PRE-REVIEW / NON-CANONICAL / BLOCKED.** Independent reviews: zero.

Phase 10 historical dataset: 121 drafts. Phase 10B candidate build: 106 drafts (34 retained, 72 new); EASY 25, MEDIUM 33, HARD 36, VERY_HARD 12, INFEASIBLE 0. The 87 unselected historical cases are not deleted and do not yet have a complete per-case disposition audit. HARD+VERY_HARD = 48/106 (45.3%). Costs are approximate tokens, not model billing tokens.

`benchmarks/phase10b_build.py` regenerates validated corpus objects and measures feasibility, but only prints candidate diagnostics: it does not persist a finished revision, complete a semantic annotation audit, or create a Phase 10B review packet/split. Successful exact-span construction does not certify necessary/sufficient evidence or contextual provenance. Phase 10 review tooling/packet applies to the older 121-case revision, not automatically to these 106 cases. No Phase 10B review batches, completed leakage audit, or final fresh split exist. Do not score a holdout.

## Validation

As of `main` at `59099df` (2026-10-10):

- **CI** (PostgreSQL 17 + pgvector, real Model2Vec, migrations down and back up): `ruff check`, `ruff format --check`, configured mypy, and pytest **241 passed, 0 skipped**, 2 dependency deprecation warnings.
- **Local, no database or model configured:** pytest **221 passed, 20 skipped**. The 20 skips are the 18 PostgreSQL tests and 2 Model2Vec smoke tests, which need `CTXD_TEST_DATABASE_URL` and `CTXD_RUN_MODEL2VEC=1`. Configured mypy covers 52 application source files, not every benchmark/test script.

This is code/integration validation, not completed benchmark-review validation. `docs/engineering_validation.json` is the earlier record taken at `83352ac` (2026-10-02: 154 passed, PostgreSQL 17.11, pgvector 0.8.6); the Phase 10B candidate counts above come from that pass and were not re-run since.

## Unresolved / out of scope

Historical shared-host latency anomaly and reranker tails remain causally unresolved. Approximate tokens, synthetic workloads and small evaluation sets constrain claims. API-key/JWT authentication exists, but deployment hardening, capacity/SLO evidence and operational recovery deserve engineering work. No algorithm tuning, new reranker, packing promotion, canonical scoring or runtime expansion is part of this checkpoint.
