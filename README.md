<div align="center">

<img src="./docs/assets/ctxd-logo.svg" width="320" alt="ctxd — context runtime" />

### Production Context Runtime for AI Agents

**Deterministic ingestion · Ranked retrieval · Token-bounded context assembly**

Build reliable context pipelines for production agents without reducing context engineering to  
`query → embedding → top-k → LLM`.

[Architecture](#architecture) · [Quickstart](#quickstart) · [Evaluation](#evaluation--benchmarks) · [API](#api)

<br />

![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-runtime-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-supported-4169E1?logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/status-active%20development-64748B)

</div>

---

## What is ctxd?

**ctxd** is a production-oriented context engineering runtime for AI agents.

The current core loads text and Markdown documents, performs structure-aware chunking, incrementally indexes tenant-scoped terms, ranks chunks with BM25, and allocates candidates into a token-bounded context packet.

It treats context construction as a first-class systems problem: deterministic ingestion, explicit retrieval semantics, bounded context assembly, persistence, evaluation, and observability live in one runtime instead of being scattered across application code.

## Why ctxd exists

A production context pipeline needs more than:

```text
query -> embedding -> top-k chunks -> LLM
```

Real systems have to reason about:

- deterministic ingestion and re-ingestion
- document and chunk identity
- tenant isolation
- ranking and corpus statistics
- explicit context budgets
- persistence and restart behavior
- evaluation quality
- observability
- storage and timeout failure semantics

ctxd builds those concerns into the runtime rather than leaving them as ad-hoc glue.

## Architecture

```text
Document
   |
   v
Loader
   |
   v
Structure-aware Chunker
   |
   v
DocumentStore
   |
   v
Incremental BM25 Index
   |
   v
ContextAssembler
   |
   v
ContextPacket
```

The implemented path is deliberately narrow and deterministic:

```text
Document -> Loader -> Structure-aware Chunker -> DocumentStore
         -> Incremental BM25 Index -> ContextAssembler -> ContextPacket
```

## Production characteristics

### Ingestion

- `.txt` and `.md` ingestion
- normalized UTF-8 content
- SHA-256 document hashes
- deterministic document and chunk IDs
- idempotent re-ingestion
- structure-aware Markdown/text chunking
- isolated token-count approximation

### Retrieval

- incremental BM25 indexing
- tenant-isolated term statistics
- tenant-isolated corpus statistics
- SQL-backed search
- deterministic ranking

### Context assembly

- explicit token budgets
- bounded context packets
- no silent candidate truncation

### Storage

- interchangeable in-memory and PostgreSQL backends
- Alembic migrations
- atomic document, chunk, posting, and corpus-statistics replacement
- restart persistence
- cross-runtime shared state with PostgreSQL

### Reliability

- bounded psycopg connection pooling
- configurable connection timeouts
- configurable query timeouts
- startup failure when PostgreSQL is unavailable
- startup failure when required migrations are missing
- distinct failures for query timeout, unavailable storage, and successful empty retrieval

### Observability

- bounded Prometheus metrics
- OpenTelemetry spans

### Evaluation

- Recall@K
- MRR
- nDCG@K
- sequential PostgreSQL benchmarks
- concurrent PostgreSQL benchmarks

## Current scope

ctxd currently focuses on the context runtime itself.

**Implemented:** ingestion, chunking, storage, BM25 retrieval, context assembly, evaluation, persistence, and observability.

**Not implemented yet:** inference, model routing, vector retrieval, reranking, tools, or a frontend.

`/v1/query` returns real retrieved context and explicitly reports that inference is not implemented.

## Quickstart

### Local development

```bash
uv sync --python 3.13
uv run pytest
uv run ruff check .
uv run mypy
uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

The default backend is in-memory.

Both POST endpoints require `x-tenant-id`; it must match the request body's `tenant_id`.

### PostgreSQL

Start PostgreSQL and apply migrations before selecting the persistent backend:

```bash
docker compose up -d postgres

CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd \
  uv run alembic upgrade head

CTXD_STORAGE_BACKEND=postgres \
CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd \
  uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

Alternatively:

```bash
docker compose up --build
```

This runs a dedicated migration service before starting the application.

### PostgreSQL pool configuration

| Variable | Default |
|---|---:|
| `CTXD_DATABASE_POOL_MIN_SIZE` | `1` |
| `CTXD_DATABASE_POOL_MAX_SIZE` | `10` |
| `CTXD_DATABASE_CONNECTION_TIMEOUT_SECONDS` | `5` |
| `CTXD_DATABASE_QUERY_TIMEOUT_MS` | `5000` |

## Evaluation & benchmarks

### In-memory retrieval evaluation

```bash
uv run python -m ctxd.app.evals.retrieval evals/retrieval_corpus.json
```

### PostgreSQL retrieval evaluation

```bash
uv run python -m ctxd.app.evals.retrieval evals/retrieval_corpus.json \
  --database-url postgresql://ctxd:ctxd@localhost:5432/ctxd
```

### Expanded 100-case corpus

```bash
uv run python -m ctxd.app.evals.retrieval evals/retrieval_expanded.json \
  --database-url postgresql://ctxd:ctxd@localhost:5432/ctxd
```

### PostgreSQL benchmarks

> These benchmark commands destructively reset corpus tables. Use a dedicated database.

```bash
uv run python benchmarks/postgres_retrieval_baseline.py
uv run python benchmarks/postgres_concurrent_load.py
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Runtime health |
| `POST` | `/v1/documents` | Ingest documents |
| `POST` | `/v1/query` | Retrieve and assemble context |
| `GET` | `/v1/index/statistics` | Inspect index statistics |
| `GET` | `/metrics` | Prometheus metrics |

## Non-goals

ctxd is not intended to be:

- a generic RAG demo
- a chatbot wrapper
- a one-step `query -> embedding -> top-k chunks -> LLM` pipeline
- an arbitrary generated-code execution environment inside the API process

## Design principle

> Context construction should be deterministic, inspectable, budget-aware, and measurable.

The runtime should make it possible to answer not only **what context was selected**, but also **why it was selected, under which budget, from which tenant-scoped corpus, and with what retrieval quality**.

---

<div align="center">

<img src="./docs/assets/ctxd-mark.svg" width="72" alt="ctxd mark" />

**ctxd**

Context runtime for production AI agents.

</div>
