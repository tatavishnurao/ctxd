from ctxd.app.integrations.synapse.evaluator import evaluate_cases
from ctxd.app.integrations.synapse.fixture import (
    synthetic_cases,
    synthetic_invocations,
    synthetic_tool_schemas,
)


def test_synthetic_synapse_fixture_report() -> None:
    cases = synthetic_cases(50)
    report = evaluate_cases(cases, synthetic_invocations(cases), synthetic_tool_schemas())

    assert report.synthetic is True
    assert report.case_count == 50
    assert report.tool_selection_accuracy == 0.96
    assert report.argument_validity_rate == 0.92
    assert report.execution_success_rate == 0.96
    assert report.task_success_rate == 0.84
    assert report.retry_rate == 0.04
    assert report.failure_counts == {
        "execution_error": 2,
        "incorrect_output": 2,
        "schema_violation": 2,
        "wrong_tool": 2,
    }
