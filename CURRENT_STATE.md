# Current engineering state

Consolidation base: `83352ac`. Maturity: **research checkpoint with a tested retrieval prototype**, not a production-certified agent runtime. Start with this file, README and ARCHITECTURE; then EXPERIMENTS and ROADMAP (approximately 30 minutes).

## What ctxd is

A context-retrieval and assembly system intended for AI-agent workloads. It returns a ContextPacket, not generated answers. No agent loop, LLM inference, model router, tool sandbox, SSE or frontend is implemented.

## Implemented and retained

- Deterministic text/Markdown ingestion and structure-aware chunking.
- Tenant-scoped in-memory storage or transactional PostgreSQL documents, postings and embeddings; migrations, restart persistence and connection pooling.
- BM25, semantic retrieval and parallel deterministic reciprocal-rank fusion.
- Real pinned Model2Vec embeddings and exact pgvector search when explicitly configured.
- Greedy whole-chunk budget assembly; oversized candidates are dropped, not truncated.
- FastAPI ingestion/query/statistics/metrics endpoints; bounded metrics, tracing and explicit storage/timeout errors.

**Actual out-of-box defaults:** memory storage, fake hash embeddings, lexical query mode. `docker compose up` instead runs PostgreSQL + Model2Vec with hybrid as the server default, and PostgreSQL + fake embeddings is refused unless explicitly allowed. Fake embeddings are fixtures, not meaningful semantic retrieval. Production-style deployment must explicitly select PostgreSQL, `CTXD_EMBEDDING_PROVIDER=model2vec`, and hybrid query mode. Hybrid branch depth is explicit constructor configuration or `max(top_k, min(100, top_k * 2))`; it is not universally 20.

Tenant header/body matching and tenant-scoped SQL enforce namespaces. The header is client supplied: authentication/authorization must be supplied by a trusted deployment boundary. `/health` is static liveness; `/ready` probes storage and the embedding model.

## Experimental and rejected

Offline-only: `ctxd/app/reranking/`, `ctxd/app/evals/`, benchmark model helpers and Synapse/MCP fixture evaluation. None is wired into the production request path.

TinyBERT is rejected for measured quality regression. Tested HNSW is rejected as a default because recall degraded. MiniLM-L6 improved one holdout ranking metric, not general retrieval; selective reranking remains inconclusive. Alternative packing is not ready for promotion. Keep exact retrieval, deterministic RRF and greedy assembly. Details: EXPERIMENTS.md.

## Blocked benchmark

**PHASE 10: PRE-REVIEW / NON-CANONICAL / BLOCKED.** Independent reviews: zero.

Phase 10 historical dataset: 121 drafts. Phase 10B candidate build: 106 drafts (34 retained, 72 new); EASY 25, MEDIUM 33, HARD 36, VERY_HARD 12, INFEASIBLE 0. The 87 unselected historical cases are not deleted and do not yet have a complete per-case disposition audit. HARD+VERY_HARD = 48/106 (45.3%). Costs are approximate tokens, not model billing tokens.

`benchmarks/phase10b_build.py` regenerates validated corpus objects and measures feasibility, but only prints candidate diagnostics: it does not persist a finished revision, complete a semantic annotation audit, or create a Phase 10B review packet/split. Successful exact-span construction does not certify necessary/sufficient evidence or contextual provenance. Phase 10 review tooling/packet applies to the older 121-case revision, not automatically to these 106 cases. No Phase 10B review batches, completed leakage audit, or final fresh split exist. Do not score a holdout.

## New validation (this consolidation)

Python 3.13 environment synchronized. Ruff passed. Configured mypy passed (51 application source files; not every benchmark/test script). Migrations on user-authorized `ctxd_test` succeeded at `0002_phase4`; PostgreSQL 17.11, pgvector 0.8.6. Full pytest: **154 passed, zero failures/errors/skips**, two dependency deprecation warnings. Candidate builder separately succeeded with the counts above. This is code/integration validation, not completed benchmark-review validation. See docs/engineering_validation.json.

## Unresolved / out of scope

Historical shared-host latency anomaly and reranker tails remain causally unresolved. Approximate tokens, synthetic workloads and small evaluation sets constrain claims. Deployment authentication, capacity/SLO evidence and operational recovery deserve engineering work. No algorithm tuning, new reranker, packing promotion, canonical scoring or runtime expansion is part of this checkpoint. Git checkpoint suggestions are in ROADMAP.md; no commit or push is authorized for this pass.
