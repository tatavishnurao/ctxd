# ctxd Architecture

## System shape

```text
Client
  -> API Gateway: auth, tenant, quotas, request IDs
  -> Context Assembly Service: retrieval, reranking, dedupe, dependency expansion, allocation
  -> Model Router: deterministic cheap/medium/strong/fallback selection
  -> LLM
  -> Structured Output Validator: JSON parse, Pydantic validation, repair, retry, fallback
  -> Tool Runtime: typed calls, policy, sandbox, timeout, stdout/stderr capture
  -> SSE Streaming
  -> Observability + Evaluation
```

## Phase 1 implemented foundation

- FastAPI application factory in `ctxd/app/main.py`
- Request context middleware that attaches `request_id`, `trace_id`, and `tenant_id`
- Structured JSON logs with context variables
- OpenTelemetry FastAPI instrumentation hook
- Prometheus metrics registry and `/metrics`
- `/health` and placeholder `/v1/query`
- Pydantic v2 domain models and golden-eval schema

## Core future design: context assembly

The retrieval path will be:

```text
request -> query analysis -> parallel retrieval
  -> BM25 / lexical
  -> semantic vector search
  -> code/symbol retrieval
-> candidate pool -> reranking -> deduplication -> dependency expansion
-> token-budget allocator -> context packet
```

The allocator will maximize useful context subject to token budget, source diversity, redundancy limits, and dependency constraints.

## Ingestion classes

- Documents: parsing, structure-aware chunking, metadata extraction, lexical and embedding indexes.
- Repositories: language detection, tree-sitter parsing, symbols, imports, definitions, modules, source ranges, signatures, docs/comments for Python, TypeScript, and Rust.

## Evaluation from day one

Golden cases are JSONL records validated by `ctxd.app.evals.schemas.GoldenEvalCase`. Metrics will be separated into retrieval quality, context assembly quality, generation quality, citation correctness, tool success, latency, and cost.
