"""Issue #7 load protocol: OCR admission control, health isolation, memory.

Sends simultaneous ``/detect`` bursts, polls ``/health`` during each burst,
renders every admitted detection in both modes, optionally fills the
detection cache past its limit, and checks each acceptance criterion.

Example (local server started with the Dockerfile environment)::

    python scripts/load_admission.py --api-url http://127.0.0.1:7860 \\
        --image "fixtures/images/친구야.jpeg" --pid <uvicorn pid> \\
        --evict 21 --report-json tmp/load.json

Exit status is 0 only when every checked criterion passes. Memory can only
be sampled for a local process (``--pid``); for a remote Space record the
platform's memory graph separately.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import threading
import time

import httpx

MAX_ADMITTED_PER_BURST = 2       # backend MAX_OCR_IN_FLIGHT
MAX_REJECT_S = 5.0
EXPECTED_RETRY_AFTER = "5"
MAX_HEALTH_S = 2.0


def _rss_mb(pid: int | None) -> float | None:
    if pid is None:
        return None
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True)
    return int(out.stdout.strip()) / 1024 if out.stdout.strip() else None


def _detect(api: str, image: bytes, name: str, origin: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        resp = httpx.post(
            f"{api}/detect",
            files={"image": (name, image)},
            headers={"Origin": origin},
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        return {"status": None, "error": type(exc).__name__, "elapsed_s": time.perf_counter() - started}
    result = {
        "status": resp.status_code,
        "elapsed_s": round(time.perf_counter() - started, 3),
        "retry_after": resp.headers.get("retry-after"),
    }
    if resp.status_code == 200:
        result["detection_id"] = resp.json()["detection_id"]
    return result


def _render(api: str, detection_id: str, origin: str, timeout: float) -> dict:
    started = time.perf_counter()
    try:
        resp = httpx.post(
            f"{api}/render",
            data={"detection_id": detection_id, "semitones": "2", "mode": "both"},
            headers={"Origin": origin},
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        return {"ok": False, "error": type(exc).__name__}
    body = resp.json() if resp.status_code == 200 else {}
    return {
        "status": resp.status_code,
        "elapsed_s": round(time.perf_counter() - started, 3),
        "ok": resp.status_code == 200
        and bool(body.get("replace_image"))
        and bool(body.get("above_image")),
    }


def _poll_health(api: str, stop: threading.Event, samples: list[dict]) -> None:
    with httpx.Client(timeout=10.0) as client:
        while not stop.is_set():
            started = time.perf_counter()
            try:
                status = client.get(f"{api}/health").status_code
            except httpx.HTTPError as exc:
                status = type(exc).__name__
            samples.append({"status": status, "elapsed_s": round(time.perf_counter() - started, 3)})
            stop.wait(0.5)


def run_burst(api: str, image: bytes, name: str, args) -> dict:
    results: list[dict | None] = [None] * args.concurrency
    barrier = threading.Barrier(args.concurrency)

    def worker(i: int) -> None:
        barrier.wait()
        results[i] = _detect(api, image, name, args.origin, args.timeout)

    health: list[dict] = []
    stop = threading.Event()
    poller = threading.Thread(target=_poll_health, args=(api, stop, health))
    poller.start()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(args.concurrency)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    stop.set()
    poller.join()

    renders = [
        _render(api, r["detection_id"], args.origin, args.timeout)
        for r in results if r and r.get("detection_id")
    ]
    admitted = [r for r in results if r and r["status"] == 200]
    rejected = [r for r in results if r and r["status"] == 429]
    health_times = [s["elapsed_s"] for s in health if s["status"] == 200]
    checks = {
        "admitted_at_most_2": len(admitted) <= MAX_ADMITTED_PER_BURST,
        "excess_rejected_429_fast": all(
            r["elapsed_s"] <= MAX_REJECT_S and r["retry_after"] == EXPECTED_RETRY_AFTER
            for r in rejected
        ) and len(admitted) + len(rejected) == args.concurrency,
        "no_5xx_or_timeout": all(r and r["status"] is not None and r["status"] < 500 for r in results),
        "health_within_2s": bool(health) and len(health_times) == len(health)
        and max(health_times) <= MAX_HEALTH_S,
        "every_admitted_renders_both_modes": all(r["ok"] for r in renders)
        and len(renders) == len(admitted),
    }
    return {
        "detect": results,
        "renders": renders,
        "health": {
            "samples": len(health),
            "max_s": max(health_times, default=None),
            "non_200": [s for s in health if s["status"] != 200],
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--origin", default="http://localhost:3000")
    parser.add_argument("--bursts", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--pid", type=int, help="Local server PID for RSS sampling.")
    parser.add_argument("--evict", type=int, default=0,
                        help="Sequential detections after the bursts to push past the cache limit.")
    parser.add_argument("--report-json")
    args = parser.parse_args()
    api = args.api_url.rstrip("/")
    with open(args.image, "rb") as file:
        image = file.read()
    name = os.path.basename(args.image)

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_url": api,
        "image": name,
        "concurrency": args.concurrency,
        "rss_mb": {"post_warm": _rss_mb(args.pid)},
        "bursts": [],
    }
    for index in range(args.bursts):
        burst = run_burst(api, image, name, args)
        burst["rss_mb_after"] = _rss_mb(args.pid)
        report["bursts"].append(burst)
        print(f"burst {index + 1}: {burst['checks']}", flush=True)

    if args.evict:
        statuses = [_detect(api, image, name, args.origin, args.timeout)["status"]
                    for _ in range(args.evict)]
        report["eviction"] = {"detections": args.evict, "statuses": statuses}
        report["rss_mb"]["after_eviction"] = _rss_mb(args.pid)

    report["pass"] = all(all(b["checks"].values()) for b in report["bursts"]) and all(
        status == 200 for status in report.get("eviction", {}).get("statuses", [])
    )
    if args.report_json:
        with open(args.report_json, "w") as file:
            json.dump(report, file, indent=2)
    print(json.dumps({"pass": report["pass"], "rss_mb": report["rss_mb"]}), flush=True)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
