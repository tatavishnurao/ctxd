from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST

REQUESTS_TOTAL = Counter(
    "ctxd_requests_total",
    "Total HTTP requests by path, method, and status.",
    ["method", "path", "status"],
)
REQUEST_LATENCY_SECONDS = Histogram(
    "ctxd_request_latency_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)
ACTIVE_REQUESTS = Gauge("ctxd_active_requests", "Number of active HTTP requests.")
INGESTED_DOCUMENTS_TOTAL = Counter(
    "ctxd_ingested_documents_total",
    "Documents successfully ingested.",
    ["source_type"],
)
INGESTED_CHUNKS_TOTAL = Counter(
    "ctxd_ingested_chunks_total",
    "Chunks produced by successful ingestion.",
    ["source_type"],
)
RETRIEVAL_MODE_REQUESTS_TOTAL = Counter(
    "ctxd_retrieval_mode_requests_total",
    "Retrieval requests by mode and outcome.",
    ["mode", "status"],
)
RETRIEVAL_REQUESTS_TOTAL = Counter(
    "ctxd_retrieval_requests_total",
    "Lexical retrieval requests by outcome.",
    ["status"],
)
RETRIEVAL_LATENCY_SECONDS = Histogram(
    "ctxd_retrieval_latency_seconds",
    "Lexical retrieval latency in seconds.",
)
RETRIEVAL_CANDIDATES_RETURNED = Histogram(
    "ctxd_retrieval_candidates_returned",
    "Number of candidates returned by lexical retrieval.",
    buckets=(0, 1, 2, 5, 10, 20, 50, 100),
)
CONTEXT_TOKENS_SELECTED = Histogram(
    "ctxd_context_tokens_selected",
    "Tokens selected into context packets.",
    buckets=(0, 50, 100, 250, 500, 1_000, 2_000, 4_000, 8_000, 16_000),
)
CONTEXT_CANDIDATES_DROPPED_TOTAL = Counter(
    "ctxd_context_candidates_dropped_total",
    "Candidates dropped because they exceed the remaining token budget.",
)
DATABASE_OPERATION_LATENCY_SECONDS = Histogram(
    "ctxd_database_operation_latency_seconds",
    "Database operation latency by bounded operation and status.",
    ["operation", "status"],
)
LEXICAL_INDEX_UPDATE_LATENCY_SECONDS = Histogram(
    "ctxd_lexical_index_update_latency_seconds",
    "Atomic lexical index update latency in seconds.",
)
LEXICAL_SEARCH_LATENCY_SECONDS = Histogram(
    "ctxd_lexical_search_latency_seconds",
    "Lexical index search latency in seconds.",
)
EMBEDDING_REFRESHES_TOTAL = Counter(
    "ctxd_embedding_refreshes_total",
    "Unchanged documents re-embedded because stored embeddings had another version.",
)
EMBEDDING_VERSION_MISMATCH_TOTAL = Counter(
    "ctxd_embedding_version_mismatch_total",
    "Semantic queries whose tenant had chunks embedded under a non-configured version.",
)
RERANKER_REQUESTS_TOTAL = Counter(
    "ctxd_reranker_requests_total",
    "Reranker requests by bounded model identifier and outcome.",
    ["model", "status"],
)
RERANKER_CANDIDATES = Histogram(
    "ctxd_reranker_candidates",
    "Candidates presented to the reranker.",
    buckets=(0, 1, 5, 10, 20, 50, 100),
)
RERANKER_PREPARATION_LATENCY_SECONDS = Histogram(
    "ctxd_reranker_preparation_latency_seconds",
    "Reranker candidate preparation latency in seconds.",
)
RERANKER_INFERENCE_LATENCY_SECONDS = Histogram(
    "ctxd_reranker_inference_latency_seconds",
    "Reranker model inference latency in seconds.",
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
