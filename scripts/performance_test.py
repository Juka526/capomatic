#!/usr/bin/env python3
"""Performance benchmarks for Capomatic API.

Usage:
    export TEST_TOKEN="eyJ..."
    python scripts/performance_test.py

Requires a running server at http://localhost:8000 and a valid Auth0 token.
"""
from __future__ import annotations

import os
import sys
import time

import httpx

API_URL = os.environ.get("TEST_API_URL", "http://localhost:8000")
TOKEN = os.environ.get("TEST_TOKEN", "")
IMAGE_PATH = "fixtures/images/친구야.jpeg"

THRESHOLDS = {
    "auth_ms": 100,
    "history_ms": 200,
    "processing_ms": 5000,
    "cache_speedup": 5.0,
}


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000


def _load_image() -> bytes:
    with open(IMAGE_PATH, "rb") as f:
        return f.read()


def bench_auth(client: httpx.Client, headers: dict) -> float:
    """Benchmark GET /api/auth/me."""
    t0 = time.perf_counter()
    res = client.get("/api/auth/me", headers=headers)
    elapsed = _ms(t0)
    assert res.status_code == 200, f"/api/auth/me failed: {res.status_code}"
    return elapsed


def bench_history(client: httpx.Client, headers: dict) -> float:
    """Benchmark GET /api/jobs/my."""
    t0 = time.perf_counter()
    res = client.get("/api/jobs/my", headers=headers)
    elapsed = _ms(t0)
    assert res.status_code == 200, f"/api/jobs/my failed: {res.status_code}"
    return elapsed


def bench_processing(client: httpx.Client, headers: dict, img: bytes) -> float:
    """Benchmark POST /api/overlay (first request — cold)."""
    t0 = time.perf_counter()
    res = client.post(
        "/api/overlay",
        headers=headers,
        files={"image": ("bench.jpeg", img, "image/jpeg")},
        data={"semitones": "-4", "mode": "replace", "song_name": "perf_bench"},
        timeout=60.0,
    )
    elapsed = _ms(t0)
    assert res.status_code == 200, f"/api/overlay failed: {res.status_code}"
    return elapsed


def bench_cache(client: httpx.Client, headers: dict, img: bytes) -> tuple[float, float]:
    """Benchmark cached vs uncached /api/overlay."""
    payload = {"semitones": "-5", "mode": "above", "song_name": "cache_bench"}

    # Uncached
    t0 = time.perf_counter()
    r1 = client.post(
        "/api/overlay",
        headers=headers,
        files={"image": ("bench.jpeg", img, "image/jpeg")},
        data=payload,
        timeout=60.0,
    )
    first_ms = _ms(t0)
    assert r1.status_code == 200

    # Cached
    t0 = time.perf_counter()
    r2 = client.post(
        "/api/overlay",
        headers=headers,
        files={"image": ("bench.jpeg", img, "image/jpeg")},
        data=payload,
        timeout=60.0,
    )
    second_ms = _ms(t0)
    assert r2.status_code == 200

    return first_ms, second_ms


def main() -> None:
    if not TOKEN:
        print("ERROR: TEST_TOKEN not set")
        print("  export TEST_TOKEN=\"eyJ...\"")
        sys.exit(1)

    if not os.path.exists(IMAGE_PATH):
        print(f"ERROR: Test image not found: {IMAGE_PATH}")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TOKEN}"}
    img = _load_image()
    results: dict[str, str] = {}
    all_pass = True

    with httpx.Client(base_url=API_URL, timeout=30.0) as client:
        print("=" * 60)
        print("Capomatic Performance Benchmarks")
        print("=" * 60)

        # Auth
        auth_ms = bench_auth(client, headers)
        ok = auth_ms < THRESHOLDS["auth_ms"]
        results["Auth (/api/auth/me)"] = f"{auth_ms:.0f}ms (threshold: <{THRESHOLDS['auth_ms']}ms)"
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'}  Auth: {auth_ms:.0f}ms")

        # History
        history_ms = bench_history(client, headers)
        ok = history_ms < THRESHOLDS["history_ms"]
        results["History (/api/jobs/my)"] = f"{history_ms:.0f}ms (threshold: <{THRESHOLDS['history_ms']}ms)"
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'}  History: {history_ms:.0f}ms")

        # Processing
        proc_ms = bench_processing(client, headers, img)
        ok = proc_ms < THRESHOLDS["processing_ms"]
        results["Processing (/api/overlay)"] = f"{proc_ms:.0f}ms (threshold: <{THRESHOLDS['processing_ms']}ms)"
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'}  Processing: {proc_ms:.0f}ms")

        # Cache
        first_ms, second_ms = bench_cache(client, headers, img)
        speedup = first_ms / max(second_ms, 1)
        ok = speedup >= THRESHOLDS["cache_speedup"]
        results["Cache speedup"] = f"{speedup:.1f}x (threshold: >{THRESHOLDS['cache_speedup']}x)"
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'}  Cache: {first_ms:.0f}ms -> {second_ms:.0f}ms ({speedup:.1f}x)")

    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)
    for name, result in results.items():
        print(f"  {name}: {result}")
    print()
    print("OVERALL:", "PASS" if all_pass else "FAIL")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
