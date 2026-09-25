from ctxd.app.integrations.synapse.evaluator import evaluate_cases
from ctxd.app.integrations.synapse.schemas import (
    McpInvocationResult,
    McpToolSchema,
    SynapseEvalCase,
)


def synthetic_tool_schemas() -> list[McpToolSchema]:
    return [
        McpToolSchema(
            name="search_code",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            },
        ),
        McpToolSchema(
            name="read_file",
            input_schema={
                "type": "object",
                "required": ["path"],
                "properties": {"path": {"type": "string"}},
            },
        ),
        McpToolSchema(
            name="run_tests",
            input_schema={
                "type": "object",
                "required": ["target"],
                "properties": {"target": {"type": "string"}},
            },
        ),
    ]


def synthetic_cases(count: int = 50) -> list[SynapseEvalCase]:
    cases: list[SynapseEvalCase] = []
    tools = ["search_code", "read_file", "run_tests"]
    for index in range(count):
        tool = tools[index % len(tools)]
        outcome: object
        if tool == "search_code":
            args = {"query": f"symbol_{index}", "limit": 5}
            outcome = [f"src/module_{index}.py"]
        elif tool == "read_file":
            args = {"path": f"src/module_{index}.py"}
            outcome = f"contents:{index}"
        else:
            args = {"target": "unit"}
            outcome = {"passed": True}
        cases.append(
            SynapseEvalCase(
                id=f"syn-fixture-{index:03d}",
                task=f"Synthetic MCP task {index}",
                expected_tool=tool,
                expected_arguments=args,
                expected_outcome=outcome,
                expected_sources=[f"src/module_{index}.py"] if tool != "run_tests" else [],
                metadata={"fixture": True},
            )
        )
    return cases


def synthetic_invocations(cases: list[SynapseEvalCase]) -> dict[str, McpInvocationResult]:
    invocations: dict[str, McpInvocationResult] = {}
    for index, case in enumerate(cases):
        selected_tool = case.expected_tool
        arguments = dict(case.expected_arguments)
        output = case.expected_outcome
        success = True
        if index in {7, 23}:
            selected_tool = "read_file" if case.expected_tool != "read_file" else "search_code"
        if index in {11, 29}:
            arguments = {"unexpected": True}
        if index in {17, 41}:
            success = False
        if index in {19, 37}:
            output = {"wrong": True}
        invocations[case.id] = McpInvocationResult(
            selected_tool=selected_tool,
            arguments=arguments,
            output=output,
            execution_success=success,
            retry_count=1 if index in {5, 31} else 0,
            latency_ms=8.0 + (index % 10) * 3.0,
            metadata={"synthetic_server": "fake-synapse-mcp-v1"},
        )
    return invocations


def run_synthetic_fixture(count: int = 50) -> str:
    cases = synthetic_cases(count)
    report = evaluate_cases(cases, synthetic_invocations(cases), synthetic_tool_schemas())
    return report.model_dump_json(indent=2)
