from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PositiveInt


class SourceType(StrEnum):
    DOCUMENT = "document"
    CODE = "code"
    MEMORY = "memory"
    TOOL = "tool"


class DocumentSourceType(StrEnum):
    TEXT = "text"
    MARKDOWN = "markdown"


class RetrievalMode(StrEnum):
    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    tenant_id: str = Field(default="default", min_length=1, max_length=200)
    retrieval_mode: RetrievalMode = RetrievalMode.LEXICAL
    task_type: str | None = None
    max_context_tokens: PositiveInt = 8_000
    top_k: PositiveInt = Field(default=10, le=100)
    require_tools: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentIngestRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=200)
    source_path: str = Field(min_length=1, max_length=4_000)
    source_type: DocumentSourceType
    content: str = Field(min_length=1)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class Document(BaseModel):
    document_id: str
    tenant_id: str
    source_path: str
    source_type: DocumentSourceType
    content: str
    content_hash: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    tenant_id: str
    content: str = Field(min_length=1)
    content_hash: str
    start_line: PositiveInt
    end_line: PositiveInt
    token_count: PositiveInt
    ordinal: NonNegativeInt
    metadata: dict[str, str | int | float | bool | None | list[str]] = Field(default_factory=dict)


class SemanticIndexStatistics(BaseModel):
    indexed_chunks: NonNegativeInt
    embedding_version: str
    embedding_dimension: PositiveInt


class LexicalIndexStatistics(BaseModel):
    indexed_documents: NonNegativeInt
    indexed_chunks: NonNegativeInt
    vocabulary_size: NonNegativeInt
    average_chunk_length: NonNegativeFloat


class DocumentIngestResponse(BaseModel):
    document: Document
    chunks: list[Chunk]
    created: bool


class TraceMetadata(BaseModel):
    request_id: str
    trace_id: str
    tenant_id: str
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextCandidate(BaseModel):
    source_id: str
    source_type: SourceType
    content: str
    token_cost: NonNegativeInt
    relevance_score: NonNegativeFloat = 0.0
    rerank_score: NonNegativeFloat = 0.0
    dependency_score: NonNegativeFloat = 0.0
    redundancy_score: NonNegativeFloat = 0.0
    recency: NonNegativeFloat = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextPacket(BaseModel):
    packet_id: UUID = Field(default_factory=uuid4)
    candidates: list[ContextCandidate] = Field(default_factory=list)
    token_budget: PositiveInt
    context_tokens: NonNegativeInt = 0
    compression_ratio: NonNegativeFloat = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelDecision(BaseModel):
    selected_model: str
    routing_score: NonNegativeFloat
    reason: str
    fallback_models: list[str] = Field(default_factory=list)
    estimated_cost_usd: NonNegativeFloat = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    tool_name: str = Field(min_length=1, max_length=200)
    arguments: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: PositiveInt = 30_000
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    latency_ms: NonNegativeFloat = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    answer: str
    request_id: str
    trace_id: str
    context: ContextPacket | None = None
    model_decision: ModelDecision | None = None
    tool_results: list[ToolResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
