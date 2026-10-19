"""Owner-bound source update and standalone reuse of frozen GT13A2 notation."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, harmony, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.chords import chord_symbol_from_text, chord_text, transpose_chord_text
from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import (
    FONT,
    GT01,
    event_signature,
    events_of,
    read,
    require,
)
from scripts.research.gt12_render_context import (
    GT11,
    KOREAN_FONT,
    ink_bbox,
    lyric_signature,
    text_mask,
)
from scripts.research.gt13a_full_system import CANDIDATES, CROP, GT12
from scripts.research.gt13a2_provisional import annotation_metrics, ink_distance
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output')
PROTOCOL = ROOT / 'docs/V4_GT13A3_PROTOCOL.json'
APPROVAL = ROOT / 'docs/evidence/GT13A3_OWNER_APPROVAL.txt'
# Exact owner-confirmed checklist, canonical music21 flat spelling and rational timing.
QUARTERS = [
    (None, '0', '1', None),
    ('B-3', '1', '1', None),
    ('C4', '2', '1', None),
    ('F4', '3', '1', None),
]
MIXED = [
    (None, '0', '1', None),
    (None, '1', '1/2', None),
    ('F3', '3/2', '1/2', None),
    ('D4', '2', '1/2', None),
    ('C4', '5/2', '1/4', None),
    ('C4', '11/4', '1/4', 'start'),
    ('C4', '3', '1/4', 'stop'),
    ('B-3', '13/4', '1/2', None),
]
EXPECTED = {
    1: QUARTERS,
    2: MIXED + [('C4', '15/4', '1/4', None)],
    4: MIXED + [('B-3', '15/4', '1/4', 'start')],
}


def verify_events(events, expected):
    """Do not promote a row that differs from the actual owner checklist."""
    require(len(events) == len(expected), 'Owner checklist count mismatch')
    for e, (written, onset, duration, tie) in zip(events, expected):
        require(e['kind'] == ('NOTE' if written else 'REST'), 'Owner event kind mismatch')
        require(e['pitch'] == written, 'Owner pitch mismatch')
        require(Fraction(e['onset']) == Fraction(onset), 'Owner onset mismatch')
        require(Fraction(e['duration']) == Fraction(duration), 'Owner duration mismatch')
        require(e['tie'] == tie, 'Owner tie mismatch')


def confirmed_inventory(old, message_sha):
    result = copy.deepcopy(old)
    require([m['printed_measure'] for m in result['measures']] == [1, 2, 3, 4], 'Wrong fixed scope')
    seen = set()
    for m in result['measures']:
        n = m['printed_measure']
        if n == 3:
            continue  # Original GT12 classification/confirmation references remain untouched.
        verify_events(m['events'], EXPECTED[n])
        for e in m['events']:
            require(e['event_id'] not in seen, 'Duplicate owner event identity')
            seen.add(e['event_id'])
            e.update(
                source_verification='OWNER_VERIFIED_SOURCE',
                render_evidence='OWNER_VERIFIED_SOURCE',
                owner_confirmation_sha256=message_sha,
            )
        m.update(
            content_status='OWNER_VERIFIED_SOURCE',
            render_action='REUSE_FROZEN_COMPONENTS',
            lyric_strings_status='OWNER_CONFIRMED_LYRIC_TRANSCRIPTION',
            lyric_note_associations='UNVERIFIED; no promotion from music-event approval',
            confirmed_newly_printed_chord='Bb' if n == 1 else None,
            chord_absence_scope='No newly printed chord identified; no new event or carry inferred',
        )
    result.update(
        owner_verified_measure_scope=[1, 2, 3, 4],
        owner_verified_music_event_count=26,
        newly_verified_event_count=22,
        independent_ground_truth=False,
        owner_approval_message_sha256=message_sha,
        outgoing_tie={
            'start': 'OWNER_VERIFIED_SOURCE',
            'destination': 'UNVERIFIED',
            'complete_cross_system_geometry': 'UNVERIFIED',
            'renderer_status': 'UNSUPPORTED_OR_UNRESOLVED',
        },
        source_completeness='OWNER_VERIFIED_LISTED_EVENTS; full-system reconstruction still incomplete',
    )
    return result


def add_confirmed_chord(score):
    """Create a separate research stream; never repair or mutate the frozen source."""
    result = copy.deepcopy(score)
    measures = list(result.parts[0].getElementsByClass(stream.Measure))
    require(
        not list(measures[0].getElementsByClass(harmony.ChordSymbol)),
        'Unexpected existing m1 harmony',
    )
    require(
        not any(list(measures[i].getElementsByClass(harmony.ChordSymbol)) for i in (1, 3)),
        'Do not invent/merge m2 or m4 chord events',
    )
    before = [event_signature(m) for m in measures]
    measures[0].insert(0, chord_symbol_from_text('Bb'))
    require([event_signature(m) for m in measures] == before, 'Music event geometry/timing changed')
    return result


def owner_panel(image, title, *, target=None, music=None, score_ink=None):
    header, footer = 250, 160
    size = (image.width, image.height + header + footer)
    view = (0, header, image.width, header + image.height)
    result = Image.new('RGB', size, 'white')
    result.paste(image, (0, header))
    masks = []

    def write(xy, text, font=None):
        mask = Image.new('L', size)
        ImageDraw.Draw(mask).text(xy, text, fill=255, font=font)
        require(mask.getbbox() is not None, 'Missing diagnostic text')
        result.paste('black', (0, 0, *size), mask)
        masks.append((text, mask))

    lines = [
        'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / FULL_SYSTEM_INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
        title,
        '26/26 displayed musical events: OWNER_VERIFIED_SOURCE; NOT_INDEPENDENT_GROUND_TRUTH.',
        'Black: confirmed musical events / chords. Amber m1 lyrics: transcription confirmed, note association still unverified.',
        'm3: original GT12 approval and rendering unchanged. New m1 chord: Bb -> A/G, original print location.',
        'OWNER_CONFIRMED_LYRIC_TRANSCRIPTION: no duplicate confirmation requested; m2/4 note associations pending.',
        'm2/4 strings in footer are transcription context, not aligned lyric engraving.',
        'Remaining: clef/key/time/forward-repeat glyph context and unresolved outgoing m4 tie destination/geometry.',
        'G-clef/target key context is caption-only. No original ink removal or original lyric-pixel composition.',
    ]
    for i, t in enumerate(lines):
        write((8, 5 + 22 * i), t)
    if target is not None:
        for column, n in enumerate((2, 4)):
            x = 10 + column * (image.width // 2)
            write(
                (x, header + image.height + 20),
                f'm{n}: OWNER_CONFIRMED_LYRIC_TRANSCRIPTION; association PENDING',
            )
            for row, key in enumerate(('upper', 'lower')):
                write(
                    (x, header + image.height + 50 + 40 * row),
                    ' / '.join(CANDIDATES[n][key]),
                    ImageFont.truetype(str(KOREAN_FONT), 22),
                )
    metrics = []
    combined = Image.new('L', size)
    if music is not None:
        mm, ss = Image.new('L', size), Image.new('L', size)
        mm.paste(music, (0, header))
        ss.paste(score_ink, (0, header))
        md, sd = ink_distance(mm), ink_distance(ss)
        for t, mask in masks:
            a = annotation_metrics(mask, mm, md, view)
            b = annotation_metrics(mask, ss, sd, view)
            require(
                a['notation_region_pixels'] == a['ink_contacts'] == b['ink_contacts'] == 0,
                'Annotation collides with score',
            )
            metrics.append({'text': t, **a, 'all_score_ink': b})
            combined = Image.fromarray(np.maximum(np.asarray(combined), np.asarray(mask)))
    require(result.crop(view).tobytes() == image.tobytes(), 'Panel altered native notation pixels')
    return result, metrics, combined


def run(out):
    require(not out.exists(), 'New run directory required')
    prior_freeze = read(PRIOR / 'prediction-freeze.json')
    require(
        all(sha(PRIOR / p) == h for p, h in prior_freeze['files'].items()), 'GT13A2 freeze mismatch'
    )
    history_roots = [
        PRIOR,
        GT12,
        Path('/private/tmp/capomatic-v4-gt13a/gt13a-output'),
        Path('/private/tmp/capomatic-v4-gt13a2/gt13a2-output'),
    ]
    histories = {str(p): file_hashes(p) for p in history_roots}
    protocol = read(PROTOCOL)
    require(
        sha(APPROVAL) == protocol['owner_message_sha256'], 'Actual owner approval bytes changed'
    )
    source_path = GT01 / 'predictions/baseline-exec/source/source.png'
    require(
        sha(source_path) == read(PRIOR / 'input-freeze.json')['source'], 'Source binding mismatch'
    )
    inventory = confirmed_inventory(read(PRIOR / 'source-event-inventory.json'), sha(APPROVAL))
    source = Image.open(source_path)
    size = (source.width, 750)
    prior_source = converter.parse(str(GT12 / 'confirmed-context/owner-augmented-source.musicxml'))
    for m in inventory['measures']:
        notes = events_of(
            list(prior_source.parts[0].getElementsByClass(stream.Measure))[m['printed_measure'] - 1]
        )
        require(len(notes) == len(m['events']), 'Frozen semantics/checklist count differs')
        for n, e in zip(notes, m['events']):
            require(
                (n.pitch.nameWithOctave if n.isNote else None) == e['pitch']
                and Fraction(n.quarterLength) == Fraction(e['duration'])
                and Fraction(n.offset) == Fraction(e['onset'])
                and getattr(n.tie, 'type', None) == e['tie'],
                'Frozen semantics differ from confirmed checklist',
            )
    out.mkdir()
    (out / 'owner-approval-verbatim.txt').write_bytes(APPROVAL.read_bytes())
    dump(out / 'source-event-inventory.json', inventory)
    dump(
        out / 'owner-normalized-checklist.json',
        {
            'classification': 'OWNER_VERIFIED_SOURCE',
            'independent_ground_truth': False,
            'source': 'Bb PDF page 2 / first system',
            'confirmed_events': {
                str(n): [{'pitch': p, 'onset': o, 'duration': d, 'tie': t} for p, o, d, t in events]
                for n, events in EXPECTED.items()
            },
            'm1_chord': {'text': 'Bb', 'quality': 'major', 'suffix': '', 'slash_bass': None},
            'm2_m4_newly_printed_chords': [],
            'm3_confirmation': 'ORIGINAL_GT12_REFERENCE_UNCHANGED',
            'lyric_transcription': 'OWNER_CONFIRMED_LYRIC_TRANSCRIPTION',
            'm2_m4_lyric_associations': 'PENDING',
            'outgoing_tie_destination': 'UNVERIFIED',
            'actual_approval_sha256': sha(APPROVAL),
        },
    )
    dump(
        out / 'owner-evidence-binding.json',
        {
            'classification': 'OWNER_VERIFIED_SOURCE',
            'independent_ground_truth': False,
            'owner_message': {'file': str(APPROVAL), 'sha256': sha(APPROVAL)},
            'review_context': {
                'source_page': 2,
                'key': 'Bb',
                'printed_measures': [1, 2, 3, 4],
                'source_raster_sha256': sha(source_path),
                'native_source_review_crop_sha256': sha(PRIOR / 'original-bb.png'),
                'frozen_checklist_sha256': sha(PRIOR / 'source-event-inventory.json'),
                'GT13A2_prediction_freeze_sha256': sha(PRIOR / 'prediction-freeze.json'),
                'GT12_original_confirmation': {
                    'file': str(GT12 / 'confirmed-context/owner-visual-confirmation.txt'),
                    'sha256': sha(GT12 / 'confirmed-context/owner-visual-confirmation.txt'),
                },
            },
            'binding_method': 'Coordinator post-approval artifact binding to the explicit current user message. No claim that owner supplied/signed these hashes.',
            'human_signatures_fabricated': False,
            'source_removal_authorized': False,
            'original_pixel_composition_authorized': False,
        },
    )
    dump(
        out / 'input-freeze.json',
        {
            'base': protocol['base'],
            'protocol_sha256': sha(PROTOCOL),
            'history_files': histories,
            'font_sha256': sha(FONT),
            'source_sha256': sha(source_path),
            'checklist_sha256': sha(out / 'source-event-inventory.json'),
            'owner_binding_sha256': sha(out / 'owner-evidence-binding.json'),
        },
    )
    source.crop(CROP).save(out / 'original-bb.png')
    require(sha(out / 'original-bb.png') == sha(PRIOR / 'original-bb.png'), 'Source crop changed')
    augmented = add_confirmed_chord(prior_source)
    augmented.write('musicxml', fp=str(out / 'owner-augmented-source.musicxml'))
    parsed_source = converter.parse(str(out / 'owner-augmented-source.musicxml'))
    guards = {'source_serialization': validate(augmented, parsed_source, 0, 'key').to_dict()}
    require(guards['source_serialization']['ok'], 'Full source roundtrip guard failed')
    require(lyric_signature(parsed_source) == lyric_signature(augmented), 'Source lyrics changed')
    chord_window = protocol['source_chord_window']
    source_box = ink_bbox(source, chord_window)
    panels = [
        owner_panel(source.crop(CROP), 'Original Bb source image; unchanged native pixels')[0]
    ]
    reports = []
    for target, shift in [('A', -1), ('G', -3)]:
        transposed = copy.deepcopy(augmented)
        summary = transpose_score(transposed, shift, 'key')
        mem = validate(augmented, transposed, shift, 'key', summary).to_dict()
        transposed.write('musicxml', fp=str(out / f'{target}-transposed.musicxml'))
        parsed = converter.parse(str(out / f'{target}-transposed.musicxml'))
        serialized = validate(augmented, parsed, shift, 'key', summary).to_dict()
        require(mem['ok'] and serialized['ok'], 'Unchanged full V3 guard failed')
        frozen_target = converter.parse(
            str(GT12 / f'confirmed-context/{target}-transposed.musicxml')
        )
        require(
            [event_signature(m) for m in parsed.parts[0].getElementsByClass(stream.Measure)]
            == [
                event_signature(m)
                for m in frozen_target.parts[0].getElementsByClass(stream.Measure)
            ],
            'Musical events changed from frozen targets',
        )
        require(
            lyric_signature(parsed) == lyric_signature(augmented), 'Target lyric semantics changed'
        )
        measures = list(parsed.parts[0].getElementsByClass(stream.Measure))
        expected = transpose_chord_text('Bb', shift, original_key='Bb', target_key=target)
        harmonies = list(measures[0].getElementsByClass(harmony.ChordSymbol))
        require(
            len(harmonies) == 1
            and harmonies[0].offset == 0
            and chord_text(harmonies[0]) == expected == target,
            'Confirmed Bb chord transposition/measure context mismatch',
        )
        require(
            not any(list(measures[i].getElementsByClass(harmony.ChordSymbol)) for i in (1, 3)),
            'New m2/4 harmony invented',
        )
        require(
            [chord_text(c) for c in measures[2].getElementsByClass(harmony.ChordSymbol)]
            == [
                chord_text(c)
                for c in list(frozen_target.parts[0].getElementsByClass(stream.Measure))[
                    2
                ].getElementsByClass(harmony.ChordSymbol)
            ],
            'GT12 m3 harmony changed',
        )
        guards[target] = {'in_memory': mem, 'serialized': serialized}
        provisional = Image.open(PRIOR / f'{target}-provisional-alpha.png').copy()
        cached = Image.open(GT12 / f'confirmed-context/{target}-combined-alpha.png').crop(
            (0, 0, *size)
        )
        scaffold = Image.open(
            '/private/tmp/capomatic-v4-gt13a/gt13a-output/staff-and-boundary-scaffold.png'
        ).crop((0, 0, *size))
        base_alpha = Image.fromarray(
            np.maximum.reduce([np.asarray(p) for p in [provisional, cached, scaffold]])
        )
        chord, chord_info = text_mask(
            size, ImageFont.truetype(str(FONT), 40), expected, left_top=source_box[:2]
        )
        require(
            chord.getbbox()[:2] == tuple(source_box[:2]), 'Chord moved from source print anchor'
        )
        count = int(np.count_nonzero((np.asarray(chord) > 0) & (np.asarray(base_alpha) > 0)))
        require(count == 0, 'New chord collides with existing notation/text')
        b = chord.getbbox()
        require(
            CROP[0] <= b[0] < b[2] <= CROP[2] and CROP[1] <= b[1] < b[3] <= CROP[3], 'Chord clipped'
        )
        require(chord.crop((1374, 310, 1783, 720)).getbbox() is None, 'New chord invades m3')
        all_alpha = Image.fromarray(np.maximum(np.asarray(base_alpha), np.asarray(chord)))
        canvas = Image.composite(
            Image.new('RGB', size, 'black'), Image.new('RGB', size, 'white'), all_alpha
        )
        lyric_union = Image.new('L', size)
        for row in (0, 1):
            for e in inventory['measures'][0]['events']:
                if e['kind'] == 'NOTE':
                    name = f'{target}-lyric_{row}_{e["event_id"].replace(":","_")}.png'
                    require(
                        sha(PRIOR / name) == prior_freeze['files'][name],
                        'Frozen lyric component changed',
                    )
                    lyric_union = Image.fromarray(
                        np.maximum(np.asarray(lyric_union), np.asarray(Image.open(PRIOR / name)))
                    )
        canvas = Image.composite(Image.new('RGB', size, (155, 85, 0)), canvas, lyric_union)
        # Reuse exact glyph masks for pixel-distance checks; no inverse segmentation.
        music_path = GT11 / f'gt11-output/components/{target}/music-only-alpha.png'
        require(
            sha(music_path)
            == read(GT11 / 'gt11-output/prediction-freeze.json')['files'][
                f'components/{target}/music-only-alpha.png'
            ],
            'GT12 music-only binding changed',
        )
        music = np.asarray(Image.open(music_path).crop((0, 0, *size))).copy()
        components = {}
        for name, h in prior_freeze['files'].items():
            if name.startswith((target + '-p1_', target + '-sheet#1_')) and name.endswith('.png'):
                require(sha(PRIOR / name) == h, 'Frozen musical glyph changed')
                components[name] = h
                music = np.maximum(music, np.asarray(Image.open(PRIOR / name)))
        require(len(components) > 0, 'Musical components missing')
        panel, ann, ann_mask = owner_panel(
            canvas.crop(CROP),
            f'{target} major / first-system owner-confirmed events; FULL_SYSTEM_INCOMPLETE',
            target=target,
            music=Image.fromarray(music).crop(CROP),
            score_ink=all_alpha.crop(CROP),
        )
        panel.save(out / f'predicted-{target.lower()}.png')
        panels.append(panel)
        chord.save(out / f'{target}-new-chord-alpha.png')
        all_alpha.save(out / f'{target}-notation-alpha.png')
        ann_mask.save(out / f'{target}-annotation-alpha.png')
        canvas.crop(CROP).save(out / f'{target}-native-notation-viewport.png')
        Image.fromarray(music).save(out / f'{target}-confirmed-music-event-alpha.png')
        native_m3 = (1374 - CROP[0], 0, 1783 - CROP[0], CROP[3] - CROP[1])
        prior_m3 = Image.open(PRIOR / f'{target}-notation-viewport.png').crop(native_m3)
        require(
            canvas.crop(CROP).crop(native_m3).tobytes() == prior_m3.tobytes(),
            'GT12 m3 rendered pixels changed',
        )
        event_report = next(
            r for r in read(PRIOR / 'provisional-rendering-report.json') if r['target'] == target
        )
        reports.append(
            {
                'target': target,
                'recognized_events': 26,
                'displayed_events': 26,
                'owner_verified_music_events': 26,
                'provisional_music_events': 0,
                'independent_ground_truth': False,
                'source_checklist_verification': 'OWNER_VERIFIED_SOURCE; not an independent completeness assessment',
                'new_chord': {
                    'source': 'Bb',
                    'target': expected,
                    'source_window': chord_window,
                    'source_bbox': source_box,
                    'print_anchor': source_box[:2],
                    'semantic_offset': '0 (measure-start context; no first-pitched-note attachment)',
                    'new_chord_existing_ink_contacts': count,
                    **chord_info,
                },
                'music_component_bindings': components,
                'music_geometry': 'EXACT_FROZEN_GT13A2_MASK_REUSE',
                'notehead_max_residual_px': event_report['max_head_residual'],
                'prior_music_event_metrics': event_report['event_metrics'],
                'm3_alpha_sha256': sha(GT12 / f'confirmed-context/{target}-combined-alpha.png'),
                'lyric_strings_evidence': 'OWNER_CONFIRMED_LYRIC_TRANSCRIPTION',
                'm1_lyric_association': 'UNVERIFIED; original provisional placement retained, amber ink',
                'm2_m4_lyric_association': 'PENDING; footer transcription only',
                'outgoing_tie': 'Start OWNER_VERIFIED_SOURCE; destination/geometry UNVERIFIED, not rendered',
                'annotation_metrics': ann,
                'full_system_status': 'FULL_SYSTEM_INCOMPLETE',
            }
        )
    sheet = Image.new('RGB', (panels[0].width, sum(p.height for p in panels)), 'white')
    for i, p in enumerate(panels):
        sheet.paste(p, (0, i * p.height))
    sheet.save(out / 'comparison-contact-sheet.png')
    dump(out / 'rendering-report.json', reports)
    dump(out / 'semantic-integrity.json', guards)
    dump(
        out / 'remaining-blockers.json',
        {
            'status': 'FULL_SYSTEM_INCOMPLETE',
            'blockers': [
                'Header clef/key/time/forward-repeat glyph placement',
                'm4 outgoing tie destination and full cross-system geometry',
                'm2/4 exact syllable-to-note associations',
                'm1 lyric association not explicitly promoted by current approval',
                'General engraving/optical and independent reference validation',
            ],
            'GT13A4_preparation_only': True,
            'no_additional_chords_in_m2_or_m4': True,
        },
    )
    require(
        all(file_hashes(Path(p)) == h for p, h in histories.items()), 'Historical artifacts changed'
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'base': protocol['base'],
            'code_sha256': sha(Path(__file__)),
            'files': file_hashes(out),
            'phase': 'BEFORE_AGENT_VISUAL_REVIEW',
        },
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
