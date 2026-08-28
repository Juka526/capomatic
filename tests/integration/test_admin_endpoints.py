"""Integration tests for admin endpoints."""
from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_TOKEN"),
    reason="TEST_TOKEN not set",
)


def _is_admin(client: httpx.Client, headers: dict) -> bool:
    """Return True if the test token belongs to an admin user."""
    res = client.get("/api/auth/me", headers=headers)
    return res.status_code == 200 and res.json().get("role") == "admin"


class TestAdminUsers:
    """GET /api/admin/users"""

    def test_returns_users_for_admin(self, client: httpx.Client, auth_headers: dict):
        if not _is_admin(client, auth_headers):
            pytest.skip("Test user is not admin")
        res = client.get("/api/admin/users", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert "users" in body
        assert isinstance(body["users"], list)
        assert len(body["users"]) >= 1
        user = body["users"][0]
        assert "id" in user
        assert "email" in user
        assert "role" in user
        assert "created_at" in user

    def test_rejects_non_admin(self, client: httpx.Client, auth_headers: dict):
        if _is_admin(client, auth_headers):
            pytest.skip("Test user is admin — can't test 403")
        res = client.get("/api/admin/users", headers=auth_headers)
        assert res.status_code == 403
