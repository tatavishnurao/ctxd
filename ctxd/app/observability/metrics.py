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
QUERY_PLACEHOLDER_TOTAL = Counter(
    "ctxd_query_placeholder_total",
    "Number of placeholder query requests served before retrieval/model integration.",
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
