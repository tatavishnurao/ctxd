from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, NonNegativeInt


class SynapseFailureCategory(StrEnum):
    WRONG_TOOL = "wrong_tool"
    MALFORMED_ARGUMENTS = "malformed_arguments"
    SCHEMA_VIOLATION = "schema_violation"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    MISSING_TOOL = "missing_tool"
    AMBIGUOUS_TOOL = "ambiguous_tool"
    INCORRECT_OUTPUT = "incorrect_output"
    UNEXPECTED_RETRY = "unexpected_retry"


class McpToolSchema(BaseModel):
    name: str = Field(min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SynapseEvalCase(BaseModel):
    id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    expected_tool: str | None = None
    expected_arguments: dict[str, Any] = Field(default_factory=dict)
    acceptable_tools: list[str] = Field(default_factory=list)
    expected_outcome: Any = None
    expected_sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class McpInvocationResult(BaseModel):
    selected_tool: str | None = None
    arguments: dict[str, Any] | None = None
    output: Any = None
    execution_success: bool = False
    retry_count: NonNegativeInt = 0
    latency_ms: float = Field(ge=0.0)
    error_category: SynapseFailureCategory | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SynapseEvalResult(BaseModel):
    case_id: str
    selected_tool: str | None
    tool_selection_correct: bool
    argument_validity: bool
    schema_validity: bool
    execution_success: bool
    task_success: bool
    retry_count: int
    latency_ms: float
    error_category: SynapseFailureCategory | None = None
    output_match_status: Literal["match", "mismatch", "not_checked"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class SynapseEvalReport(BaseModel):
    synthetic: bool = True
    case_count: int
    tool_selection_accuracy: float
    schema_validity_rate: float
    argument_validity_rate: float
    task_success_rate: float
    execution_success_rate: float
    retry_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    failure_counts: dict[str, int]
    results: list[SynapseEvalResult]
