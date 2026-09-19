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


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    tenant_id: str = Field(default="default", min_length=1, max_length=200)
    task_type: str | None = None
    max_context_tokens: PositiveInt = 8_000
    require_tools: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


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
