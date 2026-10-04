"""CORS is opt-in via CTXD_CORS_ALLOW_ORIGINS and wildcard is development-only."""

import pytest
from ctxd.app.config.settings import Settings
from ctxd.app.main import create_app
from fastapi.testclient import TestClient
from pydantic import ValidationError


def _client(**overrides: object) -> TestClient:
    return TestClient(create_app(settings=Settings(**overrides)))  # type: ignore[arg-type]


def test_cors_preflight_allows_configured_origin() -> None:
    client = _client(cors_allow_origins=["http://localhost:8080"])
    response = client.options(
        "/v1/query",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8080"


def test_no_cors_headers_when_unconfigured() -> None:
    client = _client()
    response = client.get("/health", headers={"Origin": "http://localhost:8080"})
    assert "access-control-allow-origin" not in response.headers


def test_wildcard_cors_rejected_outside_development() -> None:
    with pytest.raises(ValidationError):
        Settings(
            cors_allow_origins=["*"],
            environment="production",
            auth_mode="api_key",
            auth_api_keys={"k" * 32: "demo"},
        )


def test_wildcard_cors_allowed_in_development() -> None:
    settings = Settings(cors_allow_origins=["*"], environment="development")
    assert settings.cors_allow_origins == ["*"]
    assert settings.effective_configuration()["cors_enabled"] is True
