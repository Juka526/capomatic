"""Owner interpretation plus new standalone text over immutable GT15 music masks."""

import argparse
import copy
import math
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from music21 import converter, harmony, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.chords import chord_symbol_from_text, chord_text, transpose_chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import FONT, events_of, event_signature, read, require
from scripts.research.gt12_render_context import KOREAN_FONT, canonical_box, ink_bbox, text_mask
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import contacts, displacement_domain, translate, union
from scripts.research.gt14b_lyric_extenders import extender
from scripts.research.gt14e_two_system_validation import GT14A
from scripts.research.gt15a_owner_review import PRIOR as GT15, GT14E, SOURCE_DIR
from scripts.research.paired_ground_truth_01 import dump, file_hashes, line_y, sha

ROOT = Path(__file__).resolve().parents[2]
BINDING = ROOT / 'docs/evidence/GT15B_OWNER_BINDING.json'
PROTOCOL = ROOT / 'docs/V4_GT15B_PROTOCOL.json'
WITHHELD = {'sheet#1:5833', 'sheet#1:5841', 'sheet#1:5896', 'sheet#1:5902', 'sheet#1:5903'}


def verify_owner(path=BINDING):
    b = read(path)
    require(
        b['classification'] == 'OWNER_VERIFIED_SOURCE'
        and b['independent_ground_truth'] is False
        and b['source_ink_replacement_authorized'] is False,
        'Invalid approval scope',
    )
    require(sha(path.parent / b['approval_file']) == b['approval_sha256'], 'Approval bytes changed')
    packet = Path(b['packet_directory'])
    require(
        sha(packet / 'packet-freeze.json') == b['packet_freeze_sha256'],
        'Review packet freeze changed',
    )
    for n, h in read(packet / 'packet-freeze.json')['files'].items():
        require(sha(packet / n) == h, f'Owner reviewed file changed: {n}')
    require(
        sha(packet / 'owner-approval-checklist.json') == b['checklist_sha256']
        and sha(packet / 'source-only-owner-review-sheet.png') == b['source_review_image_sha256'],
        'Reviewed checklist/image identity mismatch',
    )
    return b, read(packet / 'owner-approval-checklist.json')


def interpretation(checklist, binding):
    require(set(binding['withheld_ids']) == WITHHELD, 'Withholding scope changed')
    correction = binding['correction']
    require(
        correction == {'id': 'm11-row1-syllable-3', 'old': '을', 'new': '은', 'onset': '3'},
        'Unexpected correction',
    )
    result = copy.deepcopy(checklist)
    corrected = 0
    for i in result['items']:
        require(
            i['owner_response'] is None
            and i['owner_correction'] is None
            and i['owner_uncertainty'] is None,
            'Frozen candidate answers were changed',
        )
        i['historical_candidate_status'] = i['candidate_status']
        i['approval_sha256'] = binding['approval_sha256']
        if i['id'] in WITHHELD:
            require(i['kind'] == 'AMBIGUOUS_SIG_OBJECT', 'Wrong withheld object kind')
            i['interpretation_status'] = 'UNRESOLVED_CLASSIFICATION_EXPLICITLY_WITHHELD'
        elif i['kind'] == 'SOURCE_COMPLETENESS':
            i['interpretation_status'] = 'NO_SEPARATE_ATTESTATION_OF_ABSENCE'
        else:
            require(i['kind'] in binding['approved_kinds'], 'Unapproved candidate kind')
            i['interpretation_status'] = 'OWNER_VERIFIED_SOURCE'
            if i['id'] == correction['id']:
                require(
                    i['candidate']['syllable'] == correction['old']
                    and i['candidate']['onset'] == correction['onset'],
                    'Correction binding mismatch',
                )
                i['historical_candidate'] = copy.deepcopy(i['candidate'])
                i['candidate']['syllable'] = correction['new']
                i['correction'] = correction
                corrected += 1
    require(corrected == 1, 'Correction must apply exactly once')
    require(
        sum(i['interpretation_status'] == 'OWNER_VERIFIED_SOURCE' for i in result['items']) == 63,
        'Confirmed scope count mismatch',
    )
    for row, text in [(1, '풀은마르고꽃은시드나'), (2, '전능하신주거룩하신왕')]:
        syllables = [
            i['candidate']['syllable']
            for i in result['items']
            if i['kind'] == 'LYRIC_ASSOCIATION' and i['candidate']['row'] == row
        ]
        require(''.join(syllables) == text, 'Confirmed lyric string mismatch')
    result.update(
        review_type='OWNER_VERIFIED_SOURCE_WITH_EXPLICIT_WITHHOLDING',
        owner_verified_source=True,
        source_completeness='UNRESOLVED_SIG_CLASSIFICATION_AND_UNATTESTED_ABSENCE',
        independent_ground_truth=False,
    )
    return result


def approved(layer, kind):
    return [
        i
        for i in layer['items']
        if i['kind'] == kind and i['interpretation_status'] == 'OWNER_VERIFIED_SOURCE'
    ]


def music_signature(score):
    return [[event_signature(m) for m in p.getElementsByClass(stream.Measure)] for p in score.parts]


def augment(source, layer):
    result = copy.deepcopy(source)
    measures = list(result.parts[0].getElementsByClass(stream.Measure))
    for i in approved(layer, 'CHORD_OR_ABSENCE'):
        c = i['candidate']
        m = measures[c['printed_measure'] - 1]
        require(not list(m.getElementsByClass(harmony.ChordSymbol)), 'Unexpected existing harmony')
        if c['printed_chord_candidate']:
            m.insert(0, chord_symbol_from_text(c['printed_chord_candidate']))
    for m in measures[8:12]:
        for n in events_of(m):
            n.lyrics = []
    for i in approved(layer, 'LYRIC_ASSOCIATION'):
        c = i['candidate']
        m = measures[c['printed_measure'] - 1]
        ns = [
            n for n in events_of(m) if Fraction(n.getOffsetInHierarchy(m)) == Fraction(c['onset'])
        ]
        require(len(ns) == 1 and ns[0].isNote, 'Confirmed lyric note missing')
        ns[0].addLyric(c['syllable'], lyricNumber=c['row'])
    require(music_signature(source) == music_signature(result), 'Notes/rhythm/voices/ties changed')
    require(
        full_lyric_signature(source)[0][:8] == full_lyric_signature(result)[0][:8],
        'Previously confirmed lyrics changed',
    )
    return result


def text_layers(layer, source, size, protocol):
    font = ImageFont.truetype(str(KOREAN_FONT), 44)
    cmap = TTFont(KOREAN_FONT).getBestCmap()
    words = approved(layer, 'LYRIC_ASSOCIATION')
    require(
        len(words) == 20 and all(ord(i['candidate']['syllable']) in cmap for i in words),
        'Missing Korean glyph or wrong lyric count',
    )
    row_boxes = [ink_bbox(source, w) for w in protocol['lyric_source_windows']]
    baselines = []
    for row, box in enumerate(row_boxes, 1):
        descent = max(
            canonical_box(font, i['candidate']['syllable'])[3] - 2 * font.size
            for i in words
            if i['candidate']['row'] == row
        )
        baselines.append(box[3] - descent)
    masks, placements = {}, []
    for i in words:
        c = i['candidate']
        x = (c['source_head_bbox'][0] + c['source_head_bbox'][2]) / 2
        mask, info = text_mask(
            size, font, c['syllable'], center_x=x, baseline=baselines[c['row'] - 1]
        )
        masks[i['id']] = mask
        placements.append({'id': i['id'], **c, **info, 'base_baseline': baselines[c['row'] - 1]})
    for i in approved(layer, 'CONTINUATION_STROKE'):
        c = i['candidate']
        masks[i['id']] = extender(size, c['source_bbox_dark_support'], 0, protocol['third_view'])
        placements.append({'id': i['id'], **c, 'initial_rendered_bbox': masks[i['id']].getbbox()})
    require(len(masks) == 31 and not contacts(masks), 'Duplicate/colliding lyric components')
    return masks, placements, baselines, row_boxes


def layout_text(parts, fixed, viewport):
    domain = displacement_domain(
        union(list(parts.values())), fixed, Image.new('L', fixed.size), viewport
    )
    require(
        domain['selected_dy'] is not None, 'No collision-safe lyric displacement in declared domain'
    )
    dy = domain['selected_dy']
    moved = {n: translate(p, dy, viewport) for n, p in parts.items()}
    pairs = contacts(moved)
    text = union(list(moved.values()))
    count = int(np.count_nonzero((np.asarray(text) > 0) & (np.asarray(fixed) > 0)))
    clearance = float(ink_distance(fixed)[np.asarray(text) > 0].min())
    require(count == 0 and not pairs and clearance >= 2, 'Lyric collision/clearance failure')
    return moved, {
        'domain': domain,
        'dy': dy,
        'lyric_music_contacts': count,
        'lyric_pair_contacts': pairs,
        'minimum_ink_center_distance_px': clearance,
        'minimum_unit_square_edge_lower_bound_px': max(0, clearance - 2**0.5),
        'clipping': [],
        'lost_glyph_pixels': 0,
        'horizontal_anchor_changes': 0,
        'row_spacing_changes': 0,
    }


def section_label(size, font, text, left_top):
    """Fixed-phase plain text with measured allocation; music placement is untouched."""
    require(bool(text.strip()) and all(math.isfinite(v) for v in left_top), 'Invalid section text')
    left, top, right, bottom = font.getbbox(text, anchor='ls')
    pad = 2 * font.size
    tile = Image.new('L', (right - left + 2 * pad, bottom - top + 2 * pad))
    ImageDraw.Draw(tile).text((pad - left, pad - top), text, font=font, fill=255, anchor='ls')
    box = tile.getbbox()
    require(
        box is not None
        and box[0] > 0
        and box[1] > 0
        and box[2] < tile.width
        and box[3] < tile.height,
        'Clipped section canonical text',
    )
    bitmap = tile.crop(box)
    x, y = [math.floor(v + 0.5) for v in left_top]
    require(
        0 <= x and 0 <= y and x + bitmap.width <= size[0] and y + bitmap.height <= size[1],
        'Clipped section placement',
    )
    mask = Image.new('L', size)
    mask.paste(bitmap, (x, y))
    require(mask.crop(mask.getbbox()).tobytes() == bitmap.tobytes(), 'Lost section glyph alpha')
    return mask, {
        'text': text,
        'requested_left_top': left_top,
        'rendered_bbox': mask.getbbox(),
        'measured_advance_px': font.getlength(text),
        'measured_ink_width_px': bitmap.width,
        'method': 'Measured whole-string allocation, integer baseline phase, lossless unscaled translation',
    }


def frame(image, title):
    canvas = Image.new('RGB', (image.width, image.height + 180), 'white')
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
    d = ImageDraw.Draw(canvas)
    for n, text in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            'OWNER_VERIFIED_SOURCE / NOT_INDEPENDENT_GROUND_TRUTH; first three systems, 59 events / 7 chords / 70 syllables / 21 continuation marks.',
            'Five SIG objects remain UNCLASSIFIED; no independent articulation glyphs added. Newly typeset lyrics, not preserved original pixels.',
            'No source ink removal or original-pixel composition. Remaining score systems outside this experiment.',
        ]
    ):
        d.text((10, 8 + n * 30), text, font=f, fill='black')
    canvas.paste(image, (0, 180))
    return canvas


def run(out):
    require(not out.exists(), 'Fresh output required')
    protocol = read(PROTOCOL)
    binding, checklist = verify_owner()
    layer = interpretation(checklist, binding)
    packet = Path(binding['packet_directory'])
    validation = read(ROOT / 'docs/V4_GT15_VALIDATION.json')
    for n, h in validation['artifact_sha256'].items():
        require(sha(GT15 / n) == h, f'GT15 binding changed: {n}')
    for root in (GT15, GT14E):
        for n, h in read(root / 'prediction-freeze.json')['files'].items():
            require(sha(root / n) == h, f'Historical freeze changed: {n}')
    history = {str(p): file_hashes(p) for p in (GT15, GT14E, packet, GT14A)}
    input_hashes = read(GT15 / 'input-freeze.json')
    for name, key in [
        ('source.png', 'source_sha256'),
        ('recognized.omr', 'omr_sha256'),
        ('visual-graph.json', 'graph_sha256'),
    ]:
        require(sha(SOURCE_DIR / name) == input_hashes[key], 'Source binding changed')
    require(
        sha(FONT) == protocol['font_sha256'] and sha(KOREAN_FONT) == protocol['korean_font_sha256'],
        'Font identity changed',
    )
    original = Image.open(SOURCE_DIR / 'source.png')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    inv = read(GT15 / 'source-event-inventory.json')
    oldsource = converter.parse(str(GT14A / 'owner-augmented-source.musicxml'))
    source = augment(oldsource, layer)
    size = tuple(protocol['size'])
    parts, placements, baselines, row_boxes = text_layers(layer, original, size, protocol)
    out.mkdir()
    dump(out / 'owner-evidence-binding.json', binding)
    dump(out / 'owner-interpretation-layer.json', layer)
    source.write('musicxml', fp=str(out / 'owner-augmented-source.musicxml'))
    roundtrip = converter.parse(str(out / 'owner-augmented-source.musicxml'))
    sourceguard = validate(source, roundtrip, 0, 'key').to_dict()
    require(
        sourceguard['ok']
        and full_lyric_signature(source) == full_lyric_signature(roundtrip)
        and music_signature(source) == music_signature(roundtrip),
        'Full source roundtrip guard/signature failed',
    )
    guards = {'source_roundtrip': sourceguard}
    section_symbol = graph['symbols']['sheet#1:4183']
    require('value="Pre-Chorus"' in section_symbol['source_xml'], 'Source section label missing')
    section, secinfo = section_label(
        size,
        ImageFont.truetype(str(FONT), 33),
        'Pre-Chorus',
        section_symbol['geometry']['bbox'][:2],
    )
    border = Image.new('L', size)
    framebox = ink_bbox(original, [145, 1015, 370, 1070])
    ImageDraw.Draw(border).rectangle(
        (framebox[0], framebox[1], framebox[2] - 1, framebox[3] - 1), outline=255, width=2
    )
    require(
        not contacts({'section-text': section, 'section-frame': border}),
        'Section text/frame collision',
    )
    section_parts = {'section-text': section, 'section-frame': border}
    chord_boxes = {
        int(m): ink_bbox(original, w) for m, w in protocol['chord_source_windows'].items()
    }
    dump(
        out / 'pre-render-freeze.json',
        {
            'base_sha': binding['base_sha'],
            'approval_sha256': binding['approval_sha256'],
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
            'history_files': history,
            'source_input_hashes': {
                k: input_hashes[k] for k in ('source_sha256', 'omr_sha256', 'graph_sha256')
            },
            'lyric_baselines': baselines,
            'lyric_measurement_boxes': row_boxes,
            'chord_measurement_boxes': chord_boxes,
            'section': {
                'raw_symbol': section_symbol,
                'source_frame_box': framebox,
                'placement': secinfo,
            },
        },
    )
    reports, images = [], []
    for target, shift in [('A', -1), ('G', -3)]:
        score = copy.deepcopy(source)
        summary = transpose_score(score, shift, 'key')
        score.write('musicxml', fp=str(out / f'{target}-transposed.musicxml'))
        parsed = converter.parse(str(out / f'{target}-transposed.musicxml'))
        frozen = converter.parse(str(GT15 / f'{target}-semantic.musicxml'))
        guards[target] = {
            'in_memory': validate(source, score, shift, 'key', summary).to_dict(),
            'serialized': validate(source, parsed, shift, 'key', summary).to_dict(),
        }
        require(
            all(g['ok'] for g in guards[target].values())
            and music_signature(score) == music_signature(frozen)
            and music_signature(parsed) == music_signature(frozen)
            and full_lyric_signature(source) == full_lyric_signature(parsed),
            'Full target semantic guard/signature failed',
        )
        third = Image.open(GT15 / f'{target}-third-system-alpha.png').copy()
        first = Image.new('L', size)
        first.paste(Image.open(GT14E / f'{target}-integrated-alpha.png'), (0, 0))
        oldreport = next(
            r for r in read(GT15 / 'rendering-validation.json') if r['target'] == target
        )
        anchors = []
        measures = list(parsed.parts[0].getElementsByClass(stream.Measure))
        for m in inv['measures']:
            es = {
                str(Fraction(n.getOffsetInHierarchy(measures[m['printed_measure'] - 1]))): n
                for n in events_of(measures[m['printed_measure'] - 1])
            }
            for e in m['events']:
                if e['kind'] != 'NOTE':
                    continue
                n = es[e['onset']]
                x = e['physical_source_center'][0]
                y = (
                    line_y(inv['staff']['lines'][2], x)
                    + (35 - n.pitch.diatonicNoteNum) * inv['staff']['interline'] / 2
                )
                name = f'{target}-{(e["id"]+":head").replace(":","_")}-alpha.png'
                b = Image.open(GT15 / name).getbbox()
                residual = [(b[0] + b[2] - 1) / 2 - x, (b[1] + b[3] - 1) / 2 - y]
                require(max(map(abs, residual)) <= 0.5, 'Reused actual head raster anchor failed')
                anchors.append(
                    {
                        'event_id': e['id'],
                        'target_pitch': n.pitch.nameWithOctave,
                        'target_staff_coordinate': [x, y],
                        'reused_actual_head_bbox': b,
                        'residual': residual,
                    }
                )
        chords, chord_report = {}, []
        for i in approved(layer, 'CHORD_OR_ABSENCE'):
            c = i['candidate']
            m = c['printed_measure']
            word = c['printed_chord_candidate']
            if word is None:
                require(
                    not list(measures[m - 1].getElementsByClass(harmony.ChordSymbol)),
                    'Unapproved harmony inserted',
                )
                continue
            text = transpose_chord_text(word, shift, original_key='Bb', target_key=target)
            cs = list(measures[m - 1].getElementsByClass(harmony.ChordSymbol))
            require(
                len(cs) == 1 and chord_text(cs[0]) == text, 'Confirmed chord serialization changed'
            )
            mask, info = text_mask(
                size, ImageFont.truetype(str(FONT), 40), text, left_top=chord_boxes[m][:2]
            )
            bounds = mask.getbbox()
            limits = inv['measures'][m - 9]['omr_bounds']
            require(limits[0] <= bounds[0] < bounds[2] <= limits[2], 'Chord width exceeds measure')
            chords[f'chord-m{m}'] = mask
            chord_report.append(
                {'measure': m, 'source': word, 'target': text, 'source_box': chord_boxes[m], **info}
            )
        fixed_music = union([first, third])
        fixed_text = {**section_parts, **chords}
        newcontacts = contacts({**fixed_text, 'frozen-music': fixed_music})
        require(not newcontacts, 'Section/chord/music actual alpha collision')
        fixed = union([fixed_music, *fixed_text.values()])
        moved, metrics = layout_text(parts, fixed, protocol['third_view'])
        addition = union([*moved.values(), *fixed_text.values()])
        combined = union([fixed_music, addition])
        require(
            not np.any((np.asarray(addition) > 0) & (np.asarray(first) > 0)),
            'New third-system text contacts frozen first two systems',
        )
        require(
            np.array_equal(
                np.asarray(combined)[np.asarray(fixed_music) > 0],
                np.asarray(fixed_music)[np.asarray(fixed_music) > 0],
            ),
            'Frozen music/lyric alpha altered',
        )
        clipping = [
            n
            for n, p in {**fixed_text, **moved}.items()
            if p.getbbox()[0] < 130
            or p.getbbox()[2] > 2430
            or p.getbbox()[1] < 1015
            or p.getbbox()[3] > 1408
        ]
        require(not clipping, 'New component clipping')
        alpha_path = out / f'{target}-combined-alpha.png'
        combined.save(alpha_path)
        third.save(out / f'{target}-reused-third-system-alpha.png')
        first.save(out / f'{target}-reused-first-two-system-alpha.png')
        for name, mask in {**fixed_text, **moved}.items():
            mask.save(out / f'{target}-{name.replace("/","_")}-alpha.png')
        canvas = Image.composite(
            Image.new('RGB', size, 'black'), Image.new('RGB', size, 'white'), combined
        )
        image = frame(
            canvas.crop(protocol['integrated_view']),
            f'{target} major / printed measures 1-12 / owner-confirmed scoped content; unresolved objects withheld',
        )
        image.save(out / f'{target}-three-systems.png')
        images.append(image)
        xml = ET.parse(out / f'{target}-transposed.musicxml').getroot()
        scoped = list(xml.find('part').findall('measure'))[8:12]
        reports.append(
            {
                'target': target,
                'confirmed_events_new': 20,
                'displayed_events_total': 59,
                'confirmed_chords_total': 7,
                'new_chords': chord_report,
                'new_syllables': 20,
                'total_syllables': 70,
                'new_continuation_marks': 11,
                'total_continuation_marks': 21,
                'withheld_SIG_ids': sorted(WITHHELD),
                'independent_articulation_glyphs_added': 0,
                'original_notes_geometry_unchanged': True,
                'reused_third_alpha_sha256': sha(GT15 / f'{target}-third-system-alpha.png'),
                'first_two_system_layer_unchanged': True,
                'old_rendered_alpha_unchanged': True,
                'new_ink_to_old_first_two_contacts': 0,
                'source_section_pixels_in_blank_band_y1015_1030': int(
                    np.count_nonzero(np.asarray(union(list(section_parts.values())))[1015:1030])
                ),
                'notehead_anchor_checks': anchors,
                'max_anchor_residual': max(max(map(abs, a['residual'])) for a in anchors),
                'old_music_connections': oldreport['connections'],
                'old_music_missing_connections': oldreport['missing_connections'],
                'old_music_unexpected_collisions': oldreport['unexpected_intersections'],
                'ties_preserved': oldreport['ties'],
                'new_fixed_text_contacts': newcontacts,
                'clipping': clipping,
                'lyric_layout': metrics,
                'initial_lyric_baselines': baselines,
                'final_lyric_baselines': [b + metrics['dy'] for b in baselines],
                'placements': placements,
                'serialization': {
                    'new_lyric_elements': sum(len(m.findall('.//lyric')) for m in scoped),
                    'new_lyric_extend_elements': sum(
                        len(m.findall('.//lyric/extend')) for m in scoped
                    ),
                    'visual_continuations_represented_separately_in_masks_json': 11,
                    'production_export_changed': False,
                },
                'status': 'INCOMPLETE_UNRESOLVED_SIG_OBJECTS',
                'visual_quality': 'PENDING_POST_FREEZE_AGENT_INSPECTION',
            }
        )
    original_panel = frame(
        original.crop(protocol['integrated_view']),
        'Unmodified original Bb source; source comparison only, no A/G references',
    )
    original_panel.save(out / 'original-bb.png')
    contact = Image.new('RGB', (images[0].width, images[0].height * 3), 'white')
    for j, img in enumerate([original_panel, *images]):
        contact.paste(img, (0, j * img.height))
    contact.save(out / 'Bb-A-G-comparison.png')
    dump(out / 'rendering-validation.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    require(
        all(file_hashes(Path(p)) == h for p, h in history.items())
        and sha(SOURCE_DIR / 'source.png') == binding['source_sha256'],
        'Historical/source mutation',
    )
    dump(
        out / 'preservation-verification.json',
        {
            'source_unchanged': True,
            'all_historical_inputs_unchanged': True,
            'first_two_system_masks_unchanged': True,
            'third_system_music_masks_unchanged': True,
            'raw_candidates_unchanged': True,
            'new_section_label_may_add_ink_only_in_old_blank_footer_context': True,
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
