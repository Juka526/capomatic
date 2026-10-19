"""Full-system audit and explicitly incomplete standalone canvas using confirmed GT12 ink."""

import argparse
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
from music21 import converter, harmony, stream
from PIL import Image, ImageDraw

from backend.omr_v3.music_guard import validate
from scripts.research.gt11_complete_measure import GT01, events_of, read, require, verify_inventory
from scripts.research.paired_ground_truth_01 import dump, file_hashes, line_y, sha

BASE = '681f4a2dec0eb0dccc8e46eac6aac19f88c44fa9'
GT12 = Path('/private/tmp/capomatic-v4-gt12/gt12-output')
GT02 = Path('/private/tmp/capomatic-v4-ground-truth-02/ground-truth-02-output')
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/V4_GT13A_PROTOCOL.json'
CROP = (130, 310, 2430, 720)
CANDIDATES = {
    1: {'chords': ['Bb'], 'upper': ['주', '님', '의'], 'lower': ['광', '야', '의']},
    2: {
        'chords': [],
        'upper': ['마', '음', '이', '있', '는', '곳'],
        'lower': ['꽃', '을', '피', '우', '시', '고'],
    },
    3: {'chords': ['F'], 'upper': ['주', '님', '의'], 'lower': ['사', '막', '의']},
    4: {
        'chords': [],
        'upper': ['시', '선', '이', '있', '는', '곳'],
        'lower': ['강', '물', '을', '내', '시', '는'],
    },
}


def eligible(number, confirmed):
    # A matching melody/lyric phrase never inherits confirmation from a different measure.
    return number in confirmed


def measure_inventory(m, rows, geometry, graph_measure, confirmed):
    number = geometry['printed_measure']
    notes = events_of(m)
    require(len(notes) == len(rows), 'Physical/semantic source event counts differ')
    require({r['omr_measure_index'] for r in rows} == {number - 1}, 'Ambiguous measure lineage')
    result = []
    for n, r in zip(notes, rows):
        require(
            Fraction(n.getOffsetInHierarchy(m)) == Fraction(r['local_offset'])
            and Fraction(n.quarterLength) == Fraction(r['duration']),
            'Source timing correspondence differs',
        )
        require(n.isRest or n.pitch.nameWithOctave == r['pitch'], 'Source written pitch differs')
        result.append(
            {
                'event_id': r['id'],
                'symbol_id': r['symbol_id'],
                'printed_measure': number,
                'kind': r['kind'],
                'pitch': r.get('pitch'),
                'onset': r['local_offset'],
                'duration': r['duration'],
                'voice': r['voice'],
                'source_bbox': r['bbox'],
                'recognition': 'OMR_RECOGNIZED',
                'source_verification': (
                    'OWNER_VERIFIED' if eligible(number, confirmed) else 'UNVERIFIED'
                ),
                'tie': getattr(n.tie, 'type', None),
                'stem_direction': n.stemDirection if n.isNote else None,
                'source_accidental': (
                    {
                        'name': n.pitch.accidental.name,
                        'display_status': n.pitch.accidental.displayStatus,
                    }
                    if n.isNote and n.pitch.accidental
                    else None
                ),
                'beams': (
                    [
                        {'number': b.number, 'type': b.type, 'direction': b.direction}
                        for b in n.beams
                    ]
                    if n.isNote
                    else []
                ),
                'raw_omr_lyrics': [
                    {'row': l.number, 'text': l.text, 'syllabic': l.syllabic} for l in n.lyrics
                ],
                'articulations': [type(a).__name__ for a in n.articulations],
                'spanners': [type(a).__name__ for a in n.getSpannerSites()],
            }
        )
    geometry_bounds = [geometry['left']['x'], geometry['right']['x']]
    omr_bounds = [graph_measure['bounds'][0], graph_measure['bounds'][2]]
    unsupported = []
    if any(n.isRest and n.duration.type == 'eighth' for n in notes):
        unsupported.append('EIGHTH_REST_NO_VALIDATED_RENDER_CONTRACT')
    if any(n.tie is not None for n in notes):
        unsupported += ['TIE_RENDERING', 'MIXED_BEAMS_AND_PARTIAL_HOOK_LAYOUT']
    if number == 4 and notes[-1].tie and notes[-1].tie.type == 'start':
        unsupported.append('CROSS_SYSTEM_TIE_ENDPOINT')
    if number == 1:
        unsupported.append('CLEF_KEY_TIME_FORWARD_REPEAT_GLYPH_PLACEMENT')
    return {
        'printed_measure': number,
        'events': result,
        'recognized_duration_total': str(
            sum((Fraction(n.quarterLength) for n in notes), Fraction(0))
        ),
        'raw_omr_harmonies': [c.figure for c in m.getElementsByClass(harmony.ChordSymbol)],
        'source_image_candidates_NOT_HUMAN_VERIFIED': CANDIDATES[number],
        'lyric_note_associations': (
            'OWNER_VERIFIED_FROM_GT12'
            if eligible(number, confirmed)
            else 'UNVERIFIED; ties, row fusion and extenders require source review'
        ),
        'content_status': 'OWNER_VERIFIED' if eligible(number, confirmed) else 'UNVERIFIED',
        'renderer_unsupported': unsupported,
        'notehead_stem_ledger_quarter_rest_support': 'SUPPORTED_EXISTING_GT12',
        'single_up_eighth_flag_support': 'SUPPORTED_GT07_ONLY_WHEN_EXPLICIT_GROUP_RELATIONS_VALID',
        'uniform_double_beam_pair_support': 'SUPPORTED_GT06; DOES_NOT_AUTHORIZE_MIXED_GROUPS',
        'physical_boundary_candidates': geometry_bounds,
        'omr_boundary_geometry': omr_bounds,
        'omr_minus_physical_candidate_px': [a - b for a, b in zip(omr_bounds, geometry_bounds)],
        'boundary_independent_ground_truth': False,
        'render_action': (
            'REUSE_EXACT_GT12_CONTENT'
            if eligible(number, confirmed)
            else 'EXPLICIT_GAP_NO_NOTATION_OR_LYRIC_GUESS'
        ),
    }


def scaffold(size, staff, boundaries, external_barline_bounds=None):
    require(
        len(staff['lines']) == 5 and all(len(poly) >= 2 for poly in staff['lines']),
        'Incomplete staff geometry',
    )
    require(
        all(math.isfinite(v) for poly in staff['lines'] for p in poly for v in p)
        and all(math.isfinite(x) for x in boundaries),
        'Invalid/nonfinite geometry',
    )
    mask = Image.new('L', size)
    draw = ImageDraw.Draw(mask)
    # Exact GT04/GT12 width-2 polyline contract, with original intermediate vertices retained.
    for poly in staff['lines']:
        draw.line([tuple(p) for p in poly], fill=255, width=2)
    for x in boundaries:
        if any(not (poly[0][0] <= x <= poly[-1][0]) for poly in staff['lines']):
            bounds = (external_barline_bounds or {}).get(x)
            require(
                bounds is not None
                and all(math.isfinite(v) for v in bounds)
                and bounds[0] <= x <= bounds[2],
                'External boundary needs explicit persisted barline geometry',
            )
            draw.line([(x, bounds[1]), (x, bounds[3])], fill=255, width=2)
            continue
        draw.line(
            [(x, line_y(staff['lines'][0], x)), (x, line_y(staff['lines'][-1], x))],
            fill=255,
            width=2,
        )
    return mask


def label(crop, title):
    result = Image.new('RGB', (crop.width, crop.height + 100), 'white')
    result.paste(crop, (0, 100))
    d = ImageDraw.Draw(result)
    for i, text in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            'Only m3 is owner-verified. m1/m2/m4 are explicit gaps; no source lyric pixels enter target canvases.',
            'Clef/key/time/repeat glyph context NOT ENGRAVED. Captions do not replace these missing symbols.',
        ]
    ):
        d.text((8, 5 + i * 20), text, fill='black')
    return result


def run(out):
    require(not out.exists(), 'New output directory required')
    verify_inventory(Path('/private/tmp/capomatic-v4-gt11/gt11-input'))
    historical = file_hashes(GT12)
    freeze = read(GT12 / 'confirmed-context/prediction-freeze.json')
    require(
        all(sha(GT12 / p) == h for p, h in freeze['output_files_sha256'].items()),
        'GT12 prediction freeze changed',
    )
    owner = read(GT12 / 'confirmed-context/confirmed-source.json')
    require(
        owner['classification'] == 'OWNER_VERIFIED_SOURCE'
        and owner['all_checklist_content_explicitly_confirmed'] is True
        and owner['printed_measure'] == 3,
        'Owner scope not established',
    )
    require(
        sha(GT12 / 'confirmed-context/owner-visual-confirmation.txt')
        == owner['actual_confirmation_sha256'],
        'Actual owner confirmation changed',
    )
    manifest = read(GT02 / 'gt02-artifact-manifest.json')
    for name in ['measure-registration.json', 'note-correspondence-diagnostic.json']:
        require(
            sha(GT02 / name) == manifest['file_sha256']['ground-truth-02-output/' + name],
            'GT02 source geometry evidence changed',
        )
    baseline = GT01 / 'predictions/baseline-exec'
    source_dir = baseline / 'source'
    score = converter.parse(str(source_dir / 'recognized.musicxml'))
    graph = read(source_dir / 'visual-graph.json')
    staff = next(s for s in graph['staves'] if s['id'] == 'sheet#1:1')
    # Read only Bb fields; the file also contains reference mappings, which are never exported or used.
    regions = [
        r
        for r in read(GT02 / 'measure-registration.json')['pages']['Bb']['measures']
        if r['system'] == 1
    ]
    require(
        [r['printed_measure'] for r in regions] == [1, 2, 3, 4],
        'Fixed first-system measure identity changed',
    )
    rows = [
        r
        for r in read(GT02 / 'note-correspondence-diagnostic.json')['events']['Bb']
        if r['system'] == 1
    ]
    measures = list(score.parts[0].getElementsByClass(stream.Measure))
    inventory = []
    for r in regions:
        n = r['printed_measure']
        gm = next(
            m
            for m in graph['measures']
            if m['system'] == 'sheet#1:system:1' and m['number'] == str(n)
        )
        inventory.append(
            measure_inventory(
                measures[n - 1], [e for e in rows if e['printed_measures'] == [n]], r, gm, {3}
            )
        )
    out.mkdir(parents=True)
    with Image.open(source_dir / 'source.png') as original:
        original.crop(CROP).save(out / 'original-bb.png')
        size = original.size
    ids = {r['symbol_id'] for r in rows}
    curve_relations = [
        r
        for r in graph['relations']
        if r['kind'] == 'slur-head' and (r['source'] in ids or r['target'] in ids)
    ]
    curve_ids = {r['source'] for r in curve_relations}
    nearby_ids = set(ids)
    for _ in range(2):
        for relation in graph['relations']:
            if relation['kind'] in [
                'head-stem',
                'beam-stem',
                'flag-stem',
                'alter-head',
                'augmentation',
            ] and (relation['source'] in nearby_ids or relation['target'] in nearby_ids):
                nearby_ids.update([relation['source'], relation['target']])
    notation_relations = [
        r for r in graph['relations'] if r['source'] in nearby_ids or r['target'] in nearby_ids
    ]
    dump(
        out / 'source-system-inventory.json',
        {
            'base': BASE,
            'scope': 'Bb PDF page 2, first system, printed 1-4',
            'measures': inventory,
            'staff': staff,
            'context': {
                'clef': 'TrebleClef: OMR_RECOGNIZED',
                'key': '2 flats: OMR_RECOGNIZED',
                'time': '4/4: agent source-image candidate; not serialized in source MusicXML',
                'forward_repeat': 'OMR_RECOGNIZED; source-image candidate',
                'header_rendering': 'UNSUPPORTED_VALIDATED_PLACEMENT_CONTRACT',
            },
            'curve_relations': curve_relations,
            'curves': [graph['symbols'][i] for i in sorted(curve_ids)],
            'notation_relations': notation_relations,
            'related_symbols': [
                graph['symbols'][i] for i in sorted(nearby_ids) if i in graph['symbols']
            ],
            'independent_ground_truth': False,
            'owner_verified_measure_scope': [3],
            'source_chord_absence_outside_candidates': 'UNVERIFIED; no carry semantics inferred',
        },
    )
    dump(
        out / 'input-and-inventory-freeze.json',
        {
            'protocol_sha256': sha(PROTOCOL),
            'source_inventory_sha256': sha(out / 'source-system-inventory.json'),
            'source_sha256': sha(source_dir / 'source.png'),
            'GT12_files_sha256': historical,
            'source_geometry_inputs': {
                str(GT02 / n): sha(GT02 / n)
                for n in ['measure-registration.json', 'note-correspondence-diagnostic.json']
            },
        },
    )
    guards = {}
    for target, shift in [('A', -1), ('G', -3)]:
        raw_target = converter.parse(str(baseline / target / 'transposed.musicxml'))
        raw = validate(score, raw_target, shift, 'key').to_dict()
        augmented = converter.parse(str(GT12 / 'confirmed-context/owner-augmented-source.musicxml'))
        context_target = converter.parse(
            str(GT12 / f'confirmed-context/{target}-transposed.musicxml')
        )
        confirmed = validate(augmented, context_target, shift, 'key').to_dict()
        require(raw['ok'] and confirmed['ok'], 'Unchanged full V3 guard failed')
        guards[target] = {'raw_frozen_GT01': raw, 'owner_augmented_frozen_GT12': confirmed}
    dump(out / 'semantic-integrity.json', guards)
    boundaries = [regions[0]['left']['x']] + [r['right']['x'] for r in regions]
    external = {}
    external_evidence = []
    for x in boundaries:
        if any(not (poly[0][0] <= x <= poly[-1][0]) for poly in staff['lines']):
            candidates = [
                s
                for s in graph['symbols'].values()
                if s['kind'] == 'staff-barline'
                and s['staff'] == staff['id']
                and s['geometry']['valid']
                and s['geometry']['bbox'] is not None
                and s['geometry']['bbox'][0] <= x <= s['geometry']['bbox'][2]
            ]
            require(len(candidates) == 1, 'External boundary barline evidence missing/ambiguous')
            external[x] = candidates[0]['geometry']['bbox']
            external_evidence.append(
                {
                    'x': x,
                    'symbol_id': candidates[0]['id'],
                    'bbox': external[x],
                    'method': 'Diagnostic barline skeleton at unchanged x, within persisted bbox; no staff extrapolation or exact glyph reconstruction claim',
                }
            )
    dump(out / 'external-boundary-evidence.json', external_evidence)
    base = scaffold(size, staff, boundaries, external)
    base.save(out / 'staff-and-boundary-scaffold.png')
    source_panel = label(
        Image.open(out / 'original-bb.png'), 'Unchanged original Bb first-system context'
    )
    panels = [source_panel]
    metrics = []
    for target in ['A', 'G']:
        cached = Image.open(GT12 / f'confirmed-context/{target}-combined-alpha.png')
        require(cached.size == size and cached.mode == 'L', 'Cached layer coordinate/mode mismatch')
        combined = Image.fromarray(np.maximum(np.asarray(base), np.asarray(cached)))
        combined.save(out / f'{target}-notation-alpha.png')
        canvas = Image.composite(
            Image.new('RGB', size, 'black'), Image.new('RGB', size, 'white'), combined
        )
        d = ImageDraw.Draw(canvas)
        for r in inventory:
            left, right = r['physical_boundary_candidates']
            if r['printed_measure'] != 3:
                d.rectangle((left + 6, 395, right - 6, 690), outline=(180, 90, 0), width=1)
                d.text(
                    (left + 16, 550),
                    f'm{r["printed_measure"]}: GAP - UNVERIFIED CONTENT',
                    fill=(140, 60, 0),
                )
                d.text((left + 16, 574), 'No notes, chord or lyrics guessed', fill=(140, 60, 0))
            else:
                d.text((left + 12, 695), 'm3: GT12 OWNER_VERIFIED content', fill=(0, 80, 0))
        p = label(
            canvas.crop(CROP),
            f'{target} major target; G clef / {3 if target == "A" else 1} sharps: TEXT CONTEXT ONLY',
        )
        p.save(out / f'predicted-{target.lower()}.png')
        panels.append(p)
        metrics.append(
            {
                'target': target,
                'rendered_measures': [3],
                'gap_measures': [1, 2, 4],
                'rendered_music_events': 4,
                'recognized_system_music_events': len(rows),
                'not_rendered_recognized_events': len(rows) - 4,
                'chords_rendered': 1,
                'lyric_syllables_rendered': 6,
                'music_chord_lyric_contract': 'EXACT_GT12_ALPHA_REUSE',
                'cached_GT12_alpha_sha256': sha(
                    GT12 / f'confirmed-context/{target}-combined-alpha.png'
                ),
                'new_note_anchor_algorithm': False,
                'staff_polyline_vertices_changed': 0,
                'GT12_notehead_max_residual': 0.5,
                'actual_extent': list(CROP),
                'full_system_complete': False,
            }
        )
    sheet = Image.new('RGB', (panels[0].width, sum(p.height for p in panels)), 'white')
    for i, p in enumerate(panels):
        sheet.paste(p, (0, i * p.height))
    sheet.save(out / 'comparison-contact-sheet.png')
    dump(
        out / 'rendering-metrics.json',
        {
            'metrics': metrics,
            'source_boundary_candidates': boundaries,
            'staff_geometry_basis': 'Exact original Audiveris polylines; no mean-y flattening',
            'source_event_counts': {
                'notes': sum(r['kind'] == 'NOTE' for r in rows),
                'rests': sum(r['kind'] == 'REST' for r in rows),
            },
            'full_system_collisions_clipping_readability': 'NOT_CERTIFIED: unrendered notation/header/context remains',
            'original_source_pixels_in_targets': False,
        },
    )
    require(file_hashes(GT12) == historical, 'GT12 historical evidence changed')
    dump(
        out / 'prediction-freeze.json',
        {
            'phase': 'BEFORE_AGENT_VISUAL_REVIEW',
            'base': BASE,
            'code_sha256': sha(Path(__file__)),
            'files': file_hashes(out),
        },
    )
    return 'FULL_SYSTEM_INCOMPLETE_WITH_EXPLICIT_GAPS'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('gt13a-output'))
    print(run(parser.parse_args().out))
