"""V4 offline-only integrity policy; the V3 production guard remains authoritative."""

from __future__ import annotations

import copy
import re

from backend.omr_v3 import music_guard

# Unknown wording, unreadable semantics and all non-chord failures stay fatal.
_CHORD_ISSUE = re.compile(
    r'bar [^:]+: (?:chord semantics changed at \S+|'
    r'chord (?:root|bass) moved wrongly at \S+|\d+ -> \d+ chord symbols)'
)


def classify_integrity(original, transposed, semitones: int) -> dict:
    """Run full and independently chord-free V3 guards for every part.

    The chord-free copies retain all notes/rests, rhythms, measures and keys.
    This second pass is required even when the full guard reports only chords:
    GuardReport caps its issue list, so a later note failure could be hidden.
    Nothing in this policy authorizes score rendering or changes either input.
    """
    from music21 import harmony, stream

    full_reports, note_reports, chord_issues, fatal_issues = [], [], [], []
    if not original.parts or len(original.parts) != len(transposed.parts):
        return {
            'overall': 'fail',
            'note_rhythm_key': 'fail',
            'chord': 'unknown',
            'chord_issues': [],
            'fatal_issues': ['missing parts or part count changed'],
            'full_guard': [],
            'note_rhythm_key_guard': [],
        }
    for index, (before, after) in enumerate(zip(original.parts, transposed.parts), 1):
        a = stream.Score([copy.deepcopy(before)])
        b = stream.Score([copy.deepcopy(after)])
        full = music_guard.validate(a, b, semitones, 'key')
        full_reports.append(full.to_dict())
        for issue in full.issues:
            destination = chord_issues if _CHORD_ISSUE.fullmatch(issue) else fatal_issues
            destination.append(f'part {index}: {issue}')
        if not full.ok and not full.issues:
            fatal_issues.append(f'part {index}: full guard failed without a diagnostic')
        for score in (a, b):
            for chord in list(score.recurse().getElementsByClass(harmony.ChordSymbol)):
                chord.activeSite.remove(chord)
        notes = music_guard.validate(a, b, semitones, 'key')
        note_reports.append(notes.to_dict())
        if not notes.ok:
            fatal_issues.extend(f'part {index}: {issue}' for issue in notes.issues)
            if not notes.issues:
                fatal_issues.append(
                    f'part {index}: note/rhythm/key guard failed without a diagnostic'
                )
    return {
        'overall': 'fail' if fatal_issues else 'warning' if chord_issues else 'pass',
        'note_rhythm_key': 'pass' if all(r['ok'] for r in note_reports) else 'fail',
        'chord': (
            'fail' if chord_issues else 'pass' if all(r['ok'] for r in full_reports) else 'unknown'
        ),
        'chord_issues': sorted(set(chord_issues)),
        'fatal_issues': sorted(set(fatal_issues)),
        'full_guard': full_reports,
        'note_rhythm_key_guard': note_reports,
    }
