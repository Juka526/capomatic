import json
import os
import sys
import time
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.ocr.stub_ocr import run_ocr_stub

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "images")
LABELS_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "labels")

COVERAGE_THRESHOLD = 0.70
MAX_AVG_TIME_S = 5.0



def evaluate(image_filename: str, label: dict) -> dict:
    image_path = os.path.join(IMAGES_DIR, image_filename)

    t0 = time.perf_counter()
    detections = run_ocr_stub(image_path)
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


def main():
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
    labeled_nfc = set()

    results = []
    any_coverage_fail = False

    for label_file in label_files:
        label_path = os.path.join(LABELS_DIR, label_file)
        with open(label_path) as f:
            label = json.load(f)

        img_label = label["image"]                     # as written in JSON
        img_nfc   = nfc("NFC", img_label)             # normalised for lookup
        labeled_nfc.add(img_nfc)

        if img_nfc not in disk_map:
            print(f"[ERROR] {img_label} — listed in {label_file} but not found in fixtures/images/")
            any_coverage_fail = True
            print("-" * 50)
            continue

        img = disk_map[img_nfc]                        # actual filename on disk
        r = evaluate(img, label)
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
    avg_time_s = sum(r["ocr_time_s"] for r in results) / len(results) if results else 0.0
    time_ok = avg_time_s <= MAX_AVG_TIME_S

    print(f"\nSUMMARY")
    print(f"Fixtures evaluated : {len(results)}")
    print(f"Avg coverage       : {avg_coverage:.2%}")
    print(f"Avg OCR time       : {avg_time_s * 1000:.1f} ms  (limit: {int(MAX_AVG_TIME_S * 1000)} ms)")

    if any_coverage_fail:
        print("\nFAIL: one or more fixtures below 0.70 coverage threshold.")
    if not time_ok:
        print(f"\nFAIL: avg OCR time {avg_time_s:.2f}s exceeds {MAX_AVG_TIME_S}s limit.")

    if any_coverage_fail or not time_ok:
        sys.exit(1)

    print("\nAll fixtures passed.")


if __name__ == "__main__":
    main()