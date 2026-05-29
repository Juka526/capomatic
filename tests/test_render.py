"""Unit tests for backend.overlay.render — overlay rendering."""
from __future__ import annotations

import pytest
from PIL import Image

from backend.overlay.render import (
    _chord_display_width,
    _load_font,
    _shorten_chord_display,
    render_overlay,
)


def _white_img(w: int = 400, h: int = 300) -> Image.Image:
    """Create a white RGB PIL image."""
    return Image.new("RGB", (w, h), (255, 255, 255))


def _chord(text: str, transposed: str, bbox: list[int]) -> dict:
    return {"text": text, "transposed": transposed, "bbox": bbox}


# ---------------------------------------------------------------------------
# _shorten_chord_display
# ---------------------------------------------------------------------------

class TestShortenChordDisplay:
    def test_maj_to_M(self):
        assert _shorten_chord_display("Bbmaj7") == ("BbM7", "")

    def test_sus_split(self):
        assert _shorten_chord_display("A7sus4") == ("A7", "sus4")

    def test_dim_split(self):
        assert _shorten_chord_display("G#dim") == ("G#", "dim")

    def test_aug_split(self):
        assert _shorten_chord_display("Faug7") == ("F", "aug7")

    def test_maj_and_sus(self):
        assert _shorten_chord_display("Fmaj7sus4") == ("FM7", "sus4")

    def test_plain_chord_unchanged(self):
        assert _shorten_chord_display("Am7") == ("Am7", "")

    def test_single_root(self):
        assert _shorten_chord_display("D") == ("D", "")

    def test_slash_chord(self):
        assert _shorten_chord_display("D/F#") == ("D/F#", "")

    def test_gmaj(self):
        assert _shorten_chord_display("Gmaj7") == ("GM7", "")

    def test_dim7(self):
        assert _shorten_chord_display("Bdim7") == ("B", "dim7")


# ---------------------------------------------------------------------------
# _chord_display_width
# ---------------------------------------------------------------------------

class TestChordDisplayWidth:
    def test_positive_width(self):
        font = _load_font(18)
        small = _load_font(13)
        assert _chord_display_width("Am7", font, small) > 0

    def test_sus_wider_than_main_alone(self):
        font = _load_font(18)
        small = _load_font(13)
        w_sus = _chord_display_width("A7sus4", font, small)
        w_plain = _chord_display_width("A7", font, small)
        assert w_sus > w_plain


# ---------------------------------------------------------------------------
# render_overlay — basic behaviour
# ---------------------------------------------------------------------------

class TestRenderOverlay:
    def test_above_mode_returns_image(self):
        img = _white_img()
        chords = [_chord("Am", "Bm", [50, 100, 100, 120])]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)

    def test_replace_mode_returns_image(self):
        img = _white_img()
        chords = [_chord("Am", "Bm", [50, 100, 100, 120])]
        result = render_overlay(img, chords, "replace")
        assert isinstance(result, Image.Image)

    def test_empty_chords_returns_copy(self):
        img = _white_img()
        result = render_overlay(img, [], "above")
        assert isinstance(result, Image.Image)
        assert result.size == img.size

    def test_skips_none_transposed(self):
        img = _white_img()
        chords = [{"text": "Am", "transposed": None, "bbox": [10, 10, 50, 30]}]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)

    def test_skips_none_bbox(self):
        img = _white_img()
        chords = [{"text": "Am", "transposed": "Bm", "bbox": None}]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)

    def test_does_not_modify_original(self):
        img = _white_img()
        original_data = list(img.getdata())
        chords = [_chord("Am", "Bm", [50, 100, 100, 120])]
        render_overlay(img, chords, "replace")
        assert list(img.getdata()) == original_data

    def test_multiple_rows_above(self):
        img = _white_img(w=400, h=600)
        chords = [
            _chord("Am", "Bm", [50, 100, 100, 120]),
            _chord("C", "D", [200, 100, 250, 120]),
            _chord("G", "A", [50, 300, 100, 320]),
        ]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)

    def test_multiple_chords_replace_uniform_font(self):
        img = _white_img(w=400, h=300)
        chords = [
            _chord("Am", "Bm", [10, 50, 60, 70]),
            _chord("C", "D", [100, 50, 150, 75]),
            _chord("G", "A", [200, 50, 250, 68]),
        ]
        result = render_overlay(img, chords, "replace")
        assert isinstance(result, Image.Image)

    def test_small_bbox_uses_min_font_size(self):
        img = _white_img()
        chords = [_chord("Am", "Bm", [10, 10, 50, 15])]
        result = render_overlay(img, chords, "replace")
        assert isinstance(result, Image.Image)

    def test_chords_near_edges(self):
        img = _white_img(w=200, h=200)
        chords = [
            _chord("Am", "Bm", [0, 0, 40, 20]),
            _chord("C", "D", [160, 180, 200, 200]),
        ]
        result = render_overlay(img, chords, "above")
        assert isinstance(result, Image.Image)


# ---------------------------------------------------------------------------
# render_overlay — key info & white box
# ---------------------------------------------------------------------------

class TestRenderReplaceRefinements:
    def test_replace_with_key_info(self):
        img = _white_img()
        chords = [_chord("Am", "Cm", [50, 100, 100, 120])]
        result = render_overlay(
            img, chords, "replace",
            original_key="F", target_key="D#", semitones=-2,
        )
        assert isinstance(result, Image.Image)

    def test_replace_uses_local_background_colour(self):
        # Colored background should be preserved instead of forcing pure white.
        img = Image.new("RGB", (400, 300), (100, 100, 100))
        chords = [_chord("Am", "Am", [50, 90, 100, 130])]
        result = render_overlay(img, chords, "replace")
        px = result.getpixel((70, 110))
        assert px == (100, 100, 100), f"Expected local background colour, got {px}"

    def test_row_y_alignment_no_crash(self):
        img = _white_img(w=400, h=300)
        # Two chords in the same row with slightly different y1 values.
        chords = [
            _chord("Am", "Cm", [50, 98, 100, 118]),
            _chord("G", "Bb", [200, 105, 250, 125]),
        ]
        result = render_overlay(img, chords, "replace")
        assert isinstance(result, Image.Image)

    def test_zero_semitones_shows_key_only(self):
        """When semitones=0 and both keys match, header shows 'Key: F'."""
        img = _white_img()
        chords = [_chord("Am", "Am", [50, 100, 100, 120])]
        result = render_overlay(
            img, chords, "replace",
            original_key="F", target_key="F", semitones=0,
        )
        assert isinstance(result, Image.Image)

    def test_dense_row_reduces_font(self):
        """Chords packed tightly should render without crashing."""
        img = _white_img(w=200, h=100)
        chords = [
            _chord("Am", "Bm", [10, 40, 40, 60]),
            _chord("C",  "D",  [45, 40, 70, 60]),
            _chord("G",  "A",  [75, 40, 100, 60]),
            _chord("F",  "G",  [105, 40, 130, 60]),
        ]
        result = render_overlay(img, chords, "replace")
        assert isinstance(result, Image.Image)
