import re


def normalize_chord_text(s: str) -> str:
    """Normalize raw chord text to a canonical form suitable for parsing.

    Steps (in order):
    1. Strip leading/trailing whitespace.
    2. Replace Unicode accidentals (♯ ♭) with ASCII equivalents.
    3. Remove all internal whitespace ("A sus4" -> "Asus4").
    4. Replace "min" with "m" ("C#min7" -> "C#m7").
       "maj" and "dim" do not contain "min" so they are unaffected.
    """
    s = s.strip()
    s = s.replace("\u266f", "#").replace("\u266d", "b")  # ♯ → #, ♭ → b
    s = re.sub(r"\s+", "", s)
    s = s.replace("min", "m")
    return s