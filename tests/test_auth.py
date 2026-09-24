"""Unit tests for Auth0 token validation without a user database."""
from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from backend.auth import auth0


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


def _token(private_key, *, audience="https://capomatic-api", expires_in=300):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "auth0|v1-user",
            "iss": "https://tenant.example/",
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "v1-test-key"},
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
