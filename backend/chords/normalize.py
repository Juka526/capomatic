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
    # Case-fold OCR-mangled quality/modifier tokens (e.g. engraving fonts).
    # Applied before min→m so ordering is safe.
    s = re.sub(r"(?i)maj", "maj", s)   # mAj, MAj, MAJ → maj
    s = re.sub(r"(?i)dim", "dim", s)   # DIm, DIM, dIm → dim
    s = re.sub(r"(?i)sus", "sus", s)   # SUS, Sus       → sus
    s = re.sub(r"(?i)add", "add", s)   # ADD, Add       → add
    s = s.replace("min", "m")
    # Strip parentheses from simple suffix qualifiers so A7(sus4) == A7sus4.
    # Applied after case-folding so paren content is already lowercase.
    s = re.sub(r"\(([a-z0-9]+)\)", r"\1", s)
    return s