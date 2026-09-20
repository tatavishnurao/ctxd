from fastapi import APIRouter, HTTPException, Request, Response, status

from ctxd.app.ingestion.loaders import DocumentLoadError
from ctxd.app.models.domain import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    LexicalIndexStatistics,
    QueryRequest,
    QueryResponse,
    SemanticIndexStatistics,
)
from ctxd.app.observability.metrics import render_metrics
from ctxd.app.runtime import RuntimeServices
from ctxd.app.storage.errors import RetrievalTimeoutError, StorageError

router = APIRouter()


def _services(request: Request) -> RuntimeServices:
    services: RuntimeServices = request.app.state.services
    return services


def _require_tenant(request: Request, claimed_tenant: str) -> str:
    authenticated_tenant = str(request.state.tenant_id)
    if authenticated_tenant == "unknown":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-tenant-id header is required",
        )
    if authenticated_tenant != claimed_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id does not match the authenticated tenant",
        )
    return authenticated_tenant


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)


@router.post("/v1/documents", status_code=status.HTTP_201_CREATED)
def ingest_document(
    request_body: DocumentIngestRequest,
    request: Request,
    response: Response,
) -> DocumentIngestResponse:
    tenant_id = _require_tenant(request, request_body.tenant_id)
    try:
        document, chunks, created = _services(request).ingestion.ingest_content(
            content=request_body.content,
            source_path=request_body.source_path,
            source_type=request_body.source_type,
            tenant_id=tenant_id,
            metadata=request_body.metadata,
        )
    except DocumentLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="document storage is unavailable",
        ) from exc
    if not created:
        response.status_code = status.HTTP_200_OK
    return DocumentIngestResponse(document=document, chunks=chunks, created=created)


@router.post("/v1/query")
def query(request_body: QueryRequest, request: Request) -> QueryResponse:
    tenant_id = _require_tenant(request, request_body.tenant_id)
    try:
        context = _services(request).assembler.assemble(
            query=request_body.query,
            tenant_id=tenant_id,
            top_k=request_body.top_k,
            max_context_tokens=request_body.max_context_tokens,
            retrieval_mode=request_body.retrieval_mode,
        )
    except RetrievalTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="retrieval timed out",
        ) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="retrieval subsystem is unavailable",
        ) from exc
    return QueryResponse(
        answer="Inference is not implemented yet.",
        request_id=request.state.request_id,
        trace_id=request.state.trace_id,
        context=context,
        model_decision=None,
        metadata={"tenant_id": tenant_id, "task_type": request_body.task_type},
    )


@router.get("/v1/index/semantic-statistics")
def semantic_index_statistics(request: Request) -> SemanticIndexStatistics:
    tenant_id = str(request.state.tenant_id)
    if tenant_id == "unknown":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="x-tenant-id header is required"
        )
    try:
        return _services(request).semantic_retriever.statistics(tenant_id)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="semantic index statistics are unavailable",
        ) from exc


@router.get("/v1/index/statistics")
def index_statistics(request: Request) -> LexicalIndexStatistics:
    tenant_id = str(request.state.tenant_id)
    if tenant_id == "unknown":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-tenant-id header is required",
        )
    try:
        return _services(request).retriever.statistics(tenant_id)
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="index statistics are unavailable",
        ) from exc
