from typing import Any

from pydantic import BaseModel, Field


class GoldenEvalCase(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    task_type: str
    expected_sources: list[str] = Field(default_factory=list)
    expected_facts: list[str] = Field(default_factory=list)
    expected_tool: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
