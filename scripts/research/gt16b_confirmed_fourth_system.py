"""Add owner-confirmed text to frozen fourth-system masks; no source ink editing."""

import argparse
import copy
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, harmony, stream
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from backend.omr_v3.chords import chord_symbol_from_text, chord_text, transpose_chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import FONT, events_of, read, require
from scripts.research.gt12_render_context import KOREAN_FONT, canonical_box, ink_bbox, text_mask
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a5_lyric_layout import contacts, union, verify_freeze
from scripts.research.gt14b_lyric_extenders import extender
from scripts.research.gt15b_confirmed_third_system import layout_text, music_signature
from scripts.research.gt16_fourth_system import SOURCE_DIR, PRIOR as GT15B, repeat_signature
from scripts.research.paired_ground_truth_01 import dump, file_hashes, line_y, sha

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt16/gt16-final-output')
BINDING = ROOT / 'docs/evidence/GT16B_OWNER_BINDING.json'
PROTOCOL = ROOT / 'docs/V4_GT16B_PROTOCOL.json'
WITHHELD = {f'sheet#1:{n}' for n in (5927, 5948, 5949, 5975, 5984)}


def verify_owner(binding_path=BINDING, prior=PRIOR):
    b = read(binding_path)
    require(
        b['classification'] == 'OWNER_VERIFIED_SOURCE'
        and b['independent_ground_truth'] is False
        and b['source_ink_replacement_authorized'] is False,
        'Invalid approval scope',
    )
    require(
        set(b['withheld_SIG_ids']) == WITHHELD
        and b['repeat_playback_route'] == 'EXPLICITLY_WITHHELD',
        'Withholding changed',
    )
    for name, digest in b['files'].items():
        path = Path(name)
        require(
            sha(path if path.is_absolute() else ROOT / path) == digest,
            'Approval context changed: ' + name,
        )
    packet = prior / 'owner-review'
    for name, digest in read(packet / 'packet-freeze.json')['files'].items():
        require(sha(packet / name) == digest, 'Reviewed packet changed: ' + name)
    return b


def interpretation(inv, binding):
    layer = copy.deepcopy(inv)
    require(
        len(layer['measures']) == 4 and layer['recognized_events'] == 18, 'Wrong fixed inventory'
    )
    require(
        {r['symbol']['id'] for r in layer['ambiguous_SIG_objects']} == WITHHELD,
        'Wrong withheld objects',
    )
    require(len(layer['candidate_continuation_marks']) == 7, 'Wrong mark count')
    for m in layer['measures']:
        require(
            m['candidate_status'] == 'AGENT_VISUAL_CANDIDATE', 'Historical candidate status changed'
        )
        m['interpretation_status'] = 'OWNER_VERIFIED_SOURCE'
        for e in m['events']:
            e['historical_render_evidence'] = e['render_evidence']
            e['source_verification'] = 'OWNER_VERIFIED_SOURCE'
        for mark in layer['candidate_continuation_marks']:
            mark['interpretation_status'] = 'OWNER_VERIFIED_SOURCE'
    for r in layer['ambiguous_SIG_objects']:
        r['interpretation_status'] = 'EXPLICITLY_WITHHELD_UNCLASSIFIED'
    layer.update(
        classification='OWNER_VERIFIED_SOURCE',
        independent_ground_truth=False,
        approval_sha256=sha(ROOT / 'docs/evidence/GT16B_OWNER_APPROVAL.txt'),
        binding=binding,
        source_completeness='UNRESOLVED_SIG_AND_UNATTESTED_ABSENCE',
        repeat_playback_route='EXPLICITLY_WITHHELD',
    )
    return layer


def augment(source, layer):
    result = copy.deepcopy(source)
    ms = list(result.parts[0].getElementsByClass(stream.Measure))
    for record in layer['measures']:
        m = ms[record['printed_measure'] - 1]
        candidate = record['agent_candidates']
        cs = list(m.getElementsByClass(harmony.ChordSymbol))
        word = candidate['chord']
        if record['printed_measure'] == 14:
            require(len(cs) == 1 and chord_text(cs[0]) == 'Gm7', 'Existing Gm7 changed')
        else:
            require(not cs, 'Unexpected prior fourth-system harmony')
            if word:
                m.insert(0, chord_symbol_from_text(word))
        for n in events_of(m):
            n.lyrics = []
        for row, key in [(1, 'upper'), (2, 'lower')]:
            require(len(candidate[key]) == len(candidate[key + '_onsets']), 'Association mismatch')
            for syllable, onset in zip(candidate[key], candidate[key + '_onsets']):
                ns = [
                    n
                    for n in events_of(m)
                    if Fraction(n.getOffsetInHierarchy(m)) == Fraction(onset)
                ]
                require(len(ns) == 1 and ns[0].isNote, 'Approved lyric note missing')
                ns[0].addLyric(syllable, lyricNumber=row)
    require(music_signature(source) == music_signature(result), 'Musical events changed')
    require(
        full_lyric_signature(source)[0][:12] == full_lyric_signature(result)[0][:12],
        'Prior confirmed lyrics changed',
    )
    for old, new in zip(list(source.parts[0].getElementsByClass(stream.Measure))[:12], ms[:12]):
        require(
            [chord_text(c) for c in old.getElementsByClass(harmony.ChordSymbol)]
            == [chord_text(c) for c in new.getElementsByClass(harmony.ChordSymbol)],
            'Prior harmonies changed',
        )
    return result


def lyric_layers(layer, original, size, protocol):
    # Reuse GT15B's exact text placement, adapted through its existing input contract.
    items = []
    for m in layer['measures']:
        for row, key in [(1, 'upper'), (2, 'lower')]:
            for syllable, onset in zip(
                m['agent_candidates'][key], m['agent_candidates'][key + '_onsets']
            ):
                e = next(e for e in m['events'] if e['onset'] == onset)
                items.append(
                    {
                        'id': f'm{m["printed_measure"]}-row{row}-syllable-{onset}',
                        'candidate': {
                            'row': row,
                            'syllable': syllable,
                            'onset': onset,
                            'printed_measure': m['printed_measure'],
                            'source_head_bbox': e['source_bbox'],
                        },
                    }
                )
    require(len(items) == 14, 'Wrong lyric count')
    font = ImageFont.truetype(str(KOREAN_FONT), protocol['lyric_font_size'])
    cmap = TTFont(KOREAN_FONT).getBestCmap()
    require(all(ord(i['candidate']['syllable']) in cmap for i in items), 'Missing Korean glyph')
    row_boxes = [ink_bbox(original, w) for w in protocol['lyric_source_windows']]
    baselines = [
        box[3]
        - max(
            canonical_box(font, i['candidate']['syllable'])[3] - 2 * font.size
            for i in items
            if i['candidate']['row'] == row
        )
        for row, box in enumerate(row_boxes, 1)
    ]
    masks, placements = {}, []
    for i in items:
        c = i['candidate']
        b = c['source_head_bbox']
        p, info = text_mask(
            size, font, c['syllable'], center_x=(b[0] + b[2]) / 2, baseline=baselines[c['row'] - 1]
        )
        masks[i['id']] = p
        placements.append({'id': i['id'], **c, **info})
    for r in layer['candidate_continuation_marks']:
        masks[r['id']] = extender(
            size, r['diagnostic_dark_support_bbox'], 0, protocol['fourth_view']
        )
        # A continuation repeats no syllable token. Its identity remains separately auditable.
        prior_words = [
            i
            for i in items
            if i['candidate']['row'] == r['row']
            and (i['candidate']['printed_measure'], Fraction(i['candidate']['onset']))
            < (r['printed_measure'], Fraction(r['onset_candidate']))
        ]
        require(prior_words, 'Continuation lacks preceding approved syllable')
        held = prior_words[-1]['candidate']
        e = next(
            e
            for m in layer['measures']
            for e in m['events']
            if m['printed_measure'] == r['printed_measure'] and e['onset'] == r['onset_candidate']
        )
        require(e['tie'] == 'stop', 'Expected tied continuation source event')
        placements.append(
            {
                'id': r['id'],
                'kind': 'CONTINUATION',
                **r,
                'held_syllable': held,
                'context_event_id': e['id'],
                'initial_bbox': masks[r['id']].getbbox(),
            }
        )
    require(len(masks) == 21 and not contacts(masks), 'Duplicate/colliding lyric components')
    return masks, placements, baselines, row_boxes


def frozen_music(target, metrics, size):
    parts = {}
    inv = read(PRIOR / 'source-event-inventory.json')
    names = [
        e['id'] + ':' + kind
        for m in inv['measures']
        for e in m['events']
        for kind in ['head', 'rest', 'stem', 'ledger', 'flag']
    ]
    names += [v['id'] for v in metrics['beams']]
    names += [v['curve_id'] for v in metrics['ties']]
    frozen_files = read(PRIOR / 'prediction-freeze.json')['files']
    for name in names:
        filename = f'{target}-{name.replace(":", "_")}-alpha.png'
        if filename in frozen_files:
            require(sha(PRIOR / filename) == frozen_files[filename], 'Frozen music mask changed')
            parts[name] = Image.open(PRIOR / filename).copy()
    require(
        all(p.size == size and p.mode == 'L' for p in parts.values()), 'Mask registration mismatch'
    )
    require(
        sum(n.endswith(':head') or n.endswith(':rest') for n in parts) == 18,
        'Missing or duplicate core masks',
    )
    return parts


def panel(image, title):
    result = Image.new('RGB', (image.width, image.height + 180), 'white')
    d = ImageDraw.Draw(result)
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    lines = [
        'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
        title,
        'OWNER_VERIFIED_SOURCE / NOT_INDEPENDENT_GROUND_TRUTH; 77 events / 10 chords / 84 syllables / 28 continuation marks.',
        'Newly typeset Korean lyrics, not original lyric pixels. Prior three systems and fourth-system music masks unchanged.',
        'Ten SIG objects unclassified; repeat playback route unresolved. No source editing or production composition.',
    ]
    for j, text in enumerate(lines):
        d.text((10, 8 + 30 * j), text, font=f, fill='black')
    result.paste(image, (0, 180))
    return result


def run(out):
    require(not out.exists(), 'Fresh output required')
    b = verify_owner()
    protocol = read(PROTOCOL)
    size = tuple(protocol['size'])
    view = protocol['fourth_view']
    require(
        sha(FONT) == read(ROOT / 'docs/V4_GT15B_PROTOCOL.json')['font_sha256']
        and sha(KOREAN_FONT) == read(ROOT / 'docs/V4_GT15B_PROTOCOL.json')['korean_font_sha256'],
        'Font changed',
    )
    verify_freeze(PRIOR)
    verify_freeze(GT15B)
    for n, h in read(ROOT / 'docs/V4_GT16_VALIDATION.json')['artifact_sha256'].items():
        require(sha(PRIOR / n) == h, 'GT16 binding changed: ' + n)
    oldfreeze = read(GT15B / 'pre-render-freeze.json')['source_input_hashes']
    for name, key in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / name) == oldfreeze[key], 'Source changed')
    history = {str(p): file_hashes(p) for p in (PRIOR, GT15B)}
    inv = read(PRIOR / 'source-event-inventory.json')
    layer = interpretation(inv, b)
    source = augment(converter.parse(str(GT15B / 'owner-augmented-source.musicxml')), layer)
    original = Image.open(SOURCE_DIR / 'source.png')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    lyrics, placements, baselines, row_boxes = lyric_layers(layer, original, size, protocol)
    out.mkdir()
    dump(out / 'owner-interpretation-layer.json', layer)
    dump(
        out / 'pre-render-freeze.json',
        {
            'binding': b,
            'history': history,
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
            'baselines': baselines,
            'row_measurement_boxes': row_boxes,
            'source_input_hashes': oldfreeze,
        },
    )
    source.write('musicxml', fp=str(out / 'owner-augmented-source.musicxml'))
    disk = converter.parse(str(out / 'owner-augmented-source.musicxml'))
    guards = {'source_roundtrip': validate(source, disk, 0, 'key').to_dict()}
    require(
        guards['source_roundtrip']['ok']
        and music_signature(source) == music_signature(disk)
        and full_lyric_signature(source) == full_lyric_signature(disk),
        'Source serialization failed',
    )
    reports, panels = [], []
    for target, shift in [('A', -1), ('G', -3)]:
        score = copy.deepcopy(source)
        summary = transpose_score(score, shift, 'key')
        score.write('musicxml', fp=str(out / f'{target}-transposed.musicxml'))
        parsed = converter.parse(str(out / f'{target}-transposed.musicxml'))
        frozen = converter.parse(str(PRIOR / f'{target}-semantic.musicxml'))
        guards[target] = {
            'in_memory': validate(source, score, shift, 'key', summary).to_dict(),
            'serialized': validate(source, parsed, shift, 'key', summary).to_dict(),
        }
        require(
            all(g['ok'] for g in guards[target].values())
            and music_signature(parsed) == music_signature(frozen)
            and full_lyric_signature(source) == full_lyric_signature(parsed),
            'Unchanged full V3 guard/signature failed',
        )
        require(
            repeat_signature(source)
            == repeat_signature(score)
            == repeat_signature(parsed)
            == repeat_signature(frozen),
            'Repeat/ending semantics changed',
        )
        oldreport = next(
            r for r in read(PRIOR / 'rendering-validation.json') if r['target'] == target
        )
        music = frozen_music(target, oldreport, size)
        fixedparts = {
            name: Image.open(PRIOR / f'{target}-{name}-alpha.png').copy()
            for name in [
                'staff-and-bars',
                'clef',
                'first-ending-bracket',
                'first-ending-number',
                'measure-number13',
            ]
        }
        for j in range(3 if target == 'A' else 1):
            fixedparts[f'sharp-{j}'] = Image.open(PRIOR / f'{target}-sharp-{j}-alpha.png').copy()
        fixed = union([*music.values(), *fixedparts.values()])
        chord_parts = {}
        chord_reports = []
        ms = list(parsed.parts[0].getElementsByClass(stream.Measure))
        for j, (number, record) in enumerate(protocol['chords'].items()):
            number = int(number)
            text = transpose_chord_text(
                record['source'], shift, original_key='Bb', target_key=target
            )
            require(
                text == protocol['expected_targets'][target][j], 'Wrong confirmed chord transpose'
            )
            cs = list(ms[number - 1].getElementsByClass(harmony.ChordSymbol))
            require(
                len(cs) == 1 and chord_text(cs[0]) == text, 'Chord semantics/serialization changed'
            )
            box = graph['symbols'][record['symbol']]['geometry']['bbox']
            p, info = text_mask(size, ImageFont.truetype(str(FONT), 40), text, left_top=box[:2])
            limits = inv['measures'][number - 13]['omr_bounds']
            require(
                limits[0] <= p.getbbox()[0] < p.getbbox()[2] <= limits[2], 'Chord exceeds measure'
            )
            if number == 14:
                require(
                    p.tobytes()
                    == Image.open(PRIOR / f'{target}-provisional-chord-m14-alpha.png').tobytes(),
                    'Existing Gm7 mask changed',
                )
            chord_parts[f'chord-m{number}'] = p
            chord_reports.append(
                {
                    'measure': number,
                    'source': record['source'],
                    'target': text,
                    'source_symbol': record['symbol'],
                    **info,
                }
            )
        require(
            not contacts({**chord_parts, 'fixed-notation': fixed}),
            'Chord/notation or chord/chord contact',
        )
        fourth_old = Image.open(PRIOR / f'{target}-fourth-alpha.png')
        require(
            union([fixed, chord_parts['chord-m14']]).tobytes() == fourth_old.tobytes(),
            'Frozen fourth-system mask reconstruction failed',
        )
        chord_clearance = float(
            ink_distance(fixed)[np.asarray(union(list(chord_parts.values()))) > 0].min()
        )
        require(chord_clearance >= 2, 'Chord/notation clearance failure')
        fixed = union([fixed, *chord_parts.values()])
        moved, lm = layout_text(lyrics, fixed, view)
        fourth = union([fixed, *moved.values()])
        old = Image.open(GT15B / f'{target}-combined-alpha.png')
        base = Image.new('L', size)
        base.paste(old, (0, 0))
        require(not contacts({'old-systems': base, 'new-fourth': fourth}), 'Old/new-system contact')
        combined = union([base, fourth])
        require(
            combined.crop((0, 0, size[0], 1408)).tobytes()
            == base.crop((0, 0, size[0], 1408)).tobytes(),
            'Prior body changed',
        )
        canvas = Image.composite(
            Image.new('RGB', size, 'black'), Image.new('RGB', size, 'white'), combined
        )
        full = panel(
            canvas.crop(protocol['integrated_view']),
            f'{target} major / printed measures1-16 / OWNER-VERIFIED SCOPED CONTENT',
        )
        oldpng = Image.open(GT15B / f'{target}-three-systems.png')
        require(
            full.crop((0, 180, full.width, 1278)).tobytes()
            == oldpng.crop((0, 180, oldpng.width, oldpng.height)).tobytes(),
            'Old RGB body changed',
        )
        full.save(out / f'{target}-four-systems.png')
        panels.append(full)
        panel(canvas.crop(view), f'{target} major / confirmed fourth-system scope').save(
            out / f'{target}-fourth-system.png'
        )
        combined.save(out / f'{target}-combined-alpha.png')
        fourth.save(out / f'{target}-fourth-alpha.png')
        for name, p in {**music, **fixedparts, **chord_parts, **moved}.items():
            p.save(out / f'{target}-{name.replace(":","_").replace("/","-")}-alpha.png')
        anchors = []
        for m in inv['measures']:
            for e, n in zip(m['events'], events_of(ms[m['printed_measure'] - 1])):
                if e['kind'] != 'NOTE':
                    continue
                x = e['physical_source_center'][0]
                y = line_y(inv['staff']['lines'][2], x) + (35 - n.pitch.diatonicNoteNum) * 9
                box = music[e['id'] + ':head'].getbbox()
                res = [(box[0] + box[2] - 1) / 2 - x, (box[1] + box[3] - 1) / 2 - y]
                require(max(map(abs, res)) <= 0.5, 'Anchor criterion failed')
                anchors.append({'event': e['id'], 'pitch': n.pitch.nameWithOctave, 'residual': res})
        clipping = [
            name
            for name, p in {**music, **fixedparts, **chord_parts, **moved}.items()
            if p.getbbox()[0] < view[0]
            or p.getbbox()[2] > view[2]
            or p.getbbox()[1] < view[1]
            or p.getbbox()[3] > view[3]
        ]
        require(not clipping, 'Component clipping')
        xml = ET.parse(out / f'{target}-transposed.musicxml').getroot()
        scoped = list(xml.find('part').findall('measure'))[12:16]
        reports.append(
            {
                'target': target,
                'confirmed_events_new': 18,
                'confirmed_events_total': 77,
                'confirmed_chords_new': 3,
                'confirmed_chords_total': 10,
                'new_chords': chord_reports,
                'chord_notation_contact_pixels': 0,
                'minimum_chord_notation_ink_center_distance_px': chord_clearance,
                'chord_pair_contacts': [],
                'old_new_system_contact_pixels': 0,
                'new_syllables': 14,
                'total_syllables': 84,
                'new_marks': 7,
                'total_marks': 28,
                'lyric_layout': lm,
                'placements': placements,
                'initial_baselines': baselines,
                'final_baselines': [v + lm['dy'] for v in baselines],
                'anchors': anchors,
                'max_anchor_residual': max(max(map(abs, a['residual'])) for a in anchors),
                'clipping': clipping,
                'unchanged_connections': oldreport['connections'],
                'missing_connections': oldreport['missing_connections'],
                'unexpected_music_contacts': oldreport['unexpected_intersections'],
                'ties': [
                    dict(
                        t,
                        historical_source_verification=t['source_verification'],
                        source_verification='OWNER_VERIFIED_SOURCE',
                    )
                    for t in oldreport['ties']
                ],
                'withheld_new_SIG': sorted(WITHHELD),
                'withheld_prior_SIG': inv['prior_withheld_SIG_ids'],
                'old_music_masks_reused_byte_identical': True,
                'prior_three_system_RGB_body_identical': True,
                'repeat_playback_route': 'EXPLICITLY_WITHHELD',
                'source_verification': 'OWNER_VERIFIED_SCOPE_WITH_EXCLUSIONS',
                'rendering_completeness': 'APPROVED_SCOPE_RENDERED_UNRESOLVED_SIG_OBJECTS',
                'serialization': {
                    'new_lyric_elements': sum(len(m.findall('.//lyric')) for m in scoped),
                    'new_extend_elements': sum(len(m.findall('.//lyric/extend')) for m in scoped),
                    'visual_continuations_separate_masks': 7,
                },
                'visual_quality': 'PENDING_POST_FREEZE_AGENT_INSPECTION',
                'status': 'DEVELOPER_ONLY_INCOMPLETE',
            }
        )
    orig = panel(
        original.crop(protocol['integrated_view']),
        'Original Bb source, unchanged; source evidence only',
    )
    orig.save(out / 'original-bb.png')
    sheet = Image.new('RGB', (orig.width, orig.height * 3), 'white')
    for j, p in enumerate([orig, *panels]):
        sheet.paste(p, (0, j * orig.height))
    sheet.save(out / 'Bb-A-G-comparison.png')
    dump(out / 'rendering-validation.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    require(
        all(file_hashes(Path(p)) == h for p, h in history.items())
        and sha(SOURCE_DIR / 'source.png') == b['source_sha256'],
        'Historical/source mutation',
    )
    dump(
        out / 'preservation-verification.json',
        {
            'history_hashes_unchanged': True,
            'source_unchanged': True,
            'fourth_music_masks_unchanged': True,
            'prior_three_RGB_body_identical': True,
            'original_candidates_unmodified': True,
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {'files': file_hashes(out), 'phase': 'BEFORE_AGENT_VISUAL_INSPECTION_NO_REFERENCE_ACCESS'},
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
