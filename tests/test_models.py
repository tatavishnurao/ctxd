import pytest
from ctxd.app.evals.schemas import GoldenEvalCase
from ctxd.app.models.domain import (
    ContextCandidate,
    ContextPacket,
    QueryRequest,
    SourceType,
    ToolCall,
)
from pydantic import ValidationError


def test_query_request_requires_non_empty_query() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="")


def test_context_packet_domain_model() -> None:
    candidate = ContextCandidate(
        source_id="doc-1",
        source_type=SourceType.DOCUMENT,
        content="content",
        token_cost=12,
        relevance_score=0.5,
    )
    packet = ContextPacket(candidates=[candidate], token_budget=100, context_tokens=12)
    assert packet.candidates[0].source_id == "doc-1"
    assert packet.token_budget == 100


def test_tool_call_schema() -> None:
    call = ToolCall(tool_name="lookup", arguments={"q": "ctxd"}, timeout_ms=1000)
    assert call.tool_name == "lookup"


def test_golden_eval_case_schema() -> None:
    case = GoldenEvalCase(
        id="case-1",
        question="Where is request_id recorded?",
        task_type="architecture",
        expected_sources=["ARCHITECTURE.md"],
        expected_facts=["Every request has request_id, trace_id, tenant_id."],
    )
    assert case.expected_tool is None
