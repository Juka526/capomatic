import re
from .types import Chord
from .normalize import normalize_chord_text

# [A-G] with optional # or b
_ROOT_RE = re.compile(r"^([A-G][#b]?)")

# Quality tokens — order matters: try "maj" before "m" to avoid short-circuiting.
# "m(?!aj)" ensures bare "m" is not consumed when "maj" follows.
_QUALITY_RE = re.compile(r"^(maj|m(?!aj)|dim|aug|sus)")

# Slash bass: last occurrence of /Note at end of string
_SLASH_RE = re.compile(r"/([A-G][#b]?)$")


def parse_chord(s: str) -> Chord:
    """Parse a chord string into a Chord dataclass.

    Raises ValueError if the root note cannot be parsed.
    """
    norm = normalize_chord_text(s)
    working = norm

    # --- slash bass ---
    bass: str | None = None
    m = _SLASH_RE.search(working)
    if m:
        bass = m.group(1)
        working = working[: m.start()]

    # --- root ---
    m = _ROOT_RE.match(working)
    if not m:
        raise ValueError(f"Cannot parse chord root from: {s!r} (normalized: {norm!r})")
    root = m.group(1)
    remaining = working[m.end() :]

    # Strip parentheses so "A(sus4)" and "Asus4" produce the same extensions.
    # "E7(sus4)" -> "E7sus4" after strip, preserving all content.
    # A numeric group after a number stays wrapped ("7(9)" is not "79").
    remaining = re.sub(
        r"(?<!\d)\(([^()]*)\)|\(((?!\d)[^()]*)\)",
        lambda m: m.group(1) if m.group(1) is not None else m.group(2),
        remaining,
    )

    # --- quality ---
    m = _QUALITY_RE.match(remaining)
    if m:
        quality = m.group(1)
        extensions = remaining[m.end() :]
    else:
        quality = ""
        extensions = remaining

    return Chord(
        root=root,
        quality=quality,
        extensions=extensions,
        bass=bass,
        original=norm,
    )
