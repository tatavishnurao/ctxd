"""Pluggable request authentication that derives the tenant from a credential.

Outside ``environment=development`` the tenant is never taken from a header:
it comes from a verified API key or JWT. The development-only header mode
performs no authentication and is named accordingly.
"""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Protocol

import jwt
from fastapi import HTTPException, Request, status

from ctxd.app.config.settings import Settings


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    authenticated: bool


class RequestVerifier(Protocol):
    def tenant(self, request: Request) -> Principal: ...

    def operator(self, request: Request) -> None:
        """Authorize operator-only endpoints such as /metrics."""
        ...


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _bearer(request: Request) -> str:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized("bearer credential is required")
    return token.strip()


def _digest(secret: str) -> bytes:
    return hashlib.sha256(secret.encode()).digest()


class _OperatorToken:
    def __init__(self, token: str | None) -> None:
        self._digest = _digest(token) if token else None

    def operator(self, request: Request) -> None:
        if self._digest is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="operator endpoints are disabled: CTXD_AUTH_OPERATOR_TOKEN is not set",
            )
        if not hmac.compare_digest(_digest(_bearer(request)), self._digest):
            raise _unauthorized("invalid operator credential")


class UnauthenticatedHeaderTenant:
    """Development only: trusts the client-supplied ``x-tenant-id`` header."""

    def tenant(self, request: Request) -> Principal:
        tenant_id = request.headers.get("x-tenant-id")
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="x-tenant-id header is required",
            )
        return Principal(tenant_id=tenant_id, authenticated=False)

    def operator(self, request: Request) -> None:
        return None


class ApiKeyVerifier(_OperatorToken):
    """Static API keys, each bound to exactly one tenant."""

    def __init__(self, keys: dict[str, str], operator_token: str | None) -> None:
        super().__init__(operator_token)
        self._tenants = {_digest(key): tenant for key, tenant in keys.items()}

    def tenant(self, request: Request) -> Principal:
        presented = _digest(_bearer(request))
        for digest, tenant_id in self._tenants.items():
            if hmac.compare_digest(presented, digest):
                return Principal(tenant_id=tenant_id, authenticated=True)
        raise _unauthorized("invalid API key")


class JwtVerifier(_OperatorToken):
    """HS256 JWTs; the tenant is read from a required claim."""

    def __init__(
        self,
        secret: str,
        *,
        tenant_claim: str,
        audience: str | None,
        issuer: str | None,
        operator_token: str | None,
    ) -> None:
        super().__init__(operator_token)
        self._secret = secret
        self._tenant_claim = tenant_claim
        self._audience = audience
        self._issuer = issuer

    def tenant(self, request: Request) -> Principal:
        try:
            claims = jwt.decode(
                _bearer(request),
                self._secret,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", self._tenant_claim]},
            )
        except jwt.PyJWTError as exc:
            raise _unauthorized("invalid or expired token") from exc
        tenant_id = claims[self._tenant_claim]
        if not isinstance(tenant_id, str) or not tenant_id:
            raise _unauthorized("token tenant claim must be a non-empty string")
        return Principal(tenant_id=tenant_id, authenticated=True)


def build_verifier(settings: Settings) -> RequestVerifier:
    if settings.auth_mode == "api_key":
        return ApiKeyVerifier(
            {key: tenant for key, tenant in settings.auth_api_keys.items()},
            settings.auth_operator_token,
        )
    if settings.auth_mode == "jwt":
        assert settings.auth_jwt_secret is not None  # enforced by Settings validation
        return JwtVerifier(
            settings.auth_jwt_secret,
            tenant_claim=settings.auth_jwt_tenant_claim,
            audience=settings.auth_jwt_audience,
            issuer=settings.auth_jwt_issuer,
            operator_token=settings.auth_operator_token,
        )
    return UnauthenticatedHeaderTenant()
