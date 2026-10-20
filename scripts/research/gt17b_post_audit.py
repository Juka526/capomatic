"""Post-freeze semantic comparison only. Never changes a prediction or owner answer."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

from music21 import converter, harmony, note, stream
from backend.omr_v3.chords import chord_symbol_from_text, chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import events_of, read, require
from scripts.research.gt15b_confirmed_third_system import music_signature
from scripts.research.gt17_fifth_system import SOURCE_DIR, BASE
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

EXPECTED = {
    'Bb': {'A': 'A', 'G': 'G'},
    'F': {'A': 'E', 'G': 'D'},
    'Gm7': {'A': 'F#m7', 'G': 'Em7'},
    'Bb/D': {'A': 'A/C#', 'G': 'G/B'},
    'Eb': {'A': 'D', 'G': 'C'},
    'Gm': {'A': 'F#m', 'G': 'Em'},
}


def candidate_semantics(source, inventory):
    score = copy.deepcopy(source)
    ms = list(score.parts[0].getElementsByClass(stream.Measure))
    added = []
    for c in inventory['chords']:
        m = ms[c['measure'] - 1]
        existing = list(m.getElementsByClass(harmony.ChordSymbol))
        if existing:
            require(
                len(existing) == 1 and chord_text(existing[0]) == c['text'],
                'Candidate conflicts with recognized harmony',
            )
        else:
            m.insert(0, chord_symbol_from_text(c['text']))
            added.append(c['id'])
    for m in ms[19:]:
        for n in events_of(m):
            n.lyrics = []
    for l in inventory['lyrics']:
        m = ms[l['measure'] - 1]
        ns = [
            n for n in events_of(m) if Fraction(n.getOffsetInHierarchy(m)) == Fraction(l['onset'])
        ]
        require(len(ns) == 1 and ns[0].isNote, 'Ambiguous provisional lyric association')
        ns[0].lyrics.append(note.Lyric(text=l['text'], number=l['row']))
    require(
        music_signature(source) == music_signature(score),
        'Candidate text changed notes/rhythm/ties',
    )
    return score, added


def run(out):
    frozen = read(out / 'prediction-freeze.json')
    for n, h in frozen['files'].items():
        require(sha(out / n) == h, 'Frozen prediction changed: ' + n)
    dest = out / 'post-freeze-semantic-audit'
    require(not dest.exists(), 'Fresh semantic audit required')
    dest.mkdir()
    inv = read(out / 'full-source-event-inventory.json')
    source = converter.parse(str(out / 'owner-augmented-source.musicxml'))
    candidate, added = candidate_semantics(source, inv)
    candidate.write('musicxml', fp=str(dest / 'provisional-source.musicxml'))
    guards = {
        'provisional_source_roundtrip': validate(
            candidate, converter.parse(str(dest / 'provisional-source.musicxml')), 0, 'key'
        ).to_dict()
    }
    texts = []
    for target, shift in [('A', -1), ('G', -3)]:
        transposed = copy.deepcopy(candidate)
        summary = transpose_score(transposed, shift, 'key')
        transposed.write('musicxml', fp=str(dest / f'{target}-provisional-transposed.musicxml'))
        parsed = converter.parse(str(dest / f'{target}-provisional-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(candidate, transposed, shift, 'key', summary).to_dict(),
            'serialized': validate(candidate, parsed, shift, 'key', summary).to_dict(),
        }
        require(
            music_signature(parsed)
            == music_signature(converter.parse(str(out / f'{target}-transposed.musicxml'))),
            'Post-audit changed frozen musical events',
        )
        ms = list(parsed.parts[0].getElementsByClass(stream.Measure))
        for c in inv['chords']:
            chords = list(ms[c['measure'] - 1].getElementsByClass(harmony.ChordSymbol))
            texts.append(
                {
                    'target': target,
                    'source_candidate': c['id'],
                    'expected': EXPECTED[c['text']][target],
                    'actual': [chord_text(x) for x in chords],
                    'ok': len(chords) == 1 and chord_text(chords[0]) == EXPECTED[c['text']][target],
                }
            )
    comparison = []
    scores = {
        label: converter.parse(str(path))
        for label, path in [
            ('original_pre_ledger', SOURCE_DIR / 'pre-ledger.musicxml'),
            ('original_recognized', SOURCE_DIR / 'recognized.musicxml'),
            ('GT16B_owner_source', BASE / 'owner-augmented-source.musicxml'),
            ('GT17B_owner_source', out / 'owner-augmented-source.musicxml'),
        ]
    }
    for i in range(37):
        row = {'printed_measure': i + 1}
        for label, s in scores.items():
            m = list(s.parts[0].getElementsByClass(stream.Measure))[i]
            row[label] = {
                'event_count': len(events_of(m)),
                'harmony_text': [chord_text(c) for c in m.getElementsByClass(harmony.ChordSymbol)],
                'pitched_events': [
                    {
                        'onset': str(Fraction(n.getOffsetInHierarchy(m))),
                        'pitch': n.pitch.nameWithOctave,
                        'duration': str(Fraction(n.quarterLength)),
                    }
                    for n in events_of(m)
                    if n.isNote
                ],
            }
        row['independent_source_correctness'] = 'UNVERIFIED'
        comparison.append(row)
    ok = all(
        g['ok'] if 'ok' in g else all(x['ok'] for x in g.values()) for g in guards.values()
    ) and all(t['ok'] for t in texts)
    report = {
        'stage': 'POST_FREEZE_DIAGNOSTIC_NO_RENDER_OR_PREDICTION_CHANGE',
        'classification': 'PROVISIONAL_SEMANTIC_CANDIDATE_NOT_OWNER_VERIFIED_BEYOND19',
        'original_prediction_freeze_sha256': sha(out / 'prediction-freeze.json'),
        'new_harmony_candidates_added_only_to_diagnostic_source': added,
        'source_harmony_count': 24,
        'guards': guards,
        'all_guard_checks_pass': ok,
        'chord_correspondence': texts,
        'rendered_event_geometry_unchanged': True,
        'notes_rhythms_ties_unchanged': True,
        'new_source_verifications': 0,
        'independent_accuracy_denominator': None,
        'warning': 'Original frozen source/target MusicXML has16 harmonies and raw new-region OCR lyrics. Diagnostic candidate MusicXML has24 harmonies and79 agent-transcribed new syllables; this is not correction of frozen predictions or source truth.',
        'lyric_extender_serialization': {
            'rendered_marks': 50,
            'diagnostic_extend_elements': (dest / 'provisional-source.musicxml')
            .read_text()
            .count('<extend'),
            'status': 'INCOMPLETE_NOT_SOLVED_BY_VISUAL_DASHES',
        },
    }
    dump(dest / 'semantic-comparison.json', report)
    dump(dest / 'raw-recognized-owner-measure-comparison.json', comparison)
    dump(
        dest / 'audit-freeze.json',
        {'files': file_hashes(dest), 'producer_sha256': sha(Path(__file__))},
    )
    for n, h in frozen['files'].items():
        require(sha(out / n) == h, 'Post-audit modified frozen artifact: ' + n)
    print('Post-freeze semantic audit', ok, 'newly proposed harmonies', len(added))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    run(p.parse_args().output)
