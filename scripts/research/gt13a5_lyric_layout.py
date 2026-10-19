"""GT13A5: integer translation of frozen lyric masks; never edits source score ink."""

import argparse
from pathlib import Path

import cv2
import numpy as np
from music21 import converter
from PIL import Image, ImageDraw, ImageFont

from backend.omr_v3.music_guard import validate
from scripts.research.gt11_complete_measure import read, require
from scripts.research.gt13a_full_system import CROP, GT12, scaffold
from scripts.research.gt13a2_provisional import ink_distance
from scripts.research.gt13a4_confirmed_lyrics import full_lyric_signature
from scripts.research.paired_ground_truth_01 import dump, file_hashes, sha

ROOT = Path(__file__).resolve().parents[2]
OLD = Path('/private/tmp/capomatic-v4-gt13a4/gt13a4-final-output')
HEADER = OLD.parent / 'gt13a4-output'
PRIOR = Path('/private/tmp/capomatic-v4-gt13a3/gt13a3-output')
SOURCE = Path(
    '/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output/predictions/baseline-exec/source/source.png'
)
PROTOCOL = ROOT / 'docs/V4_GT13A5_PROTOCOL.json'


def union(parts):
    return Image.fromarray(np.maximum.reduce([np.asarray(p) for p in parts]))


def translate(mask, dy, viewport):
    """Lossless integer translation, rejecting clipping rather than cropping glyphs."""
    require(type(dy) is int and dy >= 0, 'Nonnegative integer displacement required')
    b = mask.getbbox()
    require(b is not None, 'Empty lyric mask')
    require(
        b[0] >= viewport[0]
        and b[2] <= viewport[2]
        and b[1] >= viewport[1]
        and b[3] + dy <= viewport[3],
        'Lyric clipping',
    )
    result = Image.new('L', mask.size)
    result.paste(mask.crop(b), (b[0], b[1] + dy))
    require(result.crop(result.getbbox()).tobytes() == mask.crop(b).tobytes(), 'Lost alpha')
    return result


def spacing_obstacle(fixed):
    return cv2.dilate((np.asarray(fixed) > 0).astype('uint8'), np.ones((3, 3), 'uint8')) > 0


def displacement_domain(group, fixed, neighbors, viewport):
    """Full finite correlation domain, not a post-result threshold/shift adjustment."""
    b = group.getbbox()
    require(b is not None and b[3] <= viewport[3], 'Invalid group geometry')
    obstacle = spacing_obstacle(fixed) | (np.asarray(neighbors) > 0)
    support = np.asarray(group) > 0
    maximum = viewport[3] - b[3]
    forbidden = []
    for dy in range(maximum + 1):
        if np.any(support[b[1] : b[3], b[0] : b[2]] & obstacle[b[1] + dy : b[3] + dy, b[0] : b[2]]):
            forbidden.append(dy)
    feasible = sorted(set(range(maximum + 1)) - set(forbidden))
    return {
        'maximum_dy': maximum,
        'forbidden_dy': forbidden,
        'feasible_dy': feasible,
        'selected_dy': feasible[0] if feasible else None,
    }


def contacts(parts):
    hits = []
    names = list(parts)
    for i, name in enumerate(names):
        a = parts[name]
        ba = a.getbbox()
        for other in names[i + 1 :]:
            b = parts[other]
            bb = b.getbbox()
            box = (max(ba[0], bb[0]), max(ba[1], bb[1]), min(ba[2], bb[2]), min(ba[3], bb[3]))
            if box[0] < box[2] and box[1] < box[3]:
                n = int(
                    np.count_nonzero((np.asarray(a.crop(box)) > 0) & (np.asarray(b.crop(box)) > 0))
                )
                if n:
                    hits.append({'a': name, 'b': other, 'pixels': n})
    return hits


def layout(parts, measures, fixed, strategy, viewport=CROP):
    shifts = {}
    domains = {}
    empty = Image.new('L', fixed.size)
    if strategy == 'global':
        domain = displacement_domain(union(list(parts.values())), fixed, empty, viewport)
        require(domain['selected_dy'] is not None, 'No feasible global layout')
        shifts = {m: domain['selected_dy'] for m in set(measures.values())}
        domains['system'] = domain
    else:
        require(strategy == 'local', 'Unknown strategy')
        for m in sorted(set(measures.values())):
            group = union([p for n, p in parts.items() if measures[n] == m])
            neighbors = [p for n, p in parts.items() if measures[n] != m]
            domain = displacement_domain(
                group, fixed, union(neighbors) if neighbors else empty, viewport
            )
            require(domain['selected_dy'] is not None, 'No feasible local layout')
            require(m != 3 or domain['selected_dy'] == 0, 'Local measure 3 cannot move')
            domains[str(m)] = domain
            shifts[m] = domain['selected_dy']
    moved = {n: translate(p, shifts[measures[n]], viewport) for n, p in parts.items()}
    require(not contacts(moved), 'Final lyric/lyric collision')
    merged = union(list(moved.values()))
    require(not np.any((np.asarray(merged) > 0) & spacing_obstacle(fixed)), 'Spacing failure')
    d = ink_distance(fixed)
    minimum = float(d[np.asarray(merged) > 0].min())
    require(minimum >= 2, 'Positive clearance failure')
    return moved, {
        'dy_by_measure': shifts,
        'domains': domains,
        'minimum_ink_center_distance_px': minimum,
        'minimum_unit_square_edge_lower_bound_px': max(0, minimum - 2**0.5),
        'lyric_music_contacts': 0,
        'lyric_lyric_contacts': [],
        'clipping': [],
        'lost_alpha_pixels': 0,
        'horizontal_anchor_changes': 0,
        'row_spacing_changes': 0,
        'association_changes': 0,
        'm3_changed_on_new_canvas': shifts[3] != 0,
    }


def load_parts(target):
    parts = {}
    measures = {}
    for p in sorted(OLD.glob(f'{target}-lyric-m[124]-*.png')):
        name = p.stem[len(target) + 7 :]
        parts[name] = Image.open(p).copy()
        measures[name] = int(name[1])
    for p in sorted((GT12 / 'confirmed-context').glob(f'{target}-lyric-*-alpha.png')):
        name = 'm3-' + p.stem
        parts[name] = Image.open(p).crop((0, 0, 2520, 750))
        measures[name] = 3
    require(len(parts) == 40, 'Expected 36 syllables + 4 continuation markers')
    return parts, measures


def fixed_ink(target):
    inv = read(PRIOR / 'source-event-inventory.json')
    base = scaffold(
        (2520, 750),
        inv['staff'],
        [m['physical_boundary_candidates'][1] for m in inv['measures']],
        {2400: [2398, 443, 2402, 518]},
    )
    paths = [
        OLD / f'{target}-owner-confirmed-event-alpha.png',
        HEADER / f'{target}-header-alpha.png',
        PRIOR / f'{target}-new-chord-alpha.png',
        GT12 / 'confirmed-context' / f'{target}-chord-alpha.png',
    ]
    return union([base] + [Image.open(p).crop((0, 0, 2520, 750)) for p in paths])


def panel(native, title):
    result = Image.new('RGB', (native.width, native.height + 150), 'white')
    d = ImageDraw.Draw(result)
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 22)
    for i, line in enumerate(
        [
            'DEVELOPER-ONLY EXPERIMENTAL PROTOTYPE',
            'FULL_SYSTEM_INCOMPLETE - NOT FOR PERFORMANCE OR PRINTING',
            title,
            'Outgoing tie unresolved; newly typeset lyrics, not original lyric pixels',
        ]
    ):
        d.text((10, 8 + i * 29), line, font=f, fill='black')
    result.paste(native, (0, 150))
    return result


def render(fixed, parts, title):
    alpha = union([fixed, *parts.values()])
    native = Image.composite(
        Image.new('RGB', alpha.size, 'black'), Image.new('RGB', alpha.size, 'white'), alpha
    ).crop(CROP)
    return panel(native, title), alpha


def verify_freeze(path):
    record = read(path / 'prediction-freeze.json')
    require(
        all(sha(path / n) == h for n, h in record['files'].items()), 'Historical freeze mismatch'
    )


def run(out):
    require(not out.exists(), 'New output identity required')
    for p in (OLD, HEADER):
        verify_freeze(p)
    histories = {
        str(p): file_hashes(p)
        for p in (OLD, HEADER, PRIOR, GT12, Path('/private/tmp/capomatic-v4-gt13a/gt13a-output'))
    }
    source_hash = sha(SOURCE)
    require(source_hash == read(OLD / 'input-freeze.json')['source_sha256'], 'Source changed')
    baseline = {}
    loaded = {}
    for target in ('A', 'G'):
        parts, measures = load_parts(target)
        fixed = fixed_ink(target)
        require(
            union([fixed, *parts.values()]).tobytes()
            == Image.open(OLD / f'{target}-notation-alpha.png').tobytes(),
            'Baseline alpha reconstruction mismatch',
        )
        music = np.asarray(Image.open(OLD / f'{target}-owner-confirmed-event-alpha.png')) > 0
        detail = {n: int(np.count_nonzero((np.asarray(p) > 0) & music)) for n, p in parts.items()}
        hit = (np.asarray(union(list(parts.values()))) > 0) & music
        baseline[target] = {
            'unique_pixels': int(hit.sum()),
            'components': {n: v for n, v in detail.items() if v},
        }
        require(
            baseline[target]['unique_pixels'] == {'A': 0, 'G': 105}[target],
            'Baseline collision mismatch',
        )
        if target == 'G':
            require(sorted(v for v in detail.values() if v) == [45, 60], 'Expected 60/45 split')
        loaded[target] = (parts, measures, fixed)
    out.mkdir()
    dump(out / 'baseline-reproduction.json', baseline)
    dump(
        out / 'input-freeze.json',
        {
            'history_files': histories,
            'source_sha256': source_hash,
            'protocol_sha256': sha(PROTOCOL),
            'producer_sha256': sha(Path(__file__)),
        },
    )
    source = converter.parse(str(OLD / 'owner-associated-source.musicxml'))
    guards = {'source_identity': validate(source, source, 0, 'key').to_dict()}
    for target, shift in [('A', -1), ('G', -3)]:
        score = converter.parse(str(OLD / f'{target}-transposed.musicxml'))
        guards[target] = validate(source, score, shift, 'key').to_dict()
        require(
            full_lyric_signature(source) == full_lyric_signature(score), 'Lyric semantics changed'
        )
    require(all(r['ok'] for r in guards.values()), 'Unchanged V3 guard failed')
    dump(out / 'semantic-integrity.json', guards)
    original = panel(Image.open(SOURCE).crop(CROP), 'Unchanged original Bb source')
    original.save(out / 'original-bb.png')
    metrics = {}
    differences = {}
    panels = [original]
    for target, (parts, measures, fixed) in loaded.items():
        baseline_panel, _ = render(
            fixed, parts, f'{target} frozen baseline; contacts {baseline[target]["unique_pixels"]}'
        )
        if target == 'G':
            baseline_panel.save(out / 'baseline-g-collision.png')
        for strategy in ('local', 'global'):
            moved, report = layout(parts, measures, fixed, strategy)
            image, alpha = render(
                fixed, moved, f'{target} major / {strategy} lyric layout; zero contacts'
            )
            key = target + '-' + strategy
            metrics[key] = report
            alpha.save(out / f'{key}-notation-alpha.png')
            union(list(moved.values())).save(out / f'{key}-lyric-alpha.png')
            if target == 'G':
                image.save(out / f'candidate-{strategy}-g.png')
            if strategy == 'local':
                image.save(out / f'predicted-{target.lower()}.png')
                panels.append(image)
                require(
                    all(
                        moved[n].tobytes() == parts[n].tobytes() for n in parts if measures[n] == 3
                    ),
                    'M3 local changed',
                )
            differences[key] = [
                {
                    'component': n,
                    'measure': measures[n],
                    'dx': 0,
                    'dy': report['dy_by_measure'][measures[n]],
                    'alpha_tile_identical': moved[n].crop(moved[n].getbbox()).tobytes()
                    == parts[n].crop(parts[n].getbbox()).tobytes(),
                    'old_bbox': parts[n].getbbox(),
                    'new_bbox': moved[n].getbbox(),
                }
                for n in parts
            ]
    sheet = Image.new('RGB', (panels[0].width, sum(p.height for p in panels)), 'white')
    y = 0
    for p in panels:
        sheet.paste(p, (0, y))
        y += p.height
    sheet.save(out / 'comparison-contact-sheet.png')
    dump(out / 'lyric-layout-metrics.json', metrics)
    dump(out / 'layout-differences.json', differences)
    dump(out / 'collision-before-after.json', {'before': baseline, 'after': metrics})
    require(
        sha(SOURCE) == source_hash and all(file_hashes(Path(p)) == h for p, h in histories.items()),
        'Historical/source change',
    )
    dump(
        out / 'validation-summary.json',
        {
            'status': 'FULL_SYSTEM_INCOMPLETE',
            'events': 26,
            'owner_verified_events': 26,
            'syllables': 36,
            'continuation_marks': 4,
            'chords': 2,
            'music_header_chord_geometry': 'UNCHANGED_FROZEN_BITMAPS',
            'm3_local': 'BITWISE_UNCHANGED',
            'historical_artifacts': 'UNCHANGED',
            'source_sha256': source_hash,
            'independent_optical_validation': False,
            'outgoing_tie': 'UNRESOLVED_NOT_RENDERED',
            'final_strategy': 'local',
            'source_recognition': 'OWNER_VERIFIED scoped first-system events; not independent ground truth',
            'notehead_anchor': 'Unchanged frozen music masks; existing <=0.5px criterion retained',
        },
    )
    dump(
        out / 'prediction-freeze.json',
        {
            'files': file_hashes(out),
            'phase': 'BEFORE_AGENT_VISUAL_INSPECTION',
            'producer_sha256': sha(Path(__file__)),
        },
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
