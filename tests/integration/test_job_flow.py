"""Integration tests for job creation, history, and caching."""
from __future__ import annotations

import io
import os
import random
import time

import httpx
import pytest
from PIL import Image

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_TOKEN"),
    reason="TEST_TOKEN not set",
)


class TestJobCreation:
    """POST /api/overlay — authenticated overlay with job tracking."""

    def test_creates_job_and_returns_image(
        self,
        client: httpx.Client,
        auth_headers: dict,
        test_image_bytes: bytes,
    ):
        res = client.post(
            "/api/overlay",
            headers=auth_headers,
            files={"image": ("test.jpeg", test_image_bytes, "image/jpeg")},
            data={"semitones": "-1", "mode": "replace", "song_name": "친구야"},
            timeout=60.0,
        )
        assert res.status_code == 200
        assert res.headers.get("content-type", "").startswith("image/png")
        assert len(res.content) > 1000  # non-trivial PNG

    def test_rejects_without_auth(
        self,
        client: httpx.Client,
        test_image_bytes: bytes,
    ):
        res = client.post(
            "/api/overlay",
            files={"image": ("test.jpeg", test_image_bytes, "image/jpeg")},
            data={"semitones": "-1", "mode": "replace"},
            timeout=60.0,
        )
        assert res.status_code == 401

    def test_rejects_invalid_mode(
        self,
        client: httpx.Client,
        auth_headers: dict,
        test_image_bytes: bytes,
    ):
        res = client.post(
            "/api/overlay",
            headers=auth_headers,
            files={"image": ("test.jpeg", test_image_bytes, "image/jpeg")},
            data={"semitones": "-1", "mode": "invalid"},
        )
        assert res.status_code == 422

    def test_rejects_invalid_semitones(
        self,
        client: httpx.Client,
        auth_headers: dict,
        test_image_bytes: bytes,
    ):
        res = client.post(
            "/api/overlay",
            headers=auth_headers,
            files={"image": ("test.jpeg", test_image_bytes, "image/jpeg")},
            data={"semitones": "-15", "mode": "replace"},
        )
        assert res.status_code == 422


class TestJobHistory:
    """GET /api/jobs/my — user's job history."""

    def test_returns_jobs(self, client: httpx.Client, auth_headers: dict):
        res = client.get("/api/jobs/my", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert "jobs" in body
        assert "count" in body
        assert isinstance(body["jobs"], list)

    def test_job_has_expected_fields(self, client: httpx.Client, auth_headers: dict):
        res = client.get("/api/jobs/my", headers=auth_headers)
        body = res.json()
        if body["count"] == 0:
            pytest.skip("No jobs to inspect — run TestJobCreation first")
        job = body["jobs"][0]
        expected_fields = {
            "id", "song_name", "original_key", "target_key",
            "semitones", "mode", "status", "detected_chords_count",
            "processing_time_ms", "from_cache", "created_at",
        }
        assert expected_fields.issubset(job.keys())

    def test_pagination(self, client: httpx.Client, auth_headers: dict):
        res = client.get("/api/jobs/my?limit=1&offset=0", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert len(body["jobs"]) <= 1

    def test_rejects_without_auth(self, client: httpx.Client):
        res = client.get("/api/jobs/my")
        assert res.status_code == 401


class TestJobResults:
    """GET /api/results/{job_id} — download rendered image."""

    def _get_first_completed_job_id(
        self, client: httpx.Client, auth_headers: dict,
    ) -> str | None:
        res = client.get("/api/jobs/my", headers=auth_headers)
        for job in res.json().get("jobs", []):
            if job["status"] == "completed":
                return job["id"]
        return None

    def test_download_result(self, client: httpx.Client, auth_headers: dict):
        job_id = self._get_first_completed_job_id(client, auth_headers)
        if job_id is None:
            pytest.skip("No completed jobs — run TestJobCreation first")
        res = client.get(f"/api/results/{job_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.headers.get("content-type", "").startswith("image/png")

    def test_invalid_job_id_returns_400(self, client: httpx.Client, auth_headers: dict):
        res = client.get("/api/results/not-a-uuid", headers=auth_headers)
        assert res.status_code == 400

    def test_nonexistent_job_returns_404(self, client: httpx.Client, auth_headers: dict):
        fake_id = "00000000-0000-0000-0000-000000000000"
        res = client.get(f"/api/results/{fake_id}", headers=auth_headers)
        assert res.status_code == 404


class TestJobDeletion:
    """DELETE /api/jobs/{job_id} — soft delete."""

    @staticmethod
    def _unique_image() -> bytes:
        """Generate a small PNG with random pixels to guarantee a unique hash."""
        img = Image.new("RGB", (50, 50))
        for x in range(50):
            for y in range(50):
                img.putpixel((x, y), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_soft_delete_job(
        self,
        client: httpx.Client,
        auth_headers: dict,
    ):
        unique_img = self._unique_image()

        # Snapshot job IDs before creation
        before = client.get("/api/jobs/my", headers=auth_headers).json()
        before_ids = {j["id"] for j in before["jobs"]}

        # Create a job with a unique image (guaranteed cache miss)
        create_res = client.post(
            "/api/overlay",
            headers=auth_headers,
            files={"image": ("del_test.png", unique_img, "image/png")},
            data={"semitones": "-1", "mode": "above", "song_name": "delete_test"},
            timeout=60.0,
        )
        assert create_res.status_code == 200

        # Find the newly created job by diffing against the snapshot
        after = client.get("/api/jobs/my", headers=auth_headers).json()
        new_jobs = [j for j in after["jobs"] if j["id"] not in before_ids]
        assert new_jobs, "No new job appeared in history after creation"
        job_id = new_jobs[0]["id"]

        # Delete it
        del_res = client.delete(f"/api/jobs/{job_id}", headers=auth_headers)
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True

        # Verify it no longer appears in history
        history = client.get("/api/jobs/my", headers=auth_headers).json()
        ids = [j["id"] for j in history["jobs"]]
        assert job_id not in ids

    def test_delete_nonexistent_returns_404(
        self, client: httpx.Client, auth_headers: dict,
    ):
        fake_id = "00000000-0000-0000-0000-000000000000"
        res = client.delete(f"/api/jobs/{fake_id}", headers=auth_headers)
        assert res.status_code == 404


class TestCaching:
    """Verify that repeated requests hit the cache."""

    def test_second_request_is_cache_hit(
        self,
        client: httpx.Client,
        auth_headers: dict,
        test_image_bytes: bytes,
    ):
        payload = {
            "semitones": "-3",
            "mode": "replace",
            "song_name": "cache_test",
        }

        # First request — cache MISS
        t0 = time.perf_counter()
        r1 = client.post(
            "/api/overlay",
            headers=auth_headers,
            files={"image": ("cache.jpeg", test_image_bytes, "image/jpeg")},
            data=payload,
            timeout=60.0,
        )
        first_ms = (time.perf_counter() - t0) * 1000
        assert r1.status_code == 200

        # Second request — cache HIT
        t0 = time.perf_counter()
        r2 = client.post(
            "/api/overlay",
            headers=auth_headers,
            files={"image": ("cache.jpeg", test_image_bytes, "image/jpeg")},
            data=payload,
            timeout=60.0,
        )
        second_ms = (time.perf_counter() - t0) * 1000
        assert r2.status_code == 200
        assert r2.headers.get("x-cache") == "HIT"

        # Cache hit should be substantially faster
        print(f"\n  First:  {first_ms:.0f}ms")
        print(f"  Second: {second_ms:.0f}ms")
        print(f"  Speedup: {first_ms / max(second_ms, 1):.1f}x")
