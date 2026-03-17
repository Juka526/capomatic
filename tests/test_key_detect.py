"""Unit tests for backend.chords.key_detect — key inference from chords."""
from __future__ import annotations

import pytest

from backend.chords.key_detect import infer_key


def _items(chord_texts: list[str]) -> list[dict]:
    """Build minimal chord item dicts from a list of chord text strings."""
    return [{"text": t, "confidence": 0.95, "bbox": [0, 0, 50, 20]}
            for t in chord_texts]


# ---------------------------------------------------------------------------
# Core key detection
# ---------------------------------------------------------------------------

class TestInferKey:
    def test_f_major(self):
        """믿음으로 나아가네 — F major (Bb=IV, C=V dominate)."""
        chords = _items([
            "Bbmaj7", "F/A", "Gm7", "Bb/C", "C", "C/Bb",
            "Am7", "Dm7", "F", "Bb/F", "F/Eb", "Eb", "Csus4",
            "C/D", "Bb/D", "C/E",
        ])
        assert infer_key(chords) == "F"

    def test_c_major(self):
        chords = _items(["C", "G", "Am", "F", "Dm", "Em", "C", "G"])
        assert infer_key(chords) == "C"

    def test_a_major(self):
        """사랑한다 말하시네 — A major (E=V dominant)."""
        chords = _items([
            "A", "A7/G", "D/F#", "Dm/F", "A/E", "B7/D#",
            "Bm7", "Esus4", "E", "A/C#", "C#7", "F#m7",
            "B7", "D/E", "E7",
        ])
        assert infer_key(chords) == "A"

    def test_bb_major(self):
        chords = _items(["Bb", "Eb", "F", "Gm", "Cm", "Dm", "Bb"])
        assert infer_key(chords) == "Bb"

    def test_d_major(self):
        chords = _items(["D", "G", "A", "Bm", "Em", "F#m", "D"])
        assert infer_key(chords) == "D"

    def test_g_major(self):
        chords = _items(["G", "C", "D", "Em", "Am", "G"])
        assert infer_key(chords) == "G"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestInferKeyEdgeCases:
    def test_empty_list(self):
        assert infer_key([]) is None

    def test_unparseable_chords(self):
        chords = _items(["XYZ", "???", "123"])
        assert infer_key(chords) is None

    def test_single_chord(self):
        chords = _items(["G"])
        assert infer_key(chords) == "G"

    def test_frequency_weighted(self):
        """Many repetitions of C should outweigh a single non-diatonic F#."""
        chords = _items(["C"] * 10 + ["F#"])
        assert infer_key(chords) == "C"

    def test_slash_chords_use_root(self):
        """Slash chords like G/B should contribute the root G, not the bass B."""
        chords = _items(["G/B", "C/E", "D/F#", "G"])
        assert infer_key(chords) == "G"

    def test_missing_text_key_skipped(self):
        """Items without a 'text' key are silently skipped."""
        chords = [{"confidence": 0.9, "bbox": [0, 0, 50, 20]}]
        assert infer_key(chords) is None
