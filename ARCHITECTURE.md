# Implemented architecture

Checked against `main` at `59099df` on 2026-10-10. This document describes current implementation, not an aspirational agent platform.

## Production-reachable / supported path

```text
FastAPI -> RuntimeServices (application lifespan)
  ingestion -> loader -> StructureAwareChunker -> DocumentStore.replace_document
                                                documents/chunks/postings/embeddings
  query -> ContextAssembler
              lexical: BM25Retriever
              semantic: SemanticRetriever -> embedding provider -> exact search
              hybrid: both in parallel -> deterministic RRF
           -> greedy whole-chunk selection -> ContextPacket
```

`ctxd/app/runtime.py` constructs the storage, ingestion, retrievers and assembler. Literal defaults in `config/settings.py` and `models/domain.py` are memory storage, fake embeddings and lexical queries. Explicit PostgreSQL + Model2Vec configuration enables the supported production-style path; the server default mode stays lexical and hybrid is requested explicitly. There is no production reranker wiring.

## Ingestion

`ingestion/loaders.py` loads UTF-8 text/Markdown, normalizes line endings and constructs tenant/source-scoped identities and SHA-256 content hashes. `ingestion/chunking.py` handles headings, paragraphs, fenced code and lists, with oversized-block splitting. Default chunk target/max/overlap: 400/600/40 approximate tokens. The regex token counter is deterministic, not an LLM tokenizer. `ingestion/service.py` embeds chunks and replaces complete document state; identical ingestion reuses state. Idempotency is keyed on content *and* embedding version: unchanged content stored under another embedding version is re-embedded in place.

## Storage and consistency

`storage/documents.py` provides protocols and in-memory implementation; `storage/postgres.py` provides pooled transactional persistence. Tables: documents, chunks, lexical_corpus_stats, lexical_terms, lexical_postings and chunk_embeddings. Composite tenant keys/FKs prevent cross-tenant references. Replacement locks document identity and tenant corpus statistics, updates chunks/postings/statistics/embeddings atomically, and rolls back failures. MVCC readers see committed states. Startup verifies migration `0002_phase4`; requests never create tables. Multiple application instances share PostgreSQL state.

Default pool min/max: 1/10; connection timeout: 5 seconds; query timeout: 5000 ms. Migrations are an explicit deployment step. Exact vector search has no default HNSW index.

## Lexical retrieval

`retrieval/lexical.py`, `retrieval/index.py` and backend posting search maintain tenant-local chunk N, df, tf and average length. BM25 uses k1=1.5, b=0.75; repeated query terms retain frequency weighting. PostgreSQL scores posting matches without rebuilding the corpus at query time. Deterministic score ordering uses chunk IDs for ties.

## Semantic retrieval

`retrieval/semantic.py`: real backend is Model2Vec `minishlab/potion-base-8M@bf8b056651a2c21b8d2565580b8569da283cab23`, normalized 256-dimensional vectors and cosine search. PostgreSQL uses exact pgvector; memory uses exact scan. FakeHashEmbeddingProvider is a configured development/test fixture and the out-of-box default—not real semantic quality. Real model availability, cache and offline provisioning are deployment dependencies.

## Fusion and assembly

`retrieval/hybrid.py` runs lexical/semantic branches with a two-worker executor and unions candidates. RRF is sum of `1/(k+rank)`, default k=60, with chunk-ID tie-breaking and component scores/ranks retained. Branch depth is explicit constructor configuration or `max(top_k, min(100, top_k * 2))`; default top_k=10 happens to yield 20. There is no public candidate-depth configuration field.

`context/assembler.py` preserves returned order and selects whole candidates that fit; it skips those that do not and continues. It never silently truncates chunk content. Metadata records counts, selected tokens and budget drops. `requested_mode` is what the client asked for; `retrieval_type` names only the branches that actually returned candidates (`hybrid`, `lexical`, `semantic` or `none`), with per-branch counts in `branch_candidate_counts`. If the semantic branch returns short while the tenant has chunks embedded under another version, the packet carries `warnings: ["embedding_version_mismatch"]` and `stale_embedding_chunks`. Candidates carry only computed signals (`relevance_score` plus provenance metadata). Budgets use approximate tokens. API modes are lexical/semantic/hybrid only. A request without `retrieval_mode` uses the server default: `CTXD_DEFAULT_RETRIEVAL_MODE` if set, otherwise lexical regardless of embedding provider (see `docs/BEIR_EVAL.md`).

## API, trust and failure boundaries

`api/auth.py` derives the request tenant from a verified credential: static API keys bound to one tenant each, or HS256 JWTs with a required tenant claim and `exp`. The development-only `none` mode trusts the `x-tenant-id` header and is refused by settings validation in any other environment. Body or header tenants that differ from the credential's tenant get 403; `/metrics` requires a separate operator token. `/health` is static liveness; `/ready` probes storage (`SELECT 1` on PostgreSQL) and the embedding model and returns 503 when either fails. Storage and embedding-model failures map to 503; database statement timeouts and the request deadline (`CTXD_REQUEST_DEADLINE_MS`, default 10 s, must exceed the database query timeout) map to 504; documents over `CTXD_MAX_DOCUMENT_CHARS` map to 413; successful empty retrieval is 200. Settings refuse PostgreSQL + fake embeddings without `CTXD_ALLOW_FAKE_EMBEDDINGS`. QueryResponse's answer explicitly says inference is not implemented. ModelDecision/ToolCall/ToolResult schemas do not implement execution.

## Observability

`observability/` supplies structured logging, request/trace IDs, Prometheus metrics and OpenTelemetry spans. Metrics/spans cover database/index/retrieval/assembly work. HTTP metrics are labeled by route template (`unmatched` for unknown paths), and hybrid branches run in a copy of the request context so spans and log fields stay attached; raw text, tenant IDs and queries are not telemetry labels. OTLP export is optional. Missing operational SLOs and client-only historical CPU profiles remain limitations, not readiness claims.

## Offline evaluation (not runtime policy)

`evals/retrieval.py`: Recall/MRR/nDCG, duplicate-source gain credited once without compressing chunk ranks. `evals/phase7.py` and `analysis.py`: offline ranking analysis. `evals/context_selection.py`: experimental selectors. `evals/evidence.py`: exact tenant/source/chunk spans, AND required groups, OR alternatives, joint spans, budget metrics and clustered bootstrap. `evals/review.py`: hash-bound human review gates and exact feasibility. Mechanical validation does not prove evidence sufficiency or reviewer identity.

Phase 10 tools operate on the historical 121-case revision. Phase 10B builder produces 106 unreviewed candidate objects/diagnostics; it is not a completed canonical dataset pipeline. Synapse/MCP integration is a separate evaluator over schemas/invocation results and synthetic fixtures, not an agent tool runtime.

## Experimental / rejected

`reranking/` contains an offline Reranker protocol, fake fixture, FlashRank TinyBERT adapter and wrapper with RRF fallback. Benchmarks use pinned MiniLM/BGE ONNX helpers independently. Runtime and API do not import reranking/evaluation modules. TinyBERT is rejected; MiniLM/selective reranking inconclusive and offline. Alternative packing cannot replace greedy. Tested HNSW recall loss prevents default promotion. See EXPERIMENTS.md, not these classes' existence, for decisions.

## Future only

Authentication hardening, readiness/capacity/recovery work and reviewed ground truth are roadmap items. LLM inference, model routing, agent/tool execution, sandboxing, distributed jobs and streaming/frontend are not implemented.
