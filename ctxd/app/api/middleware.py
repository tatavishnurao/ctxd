import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware

from ctxd.app.observability.logging import request_id_var, tenant_id_var, trace_id_var
from ctxd.app.observability.metrics import ACTIVE_REQUESTS, REQUEST_LATENCY_SECONDS, REQUESTS_TOTAL

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        tenant_id = request.headers.get("x-tenant-id", "unknown")
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()
        trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else str(uuid4())

        request_id_token = request_id_var.set(request_id)
        tenant_id_token = tenant_id_var.set(tenant_id)
        trace_id_token = trace_id_var.set(trace_id)

        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request.state.tenant_id = tenant_id

        start = time.perf_counter()
        ACTIVE_REQUESTS.inc()
        status_code = 500
        try:
            logger.info("request_started")
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            response.headers["x-trace-id"] = trace_id
            return response
        finally:
            duration = time.perf_counter() - start
            path = request.url.path
            REQUEST_LATENCY_SECONDS.labels(request.method, path).observe(duration)
            REQUESTS_TOTAL.labels(request.method, path, str(status_code)).inc()
            ACTIVE_REQUESTS.dec()
            logger.info("request_finished")
            request_id_var.reset(request_id_token)
            tenant_id_var.reset(tenant_id_token)
            trace_id_var.reset(trace_id_token)
