"""Immutable source evidence for the geometry-locked score API.

No bbox, OCR text, or research approval grants permission to erase pixels.
The current OMR adapter produces diagnostics, not complete ownership proofs.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import io
import json
import math
import zipfile
from xml.etree import ElementTree as ET

from PIL import Image
import numpy as np

from .core import MAX_PIXELS, ScoreError


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Affine:
    """x' = a*x + c*y + e; y' = b*x + d*y + f, at pixel edges."""
    a: float = 1
    b: float = 0
    c: float = 0
    d: float = 1
    e: float = 0
    f: float = 0

    def __post_init__(self):
        if not all(math.isfinite(v) for v in self.values) or abs(self.a*self.d-self.b*self.c) < 1e-12:
            raise ScoreError('Unverified or singular coordinate transform')

    @property
    def values(self):
        return (self.a, self.b, self.c, self.d, self.e, self.f)

    def point(self, x, y):
        return (self.a*x+self.c*y+self.e, self.b*x+self.d*y+self.f)

    def inverse(self):
        det = self.a*self.d-self.b*self.c
        return Affine(self.d/det, -self.b/det, -self.c/det, self.a/det,
                      (self.c*self.f-self.d*self.e)/det,
                      (self.b*self.e-self.a*self.f)/det)


def pdf_metadata(data: bytes) -> list[dict]:
    """Retain PDF page boxes and rotation; reject transforms we cannot verify."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ScoreError('Encrypted PDF coordinate transforms are not supported')
        result = []
        for number, page in enumerate(reader.pages, 1):
            boxes = {name: tuple(float(v) for v in getattr(page, name))
                     for name in ('mediabox', 'cropbox', 'trimbox', 'bleedbox', 'artbox')}
            if any(not all(math.isfinite(v) for v in box) or box[2] <= box[0] or box[3] <= box[1]
                   for box in boxes.values()):
                raise ScoreError('Invalid PDF page box', report={'page': number})
            unit = float(page.get('/UserUnit', 1))
            rotation = int(page.get('/Rotate', 0))
            if unit != 1 or rotation % 90:
                raise ScoreError('Unverified PDF unit or rotation', report={'page': number})
            media, crop = boxes['mediabox'], boxes['cropbox']
            if not (media[0] <= crop[0] < crop[2] <= media[2]
                    and media[1] <= crop[1] < crop[3] <= media[3]):
                raise ScoreError('CropBox outside MediaBox is unsupported', report={'page': number})
            result.append({'boxes': boxes, 'rotation': rotation % 360, 'user_unit': unit})
        return result
    except (PdfReadError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise ScoreError('Cannot verify PDF coordinate metadata') from exc


def pdf_transform(metadata: dict, dpi: int) -> tuple[Affine, tuple[int, int]]:
    x0, y0, x1, y1 = metadata['boxes']['cropbox']
    s = dpi / 72
    transforms = {
        0: Affine(s, 0, 0, -s, -s*x0, s*y1),
        90: Affine(0, s, s, 0, -s*y0, -s*x0),
        180: Affine(-s, 0, 0, s, s*x1, -s*y0),
        270: Affine(0, -s, -s, 0, s*y1, s*x1),
    }
    # Decimal PDF boxes frequently produce 3342.0000000000005 in binary
    # floats. Compute raster extents exactly, without resizing the result.
    w = (Fraction(str(x1))-Fraction(str(x0))) * dpi / 72
    h = (Fraction(str(y1))-Fraction(str(y0))) * dpi / 72
    if metadata['rotation'] in (90, 270):
        w, h = h, w
    return transforms[metadata['rotation']], (math.ceil(w), math.ceil(h))


def _omr_inventory(data: bytes, source_png: bytes) -> dict:
    """Expose object/relation IDs without converting geometry into ownership."""
    if not data:
        return {'geometry_ready': False, 'issues': ['OMR_BUNDLE_MISSING'], 'objects': []}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > 200 or sum(i.file_size for i in infos) > 256*1024*1024:
                raise ValueError('OMR archive exceeds bounds')
            sheets = [i for i in infos if i.filename.startswith('sheet#')
                      and i.filename.endswith('.xml') and i.filename.count('/') == 1]
            if len(sheets) != 1 or sheets[0].file_size > 64*1024*1024:
                raise ValueError('Expected one bounded OMR sheet')
            xml = archive.read(sheets[0])
            gray_path = sheets[0].filename.split('/')[0] + '/GRAY.png'
            gray_png = archive.read(gray_path) if gray_path in archive.namelist() else None
        if b'\0' in xml or b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
            raise ValueError('Unsupported OMR XML')
        root = ET.fromstring(xml)
        picture = root.find('picture')
        dimensions = (int(picture.get('width')), int(picture.get('height')))
        issues = []
        with Image.open(io.BytesIO(source_png)) as source:
            size = source.size
            # Audiveris Picture.adjustImageFormat uses maxRgbToGray, not luma.
            source_gray = np.asarray(source.convert('RGB')).max(axis=2).tobytes()
        if gray_png is None:
            issues.append('OMR_SOURCE_RASTER_IDENTITY_UNVERIFIED')
        else:
            with Image.open(io.BytesIO(gray_png)) as gray:
                if gray.size != size or gray.convert('L').tobytes() != source_gray:
                    issues.append('OMR_SOURCE_RASTER_IDENTITY_MISMATCH')
        if dimensions != size:
            issues.append('OMR_RASTER_DIMENSION_MISMATCH')
        skew = root.find('skew')
        raster_identity_ready = not issues
        # A skew estimate does not establish whether any coordinate moved.
        # The adapter has no execution-bound object-plane proof, even at zero.
        issues.append('OMR_OBJECT_COORDINATE_PLANE_UNVERIFIED')
        from .scan_ink import relations as read_relations
        objects = []
        for system in root.findall('.//page/system'):
            relations = [(r['source'], r['target'], r['kind']) for r in read_relations(system)]
            for obj in system.findall('sig/inters/*'):
                ident = obj.get('id')
                objects.append({'object': ident, 'kind': obj.tag, 'system': system.get('id'),
                                'measure': obj.get('measure'), 'glyph': obj.get('glyph'),
                                'evidence_region': dict(obj.find('bounds').attrib)
                                    if obj.find('bounds') is not None else None,
                                'relations': [r for r in relations if ident in r[:2]],
                                'status': 'UNVERIFIED',
                                'reasons': ['COMPLETE_SOURCE_PIXEL_OWNERSHIP_UNAVAILABLE']})
        return {'geometry_ready': False, 'raster_identity_ready': raster_identity_ready,
                'issues': issues, 'objects': objects,
                'omr_size': dimensions, 'omr_sha256': digest(data),
                'gray_sha256': digest(gray_png) if gray_png else None,
                'skew_slope': float(skew.get('slope')) if skew is not None else None,
                'staff_model_count': len(root.findall('.//staff')),
                'glyph_count': len(root.findall('.//glyph')),
                'coordinate_plane': 'UNVERIFIED',
                'ownership_ready': False}
    except (zipfile.BadZipFile, ET.ParseError, ValueError, TypeError, AttributeError,
            KeyError, RuntimeError, OSError, Image.DecompressionBombError) as exc:
        return {'geometry_ready': False, 'issues': ['OMR_GEOMETRY_UNREADABLE'],
                'error': str(exc), 'objects': []}


@dataclass(frozen=True)
class SourcePage:
    png: bytes
    omr: bytes
    metadata_json: bytes
    evidence_json: bytes
    ink_masks: bytes = b''

    @property
    def metadata(self):
        return json.loads(self.metadata_json)

    @property
    def evidence(self):
        return json.loads(self.evidence_json)

    @property
    def byte_size(self):
        return sum(map(len, (self.png, self.omr, self.metadata_json, self.evidence_json, self.ink_masks)))

    @classmethod
    def capture(cls, png: bytes, omr: bytes, metadata: dict):
        with Image.open(io.BytesIO(png)) as image:
            if image.width*image.height > MAX_PIXELS:
                raise ScoreError('Source raster too large', 413)
            size = image.size
            rgb_sha256 = digest(image.convert('RGB').tobytes())
        if tuple(metadata['raster_size']) != size:
            raise ScoreError('Source raster size does not match coordinate contract')
        if metadata.get('raster_basis') == 'embedded_jpeg_rgb':
            if rgb_sha256 != metadata['decoded_rgb_sha256']:
                raise ScoreError('Embedded image RGB digest mismatch')
            a, b, c, d, e, f = metadata['image_placement']
            w, h = size
            transform = Affine(a/w, b/w, -c/h, -d/h, c+e, d+f)
            if (tuple(metadata['raster_to_pdf']) != transform.values
                    or tuple(metadata['pdf_to_raster']) != transform.inverse().values):
                raise ScoreError('Embedded image coordinate transform mismatch')
        elif 'pdf_to_raster' in metadata:
            transform, expected = pdf_transform(metadata, metadata['dpi'])
            if size != expected:
                raise ScoreError('PDF raster size does not match page transform')
            if tuple(metadata['pdf_to_raster']) != transform.values:
                raise ScoreError('PDF coordinate transform mismatch')
        evidence = _omr_inventory(omr, png)
        masks = b''
        if omr and 'OMR_GEOMETRY_UNREADABLE' not in evidence['issues']:
            from .scan_ink import analyze_source
            try:
                ink, masks = analyze_source(png, omr)
                evidence['component_analysis'] = ink
            except (ValueError, TypeError, KeyError, ET.ParseError, zipfile.BadZipFile, OSError) as exc:
                evidence['component_analysis'] = {'status': 'UNAVAILABLE',
                    'edit_authorized': False, 'reason': str(exc)[:300]}
        metadata = {**metadata, 'png_sha256': digest(png), 'omr_sha256': digest(omr),
                    'raster_to_output': Affine().values,
                    'output_to_raster': Affine().values,
                    'raster_to_omr': Affine().values if evidence['geometry_ready'] else None,
                    'omr_to_raster': Affine().values if evidence['geometry_ready'] else None}
        return cls(png, omr, json.dumps(metadata, sort_keys=True).encode(),
                   json.dumps(evidence, sort_keys=True).encode(), masks)


@dataclass(frozen=True)
class SourceLayoutBundle:
    source: bytes
    suffix: str
    pages: tuple[SourcePage | None, ...]

    @property
    def byte_size(self):
        return len(self.source) + sum(p.byte_size for p in self.pages if p)

    @property
    def sha256(self):
        return digest(self.source)


def readiness(page: SourcePage | None, semantic_ready: bool, number: int,
              semitones: int | None = None) -> dict:
    """Evaluate requested rendering separately from detection and V3 consistency."""
    evidence = page.evidence if page else {'geometry_ready': False, 'objects': [],
                                          'issues': ['SOURCE_LAYOUT_UNAVAILABLE']}
    if page and evidence.get('native_profile_verified'):
        return {'semantic_ready': True, 'geometry_ready': True, 'lyric_layer_ready': True,
                'render_ready': False, 'render_request': {'semitones': semitones},
                'can_plan_geometry_render': True, 'reasons': [],
                'source_ink_safety': {'status': 'VERIFIED_NATIVE_SOURCE_ONLY',
                    'edit_authorized': False, 'target_plan_required': True,
                    'objects': evidence['objects'], 'reasons': []},
                'lyric_regions': evidence['lyric_regions']}
    reasons = [{'page': number, 'measure': None, 'object': None, 'code': code}
               for code in evidence['issues']]
    if not semantic_ready:
        reasons.append({'page': number, 'measure': None, 'object': None,
                        'code': 'SEMANTIC_EVENTS_OR_RELATIONS_UNVERIFIED'})
    # Full-page protection is deliberately retained. OCR absence is not proof
    # of absent lyrics; an unrecognised word may touch a stem or a slur.
    reasons.append({'page': number, 'measure': None, 'object': None,
                    'code': 'AUTOMATIC_LYRIC_PIXEL_SEPARATION_UNAVAILABLE'})
    reasons.append({'page': number, 'measure': None, 'object': None,
                    'code': 'COMPLETE_SOURCE_PIXEL_OWNERSHIP_UNAVAILABLE'})
    return {
        'semantic_ready': semantic_ready, 'geometry_ready': evidence['geometry_ready'],
        'lyric_layer_ready': False, 'render_ready': False,
        'render_request': {'semitones': semitones} if semitones is not None else None,
        'reasons': reasons,
        'source_ink_safety': {'status': 'UNVERIFIED', 'edit_authorized': False,
                              'protected_region': 'ENTIRE_SOURCE_PAGE',
                              'component_analysis': evidence.get('component_analysis'),
                              'objects': [{'page': number, **obj} for obj in evidence['objects']],
                              'reasons': ['COMPLETE_SOURCE_PIXEL_OWNERSHIP_UNAVAILABLE']},
        'measurements': {key: None for key in (
            'fixed_anchor_displacement_px', 'note_raster_error_xy_px', 'lyric_pixel_difference',
            'alpha_collisions', 'disconnected_relations', 'duplicate_symbols', 'clipping')},
    }
