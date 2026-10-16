"""Observable fallback coverage checks, deliberately not an estimated recall."""
import math

from backend.chords.parser import parse_chord
from backend.ocr.preprocess import detect_staff_systems

REASON = 'chord_only:insufficient_chord_coverage'


def assess(image, items: list[dict]) -> dict:
    """Require confident, spatially distributed chords on every detected system.

    Legitimately sparse arrangements may be withheld. Even a pass cannot prove
    that OCR missed no symbols; calibration against independent pages is required.
    """
    systems = detect_staff_systems(image)
    counts = [0] * len(systems)
    positions = [[] for _ in systems]
    confidences = []
    boxes = set()
    invalid = 0
    for item in items:
        try:
            parse_chord(item['text'])
            confidence = float(item['confidence'])
            x1, y1, x2, y2 = map(float, item['bbox'])
            if not all(math.isfinite(v) for v in (confidence, x1, y1, x2, y2)):
                raise ValueError('nonfinite detection')
            if not (0 <= confidence <= 1 and 0 <= x1 < x2 <= image.width
                    and 0 <= y1 < y2 <= image.height):
                raise ValueError('invalid detection')
        except (KeyError, TypeError, ValueError):
            invalid += 1
            continue
        box = (x1, y1, x2, y2)
        if box in boxes:
            invalid += 1
            continue
        boxes.add(box)
        confidences.append(confidence)
        for i, (top, bottom) in enumerate(systems):
            spacing = max(1, (bottom - top) / 4)
            if top - 10 * spacing <= y2 <= top + spacing:
                counts[i] += 1
                positions[i].append((x1 + x2) / 2)
                break
    low = sum(c < 0.8 for c in confidences)
    spans = [(max(xs) - min(xs)) / image.width if len(xs) >= 2 else 0 for xs in positions]
    accepted = bool(all(span >= 0.20 for span in spans) and counts and all(n >= 2 for n in counts) and not invalid
                    and confidences and min(confidences) >= 0.6
                    and low / len(confidences) <= 0.1)
    return {'accepted': accepted, 'reason': 'chord_only:coverage_supported' if accepted else REASON,
            'systems': len(systems), 'chords_per_system': counts,
            'horizontal_span_ratios': spans, 'detected_chords': len(items), 'invalid_or_duplicate': invalid,
            'low_confidence_chords': low, 'recall_estimate': None}
