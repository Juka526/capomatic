"""Observable fallback coverage checks, deliberately not an estimated recall."""
import math

from backend.chords.parser import parse_chord
from backend.ocr.preprocess import detect_staff_systems

REASON = 'chord_only:insufficient_chord_coverage'


def _staff_regions(image) -> list[tuple[int, int]]:
    """Cross-check full-width detection using staff fragments in narrow strips.

    Skew/perspective can erase long horizontal runs while leaving short ones.
    Require support in half the strips so isolated text/noise is not a system.
    """
    observations = []
    for strip in range(6):
        left = image.width * (0.1 + 0.8 * strip / 6)
        right = image.width * (0.1 + 0.8 * (strip + 1) / 6)
        crop = image.crop((int(left), 0, int(right), image.height))
        observations.extend((top, bottom, strip) for top, bottom in detect_staff_systems(crop))
    regions = []
    for top, bottom, strip in sorted(observations):
        if regions and top <= regions[-1][1]:
            previous_top, previous_bottom, support = regions[-1]
            regions[-1] = (previous_top, max(previous_bottom, bottom), support | {strip})
        else:
            regions.append((top, bottom, {strip}))
    return [(top, bottom) for top, bottom, support in regions if len(support) >= 3]


def _overlaps(a, b) -> bool:
    return min(a[1], b[1]) > max(a[0], b[0])


def assess(image, items: list[dict]) -> dict:
    """Require confident, spatially distributed chords on every detected system.

    Legitimately sparse arrangements may be withheld. Even a pass cannot prove
    that OCR missed no symbols; calibration against independent pages is required.
    """
    systems = detect_staff_systems(image)
    regions = _staff_regions(image)
    uncovered = [region for region in regions if not any(_overlaps(region, s) for s in systems)]
    unsupported = [s for s in systems if not any(_overlaps(s, region) for region in regions)]
    staff_coverage_supported = bool(regions and not uncovered and not unsupported)
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
        else:
            invalid += 1
    low = sum(c < 0.8 for c in confidences)
    spans = [(max(xs) - min(xs)) / image.width if len(xs) >= 2 else 0 for xs in positions]
    accepted = bool(staff_coverage_supported and counts and not invalid
                    and all(span >= 0.20 for span in spans)
                    and all(n >= 2 for n in counts)
                    and confidences and min(confidences) >= 0.6
                    and low / len(confidences) <= 0.1)
    return {'accepted': accepted, 'reason': 'chord_only:coverage_supported' if accepted else REASON,
            'systems': len(systems), 'chords_per_system': counts,
            'staff_regions': len(regions), 'uncovered_staff_regions': len(uncovered),
            'unsupported_systems': len(unsupported),
            'horizontal_span_ratios': spans, 'detected_chords': len(items), 'invalid_or_duplicate': invalid,
            'low_confidence_chords': low, 'recall_estimate': None}
