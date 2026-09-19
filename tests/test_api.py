from ctxd.app.main import create_app
from fastapi.testclient import TestClient


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get(
        "/health",
        headers={"x-request-id": "req-test", "x-tenant-id": "tenant-a"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "req-test"
    assert "x-trace-id" in response.headers


def test_query_placeholder() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/query",
        headers={"x-request-id": "req-query", "x-tenant-id": "tenant-a"},
        json={"query": "What is ctxd?", "tenant_id": "tenant-a", "task_type": "qa"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-query"
    assert body["context"]["candidates"] == []
    assert body["model_decision"]["selected_model"] == "not_routed"
    assert "not implemented" in body["answer"]


def test_metrics_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "ctxd_requests_total" in response.text
