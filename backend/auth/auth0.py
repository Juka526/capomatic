"""Auth0 JWT verification and FastAPI user dependencies."""
from __future__ import annotations

import logging
import os
import json

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm

logger = logging.getLogger(__name__)

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "").strip()
AUTH0_AUDIENCE = os.environ.get("AUTH0_AUDIENCE", "").strip()
ALGORITHMS = ["RS256"]

_bearer = HTTPBearer(auto_error=False)

# JWKS cache — populated on first token verification.
_jwks: dict | None = None


_LOGIN_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Login is temporarily unavailable.",
)


async def _fetch_jwks(*, refresh: bool = False) -> dict:
    """Fetch the Auth0 JSON Web Key Set, cached until a key rotation."""
    global _jwks
    if _jwks is not None and not refresh:
        return _jwks

    # Configuration and network failures are server-side problems: report a
    # generic 503 and keep domain/URL details in the log only.
    if not AUTH0_DOMAIN:
        logger.error("AUTH0_DOMAIN is not configured")
        raise _LOGIN_UNAVAILABLE
    url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            _jwks = resp.json()
    except (httpx.HTTPError, ValueError):
        logger.exception("Could not fetch Auth0 JWKS")
        raise _LOGIN_UNAVAILABLE from None
    return _jwks


def _find_key(jwks: dict, kid: str | None) -> dict | None:
    return next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def verify_token(token: str) -> dict:
    """Verify an Auth0 JWT and return its payload.

    Raises HTTPException(401) on invalid/expired tokens and 503 when the
    signing keys cannot be obtained.
    """
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token header") from None

    key = _find_key(await _fetch_jwks(), kid)
    if key is None:
        # Auth0 may have rotated its signing key since the cache was filled.
        key = _find_key(await _fetch_jwks(refresh=True), kid)
    if key is None:
        raise _unauthorized("Unable to find matching signing key")

    try:
        public_key = RSAAlgorithm.from_jwk(json.dumps(key))
        return jwt.decode(
            token,
            public_key,
            algorithms=ALGORITHMS,
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token has expired") from None
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise _unauthorized("Invalid token") from None


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Verify a bearer token without requiring the optional user database."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return await verify_token(credentials.credentials)
