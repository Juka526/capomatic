"""GT13A4 source review packets plus standalone header experiment."""

import argparse
import copy
from fractions import Fraction
from pathlib import Path

import numpy as np
from music21 import converter, harmony, meter, stream
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from scripts.research.gt11_complete_measure import GT01, event_signature, read, require
from scripts.research.gt12_render_context import FONT, GT11, KOREAN_FONT, lyric_signature
from scripts.research.gt13a_full_system import CANDIDATES, CROP, GT12, scaffold
from scripts.research.gt13a2_provisional import annotation_metrics, ink_distance
from scripts.research.gt13a4_header import header
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
PRIOR = Path('/private/tmp/capomatic-v4-gt13a3/gt13a3-output')
GT02 = Path('/private/tmp/capomatic-v4-ground-truth-02/ground-truth-02-output')
PROTOCOL = ROOT / 'docs/V4_GT13A4_PROTOCOL.json'


def proposed_lyrics(inventory):
    """Review proposals only: string confirmation is never association confirmation."""
    audit = []
    for m in inventory['measures']:
        number = m['printed_measure']
        if number == 3:
            continue
        rows = [CANDIDATES[number]['upper'], CANDIDATES[number]['lower']]
        at = 0
        items = []
        last = None
        for e in m['events']:
            candidate = [None, None]
            mode = 'NO_SYLLABLE_CANDIDATE'
            if e['kind'] == 'NOTE':
                if e['tie'] == 'stop':
                    mode = 'TIED_CONTINUATION_NO_NEW_SYLLABLE'
                    candidate = last
                else:
                    require(
                        at < len(rows[0]) and at < len(rows[1]), 'Candidate lyric count differs'
                    )
                    candidate = [r[at] for r in rows]
                    last = candidate
                    at += 1
                    mode = 'SYLLABLE_START'
            items.append(
                {
                    'event_id': e['event_id'],
                    'pitch': e['pitch'],
                    'onset': e['onset'],
                    'duration': e['duration'],
                    'source_bbox': e['source_bbox'],
                    'upper_candidate': candidate[0],
                    'lower_candidate': candidate[1],
                    'candidate_relation': mode,
                    'tie': e['tie'],
                    'extender_candidate': e['tie'] == 'start',
                    'new_syllable_candidate': mode == 'SYLLABLE_START',
                    'association_status': 'OWNER_REVIEW_PENDING',
                    'classification': 'ASSISTANT_PROPOSED_ASSOCIATION',
                }
            )
        require(at == len(rows[0]) == len(rows[1]), 'Unconsumed candidate syllables')
        audit.append(
            {
                'printed_measure': number,
                'transcription_status': 'OWNER_CONFIRMED_LYRIC_TRANSCRIPTION',
                'transcription_reconfirmation_requested': False,
                'note_association_status': 'OWNER_REVIEW_PENDING',
                'events': items,
                'outgoing_extender': 'PENDING_DESTINATION_REVIEW' if number == 4 else None,
            }
        )
    return audit


def tie_evidence(graph, events, source_score):
    symbols = graph['symbols']
    a = symbols['sheet#1:4818']
    b = symbols['sheet#1:4798']
    require(
        dict(a['attributes']).get('right-extension') == '4798'
        and dict(b['attributes']).get('left-extension') == '4818',
        'Nonreciprocal continuation evidence',
    )
    rel = [
        r
        for r in graph['relations']
        if r['source'] in [a['id'], b['id']] and r['kind'] == 'slur-head'
    ]
    require(len(rel) == 2, 'Ambiguous cross-system head linkage')
    links = {dict(r['attributes'])['side']: r['target'] for r in rel}
    require(set(links) == {'LEFT', 'RIGHT'}, 'Missing tie side')
    matched = {
        side: [e for e in events if e['symbol_id'] == ident] for side, ident in links.items()
    }
    require(all(len(v) == 1 for v in matched.values()), 'Ambiguous semantic correspondence')
    rows = {side: v[0] for side, v in matched.items()}
    measures = list(source_score.parts[0].getElementsByClass(stream.Measure))
    from scripts.research.gt11_complete_measure import events_of

    sem = {}
    for side, e in rows.items():
        m = measures[e['omr_measure_index']]
        n = [
            n
            for n in events_of(m)
            if Fraction(n.getOffsetInHierarchy(m)) == Fraction(e['local_offset'])
        ]
        require(len(n) == 1 and n[0].isNote, 'Tie semantic event missing')
        sem[side] = {
            'pitch': n[0].pitch.nameWithOctave,
            'duration': str(n[0].quarterLength),
            'tie': getattr(n[0].tie, 'type', None),
        }
    supported = (
        sem['LEFT']['pitch'] == sem['RIGHT']['pitch']
        and sem['LEFT']['tie'] == 'start'
        and sem['RIGHT']['tie'] == 'stop'
    )
    return {
        'classification': (
            'OMR_SUPPORTED_CANDIDATE_PENDING_OWNER' if supported else 'EVIDENCE_DISAGREEMENT'
        ),
        'owner_confirmed_start': True,
        'owner_confirmed_destination': False,
        'destination_candidate': rows['RIGHT'],
        'start_event': rows['LEFT'],
        'semantic_evidence': sem,
        'curve_segments': [a, b],
        'head_relations': rel,
        'extension_relations': [
            r
            for r in graph['relations']
            if r['kind'] in ['left-extension', 'right-extension']
            and r['source'] in [a['id'], b['id']]
        ],
        'staff_pitch_evidence': {
            k: {
                'symbol_id': v,
                'pitch_position': symbols[v]['pitch_position'],
                'staff': symbols[v]['staff'],
            }
            for k, v in links.items()
        },
        'complete_tie_rendered': False,
        'destination_status': 'UNVERIFIED',
        'full_cross_system_geometry': 'UNVERIFIED_RENDER_CONTRACT',
    }


def panel(
    image,
    title,
    target=None,
    music=None,
    all_ink=None,
    *,
    associations_confirmed=False,
    lyric_contacts=0,
):
    header_height, footer = 250, 160
    size = (image.width, image.height + header_height + footer)
    view = (0, header_height, image.width, header_height + image.height)
    result = Image.new('RGB', size, 'white')
    result.paste(image, (0, header_height))
    rows = []

    def write(xy, text, font=None):
        mask = Image.new('L', size)
        ImageDraw.Draw(mask).text(xy, text, font=font, fill=255)
        result.paste('black', (0, 0, *size), mask)
        rows.append((text, mask))

    lines = [
        'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / FULL_SYSTEM_INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
        title,
        '26 OWNER_VERIFIED_SOURCE music events; two confirmed chords. NOT_INDEPENDENT_GROUND_TRUTH.',
        'Actual treble clef, target key, 4/4 and forward repeat engraved. Experimental font-specific header placement.',
        'Existing note/rest/chord geometry unchanged; m3 original GT12 region unchanged.',
        (
            'm1/2/4 lyric associations OWNER_VERIFIED; lyrics newly typeset, not original-pixel preservation.'
            if associations_confirmed
            else 'Amber m1 lyric association pending. m2/4 footer is confirmed transcription, not aligned lyric engraving.'
        ),
        'Next-system Bb3 whole-note tie-stop is OMR-supported candidate ONLY; owner destination review pending.',
        f'Outgoing tie NOT completed or drawn. Lyric/music contact pixels: {lyric_contacts}. Any contacts BLOCK visual safety.',
    ]
    for i, t in enumerate(lines):
        write((8, 5 + 22 * i), t)
    if target:
        for col, n in enumerate((2, 4)):
            x = 10 + col * (image.width // 2)
            write(
                (x, header_height + image.height + 20),
                (
                    f'm{n}: confirmed association / aligned lyric engraving above'
                    if associations_confirmed
                    else f'm{n}: confirmed strings / exact note association PENDING'
                ),
            )
            for row, key in enumerate(('upper', 'lower')):
                write(
                    (x, header_height + image.height + 50 + 40 * row),
                    ' / '.join(CANDIDATES[n][key]),
                    ImageFont.truetype(str(KOREAN_FONT), 22),
                )
    ann = []
    if target:
        m, s = Image.new('L', size), Image.new('L', size)
        m.paste(music, (0, header_height))
        s.paste(all_ink, (0, header_height))
        md, sd = ink_distance(m), ink_distance(s)
        for t, mask in rows:
            a = annotation_metrics(mask, m, md, view)
            b = annotation_metrics(mask, s, sd, view)
            require(
                a['ink_contacts'] == a['notation_region_pixels'] == b['ink_contacts'] == 0,
                'Annotation/notation collision',
            )
            ann.append({'text': t, **a, 'all_score_ink': b})
    require(result.crop(view).tobytes() == image.tobytes(), 'Native canvas changed by diagnostics')
    return result, ann


def run(out):
    require(not out.exists(), 'New run directory required')
    histories = {
        str(p): file_hashes(p)
        for p in [PRIOR, GT12, Path('/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output')]
    }
    frozen = read(PRIOR / 'prediction-freeze.json')
    require(all(sha(PRIOR / p) == h for p, h in frozen['files'].items()), 'GT13A3 freeze changed')
    source_path = GT01 / 'predictions/baseline-exec/source/source.png'
    require(
        sha(source_path) == read(PRIOR / 'input-freeze.json')['source_sha256'], 'Source changed'
    )
    require(sha(FONT) == read(PRIOR / 'input-freeze.json')['font_sha256'], 'Pinned font changed')
    source = Image.open(source_path)
    size = (source.width, 750)
    inv = read(PRIOR / 'source-event-inventory.json')
    staff = inv['staff']
    graph = read(GT01 / 'predictions/baseline-exec/source/visual-graph.json')
    source_score = converter.parse(str(PRIOR / 'owner-augmented-source.musicxml'))
    first = list(source_score.parts[0].getElementsByClass(stream.Measure))[0]
    require(
        type(first.clef).__name__ == 'TrebleClef'
        and first.keySignature.sharps == -2
        and first.leftBarline.direction == 'start',
        'Source header identity differs',
    )
    events = read(GT02 / 'note-correspondence-diagnostic.json')['events']['Bb']
    out.mkdir()
    review = out / 'owner-review'
    review.mkdir()
    audit = proposed_lyrics(inv)
    for m in inv['measures']:
        n = m['printed_measure']
        if n == 3:
            continue
        left, right = m['physical_boundary_candidates']
        bounds = (int(left) - 10, 330, int(right) + 10, 720)
        source.crop(bounds).save(review / f'm{n}-source.png')
    source.crop((2300, 420, 2430, 710)).save(review / 'outgoing-tie-source.png')
    source.crop((140, 750, 750, 1060)).save(review / 'next-system-source.png')
    source.crop((150, 400, 430, 550)).save(review / 'source-header.png')
    dump(
        out / 'lyric-association-audit.json',
        {'status': 'OWNER_REVIEW_PENDING', 'independent_ground_truth': False, 'measures': audit},
    )
    tie = tie_evidence(graph, events, source_score)
    dump(out / 'outgoing-tie-evidence.json', tie)
    dump(
        review / 'packet.json',
        {
            'source_sha256': sha(source_path),
            'images': {n: sha(review / n) for n in file_hashes(review)},
            'coordinates': 'native source pixels; crop-local translations only',
            'crop_bounds': {
                'm1-source.png': [150, 330, 770, 720],
                'm2-source.png': [750, 330, 1384, 720],
                'm4-source.png': [1772, 330, 2410, 720],
                'outgoing-tie-source.png': [2300, 420, 2430, 710],
                'next-system-source.png': [140, 750, 750, 1060],
                'source-header.png': [150, 400, 430, 550],
            },
            'review_only': 'Confirm note-to-syllable relationships, not lyric strings again. Confirm/correct next-system destination independently of OMR candidates.',
        },
    )
    dump(
        out / 'input-freeze.json',
        {
            'base': read(PROTOCOL)['base'],
            'protocol_sha256': sha(PROTOCOL),
            'source_sha256': sha(source_path),
            'font_sha256': sha(FONT),
            'history_files': histories,
            'inventory_sha256': sha(PRIOR / 'source-event-inventory.json'),
            'source_graph_sha256': sha(GT01 / 'predictions/baseline-exec/source/visual-graph.json'),
            'GT02_event_sha256': sha(GT02 / 'note-correspondence-diagnostic.json'),
        },
    )
    # Time signature is source-visible/task-specified context absent in Audiveris XML, not recognition repair.
    augmented = copy.deepcopy(source_score)
    list(augmented.parts[0].getElementsByClass(stream.Measure))[0].insert(
        0, meter.TimeSignature('4/4')
    )
    augmented.write('musicxml', fp=str(out / 'source-with-header-context.musicxml'))
    guards = {
        'source_context_roundtrip': validate(
            augmented, converter.parse(str(out / 'source-with-header-context.musicxml')), 0, 'key'
        ).to_dict()
    }
    require(guards['source_context_roundtrip']['ok'], 'Source full guard failed')
    # Keep the actual registered barlines, removing only GT13A's diagnostic dummy left frame.
    boundaries = [m['physical_boundary_candidates'][1] for m in inv['measures']]
    external = {2400: graph['symbols']['sheet#1:4581']['geometry']['bbox']}
    base = scaffold(size, staff, boundaries, external)
    panels = [panel(source.crop(CROP), 'Unchanged original Bb source comparison')[0]]
    validations = []
    for target, shift in [('A', -1), ('G', -3)]:
        from backend.omr_v3.transpose import transpose_score

        transformed = copy.deepcopy(augmented)
        summary = transpose_score(transformed, shift, 'key')
        mem = validate(augmented, transformed, shift, 'key', summary).to_dict()
        transformed.write('musicxml', fp=str(out / f'{target}-transposed.musicxml'))
        parsed = converter.parse(str(out / f'{target}-transposed.musicxml'))
        disk = validate(augmented, parsed, shift, 'key', summary).to_dict()
        require(mem['ok'] and disk['ok'], 'Full V3 guard failed')
        prior_target = converter.parse(str(PRIOR / f'{target}-transposed.musicxml'))
        require(
            [event_signature(m) for m in parsed.parts[0].getElementsByClass(stream.Measure)]
            == [
                event_signature(m) for m in prior_target.parts[0].getElementsByClass(stream.Measure)
            ],
            '26-event semantics changed',
        )
        require(lyric_signature(parsed) == lyric_signature(augmented), 'Lyric stream changed')
        require(
            [c.figure for c in parsed.recurse().getElementsByClass(harmony.ChordSymbol)]
            == [c.figure for c in prior_target.recurse().getElementsByClass(harmony.ChordSymbol)],
            'Chord stream changed',
        )
        require(
            list(parsed.parts[0].getElementsByClass(stream.Measure))[0].keySignature.sharps
            == (3 if target == 'A' else 1),
            'Target key signature differs',
        )
        guards[target] = {'in_memory': mem, 'serialized': disk}
        existing = Image.open(PRIOR / f'{target}-confirmed-music-event-alpha.png').copy()
        music = existing.copy()
        parts = {'existing-musical-events': existing}
        # Exact prior glyphs, no staff subtraction or original-ink segmentation.
        for name in (f'{target}-new-chord-alpha.png',):
            parts[name] = Image.open(PRIOR / name).copy()
        for p in (GT12 / 'confirmed-context').glob(target + '-*-alpha.png'):
            if '-chord-' in p.name or '-lyric-' in p.name:
                parts[p.name] = Image.open(p).crop((0, 0, *size))
        m1lyrics = Image.new('L', size)
        for p in Path('/private/tmp/capomatic-v4-gt13a2/gt13a2-final-output').glob(
            target + '-lyric_*.png'
        ):
            m1lyrics = Image.fromarray(np.maximum(np.asarray(m1lyrics), np.asarray(Image.open(p))))
        parts['m1-lyrics'] = m1lyrics
        nonstaff = Image.fromarray(np.maximum.reduce([np.asarray(m) for m in parts.values()]))
        hp, hm = header(size, staff, target, FONT)
        contacts = []
        for name, mask in hp.items():
            count = int(np.count_nonzero((np.asarray(mask) > 0) & (np.asarray(nonstaff) > 0)))
            if count:
                contacts.append({'header': name, 'existing_ink_pixels': count})
            b = mask.getbbox()
            require(
                CROP[0] <= b[0] < b[2] <= CROP[2] and CROP[1] <= b[1] < b[3] <= CROP[3],
                'Header viewport clipping',
            )
            mask.save(out / f'{target}-header-{name}.png')
        require(not contacts, 'Header collides with prior note/chord/lyrics')
        h_union = Image.fromarray(np.maximum.reduce([np.asarray(m) for m in hp.values()]))
        alpha = Image.fromarray(
            np.maximum.reduce([np.asarray(nonstaff), np.asarray(base), np.asarray(h_union)])
        )
        musical = Image.fromarray(np.maximum(np.asarray(music), np.asarray(h_union)))
        canvas = Image.composite(
            Image.new('RGB', size, 'black'), Image.new('RGB', size, 'white'), alpha
        )
        canvas = Image.composite(Image.new('RGB', size, (155, 85, 0)), canvas, m1lyrics)
        native = canvas.crop(CROP)
        old = Image.open(PRIOR / f'{target}-native-notation-viewport.png')
        # All source events start after x400; preserve complete right-hand content byte-for-byte.
        preserved = (400 - CROP[0], 0, CROP[2] - CROP[0], CROP[3] - CROP[1])
        require(
            native.crop(preserved).tobytes() == old.crop(preserved).tobytes(),
            'Existing event/chord/lyric geometry changed',
        )
        target_panel, annotations = panel(
            native,
            f'{target} major: actual header engraved; lyric associations and outgoing tie incomplete',
            target=target,
            music=musical.crop(CROP),
            all_ink=alpha.crop(CROP),
        )
        target_panel.save(out / f'predicted-{target.lower()}.png')
        panels.append(target_panel)
        native.save(out / f'{target}-native-notation-viewport.png')
        h_union.save(out / f'{target}-header-alpha.png')
        distance = ink_distance(nonstaff)
        minimum = float(distance[np.asarray(h_union) > 0].min())
        hm.update(
            target=target,
            header_prior_ink_contacts=contacts,
            header_prior_ink_clearance_px=minimum,
            annotation_metrics=annotations,
            unchanged_note_chord_lyric_region_source_x_ge_400=True,
            time_semantics=str(
                list(parsed.parts[0].getElementsByClass(stream.Measure))[0].timeSignature
            ),
            geometry_status='EXPERIMENTAL_SYNTHETIC_AND_AGENT_VISUAL_VALIDATION',
            source_header_evidence={
                'clef': 'MusicXML TrebleClef + Inter204',
                'key': 'MusicXML -2 fifths + Inter211',
                'time': 'Source visible 4/4 and explicit task scope; absent in raw OMR MusicXML',
                'repeat': 'MusicXML start + Inter2/4/5577/5579 relations',
            },
            dummy_left_frame_omitted=True,
        )
        validations.append(hm)
    source.crop(CROP).save(out / 'original-bb.png')
    sheet = Image.new('RGB', (panels[0].width, sum(p.height for p in panels)), 'white')
    for i, p in enumerate(panels):
        sheet.paste(p, (0, i * p.height))
    sheet.save(out / 'comparison-contact-sheet.png')
    dump(out / 'header-notation-validation.json', validations)
    dump(out / 'semantic-integrity.json', guards)
    dump(
        out / 'remaining-blockers.json',
        {
            'status': 'FULL_SYSTEM_INCOMPLETE',
            'source_verification': '26 listed events and two chords OWNER_VERIFIED_SOURCE; associations and tie destination pending',
            'rendering_completeness': 'Header engraved, outgoing tie and aligned m2/4 lyrics incomplete',
            'visual_quality': 'PENDING_POST_FREEZE_AGENT_REVIEW; independent optical validation unavailable',
            'blockers': [
                'Exact m1/2/4 syllable associations/extenders',
                'Owner confirmation of next-system tie destination',
                'Validated complete cross-system tie renderer',
                'Independent optical and musician review',
            ],
        },
    )
    require(
        all(file_hashes(Path(p)) == h for p, h in histories.items()), 'Historical evidence changed'
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'base': read(PROTOCOL)['base'],
            'producer_sha256': sha(Path(__file__)),
            'header_code_sha256': sha(ROOT / 'scripts/research/gt13a4_header.py'),
            'files': file_hashes(out),
            'phase': 'BEFORE_TARGET_REFERENCE_OR_AGENT_VISUAL_REVIEW',
        },
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
