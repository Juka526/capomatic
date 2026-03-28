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


class TestAdminStats:
    """GET /api/admin/stats"""

    def test_returns_stats_for_admin(self, client: httpx.Client, auth_headers: dict):
        if not _is_admin(client, auth_headers):
            pytest.skip("Test user is not admin")
        res = client.get("/api/admin/stats", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert "total_users" in body
        assert "total_jobs" in body
        assert "total_cached" in body
        assert "cache_hit_rate" in body
        assert "avg_processing_time" in body
        assert body["total_users"] >= 1

    def test_rejects_non_admin(self, client: httpx.Client, auth_headers: dict):
        if _is_admin(client, auth_headers):
            pytest.skip("Test user is admin — can't test 403")
        res = client.get("/api/admin/stats", headers=auth_headers)
        assert res.status_code == 403

    def test_rejects_unauthenticated(self, client: httpx.Client):
        res = client.get("/api/admin/stats")
        assert res.status_code == 401


class TestAdminPopular:
    """GET /api/admin/popular"""

    def test_returns_songs_for_admin(self, client: httpx.Client, auth_headers: dict):
        if not _is_admin(client, auth_headers):
            pytest.skip("Test user is not admin")
        res = client.get("/api/admin/popular?limit=5", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert "songs" in body
        assert isinstance(body["songs"], list)
        # If there are songs, check the shape
        if body["songs"]:
            song = body["songs"][0]
            assert "song_name" in song
            assert "original_key" in song
            assert "request_count" in song

    def test_rejects_non_admin(self, client: httpx.Client, auth_headers: dict):
        if _is_admin(client, auth_headers):
            pytest.skip("Test user is admin — can't test 403")
        res = client.get("/api/admin/popular", headers=auth_headers)
        assert res.status_code == 403


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


class TestOwnershipIsolation:
    """Verify users cannot access other users' resources."""

    def test_cannot_access_other_users_job(
        self, client: httpx.Client, auth_headers: dict,
    ):
        # Use a UUID that definitely doesn't belong to the test user
        fake_id = "11111111-1111-1111-1111-111111111111"
        res = client.get(f"/api/results/{fake_id}", headers=auth_headers)
        assert res.status_code == 404

    def test_cannot_delete_other_users_job(
        self, client: httpx.Client, auth_headers: dict,
    ):
        fake_id = "11111111-1111-1111-1111-111111111111"
        res = client.delete(f"/api/jobs/{fake_id}", headers=auth_headers)
        assert res.status_code == 404
