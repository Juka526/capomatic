"""Lossless integration and diagnostic validation of frozen standalone score layers."""

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from music21 import converter, stream, harmony
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from backend.omr_v3.transpose import transpose_score
from scripts.research.gt11_complete_measure import read, require, events_of, event_signature
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.gt13a5_lyric_layout import (
    load_parts,
    translate,
    contacts,
    union,
    verify_freeze,
)
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a6_tie_review import endpoint_pair
from scripts.research.gt14a_confirmed_context import GT13A6
from scripts.research.gt14d_confirmed_extenders import (
    GT14A,
    GT14B,
    GT14C,
    SOURCE,
    SOURCE_DIR,
    SIZE,
    native,
)
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha, line_y

ROOT = Path(__file__).resolve().parents[2]
GT14D = Path('/private/tmp/capomatic-v4-gt14d/gt14d-output')
GT13A5 = Path('/private/tmp/capomatic-v4-gt13a5/gt13a5-output')
GT13A4 = Path('/private/tmp/capomatic-v4-gt13a4/gt13a4-final-output')
GT13A3 = Path('/private/tmp/capomatic-v4-gt13a3/gt13a3-output')
GT12 = Path('/private/tmp/capomatic-v4-gt12/gt12-output/confirmed-context')
HEADER = GT13A4.parent / 'gt13a4-output'
PROTOCOL = ROOT / 'docs/V4_GT14E_PROTOCOL.json'
VIEW = (130, 310, 2430, 1030)


def expanded(mask, size=SIZE):
    require(
        mask.mode == 'L' and mask.width == size[0],
        'Mask coordinate mismatch',
    )
    bbox = mask.getbbox()
    require(bbox is not None and bbox[3] <= size[1], 'Nonempty ink would be clipped')
    result = Image.new('L', size)
    result.paste(mask.crop((0, 0, mask.width, min(mask.height, size[1]))), (0, 0))
    return result


def integrate(first, second, split):
    require(first.size == second.size and first.mode == second.mode == 'L', 'Coordinate mismatch')
    require(type(split) is int and 0 < split < first.height, 'Invalid split')
    require(not np.asarray(first)[split:].any(), 'First-system layer crosses split')
    a = Image.new('L', first.size)
    a.paste(first.crop((0, 0, first.width, split)), (0, 0))
    b = Image.new('L', second.size)
    b.paste(second.crop((0, split, second.width, second.height)), (0, split))
    result = union([a, b])
    require(result.tobytes() == second.tobytes(), 'Integration differs from frozen combined alpha')
    return result, a, b


def text_check(parts, notation, viewport):
    text = union(list(parts.values()))
    hits = int(np.count_nonzero((np.asarray(text) > 0) & (np.asarray(notation) > 0)))
    pairs = contacts(parts)
    clipping = [
        n
        for n, p in parts.items()
        if p.getbbox()[0] < viewport[0]
        or p.getbbox()[1] < viewport[1]
        or p.getbbox()[2] > viewport[2]
        or p.getbbox()[3] > viewport[3]
    ]
    d = ink_distance(notation)
    return {
        'text_notation_unique_contact_pixels': hits,
        'text_text_contacts': pairs,
        'clipped_text_components': clipping,
        'minimum_text_notation_ink_center_distance_px': float(d[np.asarray(text) > 0].min()),
    }


def serialization_audit(path):
    root = ET.parse(path).getroot()
    measures = list(root.find('part').findall('measure'))[:8]
    return {
        'file': str(path),
        'sha256': sha(path),
        'measures_scoped': len(measures),
        'lyric_elements': sum(len(m.findall('.//lyric')) for m in measures),
        'extend_elements': sum(len(m.findall('.//lyric/extend')) for m in measures),
        'tie_elements': sum(len(m.findall('.//note/tie')) for m in measures),
        'gap': 'Visual held-syllable continuation marks are diagnostic masks/JSON, not explicitly serialized lyric extend instructions',
        'production_export_modified': False,
    }


def panel(image, title):
    result = Image.new('RGB', (image.width, image.height + 140), 'white')
    draw = ImageDraw.Draw(result)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    for i, line in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE / INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            'OWNER_VERIFIED scoped source / NOT_INDEPENDENT_GROUND_TRUTH',
            'Standalone newly typeset notation and lyrics; no original ink removal or pixel composition',
        ]
    ):
        draw.text((10, 8 + i * 30), line, font=font, fill='black')
    result.paste(image, (0, 140))
    return result


def load_components(target, first_layout):
    parts, measures = load_parts(target)
    lyrics = {
        f'first-{n}': expanded(
            translate(p, first_layout['dy_by_measure'][str(measures[n])], (130, 310, 2430, 720))
        )
        for n, p in parts.items()
    }
    expected = expanded(Image.open(GT13A5 / f'{target}-local-lyric-alpha.png'))
    require(
        union(list(lyrics.values())).tobytes() == expected.tobytes(),
        'First lyric layout differs from frozen masks',
    )
    for p in GT14A.glob(f'{target}-lyric-*-alpha.png'):
        lyrics[f'second-{p.name}'] = Image.open(p).copy()
    for directory in (GT14B, GT14D):
        for p in directory.glob(f'{target}-*alpha.png'):
            if 'extender-' in p.name or '-GT14C-' in p.name:
                lyrics[f'second-{p.name}'] = Image.open(p).copy()
    require(len(lyrics) == 60, 'Expected 50 syllables and 10 continuation markers')
    paths = [
        GT13A4 / f'{target}-owner-confirmed-event-alpha.png',
        HEADER / f'{target}-header-alpha.png',
        GT13A3 / f'{target}-new-chord-alpha.png',
        GT12 / f'{target}-chord-alpha.png',
        GT13A6 / f'{target}-whole-note-alpha.png',
        GT13A6 / f'{target}-whole-ledger-alpha.png',
        GT13A6 / f'{target}-outgoing-tie-alpha.png',
        GT13A6 / f'{target}-incoming-tie-alpha.png',
        GT14A / f'{target}-reused-music-alpha.png',
        GT14A / f'{target}-whole-rest-alpha.png',
    ]
    paths += list(GT14A.glob(f'{target}-chord-*-alpha.png'))
    paths += [
        p
        for p in GT14A.glob(f'{target}-*alpha.png')
        if any(n in p.name for n in ['ending1-', 'backward-'])
    ]
    notation = {p.name: expanded(Image.open(p)) for p in paths}
    return lyrics, notation


def run(out):
    require(not out.exists(), 'Fresh output required')
    protocol = read(PROTOCOL)
    for p in (GT14A, GT14B, GT14D, GT13A6, GT13A5, GT13A4, HEADER, GT13A3):
        verify_freeze(p)
    histories = {
        str(p): file_hashes(p)
        for p in (GT14A, GT14B, GT14C, GT14D, GT13A6, GT13A5, GT13A4, HEADER, GT13A3, GT12)
    }
    graph = read(SOURCE_DIR / 'visual-graph.json')
    require(sha(SOURCE) == read(GT14D / 'input-freeze.json')['source_sha256'], 'Source mismatch')
    source = converter.parse(str(GT14A / 'owner-augmented-source.musicxml'))
    measures = list(source.parts[0].getElementsByClass(stream.Measure))[:8]
    counts = [len(events_of(m)) for m in measures]
    require(counts == [4, 9, 4, 9, 1, 10, 1, 1], 'Confirmed event inventory mismatch')
    require(
        sum(len(n.lyrics) for m in measures for n in events_of(m)) == 50, '50 syllables required'
    )
    require(
        sum(len(list(m.getElementsByClass(harmony.ChordSymbol))) for m in measures) == 5,
        '5 chords required',
    )
    endpoint_pair(source, 'B-3')
    out.mkdir()
    dump(
        out / 'input-freeze.json',
        {
            'history_files': histories,
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
            'source_sha256': sha(SOURCE),
        },
    )
    staff = graph['staves'][:2]
    reg = [
        {
            'measure': int(m['number']),
            'source_bounds': m['bounds'],
            'source_width': m['bounds'][2] - m['bounds'][0],
            'integration_translation': [0, 0],
        }
        for m in graph['measures'][:8]
    ]
    results, panels, guards = [], [], {}
    guards['source_roundtrip'] = validate(
        source, converter.parse(str(GT14A / 'owner-augmented-source.musicxml')), 0, 'key'
    ).to_dict()
    for target, shift, ep in [('A', -1, 'A3'), ('G', -3, 'G3')]:
        inherited = Image.open(GT13A6 / f'{target}-two-system-alpha.png')
        first = Image.new('L', SIZE)
        first.paste(inherited.crop((0, 0, SIZE[0], protocol['split_page_y'])), (0, 0))
        old_first = expanded(Image.open(GT13A5 / f'{target}-local-notation-alpha.png'))
        outgoing = Image.open(GT13A6 / f'{target}-outgoing-tie-alpha.png')
        require(
            first.tobytes() == union([old_first, outgoing]).tobytes(),
            'Frozen first-system geometry mismatch',
        )
        cached = Image.open(GT14D / f'{target}-combined-alpha.png')
        alpha, a, b = integrate(first, cached, protocol['split_page_y'])
        lyrics, notation = load_components(
            target, read(GT13A5 / 'lyric-layout-metrics.json')[f'{target}-local']
        )
        # Conservative staff bands use actual cached alpha, without excluding text pixels.
        bands = Image.new('L', SIZE)
        for st in staff:
            lo = int(min(p[1] for p in st['lines'][0])) - 2
            hi = int(max(p[1] for p in st['lines'][-1])) + 3
            bands.paste(alpha.crop((0, lo, SIZE[0], hi)), (0, lo))
        notation['actual-alpha-staff-bands'] = bands
        fixed = union(list(notation.values()))
        require(
            all(
                np.all(np.asarray(p) <= np.asarray(alpha))
                for p in [*lyrics.values(), *notation.values()]
            ),
            'Component pixels missing in combined canvas',
        )
        collision = text_check(lyrics, fixed, VIEW)
        chord_positions = [
            {'component': n, 'bounds': list(p.getbbox()), 'integration_translation': [0, 0]}
            for n, p in notation.items()
            if 'chord' in n
        ]
        require(
            not collision['text_notation_unique_contact_pixels']
            and not collision['text_text_contacts']
            and not collision['clipped_text_components'],
            'Integrated lyric collision/clipping',
        )
        require(
            collision['minimum_text_notation_ink_center_distance_px'] > 0, 'No positive clearance'
        )
        ab = a.getbbox()
        bb = b.getbbox()
        require(
            ab[3] < bb[1] and not np.any((np.asarray(a) > 0) & (np.asarray(b) > 0)),
            'Cross-system overlap',
        )
        require(
            alpha.crop(VIEW).getbbox() is not None
            and not np.asarray(alpha)[: VIEW[1]].any()
            and not np.asarray(alpha)[VIEW[3] :].any()
            and not np.asarray(alpha)[:, : VIEW[0]].any()
            and not np.asarray(alpha)[:, VIEW[2] :].any(),
            'Preview clipping',
        )
        ties = {
            role: Image.open(GT13A6 / f'{target}-{role}-tie-alpha.png')
            for role in ['outgoing', 'incoming']
        }
        tie_lyric = {
            role: int(
                np.count_nonzero(
                    (np.asarray(p) > 0) & (np.asarray(union(list(lyrics.values()))) > 0)
                )
            )
            for role, p in ties.items()
        }
        require(not any(tie_lyric.values()), 'Cross-system tie/lyric contact')
        score = copy.deepcopy(source)
        summary = transpose_score(score, shift, 'key')
        disk = converter.parse(str(GT14A / f'{target}-transposed.musicxml'))
        guards[target] = {
            'in_memory': validate(source, score, shift, 'key', summary).to_dict(),
            'frozen_serialized': validate(source, disk, shift, 'key', summary).to_dict(),
        }
        require(all(r['ok'] for r in guards[target].values()), 'Full V3 guard failure')
        require(
            full_lyric_signature(source) == full_lyric_signature(disk), 'Lyric semantic mismatch'
        )
        require(
            [event_signature(m) for m in score.parts[0].getElementsByClass(stream.Measure)]
            == [event_signature(m) for m in disk.parts[0].getElementsByClass(stream.Measure)],
            'Event/tie mismatch',
        )
        endpoints = endpoint_pair(disk, ep)
        image = panel(
            native(alpha).crop(VIEW),
            f'{target} major / printed measures 1-8 / 39 inherited events, 5 chords, 50 syllables, 10 continuation marks',
        )
        image.save(out / f'{target}-two-systems.png')
        panels.append(image)
        alpha.save(out / f'{target}-integrated-alpha.png')
        for label, box in {
            'm2-ledger-tie-lyrics': (920, 490, 1370, 700),
            'm4-outgoing': (1950, 490, 2430, 700),
            'm5-incoming': (250, 860, 390, 1030),
            'm6-m7-ledger-tie-lyrics': (890, 840, 1690, 1030),
        }.items():
            if target == 'G':
                native(alpha).crop(box).save(out / f'G-detail-{label}.png')
        firstlayout = read(GT13A5 / 'lyric-layout-metrics.json')[f'{target}-local']
        secondlayout = next(
            r for r in read(GT14A / 'rendering-validation.json') if r['target'] == target
        )
        sample_x = [200, 1200, 2300]
        spacing = [
            line_y(staff[1]['lines'][2], x) - line_y(staff[0]['lines'][2], x) for x in sample_x
        ]
        results.append(
            {
                'target': target,
                **collision,
                'events_by_measure': counts,
                'events_inherited_displayed': 39,
                'confirmed_chords': 5,
                'confirmed_syllables': 50,
                'continuation_mark_components': 10,
                'second_system_confirmed_extenders': 6,
                'component_masks_retained': len(lyrics) + len(notation),
                'first_system_unchanged': True,
                'second_system_unchanged': True,
                'integrated_alpha_equals_GT14D': True,
                'measure_registration': reg,
                'chord_positions': chord_positions,
                'staff_polylines': staff,
                'geometry_integration_deviation_px': 0,
                'middle_staff_spacing_px': dict(zip(map(str, sample_x), spacing)),
                'system_ink_edge_vertical_gap_px': bb[1] - ab[3],
                'cross_system_component_contact_pixels': 0,
                'first_lyric_displacements_by_measure': firstlayout['dy_by_measure'],
                'second_lyric_baselines': secondlayout['lyric_baselines'],
                'second_lyric_displacement': secondlayout['lyric_displacement_dy'],
                'tie_endpoints': endpoints,
                'tie_lyric_contacts': tie_lyric,
                'cross_system_tie_masks_unchanged': True,
                'bridge_ink_pixels': int(np.count_nonzero(np.asarray(alpha)[700:720])),
                'intentional_notation_contacts': 'Staff/head/ledger and connected stem/beam contacts are retained. No global pairwise notation reclassification is claimed.',
                'all_notation_pair_collision_audit': 'INHERITED_COMPONENT_CHECKS_NOT_RECOMPUTED_GLOBALLY',
                'clipping': [],
                'inherited_notehead_max_anchor_residual_px': 0.5,
                'SOURCE_VERIFICATION': 'OWNER_VERIFIED_SCOPED_CONTENT_NOT_INDEPENDENT_COMPLETENESS',
                'SEMANTIC_CORRECTNESS': 'UNCHANGED_V3_GUARDS_AND_SIGNATURES_PASS_NOT_RECOGNITION_GROUND_TRUTH',
                'RENDERING_COMPLETENESS': 'FROZEN_TWO_SYSTEM_CONTENT_RETAINED_NOT_FULL_SCORE',
                'VISUAL_READABILITY': 'PENDING_POST_FREEZE_AGENT_INSPECTION',
            }
        )
    require(guards['source_roundtrip']['ok'], 'Source roundtrip failed')
    original = panel(
        Image.open(SOURCE).crop(VIEW),
        'Unchanged original Bb source evidence only; no A/G reference page used',
    )
    sheet = Image.new('RGB', (original.width, original.height * 3), 'white')
    for i, p in enumerate([original, *panels]):
        sheet.paste(p, (0, i * original.height))
    sheet.save(out / 'Bb-A-G-two-system-comparison.png')
    dump(out / 'two-system-visual-validation.json', results)
    dump(out / 'semantic-integrity.json', guards)
    dump(
        out / 'lyric-extender-serialization-audit.json',
        {
            'visual_mark_count': 10,
            'files': [
                serialization_audit(GT14A / name)
                for name in [
                    'owner-augmented-source.musicxml',
                    'A-transposed.musicxml',
                    'G-transposed.musicxml',
                ]
            ],
            'production_modified': False,
        },
    )
    require(
        all(file_hashes(Path(p)) == h for p, h in histories.items()), 'Historical file mutation'
    )
    require(
        sha(SOURCE) == read(GT14D / 'input-freeze.json')['source_sha256'], 'Original source changed'
    )
    dump(
        out / 'prediction-freeze.json',
        {'files': file_hashes(out), 'phase': 'BEFORE_AGENT_VISUAL_INSPECTION_NO_REFERENCE_ACCESS'},
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
