import pytest
from backend.chords.parser import parse_chord
from backend.chords.transpose import transpose_note, transpose_chord, compute_target_key

# ---------------------------------------------------------------------------
# transpose_note — basic pitch arithmetic
# ---------------------------------------------------------------------------

def test_transpose_note_up_whole_step():
    assert transpose_note("A", 2) == "B"

def test_transpose_note_down_half_step():
    assert transpose_note("F", -1, "sharp") == "E"

def test_transpose_note_wraps_octave():
    # B + 2 semitones = C# (wraps around)
    assert transpose_note("B", 2) == "C#"

def test_transpose_note_zero():
    assert transpose_note("G", 0) == "G"


# ---------------------------------------------------------------------------
# Forbidden spelling guards
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("note,semi,prefer,expected", [
    ("B",  1, "sharp", "C"),   # never B#
    ("E",  1, "sharp", "F"),   # never E#
    ("F#", 1, "sharp", "G"),   # never F##
    ("C", -1, "flat",  "B"),   # never Cb
    ("F", -1, "flat",  "E"),   # never Fb
])
def test_forbidden_spellings(note, semi, prefer, expected):
    assert transpose_note(note, semi, prefer) == expected


# ---------------------------------------------------------------------------
# Enharmonic preference
# ---------------------------------------------------------------------------

def test_flat_preference_a_sharp_to_bb():
    assert transpose_note("A", 1, "flat") == "Bb"

def test_sharp_preference_a_sharp():
    assert transpose_note("A", 1, "sharp") == "A#"

@pytest.mark.parametrize("target_key,expected", [
    ("Bb", "Bb"),   # flat key → flat
    ("F",  "Bb"),   # flat key → flat
    ("E",  "A#"),   # sharp key → sharp
    ("F#", "A#"),   # sharp key → sharp
])
def test_target_key_preference(target_key, expected):
    c = parse_chord("A")
    assert transpose_chord(c, 1, target_key=target_key) == expected


# ---------------------------------------------------------------------------
# Specific spec-required test cases
# ---------------------------------------------------------------------------

def test_f_down_1_to_key_e():
    # transpose "F" down 1 semitone to target_key="E" => "E"
    c = parse_chord("F")
    assert transpose_chord(c, -1, target_key="E") == "E"

def test_g_over_b_up_2():
    # transpose "G/B" up 2 semitones => "A/C#"
    c = parse_chord("G/B")
    assert transpose_chord(c, 2) == "A/C#"

def test_d_over_fsharp_up_2():
    # D up 2 = E, F# up 2 = G#
    c = parse_chord("D/F#")
    assert transpose_chord(c, 2) == "E/G#"


# ---------------------------------------------------------------------------
# Quality / extension preservation
# ---------------------------------------------------------------------------

def test_transpose_m7_preserved():
    c = parse_chord("Am7")
    assert transpose_chord(c, 2) == "Bm7"

def test_transpose_maj7_preserved():
    c = parse_chord("Cmaj7")
    assert transpose_chord(c, 2) == "Dmaj7"

def test_transpose_e7sus4_no_parens():
    # E7(sus4) up 2 semitones — parens must not appear in output
    c = parse_chord("E7(sus4)")
    result = transpose_chord(c, 2)
    assert result == "F#7sus4"
    assert "(" not in result

def test_transpose_fsharp_m7_zero():
    c = parse_chord("F#m7")
    assert transpose_chord(c, 0) == "F#m7"

def test_transpose_dim_preserved():
    c = parse_chord("Bdim")
    assert transpose_chord(c, 1) == "Cdim"

def test_transpose_slash_with_quality():
    c = parse_chord("Em7/G")
    # E up 2 = F#, G up 2 = A
    assert transpose_chord(c, 2) == "F#m7/A"


# ---------------------------------------------------------------------------
# Full round-trip: parse then transpose
# ---------------------------------------------------------------------------

def test_roundtrip_fsharp_m7():
    c = parse_chord("F#m7")
    up = transpose_chord(c, 2)    # A  -> Abm7? no: F#+2=G#, so G#m7
    assert up == "G#m7"
    c2 = parse_chord(up)
    down = transpose_chord(c2, -2)
    assert down == "F#m7"


# ---------------------------------------------------------------------------
# compute_target_key — key name transposition
# ---------------------------------------------------------------------------

class TestComputeTargetKey:
    def test_c_up_2(self):
        assert compute_target_key("C", 2) == "D"

    def test_a_up_3(self):
        assert compute_target_key("A", 3) == "C"

    def test_b_up_1_wraps(self):
        assert compute_target_key("B", 1) == "C"

    def test_zero_no_change(self):
        assert compute_target_key("G", 0) == "G"

    def test_standard_flat_name(self):
        """Index 1 should be Db, not C#."""
        assert compute_target_key("C", 1) == "Db"

    def test_f_sharp_not_gb(self):
        """Index 6 should be F#, not Gb."""
        assert compute_target_key("C", 6) == "F#"

    def test_negative_semitones(self):
        assert compute_target_key("C", -3) == "A"

    def test_enharmonic_input_normalized(self):
        """Gb input should resolve to the same index as F#."""
        assert compute_target_key("Gb", 0) == "F#"

    def test_invalid_note_raises(self):
        with pytest.raises(ValueError):
            compute_target_key("Z", 3)
