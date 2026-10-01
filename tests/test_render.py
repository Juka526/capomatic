"""Unit tests for backend.overlay.render — overlay rendering."""
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

import backend.overlay.render as render_module
from backend.overlay.render import (
    _chord_display_width,
    _find_row_font_sizes,
    _header_lines,
    _get_staff_systems,
    _load_font,
    _place_row_labels_anchored,
    _shorten_chord_display,
    _text_height,
    _text_width,
    render_overlay,
)


def _white_img(w: int = 400, h: int = 300) -> Image.Image:
    """Create a white RGB PIL image."""
    return Image.new("RGB", (w, h), (255, 255, 255))


def _chord(text: str, transposed: str, bbox: list[int]) -> dict:
    return {"text": text, "transposed": transposed, "bbox": bbox}


def test_text_measurements_are_cached():
    class FakeFont:
        def __init__(self):
            self.width_calls = 0
            self.height_calls = 0

        def getlength(self, text):
            self.width_calls += 1
            return len(text) * 10

        def getbbox(self, text, anchor=None):
            self.height_calls += 1
            return (0, 0, len(text) * 10, 12)

    font = FakeFont()
    _text_width.cache_clear()
    _text_height.cache_clear()

    assert _text_width(font, "Am7") == _text_width(font, "Am7") == 30
    assert _text_height(font, "Am7") == _text_height(font, "Am7") == 12
    assert (font.width_calls, font.height_calls) == (1, 1)


def test_staff_systems_are_cached_on_source_image(monkeypatch):
    calls = 0

    def fake_detect(_img):
        nonlocal calls
        calls += 1
        return [(40, 60)]

    monkeypatch.setattr("backend.ocr.preprocess.detect_staff_systems", fake_detect)
    image = _white_img()

    assert _get_staff_systems(image) == [(40, 60)]
    assert _get_staff_systems(image) == [(40, 60)]
    assert calls == 1


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
    def test_header_color_matches_render_mode(self, monkeypatch):
        colors = []

        def fake_header(*args, **kwargs):
            colors.append(kwargs["text_fill"])

        monkeypatch.setattr(render_module, "_draw_info_header", fake_header)
        img = _white_img()
        chords = [_chord("Am", "Bm", [50, 100, 100, 120])]

        render_overlay(img, chords, "above")
        render_overlay(img, chords, "replace")

        assert colors == [render_module._ORANGE, render_module._DARK_BLUE]

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

    def test_above_mode_inserts_at_chord_row_when_space_is_occupied(self, monkeypatch):
        calls = []

        def fake_insert(img, expansions):
            calls.extend(expansions)
            return img

        monkeypatch.setattr(render_module, "_insert_whitespace", fake_insert)

        img = _white_img(w=240, h=160)
        draw = ImageDraw.Draw(img)
        # Dense lyric/staff-like content above the chord row gets its own space
        # without cutting through that existing content.
        for y in range(32, 72, 4):
            draw.line((0, y, 239, y), fill=(0, 0, 0), width=1)
        chords = [_chord("Am", "Bm", [40, 82, 90, 104])]

        render_overlay(img, chords, "above")

        assert calls and calls[0][0] == 82

    def test_above_mode_inserts_whitespace_at_original_chord_row(self, monkeypatch):
        calls = []

        def fake_insert(img, expansions):
            calls.extend(expansions)
            return img

        monkeypatch.setattr(render_module, "_insert_whitespace", fake_insert)

        img = _white_img(w=240, h=180)
        draw = ImageDraw.Draw(img)
        # Content in the label area creates a new line immediately before the
        # original chord row.
        for y in range(78, 86, 2):
            draw.line((0, y, 239, y), fill=(0, 0, 0), width=1)
        chords = [_chord("Am", "Bm", [40, 100, 90, 122])]

        render_overlay(img, chords, "above")

        assert calls
        assert calls[0][0] == 100

    def test_above_mode_inserts_when_lyrics_share_row_band(self, monkeypatch):
        calls = []

        def fake_insert(img, expansions):
            calls.extend(expansions)
            return img

        monkeypatch.setattr(render_module, "_insert_whitespace", fake_insert)

        img = _white_img(w=260, h=180)
        draw = ImageDraw.Draw(img)
        # Ink away from the exact chord label x still means the printed row has
        # no clean above-slot; insert the old extra line above the chord row.
        draw.rectangle((150, 78, 230, 86), fill=(0, 0, 0))
        chords = [_chord("Am", "Bm", [40, 100, 90, 122])]

        render_overlay(img, chords, "above")

        assert calls

    def test_above_mode_detects_local_ink_under_one_label(self, monkeypatch):
        calls = []

        def fake_insert(img, expansions):
            calls.extend(expansions)
            return img

        monkeypatch.setattr(render_module, "_insert_whitespace", fake_insert)

        img = _white_img(w=1000, h=180)
        draw = ImageDraw.Draw(img)
        draw.rectangle((76, 78, 82, 84), fill=(0, 0, 0))
        chords = [_chord("Am", "Bm", [40, 100, 90, 122])]

        render_overlay(img, chords, "above")

        assert calls and calls[0][0] == 100


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

    def test_replace_uses_each_original_chord_y(self, monkeypatch):
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

        assert [call[1] for call in calls] == [40, 44, 36]

    def test_replace_y_is_not_pulled_up_by_row_median(self, monkeypatch):
        calls = []

        def fake_draw(draw, x, y, transposed, font, small_font, fill):
            calls.append((transposed, y))
            return 0

        monkeypatch.setattr(render_module, "_draw_chord_text", fake_draw)

        img = _white_img(w=1000, h=1400)
        chords = [
            _chord("BbM7", "BbM7", [156, 1266, 225, 1294]),
            _chord("C/Bb", "C/Bb", [225, 1266, 271, 1294]),
            _chord("Am7", "Am7", [306, 1268, 353, 1292]),
            _chord("Bb/D", "Bb/D", [881, 1257, 968, 1298]),
        ]

        render_module.render_overlay(img, chords, "replace")

        assert calls == [
            ("BbM7", 1266),
            ("C/Bb", 1266),
            ("Am7", 1268),
            ("Bb/D", 1257),
        ]

    def test_render_drops_lyric_row_false_positive_near_staff(self, monkeypatch):
        calls = []

        def fake_staff_systems(_img):
            return [(196, 229), (349, 383), (513, 547)]

        def fake_draw(draw, x, y, transposed, font, small_font, fill):
            calls.append(transposed)
            return 0

        monkeypatch.setattr("backend.ocr.preprocess.detect_staff_systems", fake_staff_systems)
        monkeypatch.setattr(render_module, "_draw_chord_text", fake_draw)

        img = _white_img(w=996, h=700)
        chords = [
            _chord("BbM7", "BbM7", [245, 308, 302, 333]),
            _chord("A2", "A2", [283, 427, 369, 452]),
            _chord("Am7", "Am7", [385, 474, 430, 497]),
        ]

        render_module.render_overlay(img, chords, "replace")

        assert calls == ["BbM7", "Am7"]

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

        font = render_module._load_font(17)
        small_font = render_module._load_font(int(17 * render_module._SMALL_FONT_RATIO))
        label_height = max(
            render_module._chord_display_height(chord["transposed"], font, small_font)
            for chord in chords
        )
        expected_y = min(chord["bbox"][1] for chord in chords) - label_height - render_module._GAP
        assert [call[1] for call in calls] == [expected_y, expected_y, expected_y]

    def test_above_row_placement_resolves_chained_overlap(self, monkeypatch):
        class FakeFont:
            size = 18

        monkeypatch.setattr(render_module, "_chord_display_width", lambda *args: 42)
        row = [
            _chord("Gm7", "Gm7", [10, 40, 30, 60]),
            _chord("Am7", "Am7", [35, 40, 55, 60]),
            _chord("Bbm7", "Bbm7", [60, 40, 80, 60]),
        ]

        placed = _place_row_labels_anchored(row, FakeFont(), FakeFont(), 180)
        xs = [x for _, x in placed]

        assert xs[1] >= xs[0] + 42 + 2 * render_module._BOX_PAD + 6
        assert xs[2] >= xs[1] + 42 + 2 * render_module._BOX_PAD + 6

    def test_above_row_placement_keeps_order_when_row_cannot_fit(self, monkeypatch):
        class FakeFont:
            size = 18

        monkeypatch.setattr(render_module, "_chord_display_width", lambda *args: 42)
        row = [
            _chord("Gm7", "Gm7", [10, 40, 30, 60]),
            _chord("Am7", "Am7", [35, 40, 55, 60]),
            _chord("Bbm7", "Bbm7", [60, 40, 80, 60]),
        ]

        placed = _place_row_labels_anchored(row, FakeFont(), FakeFont(), 130)
        xs = [x for _, x in placed]

        assert xs[1] >= xs[0] + 42 + 2 * render_module._BOX_PAD + 6
        assert xs[2] >= xs[1] + 42 + 2 * render_module._BOX_PAD + 6

    def test_above_dense_row_shrinks_font_before_shifting_left(self, monkeypatch):
        class FakeFont:
            def __init__(self, size):
                self.size = size

        monkeypatch.setattr(render_module, "_load_font", lambda size: FakeFont(size))
        monkeypatch.setattr(
            render_module,
            "_chord_display_width",
            lambda transposed, font, small_font: font.size * 2,
        )
        row = [
            _chord("Gm7", "Gm7", [10, 40, 30, 60]),
            _chord("Am7", "Am7", [35, 40, 55, 60]),
            _chord("Bbm7", "Bbm7", [60, 40, 80, 60]),
        ]

        size = _find_row_font_sizes([row], 18, 130)[0]
        placed = _place_row_labels_anchored(
            row, FakeFont(size), FakeFont(size), 130,
        )

        assert size == 14
        assert placed[0][1] == row[0]["bbox"][0]

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

    def test_replace_draws_row_backgrounds_before_text(self, monkeypatch):
        calls = []

        def fake_bg(draw, chord, x, y, transposed, font, small_font, img_width):
            calls.append(("bg", transposed))
            draw.rectangle([0, 0, 80, 80], fill=(255, 255, 255))

        def fake_draw(draw, x, y, transposed, font, small_font, fill):
            calls.append(("text", transposed))
            if transposed == "Bm":
                draw.point((10, 50), fill=(0, 0, 0))
            return 0

        monkeypatch.setattr(render_module, "_draw_replace_label_background", fake_bg)
        monkeypatch.setattr(render_module, "_draw_chord_text", fake_draw)

        img = _white_img(w=120, h=90)
        chords = [
            _chord("Am", "Bm", [10, 40, 30, 60]),
            _chord("C", "D", [35, 40, 55, 60]),
        ]
        result = render_module.render_overlay(img, chords, "replace")

        assert calls == [("bg", "Bm"), ("bg", "D"), ("text", "Bm"), ("text", "D")]
        assert result.getpixel((10, 50)) == (0, 0, 0)

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


# ---------------------------------------------------------------------------
# Key-change header text
# ---------------------------------------------------------------------------

class TestHeaderLines:
    @pytest.mark.parametrize("semitones,target,expected", [
        (-2, "F", ["G -> F (-2 semitones)", "Capo: 2"]),
        (-1, "F#", ["G -> F# (-1 semitone)", "Capo: 1"]),
        (-7, "C", ["G -> C (-7 semitones)", "Capo: 7"]),
        (-8, "B", ["G -> B (-8 semitones)"]),
        (-11, "Ab", ["G -> Ab (-11 semitones)"]),
        (1, "Ab", ["G -> Ab (+1 semitone)"]),
        (2, "A", ["G -> A (+2 semitones)"]),
    ])
    def test_semitone_label_and_capo_only_in_range(self, semitones, target, expected):
        assert _header_lines("G", target, semitones) == expected

    def test_no_shift_shows_the_key(self):
        assert _header_lines("F", "F", 0) == ["Key: F"]

    def test_nothing_to_show(self):
        assert _header_lines(None, None, 0) == []

    def test_shift_without_key_names(self):
        assert _header_lines(None, None, -1) == ["Semitones: -1 semitone", "Capo: 1"]
