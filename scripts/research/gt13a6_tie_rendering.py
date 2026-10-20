"""Owner-bound standalone two-system tie context; no source-image modification."""

import argparse
import copy
import hashlib
import zipfile
from pathlib import Path

import cv2
import numpy as np
from fontTools.ttLib import TTFont
from music21 import converter, pitch
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from backend.omr_v4.masks import validate_pixel_integrity
from scripts.research.gt04_visual import HEAD
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt11_complete_measure import FONT, read, require
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a4_header import header, font_units
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import OLD, SOURCE, verify_freeze, union
from scripts.research.gt13a6_tie_review import endpoint_pair, raw_evidence, SOURCE_DIR, QUESTION
from scripts.research.gt13a6_cross_system_tie import render_segments, require_owner_confirmation
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes, line_y

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt13a5/gt13a5-output')
ORIGINAL_RECORD = Path(
    '/Users/juahnkim/Documents/Codex/2026-10-19/referenced-chatgpt-conversation-this-is-an-2/outputs/tie-owner-confirmation.json'
)
PACKET = ORIGINAL_RECORD.parent / 'gt13a6-source-review'
PROTOCOL = ROOT / 'docs/V4_GT13A6_PHASE2_PROTOCOL.json'
WHOLE = chr(0x1D15D)
SIZE = (2520, 1100)
VIEW = (130, 310, 2430, 1030)


def confirmed_record(record_path, packet):
    r = read(record_path)
    require(r.get('record_type') == 'GT13A6_OWNER_SOURCE_CONFIRMATION', 'Wrong confirmation record')
    require_owner_confirmation(r.get('status'))
    require(
        r.get('owner_response_verbatim', '').strip('` \n') == 'OWNER_CONFIRMED'
        and r.get('question') == QUESTION
        and bool(r.get('response_origin')),
        'Missing actual owner reply provenance',
    )
    require(
        r.get('source_curves') == ['sheet#1:4818', 'sheet#1:4798']
        and r.get('base_sha') == '20af28ea54d45d980da57ec3084790a2001b4d4e'
        and r.get('review_producer_commit_sha') == '596c8d716301d5c5bfc927f9a9d63652b65fa38c',
        'Wrong source/review revision',
    )
    for field, name in [
        ('review_sheet_sha256', 'source-tie-review-sheet.png'),
        ('checklist_sha256', 'tie-owner-checklist.json'),
        ('source_evidence_sha256', 'tie-source-evidence.json'),
        ('review_freeze_sha256', 'review-freeze.json'),
    ]:
        require(sha(packet / name) == r.get(field), 'Owner packet hash mismatch: ' + name)
    freeze = read(packet / 'review-freeze.json')
    require(all(sha(packet / n) == h for n, h in freeze['files'].items()), 'Review freeze mismatch')
    checklist = read(packet / 'tie-owner-checklist.json')
    require(
        checklist['review_sheet_sha256'] == r['review_sheet_sha256']
        and checklist['source_sha256'] == r['source_sha256'],
        'Checklist/source binding mismatch',
    )
    evidence = read(packet / 'tie-source-evidence.json')
    require(evidence['source_sha256'] == r['source_sha256'], 'Source provenance mismatch')
    return r


def whole_head(size, staff, x, target_pitch, font_path=FONT):
    """Same fixed-phase raster placement and head font scale as GT13A2, open glyph."""
    require(target_pitch in ('A3', 'G3'), 'Unsupported endpoint pitch')
    return calibrated_whole_head(size, staff, x, target_pitch, font_path)


def calibrated_whole_head(size, staff, x, target_pitch, font_path=FONT):
    """Existing whole glyph at an explicit semantic staff coordinate; no tie identity."""
    tt = TTFont(font_path)
    upm = tt['head'].unitsPerEm
    black = font_units(tt, HEAD)
    u = font_units(tt, WHOLE)
    font = ImageFont.truetype(
        str(font_path), round(1.25 * staff['interline'] * upm / (black[2] - black[0]))
    )
    pos = 35 - pitch.Pitch(target_pitch).diatonicNoteNum
    y = line_y(staff['lines'][2], x) + pos * staff['interline'] / 2
    mask, info = glyph(size, font, WHOLE, (x, y), u, font.size / upm)
    b = mask.getbbox()
    center = [(b[0] + b[2] - 1) / 2, (b[1] + b[3] - 1) / 2]
    residual = [center[0] - x, center[1] - y]
    require(max(map(abs, residual)) <= 0.5, 'Whole-note raster anchor failed')
    tile = np.asarray(mask.crop(b)) > 0
    _, labels, stats, _ = cv2.connectedComponentsWithStats((~tile).astype('uint8'), 8)
    holes = [
        i
        for i, s in enumerate(stats[1:], 1)
        if s[0] > 0 and s[1] > 0 and s[0] + s[2] < tile.shape[1] and s[1] + s[3] < tile.shape[0]
    ]
    require(bool(holes), 'Whole-note transparent center missing')
    info.update(
        target_pitch=target_pitch,
        staff_position=pos,
        independently_measured_raster_center=center,
        measured_residual=residual,
        transparent_hole_pixels=int(sum(stats[i, cv2.CC_STAT_AREA] for i in holes)),
        font_size=font.size,
    )
    return mask, info


def segment_spec(role, curve, source_box, target_box, viewport):
    index = 0 if role == 'OUTGOING' else -1
    source_ref = [(source_box[0] + source_box[2]) / 2, source_box[3]]
    target_ref = [(target_box[0] + target_box[2] - 1) / 2, target_box[3]]
    return {
        'role': role,
        'source_curve': curve,
        'dy': target_box[3] - source_box[3],
        'head_anchor': target_ref,
        'attachment_offset': [curve[index][i] - source_ref[i] for i in (0, 1)],
        'system_bbox': viewport,
    }


def gray_canvas(alpha):
    return Image.composite(
        Image.new('RGB', alpha.size, 'black'), Image.new('RGB', alpha.size, 'white'), alpha
    )


def context_panel(native, title):
    result = Image.new('RGB', (native.width, native.height + 150), 'white')
    draw = ImageDraw.Draw(result)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    for i, text in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE',
            'INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            'OWNER_VERIFIED_SOURCE; not independent ground truth; newly typeset standalone context',
        ]
    ):
        draw.text((10, 8 + 29 * i), text, font=font, fill='black')
    result.paste(native, (0, 150))
    return result


def run(out, record_path=ORIGINAL_RECORD, packet=PACKET):
    require(not out.exists(), 'Fresh output required')
    record = confirmed_record(record_path, packet)
    require(sha(SOURCE) == record['source_sha256'], 'Original source changed')
    evidence = read(packet / 'tie-source-evidence.json')
    pdf = evidence['source_pdf_provenance']
    require(sha(Path(pdf['path'])) == pdf['sha256'], 'Original PDF hash mismatch')
    omr = SOURCE_DIR / 'recognized.omr'
    require(sha(omr) == evidence['omr_sha256'], 'OMR hash mismatch')
    with zipfile.ZipFile(omr) as z:
        raw = z.read('sheet#1/sheet#1.xml')
    require(hashlib.sha256(raw).hexdigest() == evidence['raw_member_sha256'], 'Raw sheet mismatch')
    require(raw_evidence(raw) == evidence['raw_records'], 'Raw tie records differ')
    verify_freeze(PRIOR)
    verify_freeze(OLD)
    histories = {str(p): file_hashes(p) for p in (PRIOR, OLD, packet, ROOT / 'gt13a6-output')}
    record_hash = sha(record_path)
    protocol = read(PROTOCOL)
    require(sha(FONT) == protocol['font_sha256'], 'Font identity changed')
    graph = read(SOURCE_DIR / 'visual-graph.json')
    require(
        sha(SOURCE_DIR / 'visual-graph.json') == evidence['graph_sha256'], 'Graph hash mismatch'
    )
    staff = next(s for s in graph['staves'] if s['id'] == 'sheet#1:2')
    measure = next(
        m for m in graph['measures'] if m['system'] == staff['system'] and m['number'] == '5'
    )
    require(
        measure['bounds'][0] == 159 and measure['bounds'][2] == 639,
        'Second-system measure geometry differs',
    )
    incoming = graph['symbols']['sheet#1:1923']
    outgoing = graph['symbols']['sheet#1:1852']
    require(
        incoming['shape'] == 'WHOLE_NOTE' and incoming['system'] == staff['system'],
        'Endpoint symbol identity',
    )
    require(
        graph['symbols']['sheet#1:240']['shape'] == 'G_CLEF', 'Second-system clef evidence missing'
    )
    source_score = converter.parse(str(OLD / 'owner-associated-source.musicxml'))
    source_endpoints = endpoint_pair(source_score, 'B-3')
    guards = {}
    results = []
    images = []
    out.mkdir()
    (out / 'tie-owner-confirmation.json').write_bytes(record_path.read_bytes())
    dump(
        out / 'source-verification.json',
        {
            'classification': 'OWNER_VERIFIED_SOURCE',
            'independent_ground_truth': False,
            'confirmation_sha256': record_hash,
            'record_preserved_verbatim': True,
            'review_sheet_sha256': record['review_sheet_sha256'],
            'scope': record['confirmed_scope'],
            'source_endpoints': source_endpoints,
            'provenance_limit': 'Hash-bound coordinator record of human reply; not a cryptographic human signature',
        },
    )
    reports = read(
        Path(
            '/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output/provisional-rendering-report.json'
        )
    )
    for target, shift, target_pitch in [('A', -1, 'A3'), ('G', -3, 'G3')]:
        transposed = copy.deepcopy(source_score)
        summary = transpose_score(transposed, shift, 'key')
        mem = validate(source_score, transposed, shift, 'key', summary).to_dict()
        target_endpoints = endpoint_pair(transposed, target_pitch)
        frozen = converter.parse(str(OLD / f'{target}-transposed.musicxml'))
        disk = validate(source_score, frozen, shift, 'key').to_dict()
        require(
            mem['ok']
            and disk['ok']
            and endpoint_pair(frozen, target_pitch) == target_endpoints
            and full_lyric_signature(source_score) == full_lyric_signature(frozen),
            'Full semantic guard/endpoint failure',
        )
        guards[target] = {'in_memory': mem, 'frozen_serialized': disk}
        old_alpha = Image.open(PRIOR / f'{target}-local-notation-alpha.png').copy()
        first = Image.new('L', SIZE)
        first.paste(old_alpha, (0, 0))
        x = (incoming['geometry']['bbox'][0] + incoming['geometry']['bbox'][2]) / 2
        head, head_info = whole_head(SIZE, staff, x, target_pitch)
        context = {}
        lines = Image.new('L', SIZE)
        draw = ImageDraw.Draw(lines)
        for line in staff['lines']:
            draw.line([(159, line_y(line, 159)), (639, line_y(line, 639))], fill=255, width=2)
        draw.line(
            [(639, line_y(staff['lines'][0], 639)), (639, line_y(staff['lines'][-1], 639))],
            fill=255,
            width=2,
        )
        context['staff/barline'] = lines
        hp, hm = header(SIZE, staff, target, FONT)
        for n, m in hp.items():
            if n == 'clef' or n.startswith('sharp'):
                context[n] = m
        context['whole-head'] = head
        ledger = Image.new('L', SIZE)
        ld = ImageDraw.Draw(ledger)
        hb = head.getbbox()
        for pos in range(6, head_info['staff_position'] + 1, 2):
            y = line_y(staff['lines'][2], x) + pos * staff['interline'] / 2
            ld.line([(hb[0] - 4, y), (hb[2] + 3, y)], fill=255, width=2)
        context['ledger'] = ledger
        require(
            not np.any(
                (np.asarray(head) > 0)
                & (
                    np.asarray(
                        union([m for n, m in context.items() if n not in ['whole-head', 'ledger']])
                    )
                    > 0
                )
            ),
            'Whole head/unrelated context collision',
        )
        before_alpha = union([first, *context.values()])
        metric = next(r for r in reports if r['target'] == target)
        last = next(e for e in metric['event_metrics'] if e['id'] == 'p1:m3:n6')
        require(
            last['target_pitch'] == target_pitch and max(map(abs, last['anchor_residual'])) <= 0.5,
            'Frozen outgoing anchor failure',
        )
        specs = [
            segment_spec(
                'OUTGOING',
                graph['symbols']['sheet#1:4818']['geometry']['curve'],
                outgoing['geometry']['bbox'],
                last['rendered_bounds'],
                [130, 310, 2430, 720],
            ),
            segment_spec(
                'INCOMING',
                graph['symbols']['sheet#1:4798']['geometry']['curve'],
                incoming['geometry']['bbox'],
                hb,
                [130, 750, 2430, 1030],
            ),
        ]
        ties, tie_info = render_segments(SIZE, *specs, unrelated_ink=before_alpha)
        tie_union = union(list(ties.values()))
        alpha = union([before_alpha, tie_union])
        binary = Image.fromarray((np.asarray(tie_union) > 0).astype('uint8') * 255)
        integrity = validate_pixel_integrity(gray_canvas(before_alpha), gray_canvas(alpha), binary)
        require(
            first.crop((0, 0, 2520, 750)).tobytes() == old_alpha.tobytes(),
            'Frozen first-system masks changed',
        )
        lyric = Image.new('L', SIZE)
        lyric.paste(Image.open(PRIOR / f'{target}-local-lyric-alpha.png'), (0, 0))
        music = Image.new('L', SIZE)
        music.paste(Image.open(OLD / f'{target}-owner-confirmed-event-alpha.png'), (0, 0))
        lyric_contacts = int(
            np.count_nonzero((np.asarray(lyric) > 0) & (np.asarray(union([music, tie_union])) > 0))
        )
        require(lyric_contacts == 0, 'New tie/lyric collision')
        distance = ink_distance(before_alpha)
        nearest = {n: float(distance[np.asarray(mask) > 0].min()) for n, mask in ties.items()}
        lyric_distance = ink_distance(lyric)
        lyric_clearance = float(lyric_distance[np.asarray(tie_union) > 0].min())
        require(lyric_clearance >= 2, 'Existing positive lyric clearance not preserved')
        for n, m in ties.items():
            m.save(out / f'{target}-{n.lower()}-tie-alpha.png')
        head.save(out / f'{target}-whole-note-alpha.png')
        ledger.save(out / f'{target}-whole-ledger-alpha.png')
        first.save(out / f'{target}-frozen-first-system-alpha.png')
        alpha.save(out / f'{target}-two-system-alpha.png')
        before_alpha.save(out / f'{target}-before-tie-alpha.png')
        image = context_panel(
            gray_canvas(alpha).crop(VIEW),
            f'{target} major: owner-confirmed m4 to m5 tie; second system shows m5 endpoint only',
        )
        d = ImageDraw.Draw(image)
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
        label = 'MEASURE 5 ENDPOINT CONTEXT ONLY - remaining second-system music/chords/lyrics NOT RENDERED'
        # Empty right side of the second-system viewport, not over source or score ink.
        d.text((650, VIEW[3] - VIEW[1] + 20), label, font=font, fill='black')
        image.save(out / f'predicted-{target.lower()}-tie.png')
        images.append(image)
        results.append(
            {
                'target': target,
                'source_endpoints': source_endpoints,
                'target_endpoints': target_endpoints,
                'semantic_source_staff_coordinate': [
                    x,
                    line_y(staff['lines'][2], x) + 7 * staff['interline'] / 2,
                ],
                'physical_source_head_center': [
                    (incoming['geometry']['bbox'][0] + incoming['geometry']['bbox'][2]) / 2,
                    (incoming['geometry']['bbox'][1] + incoming['geometry']['bbox'][3]) / 2,
                ],
                'incoming_whole_note': head_info,
                'outgoing_frozen_head': last,
                'segments': tie_info,
                'segment_specs': specs,
                'tie_unrelated_contacts': 0,
                'tie_lyric_contacts': lyric_contacts,
                'tie_to_existing_ink_min_center_px': nearest,
                'tie_to_lyric_min_center_px': lyric_clearance,
                'head_ledger_intentional_contact_pixels': int(
                    np.count_nonzero((np.asarray(head) > 0) & (np.asarray(ledger) > 0))
                ),
                'first_system_frozen_layer_byte_identical': True,
                'pixel_integrity_on_generated_canvas_only': integrity,
                'second_system_measure_bounds': measure['bounds'],
                'header_context': 'clef/key only; no invented repeat/time',
                'SOURCE_VERIFICATION': 'OWNER_VERIFIED_SOURCE',
                'TIE_RENDERING_COMPLETENESS': 'COMPLETE_SCOPED_TWO_SEGMENT_CONTEXT',
                'VISUAL_QUALITY': 'PENDING_POST_FREEZE_INSPECTION',
                'full_score': 'INCOMPLETE',
            }
        )
    contact = Image.new('RGB', (images[0].width, sum(i.height for i in images)), 'white')
    y = 0
    for image in images:
        contact.paste(image, (0, y))
        y += image.height
    contact.save(out / 'tie-comparison-contact-sheet.png')
    Image.open(SOURCE).crop(VIEW).save(out / 'original-bb-two-system-context.png')
    dump(out / 'endpoint-rendering-validation.json', results)
    dump(out / 'semantic-integrity.json', guards)
    require(
        sha(record_path) == record_hash
        and all(file_hashes(Path(p)) == h for p, h in histories.items()),
        'Historical/owner-record change',
    )
    require(
        sha(Path(pdf['path'])) == pdf['sha256'] and sha(SOURCE) == record['source_sha256'],
        'Original PDF/raster change',
    )
    dump(
        out / 'input-freeze.json',
        {
            'history_files': histories,
            'confirmation_sha256': record_hash,
            'source_sha256': sha(SOURCE),
            'omr_sha256': sha(omr),
            'font_sha256': sha(FONT),
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
        },
    )
    dump(
        out / 'validation-summary.json',
        {
            'SOURCE_VERIFICATION': 'OWNER_VERIFIED_SOURCE',
            'TIE_RENDERING_COMPLETENESS': 'COMPLETE_SCOPED_TWO_SEGMENT_CONTEXT',
            'VISUAL_QUALITY': 'PENDING_POST_FREEZE_INSPECTION',
            'status': 'FULL_SCORE_INCOMPLETE',
            'independent_ground_truth': False,
            'first_system_music_lyric_geometry_changed': False,
            'notes_visible': '26 frozen first-system events plus confirmed m5 whole-note endpoint',
            'remaining_second_system_notation_lyrics_chords': 'NOT_RENDERED',
            'source_ink_edit_authorization': False,
            'real_two_segment_ties_rendered': True,
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {'files': file_hashes(out), 'phase': 'BEFORE_AGENT_VISUAL_REVIEW'},
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
