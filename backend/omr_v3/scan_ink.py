"""Conservative component ownership from retained source samples and OMR runs.

Run coverage is a necessary source-ink test, not a semantic or geometry proof.
Shared staff pixels and unexplained RGB edge samples never grant erase rights.
"""
from __future__ import annotations

import io
import zipfile
from xml.etree import ElementTree as ET

import cv2
import numpy as np
from PIL import Image

from .core import MAX_PIXELS

MUSIC_KINDS = frozenset({'head', 'stem', 'beam', 'beam-hook', 'flag', 'slur',
                         'alter', 'key-alter', 'ledger', 'augmentation-dot'})


def relations(system):
    """Read actual Audiveris wrapper relations, retaining typed child evidence."""
    result = []
    for relation in system.findall('sig/relations/*'):
        children = list(relation)
        kind = children[0].tag if relation.tag == 'relation' and len(children) == 1 else relation.tag
        result.append({'source': relation.get('source'), 'target': relation.get('target'),
                       'kind': kind, 'attributes': dict(children[0].attrib) if children else {}})
    return result


def run_mask(glyph, size):
    """Decode a bounded glyph tile; return its original pixel-edge origin."""
    table = glyph.find('run-table')
    if table is None:
        raise ValueError('RUN_TABLE_MISSING')
    x, y = int(glyph.get('left')), int(glyph.get('top'))
    w, h = int(table.get('width')), int(table.get('height'))
    if min(x, y) < 0 or min(w, h) <= 0 or w*h > MAX_PIXELS or x+w > size[0] or y+h > size[1]:
        raise ValueError('GLYPH_OUTSIDE_SOURCE')
    vertical = table.get('orientation') == 'VERTICAL'
    if table.get('orientation') not in {'VERTICAL', 'HORIZONTAL'}:
        raise ValueError('RUN_ORIENTATION_UNSUPPORTED')
    sequences = table.findall('runs')
    if len(sequences) != (w if vertical else h):
        raise ValueError('RUN_SEQUENCE_COUNT')
    tile = np.zeros((h, w), dtype=bool)
    for index, sequence in enumerate(sequences):
        cursor = 0
        for run_index, length in enumerate(map(int, (sequence.text or '').split())):
            end = cursor+length
            if length < 0 or end > (h if vertical else w):
                raise ValueError('RUN_LENGTH_OUTSIDE_GLYPH')
            if run_index % 2 == 0:
                if vertical:
                    tile[cursor:end, index] = True
                else:
                    tile[index, cursor:end] = True
            cursor = end
    if not tile.any():
        raise ValueError('EMPTY_GLYPH_SUPPORT')
    return x, y, tile


def _pack(masks):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, mask in masks.items():
            png = io.BytesIO()
            Image.fromarray(mask.astype(np.uint8)*255).save(png, format='PNG')
            archive.writestr(name+'.png', png.getvalue())
    return out.getvalue()


def analyze_source(png: bytes, omr: bytes) -> tuple[dict, bytes]:
    """Produce coverage/protection partition and diagnostic masks without editing pixels."""
    from .source_layout import digest
    with Image.open(io.BytesIO(png)) as source:
        if source.width*source.height > MAX_PIXELS:
            raise ValueError('SOURCE_PIXEL_LIMIT')
        rgb = np.asarray(source.convert('RGB'))
    h, w = rgb.shape[:2]
    if w*h > MAX_PIXELS:
        raise ValueError('SOURCE_PIXEL_LIMIT')
    with zipfile.ZipFile(io.BytesIO(omr)) as archive:
        infos = archive.infolist()
        if len(infos) > 200 or sum(i.file_size for i in infos) > 256*1024*1024:
            raise ValueError('OMR_ARCHIVE_LIMIT')
        sheets = [i for i in infos if i.filename.startswith('sheet#')
                  and i.filename.endswith('.xml') and i.filename.count('/') == 1]
        if len(sheets) != 1:
            raise ValueError('OMR_SHEET_COUNT')
        xml = archive.read(sheets[0])
        if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
            raise ValueError('OMR_XML_ENTITIES')
        root = ET.fromstring(xml)
        binary_path = sheets[0].filename.rsplit('/', 1)[0]+'/BINARY.png'
        if binary_path not in archive.namelist():
            return {'status': 'UNAVAILABLE', 'reasons': ['OMR_BINARY_MISSING']}, b''
        with Image.open(io.BytesIO(archive.read(binary_path))) as image:
            if image.size != (w, h):
                raise ValueError('BINARY_SOURCE_SIZE_MISMATCH')
            binary = np.asarray(image.convert('L'))
    if binary.shape != (h, w):
        raise ValueError('BINARY_SOURCE_SIZE_MISMATCH')
    music, staff, other = (np.zeros((h, w), dtype=bool) for _ in range(3))
    owners, glyphs, issues = {}, {}, []
    object_systems, measure_refs, tiles = {}, {}, {}
    all_relations = []
    for system in root.findall('page/system'):
        for obj in system.findall('sig/inters/*'):
            ident = obj.get('id')
            if ident in owners:
                issues.append({'code': 'DUPLICATE_OBJECT_ID', 'object': ident})
            owners[ident] = obj
            object_systems[ident] = system.get('id')
        all_relations.extend(relations(system))
        for measure in system.findall('part/measure'):
            for field in ('head-chords', 'rest-chords', 'clefs', 'keys', 'times'):
                for ident in (measure.findtext(field) or '').split():
                    measure_refs.setdefault(ident, set()).add(measure.get('id'))
        for line in system.findall('part/staff/lines/line'):
            if line.get('glyph'):
                glyphs.setdefault(line.get('glyph'), set()).add('staff')
    for edge in all_relations:
        if edge['source'] not in owners or edge['target'] not in owners:
            issues.append({'code': 'DANGLING_OBJECT_RELATION', **edge})
    # Membership is provenance only: endpoints can legitimately span measures.
    for _ in range(3):
        for edge in all_relations:
            a, b = edge['source'], edge['target']
            if edge['kind'] in {'containment', 'head-stem'}:
                measure_refs.setdefault(b, set()).update(measure_refs.get(a, set()))
            elif edge['kind'] in {'beam-stem', 'slur-head', 'alter-head', 'augmentation', 'flag-stem'}:
                measure_refs.setdefault(a, set()).update(measure_refs.get(b, set()))
    for obj in owners.values():
        if obj.get('glyph'):
            glyphs.setdefault(obj.get('glyph'), set()).add('music' if obj.tag in MUSIC_KINDS else 'other')
    seen = set()
    for glyph in root.findall('glyph-index/glyph'):
        ident = glyph.get('id')
        if ident in seen:
            issues.append({'code': 'DUPLICATE_GLYPH_ID', 'glyph': ident})
            continue
        seen.add(ident)
        if ident not in glyphs:
            continue
        try:
            x, y, tile = run_mask(glyph, (w, h))
            if np.any(binary[y:y+tile.shape[0], x:x+tile.shape[1]][tile] != 0):
                raise ValueError('GLYPH_BINARY_SUPPORT_MISMATCH')
        except (ValueError, TypeError) as exc:
            issues.append({'code': str(exc), 'glyph': ident})
            continue
        tiles[ident] = (x, y, tile)
        for kind in glyphs[ident]:
            target = {'music': music, 'staff': staff, 'other': other}[kind]
            target[y:y+tile.shape[0], x:x+tile.shape[1]] |= tile
    for missing in sorted(set(glyphs)-seen):
        issues.append({'code': 'REFERENCED_GLYPH_MISSING', 'glyph': missing})
    foreground = np.any(rgb != 255, axis=2)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground.astype(np.uint8), 8)
    total = stats[:, cv2.CC_STAT_AREA]
    glyph_components = {}
    for ident, (x, y, tile) in tiles.items():
        component_ids = np.unique(labels[y:y+tile.shape[0], x:x+tile.shape[1]][tile])
        glyph_components[ident] = [int(c) for c in component_ids if c]
    component_objects, object_regions = {}, []
    for ident, obj in owners.items():
        if obj.get('glyph') not in glyph_components:
            continue
        components = glyph_components[obj.get('glyph')]
        bounds = obj.find('bounds')
        object_regions.append({'page': 1, 'system': object_systems[ident], 'object': ident,
            'glyph': obj.get('glyph'), 'measure_candidates': sorted(measure_refs.get(ident, set())),
            'region': dict(bounds.attrib) if bounds is not None else None, 'components': components})
        for component in components:
            component_objects.setdefault(component, []).append(ident)
    samples = lambda mask: np.bincount(labels[mask], minlength=count)
    nm, ns, no = samples(music), samples(staff), samples(other)
    covered = samples(music | staff)
    # Exact component coverage includes every decoded fringe pixel. A grayscale
    # edge, watermark or missed glyph cannot disappear behind a binary threshold.
    editable_ids = (nm > 0) & (ns == 0) & (no == 0) & (covered == total)
    editable_ids[0] = False
    if issues:
        editable_ids[:] = False
    owned = editable_ids[labels]
    shared_ids = (nm > 0) & (ns > 0)
    protected_touch_ids = (nm > 0) & ((no > 0) | (covered != total))
    ambiguous = (shared_ids | protected_touch_ids)[labels] & foreground & ~owned
    protected = ~owned
    blockers = []
    for component in np.flatnonzero((nm > 0) & ~editable_ids):
        x, y, cw, ch, area = map(int, stats[component])
        codes = []
        if ns[component]:
            codes.append('MUSIC_STAFF_COMPONENT_REQUIRES_RECONSTRUCTION_PROOF')
        if no[component]:
            codes.append('MUSIC_PROTECTED_GLYPH_CONTACT')
        if covered[component] != total[component]:
            codes.append('UNASSIGNED_SOURCE_RGB_OR_JPEG_EDGE')
        blockers.append({'page': 1, 'component': int(component),
                         'objects': component_objects.get(int(component), []), 'region': [x, y, x+cw, y+ch],
                         'pixels': area, 'codes': codes or ['SOURCE_STRUCTURE_UNVERIFIED']})
    lyric_regions = []
    for system_index, system in enumerate(root.findall('page/system'), 1):
        points = system.findall('part/staff/lines/line/point')
        if not points:
            continue
        bottom = max(float(p.get('y')) for p in points)
        next_system = root.findall('page/system')[system_index:system_index+1]
        next_points = next_system[0].findall('part/staff/lines/line/point') if next_system else []
        limit = min(float(p.get('y')) for p in next_points) if next_points else h
        for component in range(1, count):
            x, y, cw, ch, area = map(int, stats[component])
            if bottom < y and y+ch < limit and not nm[component] and not ns[component]:
                lyric_regions.append({'system': system_index, 'region': [x, y, x+cw, y+ch],
                                      'component': component, 'pixels': area,
                                      'status': 'PROTECTED_RESIDUAL_CANDIDATE_NOT_TEXT_VERIFIED'})
    report = {'status': 'COMPONENT_ANALYSIS_ONLY', 'source_png_sha256': digest(png),
              'source_omr_sha256': digest(omr), 'edit_authorized': False,
              'source_component_coverage_pixels': int(owned.sum()),
              'protected_pixels': int(protected.sum()), 'ambiguous_pixels': int(ambiguous.sum()),
              'music_staff_components': int(shared_ids.sum()),
              'unresolved_rgb_components': int(protected_touch_ids.sum()),
              'structure_issues': issues, 'blockers': blockers, 'object_regions': object_regions,
              'lyric_candidates': lyric_regions,
              'lyric_identity': 'UNMEASURED_NO_OUTPUT',
              'ownership_ready': False, 'semantic_and_object_plane_proof_required': True}
    masks = _pack({'component_coverage': owned, 'staff_support': staff,
                   'protected': protected, 'ambiguous': ambiguous})
    report['masks_sha256'] = digest(masks)
    return report, masks
