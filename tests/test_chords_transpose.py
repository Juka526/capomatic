import pytest
from backend.chords.parser import parse_chord
from backend.chords.transpose import transpose_note, transpose_chord

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

def test_no_b_sharp():
    # B + 1 must be C, never B#
    assert transpose_note("B", 1) == "C"

def test_no_e_sharp():
    # E + 1 must be F, never E#
    assert transpose_note("E", 1) == "F"

def test_no_f_double_sharp():
    # F# + 1 with sharp preference must be G, never F##
    assert transpose_note("F#", 1, "sharp") == "G"

def test_no_c_flat():
    # C - 1 with flat preference must be B, never Cb
    assert transpose_note("C", -1, "flat") == "B"

def test_no_f_flat():
    # F - 1 with flat preference must be E, never Fb
    assert transpose_note("F", -1, "flat") == "E"


# ---------------------------------------------------------------------------
# Enharmonic preference
# ---------------------------------------------------------------------------

def test_flat_preference_a_sharp_to_bb():
    # A + 1 semitone with flat preference = Bb, not A#
    assert transpose_note("A", 1, "flat") == "Bb"

def test_sharp_preference_a_sharp():
    assert transpose_note("A", 1, "sharp") == "A#"

def test_target_key_bb_gives_flat():
    # A + 1 with target_key="Bb" -> Bb
    c = parse_chord("A")
    assert transpose_chord(c, 1, target_key="Bb") == "Bb"

def test_target_key_e_gives_sharp():
    # A + 1 with target_key="E" -> A# (sharp-preferred key)
    c = parse_chord("A")
    assert transpose_chord(c, 1, target_key="E") == "A#"

def test_target_key_f_gives_flat():
    c = parse_chord("A")
    assert transpose_chord(c, 1, target_key="F") == "Bb"

def test_target_key_fsharp_gives_sharp():
    # F# is sharp-preferred per spec (not in flat keys)
    c = parse_chord("A")
    assert transpose_chord(c, 1, target_key="F#") == "A#"


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
