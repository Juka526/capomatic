"""One preregistered source-only OCR attempt. No renderer or Audiveris execution."""

import copy
import hashlib
import json
from pathlib import Path
import time


def run(source, out, expected):
    if out.exists() or source.resolve() in out.resolve().parents:
        raise ValueError('New output outside immutable source required')
    if set(expected) != {'source.png', 'audiveris.mxl', 'recognized.omr'}:
        raise ValueError('Exactly the preregistered Bb inputs required')
    if any(p.is_symlink() or not p.is_file() for p in source.iterdir()):
        raise ValueError('Plain source files only')
    actual = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()}
    if actual != expected:
        raise ValueError('Source-only input binding mismatch')
    # Imports intentionally occur after the caller has bound this offline environment.
    from music21 import converter, harmony, stream
    from backend.ocr.hybrid_detect import detect_chords_hybrid
    from backend.omr_v3 import cleanup
    from backend.omr_v3.chords import (
        align_ocr_chords,
        merge_chords,
        replace_chord_symbols,
        score_chords,
        chord_text,
    )
    from backend.omr_v3.geometry import load_geometry
    from backend.omr_v3.transpose import transpose_score
    from backend.omr_v3.music_guard import validate

    def dump(name, value):
        (out / name).write_text(
            json.dumps(
                value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False, default=str
            )
            + '\n'
        )

    def inventory(score):
        return [
            {
                'measure': str(m.number),
                'offset': str(c.getOffsetInHierarchy(m)),
                'text': chord_text(c),
                'kind': c.chordKind,
            }
            for m in score.parts[0].getElementsByClass(stream.Measure)
            for c in m.recurse().getElementsByClass(harmony.ChordSymbol)
        ]

    out.mkdir()
    started = time.monotonic()
    report = {
        'status': 'STARTED',
        'input_hashes': actual,
        'ocr_calls': 0,
        'musical_accuracy': None,
        'no_reference_inputs': True,
    }
    dump('run-report.json', report)
    try:
        report['ocr_calls'] = 1
        items, meta = detect_chords_hybrid(str(source / 'source.png'), use_ai_fallback=False)
        dump('ocr-items.json', items)
        dump('ocr-meta.json', meta)
        score = converter.parse(str(source / 'audiveris.mxl'))
        report['repairs'] = {
            'rest_only_voices_removed': cleanup.drop_rest_only_voices(score),
            'lyrics_removed': cleanup.clean_lyrics(score),
            'chord_words': cleanup.chord_words_to_symbols(score),
            'marks_removed': cleanup.strip_marks(score),
            'layout': cleanup.normalize_layout(score),
        }
        geometry = load_geometry(source / 'recognized.omr')
        measures = list(score.parts[0].getElementsByClass(stream.Measure))
        aligned = geometry.remap_to_measures(
            [m.measureNumberWithSuffix() for m in measures]
        ) or geometry.measure_count == len(measures)
        if not aligned:
            raise ValueError('Unchanged V3 alignment condition failed')
        report['repairs']['ledger_notes_fixed'] = cleanup.fix_missed_ledgers(
            score, geometry, source / 'source.png'
        )
        dump('audiveris-only-harmonies.json', inventory(score))
        placed = align_ocr_chords(items, geometry, report)
        placed, added = merge_chords(placed, score_chords(score))
        report['chords_from_audiveris'] = added
        report['chords_placed'] = replace_chord_symbols(score, placed)
        dump('ocr-assisted-harmonies.json', inventory(score))
        score.write('musicxml', fp=str(out / 'recognized.musicxml'))
        results = {}
        for label, shift in [('A', -1), ('G', -3)]:
            target = copy.deepcopy(score)
            summary = transpose_score(target, shift)
            memory = validate(score, target, shift, 'key', summary).to_dict()
            path = out / f'{label}-transposed.musicxml'
            target.write('musicxml', fp=str(path))
            serialized = validate(
                converter.parse(str(out / 'recognized.musicxml')),
                converter.parse(str(path)),
                shift,
                'key',
                summary,
            ).to_dict()
            results[label] = {
                'memory': memory,
                'serialized': serialized,
                'usable': memory['ok'] and serialized['ok'],
            }
        report['integrity'] = results
        report['status'] = (
            'COMPLETED' if all(r['usable'] for r in results.values()) else 'INTEGRITY_FAILURE'
        )
    except Exception as exc:
        report['status'] = 'FAILED_ATTEMPT'
        report['error_type'] = type(exc).__name__
        report['error'] = str(exc)
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic() - started
        dump('run-report.json', report)


if __name__ == '__main__':
    import sys

    run(Path(sys.argv[1]), Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text()))
