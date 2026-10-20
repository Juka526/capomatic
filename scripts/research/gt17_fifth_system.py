"""Source-only fifth-system packet and provisional generated notation; no source editing."""

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from music21 import converter, harmony, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from backend.omr_v3.chords import chord_text
from scripts.research.gt11_complete_measure import FONT, read, require
from scripts.research.gt12_render_context import text_mask
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a4_header import header
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a_full_system import scaffold
from scripts.research.gt13a5_lyric_layout import contacts, union
from scripts.research.gt13a6_tie_rendering import calibrated_whole_head
from scripts.research.gt14c_continuation_audit import dark_support_bbox, save_native
from scripts.research.gt15_third_system import render_music
from scripts.research.gt15b_confirmed_third_system import music_signature
from scripts.research.gt16_fourth_system import (
    measure_inventory,
    repeat_signature,
    SOURCE_DIR,
    GT02,
)
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = '4da717a8e8675db84ea6a6b941bec3d4dacc86a5'
BASE = Path('/private/tmp/capomatic-v4-gt16b/gt16b-final-output')
OPTICAL = Path('/private/tmp/capomatic-v4-gt16c/gt16c-final-output')
SIZE = (2520, 2110)
VIEW = (130, 1740, 2430, 2050)
INTEGRATED = (130, 310, 2430, 2050)
WARNING = 'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE — INCOMPLETE — NOT FOR PERFORMANCE OR PRINTING'
WITHHELD = [5833, 5841, 5896, 5902, 5903, 5927, 5948, 5949, 5975, 5984]
CANDIDATES = {
    17: {
        'chord': 'Bb/D',
        'upper': ['이', '루', '시', '네'],
        'lower': [],
        'upper_onsets': ['3/2', '2', '5/2', '7/2'],
        'lower_onsets': [],
    },
    18: {'chord': 'Eb', 'upper': [], 'lower': [], 'upper_onsets': [], 'lower_onsets': []},
    19: {'chord': None, 'upper': [], 'lower': [], 'upper_onsets': [], 'lower_onsets': []},
}


def inventory(score, graph, rows, source):
    staff = next(s for s in graph['staves'] if s['id'] == 'sheet#1:5')
    records = measure_inventory(score, graph, rows, staff, range(17, 20), CANDIDATES)
    symbols = [s for s in graph['symbols'].values() if s['system'] == staff['system']]
    ids = {s['id'] for s in symbols}
    relations = [r for r in graph['relations'] if ids.intersection((r['source'], r['target']))]
    marks = []
    for sid, measure, syllable, onset in [('5999', 17, '시', '3'), ('6001', 18, '네', '0')]:
        s = graph['symbols']['sheet#1:' + sid]
        b = s['geometry']['bbox']
        window = [int(b[0]) - 8, int(b[1]) - 8, int(b[2]) + 8, int(b[3]) + 8]
        marks.append(
            {
                'id': 'GT17-stroke-' + sid,
                'measure': measure,
                'row': 1,
                'associated_syllable_candidate': syllable,
                'onset': onset,
                'source_window': window,
                'source_object_bbox': b,
                'diagnostic_dark_bbox': dark_support_bbox(source, window),
                'original_omr_shape': s['shape'],
                'symbol_id': s['id'],
                'classification': 'AGENT_VISUAL_CANDIDATE',
                'owner_answer': None,
                'rendered': False,
            }
        )
    lyric_candidates = []
    for text, onset, sid, window in [
        ('이', '3/2', '4274', [635, 1950, 682, 2000]),
        ('루', '2', '4272', [777, 1950, 826, 2000]),
        ('시', '5/2', '4275', [920, 1950, 965, 2000]),
        ('네', '7/2', None, [1210, 1950, 1257, 2000]),
    ]:
        lyric_candidates.append(
            {
                'text': text,
                'measure': 17,
                'row': 1,
                'onset_candidate': onset,
                'symbol_id': ('sheet#1:' + sid) if sid else None,
                'source_window': window,
                'diagnostic_dark_bbox': dark_support_bbox(source, window),
                'classification': 'AGENT_VISUAL_CANDIDATE',
                'owner_answer': None,
                'note': 'Word 루 is not a lyric-item; 네 lacks persisted lyric support; no automatic MusicXML repair',
            }
        )
    return {
        'staff': staff,
        'lyric_candidates': lyric_candidates,
        'measures': records,
        'recognized_events': sum(len(m['events']) for m in records),
        'ambiguous_SIG_objects': [s for s in symbols if s['kind'] in ('articulation', 'fermata')],
        'source_symbols': symbols,
        'source_relations': relations,
        'continuation_candidates': marks,
        'prior_withheld_SIG_ids': WITHHELD,
        'source_verification': 'UNVERIFIED',
        'new_owner_verified_events': 0,
        'independent_ground_truth_count': 0,
        'row_census': {
            'upper': '4 syllable and 2 stroke candidates',
            'lower': 'No visible second row in fifth-system crop; NOT copied from upper',
        },
        'negative_observations': [
            'm19 no newly printed chord/lyric candidate',
            'No new section label inside fifth system; Chorus below belongs to system6',
        ],
        'repeat_context': {
            'source_id': 'sheet#1:5195',
            'numeral_id': 'sheet#1:4269',
            'span_candidate': [17],
            'left_x': 276.4,
            'right_x': 1358,
            'right_leg': None,
            'classification': 'OMR_PROVISIONAL',
            'earlier_first_ending': [15, 16],
            'visible_notation': 'Open-right second-ending bracket; ordinary thin right barlines in m17-19',
            'playback_route': 'UNRESOLVED_NO_OWNER_APPROVAL_NO_JUMPS_ADDED',
            'graph_caveat': '5195 has ending-bar links to4597/4598 but no ending-sentence link. Numeral2. and Bb/D are words in shared sentence4268; Bb/D not exported as harmony.',
        },
    }


def second_ending(size, graph):
    raw = ET.fromstring(graph['symbols']['sheet#1:5195']['source_xml'])

    def xy(path):
        q = raw.find(path)
        require(q is not None, 'Missing second-ending geometry')
        return float(q.get('x')), float(q.get('y'))

    require(raw.find('right-leg') is None, 'Unexpected closed ending')
    p = Image.new('L', size)
    points = [xy('left-leg/p2'), xy('left-leg/p1'), xy('line/p1'), xy('line/p2')]
    ImageDraw.Draw(p).line(points, fill=255, width=2)
    number = graph['symbols']['sheet#1:4269']
    require(ET.fromstring(number['source_xml']).get('value') == '2.', 'Numeral mismatch')
    b = number['geometry']['bbox']
    num, info = text_mask(size, ImageFont.truetype(str(FONT), 40), '2.', left_top=b[:2])
    return {'ending2': p, 'ending2-number': num}, {'path': points, 'number': info}


def panel(image, title):
    result = Image.new('RGB', (image.width, image.height + 130), 'white')
    d = ImageDraw.Draw(result)
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    for i, text in enumerate(
        [
            WARNING,
            title,
            'Systems1-4: frozen GT16C layout; BLUE system5: OMR_PROVISIONAL, NOT owner verified.',
            'System5 lyrics/extenders and Bb/D candidate WITHHELD; recognized Eb transposed provisionally.',
            'Text/music safety NOT EVALUABLE; ambiguous SIG5999/6001 and repeat playback unresolved.',
        ]
    ):
        d.text((10, 5 + 25 * i), text, font=f, fill='black')
    result.paste(image, (0, 130))
    return result


def run(out):
    require(not out.exists(), 'Fresh output directory required')
    bindings = {}
    for folder, doc in [(BASE, 'V4_GT16B_VALIDATION.json'), (OPTICAL, 'V4_GT16C_VALIDATION.json')]:
        for n, h in read(ROOT / 'docs' / doc)['artifact_sha256'].items():
            require(sha(folder / n) == h, 'Historical document binding mismatch: ' + n)
        for n, h in read(folder / 'prediction-freeze.json')['files'].items():
            require(sha(folder / n) == h, 'Historical freeze mismatch: ' + n)
        bindings[str(folder)] = file_hashes(folder)
    source_binding = read(BASE / 'pre-render-freeze.json')['source_input_hashes']
    for n, k in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / n) == source_binding[k], 'Source mismatch: ' + n)
    require(sha(FONT) == read(ROOT / 'docs/V4_GT15B_PROTOCOL.json')['font_sha256'], 'Font changed')
    source = Image.open(SOURCE_DIR / 'source.png')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    score = converter.parse(str(BASE / 'owner-augmented-source.musicxml'))
    inv = inventory(
        score, graph, read(GT02 / 'note-correspondence-diagnostic.json')['events']['Bb'], source
    )
    require(inv['recognized_events'] == 9, 'Unexpected fixed scope')
    out.mkdir()
    dump(out / 'source-fifth-system-inventory.json', inv)
    crops = [save_native(source, list(VIEW), out / 'source-fifth-system-review-sheet.png')]
    for m in inv['measures']:
        b = m['omr_bounds']
        crops.append(
            save_native(
                source,
                [max(130, int(b[0]) - 10), 1740, min(2430, int(b[2]) + 10), 2050],
                out / f'source-m{m["printed_measure"]}.png',
            )
        )
    for r in inv['continuation_candidates']:
        crops.append(save_native(source, r['source_window'], out / (r['id'] + '.png')))
    crops.append(
        save_native(source, [2060, 1395, 2430, 1930], out / 'source-ending-transition.png')
    )
    dump(out / 'source-crop-map.json', crops)
    checklist = {
        'classification': 'OWNER_REVIEW_PENDING_NOT_INDEPENDENT_GROUND_TRUTH',
        'source_hashes': source_binding,
        'review_sheet_sha256': sha(out / 'source-fifth-system-review-sheet.png'),
        'measures': [
            dict(
                m,
                events=[dict(e, owner_answer=None) for e in m['events']],
                music_answer=None,
                chord_answer=None,
                lyric_answer=None,
                association_answer=None,
                missing_symbol_answer=None,
            )
            for m in inv['measures']
        ],
        'continuation_candidates': inv['continuation_candidates'],
        'ambiguous_objects': [dict(s, owner_answer=None) for s in inv['ambiguous_SIG_objects']],
        'ending_context': inv['repeat_context'],
        'ending_answer': None,
        'lyric_candidates': inv['lyric_candidates'],
        'beam_flag_tie_answers': [
            dict(s, owner_answer=None)
            for s in inv['source_symbols']
            if s['kind'] in ('beam', 'beam-hook', 'flag', 'slur')
        ],
        'lower_row_absence_answer': None,
        'new_owner_approvals': 0,
    }
    dump(out / 'owner-review-checklist.json', checklist)
    dump(
        out / 'source-inventory-freeze.json',
        {
            'files': file_hashes(out),
            'source_hashes': source_binding,
            'producer_sha256': sha(Path(__file__)),
            'renderer_sha256': sha(ROOT / 'scripts/research/gt15_third_system.py'),
            'layout_approval': read(ROOT / 'docs/V4_GT17_PROTOCOL.json')['layout_approval'],
        },
    )
    guards = {
        'source_roundtrip': validate(
            score, converter.parse(str(BASE / 'owner-augmented-source.musicxml')), 0, 'key'
        ).to_dict()
    }
    reports = []
    originals = panel(source.crop(VIEW), 'ORIGINAL Bb source only / printed17-19')
    originals.save(out / 'original-fifth-system.png')
    pictures = [originals]
    for target, shift in [('A', -1), ('G', -3)]:
        transposed = copy.deepcopy(score)
        summary = transpose_score(transposed, shift, 'key')
        transposed.write('musicxml', fp=str(out / f'{target}-semantic.musicxml'))
        parsed = converter.parse(str(out / f'{target}-semantic.musicxml'))
        old = converter.parse(str(OPTICAL / f'{target}-semantic.musicxml'))
        guards[target] = {
            'in_memory': validate(score, transposed, shift, 'key', summary).to_dict(),
            'serialized': validate(score, parsed, shift, 'key', summary).to_dict(),
        }
        require(all(g['ok'] for g in guards[target].values()), 'Full unchanged guard failed')
        require(music_signature(parsed) == music_signature(old), 'Historical pitch/rhythm changed')
        require(
            full_lyric_signature(score) == full_lyric_signature(parsed), 'Semantic lyrics changed'
        )
        require(
            repeat_signature(score) == repeat_signature(parsed) == repeat_signature(old),
            'Repeat signature changed',
        )
        parts, report = render_music(
            inv,
            transposed,
            target,
            graph,
            size=SIZE,
            viewport=VIEW,
            whole_note_renderer=calibrated_whole_head,
        )
        require(
            not report['unexpected_intersections']
            and not report['missing_connections']
            and not report['clipping'],
            'Music geometry failure',
        )
        hp, hm = header(SIZE, inv['staff'], target, FONT)
        context = {k: v for k, v in hp.items() if k == 'clef' or k.startswith('sharp')}
        ep, em = second_ending(SIZE, graph)
        context.update(ep)
        # Only the persisted m18 harmony is rendered. m17 Bb/D remains a review candidate.
        cs = list(
            list(parsed.parts[0].getElementsByClass(stream.Measure))[17].getElementsByClass(
                harmony.ChordSymbol
            )
        )
        require(
            len(cs) == 1 and chord_text(cs[0]) == ('D' if target == 'A' else 'C'),
            'Provisional Eb transposition mismatch',
        )
        context['provisional-chord-m18'], cm = text_mask(
            SIZE, ImageFont.truetype(str(FONT), 40), chord_text(cs[0]), left_top=(1383, 1770)
        )
        bad = [c for c in contacts({**parts, **context}) if c['a'] in context or c['b'] in context]
        require(not bad, 'Header/chord/ending contact')
        context['staff-bars'] = scaffold(
            SIZE,
            inv['staff'],
            [159, 1361, 1851, 2400],
            {2400: graph['symbols']['sheet#1:92']['geometry']['bbox']},
        )
        fifth = union([*parts.values(), *context.values()])
        require(
            fifth.getbbox()[0] >= VIEW[0]
            and fifth.getbbox()[1] >= VIEW[1]
            and fifth.getbbox()[2] <= VIEW[2]
            and fifth.getbbox()[3] <= VIEW[3],
            'Fifth viewport clipping',
        )
        oldmask = Image.open(OPTICAL / f'{target}-refined-alpha.png')
        base = Image.new('L', SIZE)
        base.paste(oldmask, (0, 0))
        require(not np.any((np.asarray(base) > 0) & (np.asarray(fifth) > 0)), 'System overlap')
        combined = union([base, fifth])
        require(
            np.array_equal(
                np.asarray(combined)[np.asarray(base) > 0], np.asarray(base)[np.asarray(base) > 0]
            ),
            'Historical ink changed',
        )
        fifth.save(out / f'{target}-fifth-alpha.png')
        combined.save(out / f'{target}-five-alpha.png')
        for name, p in parts.items():
            p.save(out / f'{target}-{name.replace(":","_")}-alpha.png')
        canvas = Image.composite(
            Image.new('RGB', SIZE, 'black'), Image.new('RGB', SIZE, 'white'), base
        )
        canvas = Image.composite(Image.new('RGB', SIZE, '#3057a0'), canvas, fifth)
        pic = panel(
            canvas.crop(VIEW),
            f'{target} major fifth system / printed17-19 / 9 provisional note-rest cores',
        )
        pic.save(out / f'{target}-fifth-system-provisional.png')
        pictures.append(pic)
        panel(
            canvas.crop(INTEGRATED),
            f'{target} major printed1-19 / 77 confirmed +9 provisional event cores',
        ).save(out / f'{target}-five-systems.png')
        report.update(
            fifth_lyric_music_contacts='NOT_EVALUABLE_LYRICS_WITHHELD',
            new_chords_rendered=1,
            new_chord_evidence='OMR_PROVISIONAL',
            header=hm,
            ending=em,
            chord=cm,
            context_unexpected_contacts=bad,
            historical_layer_sha256=sha(OPTICAL / f'{target}-refined-alpha.png'),
            historical_scope={
                'events': 77,
                'chords': 10,
                'syllables': 84,
                'continuation_marks': 28,
            },
            old_ink_unchanged=True,
            old_new_alpha_contacts=0,
            old_new_min_ink_center_distance_px=float(
                ink_distance(base)[np.asarray(fifth) > 0].min()
            ),
            canvas_size=SIZE,
            fifth_view=VIEW,
        )
        reports.append(report)
    require(guards['source_roundtrip']['ok'], 'Source roundtrip failed')
    dump(
        out / 'semantic-integrity.json',
        {
            'guards': guards,
            'repeat_route': 'UNRESOLVED_UNCHANGED',
            'whole_score_events': 169,
            'independent_accuracy_denominator': None,
        },
    )
    sheet = Image.new(
        'RGB', (max(p.width for p in pictures), sum(p.height for p in pictures)), 'white'
    )
    y = 0
    for p in pictures:
        sheet.paste(p, (0, y))
        y += p.height
    sheet.save(out / 'Bb-A-G-fifth-system-comparison.png')
    dump(out / 'rendering-validation.json', reports)
    preservation = {
        str(p): file_hashes(p) == before
        for p, before in [(Path(k), v) for k, v in bindings.items()]
    }
    require(all(preservation.values()), 'Frozen baseline modified')
    for n, k in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / n) == source_binding[k], 'Source changed during run')
    dump(
        out / 'preservation-verification.json',
        {
            'all_historical_files_unchanged': preservation,
            'source_hashes_unchanged': {
                n: sha(SOURCE_DIR / n)
                for n in ['source.png', 'recognized.omr', 'visual-graph.json']
            },
            'prior_withheld_SIG_ids': WITHHELD,
            'reclassified_prior_SIG': 0,
            'baseline_scope_preserved': [77, 10, 84, 28],
        },
    )
    dump(
        out / 'validation-summary.json',
        {
            'base_sha': BASE_SHA,
            'source_completeness': 'UNVERIFIED',
            'new_events': 9,
            'new_owner_confirmed_events': 0,
            'displayed_events_per_target': 9,
            'rendering_completeness': 'INCOMPLETE_TEXT_AND_AMBIGUOUS_OBJECTS_WITHHELD',
            'independent_labels': 0,
            'visual_quality': 'PENDING_POST_FREEZE_AGENT_INSPECTION',
            'next': 'Owner review only; GT17B not authorized',
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'producer_sha256': sha(Path(__file__)),
            'freeze_before_visual_inspection': True,
        },
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
