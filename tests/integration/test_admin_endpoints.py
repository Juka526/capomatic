"""Integration tests for admin endpoints."""
from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_TOKEN"),
    reason="TEST_TOKEN not set",
)


class TestAdminUsers:
    """GET /api/admin/users — retired in V1."""

    def test_rejects_authenticated(self, client: httpx.Client, auth_headers: dict):
        res = client.get("/api/admin/users", headers=auth_headers)
        assert res.status_code == 410

    def test_rejects_unauthenticated(self, client: httpx.Client):
        res = client.get("/api/admin/users")
        assert res.status_code == 410
