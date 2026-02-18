from dataclasses import dataclass
from typing import Optional


@dataclass
class Chord:
    root: str           # e.g. "C#", "F", "Bb"
    quality: str        # one of "", "m", "maj", "dim", "aug", "sus"
    extensions: str     # everything after quality, e.g. "7", "maj7", "7sus4", "add9"
    bass: Optional[str] # e.g. "B" for G/B; None otherwise
    original: str       # normalized input string