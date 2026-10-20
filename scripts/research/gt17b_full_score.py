"""Standalone full-score development preview and consolidated source review, no runtime routes."""

import argparse
import copy
import importlib.metadata as metadata
import math
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, harmony, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.chords import transpose_chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import FONT, read, require
from scripts.research.gt12_render_context import KOREAN_FONT, text_mask, canonical_box
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a4_header import header
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import union, contacts
from scripts.research.gt15b_confirmed_third_system import music_signature
from scripts.research.gt16_fourth_system import repeat_signature
from scripts.research.gt17_fifth_system import BASE, OPTICAL, SOURCE_DIR
from scripts.research.gt17b_source import (
    full_inventory,
    owner_augmented,
    review_packet,
    ROWS,
    CHORDS,
)
from scripts.research.gt17b_notation import render
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes

ROOT = Path(__file__).resolve().parents[2]
GT17 = Path('/private/tmp/capomatic-v4-gt17/gt17-final-output')
SIZE = (2520, 3564)
WARNING = 'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING'
BASE_SHA = '36a6b153aa40f44986b30ca112e73114e8c8ec79'
APPROVAL = '''The owner has explicitly approved the GT-17 review candidates for printed measures 17–19.

Promote only the approved interpretations into a separate owner-verification layer.

Approved content:

- 9 note/rest events
- 2 ties
- 1 beam group
- 1 isolated flag
- m17 B♭/D
- m18 E♭
- m19 no newly printed chord
- Upper Korean lyric: 이 / 루 / 시 / 네
- Approved note-onset associations
- 2 lyric continuation strokes
- No new lower lyric row
- Local second-ending notation associated with measure 17

Preserve raw SIG objects 5999 and 6001 and their historical classification records unchanged.

Store the approved continuation-stroke interpretation in a separate evidence layer.

Do not infer the complete repeat playback route.'''


def localize(sys, graph):
    top = sys['view'][1]
    inv = copy.deepcopy(sys)
    inv['staff']['lines'] = [[[x, y - top] for x, y in line] for line in inv['staff']['lines']]
    for m in inv['measures']:
        for e in m['events']:
            e['source_bbox'] = [v - (top if i % 2 else 0) for i, v in enumerate(e['source_bbox'])]
    symbols = copy.deepcopy(
        {k: v for k, v in graph['symbols'].items() if v['system'] == sys['staff']['system']}
    )
    for s in symbols.values():
        for key in ['line', 'curve']:
            s['geometry'][key] = [[x, y - top] for x, y in s['geometry'][key]]
        s['geometry']['bbox'] = [
            v - (top if i % 2 else 0) for i, v in enumerate(s['geometry']['bbox'])
        ]
    return (
        inv,
        {'symbols': symbols, 'relations': graph['relations'], 'all_symbols': graph['symbols']},
        top,
    )


def combine(parts, size):
    p = Image.new('L', size)
    for mask in parts:
        p = Image.fromarray(np.maximum(np.asarray(p), np.asarray(mask)))
    return p


def shift(mask, dy):
    b = mask.getbbox()
    require(b and b[3] + dy < mask.height, 'Translation clips')
    p = Image.new('L', mask.size)
    p.paste(mask.crop(b), (b[0], b[1] + dy))
    require(p.crop(p.getbbox()).tobytes() == mask.crop(b).tobytes(), 'Lost glyph pixels')
    return p


def layout_text(parts, music, max_dy=40):
    if not parts:
        return {}, {'status': 'NO_TEXT', 'dy': 0, 'min_center_distance': None}
    require(not contacts(parts), 'Initial text/text collision')
    joined = combine(parts.values(), music.size)
    b = joined.getbbox()
    dist = ink_distance(music)
    for dy in range(max_dy + 1):
        if b[3] + dy >= music.height:
            break
        region = dist[b[1] + dy : b[3] + dy, b[0] : b[2]]
        pixels = np.asarray(joined.crop(b)) > 0
        if float(region[pixels].min()) >= 2:
            moved = {k: shift(p, dy) for k, p in parts.items()}
            require(not contacts(moved), 'Moved text collision')
            return moved, {
                'status': 'PLACED',
                'dy': dy,
                'min_center_distance': float(region[pixels].min()),
                'actual_contacts': 0,
                'glyph_pixels_lost': 0,
            }
    return {}, {
        'status': 'BLOCKED_NO_SAFE_LOCAL_SPACE',
        'dy': None,
        'withheld_components': list(parts),
        'actual_contacts': 'NOT_EVALUABLE_WITHHELD',
    }


def lyric_parts(sys, inventory, size, top, source):
    font = ImageFont.truetype(str(KOREAN_FONT), 44)
    desc = canonical_box(font, '주')[3] - 2 * font.size
    cy = sys['staff']['lines'][2][0][1]
    baselines = [round(cy + 112.5 - desc - top), round(cy + 157.5 - desc - top)]
    parts = {}
    placements = []
    for l in inventory['lyrics']:
        if l['measure'] not in sys['printed_measures']:
            continue
        e = next(e for m in sys['measures'] for e in m['events'] if e['id'] == l['event_id'])
        p, info = text_mask(
            size,
            font,
            l['text'],
            center_x=e['physical_source_center'][0],
            baseline=baselines[l['row'] - 1],
        )
        parts[l['id']] = p
        placements.append({**l, 'rendered_bbox_local': p.getbbox(), **info})
    for mark in inventory['continuations']:
        if mark['measure'] not in sys['printed_measures']:
            continue
        b = mark['source_dark_bbox']
        p = Image.new('L', size)
        y = round((b[1] + b[3] - 1) / 2 - top)
        ImageDraw.Draw(p).line([(b[0], y), (b[2] - 1, y)], fill=255, width=2)
        parts[mark['id']] = p
        placements.append({**mark, 'rendered_bbox_local': p.getbbox()})
    return parts, placements


def key_clearance(keys, obstacles, max_left=40):
    """Minimal whole-key horizontal translation, preserving glyph bitmap, y and order."""
    dist = ink_distance(obstacles)
    for dx in range(0, -max_left - 1, -1):
        moved = {}
        for k, p in keys.items():
            b = p.getbbox()
            if b[0] + dx < 0:
                break
            q = Image.new('L', p.size)
            q.paste(p.crop(b), (b[0] + dx, b[1]))
            moved[k] = q
        if len(moved) != len(keys):
            continue
        ink = combine(moved.values(), obstacles.size)
        clearance = float(dist[np.asarray(ink) > 0].min())
        if clearance >= 2:
            require(not contacts(moved), 'Key glyphs intersect')
            return moved, {
                'dx': dx,
                'dy': 0,
                'minimum_ink_center_distance_px': clearance,
                'actual_contacts': 0,
                'glyph_pixels_lost': 0,
                'coordinate_contract': 'Integer x translation of target key group only; note/staff/clef/repeat positions unchanged',
            }
    raise ValueError('Target key cannot fit safely before source repeat')


def context(sys, graph, size, top, target):
    inv, lg, _ = localize(sys, graph)
    hp, hm = header(size, inv['staff'], target, FONT)
    parts = {k: p for k, p in hp.items() if k == 'clef' or k.startswith('sharp')}
    structure = {}
    dummymask = Image.new('L', size)
    draw = ImageDraw.Draw(dummymask)
    for poly in inv['staff']['lines']:
        draw.line([tuple(q) for q in poly], fill=255, width=2)
    structure['staff'] = dummymask
    # Exact persisted barline and repeat-dot objects, never source pixel masks.
    for s in lg['symbols'].values():
        if s['kind'] == 'barline' and s['shape'] in ('THIN_BARLINE', 'THICK_BARLINE'):
            b = s['geometry']['bbox']
            p = Image.new('L', size)
            ImageDraw.Draw(p).rectangle(
                (round(b[0]), round(b[1]), round(b[2] - 1), round(b[3] - 1)), fill=255
            )
            structure[s['id']] = p
        elif s['kind'] == 'repeat-dot':
            b = s['geometry']['bbox']
            p = Image.new('L', size)
            ImageDraw.Draw(p).ellipse((b[0], b[1], b[2] - 1, b[3] - 1), fill=255)
            structure[s['id']] = p
    for ident, numeral, xy in [('5197', '1.', (1027, 2473)), ('5199', '2.', (1827, 2470))]:
        if 'sheet#1:' + ident not in lg['symbols']:
            continue
        raw = ET.fromstring(graph['symbols']['sheet#1:' + ident]['source_xml'])
        p = Image.new('L', size)
        d = ImageDraw.Draw(p)
        for path in ['left-leg', 'line', 'right-leg']:
            a = raw.find(path)
            if a is not None:
                d.line(
                    [
                        (float(a.find(q).get('x')), float(a.find(q).get('y')) - top)
                        for q in ['p1', 'p2']
                    ],
                    fill=255,
                    width=2,
                )
        parts['ending-' + ident] = p
        parts['ending-number-' + ident], _ = text_mask(
            size, ImageFont.truetype(str(FONT), 40), numeral, left_top=(xy[0], xy[1] - top)
        )
    for system, label, xy in [(6, 'Chorus', (168, 2057)), (8, 'Tag', (178, 2762))]:
        if sys['system'] == system:
            p, info = text_mask(
                size, ImageFont.truetype(str(FONT), 34), label, left_top=(xy[0], xy[1] - top)
            )
            b = p.getbbox()
            frame = Image.new('L', size)
            ImageDraw.Draw(frame).rectangle(
                (b[0] - 8, b[1] - 5, b[2] + 8, b[3] + 5), outline=255, width=2
            )
            parts['section-' + label] = combine([p, frame], size)
    keys = {k: p for k, p in parts.items() if k.startswith('sharp')}
    obstacles = combine(
        [p for k, p in parts.items() if not k.startswith('sharp')]
        + [p for k, p in structure.items() if k != 'staff'],
        size,
    )
    keys, km = key_clearance(keys, obstacles)
    parts.update(keys)
    hm['key_horizontal_clearance'] = km
    return parts, structure, hm


def expected_tie_barline(curve_id, bar_id, graph, events, sys):
    """Only an equal-pitch serialized tie across this exact adjacent-measure boundary."""
    c = graph['symbols'].get(curve_id)
    bar = graph['symbols'].get(bar_id)
    if (
        not c
        or not bar
        or c['kind'] != 'slur'
        or bar['kind'] != 'barline'
        or ET.fromstring(c['source_xml']).get('tie') != 'true'
    ):
        return False
    rs = [r for r in graph['relations'] if r['source'] == curve_id and r['kind'] == 'slur-head']
    if len(rs) != 2 or any(r['target'] not in events for r in rs):
        return False
    ends = sorted([events[r['target']] for r in rs], key=lambda e: e['printed_measure'])
    if (
        ends[1]['printed_measure'] != ends[0]['printed_measure'] + 1
        or ends[0]['pitch'] != ends[1]['pitch']
        or [e['tie'] for e in ends] != ['start', 'stop']
    ):
        return False
    m = next(
        (m for m in sys['measures'] if m['printed_measure'] == ends[0]['printed_measure']), None
    )
    b = bar['geometry']['bbox']
    return bool(m and b[0] <= m['omr_bounds'][2] <= b[2])


def page(mask, provisional=None, title='', clean=False):
    canvas = (
        mask.copy()
        if mask.mode == 'RGB'
        else Image.composite(
            Image.new('RGB', mask.size, 'black'), Image.new('RGB', mask.size, 'white'), mask
        )
    )
    if provisional is not None and not clean:
        canvas = Image.composite(Image.new('RGB', mask.size, '#3057a0'), canvas, provisional)
    if clean:
        watermark = Image.new('RGB', (370, 30), 'white')
        ImageDraw.Draw(watermark).text(
            (2, 2),
            'PROVISIONAL / INCOMPLETE',
            font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20),
            fill='#777777',
        )
        watermark = watermark.transpose(Image.Transpose.ROTATE_90)
        for y in range(360, canvas.height - 370, 500):
            canvas.paste(watermark, (2470, y))
    out = Image.new('RGB', (canvas.width, canvas.height + 140), 'white')
    out.paste(canvas, (0, 140))
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    d = ImageDraw.Draw(out)
    for i, t in enumerate(
        [
            WARNING,
            title,
            'm1-19: owner-verified scope; m20-37: PROVISIONAL, NOT a verified performance score.',
            'Missing ties / disputed SIG objects withheld. Korean text newly typeset; no original-pixel preservation claim.',
            'Full source completeness, repeat playback and independent musician validation remain unresolved.',
        ]
    ):
        d.text((15, 6 + i * 26), t, font=font, fill='black')
    return out


def fifth_text(size, target, inventory):
    font = ImageFont.truetype(str(KOREAN_FONT), 44)
    desc = canonical_box(font, '주')[3] - 2 * font.size
    sys = inventory['systems'][4]
    events = {
        e['onset']: e for m in sys['measures'] if m['printed_measure'] == 17 for e in m['events']
    }
    parts = {}
    for onset, text in zip(['3/2', '2', '5/2', '7/2'], ['이', '루', '시', '네']):
        parts['m17-' + text], _ = text_mask(
            size,
            font,
            text,
            center_x=events[onset]['physical_source_center'][0],
            baseline=1994 - desc,
        )
    for sid in ['5999', '6001']:
        b = read(SOURCE_DIR / 'visual-graph.json')['symbols']['sheet#1:' + sid]['geometry']['bbox']
        p = Image.new('L', size)
        ImageDraw.Draw(p).line(
            [(b[0], round((b[1] + b[3] - 1) / 2)), (b[2] - 1, round((b[1] + b[3] - 1) / 2))],
            fill=255,
            width=2,
        )
        parts['approved-stroke-' + sid] = p
    return parts


def binding(out):
    history = {}
    for folder, doc in [
        (BASE, 'V4_GT16B_VALIDATION.json'),
        (OPTICAL, 'V4_GT16C_VALIDATION.json'),
        (GT17, 'V4_GT17_VALIDATION.json'),
    ]:
        for n, h in read(ROOT / 'docs' / doc)['artifact_sha256'].items():
            require(sha(folder / n) == h, 'History changed:' + str(folder / n))
        for n, h in read(folder / 'prediction-freeze.json')['files'].items():
            require(sha(folder / n) == h, 'History freeze changed:' + n)
        history[str(folder)] = file_hashes(folder)
    src = read(BASE / 'pre-render-freeze.json')['source_input_hashes']
    for n, k in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / n) == src[k], 'Source provenance mismatch')
    dump(
        out / 'owner-interpretation-layer.json',
        {
            'classification': 'OWNER_VERIFIED_SOURCE',
            'independent_ground_truth': False,
            'approval_verbatim': APPROVAL,
            'approval_origin': 'Actual current GT17B user instruction Phase2, not an invented external submission',
            'preceding_review_context': {
                'commit': BASE_SHA,
                'source_inventory_sha256': sha(GT17 / 'source-fifth-system-inventory.json'),
                'checklist_sha256': sha(GT17 / 'owner-review-checklist.json'),
                'review_sheet_sha256': sha(GT17 / 'source-fifth-system-review-sheet.png'),
                'packet_freeze_sha256': sha(GT17 / 'prediction-freeze.json'),
            },
            'source_binding': src,
            'approved_events': 9,
            'approved_chords': ['Bb/D', 'Eb'],
            'approved_lyrics': ['이', '루', '시', '네'],
            'approved_strokes': ['sheet#1:5999', 'sheet#1:6001'],
            'raw_SIG_observations_unchanged': True,
            'repeat_playback_approved': False,
            'new_content_beyond_m19_approved': False,
        },
    )
    return history, src


def export_pdf(image, path):
    """Keep calibrated font runtime unchanged; use installed system pypdf in a child."""
    import io, subprocess, json, hashlib

    data = io.BytesIO()
    image.save(data, format='PNG')
    proc = subprocess.run(
        [
            '/opt/anaconda3/bin/python',
            str(ROOT / 'scripts/research/gt17b_pdf.py'),
            '--output',
            str(path),
        ],
        input=data.getvalue(),
        capture_output=True,
        check=True,
    )
    report = json.loads(proc.stdout)
    require(
        report['rgb_sha256'] == hashlib.sha256(image.tobytes()).hexdigest(),
        'PDF image pixels changed',
    )
    return report


def run(out):
    require(not out.exists(), 'Fresh output only')
    out.mkdir()
    history, src = binding(out)
    graph = read(SOURCE_DIR / 'visual-graph.json')
    original = Image.open(SOURCE_DIR / 'source.png')
    baseline = converter.parse(str(BASE / 'owner-augmented-source.musicxml'))
    augmented = owner_augmented(baseline)
    inventory = full_inventory(augmented, graph, original)
    require(
        len(inventory['events']) == 169 and len(inventory['systems']) == 9,
        'Source structure mismatch',
    )
    require(
        sum(e['printed_measure'] <= 19 for e in inventory['events']) == 86,
        'Confirmed event scope mismatch',
    )
    first19 = list(augmented.parts[0].getElementsByClass(stream.Measure))[:19]
    require(
        sum(len(m.getElementsByClass(harmony.ChordSymbol)) for m in first19) == 12
        and sum(len(n.lyrics) for m in first19 for n in m.recurse().notes) == 88,
        'Confirmed chord/lyric scope mismatch',
    )
    dump(out / 'full-source-event-inventory.json', inventory)
    dump(
        out / 'full-source-system-map.json',
        {
            'systems': inventory['systems'],
            'source_hashes': src,
            'registration': 'Original2520x3564 page integer pixel coordinates; bbox endpoints exclusive',
        },
    )
    review_packet(out, inventory, graph, original)
    # Source-only native page is the complete review sheet; no target pixels in the packet.
    original.save(out / 'full-source-owner-review-sheet.png')
    augmented.write('musicxml', fp=str(out / 'owner-augmented-source.musicxml'))
    guards = {
        'baseline_roundtrip': validate(
            baseline, converter.parse(str(BASE / 'owner-augmented-source.musicxml')), 0, 'key'
        ).to_dict(),
        'augmented_roundtrip': validate(
            augmented, converter.parse(str(out / 'owner-augmented-source.musicxml')), 0, 'key'
        ).to_dict(),
    }
    dump(
        out / 'source-inventory-freeze.json',
        {
            'files': file_hashes(out),
            'source_hashes': src,
            'protocol_sha256': sha(ROOT / 'docs/V4_GT17B_PROTOCOL.json'),
            'code_sha256': {
                str(p.relative_to(ROOT)): sha(p)
                for p in [
                    Path(__file__),
                    ROOT / 'scripts/research/gt17b_source.py',
                    ROOT / 'scripts/research/gt17b_notation.py',
                    ROOT / 'scripts/research/gt17b_pdf.py',
                ]
            },
        },
    )
    reports = []
    coverage = []
    pdfs = {}
    all_events = {e['symbol_id']: e for e in inventory['events']}
    pngs = []
    for target, semitones in [('A', -1), ('G', -3)]:
        score = copy.deepcopy(augmented)
        summary = transpose_score(score, semitones, 'key')
        score.write('musicxml', fp=str(out / f'{target}-transposed.musicxml'))
        parsed = converter.parse(str(out / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(augmented, score, semitones, 'key', summary).to_dict(),
            'serialized': validate(augmented, parsed, semitones, 'key', summary).to_dict(),
        }
        require(all(g['ok'] for g in guards[target].values()), 'Unchanged full V3 guard failed')
        require(
            music_signature(score)
            == music_signature(converter.parse(str(GT17 / f'{target}-semantic.musicxml'))),
            'Frozen event signatures changed',
        )
        require(
            full_lyric_signature(score) == full_lyric_signature(augmented),
            'Lyric semantics changed',
        )
        require(
            repeat_signature(augmented) == repeat_signature(score) == repeat_signature(parsed),
            'Repeat signature changed',
        )
        prior = Image.open(OPTICAL / f'{target}-refined-alpha.png')
        full = Image.new('L', SIZE)
        full.paste(prior, (0, 0))
        fifth = Image.open(GT17 / f'{target}-fifth-alpha.png')
        layer5 = Image.new('L', SIZE)
        layer5.paste(fifth, (0, 0))
        baseplus5 = combine([full, layer5], SIZE)
        lp = fifth_text(SIZE, target, inventory)
        moved, lm = layout_text(lp, baseplus5, max_dy=30)
        require(len(moved) == 6, 'Approved fifth lyrics/extenders blocked')
        chordtext = transpose_chord_text('Bb/D', semitones, original_key='Bb', target_key=target)
        cp, ci = text_mask(SIZE, ImageFont.truetype(str(FONT), 40), chordtext, left_top=(335, 1770))
        require(
            not contacts(
                {'chord': cp, 'existing': baseplus5, 'lyrics': combine(moved.values(), SIZE)}
            ),
            'Fifth chord contact',
        )
        full = combine([baseplus5, cp, *moved.values()], SIZE)
        require(
            np.array_equal(
                np.asarray(full)[np.asarray(baseplus5) > 0],
                np.asarray(baseplus5)[np.asarray(baseplus5) > 0],
            ),
            'Old notation changed',
        )
        new = Image.new('L', SIZE)
        system_reports = []
        for sys in inventory['systems'][5:]:
            inv, lg, top = localize(sys, graph)
            size = (2520, sys['view'][3] - top)
            parts, metrics = render(inv, score, target, lg, size, all_events)
            require(
                not metrics['unexpected_contacts'] and not metrics['missing_connections'],
                'Music contacts/connections',
            )
            contextparts, scaffold, hm = context(sys, graph, size, top, target)
            require(
                not [
                    c
                    for c in contacts({**parts, **contextparts})
                    if c['a'] in contextparts or c['b'] in contextparts
                ],
                'Music/context collision',
            )
            structured_hits = contacts(
                {**parts, **contextparts, **{k: p for k, p in scaffold.items() if k != 'staff'}}
            )
            explained_structure = []
            bad_structure = []
            for hit in structured_hits:
                if hit['a'] not in scaffold and hit['b'] not in scaffold:
                    continue
                other = hit['b'] if hit['a'] in scaffold else hit['a']
                barid = hit['a'] if hit['a'] in scaffold else hit['b']
                if expected_tie_barline(other, barid, graph, all_events, sys):
                    explained_structure.append(
                        dict(
                            hit, classification='EXPLICIT_ADJACENT_MEASURE_TIE_CROSSES_ITS_BARLINE'
                        )
                    )
                else:
                    bad_structure.append(hit)
            require(not bad_structure, 'Non-staff structural collision')
            fixed = combine([*parts.values(), *contextparts.values(), *scaffold.values()], size)
            chordparts = {}
            chordmetrics = []
            for c in inventory['chords']:
                if c['measure'] not in sys['printed_measures']:
                    continue
                text = transpose_chord_text(
                    c['text'], semitones, original_key='Bb', target_key=target
                )
                p, info = text_mask(
                    size,
                    ImageFont.truetype(str(FONT), 40),
                    text,
                    left_top=(c['source_window'][0], c['source_window'][1] - top),
                )
                require(not contacts({c['id']: p, 'fixed': fixed}), 'Provisional chord collision')
                chordparts[c['id']] = p
                chordmetrics.append({**c, 'target_text': text, **info})
            require(not contacts(chordparts), 'Chord/chord collision')
            fixed = combine([fixed, *chordparts.values()], size)
            textparts, placements = lyric_parts(sys, inventory, size, top, original)
            moved, tm = layout_text(textparts, fixed)
            systemmask = combine([fixed, *moved.values()], size)
            require(
                systemmask.getbbox()
                and systemmask.getbbox()[1] > 0
                and systemmask.getbbox()[3] < size[1],
                'System viewport clipping',
            )
            padded = Image.new('L', SIZE)
            padded.paste(systemmask, (0, top))
            require(not contacts({'old': full, 'new': padded}), 'Inter-system alpha collision')
            inter_system_clearance = float(ink_distance(full)[np.asarray(padded) > 0].min())
            require(inter_system_clearance >= 2, 'Insufficient inter-system ink clearance')
            full = combine([full, padded], SIZE)
            new = combine([new, padded], SIZE)
            systemmask.save(out / f'{target}-system-{sys["system"]}-alpha.png')
            page(
                systemmask,
                title=f'{target} major / system{sys["system"]} / printed{sys["printed_measures"]} OMR_PROVISIONAL',
            ).save(out / f'{target}-system-{sys["system"]}-provisional.png')
            component_dir = out / f'{target}-system-{sys["system"]}-components'
            component_dir.mkdir()
            maps = []
            for name, p in {**parts, **contextparts, **scaffold, **chordparts, **moved}.items():
                b = p.getbbox()
                file = name.replace(':', '_').replace('/', '_') + '.png'
                p.crop(b).save(component_dir / file)
                maps.append(
                    {
                        'id': name,
                        'file': file,
                        'bbox_local': b,
                        'page_origin_y': top,
                        'sha256': sha(component_dir / file),
                    }
                )
            dump(component_dir / 'component-map.json', maps)
            for e in metrics['events']:
                if 'target_staff_coordinate' in e:
                    e['target_staff_coordinate_page'] = [
                        e['target_staff_coordinate'][0],
                        e['target_staff_coordinate'][1] + top,
                    ]
            metrics.update(
                system=sys['system'],
                page_origin_y=top,
                previous_systems_min_ink_center_clearance_px=inter_system_clearance,
                size=size,
                header=hm,
                source_backed_tie_barline_contacts=explained_structure,
                unexpected_structural_contacts=bad_structure,
                lyric_layout=tm,
                lyrics=placements,
                rendered_lyrics=sum(
                    l['id'] in moved
                    for l in inventory['lyrics']
                    if l['measure'] in sys['printed_measures']
                ),
                rendered_continuations=sum(
                    l['id'] in moved
                    for l in inventory['continuations']
                    if l['measure'] in sys['printed_measures']
                ),
                chords=chordmetrics,
                lyric_text_alpha_contacts=0 if moved else 'NOT_EVALUABLE_WITHHELD',
                max_chord_width=max((x['measured_ink_width_px'] for x in chordmetrics), default=0),
            )
            system_reports.append(metrics)
            for m in sys['measures']:
                num = m['printed_measure']
                coverage.append(
                    {
                        'target': target,
                        'measure': num,
                        'source_status': 'OMR_PROVISIONAL',
                        'recognized_events': len(m['events']),
                        'rendered_events': sum(e['measure'] == num for e in metrics['events']),
                        'owner_confirmed_events': 0,
                        'recognized_chords': m['recognized_harmonies'],
                        'chord_candidates': [c for c in inventory['chords'] if c['measure'] == num],
                        'lyric_candidates': sum(l['measure'] == num for l in inventory['lyrics']),
                        'rendered_lyric_syllables': sum(
                            l['measure'] == num and l['id'] in moved for l in inventory['lyrics']
                        ),
                        'continuation_candidates': sum(
                            l['measure'] == num for l in inventory['continuations']
                        ),
                        'rendered_continuations': sum(
                            l['measure'] == num and l['id'] in moved
                            for l in inventory['continuations']
                        ),
                        'repeat_playback': 'UNRESOLVED',
                        'independently_verified_completeness': False,
                    }
                )
        # Prior ink is checked directly; new systems occupy different page regions.
        require(
            np.array_equal(np.asarray(full)[:1740], np.asarray(baseplus5)[:1740]),
            'First four systems changed',
        )
        pic = page(
            full,
            new,
            title=f'{target} major / full printed1-37 / 86 owner-confirmed+83 provisional event cores',
        )
        pic.save(out / f'{target}-full-score.png')
        pngs.append(pic)
        clean = page(
            full, title=f'{target} major CLEAN-STYLE CANDIDATE / PROVISIONAL systems6-9', clean=True
        )
        clean.save(out / f'{target}-full-score-clean-style.png')
        full.save(out / f'{target}-full-alpha.png')
        pdfs[target] = export_pdf(pic, out / f'{target}-full-score-experimental.pdf')
        reports.append(
            {
                'target': target,
                'source_registered_canvas': SIZE,
                'display_header_height': 140,
                'confirmed_scope': {
                    'events': 86,
                    'chords': 12,
                    'syllables': 88,
                    'continuations': 30,
                },
                'new_provisional_scope': {
                    'events': sum(len(s['events']) for s in system_reports),
                    'chords': sum(len(s['chords']) for s in system_reports),
                    'syllables': sum(s['rendered_lyrics'] for s in system_reports),
                    'continuations': sum(s['rendered_continuations'] for s in system_reports),
                },
                'fifth_approved_text_layout': lm,
                'fifth_chord': ci,
                'systems': system_reports,
                'full_score_complete': False,
                'repeat_playback': 'UNRESOLVED',
                'independent_validation_count': 0,
                'lyric_extender_musicxml_serialization': 'INCOMPLETE_VISUAL_MARKS_ARE_NOT_XML_EXTEND_RECORDS',
            }
        )
    sourcepanel = page(original, title='ORIGINAL Bb page2 source only')
    thumbwidth = 1000
    thumbs = []
    for img in [sourcepanel, *pngs]:
        thumbs.append(
            img.resize(
                (thumbwidth, round(img.height * thumbwidth / img.width)), Image.Resampling.LANCZOS
            )
        )
    comparison = Image.new('RGB', (3000, max(p.height for p in thumbs)), 'white')
    for i, img in enumerate(thumbs):
        comparison.paste(img, (i * 1000, 0))
    comparison.save(out / 'Bb-A-G-full-score-comparison.png')
    confirmed_marks = {
        2: 2,
        4: 2,
        5: 2,
        6: 2,
        7: 2,
        10: 5,
        12: 6,
        14: 5,
        15: 1,
        16: 1,
        17: 1,
        18: 1,
    }
    require(sum(confirmed_marks.values()) == 30, 'Prior+approved continuation scope mismatch')
    measures = list(augmented.parts[0].getElementsByClass(stream.Measure))
    for target in ['A', 'G']:
        for sys in inventory['systems'][:5]:
            for m in sys['measures']:
                num = m['printed_measure']
                sem = measures[num - 1]
                coverage.append(
                    {
                        'target': target,
                        'measure': num,
                        'source_status': 'OWNER_VERIFIED_SOURCE_WITHIN_APPROVED_SCOPE',
                        'recognized_events': len(m['events']),
                        'rendered_events': len(m['events']),
                        'owner_confirmed_events': len(m['events']),
                        'rendered_chords': len(sem.getElementsByClass(harmony.ChordSymbol)),
                        'rendered_lyric_syllables': sum(len(n.lyrics) for n in sem.recurse().notes),
                        'rendered_continuations': confirmed_marks.get(num, 0),
                        'source_completeness': 'NOT_INDEPENDENTLY_ESTABLISHED',
                        'historical_layer_preserved': True,
                        'repeat_playback': 'UNRESOLVED',
                    }
                )
    for row in coverage:
        num = row['measure']
        row['unclassified_object_ids'] = [
            u['id']
            for u in inventory['unresolved_objects']
            if u.get('measure') == num
            or (
                u.get('original_observation', {}).get('system')
                == next(
                    s['staff']['system']
                    for s in inventory['systems']
                    if num in s['printed_measures']
                )
                and u.get('original_observation', {}).get('geometry', {}).get('bbox')
                and next(
                    m
                    for s in inventory['systems']
                    for m in s['measures']
                    if m['printed_measure'] == num
                )['omr_bounds'][0]
                <= sum(u['original_observation']['geometry']['bbox'][::2]) / 2
                < next(
                    m
                    for s in inventory['systems']
                    for m in s['measures']
                    if m['printed_measure'] == num
                )['omr_bounds'][2]
            )
        ]
        row['unclassified_object_count'] = len(row['unclassified_object_ids'])
        row['accuracy_denominator'] = None
    dump(out / 'full-source-coverage-matrix.json', coverage)
    dump(out / 'full-score-rendering-validation.json', {'targets': reports, 'pdfs': pdfs})
    dump(
        out / 'full-score-semantic-integrity.json',
        {
            'guards': guards,
            'semantic_event_count': 169,
            'measure_count': 37,
            'augmented_harmony_count': 16,
            'notes_onsets_durations_voices_unchanged': True,
            'independent_accuracy_denominator': None,
            'lyric_extender_serialization': 'INCOMPLETE_SEPARATE_FROM_VISUAL_MARKS',
        },
    )
    dump(out / 'unresolved-source-objects.json', inventory['unresolved_objects'])
    preservation = {k: file_hashes(Path(k)) == v for k, v in history.items()}
    require(all(preservation.values()), 'Historical artifact changed')
    for n, k in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / n) == src[k], 'Source changed')
    dump(
        out / 'full-score-preservation-verification.json',
        {
            'history': preservation,
            'source_hashes': src,
            'prior_withheld_SIG_unchanged': True,
            'previous_frozen_files_unchanged': True,
            'new_owner_approved_scope': [17, 18, 19],
            'no_new_owner_approval_beyond19': True,
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'freeze_before_agent_visual_review': True,
            'code_sha256': {
                str(p.relative_to(ROOT)): sha(p)
                for p in [
                    Path(__file__),
                    ROOT / 'scripts/research/gt17b_source.py',
                    ROOT / 'scripts/research/gt17b_notation.py',
                    ROOT / 'scripts/research/gt17b_pdf.py',
                ]
            },
        },
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
