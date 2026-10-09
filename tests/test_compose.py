"""The compose stack must pass dashboard CORS origins into its containers.

A host-shell export never reaches a container, so the origins have to be declared in
docker-compose.yml itself; otherwise the dashboard's preflight gets a 405 with no
Access-Control-Allow-Origin and the browser reports "Failed to fetch".
"""

import re
from pathlib import Path

import yaml
from ctxd.app.config.settings import Settings
from ctxd.app.main import create_app
from fastapi.testclient import TestClient

COMPOSE_FILE = Path(__file__).resolve().parents[1] / "docker-compose.yml"
DASHBOARD_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080"]


def _compose_cors_default() -> str:
    compose = yaml.safe_load(COMPOSE_FILE.read_text())
    value = compose["x-ctxd-env"]["CTXD_CORS_ALLOW_ORIGINS"]
    # Resolve compose's ${VAR:-default} interpolation the way an unset host env would.
    match = re.fullmatch(r"\$\{CTXD_CORS_ALLOW_ORIGINS:-(.*)\}", value)
    return match.group(1) if match else value


def test_compose_env_declares_dashboard_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv("CTXD_CORS_ALLOW_ORIGINS", _compose_cors_default())
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.cors_allow_origins == DASHBOARD_ORIGINS
    assert settings.environment == "development"


def test_compose_cors_default_allows_dashboard_preflight(monkeypatch) -> None:
    monkeypatch.setenv("CTXD_CORS_ALLOW_ORIGINS", _compose_cors_default())
    client = TestClient(create_app(settings=Settings(_env_file=None)))  # type: ignore[call-arg]
    response = client.options(
        "/v1/query",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8080"
