# ctxd

Context runtime for production AI agents with retrieval, token budgeting, model routing, tool execution, evaluation, and observability.

## Goal

Build a production-oriented context engineering runtime. The core of ctxd is the Context Assembly Service: query analysis, parallel lexical/vector/symbol retrieval, reranking, deduplication, dependency expansion, and token-budget allocation into a context packet.

## Non-goals

- Generic RAG demo
- Chatbot wrapper
- One-step `query -> embedding -> top-k chunks -> LLM` pipeline
- Arbitrary generated code execution inside the API process

## Architecture

Client -> API Gateway -> Context Assembly Service -> Model Router -> LLM -> Structured Output Validator -> Tool Runtime -> SSE Streaming -> Observability + Evaluation.

Phase 1 contains the API foundation only: config, request/trace IDs, structured logs, health/query placeholders, OpenTelemetry hooks, Prometheus metrics, domain models, eval schema, tests, CI, and Docker Compose.

## Planned metrics

Request success, goodput RPS, p50/p95/p99 latency, TTFT, TPOT, token counts, queue depth, Recall@K, MRR, nDCG, context tokens, citation accuracy, selected model, fallback rate, cost per request, structured-output validity, tool success, cache hit rate, tokens avoided, and cost saved.

Primary derived metric: Agent Goodput = successful requests satisfying quality + latency + cost SLOs divided by time.

## Local development

```bash
uv sync --python 3.13
uv run pytest
uv run ruff check .
uv run mypy
uv run uvicorn ctxd.app.main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `GET /health`
- `POST /v1/query`
- `GET /metrics`
