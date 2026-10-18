"""Offline persisted-state evidence, never source ownership or edit permission."""

from collections import Counter
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image

from .ink import glyphs_from_omr, pixels_from_runs, rle
from .masks import raster_digest
from .source_ink import PINNED_BUILD
from .visual_graph import load_visual_graph, safe_xml


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def reconstruct_no_staff(binary, staff_points):
    """Replay Picture.buildNoStaffBuffer on persisted state; not a runtime capture."""
    values = np.array(binary.convert('L'))
    if not set(np.unique(values)) <= {0, 255}:
        raise ValueError('Expected exact binary pixels')
    for x, y in staff_points:
        if not (0 <= x < binary.width and 0 <= y < binary.height):
            raise ValueError('Staff glyph outside page')
        values[y, x] = 255
    return Image.fromarray(values)


def extract_evidence(source_path, omr_path, out, *, expected_source_sha, expected_omr_sha):
    """Single-page, pinned-build extractor. Callers supply existing artifact bindings.

    Hash binding validates the selected pair, not historical input identity: OMR
    itself does not persist an original-input SHA. No missing resource is inferred.
    """
    source_path, omr_path, out = map(Path, (source_path, omr_path, out))
    if out.exists() and any(out.iterdir()):
        raise ValueError('New/empty output directory required')
    source_bytes, omr_bytes = source_path.read_bytes(), omr_path.read_bytes()
    if sha(source_bytes) != expected_source_sha or sha(omr_bytes) != expected_omr_sha:
        raise ValueError('Input hash binding mismatch')
    graph = load_visual_graph(omr_path)
    if len(graph.pages) != 1 or graph.invalid_geometry_count:
        raise ValueError('One valid page required')
    page = graph.pages[0]
    with Image.open(io.BytesIO(source_bytes)) as image:
        source = image.copy()
    if source.size != (page.width, page.height):
        raise ValueError('Source coordinate dimensions differ')
    glyphs = glyphs_from_omr(omr_path)
    with zipfile.ZipFile(omr_path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError('Duplicate archive resources')
        book_bytes = archive.read('book.xml')
        book = safe_xml(book_bytes)
        if book.get('software-build') != PINNED_BUILD:
            raise ValueError('Unverified build')
        root_bytes = archive.read(f'{page.id}/{page.id}.xml')
        root = safe_xml(root_bytes)
        binary_bytes = archive.read(f'{page.id}/BINARY.png')
        inventory = [{'name': i.filename, 'bytes': i.file_size} for i in archive.infolist()]
    with Image.open(io.BytesIO(binary_bytes)) as image:
        if image.size != source.size:
            raise ValueError('BINARY coordinate dimensions differ')
        binary = image.convert('L')
    for points in glyphs.values():
        if points is None or any(
            not (0 <= x < page.width and 0 <= y < page.height) for x, y in points
        ):
            raise ValueError('Invalid or out-of-page persisted glyph')
    staff_records, staff_union = [], set()
    for staff in graph.staves:
        xml = safe_xml(staff.source_xml.encode())
        for number, line in enumerate(xml.findall('lines/line'), 1):
            ident = page.id + ':' + str(line.get('glyph'))
            if not glyphs.get(ident):
                raise ValueError('Missing exact staff glyph support')
            points = glyphs[ident]
            staff_union.update(points)
            staff_records.append(
                {
                    'staff_id': staff.id,
                    'line_number': number,
                    'glyph_id': ident,
                    'polyline': staff.lines[number - 1],
                    'thickness': line.get('thickness'),
                    'attributed_runs': rle(points),
                    'pixel_count': len(points),
                    'hole_or_recovery_metadata': 'NOT_PERSISTED',
                    'source_ownership': False,
                }
            )
    if not staff_records:
        raise ValueError('Missing staff attribution')
    no_staff = reconstruct_no_staff(binary, staff_union)
    metadata = {
        page.id + ':' + g.get('id'): dict(g.attrib) for g in root.findall('glyph-index/glyph')
    }
    symbols = []
    for symbol in sorted(graph.symbols.values(), key=lambda s: s.id):
        attrs = dict(symbol.attributes)
        glyph_id = page.id + ':' + attrs['glyph'] if attrs.get('glyph') else None
        if glyph_id and glyph_id not in glyphs:
            raise ValueError('Dangling symbol glyph')
        symbols.append(
            {
                'id': symbol.id,
                'kind': symbol.kind,
                'glyph_id': glyph_id,
                'geometry': asdict(symbol.geometry),
                'relation_ids': symbol.relation_ids,
                'attributes': attrs,
                'source_xml': symbol.source_xml,
                'construction_parent_parts': 'NOT_PERSISTED',
                'instance_construction_history': 'NOT_PERSISTED',
            }
        )
    relations = [asdict(r) for r in graph.relations]
    payloads = {
        'source.png': (source_bytes, 'EXACT_INPUT_COPY'),
        'book.xml': (book_bytes, 'EXACT_PERSISTED_RESOURCE'),
        'binary.png': (binary_bytes, 'EXACT_PERSISTED_RESOURCE'),
        'sheet.xml': (root_bytes, 'EXACT_PERSISTED_RESOURCE'),
        'staff-evidence.json': (json_bytes(staff_records), 'EXACT_PERSISTED_ATTRIBUTION'),
        'glyph-support.json': (
            json_bytes(
                [
                    {'id': ident, 'attributes': metadata[ident], 'runs': rle(points)}
                    for ident, points in sorted(glyphs.items())
                ]
            ),
            'EXACT_DECODED_PERSISTED_SUPPORT',
        ),
        'symbol-lineage.json': (json_bytes(symbols), 'PERSISTED_REFERENCES_NOT_CONSTRUCTION_DAG'),
        'relations.json': (json_bytes(relations), 'DECODED_SIG_AND_EXPLICIT_REFERENCES'),
    }
    buffer = io.BytesIO()
    no_staff.save(buffer, format='PNG')
    payloads['no-staff.png'] = (
        buffer.getvalue(),
        'EXACT_PERSISTED_STATE_RECONSTRUCTION_NOT_RUNTIME_CAPTURE',
    )
    manifest = {
        'schema': 'capomatic.v3-evidence/1',
        'diagnostic_only': True,
        'edit_authorization': False,
        'source_sha256': sha(source_bytes),
        'source_raster_digest': raster_digest(source),
        'source_mode': source.mode,
        'omr_sha256': sha(omr_bytes),
        'audiveris_build_sha': PINNED_BUILD,
        'dimensions': list(source.size),
        'coordinate_system': 'ORIGINAL_AUDIVERIS_RASTER_XY',
        'input_binding': 'CALLER_SUPPLIED_HASH_PAIR_NOT_EMBEDDED_INPUT_DIGEST',
        'inventory': inventory,
        'declared_images': [
            {'key': e.findtext('key'), 'path': e.find('value').get('path')}
            for e in root.findall('picture/images/entry')
            if e.find('value') is not None
        ],
        'generation_method': 'OFFLINE_OMR_EXTRACTION_NO_AUDIVERIS_EXECUTION',
        'no_staff': {
            'method': 'BINARY whiten exact union of serialized StaffLine glyph runs',
            'historical_runtime_equality': 'UNVERIFIED_NO_RETAINED_RUNTIME_IMAGE',
            'staff_lines': len(staff_records),
            'staff_attributed_pixels': len(staff_union),
        },
        'files': {
            name: {'sha256': sha(data), 'status': status}
            for name, (data, status) in sorted(payloads.items())
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, (data, _) in payloads.items():
        (out / name).write_bytes(data)
    (out / 'manifest.json').write_bytes(json_bytes(manifest))
    return manifest


def attribute_handoff(graph, glyphs, staff_points, binary, handoff, source):
    """Exact persisted-support intersections, not a new eligibility/ownership verdict.

    Labels overlap; UNKNOWN is only the residual after all direct glyph support.
    A support hit explains representation, never proves original-pixel ownership.
    """
    symbol_support = {}
    by_pixel = {}
    for s in graph.symbols.values():
        glyph = dict(s.attributes).get('glyph')
        points = glyphs.get(s.page + ':' + glyph, ()) if glyph else ()
        symbol_support[s.id] = points
        for point in points:
            by_pixel.setdefault(point, set()).add(s.id)
    groups, all_remote, all_explained = [], set(), set()
    attachment_counts, attachment_ids = Counter(), {}
    binary_values = np.asarray(binary)
    gray = np.asarray(source.convert('L'))
    for group in handoff['groups']:
        if group['ownership_evidence_status'] != 'VERIFIED_PARTIAL':
            continue
        members = set(group['members'])
        remote = pixels_from_runs(group['remote_continuation'])
        labels = {}
        for point in remote:
            names = set()
            if point in staff_points:
                names.add('STAFF_GLYPH')
            for ident in by_pixel.get(point, ()):
                kind = graph.symbols[ident].kind
                if ident in members:
                    names.add('SAME_ATOMIC_GROUP_SUPPORT')
                elif kind in {'ledger', 'slur', 'articulation', 'fermata'}:
                    names.add(kind.upper() + '_GLYPH')
                elif kind in {'head', 'stem', 'beam', 'beam-hook', 'flag', 'augmentation-dot'}:
                    names.add('NEIGHBORING_MUSICAL_GLYPH')
                else:
                    names.add('OTHER_PERSISTED_GLYPH')
            if not names:
                names.add(
                    'UNKNOWN_BINARY_INK'
                    if binary_values[point[1], point[0]] == 0
                    else 'OUTSIDE_PERSISTED_BINARY'
                )
            for name in names:
                labels.setdefault(name, set()).add(point)
        attachments = []
        if any(b.startswith('MOVING_ATTACHMENT:') for b in group['blockers']):
            for attachment in group['attachments']:
                ident = attachment['symbol_id']
                symbol = graph.symbols[ident]
                edges = [r for r in graph.relations if ident in (r.source, r.target)]
                extensions = [r for r in edges if r.kind in {'left-extension', 'right-extension'}]
                explicit = [
                    r
                    for r in edges
                    if r.kind in {'slur-head', 'chord-articulation', 'fermata-chord'}
                ]
                support = bool(symbol_support[ident])
                if extensions:
                    category = 'CROSS_SYSTEM_EXTENSION'
                elif explicit and symbol.geometry.region is not None:
                    category = (
                        'EXPLICIT_RELATION_AND_GEOMETRY_AVAILABLE'
                        if support
                        else 'RELATION_AVAILABLE_BUT_PIXEL_SUPPORT_MISSING'
                    )
                else:
                    category = (
                        'PIXEL_SUPPORT_AVAILABLE_BUT_RELATION_AMBIGUOUS' if support else 'UNKNOWN'
                    )
                attachment_counts[category] += 1
                attachment_ids[ident] = category
                attachments.append(
                    {
                        'symbol_id': ident,
                        'kind': symbol.kind,
                        'category': category,
                        'relation_ids': [r.id for r in edges],
                        'glyph_pixels': len(symbol_support[ident]),
                        'group_ownership_proven': False,
                    }
                )
        explained = (
            set().union(
                *(
                    ps
                    for name, ps in labels.items()
                    if name not in {'UNKNOWN_BINARY_INK', 'OUTSIDE_PERSISTED_BINARY'}
                )
            )
            if labels
            else set()
        )
        all_remote.update(remote)
        all_explained.update(explained)
        groups.append(
            {
                'group_id': group['group_id'],
                'remote_pixels': len(remote),
                'attribution': {k: len(v) for k, v in sorted(labels.items())},
                'fully_explained_by_persisted_support': bool(remote) and remote <= explained,
                'attachments': attachments,
                'eligibility_unchanged': True,
            }
        )
    return {
        'method': 'EXACT_PIXEL_SUPPORT_INTERSECTION_NONEXCLUSIVE_NOT_OWNERSHIP',
        'groups': groups,
        'group_counts_by_explanation': dict(
            sorted(Counter(k for g in groups for k in g['attribution']).items())
        ),
        'pixel_reference_counts': dict(
            sorted(
                Counter(
                    {
                        k: sum(g['attribution'].get(k, 0) for g in groups)
                        for k in {k for g in groups for k in g['attribution']}
                    }
                ).items()
            )
        ),
        'source_gray_histogram_at_distinct_remote_pixels': dict(
            sorted(Counter(int(gray[p[1], p[0]]) for p in all_remote).items())
        ),
        'distinct_remote_pixels': len(all_remote),
        'distinct_explained_remote_pixels': len(all_explained),
        'fully_explained_groups': sum(g['fully_explained_by_persisted_support'] for g in groups),
        'attachment_reference_counts': dict(sorted(attachment_counts.items())),
        'unique_attachment_counts': dict(sorted(Counter(attachment_ids.values()).items())),
        'attachment_blocked_groups': sum(bool(g['attachments']) for g in groups),
        'construction_seed_part_attribution': 'NOT_RECOVERABLE_FROM_SERIALIZED_CONSTRUCTION_DAG',
    }
