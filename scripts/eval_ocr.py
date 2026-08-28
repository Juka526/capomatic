import argparse
import atexit
import json
import os
import statistics
import sys
import time
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "images")
LABELS_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "labels")

COVERAGE_THRESHOLD = 0.70
MAX_AVG_TIME_S = 20.0  # local dependency screen; deployed HF timing is the release gate
MIN_FULL_SUITE_COVERAGE = 0.9806  # Paddle 3.2.2 + PaddleOCR 3.7.0 production baseline
MIN_FULL_SUITE_PRECISION = 0.8890
MAX_API_AVG_TIME_S = 80.0         # 60 s target + 20 s tolerance
MAX_API_STDDEV_TIME_S = 20.0
MIN_API_FIXTURES = 3


def build_runner(engine: str):
    """Return a callable ``(image_path) -> list[dict]`` for the chosen engine."""
    if engine == "paddle":
        from backend.ocr.paddle_ocr import run_ocr_paddle, get_ocr
        from backend.ocr.filter import filter_candidates

        print("Warming up OCR engine (first-run model load)...", flush=True)
        get_ocr()  # initialise singleton before timed evaluation begins
        print("Engine ready.\n", flush=True)

        from backend.ocr.filter import recover_candidates, is_chord_candidate, CONFIDENCE_THRESHOLD, _RESCUE_FLOOR  # noqa: PLC0415

        _meta: dict = {}      # side-channel: crop mode + region info
        _recovery: dict = {}  # side-channel: parse/split recovery counts

        def run_ocr(path: str) -> list[dict]:
            items, meta = run_ocr_paddle(path)
            _meta.clear()
            _meta.update(meta)
            confident = [i for i in items if i["confidence"] > CONFIDENCE_THRESHOLD]
            strict  = [i for i in confident if is_chord_candidate(i["text"])]
            failed  = [i for i in confident if not is_chord_candidate(i["text"])]
            extra, pc, sc = recover_candidates(failed)
            _recovery["parse"] = pc
            _recovery["split"] = sc
            # Chord-syntax rescue for lower-confidence items
            rescued = [
                i for i in items
                if _RESCUE_FLOOR < i["confidence"] <= CONFIDENCE_THRESHOLD
                and is_chord_candidate(i["text"])
            ]
            return strict + extra + rescued

        run_ocr.last_meta     = _meta      # type: ignore[attr-defined]
        run_ocr.last_recovery = _recovery  # type: ignore[attr-defined]
    elif engine == "gpt":
        from backend.ocr.gpt_ocr import run_ocr_gpt_vision  # noqa: PLC0415

        print(f"GPT OCR model: {os.environ.get('OPENAI_OCR_MODEL', 'gpt-5.4-mini')}\n", flush=True)

        _meta: dict = {}

        def run_ocr(path: str) -> list[dict]:
            items, meta = run_ocr_gpt_vision(path)
            _meta.clear()
            _meta.update(meta)
            return items

        run_ocr.last_meta = _meta  # type: ignore[attr-defined]
    elif engine == "paddle-gpt":
        from backend.ocr.paddle_ocr import get_ocr  # noqa: PLC0415
        from backend.ocr.paddle_gpt_hybrid import run_ocr_paddle_gpt_hybrid  # noqa: PLC0415

        print("Warming up PaddleOCR engine (first-run model load)...", flush=True)
        get_ocr()
        print(f"GPT OCR model: {os.environ.get('OPENAI_OCR_MODEL', 'gpt-5.4-mini')}\n", flush=True)

        _meta: dict = {}

        def run_ocr(path: str) -> list[dict]:
            items, meta = run_ocr_paddle_gpt_hybrid(path)
            _meta.clear()
            _meta.update(meta)
            return items

        run_ocr.last_meta = _meta  # type: ignore[attr-defined]
    elif engine == "hybrid":
        from backend.ocr.paddle_ocr import get_ocr  # noqa: PLC0415
        from backend.ocr.hybrid_detect import detect_chords_hybrid  # noqa: PLC0415

        print("Warming up OCR engine (first-run model load)...", flush=True)
        get_ocr()
        print("Engine ready.\n", flush=True)

        _meta: dict = {}
        ai_provider = os.environ.get("AI_PROVIDER", "mock")

        def run_ocr(path: str) -> list[dict]:
            items, meta = detect_chords_hybrid(path, ai_provider=ai_provider)
            _meta.clear()
            _meta.update(meta)
            return items

        run_ocr.last_meta = _meta  # type: ignore[attr-defined]
    else:
        from backend.ocr.stub_ocr import run_ocr_stub

        def run_ocr(path: str) -> list[dict]:
            return run_ocr_stub(path)

    return run_ocr


def build_api_runner(api_url: str, engine: str, timeout_s: float, origin: str):
    """Return a runner that exercises the deployed browser-to-HF API path."""
    import httpx  # already installed with the OCR runtime

    client = httpx.Client(
        base_url=api_url.rstrip("/"),
        headers={"Origin": origin},
        timeout=timeout_s,
    )
    atexit.register(client.close)
    _meta: dict = {}

    def run_ocr(path: str) -> list[dict]:
        media_type = "image/png" if path.lower().endswith(".png") else "image/jpeg"
        with open(path, "rb") as image:
            response = client.post(
                "/detect",
                files={"image": (os.path.basename(path), image, media_type)},
                data={"ocr_engine": engine},
            )
        response.raise_for_status()
        if response.headers.get("access-control-allow-origin") != origin:
            raise RuntimeError(f"API does not allow browser origin {origin}")
        payload = response.json()
        _meta.clear()
        _meta.update(payload.get("meta") or {})
        expected_engine = "paddle-gpt-hybrid" if engine == "paddle-gpt" else "paddle"
        if _meta.get("ocr_engine") != expected_engine:
            raise RuntimeError(
                f"API used {_meta.get('ocr_engine')!r}; expected {expected_engine!r}"
            )
        if engine == "paddle-gpt" and not _meta.get("gpt_used"):
            raise RuntimeError("API reported paddle-gpt without GPT refinement")
        return payload.get("chords") or []

    run_ocr.last_meta = _meta  # type: ignore[attr-defined]
    return run_ocr


def evaluate(image_filename: str, label: dict, run_ocr) -> dict:
    image_path = os.path.join(IMAGES_DIR, image_filename)

    t0 = time.perf_counter()
    detections = run_ocr(image_path)
    ocr_time_s = time.perf_counter() - t0

    total_detected = len(detections)
    detected_unique_list = sorted(set(d["text"] for d in detections))

    expected_unique = label["expected_unique_chords"]
    expected_unique_set = set(expected_unique)

    hit = sorted(set(detected_unique_list) & expected_unique_set)
    miss = sorted(expected_unique_set - set(detected_unique_list))
    extra = sorted(set(detected_unique_list) - expected_unique_set)

    coverage = len(hit) / len(expected_unique_set) if expected_unique_set else 0.0
    unique_precision = len(hit) / len(detected_unique_list) if detected_unique_list else 0.0
    expected_total_min = int(label.get("expected_total_chords_min", 0))
    expected_total_max = int(label.get("expected_total_chords_max", sys.maxsize))

    return {
        "image": image_filename,
        "total_detected": total_detected,
        "unique_detected": len(detected_unique_list),
        "detected_unique_list": detected_unique_list,
        "expected_unique": expected_unique,
        "hit": hit,
        "miss": miss,
        "extra": extra,
        "coverage": coverage,
        "unique_precision": unique_precision,
        "expected_total_min": expected_total_min,
        "expected_total_max": expected_total_max,
        "total_count_ok": expected_total_min <= total_detected <= expected_total_max,
        "ocr_time_s": ocr_time_s,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR fixture evaluation.")
    parser.add_argument(
        "--engine",
        choices=["stub", "paddle", "hybrid", "gpt", "paddle-gpt"],
        default="stub",
        help="OCR engine to use (default: stub)",
    )
    parser.add_argument(
        "--max-fixtures",
        type=int,
        default=None,
        help="Evaluate only the first N labeled fixtures.",
    )
    parser.add_argument(
        "--api-url",
        help="Run through a deployed HF API instead of local OCR, for example https://example.hf.space.",
    )
    parser.add_argument(
        "--origin",
        default="https://capomatic.vercel.app",
        help="Browser Origin header for API mode (default: production Vercel URL).",
    )
    parser.add_argument(
        "--baseline-api-url",
        help="Production HF API used for fixture-by-fixture quality non-regression comparison.",
    )
    parser.add_argument(
        "--request-timeout-s",
        type=float,
        default=240.0,
        help="Per-image API timeout in seconds (default: 240).",
    )
    args = parser.parse_args()
    if args.max_fixtures is not None and args.max_fixtures < 1:
        parser.error("--max-fixtures must be at least 1")
    if args.api_url and args.engine not in {"paddle", "paddle-gpt"}:
        parser.error("--api-url supports --engine paddle or paddle-gpt")
    if args.baseline_api_url and not args.api_url:
        parser.error("--baseline-api-url requires --api-url")
    if args.request_timeout_s <= 0:
        parser.error("--request-timeout-s must be positive")

    run_ocr = (
        build_api_runner(args.api_url, args.engine, args.request_timeout_s, args.origin)
        if args.api_url else build_runner(args.engine)
    )
    baseline_runner = (
        build_api_runner(
            args.baseline_api_url,
            args.engine,
            args.request_timeout_s,
            args.origin,
        )
        if args.baseline_api_url else None
    )
    print(f"Engine: {args.engine}")
    if args.api_url:
        print(f"API: {args.api_url}  (Origin: {args.origin})")
    print()

    # Drive evaluation by labels, not by image filenames.
    label_files = sorted(f for f in os.listdir(LABELS_DIR) if f.endswith(".json"))
    if not label_files:
        print("No label files found in fixtures/labels/. Add .json labels to run evaluation.")
        sys.exit(0)

    # Index images present on disk.
    # macOS HFS+ stores filenames in NFD; label JSON is typically NFC.
    # Build a NFC-key → actual-disk-name map so lookup is form-agnostic.
    nfc = unicodedata.normalize
    disk_files = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    disk_map = {nfc("NFC", f): f for f in disk_files}  # NFC key → real filename
    labeled_nfc: set = set()

    selected_label_files = label_files[:args.max_fixtures]
    is_full_suite = len(selected_label_files) == len(label_files)

    if args.api_url:
        warmup_path = None
        for label_file in selected_label_files:
            with open(os.path.join(LABELS_DIR, label_file)) as f:
                warmup_label = json.load(f)
            warmup_name = disk_map.get(nfc("NFC", warmup_label["image"]))
            if warmup_name:
                warmup_path = os.path.join(IMAGES_DIR, warmup_name)
                break
        if warmup_path:
            for name, runner in (("candidate", run_ocr), ("baseline", baseline_runner)):
                if runner is None:
                    continue
                t0 = time.perf_counter()
                runner(warmup_path)
                print(
                    f"Pre-gate {name} warm-up: {time.perf_counter() - t0:.2f} s "
                    "(record as cold only immediately after a Space restart)"
                )
            print()

    results: list = []
    baseline_results: list = []
    any_fixture_fail = False
    any_quality_regression = False

    for label_file in selected_label_files:
        label_path = os.path.join(LABELS_DIR, label_file)
        with open(label_path) as f:
            label = json.load(f)

        img_label = label["image"]                 # as written in JSON
        img_nfc   = nfc("NFC", img_label)          # normalised for lookup
        labeled_nfc.add(img_nfc)

        if img_nfc not in disk_map:
            print(f"[ERROR] {img_label} — listed in {label_file} but not found in fixtures/images/")
            any_fixture_fail = True
            print("-" * 50)
            continue

        img = disk_map[img_nfc]                    # actual filename on disk
        baseline = evaluate(img, label, baseline_runner) if baseline_runner else None
        if baseline:
            baseline_results.append(baseline)
        r = evaluate(img, label, run_ocr)
        results.append(r)

        coverage_ok = r["coverage"] >= COVERAGE_THRESHOLD
        fixture_ok = coverage_ok and r["total_count_ok"]
        if not fixture_ok:
            any_fixture_fail = True
        regression = bool(
            baseline
            and (
                r["coverage"] < baseline["coverage"]
                or r["unique_precision"] < baseline["unique_precision"]
            )
        )
        any_quality_regression = any_quality_regression or regression
        status = "PASS" if fixture_ok and not regression else "FAIL"

        print(f"Image            : {r['image']}")
        print(f"Total detected   : {r['total_detected']}")
        print(f"Unique detected  : {r['unique_detected']}  {r['detected_unique_list']}")
        print(f"Expected unique  : {r['expected_unique']}")
        print(f"Hit              : {r['hit']}")
        print(f"Miss             : {r['miss']}")
        print(f"Extra            : {r['extra']}")
        print(f"Coverage         : {r['coverage']:.2%}  ({len(r['hit'])}/{len(r['expected_unique'])})")
        print(f"Unique precision : {r['unique_precision']:.2%}")
        print(
            f"Expected total    : {r['expected_total_min']}–{r['expected_total_max']} "
            f"({'PASS' if r['total_count_ok'] else 'FAIL'})"
        )
        if baseline:
            print(
                f"Production quality: coverage {baseline['coverage']:.2%}, "
                f"precision {baseline['unique_precision']:.2%} "
                f"({'REGRESSION' if regression else 'PASS'})"
            )
        print(f"OCR time         : {r['ocr_time_s'] * 1000:.1f} ms")
        print(f"Status           : {status}")
        if hasattr(run_ocr, "last_meta") and run_ocr.last_meta:
            m = run_ocr.last_meta
            print(f"Crop mode        : {m.get('crop_mode', '?')}")
            print(f"Regions          : {m.get('num_regions', '?')}")
            print(f"Stitched         : {m.get('stitched', '?')}  (predict calls: {m.get('predict_calls', '?')})")
            if m.get("predict_ms") is not None:
                print(f"Predict time     : {m['predict_ms']:.1f} ms")
                r["predict_ms"] = m["predict_ms"]
            if m.get("input_tokens") is not None:
                print(f"Input tokens     : {m['input_tokens']}")
                r["input_tokens"] = m["input_tokens"]
            if m.get("sent_image_width") and m.get("sent_image_height"):
                print(f"Sent image       : {m['sent_image_width']}×{m['sent_image_height']}"
                      f"  (max_side={m.get('max_side')})")
            if m.get("stitched_shape"):
                H, W = m["stitched_shape"]
                print(f"Stitched shape   : {H}×{W}  ({m['stitched_pixels']:,} px)")
            if m.get("resize_applied"):
                print(f"Resize           : scale={m['resize_scale']:.3f}"
                      f"  → {m['resized_shape'][0]}×{m['resized_shape'][1]}")
        if hasattr(run_ocr, "last_recovery") and run_ocr.last_recovery:
            rec = run_ocr.last_recovery
            print(f"Recovered        : parse={rec.get('parse', 0)} split={rec.get('split', 0)}")
        if hasattr(run_ocr, "last_meta") and run_ocr.last_meta.get("gate"):
            g = run_ocr.last_meta["gate"]
            gate_str = "PASS" if g["pass"] else f"FAIL – {'; '.join(g['reasons'])}"
            print(f"Gate             : {gate_str}  (score={g['score']:.3f})")
            print(f"AI used          : {run_ocr.last_meta.get('ai_used', False)}"
                  + (f"  (provider={run_ocr.last_meta['ai_provider']})"
                     if run_ocr.last_meta.get("ai_used") else ""))
        print("-" * 50)

    # Warn about images present on disk that have no label.
    if args.max_fixtures is None:
        unlabeled = sorted(f for nfc_f, f in disk_map.items() if nfc_f not in labeled_nfc)
        for img in unlabeled:
            print(f"[WARN]  {img} — image present but has no label (skipped)")
        if unlabeled:
            print()

    if not results and not any_fixture_fail:
        print("No fixtures evaluated. Add images + labels to fixtures/ to run evaluation.")
        sys.exit(0)

    avg_coverage = sum(r["coverage"] for r in results) / len(results) if results else 0.0
    avg_unique_precision = (
        sum(r["unique_precision"] for r in results) / len(results) if results else 0.0
    )
    times_s      = [r["ocr_time_s"] for r in results]
    avg_time_s   = sum(times_s) / len(times_s) if times_s else 0.0
    median_time_s = statistics.median(times_s) if times_s else 0.0
    max_avg_time_s = MAX_API_AVG_TIME_S if args.api_url else MAX_AVG_TIME_S
    time_stddev_s = statistics.pstdev(times_s) if len(times_s) > 1 else 0.0
    time_ok = avg_time_s <= max_avg_time_s
    variability_ok = (
        not args.api_url
        or (len(results) >= MIN_API_FIXTURES and time_stddev_s <= MAX_API_STDDEV_TIME_S)
    )
    full_suite_coverage_ok = not is_full_suite or avg_coverage >= MIN_FULL_SUITE_COVERAGE
    full_suite_precision_ok = not is_full_suite or avg_unique_precision >= MIN_FULL_SUITE_PRECISION

    print(f"\nSUMMARY")
    print(f"Engine             : {args.engine}")
    print(f"Fixtures evaluated : {len(results)}")
    print(f"Avg coverage       : {avg_coverage:.2%}")
    print(f"Avg unique precision: {avg_unique_precision:.2%}")
    print(f"Avg OCR time       : {avg_time_s * 1000:.1f} ms  (limit: {int(max_avg_time_s * 1000)} ms)")
    print(f"Median OCR time    : {median_time_s * 1000:.1f} ms")
    if args.api_url:
        print(f"Time stddev        : {time_stddev_s * 1000:.1f} ms  (limit: {int(MAX_API_STDDEV_TIME_S * 1000)} ms)")
    if baseline_results:
        baseline_times = [r["ocr_time_s"] for r in baseline_results]
        print(f"Production avg time: {statistics.mean(baseline_times) * 1000:.1f} ms")
        print(f"Production stddev  : {statistics.pstdev(baseline_times) * 1000:.1f} ms")
    predict_ms_list = [r["predict_ms"] for r in results if "predict_ms" in r]
    if predict_ms_list:
        print(f"Avg predict time   : {sum(predict_ms_list) / len(predict_ms_list):.1f} ms")
        print(f"Median predict time: {statistics.median(predict_ms_list):.1f} ms")
    input_tokens_list = [r["input_tokens"] for r in results if "input_tokens" in r]
    if input_tokens_list:
        print(f"Avg input tokens   : {sum(input_tokens_list) / len(input_tokens_list):.1f}")
        print(f"Median input tokens: {statistics.median(input_tokens_list):.1f}")

    if any_fixture_fail:
        print("\nFAIL: one or more fixtures is below 0.70 coverage or outside its expected total range.")
    if any_quality_regression:
        print("\nFAIL: candidate quality regressed against production on one or more fixtures.")
    if not full_suite_coverage_ok:
        print(f"\nFAIL: full-suite coverage {avg_coverage:.2%} is below the {MIN_FULL_SUITE_COVERAGE:.2%} production baseline.")
    if not full_suite_precision_ok:
        print(f"\nFAIL: full-suite unique precision {avg_unique_precision:.2%} is below the {MIN_FULL_SUITE_PRECISION:.2%} production baseline.")
    if not time_ok:
        print(f"\nFAIL: avg OCR time {avg_time_s:.2f}s exceeds {max_avg_time_s}s limit.")
    if not variability_ok:
        if len(results) < MIN_API_FIXTURES:
            print(f"\nFAIL: API timing needs at least {MIN_API_FIXTURES} fixtures; got {len(results)}.")
        else:
            print(f"\nFAIL: API time stddev {time_stddev_s:.2f}s exceeds {MAX_API_STDDEV_TIME_S}s limit.")

    if (
        any_fixture_fail
        or any_quality_regression
        or not full_suite_coverage_ok
        or not full_suite_precision_ok
        or not time_ok
        or not variability_ok
    ):
        sys.exit(1)

    print("\nAll fixtures passed.")


if __name__ == "__main__":
    main()
