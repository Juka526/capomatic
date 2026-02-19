import argparse
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
MAX_AVG_TIME_S = 15.0  # CPU-only inference (Apple Silicon M-series): ~8-10 s/image


def build_runner(engine: str):
    """Return a callable ``(image_path) -> list[dict]`` for the chosen engine."""
    if engine == "paddle":
        from backend.ocr.paddle_ocr import run_ocr_paddle, get_ocr
        from backend.ocr.filter import filter_candidates

        print("Warming up OCR engine (first-run model load)...", flush=True)
        get_ocr()  # initialise singleton before timed evaluation begins
        print("Engine ready.\n", flush=True)

        from backend.ocr.filter import recover_candidates, is_chord_candidate  # noqa: PLC0415

        _meta: dict = {}      # side-channel: crop mode + region info
        _recovery: dict = {}  # side-channel: parse/split recovery counts

        def run_ocr(path: str) -> list[dict]:
            items, meta = run_ocr_paddle(path)
            _meta.clear()
            _meta.update(meta)
            strict  = [i for i in items if is_chord_candidate(i["text"])]
            failed  = [i for i in items if not is_chord_candidate(i["text"])]
            extra, pc, sc = recover_candidates(failed)
            _recovery["parse"] = pc
            _recovery["split"] = sc
            return strict + extra

        run_ocr.last_meta     = _meta      # type: ignore[attr-defined]
        run_ocr.last_recovery = _recovery  # type: ignore[attr-defined]
    else:
        from backend.ocr.stub_ocr import run_ocr_stub

        def run_ocr(path: str) -> list[dict]:
            return run_ocr_stub(path)

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

    coverage = len(hit) / len(expected_unique_set) if expected_unique_set else 0.0

    return {
        "image": image_filename,
        "total_detected": total_detected,
        "unique_detected": len(detected_unique_list),
        "detected_unique_list": detected_unique_list,
        "expected_unique": expected_unique,
        "hit": hit,
        "miss": miss,
        "coverage": coverage,
        "ocr_time_s": ocr_time_s,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR fixture evaluation.")
    parser.add_argument(
        "--engine",
        choices=["stub", "paddle"],
        default="stub",
        help="OCR engine to use (default: stub)",
    )
    args = parser.parse_args()

    run_ocr = build_runner(args.engine)
    print(f"Engine: {args.engine}\n")

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

    results: list = []
    any_coverage_fail = False

    for label_file in label_files:
        label_path = os.path.join(LABELS_DIR, label_file)
        with open(label_path) as f:
            label = json.load(f)

        img_label = label["image"]                 # as written in JSON
        img_nfc   = nfc("NFC", img_label)          # normalised for lookup
        labeled_nfc.add(img_nfc)

        if img_nfc not in disk_map:
            print(f"[ERROR] {img_label} — listed in {label_file} but not found in fixtures/images/")
            any_coverage_fail = True
            print("-" * 50)
            continue

        img = disk_map[img_nfc]                    # actual filename on disk
        r = evaluate(img, label, run_ocr)
        results.append(r)

        coverage_ok = r["coverage"] >= COVERAGE_THRESHOLD
        if not coverage_ok:
            any_coverage_fail = True
        status = "PASS" if coverage_ok else "FAIL"

        print(f"Image            : {r['image']}")
        print(f"Total detected   : {r['total_detected']}")
        print(f"Unique detected  : {r['unique_detected']}  {r['detected_unique_list']}")
        print(f"Expected unique  : {r['expected_unique']}")
        print(f"Hit              : {r['hit']}")
        print(f"Miss             : {r['miss']}")
        print(f"Coverage         : {r['coverage']:.2%}  ({len(r['hit'])}/{len(r['expected_unique'])})")
        print(f"OCR time         : {r['ocr_time_s'] * 1000:.1f} ms")
        print(f"Status           : {status}")
        if hasattr(run_ocr, "last_meta") and run_ocr.last_meta:
            m = run_ocr.last_meta
            print(f"Crop mode        : {m.get('crop_mode', '?')}")
            print(f"Regions          : {m.get('num_regions', '?')}")
            print(f"Stitched         : {m.get('stitched', '?')}  (predict calls: {m.get('predict_calls', '?')})")
        if hasattr(run_ocr, "last_recovery") and run_ocr.last_recovery:
            rec = run_ocr.last_recovery
            print(f"Recovered        : parse={rec.get('parse', 0)} split={rec.get('split', 0)}")
        print("-" * 50)

    # Warn about images present on disk that have no label.
    unlabeled = sorted(f for nfc_f, f in disk_map.items() if nfc_f not in labeled_nfc)
    for img in unlabeled:
        print(f"[WARN]  {img} — image present but has no label (skipped)")
    if unlabeled:
        print()

    if not results and not any_coverage_fail:
        print("No fixtures evaluated. Add images + labels to fixtures/ to run evaluation.")
        sys.exit(0)

    avg_coverage = sum(r["coverage"] for r in results) / len(results) if results else 0.0
    times_s      = [r["ocr_time_s"] for r in results]
    avg_time_s   = sum(times_s) / len(times_s) if times_s else 0.0
    median_time_s = statistics.median(times_s) if times_s else 0.0
    time_ok = avg_time_s <= MAX_AVG_TIME_S

    print(f"\nSUMMARY")
    print(f"Engine             : {args.engine}")
    print(f"Fixtures evaluated : {len(results)}")
    print(f"Avg coverage       : {avg_coverage:.2%}")
    print(f"Avg OCR time       : {avg_time_s * 1000:.1f} ms  (limit: {int(MAX_AVG_TIME_S * 1000)} ms)")
    print(f"Median OCR time    : {median_time_s * 1000:.1f} ms")

    if any_coverage_fail:
        print("\nFAIL: one or more fixtures below 0.70 coverage threshold.")
    if not time_ok:
        print(f"\nFAIL: avg OCR time {avg_time_s:.2f}s exceeds {MAX_AVG_TIME_S}s limit.")

    if any_coverage_fail or not time_ok:
        sys.exit(1)

    print("\nAll fixtures passed.")


if __name__ == "__main__":
    main()
