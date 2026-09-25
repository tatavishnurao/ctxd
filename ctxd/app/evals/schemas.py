from typing import Any

from pydantic import BaseModel, Field, PositiveInt

from ctxd.app.models.domain import DocumentSourceType


class GoldenEvalCase(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    task_type: str
    tenant_id: str = "eval"
    top_k: PositiveInt = 5
    expected_sources: list[str] = Field(default_factory=list)
    expected_facts: list[str] = Field(default_factory=list)
    expected_tool: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalDocument(BaseModel):
    source_path: str
    tenant_id: str = "eval"
    source_type: DocumentSourceType
    content: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class RetrievalEvalCorpus(BaseModel):
    documents: list[EvalDocument]
    cases: list[GoldenEvalCase]


class RetrievalEvalResult(BaseModel):
    case_count: int
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    per_case: dict[str, dict[str, float]]


class RetrievalMetrics(BaseModel):
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_5: float
    ndcg_at_10: float


class RetrievalModeEvalResult(BaseModel):
    case_count: int
    model_version: str
    modes: dict[str, RetrievalMetrics]
    categories: dict[str, dict[str, RetrievalMetrics]]
    failures: list[dict[str, Any]]
