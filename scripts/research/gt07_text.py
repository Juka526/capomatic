"""Frozen OMR text lineage and diagnostic support categories; no edit authorization."""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

from backend.omr_v4.visual_graph import safe_xml
from backend.omr_v4.ink import glyphs_from_omr, rle
from scripts.research.gt05_raster_anchor import glyph
from scripts.research.gt04_visual import HEAD
from scripts.research.paired_ground_truth_01 import dump, sha, file_hashes, line_y
from scripts.research.ground_truth_02 import verify_inputs

DESIGN = Path(__file__).resolve().parents[2] / 'docs/V4_GT07_TEXT_AUDIT_PROTOCOL.json'
MUSICAL = {
    'head',
    'stem',
    'beam',
    'beam-hook',
    'flag',
    'augmentation-dot',
    'ledger',
    'alter',
    'accidental',
    'slur',
    'clef',
    'key-alter',
    'key',
    'time-number',
    'time-whole',
    'rest',
    'barline',
    'staff-barline',
    'articulation',
    'fermata',
}


def descendants(graph, root):
    found = set()
    pending = [root]
    while pending:
        ident = pending.pop()
        if ident in found:
            continue
        if ident not in graph['symbols']:
            raise ValueError('Missing text lineage object')
        found.add(ident)
        pending.extend(
            r['target']
            for r in graph['relations']
            if r['kind'] == 'contains' and r['source'] == ident
        )
    return sorted(found)


def classify(text, music):
    """Disjoint diagnostic categories, never pixels eligible for editing."""
    if text.shape != music.shape:
        raise ValueError('Coordinate mismatch')
    return np.where(text & music, 3, np.where(text, 1, np.where(music, 2, 0))).astype('uint8')


def mask_of(size, pixels):
    a = np.zeros((size[1], size[0]), bool)
    for x, y in pixels:
        if not 0 <= x < size[0] or not 0 <= y < size[1]:
            raise ValueError('Glyph escapes exact page coordinates')
        a[y, x] = True
    return a


def verify_freeze(root):
    f = json.loads((root / 'prototype-freeze.json').read_text())
    a = file_hashes(root)
    a.pop('prototype-freeze.json')
    if a != f['files']:
        raise ValueError('Frozen output changed')
    return f


def frozen_music(spec, metrics, target, font_path, frozen_alpha):
    """Replay documented GT06 mask parts solely to audit frozen intersections.

    This creates no score output. Byte-identical union with frozen alpha is required.
    """
    staff = spec['staff']
    inter = staff['interline']
    size = frozen_alpha.size
    parts = []
    tt = TTFont(font_path)
    gg = tt['glyf'][tt.getBestCmap()[ord(HEAD)]]
    units = (gg.xMin, gg.yMin, gg.xMax, gg.yMax)
    font = ImageFont.truetype(
        str(font_path), round(1.25 * inter * tt['head'].unitsPerEm / (gg.xMax - gg.xMin))
    )
    for event, info in zip(spec['events'], metrics['events']):
        x, y = info['requested_anchor']
        mask, actual = glyph(size, font, HEAD, (x, y), units, font.size / tt['head'].unitsPerEm)
        if actual['canonical_alpha_sha256'] != info['canonical_alpha_sha256']:
            raise ValueError('Glyph replay mismatch')
        parts.append(np.asarray(mask))
        pix = np.argwhere(np.asarray(mask) > 0)
        up = event['stem_side'] == 'RIGHT'
        edge = int(pix[:, 1].max() - 1 if up else pix[:, 1].min() + 1)
        attach = float(np.median(pix[pix[:, 1] == edge, 0]))
        b = metrics['beam_geometry'][0]
        end = line_y(b['line'], edge) + (-1 if up else 1) * b['thickness'] / 2
        stem = Image.new('L', size)
        ImageDraw.Draw(stem).line([(edge, attach), (edge, end)], fill=255, width=2)
        parts.append(np.asarray(stem))
        from music21 import pitch

        pos = 35 - pitch.Pitch(info['target_pitch']).diatonicNoteNum
        ledger = Image.new('L', size)
        d = ImageDraw.Draw(ledger)
        positions = (
            range(6, pos + 1, 2) if pos >= 6 else range(-6, pos - 1, -2) if pos <= -6 else []
        )
        for p in positions:
            ly = line_y(staff['lines'][2], x) + p * inter / 2
            d.line([(x - 0.875 * inter, ly), (x + 0.875 * inter, ly)], fill=255, width=2)
        parts.append(np.asarray(ledger))
    for b in metrics['beam_geometry']:
        layer = Image.new('L', size)
        d = ImageDraw.Draw(layer)
        (x0, y0), (x1, y1) = b['line']
        h = b['thickness'] / 2
        d.polygon([(x0, y0 - h), (x1 + 1, y1 - h), (x1 + 1, y1 + h), (x0, y0 + h)], fill=255)
        parts.append(np.asarray(layer))
    music = np.maximum.reduce(parts)
    sf = Image.new('L', size)
    d = ImageDraw.Draw(sf)
    left, right = spec['left'], spec['right']
    for line in staff['lines']:
        d.line(
            [(left, line_y(line, left))]
            + [tuple(p) for p in line if left < p[0] < right]
            + [(right, line_y(line, right))],
            fill=255,
            width=2,
        )
    bar = Image.new('L', size)
    d = ImageDraw.Draw(bar)
    for x in [left, right]:
        d.line(
            [(x, line_y(staff['lines'][0], x)), (x, line_y(staff['lines'][-1], x))],
            fill=255,
            width=2,
        )
    if not np.array_equal(
        np.maximum.reduce([music, np.asarray(sf), np.asarray(bar)]), np.asarray(frozen_alpha)
    ):
        raise ValueError('Frozen notation replay not byte-identical')
    return music > 0


def neutral_packet(source, cases, out):
    """Private mapping stays outside public packet; no answers/predictions included."""
    out.mkdir(parents=True)
    forms = []
    private = []
    for ident, bbox in cases:
        case = hashlib.sha256(('gt07a-source-' + ident).encode()).hexdigest()[:20]
        source.crop(tuple(bbox)).save(out / f'{case}.png')
        forms.append(
            {
                'case_id': case,
                'image': case + '.png',
                'coordinate_system': 'crop-local pixel centers; no scaling',
                'text_extent_polygons': [],
                'uncertain_regions': [],
                'observation_label': None,
                'allowed_labels': ['TEXT', 'MUSIC', 'BACKGROUND', 'MIXED', 'UNKNOWN'],
                'notes': '',
            }
        )
        private.append({'case_id': case, 'source_object': ident, 'page_bbox': bbox})
    for reader in ['A', 'B']:
        dump(
            out / f'blank-{reader}.json',
            {
                'reader': reader,
                'independence_attestation': None,
                'excluded_prior_exposure': None,
                'cases': forms,
            },
        )
    (out / 'README.txt').write_text(
        'Source-only extent review. No expected answers are supplied. Readers A and B work separately, declare prior exposure and exclusions, and save original observations immutably. A custodian hashes/freezes each submission without sharing it. Only after BOTH are frozen may a separate adjudicator inspect disagreements; preserve both originals and record decisions in a separate file. Mark UNKNOWN/MIXED freely. No labels have been collected. Do not expose predictions, OCR strings, coordinator support masks or classifications. Crops overlap; do not treat them as independent accuracy cases.\n'
    )
    return private


def audit(gt01, gt06, font, out):
    if out.exists() or any(
        r.resolve() == out.resolve() or r.resolve() in out.resolve().parents for r in [gt01, gt06]
    ):
        raise ValueError('Separate new diagnostic output required')
    verify_inputs(gt01)
    verify_freeze(gt06 / 'gt06-output')
    b = gt01 / 'predictions/baseline-exec/source'
    graph = json.loads((b / 'visual-graph.json').read_text())
    spec = json.loads((gt06 / 'gt06-inputs/selection.json').read_text())
    metrics = json.loads((gt06 / 'gt06-output/rendering-metrics.json').read_text())
    if sha(b / 'source.png') != spec['source_sha256'] or sha(font) != metrics['font_sha256']:
        raise ValueError('Source/font changed')
    source = Image.open(b / 'source.png')
    size = source.size
    gray = np.asarray(source.convert('L'))
    glyphs = glyphs_from_omr(b / 'recognized.omr')
    with zipfile.ZipFile(b / 'recognized.omr') as z:
        binary = Image.open(io.BytesIO(z.read('sheet#1/BINARY.png'))).convert('L')
        xml = safe_xml(z.read('sheet#1/sheet#1.xml'))
    if binary.size != size:
        raise ValueError('Processed/source page alignment mismatch')
    raw = {n.get('id'): n for n in xml.findall('.//sig/inters/*')}
    raw_edges = {
        (r.get('source'), r.get('target'))
        for r in xml.iter('relation')
        if r.find('containment') is not None
    }
    ids = descendants(graph, 'sheet#1:4134')
    text_pixels = set()
    lineage = []
    for ident in ids:
        s = graph['symbols'][ident]
        attrs = dict(s['attributes'])
        n = raw[s['source_id']]
        if dict(n.attrib) != attrs:
            raise ValueError('Frozen graph/raw Inter mismatch')
        children = [
            r['target']
            for r in graph['relations']
            if r['source'] == ident and r['kind'] == 'contains'
        ]
        if any(
            (s['source_id'], graph['symbols'][c]['source_id']) not in raw_edges for c in children
        ):
            raise ValueError('Raw containment mismatch')
        pixels = glyphs.get(s['page'] + ':' + attrs.get('glyph', ''), frozenset()) or frozenset()
        text_pixels.update(pixels)
        bands = []
        for y in sorted({y for _, y in pixels}):
            if not bands or y > bands[-1][-1] + 1:
                bands.append([y])
            else:
                bands[-1].append(y)
        lineage.append(
            {
                'id': ident,
                'kind': s['kind'],
                'raw_attributes': attrs,
                'bbox': s['geometry']['bbox'],
                'location': s['geometry']['location'],
                'children': children,
                'relations': [r for r in graph['relations'] if ident in [r['source'], r['target']]],
                'glyph_pixel_count': len(pixels),
                'glyph_runs': rle(pixels),
                'occupied_row_bands': [[v[0], v[-1]] for v in bands],
                'raw_inter_xml': ET.tostring(n, encoding='unicode'),
            }
        )
    music_pixels = set()
    music_ids = []
    for s in graph['symbols'].values():
        if s['kind'] not in MUSICAL:
            continue
        attrs = dict(s['attributes'])
        pixels = glyphs.get(s['page'] + ':' + attrs.get('glyph', ''), frozenset()) or frozenset()
        if pixels:
            music_pixels.update(pixels)
            music_ids.append(s['id'])
    text = mask_of(size, text_pixels)
    music = mask_of(size, music_pixels)
    labels = classify(text, music)
    out.mkdir(parents=True)
    context = (900, 548, 1330, 1051)
    cases = [('sentence-context', context)]
    for row in lineage:
        box = tuple(map(int, row['bbox']))
        cases.append((row['id'], box))
        stem = row['id'].split(':')[-1]
        crop = source.crop(box)
        crop.save(out / f'object-{stem}-source.png')
        crop.convert('L').save(out / f'object-{stem}-gray.png')
        crop.convert('RGBA').getchannel('A').save(out / f'object-{stem}-source-alpha.png')
    source.crop(context).save(out / 'direction-context-source.png')
    palette = np.array(
        [[240, 240, 240], [0, 150, 255], [255, 120, 0], [200, 0, 200]], dtype=np.uint8
    )
    overlay = Image.fromarray(palette[labels]).crop(context)
    overlay.save(out / 'diagnostic-support-categories.png')
    for name, mask in [('text-glyph-support', text), ('music-glyph-support', music)]:
        Image.fromarray((mask.astype('uint8') * 255)).crop(context).save(out / (name + '.png'))
    private = neutral_packet(source, cases, out / 'independent-review-packet')
    dump(out / 'custodian-only.json', private)
    broad = np.zeros_like(text)
    for region in spec['protected']:
        x0, y0, x1, y1 = region['bbox']
        broad[
            max(0, math.floor(y0)) : min(size[1], math.ceil(y1)),
            max(0, math.floor(x0)) : min(size[0], math.ceil(x1)),
        ] = True
    target_reports = []
    for m in metrics['metrics']:
        target = m['target']
        a = Image.open(gt06 / f'gt06-output/{target}-notation-alpha.png')
        moving = frozen_music(spec, m, target, font, a)
        count = int(np.count_nonzero(moving & broad))
        dark_count = int(np.count_nonzero(moving & broad & (gray < 127)))
        if (
            count != m['protected_envelope_contact_pixels']
            or dark_count != m['protected_source_dark_contact_pixels']
        ):
            raise ValueError('Historical contact counts not reproduced')
        region_counts = []
        for ident in ['sheet#1:4134', 'sheet#1:4135']:
            region = np.zeros_like(text)
            x0, y0, x1, y1 = map(int, graph['symbols'][ident]['geometry']['bbox'])
            region[y0:y1, x0:x1] = True
            hit = moving & region
            region_counts.append(
                {
                    'id': ident,
                    'broad_envelope_pixels': int(hit.sum()),
                    'confirmed_text_pixels': 'UNKNOWN',
                    'text_support_only_candidates': int(np.count_nonzero(hit & (labels == 1))),
                    'music_support_only_candidates': int(np.count_nonzero(hit & (labels == 2))),
                    'shared_or_ambiguous': int(np.count_nonzero(hit & (labels == 3))),
                    'unclassified': int(np.count_nonzero(hit & (labels == 0))),
                    'independently_confirmed_source_music_pixels': 'UNKNOWN',
                }
            )
        target_reports.append(
            {
                'target': target,
                'all_protections_union_intersections': count,
                'original_dark_in_union': dark_count,
                'regions': region_counts,
                'confirmed_text_intersection': 'UNKNOWN',
                'frozen_alpha_replay_exact': True,
            }
        )
    report = {
        'decision': (
            'TEXT_PROVENANCE_EVIDENCE_READY'
            if all(r['glyph_pixel_count'] for r in lineage if r['kind'] == 'word')
            else 'TEXT_PROVENANCE_UNRESOLVED'
        ),
        'purpose': 'LINEAGE_AND_REVIEW_READY_NOT_OWNERSHIP_AUTHORIZATION',
        'source_sha256': sha(b / 'source.png'),
        'omr_sha256': sha(b / 'recognized.omr'),
        'graph_sha256': sha(b / 'visual-graph.json'),
        'gt06_freeze_sha256': sha(gt06 / 'gt06-output/prototype-freeze.json'),
        'protected_regions_sha256': hashlib.sha256(
            json.dumps(spec['protected'], sort_keys=True).encode()
        ).hexdigest(),
        'protocol_sha256': sha(DESIGN),
        'size': size,
        'source_mode': source.mode,
        'gray_derivation': 'Pillow convert L; diagnostic only, original untouched',
        'alpha': 'Original RGB is opaque; source-alpha artifacts are uniformly 255, not symbol masks',
        'lineage': lineage,
        'text_support_pixel_count': len(text_pixels),
        'text_music_shared_pixels': int(np.count_nonzero(text & music)),
        'text_support_binary_agreement': int(np.count_nonzero(text & (np.asarray(binary) == 0))),
        'candidate_categories_not_source_ownership': True,
        'target_intersections': target_reports,
        'independent_human_labels': 0,
        'confirmed_text_extents': 'UNKNOWN',
        'protection_change': 'NONE',
        'musical_attachment_to_text': [
            r
            for r in graph['relations']
            if (r['source'] in ids or r['target'] in ids) and r['kind'] != 'contains'
        ],
        'packet_files': file_hashes(out / 'independent-review-packet'),
        'source_hash_after': sha(b / 'source.png'),
    }
    if report['source_sha256'] != report['source_hash_after']:
        raise ValueError('Source changed')
    dump(out / 'text-provenance-report.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = audit(
        Path('/private/tmp/capomatic-v4-ground-truth-01/ground-truth-01-output'),
        Path('/private/tmp/capomatic-v4-gt06-extended'),
        Path('/private/tmp/capomatic-v4-gt04-visual/ground-truth-04-output/font/FreeSerif.ttf'),
        a.out,
    )
    print(result['decision'])
