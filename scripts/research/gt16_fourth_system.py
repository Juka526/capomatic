"""Source-only fourth-system audit and provisional expansion of frozen GT15B layers."""

import argparse
import copy
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import bar, converter, harmony, spanner, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.chords import chord_text, transpose_chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import FONT, events_of, read, require
from scripts.research.gt13a2_provisional import linked, ink_distance
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a4_header import header
from scripts.research.gt13a_full_system import scaffold
from scripts.research.gt13a5_lyric_layout import contacts, union
from scripts.research.gt13a6_tie_review import SOURCE_DIR, GT02
from scripts.research.gt14c_continuation_audit import dark_support_bbox, save_native
from scripts.research.gt15_third_system import render_music
from scripts.research.gt15b_confirmed_third_system import WITHHELD, music_signature
from scripts.research.gt12_render_context import text_mask
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt15b/gt15b-final-output')
GT15 = Path('/private/tmp/capomatic-v4-gt15/gt15-final-output')
PROTOCOL = ROOT / 'docs/V4_GT16_PROTOCOL.json'
TEXT = {
    13: {
        'chord': None,
        'upper': ['주', '의', '말'],
        'lower': ['주', '님', '의'],
        'upper_onsets': ['5/2', '3', '7/2'],
        'lower_onsets': ['5/2', '3', '7/2'],
    },
    14: {
        'chord': 'Gm7',
        'upper': ['씀', '은'],
        'lower': ['말', '씀'],
        'upper_onsets': ['1/2', '3/2'],
        'lower_onsets': ['1/2', '3/2'],
    },
    15: {
        'chord': 'Bb/D',
        'upper': ['영', '원', '하', '네'],
        'lower': [],
        'upper_onsets': ['3/2', '2', '5/2', '7/2'],
        'lower_onsets': [],
    },
    16: {'chord': 'Eb', 'upper': [], 'lower': [], 'upper_onsets': [], 'lower_onsets': []},
}


def measure_inventory(score, graph, rows, staff, numbers, candidates):
    """Bind persisted physical events to semantics without assigning source verification."""
    mm = list(score.parts[0].getElementsByClass(stream.Measure))
    records = []
    for number in numbers:
        measure = mm[number - 1]
        rr = sorted(
            [r for r in rows if r['omr_measure_index'] == number - 1],
            key=lambda r: Fraction(r['local_offset']),
        )
        ns = events_of(measure)
        require(len(rr) == len(ns), 'Unmatched event count')
        geometry = next(
            m
            for m in graph['measures']
            if m['system'] == staff['system'] and m['number'] == str(number)
        )
        events = []
        for r, n in zip(rr, ns):
            require(
                r['printed_measures'] == [number]
                and r['status'] == 'MATCHED'
                and Fraction(r['local_offset']) == Fraction(n.getOffsetInHierarchy(measure))
                and Fraction(r['duration']) == Fraction(n.quarterLength)
                and (n.isRest or r['pitch'] == n.pitch.nameWithOctave),
                'Ambiguous source registration',
            )
            sid = r['symbol_id']
            b = r['bbox']
            stems = linked(graph['relations'], 'head-stem', sid) if n.isNote else []
            rel = [
                v
                for v in graph['relations']
                if sid in (v['source'], v['target'])
                or any(s in (v['source'], v['target']) for s in stems)
            ]
            events.append(
                {
                    'id': r['id'],
                    'symbol_id': sid,
                    'printed_measure': number,
                    'onset': str(Fraction(n.getOffsetInHierarchy(measure))),
                    'duration': str(Fraction(n.quarterLength)),
                    'kind': 'NOTE' if n.isNote else 'REST',
                    'pitch': n.pitch.nameWithOctave if n.isNote else None,
                    'source_bbox': b,
                    'physical_source_center': [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2],
                    'voice': '1',
                    'stem_ids': stems,
                    'stem_direction': n.stemDirection if n.isNote else None,
                    'tie': getattr(n.tie, 'type', None),
                    'beams': (
                        [
                            {'number': v.number, 'type': v.type, 'direction': v.direction}
                            for v in n.beams
                        ]
                        if n.isNote
                        else []
                    ),
                    'articulations': [type(v).__name__ for v in n.articulations],
                    'expressions': [type(v).__name__ for v in n.expressions],
                    'accidental': (
                        n.pitch.accidental.name if n.isNote and n.pitch.accidental else None
                    ),
                    'omr_lyrics': [
                        {'row': l.number, 'text': l.text, 'syllabic': l.syllabic} for l in n.lyrics
                    ],
                    'source_symbol': graph['symbols'][sid],
                    'source_relations': rel,
                    'render_evidence': 'OMR_PROVISIONAL',
                    'source_verification': 'UNVERIFIED',
                }
            )
        require(sum(Fraction(e['duration']) for e in events) == 4, 'Measure duration mismatch')
        records.append(
            {
                'printed_measure': number,
                'omr_bounds': geometry['bounds'],
                'events': events,
                'source_measure_record': geometry,
                'recognized_harmonies': [
                    chord_text(c) for c in measure.getElementsByClass(harmony.ChordSymbol)
                ],
                'agent_candidates': candidates[number],
                'candidate_status': 'AGENT_VISUAL_CANDIDATE',
            }
        )
    return records


def inventory(score, graph, rows, source):
    staff = next(s for s in graph['staves'] if s['id'] == 'sheet#1:4')
    records = measure_inventory(score, graph, rows, staff, range(13, 17), TEXT)
    mm = list(score.parts[0].getElementsByClass(stream.Measure))
    marks = []
    for number, row, onset, x in [
        (14, 1, '0', 892),
        (14, 1, '1', 1065),
        (14, 1, '2', 1238),
        (14, 2, '0', 892),
        (14, 2, '2', 1238),
        (15, 1, '3', 1934),
        (16, 1, '0', 2138),
    ]:
        cy = 1655 if row == 1 else 1700
        box = [x - 24, cy - 9, x + 24, cy + 9]
        marks.append(
            {
                'id': f'm{number}-row{row}-stroke-{onset}',
                'printed_measure': number,
                'row': row,
                'onset_candidate': onset,
                'source_window': box,
                'diagnostic_dark_support_bbox': dark_support_bbox(source, box),
                'classification': 'AGENT_VISUAL_CANDIDATE',
                'owner_response': None,
                'rendered': False,
            }
        )
    symbols = [s for s in graph['symbols'].values() if s['system'] == staff['system']]
    return {
        'staff': staff,
        'measures': records,
        'recognized_events': sum(len(m['events']) for m in records),
        'source_sha256': sha(SOURCE_DIR / 'source.png'),
        'new_owner_verified_events': 0,
        'candidate_syllables': 14,
        'candidate_continuation_marks': marks,
        'candidate_chords': 3,
        'ambiguous_SIG_objects': [
            {
                'symbol': s,
                'relations': [
                    r for r in graph['relations'] if s['id'] in (r['source'], r['target'])
                ],
            }
            for s in symbols
            if s['kind'] in ('articulation', 'fermata')
        ],
        'notation_evidence': [
            s
            for s in symbols
            if s['kind']
            in (
                'beam',
                'beam-hook',
                'flag',
                'slur',
                'ending',
                'chord-name',
                'sentence',
                'word',
                'lyric-line',
                'lyric-item',
            )
        ],
        'source_relations': [
            r
            for r in graph['relations']
            if any(s['id'] in (r['source'], r['target']) for s in symbols)
        ],
        'repeat_context': {
            'brackets': [
                {'number': str(b.number), 'measures': [m.number for m in b.getSpannedElements()]}
                for b in score.recurse().getElementsByClass(spanner.RepeatBracket)
                if any(13 <= m.number <= 17 for m in b.getSpannedElements())
            ],
            'right_m16_barline': str(mm[15].rightBarline),
            'playback': 'UNRESOLVED_NOT_EXPANDED',
            'discrepancy': 'Ending5203 sentence relation targets4236/Eb, while leading source 1. is word4234 in Direction4233. Preserve both; source visual first-ending candidate, not repaired graph.',
        },
        'negative_observations': [
            'm14 lower onset1: no visible continuation dash candidate; do not mirror upper row',
            'm15/m16 lower: no new visible syllables or strokes; do not copy upper row',
            'No new section heading observed; printed13 is a measure-number candidate',
        ],
        'prior_withheld_SIG_ids': sorted(WITHHELD),
        'new_source_completeness': 'UNVERIFIED',
        'independent_ground_truth': False,
    }


def repeat_signature(score):
    """Only explicit repeat semantics; ordinary barline normalization is irrelevant."""
    bars = []
    for part_index, part in enumerate(score.parts):
        for m in part.getElementsByClass(stream.Measure):
            for side, b in [('left', m.leftBarline), ('right', m.rightBarline)]:
                if isinstance(b, bar.Repeat):
                    bars.append((part_index, m.number, side, b.direction, b.times))
    brackets = sorted(
        (str(b.number), tuple(m.number for m in b.getSpannedElements()))
        for b in score.recurse().getElementsByClass(spanner.RepeatBracket)
    )
    return {'repeat_bars': bars, 'ending_spans': brackets}


def ending(size, graph):
    raw = graph['symbols']['sheet#1:5203']
    xml = ET.fromstring(raw['source_xml'])
    mask = Image.new('L', size)
    d = ImageDraw.Draw(mask)
    for path in ['left-leg', 'line', 'right-leg']:
        el = xml.find(path)
        require(el is not None, 'Missing source ending geometry')
        pts = [(float(p.get('x')), float(p.get('y'))) for p in el]
        require(len(pts) == 2, 'Invalid ending line')
        d.line(pts, fill=255, width=2)
    # Join source corner gaps only at their persisted top coordinates, as GT14A.
    d.line([(1428.5, 1455), (1428.5, 1410), (2396, 1410), (2396, 1455)], fill=255, width=2)
    digit, info = text_mask(
        size,
        ImageFont.truetype(str(FONT), 40),
        '1.',
        left_top=graph['symbols']['sheet#1:4234']['geometry']['bbox'][:2],
    )
    num, _ = text_mask(
        size,
        ImageFont.truetype(str(FONT), 36),
        '13',
        left_top=graph['symbols']['sheet#1:4232']['geometry']['bbox'][:2],
    )
    return {
        'first-ending-bracket': mask,
        'first-ending-number': digit,
        'measure-number13': num,
    }, info


def panel(image, title):
    result = Image.new('RGB', (image.width, image.height + 180), 'white')
    d = ImageDraw.Draw(result)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    for n, t in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            'BLACK systems1-3 unchanged owner-confirmed scope; BLUE system4 = OMR_PROVISIONAL / not owner verified.',
            'System4: music + recognized Gm7 only; 2 additional chord candidates, 14 lyric syllables and 7 continuation marks WITHHELD.',
            '5 earlier and 5 new ambiguous SIG objects withheld; no source ink editing or original-pixel composition.',
        ]
    ):
        d.text((10, 8 + 30 * n), t, font=font, fill='black')
    result.paste(image, (0, 180))
    return result


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    protocol = read(PROTOCOL)
    require(
        sha(FONT) == read(ROOT / 'docs/V4_GT15B_PROTOCOL.json')['font_sha256'],
        'Pinned notation font changed',
    )
    size = tuple(protocol['size'])
    view = protocol['fourth_view']
    binding = read(ROOT / 'docs/V4_GT15B_VALIDATION.json')
    for n, h in binding['artifact_sha256'].items():
        require(sha(PRIOR / n) == h, 'GT15B binding changed: ' + n)
    for n, h in read(PRIOR / 'prediction-freeze.json')['files'].items():
        require(sha(PRIOR / n) == h, 'GT15B freeze changed: ' + n)
    frozen = read(PRIOR / 'pre-render-freeze.json')
    for name, key in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(
            sha(SOURCE_DIR / name) == frozen['source_input_hashes'][key],
            'Original source provenance changed',
        )
    history = {str(p): file_hashes(p) for p in (PRIOR, GT15)}
    original = Image.open(SOURCE_DIR / 'source.png')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    source = converter.parse(str(PRIOR / 'owner-augmented-source.musicxml'))
    rows = read(GT02 / 'note-correspondence-diagnostic.json')['events']['Bb']
    inv = inventory(source, graph, rows, original)
    require(inv['recognized_events'] == 18, 'Fixed event count mismatch')
    out.mkdir()
    dump(out / 'source-event-inventory.json', inv)
    crop_map = [save_native(original, view, out / 'source-fourth-system-review-sheet.png')]
    for m in inv['measures']:
        bounds = m['omr_bounds']
        box = [max(130, int(bounds[0]) - 15), 1395, min(2430, int(bounds[2]) + 15), 1740]
        crop_map.append(
            save_native(original, box, out / f'source-measure-{m["printed_measure"]}.png')
        )
    for r in inv['candidate_continuation_marks']:
        crop_map.append(save_native(original, r['source_window'], out / (r['id'] + '.png')))
    for r in inv['ambiguous_SIG_objects']:
        s = r['symbol']
        b = s['geometry']['bbox']
        box = [int(b[0]) - 35, int(b[1]) - 35, int(b[2]) + 35, int(b[3]) + 35]
        crop_map.append(save_native(original, box, out / f'source-ambiguous-{s["source_id"]}.png'))
    dump(out / 'source-crop-map.json', crop_map)
    checklist = {
        'classification': 'OWNER_REVIEW_PENDING_NOT_INDEPENDENT_GROUND_TRUTH',
        'source_sha256': inv['source_sha256'],
        'source_review_image_sha256': sha(out / 'source-fourth-system-review-sheet.png'),
        'measures': [
            {
                'printed_measure': m['printed_measure'],
                'events': m['events'],
                'text_candidates': m['agent_candidates'],
                'recognized_harmonies': m['recognized_harmonies'],
                'music_answer': None,
                'chord_answer': None,
                'lyrics_answer': None,
                'association_answer': None,
                'additional_or_missing_symbols': None,
            }
            for m in inv['measures']
        ],
        'continuation_candidates': inv['candidate_continuation_marks'],
        'ambiguous_SIG_objects': [
            dict(r, owner_response=None) for r in inv['ambiguous_SIG_objects']
        ],
        'repeat_context': inv['repeat_context'],
        'repeat_answer': None,
        'negative_observation_answers': None,
        'new_owner_confirmations': 0,
    }
    dump(out / 'owner-review-checklist.json', checklist)
    dump(
        out / 'input-freeze.json',
        {
            'history_files': history,
            'source_sha256': sha(SOURCE_DIR / 'source.png'),
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
            'music_renderer_sha256': sha(ROOT / 'scripts/research/gt15_third_system.py'),
        },
    )
    # Reproduce historical primitives in new temporary memory, never rewrite frozen files.
    regression = []
    for target in ['A', 'G']:
        pastscore = converter.parse(str(GT15 / f'{target}-semantic.musicxml'))
        oldparts, _ = render_music(
            read(GT15 / 'source-event-inventory.json'), pastscore, target, graph
        )
        for name, p in oldparts.items():
            ref = Image.open(GT15 / f'{target}-{name.replace(":","_")}-alpha.png')
            require(
                p.mode == ref.mode and p.size == ref.size and p.tobytes() == ref.tobytes(),
                'Historical rendering byte regression: ' + name,
            )
        regression.append({'target': target, 'component_masks_byte_identical': len(oldparts)})
    dump(out / 'historical-renderer-regression.json', regression)
    sourceguard = validate(
        source, converter.parse(str(PRIOR / 'owner-augmented-source.musicxml')), 0, 'key'
    ).to_dict()
    guards = {'source_roundtrip': sourceguard}
    reports = []
    repeat_reports = []
    images = []
    for target, shift in [('A', -1), ('G', -3)]:
        score = copy.deepcopy(source)
        summary = transpose_score(score, shift, 'key')
        score.write('musicxml', fp=str(out / f'{target}-semantic.musicxml'))
        parsed = converter.parse(str(out / f'{target}-semantic.musicxml'))
        old = converter.parse(str(PRIOR / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(source, score, shift, 'key', summary).to_dict(),
            'serialized': validate(source, parsed, shift, 'key', summary).to_dict(),
        }
        require(
            all(g['ok'] for g in guards[target].values())
            and music_signature(parsed) == music_signature(old)
            and full_lyric_signature(source) == full_lyric_signature(parsed),
            'Unchanged full V3 guard/signature failed',
        )
        require(
            repeat_signature(source)
            == repeat_signature(score)
            == repeat_signature(parsed)
            == repeat_signature(old),
            'Repeat/ending preservation failure',
        )
        repeat_reports.append(
            {
                'target': target,
                'signature': repeat_signature(parsed),
                'unchanged': True,
                'new_playback_interpretation_authorized': False,
            }
        )
        parts, metrics = render_music(inv, score, target, graph, size=size, viewport=view)
        require(
            not metrics['unexpected_intersections']
            and not metrics['missing_connections']
            and not metrics['clipping'],
            'Music collision/attachment/clipping failure',
        )
        hp, _ = header(size, inv['staff'], target, FONT)
        context = {n: p for n, p in hp.items() if n == 'clef' or n.startswith('sharp')}
        endingparts, _ = ending(size, graph)
        context.update(endingparts)
        music = union(list(parts.values()))
        actual = contacts({**parts, **context})
        unexpected = [h for h in actual if h['a'] in context or h['b'] in context]
        require(not unexpected, 'Context/music collision')
        cs = list(
            list(parsed.parts[0].getElementsByClass(stream.Measure))[13].getElementsByClass(
                harmony.ChordSymbol
            )
        )
        text = transpose_chord_text('Gm7', shift, original_key='Bb', target_key=target)
        require(len(cs) == 1 and chord_text(cs[0]) == text, 'Recognized chord semantics mismatch')
        chord, ci = text_mask(size, ImageFont.truetype(str(FONT), 40), text, left_top=(860, 1421))
        context['provisional-chord-m14'] = chord
        chordcontacts = int(
            np.count_nonzero(
                (np.asarray(chord) > 0)
                & (
                    np.asarray(
                        union(
                            [
                                music,
                                *[p for n, p in context.items() if n != 'provisional-chord-m14'],
                            ]
                        )
                    )
                    > 0
                )
            )
        )
        require(chordcontacts == 0, 'Provisional chord collision')
        context['staff-and-bars'] = scaffold(
            size,
            inv['staff'],
            [851, 1427, 2093, 2400],
            {2400: graph['symbols']['sheet#1:80']['geometry']['bbox']},
        )
        fourth = union([music, *context.values()])
        require(
            not np.asarray(fourth)[:1408].any(), 'New notation enters old three-system viewport'
        )
        prior = Image.open(PRIOR / f'{target}-combined-alpha.png')
        base = Image.new('L', size)
        base.paste(prior, (0, 0))
        require(
            not np.any((np.asarray(fourth) > 0) & (np.asarray(base) > 0)),
            'Old/new system alpha collision',
        )
        combined = union([base, fourth])
        require(
            combined.crop((0, 0, size[0], 1408)).tobytes()
            == base.crop((0, 0, size[0], 1408)).tobytes(),
            'Old body alpha changed',
        )
        canvas = Image.composite(
            Image.new('RGB', size, 'black'), Image.new('RGB', size, 'white'), base
        )
        canvas = Image.composite(Image.new('RGB', size, '#3057a0'), canvas, fourth)
        img = panel(
            canvas.crop(protocol['integrated_view']),
            f'{target} major / printed1-16 / 59 confirmed + 18 provisional event cores',
        )
        historical = Image.open(PRIOR / f'{target}-three-systems.png')
        require(
            img.crop((0, 180, img.width, 1278)).tobytes()
            == historical.crop((0, 180, historical.width, historical.height)).tobytes(),
            'First-three-system RGB body changed',
        )
        img.save(out / f'{target}-four-systems.png')
        shown = panel(
            canvas.crop(view), f'{target} major system4 / printed13-16 / 18 OMR_PROVISIONAL events'
        )
        shown.save(out / f'{target}-fourth-system.png')
        images.append(shown)
        combined.save(out / f'{target}-combined-alpha.png')
        fourth.save(out / f'{target}-fourth-alpha.png')
        for n, p in {**parts, **context}.items():
            p.save(out / f'{target}-{n.replace(":","_")}-alpha.png')
        metrics.update(
            {
                'target': target,
                'old_three_system_RGB_body_byte_identical': True,
                'old_confirmed_events': 59,
                'new_confirmed_events': 0,
                'total_displayed_event_cores': 77,
                'old_confirmed_chords': 7,
                'new_provisional_chords': 1,
                'new_chord_text': text,
                'chord_metrics': ci,
                'old_confirmed_syllables': 70,
                'old_continuation_marks': 21,
                'new_syllables_rendered': 0,
                'new_continuation_marks_rendered': 0,
                'new_lyric_music_safety': 'NOT_EVALUABLE_NEW_LYRICS_WITHHELD',
                'old_new_system_contact_pixels': 0,
                'new_chord_contacts': chordcontacts,
                'context_contact_pairs': unexpected,
                'prior_withheld_ids': sorted(WITHHELD),
                'new_ambiguous_SIG_objects': len(inv['ambiguous_SIG_objects']),
                'source_verification': 'OMR_PROVISIONAL_OWNER_PENDING',
                'visual_quality': 'PENDING_POST_FREEZE_AGENT_REVIEW',
                'status': 'FOUR_SYSTEM_PREVIEW_INCOMPLETE_PROVISIONAL_FOURTH_SYSTEM',
            }
        )
        reports.append(metrics)
    orig = panel(
        original.crop(view),
        'Unchanged original Bb fourth-system source evidence; no A/G reference pages',
    )
    orig.save(out / 'original-fourth-system.png')
    contact = Image.new('RGB', (orig.width, orig.height * 3), 'white')
    for n, im in enumerate([orig, *images]):
        contact.paste(im, (0, n * orig.height))
    contact.save(out / 'fourth-system-comparison.png')
    require(sourceguard['ok'], 'Source full guard failed')
    dump(out / 'rendering-validation.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    dump(out / 'repeat-preservation.json', repeat_reports)
    require(
        all(file_hashes(Path(p)) == h for p, h in history.items())
        and sha(SOURCE_DIR / 'source.png') == protocol['source_sha256'],
        'Historical/source mutation',
    )
    dump(
        out / 'preservation-verification.json',
        {
            'all_history_hashes_unchanged': True,
            'source_unchanged': True,
            'GT15B_three_system_body_byte_identical': True,
            'prior_five_SIG_still_withheld': True,
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'phase': 'BEFORE_AGENT_VISUAL_INSPECTION_NO_TARGET_REFERENCE_ACCESS',
        },
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
