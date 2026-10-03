# ctxd — context retrieval and assembly

A retrieval-engineering prototype that turns documents into token-bounded ContextPackets for AI-agent workloads. **Maturity: pre-alpha research checkpoint.** Read these two limits before anything else:

- **Tests prove behavior, not quality.** Every retrieval mode (lexical, semantic, hybrid) is exercised through the API on memory and PostgreSQL + pgvector, RRF math/ties/depth have unit tests, and CI runs a pinned Model2Vec smoke test. None of this measures retrieval quality on real text.
- **Quality numbers are not evidence about real text.** 100 of the 150 cases behind the historical hybrid/reranker metrics (`evals/retrieval_semantic.json`) are synthetic marker queries such as `codename_0` against filler-padded documents; only 50 are natural-language paraphrases. The realistic Phase 10/10B benchmark has agent-authored labels and zero independent reviews. No retrieval-quality claim on realistic, independently judged data exists yet.

Implemented: deterministic ingestion, tenant-scoped storage, BM25, semantic retrieval, parallel deterministic RRF and token-bounded whole-chunk ContextPackets.

**Not implemented:** LLM inference, model routing, production/public reranking, tools/sandbox, agent loop, SSE or frontend. `/v1/query` returns retrieved context and an explicit inference-not-implemented placeholder.

```text
Documents -> structure-aware chunks -> documents/postings/embeddings
                                          |
Query -> BM25 + exact semantic search -> parallel deterministic RRF
                                          |
                              greedy ContextAssembler -> ContextPacket
```

Out-of-box defaults are **memory + fake fixture embeddings + lexical queries**, for tests and local hacking only. `docker compose up` runs the evaluated path instead: **PostgreSQL + pinned Model2Vec + exact pgvector, with hybrid as the server default mode**. The server refuses to start with PostgreSQL + fake embeddings unless `CTXD_ALLOW_FAKE_EMBEDDINGS=true`, and logs an `effective_configuration` line at startup. Candidate depth depends on request/configuration, not a universal 20. Outside `CTXD_ENVIRONMENT=development` the server refuses to start without authentication (see below).

## Quickstart

```bash
uv sync --python 3.13
uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

In development (`auth_mode=none`, the default), the tenant comes from the unauthenticated `x-tenant-id` header, which must match the body's `tenant_id`. Example:

```bash
curl localhost:8000/v1/documents -H 'content-type: application/json' \
  -H 'x-tenant-id: demo' -d '{"tenant_id":"demo","source_path":"hello.txt","source_type":"text","content":"ctxd assembles whole chunks within a token budget."}'
curl localhost:8000/v1/query -H 'content-type: application/json' \
  -H 'x-tenant-id: demo' -d '{"tenant_id":"demo","query":"token budget","retrieval_mode":"lexical"}'
```

### Persistent, real-embedding path

```bash
docker compose up -d --wait        # postgres, migrations, app on 127.0.0.1:8000
curl localhost:8000/ready          # storage + embedding model probe
```

Or run the app outside Docker:

```bash
docker compose up -d postgres
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd uv run alembic upgrade head
CTXD_STORAGE_BACKEND=postgres CTXD_EMBEDDING_PROVIDER=model2vec \
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd \
  uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

With Model2Vec configured, queries without `retrieval_mode` run hybrid (`CTXD_DEFAULT_RETRIEVAL_MODE` overrides). Real embeddings require pinned model artifacts (first use may download them); configure `CTXD_EMBEDDING_CACHE_DIR` / `CTXD_EMBEDDING_OFFLINE` for deployment. Docker Compose's database startup is not authentication or deployment hardening.

### Validation

```bash
uv run ruff check .
uv run mypy
# Create a dedicated ctxd_test database first; tests TRUNCATE corpus tables.
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test uv run alembic upgrade head
CTXD_TEST_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test uv run pytest
```

Without the test database variable, the PostgreSQL integration tests skip; without `CTXD_RUN_MODEL2VEC=1`, the real-model smoke test skips. Current consolidation: 154 passed, zero skipped. Configured mypy covers application code, not all historical scripts.

## Read the project in 30 minutes

1. [Current state](CURRENT_STATE.md): scope, defaults, blockers, validation.
2. [Architecture](ARCHITECTURE.md): implementation and trust boundaries.
3. [Experiments](EXPERIMENTS.md): keep/reject decisions and evidence.
4. [Roadmap](ROADMAP.md): engineering objectives, not another numbered phase.
5. [Benchmarks](BENCHMARKS.md) and [performance](PERFORMANCE.md): historical measurements and limitations.

[Evidence inventory](docs/evidence_inventory.json) indexes reports/artifacts by SHA-256. [Code audit](docs/ENGINEERING_AUDIT.md) classifies offline and stale code without deleting it.

**Phase 10/10B benchmark: PRE-REVIEW / NON-CANONICAL / BLOCKED.** 106 current candidates, zero independent human reviews; the full audit/review infrastructure is unfinished. No canonical result exists.

### Authentication

Any environment other than `development` requires `CTXD_AUTH_MODE=api_key` or `jwt`, and the tenant is then derived from the credential, never from a header:

- `api_key`: `CTXD_AUTH_API_KEYS='{"<key of 32+ chars>": "tenant-a"}'`; clients send `Authorization: Bearer <key>`.
- `jwt`: HS256 with `CTXD_AUTH_JWT_SECRET` (32+ chars); the token must carry `exp` and the tenant claim (`CTXD_AUTH_JWT_TENANT_CLAIM`, default `tenant_id`); optional `CTXD_AUTH_JWT_AUDIENCE` / `CTXD_AUTH_JWT_ISSUER`.
- `/metrics` requires `Authorization: Bearer $CTXD_AUTH_OPERATOR_TOKEN` and returns 403 if no operator token is configured. `/health` and `/ready` stay open for orchestrators.

A body `tenant_id` or `x-tenant-id` header naming a different tenant than the credential gets 403. This is a floor, not a complete identity system: there is no key rotation API, no per-tenant roles, and no TLS termination.

## API surface

- `GET /health`: static liveness.
- `GET /ready`: readiness; probes storage and the embedding model, 503 if either fails.
- `POST /v1/documents`: ingestion.
- `POST /v1/query`: retrieval and context assembly.
- `GET /v1/index/statistics`, `/v1/index/semantic-statistics`: tenant statistics.
- `GET /metrics`: Prometheus metrics.

No experimental reranker or packing policy is exposed by these endpoints.
