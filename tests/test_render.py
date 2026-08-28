"""Unit tests for backend.overlay.render — overlay rendering."""
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

import backend.overlay.render as render_module
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
    def test_load_font_reuses_cached_font_object(self):
        _load_font.cache_clear()
        first = _load_font(18)
        second = _load_font(18)

        assert first is second
        assert _load_font.cache_info().hits >= 1

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
        original_data = img.tobytes()
        chords = [_chord("Am", "Bm", [50, 100, 100, 120])]
        render_overlay(img, chords, "replace")
        assert img.tobytes() == original_data

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

    def test_above_mode_skips_whitespace_insert_when_no_safe_blank_band(self, monkeypatch):
        calls = []

        def fake_insert(img, expansions):
            calls.extend(expansions)
            return img

        monkeypatch.setattr(render_module, "_insert_whitespace", fake_insert)

        img = _white_img(w=240, h=160)
        draw = ImageDraw.Draw(img)
        # Dense lyric/staff-like content above the chord row should not be split.
        for y in range(32, 72, 4):
            draw.line((0, y, 239, y), fill=(0, 0, 0), width=1)
        chords = [_chord("Am", "Bm", [40, 82, 90, 104])]

        render_overlay(img, chords, "above")

        assert calls == []

    def test_above_mode_inserts_whitespace_at_safe_blank_band(self, monkeypatch):
        calls = []

        def fake_insert(img, expansions):
            calls.extend(expansions)
            return img

        monkeypatch.setattr(render_module, "_insert_whitespace", fake_insert)

        img = _white_img(w=240, h=180)
        draw = ImageDraw.Draw(img)
        # Content in the label area forces above mode to seek the safe blank
        # band immediately below it.
        for y in range(78, 86, 2):
            draw.line((0, y, 239, y), fill=(0, 0, 0), width=1)
        chords = [_chord("Am", "Bm", [40, 100, 90, 122])]

        render_overlay(img, chords, "above")

        assert calls
        assert 86 <= calls[0][0] <= 100


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

    def test_replace_uses_white_label_background(self, monkeypatch):
        # Replace labels should sit on a clean white rectangle for readability.
        monkeypatch.setattr(render_module, "_draw_chord_text", lambda *args, **kwargs: 0)
        img = Image.new("RGB", (400, 300), (100, 100, 100))
        chords = [_chord("Am", "Am", [50, 90, 100, 130])]
        result = render_overlay(img, chords, "replace")
        px = result.getpixel((70, 110))
        assert px == (255, 255, 255), f"Expected white label background, got {px}"

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

    def test_replace_anchors_text_to_bbox_top_left(self, monkeypatch):
        calls = []

        def fake_draw(draw, x, y, transposed, font, small_font, fill):
            calls.append((x, y, transposed))
            return 0

        monkeypatch.setattr(render_module, "_draw_chord_text", fake_draw)

        img = _white_img(w=300, h=200)
        chords = [
            _chord("Am", "Bm", [10, 40, 60, 65]),
            _chord("C", "D", [120, 90, 170, 115]),
        ]
        render_module.render_overlay(img, chords, "replace")

        assert calls == [
            (10, 40, "Bm"),
            (120, 90, "D"),
        ]

    def test_replace_aligns_same_row_to_one_y(self, monkeypatch):
        calls = []

        def fake_draw(draw, x, y, transposed, font, small_font, fill):
            calls.append((x, y, transposed))
            return 0

        monkeypatch.setattr(render_module, "_draw_chord_text", fake_draw)

        img = _white_img(w=300, h=200)
        chords = [
            _chord("Am", "Bm", [10, 40, 60, 65]),
            _chord("C", "D", [90, 44, 140, 69]),
            _chord("G", "A", [180, 36, 230, 61]),
        ]
        render_module.render_overlay(img, chords, "replace")

        assert [call[1] for call in calls] == [40, 40, 40]

    def test_replace_draws_white_rectangular_label_background(self):
        original_draw = render_module._draw_chord_text
        render_module._draw_chord_text = lambda *args, **kwargs: 0
        img = Image.new("RGB", (180, 120), (180, 180, 180))
        chords = [_chord("Am", "Bm", [40, 50, 80, 72])]

        try:
            result = render_module.render_overlay(img, chords, "replace")
        finally:
            render_module._draw_chord_text = original_draw

        assert result.getpixel((42, 50)) == (255, 255, 255)

    def test_above_aligns_same_row_to_one_y(self, monkeypatch):
        calls = []

        def fake_draw(draw, x, y, transposed, font, small_font, fill):
            calls.append((x, y, transposed))
            return 0

        monkeypatch.setattr(render_module, "_draw_chord_text", fake_draw)

        img = _white_img(w=300, h=200)
        chords = [
            _chord("Am", "Bm", [10, 60, 60, 80]),
            _chord("C", "D", [90, 66, 140, 86]),
            _chord("G", "A", [180, 54, 230, 74]),
        ]
        render_module.render_overlay(img, chords, "above")

        assert [call[1] for call in calls] == [41, 41, 41]

    def test_replace_shifts_dense_row_to_avoid_overlap(self, monkeypatch):
        calls = []

        class FakeFont:
            def __init__(self, size):
                self.size = size

        def fake_load_font(size, *, bold=False):
            return FakeFont(size)

        def fake_width(transposed, font, small_font):
            return 30

        def fake_draw(draw, x, y, transposed, font, small_font, fill):
            calls.append((x, y, transposed, font.size))
            return 30

        monkeypatch.setattr(render_module, "_load_font", fake_load_font)
        monkeypatch.setattr(render_module, "_chord_display_width", fake_width)
        monkeypatch.setattr(render_module, "_draw_chord_text", fake_draw)

        img = _white_img(w=180, h=120)
        chords = [
            _chord("Am", "Bm", [10, 40, 30, 60]),
            _chord("C", "D", [25, 40, 45, 60]),
            _chord("G", "A", [40, 40, 60, 60]),
        ]
        render_module.render_overlay(img, chords, "replace")

        xs = [call[0] for call in calls]
        assert xs == [10, 44, 78]

    def test_replace_uses_one_median_bbox_font_size(self, monkeypatch):
        calls = []

        class FakeFont:
            def __init__(self, size):
                self.size = size

        def fake_load_font(size, *, bold=False):
            return FakeFont(size)

        def fake_draw(draw, x, y, transposed, font, small_font, fill):
            calls.append(font.size)
            return 0

        monkeypatch.setattr(render_module, "_load_font", fake_load_font)
        monkeypatch.setattr(render_module, "_draw_chord_text", fake_draw)

        img = _white_img(w=400, h=250)
        chords = [
            _chord("Am", "Bm", [10, 40, 60, 50]),    # height 10
            _chord("C", "D", [120, 90, 170, 120]),   # height 30
            _chord("G", "A", [220, 140, 270, 190]),  # height 50
        ]
        render_module.render_overlay(img, chords, "replace")

        assert calls == [26, 26, 26]

    def test_glyph_mask_pixels_include_chord_but_skip_staff_line(self):
        img = _white_img(w=160, h=90)
        draw = ImageDraw.Draw(img)
        draw.rectangle([52, 20, 70, 32], fill=(0, 0, 0))
        draw.line((0, 55, 159, 55), fill=(0, 0, 0))

        pixels = render_module._glyph_mask_pixels(img, [40, 10, 110, 65])

        assert (60, 25) in pixels
        assert (60, 55) not in pixels

    def test_erase_glyph_pixels_preserves_staff_line(self):
        img = _white_img(w=160, h=90)
        draw = ImageDraw.Draw(img)
        draw.rectangle([52, 20, 70, 32], fill=(0, 0, 0))
        draw.line((0, 55, 159, 55), fill=(0, 0, 0))

        result = img.copy()
        render_module._erase_glyph_pixels(
            result,
            img,
            [40, 10, 110, 65],
            (255, 255, 255),
        )

        assert result.getpixel((60, 25)) == (255, 255, 255)
        assert result.getpixel((60, 55)) == (0, 0, 0)
