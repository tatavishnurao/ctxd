<p align="center">
  <img src="docs/assets/ctxd-logo.svg" alt="ctxd — Context Runtime" width="620" />
</p>

<div align="center">

# ctxd

### Context Runtime

**Turns a large, messy information space into the smallest _trustworthy_ context packet an AI task actually needs.**

Retrieval, evidence selection, provenance, and token-budgeted assembly — before inference, behind one API.

![status](https://img.shields.io/badge/status-v0.1-blue.svg)
![python](https://img.shields.io/badge/python-3.13%2B-3776AB.svg?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791.svg?logo=postgresql&logoColor=white)

</div>

---

## What is ctxd?

An agent can reach millions of pieces of information; the model it calls can only receive a small slice. **ctxd decides the slice** — what to retrieve, what to keep, what to drop, how to spend a token budget — and returns a single, auditable `ContextPacket`.

It is deliberately **not** a model runtime. ctxd answers _"give me the best context for this request"_ and stops at the packet boundary. The difference from ordinary RAG isn't better recall — it's a packet you can trust: it never reports a signal it didn't compute, and it degrades loudly rather than silently.

```text
query · tenant · budget  ──►  ctxd  ──►  ContextPacket  ──►  your agent / model
```

## Status

ctxd is **v0.1** — a tested, authenticated baseline, not a finished product.

- Tenant-scoped retrieval over text / Markdown, on PostgreSQL + pgvector.
- Lexical (BM25), semantic (Model2Vec), and hybrid (RRF) modes through one API.
- Token-budgeted, no-truncation context assembly into an observable `ContextPacket`.
- API-key / JWT auth, deny-by-default outside development.

The default mode is **lexical**: on the one real-text evaluation ctxd has, hybrid didn't improve top-of-ranking quality (see [Evaluation](#evaluation)). Out of scope for v0.1: reranking, approximate search, and anything past the packet — inference, routing, tools.

## Architecture

```text
   documents ──►  PostgreSQL + pgvector   (BM25 stats · vectors · provenance)
                        ▲
   Request  (query · tenant · budget · mode)
       │
   ┌───┴──────────── ctxd runtime ───────────────┐
   │  Retrieve   BM25  +  dense semantic           │
   │  Fuse       deterministic RRF                 │
   │  Select     whole chunks · provenance         │
   │  Budget     token-bounded assembly            │
   └──────────────────┬─────────────────────────────┘
                      ▼
                ContextPacket   ┄┄►  agent / model  (out of scope)
```

Invariants held everywhere: determinism, provenance integrity, truth-in-labeling, schema-enforced tenant isolation, bounded failure.

## Quick start

Docker Compose brings up the real stack — PostgreSQL + pgvector, the pinned Model2Vec model, migrations applied, API on `localhost:8000`:

```bash
git clone https://github.com/tatavishnurao/ctxd.git
cd ctxd
docker compose up --build
```

```bash
# ingest
curl -s localhost:8000/v1/documents -H 'content-type: application/json' -H 'x-tenant-id: acme' \
  -d '{"tenant_id":"acme","source_path":"cache.md","source_type":"markdown",
       "content":"# Cache\n\nThe cache evicts entries under memory pressure."}'

# query → ContextPacket
curl -s localhost:8000/v1/query -H 'content-type: application/json' -H 'x-tenant-id: acme' \
  -d '{"tenant_id":"acme","query":"how does the cache free memory?","max_context_tokens":2000}'
```

The response is a `ContextPacket`: the selected candidates with provenance, the tokens used against the budget, and a `retrieval_type` naming what actually ran.

> In development the tenant is trusted from `x-tenant-id`. Outside development, real authentication is required.

To watch a query move through retrieval and the budget cut in a browser, see the [context packet inspector](tools/dashboard/README.md).

## Configuration

Environment variables, `CTXD_` prefix (or a `.env` file), validated at startup.

| Variable | Default | Notes |
|---|---|---|
| `CTXD_ENVIRONMENT` | `development` | Any other value enforces authentication. |
| `CTXD_STORAGE_BACKEND` | `memory` | `memory` or `postgres`. |
| `CTXD_DATABASE_URL` | local dev DSN | Set it for any real `postgres` deployment. |
| `CTXD_EMBEDDING_PROVIDER` | `fake` | `fake` (dev only) or `model2vec`. |
| `CTXD_DEFAULT_RETRIEVAL_MODE` | `lexical` | `lexical` · `semantic` · `hybrid`. |
| `CTXD_AUTH_MODE` | `none` | `none` (dev only) · `api_key` · `jwt`. |

Auth adds `CTXD_AUTH_API_KEYS` / `CTXD_AUTH_JWT_SECRET` and an operator token for `/metrics`. Without Docker: `uv sync`, point `CTXD_DATABASE_URL` at a pgvector Postgres, `uv run alembic upgrade head`, then `uv run uvicorn ctxd.app.main:app`.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/documents` | Ingest / replace a document. |
| `POST` | `/v1/query` | Retrieve, select, assemble a `ContextPacket`. |
| `GET` | `/v1/index/statistics`, `/v1/index/semantic-statistics` | Per-tenant corpus stats. |
| `GET` | `/health`, `/ready` | Liveness / readiness. |
| `GET` | `/metrics` | Prometheus (operator-token gated when auth is on). |

## Evaluation

Run through the shipped code on public BEIR datasets, nothing tuned. BM25 reproduces the published baseline, so the harness is sound. Full protocol and intervals: [docs/BEIR_EVAL.md](docs/BEIR_EVAL.md).

| Dataset | nDCG@10 (lexical) | nDCG@10 (hybrid) | Δ recall@100 (hybrid − lexical) |
|---|---|---|---|
| SciFact | **0.662** _(published 0.665)_ | 0.603 | +0.069 |
| NFCorpus | 0.309 | 0.308 | +0.033 |

A `ContextPacket` is the top of the ranking cut to a budget, so nDCG@10 is what matters — and hybrid didn't help there, so lexical is the default. Caveat: one static embedding model on two BM25-friendly corpora; provisional, not a claim that dense retrieval is weak.

## Development

```bash
uv sync --all-groups
uv run ruff check . && uv run mypy

# Full suite: needs a migrated pgvector test database (tests TRUNCATE it) and the real model.
export CTXD_DATABASE_URL=postgresql://ctxd:ctxd@localhost:5432/ctxd_test
export CTXD_TEST_DATABASE_URL=$CTXD_DATABASE_URL CTXD_RUN_MODEL2VEC=1
uv run alembic upgrade head
uv run pytest

uv run pytest -m "not postgres"   # fast subset, no database
```

Without those variables the Postgres and Model2Vec tests skip. CI runs the full suite against `pgvector/pgvector:pg17` with the real model, migrates down and back up, and gates on ruff and mypy.

## Roadmap

- The request deadline bounds the response, not hybrid's background threads ([#9](https://github.com/tatavishnurao/ctxd/issues/9)).
- The container image isn't yet built from `uv.lock` ([#10](https://github.com/tatavishnurao/ctxd/issues/10)).
- **Evidence-aware selection is unmeasured** — BEIR judges documents, not spans. A span-annotated evaluation (HotpotQA / MuSiQue) is the next real step ([#11](https://github.com/tatavishnurao/ctxd/issues/11)).

## License

MIT — see [LICENSE](LICENSE).
