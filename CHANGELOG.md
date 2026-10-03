# Changelog

## 0.1.0

First versioned release. It contains breaking API changes relative to the pre-release `main`.

### Breaking

- **Packet fields removed.** `ContextCandidate.rerank_score`, `dependency_score`, `redundancy_score` and `recency`, and `ContextPacket.compression_ratio`, are gone. They were never computed and were always reported as `0.0`. A packet now carries only signals it computed.
- **`retrieval_type` now means "what ran".** `metadata.retrieval_type` names the branches that actually returned candidates (`hybrid`, `lexical`, `semantic` or `none`). It used to echo the requested mode. The requested mode is now in `metadata.requested_mode`, and per-branch counts are in `metadata.branch_candidate_counts`.
- **`retrieval_mode` is optional, with a server default.** A `QueryRequest` without `retrieval_mode` uses the server's default (`CTXD_DEFAULT_RETRIEVAL_MODE`), which is **lexical**. Previously the field defaulted to lexical in the request model. Callers that need hybrid or semantic must ask for it.
- **Tenant comes from credentials outside development.** With `CTXD_ENVIRONMENT` other than `development`, the server refuses to start without `CTXD_AUTH_MODE=api_key` or `jwt`, and the tenant is derived from the verified credential. An `x-tenant-id` header that disagrees with it is rejected with 403. The unauthenticated header mode is development-only.
- **`/metrics` is an operator endpoint.** With authentication enabled it requires `CTXD_AUTH_OPERATOR_TOKEN`, and is disabled (403) when no operator token is set.
- **Fail-loud configuration.** PostgreSQL with fake embeddings is refused unless `CTXD_ALLOW_FAKE_EMBEDDINGS=true`.

### Added

- `/ready` probe for storage and the embedding model (503 when not ready).
- Request deadline, ingest size limit (413), and explicit 503 responses for storage and embedding failures.
- Re-embedding on embedding-version change. Packets carry `warnings: ["embedding_version_mismatch"]` and stale-chunk counts when the semantic branch is short because chunks were embedded under another version. `SemanticIndexStatistics.stale_chunks` exposes the same count.
- Metrics are labeled by route template, never the raw path.
- BEIR evaluation harness (`benchmarks/beir_eval.py`) run through the production retrievers. See `docs/BEIR_EVAL.md`.

### Decision

- The server default retrieval mode is lexical (BM25), whatever embedding provider is configured. On BEIR, hybrid RRF gained Recall@100 but lost nDCG@10 on SciFact (−0.059, 95% CI [−0.094, −0.026]) and tied on NFCorpus. That finding is for Model2Vec (static embedding) on two BM25-friendly corpora; it is provisional, not a claim that dense retrieval is useless. Hybrid stays a supported mode.
