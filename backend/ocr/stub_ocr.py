def run_ocr_stub(image_path: str) -> list[dict]:
    """Return simulated OCR detections for a given image path."""
    chords = ["A", "E/G#", "F#m7", "A", "D", "E", "F#m7", "E7(sus4)", "A", "E/G#"]
    results = []
    for i, chord in enumerate(chords):
        x1 = 10 + i * 80
        y1 = 20
        x2 = x1 + 60
        y2 = 50
        results.append({
            "text": chord,
            "confidence": 0.95,
            "bbox": [x1, y1, x2, y2],
        })
    return results