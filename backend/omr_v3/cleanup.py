"""Repairs for systematic Audiveris artefacts on lead sheets, plus review flags.

Every repair here was introduced for an artefact seen on the evaluation sheets:

* phantom second voices made only of rests (the large "WCT" watermark on the
  WELOVE sheets is read as a whole-bar rest in voice 2);
* lyric junk: the copyright footer read as lyrics, and the U+2032 prime
  Audiveris appends to hyphenated syllables.

Nothing here guesses notes; questionable bars are only reported.
"""
from __future__ import annotations

import re
from fractions import Fraction

_HANGUL = re.compile(r'[가-힣]')
_FOOTER = re.compile(r'©|\(c\)|rights|reserved|copyright|creative|team', re.I)


def drop_rest_only_voices(score) -> int:
    """Remove secondary voices that contain nothing but rests. Returns voices removed."""
    from music21 import stream

    removed = 0
    for m in list(score.recurse().getElementsByClass(stream.Measure)):
        voices = list(m.voices)
        if len(voices) < 2:
            continue
        keep = [v for v in voices if any(not n.isRest for n in v.notesAndRests)]
        if not keep:
            keep = voices[:1]
        for v in voices:
            if v not in keep:
                m.remove(v)
                removed += 1
        if len(keep) == 1:
            m.flattenUnnecessaryVoices(inPlace=True)
    return removed


def clean_lyrics(score) -> int:
    """Drop footer/garbage lyrics and Audiveris' prime marks. Returns lyrics removed."""
    from music21 import note

    notes = [n for n in score.recurse().getElementsByClass(note.Note) if n.lyrics]
    texts = [ly.text or '' for n in notes for ly in n.lyrics]
    korean = sum(bool(_HANGUL.search(t)) for t in texts) > len(texts) / 2
    removed = 0
    for n in notes:
        kept = []
        for ly in n.lyrics:
            text = (ly.text or '').replace('′', '').strip()
            if not text or _FOOTER.search(text) or (korean and not _HANGUL.search(text)):
                removed += 1
                continue
            ly.text = text
            kept.append(ly)
        n.lyrics = kept
        for i, ly in enumerate(n.lyrics, 1):
            ly.number = i
    return removed


def measure_warnings(score) -> list[dict]:
    """Bars whose recognised content does not add up to the time signature."""
    from music21 import stream

    warnings: list[dict] = []
    for part in score.parts:
        measures = list(part.getElementsByClass(stream.Measure))
        for i, m in enumerate(measures):
            ts = m.getContextByClass('TimeSignature')
            if ts is None:
                continue
            expected = Fraction(ts.barDuration.quarterLength).limit_denominator(64)
            voices = list(m.voices) or [m]
            for v in voices:
                filled = sum((Fraction(n.quarterLength).limit_denominator(64) for n in v.notesAndRests), Fraction(0))
                if filled == expected or (i in (0, len(measures) - 1) and filled < expected):
                    continue
                warnings.append({'measure': m.number, 'index': i,
                                 'expected_quarters': float(expected), 'found_quarters': float(filled)})
                break
    return warnings


_NAVIGATION = re.compile(
    r'^(fine|coda|to\s*coda|d\.?\s?[sc]\.?(\s.*)?|al\s.*|bridge|chorus|verse.*|intro|outro|ending|'
    r'interlude|rit\.?.*|a\s?tempo|repeat.*)$', re.I)
_CHORD_LIKE = re.compile(r'^[A-G][#b♭♯]?[A-Za-z0-9()#b+/\-♭♯]{0,12}$')


def chord_words_to_symbols(score) -> dict:
    """Turn chord names that Audiveris exported as plain words into chord symbols.

    Left as text such a chord (``Bbadd2``, ``Am7/c``) is printed unchanged in a
    transposed score, i.e. silently wrong. Words that look like a chord but
    cannot be parsed are removed and reported instead of being kept.
    """
    from music21 import expressions

    from backend.chords.normalize import normalize_chord_text
    from backend.ocr.filter import is_chord_candidate

    from .chords import chord_symbol_from_text

    converted, dropped = 0, []
    for te in list(score.recurse().getElementsByClass(expressions.TextExpression)):
        raw = (te.content or '').strip().replace('♭', 'b').replace('♯', '#')
        if not raw or _NAVIGATION.match(raw) or not _CHORD_LIKE.match(raw):
            continue
        text = normalize_chord_text(re.sub(r'/([a-g])([#b]?)$', lambda m: '/' + m.group(1).upper() + m.group(2), raw))
        site, offset = te.activeSite, te.offset
        measure = te.getContextByClass('Measure')
        site.remove(te)
        if is_chord_candidate(text):
            site.insert(offset, chord_symbol_from_text(text))
            converted += 1
        else:
            dropped.append(getattr(measure, 'number', None))
    return {'converted': converted, 'dropped_unreadable': len(dropped), 'dropped_in_measures': dropped}


def strip_marks(score) -> dict:
    """Remove dynamics, articulations and fermatas.

    On the evaluation lead sheets every recognised dynamic/accent was a false
    positive (watermark strokes and lyric hyphens); real lead sheets rarely
    carry them. Set CAPOMATIC_OMR_KEEP_MARKS=1 to keep them.
    """
    import os

    from music21 import dynamics, expressions, note

    if os.environ.get('CAPOMATIC_OMR_KEEP_MARKS') == '1':
        return {'dynamics': 0, 'articulations': 0, 'fermatas': 0}
    dyn = 0
    for d in list(score.recurse().getElementsByClass(dynamics.Dynamic)):
        d.activeSite.remove(d)
        dyn += 1
    for part in score.parts:
        for sp in list(part.spannerBundle):
            if isinstance(sp, dynamics.DynamicWedge):
                part.remove(sp, recurse=True)
                dyn += 1
    arts = ferm = 0
    for n in score.recurse().getElementsByClass(note.GeneralNote):
        if n.articulations:
            arts += len(n.articulations)
            n.articulations = []
        kept = [e for e in n.expressions if not isinstance(e, expressions.Fermata)]
        ferm += len(n.expressions) - len(kept)
        n.expressions = kept
    return {'dynamics': dyn, 'articulations': arts, 'fermatas': ferm}


def _dark_ratio(pixels, width: int, y: int, x0: int, x1: int, dark: int = 128) -> float:
    x0, x1 = max(0, x0), min(width - 1, x1)
    if x1 < x0:
        return 0.0
    return sum(1 for x in range(x0, x1 + 1) if pixels[x, y] < dark) / (x1 - x0 + 1)


def _local_line_y(pixels, width: int, height: int, head, near: float, interline: float) -> float:
    """y of the staff line nearest *near*, measured just beside the head.

    The system's mean line positions can be several pixels off at a given x on
    a skewed raster, which is enough to mistake the staff line for a ledger.
    """
    w = max(4, int(head.w))
    x0, x1 = int(head.x - 2.5 * w), int(head.x - 1.2 * w)
    if x0 < 0:
        x0, x1 = int(head.x + head.w + 1.2 * w), int(head.x + head.w + 2.5 * w)
    rows = range(max(0, int(near - interline / 2)), min(height, int(near + interline / 2) + 1))
    best = max(rows, key=lambda y: _dark_ratio(pixels, width, y, x0, x1), default=None)
    return near if best is None else float(best)


def _has_ledger(pixels, width: int, height: int, head, line_ys) -> bool:
    """True when a ledger line lies one staff space outside the staff at this head.

    Audiveris marks the head at staff position +5/-5 (the space just outside
    the staff); a real ledger for +6/-6 is one interline beyond the outer staff
    line, measured locally, and crosses the head on both sides.
    """
    ys = sorted(line_ys)
    gaps = sorted(b - a for a, b in zip(ys, ys[1:]) if b > a)
    if not gaps:
        return False
    interline = gaps[len(gaps) // 2]
    centre = head.y + head.h / 2
    if head.pitch > 0:
        above = [ly for ly in ys if ly < centre]
        if not above:
            return False
        target = _local_line_y(pixels, width, height, head, above[-1], interline) + interline
    else:
        below = [ly for ly in ys if ly > centre]
        if not below:
            return False
        target = _local_line_y(pixels, width, height, head, below[0], interline) - interline
    reach = max(3, int(head.w * 0.2))
    left = (int(head.x) - reach, int(head.x) - 1)
    right = (int(head.x + head.w) + 1, int(head.x + head.w) + reach)
    tol = max(2, int(interline / 4))
    for y in range(max(0, int(target) - tol), min(height, int(target) + tol + 1)):
        if _dark_ratio(pixels, width, y, *left) >= 0.6 and _dark_ratio(pixels, width, y, *right) >= 0.6:
            return True
    return False


def fix_missed_ledgers(score, geometry, page_png) -> int:
    """Raise/lower notes Audiveris placed in the space next to a ledger it missed.

    On the evaluation sheets Audiveris read 5 of ~21 middle Cs (on a ledger
    line) as D4 where adjacent ledger segments ran together. A head at staff
    position +5/-5 (the space just outside the staff) that has a ledger line
    through its centre is really at +6/-6, so the note moves one step outward.
    """
    from music21 import note, stream
    from PIL import Image

    with Image.open(page_png) as im:
        gray = im.convert('L')
        if gray.size != (geometry.width, geometry.height):
            return 0
        pixels = gray.load()
        width, height = gray.size
        measures = list(score.parts[0].getElementsByClass(stream.Measure))
        fixed = 0
        for system in geometry.systems:
            for head in system.heads:
                if abs(head.pitch) != 5 or not _has_ledger(pixels, width, height, head, system.line_ys):
                    continue
                cx = head.x + head.w / 2
                stack = system.stack_at(cx)
                if stack is None or stack.index >= len(measures):
                    continue
                offset = stack.offset_at(cx, tolerance=head.w)
                m = measures[stack.index]
                for n in m.recurse().getElementsByClass(note.Note):
                    if Fraction(n.getOffsetInHierarchy(m)).limit_denominator(64) != offset:
                        continue
                    target = _outward(n, head.pitch)
                    if target is not None:
                        n.pitch = target
                        fixed += 1
                    break
        return fixed


def _outward(n, staff_position: int):
    """One diatonic step outward from the staff, if *n* sits in that outer space."""
    from music21 import pitch as m21pitch

    clef = n.getContextByClass('Clef')
    if clef is None or clef.sign != 'G' or clef.line != 2:
        return None
    # Treble clef: position +5 is D4 (below), -5 is G5 (above).
    expected = 'D4' if staff_position > 0 else 'G5'
    if n.pitch.step + str(n.pitch.octave) != expected:
        return None
    new = m21pitch.Pitch('C4' if staff_position > 0 else 'A5')
    # Keep the key-signature accidental the reader would apply to the new step.
    ks = n.getContextByClass('KeySignature')
    if ks is not None:
        new.accidental = ks.accidentalByStep(new.step)
    return new


_CREDIT_PEOPLE = re.compile(r'\bby\b|compos|words|music|lyric|arr\.|작사|작곡|편곡', re.I)


def normalize_layout(score) -> dict:
    """Let MuseScore lay the page out instead of replaying the scanned layout.

    Audiveris exports the original page geometry (system distances, credit
    coordinates). Rendered at a new size that produced a half-empty first page
    and stray credits such as "0" and old bar numbers. The title (largest
    credit) and composer line are kept as metadata; every other credit, all
    layout hints and above-staff words that are not navigation marks are dropped.
    """
    from music21 import expressions, layout, metadata, text

    removed = {'layout': 0, 'credits': 0, 'words': 0}
    for el in list(score.recurse().getElementsByClass(layout.LayoutBase)):
        el.activeSite.remove(el)
        removed['layout'] += 1
    boxes = [b for b in score.getElementsByClass(text.TextBox)]
    title = composer = None
    if boxes:
        def size(b):
            try:
                return float(b.style.fontSize or 0)
            except (TypeError, ValueError):
                return 0.0
        wordy = [b for b in boxes if re.search(r'[A-Za-z가-힣]{2,}', b.content or '')]
        if wordy:
            title = max(wordy, key=size).content.strip()
        people = [b.content.strip() for b in wordy if _CREDIT_PEOPLE.search(b.content or '') and b.content.strip() != title]
        composer = ' / '.join(people) or None
    for b in boxes:
        score.remove(b)
        removed['credits'] += 1
    if score.metadata is None:
        score.metadata = metadata.Metadata()
    if title and not (score.metadata.title or '').strip():
        score.metadata.title = title
    if composer:
        score.metadata.composer = composer
    # Audiveris sometimes files a chord label near the title as a composer credit;
    # it would be printed untransposed in the header.
    from backend.ocr.filter import is_chord_candidate

    names = list(score.metadata.composers)
    kept = [n for n in names if not is_chord_candidate(str(n).strip())]
    if len(kept) != len(names):
        score.metadata.composers = kept
        removed['credits'] += len(names) - len(kept)
    for te in list(score.recurse().getElementsByClass(expressions.TextExpression)):
        if not _NAVIGATION.match((te.content or '').strip()):
            te.activeSite.remove(te)
            removed['words'] += 1
    return removed
