from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any, Literal, cast

from ctxd.app.integrations.synapse.schemas import (
    McpInvocationResult,
    McpToolSchema,
    SynapseEvalCase,
    SynapseEvalReport,
    SynapseEvalResult,
    SynapseFailureCategory,
)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return ordered[index]


def _json_type_matches(value: Any, json_type: str) -> bool:
    if json_type == "string":
        return isinstance(value, str)
    if json_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if json_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if json_type == "boolean":
        return isinstance(value, bool)
    if json_type == "array":
        return isinstance(value, list)
    if json_type == "object":
        return isinstance(value, dict)
    return True


def validate_arguments(schema: McpToolSchema | None, arguments: Mapping[str, Any] | None) -> bool:
    if schema is None or arguments is None:
        return False
    input_schema = schema.input_schema
    required = input_schema.get("required", [])
    if not isinstance(required, list):
        return False
    for key in required:
        if not isinstance(key, str) or key not in arguments:
            return False
    properties = input_schema.get("properties", {})
    if not isinstance(properties, dict):
        return False
    for key, value in arguments.items():
        definition = properties.get(key)
        if (
            isinstance(definition, dict)
            and isinstance(definition.get("type"), str)
            and not _json_type_matches(value, definition["type"])
        ):
            return False
    return True


def _tool_correct(case: SynapseEvalCase, selected_tool: str | None) -> bool:
    acceptable = set(case.acceptable_tools)
    if case.expected_tool is not None:
        acceptable.add(case.expected_tool)
    return selected_tool is not None and selected_tool in acceptable


def _arguments_match(expected: Mapping[str, Any], actual: Mapping[str, Any] | None) -> bool:
    if actual is None:
        return False
    return all(actual.get(key) == value for key, value in expected.items())


def _output_status(case: SynapseEvalCase, invocation: McpInvocationResult) -> str:
    if case.expected_outcome is None:
        return "not_checked"
    return "match" if invocation.output == case.expected_outcome else "mismatch"


def evaluate_cases(
    cases: Iterable[SynapseEvalCase],
    invocations: Mapping[str, McpInvocationResult],
    tool_schemas: Iterable[McpToolSchema],
    *,
    synthetic: bool = True,
) -> SynapseEvalReport:
    schema_by_name = {schema.name: schema for schema in tool_schemas}
    results: list[SynapseEvalResult] = []
    failures: Counter[str] = Counter()
    for case in cases:
        invocation = invocations[case.id]
        schema = schema_by_name.get(invocation.selected_tool or "")
        schema_valid = validate_arguments(schema, invocation.arguments)
        tool_correct = _tool_correct(case, invocation.selected_tool)
        arguments_valid = schema_valid and _arguments_match(
            case.expected_arguments, invocation.arguments
        )
        output_status = _output_status(case, invocation)
        task_success = (
            tool_correct
            and arguments_valid
            and invocation.execution_success
            and output_status != "mismatch"
        )
        category = invocation.error_category
        if category is None and not tool_correct:
            category = SynapseFailureCategory.WRONG_TOOL
        elif category is None and not schema_valid:
            category = SynapseFailureCategory.SCHEMA_VIOLATION
        elif category is None and not arguments_valid:
            category = SynapseFailureCategory.MALFORMED_ARGUMENTS
        elif category is None and not invocation.execution_success:
            category = SynapseFailureCategory.EXECUTION_ERROR
        elif category is None and invocation.execution_success and output_status == "mismatch":
            category = SynapseFailureCategory.INCORRECT_OUTPUT
        if category is not None and not task_success:
            failures[category.value] += 1
        results.append(
            SynapseEvalResult(
                case_id=case.id,
                selected_tool=invocation.selected_tool,
                tool_selection_correct=tool_correct,
                argument_validity=arguments_valid,
                schema_validity=schema_valid,
                execution_success=invocation.execution_success,
                task_success=task_success,
                retry_count=invocation.retry_count,
                latency_ms=invocation.latency_ms,
                error_category=category if not task_success else None,
                output_match_status=cast(
                    "Literal['match', 'mismatch', 'not_checked']", output_status
                ),
                metadata={**case.metadata, **invocation.metadata},
            )
        )
    count = len(results)
    denominator = max(count, 1)
    latencies = [result.latency_ms for result in results]
    return SynapseEvalReport(
        synthetic=synthetic,
        case_count=count,
        tool_selection_accuracy=sum(r.tool_selection_correct for r in results) / denominator,
        schema_validity_rate=sum(r.schema_validity for r in results) / denominator,
        argument_validity_rate=sum(r.argument_validity for r in results) / denominator,
        task_success_rate=sum(r.task_success for r in results) / denominator,
        execution_success_rate=sum(r.execution_success for r in results) / denominator,
        retry_rate=sum(r.retry_count > 0 for r in results) / denominator,
        p50_latency_ms=_percentile(latencies, 0.50),
        p95_latency_ms=_percentile(latencies, 0.95),
        p99_latency_ms=_percentile(latencies, 0.99),
        failure_counts=dict(sorted(failures.items())),
        results=results,
    )
