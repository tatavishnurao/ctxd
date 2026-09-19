from fastapi import APIRouter, Request, Response

from ctxd.app.models.domain import ContextPacket, ModelDecision, QueryRequest, QueryResponse
from ctxd.app.observability.metrics import QUERY_PLACEHOLDER_TOTAL, render_metrics

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)


@router.post("/v1/query")
async def query(request_body: QueryRequest, request: Request) -> QueryResponse:
    QUERY_PLACEHOLDER_TOTAL.inc()
    context = ContextPacket(
        candidates=[],
        token_budget=request_body.max_context_tokens,
        metadata={"phase": "foundation", "retrieval": "not_implemented"},
    )
    model_decision = ModelDecision(
        selected_model="not_routed",
        routing_score=0.0,
        reason="Phase 1 placeholder: model routing and inference are not implemented.",
    )
    return QueryResponse(
        answer=(
            "ctxd Phase 1 placeholder: retrieval, routing, inference, "
            "and tools are not implemented yet."
        ),
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        context=context,
        model_decision=model_decision,
        metadata={"tenant_id": request_body.tenant_id, "task_type": request_body.task_type},
    )
