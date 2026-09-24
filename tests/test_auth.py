"""Unit tests for Auth0 token validation without a user database."""
from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.auth import auth0

client = TestClient(app, raise_server_exceptions=False)


def _b64uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture
def rsa_identity():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwks = {"keys": [{
        "kty": "RSA",
        "kid": "v1-test-key",
        "use": "sig",
        "alg": "RS256",
        "n": _b64uint(numbers.n),
        "e": _b64uint(numbers.e),
    }]}
    return private_key, jwks


def _token(
    private_key,
    *,
    audience="https://capomatic-api",
    expires_in=300,
    issuer="https://tenant.example/",
    kid="v1-test-key",
    extra_claims=None,
):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "auth0|v1-user",
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            **(extra_claims or {}),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


def test_verify_token_accepts_expected_issuer_and_audience(rsa_identity):
    private_key, jwks = rsa_identity
    with (
        patch.object(auth0, "AUTH0_DOMAIN", "tenant.example"),
        patch.object(auth0, "AUTH0_AUDIENCE", "https://capomatic-api"),
        patch.object(auth0, "_fetch_jwks", AsyncMock(return_value=jwks)),
    ):
        payload = asyncio.run(auth0.verify_token(_token(private_key)))
    assert payload["sub"] == "auth0|v1-user"


@pytest.mark.parametrize("audience,expires_in", [
    ("https://wrong.example", 300),
    ("https://capomatic-api", -1),
])
def test_verify_token_rejects_invalid_claims(rsa_identity, audience, expires_in):
    private_key, jwks = rsa_identity
    with (
        patch.object(auth0, "AUTH0_DOMAIN", "tenant.example"),
        patch.object(auth0, "AUTH0_AUDIENCE", "https://capomatic-api"),
        patch.object(auth0, "_fetch_jwks", AsyncMock(return_value=jwks)),
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(auth0.verify_token(
                _token(private_key, audience=audience, expires_in=expires_in)
            ))
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# /api/auth/me through the real verifier (issue #12)
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_config(rsa_identity):
    private_key, jwks = rsa_identity
    fetch = AsyncMock(return_value=jwks)
    with (
        patch.object(auth0, "AUTH0_DOMAIN", "tenant.example"),
        patch.object(auth0, "AUTH0_AUDIENCE", "https://capomatic-api"),
        patch.object(auth0, "_fetch_jwks", fetch),
    ):
        yield private_key, fetch


def _me(token=None):
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return client.get("/api/auth/me", headers=headers)


def test_auth_me_returns_only_minimal_identity(auth_config):
    private_key, _ = auth_config
    token = _token(private_key, extra_claims={
        "email": "user@example.com",
        "name": "User",
        "permissions": ["admin"],
        "https://example/roles": ["admin"],
    })

    resp = _me(token)

    assert resp.status_code == 200
    assert resp.json() == {"sub": "auth0|v1-user", "email": "user@example.com", "name": "User"}


@pytest.mark.parametrize("case", [
    "missing",
    "malformed",
    "expired",
    "wrong_issuer",
    "wrong_audience",
    "unknown_kid",
    "alg_none",
])
def test_auth_me_rejects_invalid_tokens_without_details(auth_config, case):
    private_key, _ = auth_config
    token = {
        "missing": None,
        "malformed": "not-a-jwt",
        "expired": _token(private_key, expires_in=-1),
        "wrong_issuer": _token(private_key, issuer="https://evil.example/"),
        "wrong_audience": _token(private_key, audience="https://other-api"),
        "unknown_kid": _token(private_key, kid="rotated-away"),
        "alg_none": jwt.encode(
            {"sub": "auth0|v1-user", "iss": "https://tenant.example/",
             "aud": "https://capomatic-api", "exp": 4102444800},
            key=None, algorithm="none", headers={"kid": "v1-test-key"},
        ),
    }[case]

    resp = _me(token)

    assert resp.status_code == 401
    body = resp.text
    assert "tenant.example" not in body and "Traceback" not in body


def test_malformed_token_is_rejected_before_fetching_keys(auth_config):
    _, fetch = auth_config

    _me("not-a-jwt")

    fetch.assert_not_called()


def test_unknown_kid_refreshes_keys_once(auth_config, rsa_identity):
    private_key, fetch = auth_config
    _, jwks = rsa_identity
    fetch.side_effect = [{"keys": []}, jwks]

    resp = _me(_token(private_key))

    assert resp.status_code == 200
    assert [call.kwargs for call in fetch.call_args_list] == [{}, {"refresh": True}]


def test_missing_domain_is_generic_503():
    with patch.object(auth0, "AUTH0_DOMAIN", ""), patch.object(auth0, "_jwks", None):
        resp = _me("eyJhbGciOiJSUzI1NiIsImtpZCI6ImsifQ.e30.sig")

    assert resp.status_code == 503
    assert "AUTH0" not in resp.text


def test_jwks_network_failure_is_generic_503():
    with (
        patch.object(auth0, "AUTH0_DOMAIN", "tenant.example"),
        patch.object(auth0, "_jwks", None),
        patch("httpx.AsyncClient.get", AsyncMock(side_effect=httpx.ConnectError("down"))),
    ):
        resp = _me("eyJhbGciOiJSUzI1NiIsImtpZCI6ImsifQ.e30.sig")

    assert resp.status_code == 503
    assert "tenant.example" not in resp.text


def test_jwk_without_use_field_still_verifies(rsa_identity):
    private_key, jwks = rsa_identity
    stripped = {"keys": [{k: v for k, v in jwks["keys"][0].items() if k != "use"}]}
    with (
        patch.object(auth0, "AUTH0_DOMAIN", "tenant.example"),
        patch.object(auth0, "AUTH0_AUDIENCE", "https://capomatic-api"),
        patch.object(auth0, "_fetch_jwks", AsyncMock(return_value=stripped)),
    ):
        resp = _me(_token(private_key))

    assert resp.status_code == 200
