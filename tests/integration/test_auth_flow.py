"""Integration tests for authentication endpoints."""
from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_TOKEN"),
    reason="TEST_TOKEN not set",
)


class TestAuthMe:
    """GET /api/auth/me — verified Auth0 identity."""

    def test_returns_profile(self, client: httpx.Client, auth_headers: dict):
        res = client.get("/api/auth/me", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert body["sub"]
        assert "email" in body
        assert "name" in body

    def test_returns_401_without_token(self, client: httpx.Client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_returns_401_with_invalid_token(self, client: httpx.Client):
        res = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert res.status_code == 401


class TestAdminTest:
    """GET /api/auth/admin-test — retired in V1."""

    def test_authenticated_gets_410(self, client: httpx.Client, auth_headers: dict):
        res = client.get("/api/auth/admin-test", headers=auth_headers)
        assert res.status_code == 410

    def test_unauthenticated_gets_410(self, client: httpx.Client):
        res = client.get("/api/auth/admin-test")
        assert res.status_code == 410


class TestPublicEndpointsUnchanged:
    """Existing public endpoints must remain accessible without auth."""

    def test_health(self, client: httpx.Client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_detect_rejects_no_image(self, client: httpx.Client):
        res = client.post("/detect")
        assert res.status_code == 422

    def test_render_rejects_missing_id(self, client: httpx.Client):
        res = client.post("/render", data={"detection_id": "nonexistent"})
        assert res.status_code == 404
