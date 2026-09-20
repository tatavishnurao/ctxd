# ctxd

Context runtime for production AI agents with deterministic ingestion, retrieval, token budgeting, evaluation, and observability.

## Goal

Build a production-oriented context engineering runtime. The current core loads text and Markdown documents, performs structure-aware chunking, incrementally indexes tenant-scoped terms, ranks chunks with BM25, and allocates candidates into a token-bounded context packet.

## Non-goals

- Generic RAG demo
- Chatbot wrapper
- One-step `query -> embedding -> top-k chunks -> LLM` pipeline
- Arbitrary generated code execution inside the API process

## Implemented path

```text
Document -> Loader -> Structure-aware Chunker -> DocumentStore
         -> Incremental BM25 Index -> ContextAssembler -> ContextPacket
```

Phase 3 provides:

- `.txt` and `.md` ingestion with normalized UTF-8 content and SHA-256 hashes
- deterministic document/chunk IDs and idempotent re-ingestion
- Markdown/text structure-aware chunking with an isolated token-count approximation
- interchangeable in-memory and PostgreSQL document/index backends
- Alembic database migrations
- atomic document, chunk, posting, and corpus-statistics replacement
- tenant-isolated incremental BM25 statistics and SQL search
- bounded psycopg connection pooling and query timeout configuration
- restart persistence and cross-runtime shared state with PostgreSQL
- token-budget context assembly without silent candidate truncation
- bounded Prometheus metrics and OpenTelemetry spans
- deterministic Recall@K, MRR, and nDCG@K evaluation
- sequential and concurrent PostgreSQL benchmarks

Inference, model routing, vector retrieval, reranking, tools, and a frontend are not implemented. `/v1/query` returns real retrieved context and explicitly reports that inference is not implemented.

## Local development

```bash
uv sync --python 3.13
uv run pytest
uv run ruff check .
uv run mypy
uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

The default backend is in-memory. Both POST endpoints require `x-tenant-id`; it must match the request body's `tenant_id`.

## PostgreSQL

Start PostgreSQL and run the migration before selecting the persistent backend:

```bash
docker compose up -d postgres
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd \
  uv run alembic upgrade head

CTXD_STORAGE_BACKEND=postgres \
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd \
  uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

Alternatively, `docker compose up --build` runs a dedicated migration service before starting the application.

Pool configuration:

- `CTXD_DATABASE_POOL_MIN_SIZE` (default `1`)
- `CTXD_DATABASE_POOL_MAX_SIZE` (default `10`)
- `CTXD_DATABASE_CONNECTION_TIMEOUT_SECONDS` (default `5`)
- `CTXD_DATABASE_QUERY_TIMEOUT_MS` (default `5000`)

Startup fails explicitly when PostgreSQL is unavailable or the required migration is missing. Query timeouts and unavailable storage return different HTTP failures from a successful empty retrieval.

## Evaluation and benchmarks

```bash
# Original Phase 2 corpus, in memory
uv run python -m ctxd.app.evals.retrieval evals/retrieval_corpus.json

# Original corpus through PostgreSQL
uv run python -m ctxd.app.evals.retrieval evals/retrieval_corpus.json \
  --database-url postgresql://ctxd:ctxd@localhost:5432/ctxd

# Expanded 100-case corpus
uv run python -m ctxd.app.evals.retrieval evals/retrieval_expanded.json \
  --database-url postgresql://ctxd:ctxd@localhost:5432/ctxd

# These benchmark commands destructively reset corpus tables; use a dedicated DB.
uv run python benchmarks/postgres_retrieval_baseline.py
uv run python benchmarks/postgres_concurrent_load.py
```

## Endpoints

- `GET /health`
- `POST /v1/documents`
- `POST /v1/query`
- `GET /v1/index/statistics`
- `GET /metrics`
