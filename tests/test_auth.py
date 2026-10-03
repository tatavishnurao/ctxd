"""Credential-derived tenancy: no tenant is readable by header alone outside development."""

import time

import jwt
import pytest
from ctxd.app.config.settings import Settings
from ctxd.app.main import create_app
from ctxd.app.storage.documents import InMemoryDocumentStore
from fastapi.testclient import TestClient
from pydantic import ValidationError

KEY_A = "a" * 40
KEY_B = "b" * 40
OPERATOR = "o" * 40
SECRET = "s" * 48


def document(tenant: str) -> dict[str, str]:
    return {
        "tenant_id": tenant,
        "source_path": "secret.md",
        "source_type": "markdown",
        "content": f"The {tenant} launch codename is zephyr.",
    }


def query(tenant: str) -> dict[str, str]:
    return {"tenant_id": tenant, "query": "launch codename zephyr"}


def bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def api_key_client(**overrides: object) -> TestClient:
    settings = Settings(
        environment="production",
        auth_mode="api_key",
        auth_api_keys={KEY_A: "tenant-a", KEY_B: "tenant-b"},
        **overrides,  # type: ignore[arg-type]
    )
    return TestClient(create_app(InMemoryDocumentStore(), settings))


def jwt_client() -> TestClient:
    settings = Settings(
        environment="production",
        auth_mode="jwt",
        auth_jwt_secret=SECRET,
        auth_jwt_audience="ctxd",
    )
    return TestClient(create_app(InMemoryDocumentStore(), settings))


def token(claims: dict[str, object], secret: str = SECRET) -> str:
    payload: dict[str, object] = {"aud": "ctxd", "exp": int(time.time()) + 60, **claims}
    return jwt.encode(payload, secret, algorithm="HS256")


# --- deny by default -----------------------------------------------------------------


def test_header_trust_is_refused_outside_development() -> None:
    with pytest.raises(ValidationError, match="requires authentication"):
        Settings(environment="production")
    assert Settings(environment="development").auth_mode == "none"


@pytest.mark.parametrize(
    "overrides",
    [
        {"auth_mode": "api_key"},
        {"auth_mode": "api_key", "auth_api_keys": {"short": "t"}},
        {"auth_mode": "jwt"},
        {"auth_mode": "jwt", "auth_jwt_secret": "short"},
        {"auth_mode": "jwt", "auth_jwt_secret": SECRET, "auth_operator_token": "short"},
    ],
)
def test_incomplete_or_weak_auth_configuration_is_refused(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", **overrides)  # type: ignore[arg-type]


def test_header_alone_cannot_read_a_tenant_when_authentication_is_on() -> None:
    client = api_key_client()
    assert client.post("/v1/documents", headers=bearer(KEY_A), json=document("tenant-a")).is_success
    for path, body in (("/v1/query", query("tenant-a")), ("/v1/documents", document("tenant-a"))):
        response = client.post(path, headers={"x-tenant-id": "tenant-a"}, json=body)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    for path in ("/v1/index/statistics", "/v1/index/semantic-statistics"):
        assert client.get(path, headers={"x-tenant-id": "tenant-a"}).status_code == 401


# --- API keys ------------------------------------------------------------------------


def test_api_key_derives_tenant_and_isolates_reads() -> None:
    client = api_key_client()
    assert client.post("/v1/documents", headers=bearer(KEY_A), json=document("tenant-a")).is_success

    own = client.post("/v1/query", headers=bearer(KEY_A), json=query("tenant-a"))
    assert own.status_code == 200
    assert own.json()["context"]["candidates"][0]["content"].startswith("The tenant-a")

    other = client.post("/v1/query", headers=bearer(KEY_B), json=query("tenant-b"))
    assert other.json()["context"]["candidates"] == []
    stats = client.get("/v1/index/statistics", headers=bearer(KEY_B)).json()
    assert stats["indexed_documents"] == 0


def test_api_key_cannot_be_redirected_to_another_tenant() -> None:
    client = api_key_client()
    by_body = client.post("/v1/query", headers=bearer(KEY_B), json=query("tenant-a"))
    assert by_body.status_code == 403
    by_header = client.post(
        "/v1/query",
        headers={**bearer(KEY_B), "x-tenant-id": "tenant-a"},
        json=query("tenant-b"),
    )
    assert by_header.status_code == 403
    by_header_stats = client.get(
        "/v1/index/statistics", headers={**bearer(KEY_B), "x-tenant-id": "tenant-a"}
    )
    assert by_header_stats.status_code == 403


@pytest.mark.parametrize("header", ["Bearer " + "x" * 40, "Basic " + KEY_A, KEY_A, "Bearer"])
def test_invalid_or_malformed_api_credentials_are_401(header: str) -> None:
    response = api_key_client().post(
        "/v1/query", headers={"authorization": header}, json=query("tenant-a")
    )
    assert response.status_code == 401


# --- JWT -----------------------------------------------------------------------------


def test_jwt_tenant_claim_is_the_tenant() -> None:
    client = jwt_client()
    credential = bearer(token({"tenant_id": "tenant-a"}))
    assert client.post("/v1/documents", headers=credential, json=document("tenant-a")).is_success
    response = client.post("/v1/query", headers=credential, json=query("tenant-a"))
    assert len(response.json()["context"]["candidates"]) == 1
    assert client.post("/v1/query", headers=credential, json=query("tenant-b")).status_code == 403


@pytest.mark.parametrize(
    "bad_token",
    [
        token({"tenant_id": "tenant-a", "exp": int(time.time()) - 10}),
        token({"tenant_id": "tenant-a"}, secret="w" * 48),
        token({"tenant_id": "tenant-a", "aud": "someone-else"}),
        token({}),
        token({"tenant_id": ""}),
        jwt.encode({"tenant_id": "tenant-a", "aud": "ctxd"}, SECRET, algorithm="HS256"),
        jwt.encode(
            {"tenant_id": "tenant-a", "aud": "ctxd", "exp": int(time.time()) + 60},
            key=None,
            algorithm="none",
        ),
    ],
    ids=[
        "expired",
        "wrong-secret",
        "wrong-audience",
        "no-tenant",
        "empty-tenant",
        "no-exp",
        "alg-none",
    ],
)
def test_invalid_jwts_are_401(bad_token: str) -> None:
    response = jwt_client().post("/v1/query", headers=bearer(bad_token), json=query("tenant-a"))
    assert response.status_code == 401


# --- operator endpoints ---------------------------------------------------------------


def test_metrics_require_operator_token_when_authentication_is_on() -> None:
    assert api_key_client().get("/metrics").status_code == 403
    client = api_key_client(auth_operator_token=OPERATOR)
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers=bearer(KEY_A)).status_code == 401
    assert client.get("/metrics", headers=bearer(OPERATOR)).status_code == 200


def test_liveness_and_readiness_stay_open_for_orchestrators() -> None:
    client = api_key_client()
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_development_mode_is_labeled_unauthenticated() -> None:
    settings = Settings()
    assert settings.effective_configuration()["auth_mode"] == "none"
    client = TestClient(create_app(InMemoryDocumentStore(), settings))
    assert client.get("/metrics").status_code == 200
    mismatch = client.post("/v1/query", headers={"x-tenant-id": "tenant-a"}, json=query("tenant-b"))
    assert mismatch.json()["detail"] == "tenant_id does not match the request tenant"
