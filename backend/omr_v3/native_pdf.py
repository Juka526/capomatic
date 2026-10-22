"""Verified source-object PDFs: deliberately narrow, non-OCR rendering profile.

This does NOT authorize edits to ordinary raster/OMR PDFs. Source PDFs carry
MusicXML, fixed staff/event geometry and three actual image layers. Every
layer, semantic object and displayed source pixel is verified before editing.
Supported music: single treble staff, 4/4, one whole note per measure, one key.
Other mandatory notation is rejected, never omitted.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile
from xml.etree import ElementTree as ET
import zlib
from functools import wraps

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (ArrayObject, BooleanObject, DecodedStreamObject,
                           DictionaryObject, NameObject, NumberObject, RectangleObject)

from . import core, music_guard
from .raster_anchor import glyph
from .source_layout import SourceLayoutBundle, SourcePage, pdf_metadata, digest
from .transpose import transpose_score

PROFILE = 'capomatic-native-layers-v1'
MAX_PROFILE_BYTES = 1_000_000
MUSIC_FONT = '/usr/share/fonts/truetype/freefont/FreeSerif.ttf'
# FreeSerif font design calibration (GT-13a4), never a score coordinate.
MUSIC_FONT_SHA256 = 'c1dd2270ff624d66a7f1cd23075b5ce05a662f560be06a70a9599065ce008355'
LYRIC_FONT = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'


def fail(code, **where):
    raise core.ScoreError(code, 422, {'first_blocker': code, **where})



def checked(operation):
    @wraps(operation)
    def run(*args, **kwargs):
        from pypdf.errors import PdfReadError
        try:
            return operation(*args, **kwargs)
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError, PdfReadError, zlib.error, ET.ParseError) as exc:
            raise core.ScoreError('NATIVE_SOURCE_STRUCTURE_INVALID', 422,
                                  {'first_blocker': 'NATIVE_SOURCE_STRUCTURE_INVALID',
                                   'detail': str(exc)[:300]}) from exc
    return run


def _stream_bytes(stream, limit):
    raw = stream._data
    if stream.get('/DecodeParms'):
        fail('UNSUPPORTED_STREAM_PREDICTOR')
    filter_name = stream.get('/Filter')
    if filter_name is None:
        decoded = raw
    elif filter_name == '/FlateDecode':
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(raw, limit+1)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            fail('STREAM_DECOMPRESSION_BOUND_OR_FORMAT')
    else:
        fail('UNSUPPORTED_STREAM_FILTER')
    if len(decoded) > limit:
        fail('STREAM_SIZE_LIMIT')
    return decoded

def _font(path, size):
    if not 8 <= size <= 256:
        fail('FONT_SIZE_UNSUPPORTED')
    try:
        return ImageFont.truetype(path, size)
    except OSError as exc:
        raise core.ScoreError('Native profile font unavailable', 503) from exc


def fonts():
    return (os.environ.get('CAPOMATIC_MUSIC_FONT', MUSIC_FONT),
            os.environ.get('CAPOMATIC_LYRIC_FONT', LYRIC_FONT))


def font_hashes():
    try:
        return [digest(Path(p).read_bytes()) for p in fonts()]
    except OSError as exc:
        raise core.ScoreError('Native profile font unavailable', 503) from exc


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 10000:
        fail('INVALID_GEOMETRY')
    return float(value)


def _point(value):
    if not isinstance(value, list) or len(value) != 2:
        fail('INVALID_GEOMETRY')
    return tuple(_number(v) for v in value)


def _mask(size):
    return Image.new('L', size)


def _overlap(a, b):
    return int(np.count_nonzero((np.asarray(a) > 0) & (np.asarray(b) > 0)))


def _union(a, b):
    return ImageChops.lighter(a, b)


def _blend(layers):
    image = Image.new('RGB', layers[0].size, 'white')
    for alpha in layers:
        image.paste((0, 0, 0), (0, 0), alpha)
    return image


def _glyph(size, font, char, point):
    # Fixed-phase canonical alpha and nearest-integer translation, reused from
    # the independently measured GT-05 algorithm; no source/score constants.
    return glyph(size, font, char, point, (0, 0, 0, 0), 1)


def _score(xml):
    from music21 import converter, stream, note, clef, meter, key, harmony, spanner
    core.validate(xml, '.musicxml')
    if b'\0' in xml:
        fail('UNSUPPORTED_XML_ENCODING')
    root = ET.fromstring(xml)
    allowed_xml = set('score-partwise work work-title movement-title identification creator encoding software encoding-date defaults scaling millimeters tenths part-list score-part part-name part attributes divisions key fifths time beats beat-type clef sign line measure note pitch step alter octave duration type'.split())
    for node in root.iter():
        if node.tag not in allowed_xml:
            fail('UNSUPPORTED_MUSICXML_CONSTRUCT', object=node.tag)
    try:
        score = converter.parseData(xml.decode(), format='musicxml')
    except Exception as exc:
        raise core.ScoreError('Native MusicXML cannot be parsed') from exc
    if len(score.parts) != 1:
        fail('UNSUPPORTED_PART_COUNT')
    measures = list(score.parts[0].getElementsByClass(stream.Measure))
    if not measures or len(measures) > 100:
        fail('UNSUPPORTED_MEASURE_COUNT')
    signatures = list(score.recurse().getElementsByClass(key.KeySignature))
    if len(signatures) != 1 or abs(signatures[0].sharps) > 7:
        fail('UNSUPPORTED_KEY_REGIONS')
    clefs = list(score.recurse().getElementsByClass(clef.Clef))
    times = list(score.recurse().getElementsByClass(meter.TimeSignature))
    if len(clefs) != 1 or not isinstance(clefs[0], clef.TrebleClef) or len(times) != 1 or times[0].ratioString != '4/4':
        fail('UNSUPPORTED_CLEF_OR_METER')
    if score.spannerBundle or score.recurse().getElementsByClass(harmony.ChordSymbol):
        fail('UNSUPPORTED_SPANNER_OR_CHORD')
    events = []
    allowed = {'Score', 'Part', 'Measure', 'TrebleClef', 'TimeSignature', 'KeySignature',
               'Note', 'Metadata', 'PartStaff', 'Instrument', 'ScoreLayout'}
    for element in score.recurse():
        if element.__class__.__name__ not in allowed:
            fail('UNSUPPORTED_MANDATORY_NOTATION', object=element.__class__.__name__)
    for measure in measures:
        notes = list(measure.recurse().notesAndRests)
        if len(notes) != 1 or not isinstance(notes[0], note.Note):
            fail('UNSUPPORTED_EVENT', measure=str(measure.number))
        n = notes[0]
        if n.offset != 0 or n.duration.quarterLength != 4 or n.duration.type != 'whole' or n.duration.dots:
            fail('UNSUPPORTED_RHYTHM', measure=str(measure.number))
        if n.tie or n.articulations or n.expressions or n.lyrics:
            fail('UNSUPPORTED_NOTE_ATTACHMENTS', measure=str(measure.number))
        events.append(n)
    return score, events, signatures[0].sharps


def layers(profile, score, events, fifths):
    """Derive every supported music pixel and connection from semantic events."""
    size = profile.get('size')
    if not isinstance(size, list) or len(size) != 2 or any(type(v) is not int for v in size):
        fail('INVALID_PAGE_SIZE')
    if min(size) < 200 or max(size) > 10000 or size[0]*size[1] > core.MAX_PIXELS:
        fail('INVALID_PAGE_SIZE')
    size = tuple(size)
    music_path, lyric_path = fonts()
    if font_hashes()[0] != MUSIC_FONT_SHA256:
        fail('UNVALIDATED_MUSIC_FONT_DESIGN')
    if profile.get('font_sha256') != font_hashes():
        fail('SOURCE_FONT_BINDING_MISMATCH')
    interline = _number(profile['interline'])
    if not 12 <= interline <= 40:
        fail('UNSUPPORTED_STAFF_SCALE')
    top = _number(profile['staff_top'])
    left, right = _point(profile['staff_span'])
    slots = profile['note_x']
    boundaries = profile['bar_x']
    if len(slots) != len(events) or len(boundaries) != len(events)+1:
        fail('EVENT_GEOMETRY_CARDINALITY_MISMATCH')
    slots = [_number(v) for v in slots]; boundaries = [_number(v) for v in boundaries]
    if slots != sorted(set(slots)) or boundaries != sorted(set(boundaries)):
        fail('NONUNIQUE_EVENT_GEOMETRY')
    if left < 10 or right >= size[0]-10 or top < 4*interline or top+8*interline >= size[1]:
        fail('STAFF_CLIPPING')
    if boundaries[0] <= left or boundaries[-1] != right:
        fail('INVALID_MEASURE_BOUNDARIES')
    for i, x in enumerate(slots):
        if not boundaries[i]+2*interline < x < boundaries[i+1]-2*interline:
            fail('FIXED_MEASURE_COLLISION', measure=i+1)
    staff = _mask(size); draw = ImageDraw.Draw(staff)
    for i in range(5):
        draw.line((left, top+i*interline, right, top+i*interline), fill=255, width=1)
    for x in boundaries:
        draw.line((x, top, x, top+4*interline), fill=255, width=1)
    music = _mask(size); records = []
    font_size = round(interline*4)
    music_font = _font(music_path, font_size)
    def add(ident, char, point, kind, **extra):
        nonlocal music
        active_font = music_font
        if kind in {'accidental', 'key-signature'}:
            box = music_font.getbbox(char, anchor='ls')
            active_font = _font(music_path, round(font_size*2.6*interline/(box[3]-box[1])))
        alpha, info = _glyph(size, active_font, char, point)
        if _overlap(alpha, music):
            fail('MUSIC_ALPHA_COLLISION', object=ident)
        if max(abs(v) for v in info['anchor_residual']) > .5:
            fail('NOTE_ANCHOR_ERROR', object=ident)
        music = _union(music, alpha)
        records.append({'object': ident, 'kind': kind, 'alpha_sha256': digest(alpha.tobytes()),
                        **info, **extra})
    # Unicode music glyphs are checked for presence by the font profile and
    # whole-page canonical comparison, never replaced with textual ASCII.
    clef_point = (left+interline, top+3*interline)
    _, calibration = _glyph((font_size*8, font_size*8), music_font, '\U0001d11e',
                              (font_size*4, font_size*4))
    semantic_anchor = [calibration['baseline'][0]+331*font_size/1000,
                       calibration['baseline'][1]-160*font_size/1000]
    clef_center = [calibration['raster_placement_anchor'][i]+clef_point[i]-semantic_anchor[i]
                   for i in (0,1)]
    add('clef', '\U0001d11e', clef_center, 'clef')
    for row in (1, 3):
        f = _font(music_path, round(interline*1.8))
        alpha, info = _glyph(size, f, '4', (boundaries[0]-interline, top+row*interline))
        music = _union(music, alpha)
    # Standard treble signature positions in diatonic steps above E4.
    if fifths < 0:
        fail('UNSUPPORTED_FLAT_SIGNATURE_ANCHOR')
    signature_steps = [8, 5, 9, 6, 3, 7, 4]
    signature_start = left+3*interline
    for index in range(abs(fifths)):
        x = signature_start+index*2*interline
        if x+interline >= boundaries[0]-2*interline:
            fail('KEY_SIGNATURE_FIXED_LAYOUT_COLLISION')
        add(f'key-{index}', '♯' if fifths > 0 else '♭',
            (x, top+4*interline-signature_steps[index]*interline/2), 'key-signature')
    from music21 import key
    signature = key.KeySignature(fifths)
    for index, (n, x) in enumerate(zip(events, slots)):
        # E4 is diatonic number 31, the bottom line in a treble staff.
        steps = n.pitch.diatonicNoteNum-31
        y = top+4*interline-steps*interline/2
        if y < 2*interline or y > size[1]-2*interline:
            fail('NOTE_CLIPPING', object=f'note-{index}')
        expected_acc = signature.accidentalByStep(n.pitch.step)
        alter = n.pitch.accidental.alter if n.pitch.accidental else 0
        key_alter = expected_acc.alter if expected_acc else 0
        if alter != key_alter:
            fail('UNSUPPORTED_EXPLICIT_ACCIDENTAL', object=f'note-{index}', measure=index+1)
        # A whole-note head has no stem/beam/flag. These are unsupported in
        # this profile rather than silently dropped from shorter durations.
        add(f'note-{index}', '\U0001d15d', (x, y), 'whole-note',
            measure=index+1, written_pitch=n.pitch.nameWithOctave,
            target_anchor=[x, y], relations=[])
        ledger_steps = range(10, steps+1, 2) if steps >= 10 else range(-2, steps-1, -2)
        for step in ledger_steps:
            yy = top+4*interline-step*interline/2
            ledger = _mask(size); ImageDraw.Draw(ledger).line(
                (x-interline, yy, x+interline, yy), fill=255, width=1)
            music = _union(music, ledger)
            records.append({'object': f'ledger-{index}-{step}', 'kind': 'ledger',
                            'relations': [f'note-{index}']})
    lyrics = _mask(size)
    rows = profile.get('lyrics', [])
    if not rows or len(rows) > 12:
        fail('UNSUPPORTED_LYRIC_ROWS')
    lyric_regions = []
    for index, row in enumerate(rows):
        text = row['text']
        if not isinstance(text, str) or len(text) > 300 or not re.fullmatch(r'[가-힣ㄱ-ㅎㅏ-ㅣ 0-9.,!?]+', text):
            fail('UNSUPPORTED_NATIVE_LYRIC_TEXT', object=f'lyrics-{index}')
        position = _point(row['xy']); font = _font(lyric_path, row['font_size'])
        if position[1] < top+6*interline:
            fail('LYRIC_STAFF_OVERLAP', object=f'lyrics-{index}', source_region=list(position))
        alpha = _mask(size); ImageDraw.Draw(alpha).text(position, text, font=font, fill=255)
        for extender in row.get('extenders', []):
            if len(extender) != 4:
                fail('INVALID_LYRIC_EXTENDER')
            x0, y0, x1, y1 = [_number(v) for v in extender]
            if x1 <= x0 or y1 != y0 or y0 < position[1] or y0 > position[1]+font.size*2:
                fail('INVALID_LYRIC_EXTENDER')
            ImageDraw.Draw(alpha).line((x0, y0, x1, y1), fill=255, width=1)
        box = alpha.getbbox()
        if box is None or min(box) <= 0 or box[2] >= size[0] or box[3] >= size[1]:
            fail('LYRIC_CLIPPING', object=f'lyrics-{index}')
        if _overlap(alpha, lyrics):
            fail('AMBIGUOUS_LYRIC_ROWS', source_region=box)
        lyrics = _union(lyrics, alpha)
        lyric_regions.append({'object': f'lyrics-{index}', 'source_region': list(box),
                              'ink_pixels': int(np.count_nonzero(np.asarray(alpha))),
                              'alpha_sha256': digest(alpha.tobytes())})
    if _overlap(music, lyrics) or _overlap(staff, lyrics):
        intersection = ImageChops.multiply(music, lyrics).getbbox()
        fail('MUSIC_LYRIC_COLLISION', source_region=intersection)
    return (staff, music, lyrics), records, lyric_regions


def _image_object(writer, alpha):
    w, h = alpha.size
    smask = DecodedStreamObject(); smask.set_data(alpha.tobytes())
    common = {'/Type': NameObject('/XObject'), '/Subtype': NameObject('/Image'),
              '/Width': NumberObject(w), '/Height': NumberObject(h),
              '/ColorSpace': NameObject('/DeviceGray'), '/BitsPerComponent': NumberObject(8),
              '/Interpolate': BooleanObject(False)}
    smask.update({NameObject(k): v for k,v in common.items()})
    image = DecodedStreamObject(); image.set_data(bytes(w*h))
    image.update({NameObject(k): v for k,v in common.items()})
    image[NameObject('/SMask')] = writer._add_object(smask.flate_encode())
    return writer._add_object(image.flate_encode())


def _commands(width, height):
    return ''.join(f'q {width:.12g} 0 0 {height:.12g} 0 0 cm /{role} Do Q\n'
                   for role in ('Staff', 'Music', 'Lyrics')).encode()


def source_pdf(profiles, xml_pages):
    """Create a self-describing controlled/native score; never used as OMR."""
    writer = PdfWriter(); payload = {'profile': PROFILE, 'pages': []}
    for profile, xml in zip(profiles, xml_pages, strict=True):
        score, events, fifths = _score(xml)
        alpha, _, _ = layers(profile, score, events, fifths)
        width, height = [v*72/core.PDF_DPI for v in profile['size']]
        page = writer.add_blank_page(width, height)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/XObject'): DictionaryObject({
            NameObject('/'+name): _image_object(writer, mask)
            for name, mask in zip(('Staff', 'Music', 'Lyrics'), alpha)})})
        content = DecodedStreamObject(); content.set_data(_commands(width, height))
        page[NameObject('/Contents')] = writer._add_object(content)
        payload['pages'].append({'layout': profile, 'musicxml': xml.decode()})
    stream = DecodedStreamObject(); stream.set_data(json.dumps(payload, ensure_ascii=False).encode())
    writer._root_object[NameObject('/CapomaticSource')] = writer._add_object(stream.flate_encode())
    out = io.BytesIO(); writer.write(out); return out.getvalue()


def _read_layers(page, size):
    # No arbitrary drawing commands, extra images, clipping, annotations or
    # inherited source layers can hide additional ink in this native profile.
    width, height = [v*72/core.PDF_DPI for v in size]
    if page.rotation or tuple(float(v) for v in page.mediabox) != (0, 0, width, height):
        fail('UNSUPPORTED_NATIVE_PAGE_TRANSFORM')
    if tuple(page.cropbox) != tuple(page.mediabox) or page.get('/Annots'):
        fail('UNSUPPORTED_NATIVE_PAGE_CONTENT')
    if page.get_contents().get_data() != _commands(width, height):
        fail('UNDECLARED_PDF_DRAWING_COMMANDS')
    resources = page['/Resources']
    if set(resources) != {'/XObject'} or set(resources['/XObject']) != {'/Staff', '/Music', '/Lyrics'}:
        fail('UNDECLARED_PDF_RESOURCE')
    result = []
    for name in ('Staff', 'Music', 'Lyrics'):
        image = resources['/XObject']['/'+name].get_object()
        allowed = {'/Type','/Subtype','/Width','/Height','/ColorSpace','/BitsPerComponent','/Interpolate','/SMask','/Filter','/Length'}
        if set(image)-allowed or getattr(image.get('/Interpolate'), 'value', True) is not False:
            fail('UNDECLARED_IMAGE_TRANSFORM', object=name)
        if image.get('/Subtype') != '/Image' or image.get('/ColorSpace') != '/DeviceGray' or image.get('/BitsPerComponent') != 8:
            fail('UNSUPPORTED_IMAGE_ENCODING', object=name)
        colour = _stream_bytes(image, size[0]*size[1])
        if (image['/Width'], image['/Height']) != tuple(size) or len(colour) != size[0]*size[1] or any(colour):
            fail('UNDECLARED_IMAGE_PIXELS', object=name)
        alpha = image['/SMask'].get_object()
        if set(alpha)-allowed or alpha.get('/SMask') is not None or getattr(alpha.get('/Interpolate'), 'value', True) is not False:
            fail('UNDECLARED_ALPHA_TRANSFORM', object=name)
        if (alpha.get('/Width'), alpha.get('/Height')) != tuple(size) or alpha.get('/BitsPerComponent') != 8 or alpha.get('/ColorSpace') != '/DeviceGray':
            fail('UNSUPPORTED_ALPHA_ENCODING', object=name)
        raw = _stream_bytes(alpha, size[0]*size[1])
        if len(raw) != size[0]*size[1]:
            fail('ALPHA_SIZE_MISMATCH', object=name)
        result.append(Image.frombytes('L', tuple(size), raw))
    return tuple(result)


@checked
def inspect(data):
    """Return native source payload only when the marker is actually present."""
    reader = PdfReader(io.BytesIO(data), strict=True)
    marker = reader.trailer['/Root'].get('/CapomaticSource')
    if marker is None:
        return None
    raw = _stream_bytes(marker.get_object(), MAX_PROFILE_BYTES)
    if len(raw) > MAX_PROFILE_BYTES:
        fail('NATIVE_PROFILE_TOO_LARGE')
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise core.ScoreError('Malformed native source profile') from exc
    if payload.get('profile') != PROFILE or len(payload.get('pages', [])) != len(reader.pages):
        fail('NATIVE_PROFILE_PAGE_MISMATCH')
    return reader, payload


@checked
def recognize(data):
    """Verify source vectors/layers and their actual Poppler-rendered pixels."""
    parsed = inspect(data)
    if parsed is None:
        return None
    reader, payload = parsed
    if len(reader.pages) > core.MAX_PAGES:
        fail('NATIVE_PAGE_LIMIT')
    metas = pdf_metadata(data)
    results = []; captured = []
    with tempfile.TemporaryDirectory(prefix='capomatic-native-') as tmp:
        home = Path(tmp); source = home/'source.pdf'; source.write_bytes(data)
        for index, (page, entry, meta) in enumerate(zip(reader.pages, payload['pages'], metas), 1):
            profile = entry['layout']; xml = entry['musicxml'].encode()
            score, events, fifths = _score(xml)
            predicted, objects, lyric_regions = layers(profile, score, events, fifths)
            actual = _read_layers(page, profile['size'])
            for name, expected, observed in zip(('staff', 'music', 'lyrics'), predicted, actual):
                if expected.tobytes() != observed.tobytes():
                    fail('SOURCE_LAYER_CANONICAL_MISMATCH', page=index, object=name)
            output = home/f'page-{index}'
            core._run([core._bin('CAPOMATIC_NATIVE_PDF_RASTERIZER', 'pdftocairo'), '-r', str(core.PDF_DPI),
                       '-f', str(index), '-l', str(index), '-cropbox', '-singlefile', '-png',
                       str(source), str(output)], 60, home, 'Native source raster verification')
            png = output.with_suffix('.png').read_bytes()
            with Image.open(io.BytesIO(png)) as raster:
                if raster.size != tuple(profile['size']) or raster.convert('RGB').tobytes() != _blend(actual).tobytes():
                    fail('SOURCE_PDF_RASTER_MISMATCH', page=index)
            evidence = {'native_profile_verified': True, 'geometry_ready': True,
                        'semantic_ready': True, 'lyric_layer_ready': True,
                        'issues': [], 'objects': objects, 'lyric_regions': lyric_regions,
                        'source_pixel_sha256': digest(_blend(actual).tobytes()),
                        'ownership_basis': 'complete canonical semantic glyph alpha + actual PDF objects + exact source raster',
                        'profile': PROFILE, 'rasterizer': 'pdftocairo',
                        'source_pixel_grid': 'native 300 dpi; no image resizing'}
            metadata = {**meta, 'dpi': core.PDF_DPI, 'raster_size': profile['size'],
                        'native_profile': PROFILE, 'png_sha256': digest(png)}
            captured.append(SourcePage(png, b'', json.dumps(metadata).encode(), json.dumps(evidence).encode()))
            results.append(core.Result(b'', None, xml, {}, {'input': {'source': PROFILE},
                'accuracy': 'provided_native_semantics_not_omr_accuracy', 'review_required': True}))
    bundle = SourceLayoutBundle(data, '.pdf', tuple(captured))
    if len(results) == 1:
        from dataclasses import replace
        return replace(results[0], source_layout=bundle)
    return core.Result(b'', None, None, {}, source_layout=bundle, pages=tuple(results))


@checked
def compose(data, semitones):
    """Plan all pages, verify ownership/collisions, then compose a separate canvas."""
    parsed = inspect(data)
    if parsed is None:
        fail('NATIVE_OWNERSHIP_PROFILE_REQUIRED')
    reader, payload = parsed
    outputs = []; reports = []; target_xml = []
    for index, (page, entry) in enumerate(zip(reader.pages, payload['pages']), 1):
        profile = entry['layout']; source, source_events, fifths = _score(entry['musicxml'].encode())
        original, source_objects, regions = layers(profile, source, source_events, fifths)
        actual = _read_layers(page, profile['size'])
        if any(a.tobytes() != b.tobytes() for a,b in zip(original, actual)):
            fail('SOURCE_LAYER_CHANGED', page=index)
        target = copy.deepcopy(source); summary = transpose_score(target, semitones, 'key')
        guard = music_guard.validate(source, target, semitones, 'key', summary)
        if not guard.ok:
            raise core.ScoreError('V3 semantic integrity failed', 422, guard.to_dict())
        from music21 import key
        target_events = list(target.recurse().notes)
        target_fifths = target.recurse().getElementsByClass(key.KeySignature).first().sharps
        try:
            planned, objects, _ = layers(profile, target, target_events, target_fifths)
        except core.ScoreError as exc:
            exc.report.setdefault('page', index)
            raise
        staff, old_music, lyrics = actual
        new_music = planned[1]
        if _overlap(new_music, lyrics):
            fail('TARGET_MUSIC_LYRIC_COLLISION', page=index,
                 source_region=ImageChops.multiply(new_music, lyrics).getbbox())
        source_raster = _blend(actual)
        source_array = np.asarray(source_raster)
        # Only the old music support is replaced. Where it crossed staff ink,
        # the exact verified staff model is reconstructed and reported as such.
        canvas = source_raster.copy()
        owned = np.asarray(old_music) > 0
        rebuilt = np.asarray(_blend((staff, lyrics)))
        array = np.array(canvas); array[owned] = rebuilt[owned]
        canvas = Image.fromarray(array)
        canvas.paste((0, 0, 0), (0, 0), new_music)
        out_array = np.asarray(canvas); lyric_support = np.asarray(lyrics) > 0
        if not np.array_equal(out_array[lyric_support], source_array[lyric_support]):
            fail('LYRIC_PIXEL_PRESERVATION_FAILED', page=index)
        edits = owned | (np.asarray(new_music) > 0)
        if not np.array_equal(out_array[~edits], source_array[~edits]):
            fail('UNRELATED_SOURCE_PIXEL_CHANGED', page=index)
        expected = _blend((staff, new_music, lyrics))
        if expected.tobytes() != canvas.tobytes():
            fail('RESIDUAL_OR_DOUBLE_MUSIC_INK', page=index)
        # Independent observation of the actual alpha masks, not only planned anchors.
        residuals = [o['anchor_residual'] for o in objects if o['kind']=='whole-note']
        report = {'page': index, 'semantic_ready': True, 'geometry_ready': True,
                  'lyric_layer_ready': True, 'render_ready': True,
                  'render_path': 'source_identity' if semitones == 0 else 'native_geometry_transposition',
                  'semitones': semitones, 'integrity': guard.to_dict(),
                  'source_ink_safety': {'status': 'VERIFIED_NATIVE_PROFILE', 'objects': source_objects,
                      'owned_pixel_count': int(np.count_nonzero(owned)),
                      'reconstructed_staff_pixels': int(np.count_nonzero(owned & (np.asarray(staff)>0))),
                      'reconstructed_background_pixels': int(np.count_nonzero(owned & (np.asarray(staff)==0))),
                      'preserved_unrelated_source_pixels': int(np.count_nonzero(~edits))},
                  'lyrics': {'regions': regions, 'pixel_difference': 0,
                             'preserved_ink_pixels': int(np.count_nonzero(lyric_support)),
                             'ocr_replacement': False},
                  'fixed_anchor_displacement_px': 0, 'target_objects': objects,
                  'note_anchor_max_error_xy_px': [max(abs(r[i]) for r in residuals) for i in (0,1)],
                  'unexplained_alpha_collisions': 0, 'duplicate_music_pixels': 0,
                  'clipping': 0, 'source_raster_sha256': digest(source_raster.tobytes()),
                  'output_raster_sha256': digest(canvas.tobytes()),
                  'recognition_accuracy': 'UNVERIFIED; native semantic input, not OMR recognition'}
        outputs.append(canvas); reports.append(report)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'target.musicxml'; target.write('musicxml', fp=str(path))
            serialized = path.read_bytes()
            from music21 import converter
            roundtrip = converter.parseData(serialized.decode(), format='musicxml')
            serialized_guard = music_guard.validate(source, roundtrip, semitones, 'key', summary)
            if not serialized_guard.ok:
                fail('SERIALIZED_V3_INTEGRITY_FAILED', page=index)
            report['serialized_integrity'] = serialized_guard.to_dict()
            target_xml.append(serialized)
    return outputs, reports, target_xml


def lossless_pdf(images, metadata):
    """Embed unscaled RGB pixels with Flate compression; preserve page boxes."""
    writer = PdfWriter()
    for image, meta in zip(images, metadata, strict=True):
        if meta['rotation'] != 0 or tuple(meta['boxes']['cropbox']) != tuple(meta['boxes']['mediabox']):
            fail('UNSUPPORTED_OUTPUT_PAGE_TRANSFORM')
        x0,y0,x1,y1 = meta['boxes']['mediabox']
        if x0 != 0 or y0 != 0:
            fail('UNSUPPORTED_OUTPUT_PAGE_ORIGIN')
        page = writer.add_blank_page(x1, y1)
        for name in ('mediabox', 'cropbox', 'trimbox', 'bleedbox', 'artbox'):
            setattr(page, name, RectangleObject(meta['boxes'][name]))
        raw = DecodedStreamObject(); raw.set_data(image.convert('RGB').tobytes())
        raw.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),
                    NameObject('/Width'):NumberObject(image.width), NameObject('/Height'):NumberObject(image.height),
                    NameObject('/BitsPerComponent'):NumberObject(8),NameObject('/ColorSpace'):NameObject('/DeviceRGB'),
                    NameObject('/Interpolate'):BooleanObject(False)})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/XObject'):DictionaryObject({NameObject('/PageRaster'):writer._add_object(raw.flate_encode())})})
        content = DecodedStreamObject();content.set_data(f'q {x1:.12g} 0 0 {y1:.12g} 0 0 cm /PageRaster Do Q\n'.encode())
        page[NameObject('/Contents')] = writer._add_object(content)
    out=io.BytesIO();writer.write(out);return out.getvalue()
