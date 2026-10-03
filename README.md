# ctxd — context retrieval and assembly

A context-runtime / retrieval-engineering prototype for AI-agent workloads. **Maturity: research checkpoint**, with a tested retrieval core; not a complete agent runtime or production-certified service.

Implemented: deterministic ingestion, tenant-scoped storage, BM25, semantic retrieval, parallel deterministic RRF and token-bounded whole-chunk ContextPackets.

**Not implemented:** LLM inference, model routing, production/public reranking, tools/sandbox, agent loop, SSE or frontend. `/v1/query` returns retrieved context and an explicit inference-not-implemented placeholder.

```text
Documents -> structure-aware chunks -> documents/postings/embeddings
                                          |
Query -> BM25 + exact semantic search -> parallel deterministic RRF
                                          |
                              greedy ContextAssembler -> ContextPacket
```

Defaults are **memory + fake fixture embeddings + lexical queries**. The supported production-style path is explicit **PostgreSQL + pinned real Model2Vec + exact pgvector + hybrid queries**. Candidate depth depends on request/configuration, not a universal 20. Tenant headers require a trusted authentication boundary.

## Quickstart

```bash
uv sync --python 3.13
uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

Both POST endpoints require `x-tenant-id` matching the body's `tenant_id`. Example:

```bash
curl localhost:8000/v1/documents -H 'content-type: application/json' \
  -H 'x-tenant-id: demo' -d '{"tenant_id":"demo","source_path":"hello.txt","source_type":"text","content":"ctxd assembles whole chunks within a token budget."}'
curl localhost:8000/v1/query -H 'content-type: application/json' \
  -H 'x-tenant-id: demo' -d '{"tenant_id":"demo","query":"token budget","retrieval_mode":"lexical"}'
```

### Persistent, real-embedding path

```bash
docker compose up -d postgres
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd uv run alembic upgrade head
CTXD_STORAGE_BACKEND=postgres CTXD_EMBEDDING_PROVIDER=model2vec \
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd \
  uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

Request `"retrieval_mode":"hybrid"` explicitly. Real embeddings require pinned model artifacts (first use may download them); configure `CTXD_EMBEDDING_CACHE_DIR` / `CTXD_EMBEDDING_OFFLINE` for deployment. Docker Compose's database startup is not authentication or deployment hardening.

### Validation

```bash
uv run ruff check .
uv run mypy
# Create a dedicated ctxd_test database first; tests TRUNCATE corpus tables.
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test uv run alembic upgrade head
CTXD_TEST_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test uv run pytest
```

Without the test database variable, 11 integration tests skip. Current consolidation: 154 passed, zero skipped. Configured mypy covers application code, not all historical scripts.

## Read the project in 30 minutes

1. [Current state](CURRENT_STATE.md): scope, defaults, blockers, validation.
2. [Architecture](ARCHITECTURE.md): implementation and trust boundaries.
3. [Experiments](EXPERIMENTS.md): keep/reject decisions and evidence.
4. [Roadmap](ROADMAP.md): engineering objectives, not another numbered phase.
5. [Benchmarks](BENCHMARKS.md) and [performance](PERFORMANCE.md): historical measurements and limitations.

[Evidence inventory](docs/evidence_inventory.json) indexes reports/artifacts by SHA-256. [Code audit](docs/ENGINEERING_AUDIT.md) classifies offline and stale code without deleting it.

**Phase 10/10B benchmark: PRE-REVIEW / NON-CANONICAL / BLOCKED.** 106 current candidates, zero independent human reviews; the full audit/review infrastructure is unfinished. No canonical result exists.

## API surface

- `GET /health`: liveness (not database readiness).
- `POST /v1/documents`: ingestion.
- `POST /v1/query`: retrieval and context assembly.
- `GET /v1/index/statistics`, `/v1/index/semantic-statistics`: tenant statistics.
- `GET /metrics`: Prometheus metrics.

No experimental reranker or packing policy is exposed by these endpoints.
