"""Shared fixtures for integration tests.

These tests run against a live server (default http://localhost:8000)
and require a valid Auth0 access token in the TEST_TOKEN env var.

    export TEST_TOKEN="eyJ..."
    python -m pytest tests/integration/ -v
"""
from __future__ import annotations

import os

import httpx
import pytest

API_URL = os.environ.get("TEST_API_URL", "http://localhost:8000")
TEST_TOKEN = os.environ.get("TEST_TOKEN", "")
TEST_IMAGE = "fixtures/images/ci-selfmade.png"

# Skip the entire integration suite when no token is available.
pytestmark = pytest.mark.skipif(
    not TEST_TOKEN,
    reason="TEST_TOKEN not set — skipping integration tests",
)


@pytest.fixture(scope="session")
def api_url() -> str:
    return API_URL


@pytest.fixture(scope="session")
def token() -> str:
    return TEST_TOKEN


@pytest.fixture(scope="session")
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKEN}"}


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    """Persistent httpx client reused across tests."""
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="session")
def test_image_bytes() -> bytes:
    """Load the fixture test image as bytes."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", TEST_IMAGE)
    path = os.path.abspath(path)
    if not os.path.exists(path):
        pytest.skip(f"Test image not found: {path}")
    with open(path, "rb") as f:
        return f.read()
