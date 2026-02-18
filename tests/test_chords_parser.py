import pytest
from backend.chords.normalize import normalize_chord_text
from backend.chords.parser import parse_chord


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def test_normalize_min_to_m():
    assert normalize_chord_text("C#min7") == "C#m7"

def test_normalize_spaces_removed():
    assert normalize_chord_text("A sus4") == "Asus4"

def test_normalize_unicode_sharp():
    assert normalize_chord_text("C\u266fm7") == "C#m7"

def test_normalize_unicode_flat():
    assert normalize_chord_text("B\u266dmaj7") == "Bbmaj7"

def test_normalize_trim():
    assert normalize_chord_text("  Am  ") == "Am"

def test_normalize_maj_unchanged():
    # "maj" must not be mutated by the "min"->"m" substitution
    assert normalize_chord_text("Cmaj7") == "Cmaj7"

def test_normalize_dim_unchanged():
    assert normalize_chord_text("Bdim") == "Bdim"


# ---------------------------------------------------------------------------
# Asus4 variant equivalence
# ---------------------------------------------------------------------------

def test_asus4_variants_same_root_and_bass():
    """A sus4, A(sus4), Asus4 must all parse to the same root/bass."""
    a = parse_chord("A sus4")
    b = parse_chord("A(sus4)")
    c = parse_chord("Asus4")
    for chord in (a, b, c):
        assert chord.root == "A"
        assert chord.bass is None

def test_asus4_variants_same_quality_and_ext():
    a = parse_chord("A sus4")
    b = parse_chord("A(sus4)")
    c = parse_chord("Asus4")
    assert a.quality == b.quality == c.quality
    assert a.extensions == b.extensions == c.extensions


# ---------------------------------------------------------------------------
# Root extraction
# ---------------------------------------------------------------------------

def test_parse_simple_root():
    c = parse_chord("A")
    assert c.root == "A"
    assert c.quality == ""
    assert c.extensions == ""
    assert c.bass is None

def test_parse_sharp_root():
    c = parse_chord("F#m7")
    assert c.root == "F#"
    assert c.quality == "m"
    assert c.extensions == "7"

def test_parse_flat_root():
    c = parse_chord("Bbmaj7")
    assert c.root == "Bb"
    assert c.quality == "maj"
    assert c.extensions == "7"

def test_parse_e7sus4_root():
    c = parse_chord("E7(sus4)")
    assert c.root == "E"
    assert c.bass is None

def test_parse_e7sus4_extensions_no_parens():
    # Parentheses stripped; extensions stored compactly.
    c = parse_chord("E7(sus4)")
    assert "(" not in c.extensions
    assert "sus4" in c.extensions

def test_parse_csharp_min7():
    c = parse_chord("C#min7")
    assert c.root == "C#"
    assert c.quality == "m"
    assert c.extensions == "7"


# ---------------------------------------------------------------------------
# Quality parsing
# ---------------------------------------------------------------------------

def test_parse_maj7():
    c = parse_chord("Amaj7")
    assert c.quality == "maj"
    assert c.extensions == "7"

def test_parse_m7():
    c = parse_chord("Am7")
    assert c.quality == "m"
    assert c.extensions == "7"

def test_parse_dim():
    c = parse_chord("Bdim")
    assert c.quality == "dim"
    assert c.extensions == ""

def test_parse_aug():
    c = parse_chord("Caug")
    assert c.quality == "aug"
    assert c.extensions == ""

def test_parse_no_quality():
    c = parse_chord("A7")
    assert c.quality == ""
    assert c.extensions == "7"


# ---------------------------------------------------------------------------
# Slash chords
# ---------------------------------------------------------------------------

def test_parse_slash_g_b():
    c = parse_chord("G/B")
    assert c.root == "G"
    assert c.bass == "B"

def test_parse_slash_d_fsharp():
    c = parse_chord("D/F#")
    assert c.root == "D"
    assert c.bass == "F#"

def test_parse_slash_a_csharp():
    c = parse_chord("A/C#")
    assert c.root == "A"
    assert c.bass == "C#"

def test_parse_slash_with_quality():
    c = parse_chord("Em7/G")
    assert c.root == "E"
    assert c.quality == "m"
    assert c.extensions == "7"
    assert c.bass == "G"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_parse_invalid_raises():
    with pytest.raises(ValueError):
        parse_chord("not_a_chord")

def test_parse_empty_raises():
    with pytest.raises(ValueError):
        parse_chord("")
