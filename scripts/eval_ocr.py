import argparse
import atexit
from collections import Counter
from datetime import datetime, timezone
import hashlib
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
        _meta["detection_id"] = payload.get("detection_id")
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


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate(image_filename: str, label: dict, run_ocr, *, label_file: str | None = None) -> dict:
    image_path = (
        image_filename
        if os.path.isabs(image_filename) or os.path.isfile(image_filename)
        else os.path.join(IMAGES_DIR, image_filename)
    )

    image_sha256 = _sha256_file(image_path)
    t0 = time.perf_counter()
    detections = run_ocr(image_path)
    ocr_time_s = time.perf_counter() - t0

    detected_texts = [d["text"] for d in detections]
    total_detected = len(detected_texts)
    detected_unique_list = sorted(set(detected_texts))

    expected_unique = label["expected_unique_chords"]
    expected_unique_set = set(expected_unique)

    hit = sorted(set(detected_unique_list) & expected_unique_set)
    miss = sorted(expected_unique_set - set(detected_unique_list))
    extra = sorted(set(detected_unique_list) - expected_unique_set)

    coverage = len(hit) / len(expected_unique_set) if expected_unique_set else 0.0
    unique_precision = len(hit) / len(detected_unique_list) if detected_unique_list else 0.0
    expected_total_min = int(label.get("expected_total_chords_min", 0))
    expected_total_max = int(label.get("expected_total_chords_max", sys.maxsize))
    expected_sequence = label.get("expected_chord_sequence")
    occurrence_coverage = None
    occurrence_precision = None
    occurrence_exact = None
    if expected_sequence is not None:
        expected_counts = Counter(expected_sequence)
        detected_counts = Counter(detected_texts)
        occurrence_hits = sum((expected_counts & detected_counts).values())
        occurrence_coverage = occurrence_hits / len(expected_sequence) if expected_sequence else 0.0
        occurrence_precision = occurrence_hits / total_detected if total_detected else 0.0
        occurrence_exact = detected_counts == expected_counts
    hard_targets = label.get("hard_targets") or []
    missing_hard_targets = sorted(set(hard_targets) - set(detected_unique_list))

    return {
        "image": label.get("image", os.path.basename(image_path)),
        "image_sha256": image_sha256,
        "label_file": label_file,
        "total_detected": total_detected,
        "detected_chord_sequence": detected_texts,
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
        "expected_chord_sequence": expected_sequence,
        "occurrence_coverage": occurrence_coverage,
        "occurrence_precision": occurrence_precision,
        "occurrence_exact": occurrence_exact,
        "hard_targets": hard_targets,
        "missing_hard_targets": missing_hard_targets,
        "strict_unseen": bool(label.get("strict_unseen")),
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
        "--label",
        action="append",
        help="Evaluate only this label name or JSON path; repeat to select multiple labels.",
    )
    parser.add_argument(
        "--extra-label",
        action="append",
        default=[],
        help="Add an external JSON label to the normal fixture set; repeat as needed.",
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
        "--baseline-report",
        help="Previously saved JSON report used for sequential quality comparison.",
    )
    parser.add_argument(
        "--report-json",
        help="Write a machine-readable report even when a quality or timing gate fails.",
    )
    parser.add_argument(
        "--deployment-sha",
        help="Exact deployed Git/HF SHA recorded in --report-json.",
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
    if args.label and args.max_fixtures is not None:
        parser.error("--label and --max-fixtures cannot be combined")
    if args.api_url and args.engine not in {"paddle", "paddle-gpt"}:
        parser.error("--api-url supports --engine paddle or paddle-gpt")
    if args.baseline_api_url and not args.api_url:
        parser.error("--baseline-api-url requires --api-url")
    if args.baseline_report and not args.api_url:
        parser.error("--baseline-report requires --api-url")
    if args.baseline_api_url and args.baseline_report:
        parser.error("use only one of --baseline-api-url or --baseline-report")
    if args.report_json and args.api_url and not args.deployment_sha:
        parser.error("API reports require --deployment-sha")
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
    baseline_report = None
    baseline_by_sha: dict[str, dict] = {}
    if args.baseline_report:
        with open(args.baseline_report) as file:
            baseline_report = json.load(file)
        if baseline_report.get("schema_version") != 1:
            parser.error("--baseline-report schema_version must be 1")
        if baseline_report.get("engine") != args.engine:
            parser.error("--baseline-report engine does not match --engine")
        baseline_rows = baseline_report.get("results", [])
        if any(not result.get("image_sha256") for result in baseline_rows):
            parser.error("--baseline-report contains a result without image_sha256")
        baseline_by_sha = {
            result["image_sha256"]: result
            for result in baseline_rows
        }
        if len(baseline_by_sha) != len(baseline_rows):
            parser.error("--baseline-report contains duplicate image_sha256 values")
    print(f"Engine: {args.engine}")
    if args.api_url:
        print(f"API: {args.api_url}  (Origin: {args.origin})")
    print()

    # Drive evaluation by labels, not by image filenames.
    canonical_label_paths = sorted(
        os.path.abspath(os.path.join(LABELS_DIR, filename))
        for filename in os.listdir(LABELS_DIR)
        if filename.endswith(".json")
    )
    if not canonical_label_paths:
        print("No label files found in fixtures/labels/. Add .json labels to run evaluation.")
        sys.exit(0)

    def resolve_label_path(value: str) -> str:
        candidates = [value]
        name = value if value.endswith(".json") else f"{value}.json"
        candidates.append(os.path.join(LABELS_DIR, name))
        for candidate in candidates:
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
        parser.error(f"label not found: {value}")
        raise AssertionError("unreachable")

    if args.label:
        selected_label_paths = [resolve_label_path(value) for value in args.label]
    else:
        selected_label_paths = canonical_label_paths[:args.max_fixtures]
    selected_label_paths.extend(resolve_label_path(value) for value in args.extra_label)
    selected_label_paths = list(dict.fromkeys(selected_label_paths))
    is_full_suite = set(canonical_label_paths).issubset(selected_label_paths)

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
    cases: list[tuple[str, dict, str]] = []
    missing_labels: list[str] = []
    canonical_set = set(canonical_label_paths)
    for label_path in selected_label_paths:
        with open(label_path) as file:
            label = json.load(file)
        image_name = label["image"]
        if label_path in canonical_set:
            image_nfc = nfc("NFC", image_name)
            labeled_nfc.add(image_nfc)
            disk_name = disk_map.get(image_nfc)
            image_path = os.path.join(IMAGES_DIR, disk_name) if disk_name else ""
        else:
            image_path = (
                image_name
                if os.path.isabs(image_name)
                else os.path.join(os.path.dirname(label_path), image_name)
            )
        if not image_path or not os.path.isfile(image_path):
            missing_labels.append(label_path)
            print(f"[ERROR] {image_name} — listed in {label_path} but not found")
            continue
        cases.append((label_path, label, image_path))

    if args.api_url:
        warmup_path = cases[0][2] if cases else None
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
    any_fixture_fail = bool(missing_labels)
    any_quality_regression = False

    report_meta_keys = {
        "ocr_engine",
        "crop_mode",
        "num_regions",
        "stitched",
        "predict_calls",
        "predict_ms",
        "total_ms",
        "service_ms",
        "gpt_used",
        "gpt_crop_ms",
        "gpt_gap_ms",
        "high_recall_predict_ms",
        "parallel_refinement",
        "input_tokens",
        "output_tokens",
        "detection_id",
        "sent_image_width",
        "sent_image_height",
        "max_side",
        "stitched_shape",
        "stitched_pixels",
        "resize_applied",
        "resize_scale",
        "resized_shape",
    }

    def truth_signature(result: dict) -> tuple:
        return (
            frozenset(result.get("expected_unique") or []),
            result.get("expected_total_min"),
            result.get("expected_total_max"),
            tuple(result.get("expected_chord_sequence") or []),
            frozenset(result.get("hard_targets") or []),
            bool(result.get("strict_unseen")),
        )

    for label_path, label, image_path in cases:
        baseline = (
            evaluate(image_path, label, baseline_runner, label_file=label_path)
            if baseline_runner else None
        )
        r = evaluate(image_path, label, run_ocr, label_file=label_path)
        if hasattr(run_ocr, "last_meta"):
            r["meta"] = {
                key: value
                for key, value in run_ocr.last_meta.items()
                if key in report_meta_keys
            }
            for key in ("predict_ms", "input_tokens"):
                if r["meta"].get(key) is not None:
                    r[key] = r["meta"][key]

        if baseline_report is not None:
            baseline = baseline_by_sha.get(r["image_sha256"])
            if baseline is None:
                print(f"[ERROR] {r['image']} — image SHA is absent from baseline report")
                any_quality_regression = True
            elif truth_signature(r) != truth_signature(baseline):
                print(f"[ERROR] {r['image']} — expected truth differs from baseline report")
                any_quality_regression = True
                baseline = None
        if baseline:
            baseline_results.append(baseline)
        results.append(r)

        coverage_ok = r["coverage"] >= COVERAGE_THRESHOLD
        strict_ok = not r["strict_unseen"] or (
            r["coverage"] == 1.0
            and r["unique_precision"] == 1.0
            and r["occurrence_exact"] is True
            and r["total_count_ok"]
            and not r["missing_hard_targets"]
        )
        fixture_ok = coverage_ok and r["total_count_ok"] and strict_ok
        if not fixture_ok:
            any_fixture_fail = True
        regression = bool(
            baseline
            and (
                r["coverage"] < baseline["coverage"]
                or r["unique_precision"] < baseline["unique_precision"]
                or (
                    r["expected_chord_sequence"] is not None
                    and (
                        baseline.get("occurrence_coverage") is None
                        or baseline.get("occurrence_precision") is None
                        or r["occurrence_coverage"] < baseline["occurrence_coverage"]
                        or r["occurrence_precision"] < baseline["occurrence_precision"]
                    )
                )
            )
        )
        any_quality_regression = any_quality_regression or regression
        status = "PASS" if fixture_ok and not regression else "FAIL"
        r["fixture_pass"] = fixture_ok
        r["quality_regression"] = regression

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
        if r["expected_chord_sequence"] is not None:
            print(
                f"Occurrence match : coverage {r['occurrence_coverage']:.2%}, "
                f"precision {r['occurrence_precision']:.2%}, "
                f"exact {'PASS' if r['occurrence_exact'] else 'FAIL'}"
            )
        if r["hard_targets"]:
            print(
                f"Hard targets     : "
                f"{'PASS' if not r['missing_hard_targets'] else 'FAIL ' + str(r['missing_hard_targets'])}"
            )
        if baseline:
            print(
                f"Production quality: coverage {baseline['coverage']:.2%}, "
                f"precision {baseline['unique_precision']:.2%} "
                f"({'REGRESSION' if regression else 'PASS'})"
            )
        print(f"OCR time         : {r['ocr_time_s'] * 1000:.1f} ms")
        print(f"Status           : {status}")
        if r.get("meta"):
            m = r["meta"]
            print(f"Crop mode        : {m.get('crop_mode', '?')}")
            print(f"Regions          : {m.get('num_regions', '?')}")
            print(f"Stitched         : {m.get('stitched', '?')}  (predict calls: {m.get('predict_calls', '?')})")
            if m.get("predict_ms") is not None:
                print(f"Predict time     : {m['predict_ms']:.1f} ms")
            if m.get("input_tokens") is not None:
                print(f"Input tokens     : {m['input_tokens']}")
            if m.get("sent_image_width") and m.get("sent_image_height"):
                print(
                    f"Sent image       : {m['sent_image_width']}×{m['sent_image_height']}"
                    f"  (max_side={m.get('max_side')})"
                )
            if m.get("stitched_shape"):
                height, width = m["stitched_shape"]
                print(
                    f"Stitched shape   : {height}×{width}  "
                    f"({m['stitched_pixels']:,} px)"
                )
            if m.get("resize_applied"):
                print(
                    f"Resize           : scale={m['resize_scale']:.3f}"
                    f"  → {m['resized_shape'][0]}×{m['resized_shape'][1]}"
                )
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

    if baseline_report is not None:
        current_hashes = {result["image_sha256"] for result in results}
        if current_hashes != set(baseline_by_sha):
            print("[ERROR] Candidate and baseline reports contain different image sets")
            any_quality_regression = True

    # Warn about images present on disk that have no label.
    if not args.label and args.max_fixtures is None:
        unlabeled = sorted(f for nfc_f, f in disk_map.items() if nfc_f not in labeled_nfc)
        for img in unlabeled:
            print(f"[WARN]  {img} — image present but has no label (skipped)")
        if unlabeled:
            print()

    if not results and not any_fixture_fail:
        print("No fixtures evaluated. Add images + labels to fixtures/ to run evaluation.")
        sys.exit(0)

    quality_results = [r for r in results if not r["strict_unseen"]] or results
    avg_coverage = (
        sum(r["coverage"] for r in quality_results) / len(quality_results)
        if quality_results else 0.0
    )
    avg_unique_precision = (
        sum(r["unique_precision"] for r in quality_results) / len(quality_results)
        if quality_results else 0.0
    )
    times_s = [r["ocr_time_s"] for r in results]
    avg_time_s = sum(times_s) / len(times_s) if times_s else 0.0
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
        print(
            f"Production stddev  : "
            f"{statistics.pstdev(baseline_times) * 1000:.1f} ms"
        )
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

    failure_reasons = []
    if any_fixture_fail:
        failure_reasons.append("fixture_quality")
    if any_quality_regression:
        failure_reasons.append("quality_regression")
    if not full_suite_coverage_ok:
        failure_reasons.append("full_suite_coverage")
    if not full_suite_precision_ok:
        failure_reasons.append("full_suite_precision")
    if not time_ok:
        failure_reasons.append("average_time")
    if not variability_ok:
        failure_reasons.append("time_variability")
    gate_failed = bool(failure_reasons)
    summary = {
        "passed": not gate_failed,
        "failure_reasons": failure_reasons,
        "fixtures_evaluated": len(results),
        "quality_fixtures": len(quality_results),
        "avg_coverage": avg_coverage,
        "avg_unique_precision": avg_unique_precision,
        "avg_time_s": avg_time_s,
        "median_time_s": median_time_s,
        "time_stddev_s": time_stddev_s,
    }
    if args.report_json:
        report = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine": args.engine,
            "api_url": args.api_url,
            "origin": args.origin if args.api_url else None,
            "deployment_sha": args.deployment_sha,
            "baseline_deployment_sha": (
                baseline_report.get("deployment_sha") if baseline_report else None
            ),
            "results": results,
            "summary": summary,
            "gate": {
                "pass": not gate_failed,
                "fixture_quality": not any_fixture_fail,
                "no_quality_regression": not any_quality_regression,
                "full_suite_coverage": full_suite_coverage_ok,
                "full_suite_precision": full_suite_precision_ok,
                "average_time": time_ok,
                "time_variability": variability_ok,
            },
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.report_json)), exist_ok=True)
        with open(args.report_json, "w") as file:
            json.dump(report, file, ensure_ascii=False, indent=2)
            file.write("\n")
        print(f"\nReport written     : {args.report_json}")

    if gate_failed:
        sys.exit(1)

    print("\nAll fixtures passed.")


if __name__ == "__main__":
    main()
