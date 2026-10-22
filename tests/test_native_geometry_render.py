"""Real native-profile source ownership and composition controls.

These tests do not measure ordinary OMR recognition accuracy.
"""
import copy
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
import pytest
from fastapi.testclient import TestClient
from music21 import converter

from backend.api import score as api
from backend.api.main import app, _detection_cache, _cache_get
from backend.omr_v3 import core, native_pdf as native, router as v3
from scripts.controlled_native_score import make_fixture


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('CAPOMATIC_OMR_REQUIRE_AUTH', '0')
    monkeypatch.setenv('CAPOMATIC_OMR_RATE_LIMIT', '1000/3600')
    monkeypatch.setenv('CAPOMATIC_ENABLE_SCORE_API', '1')
    _detection_cache.clear(); v3.rate_limiter.reset()
    yield TestClient(app)
    _detection_cache.clear(); v3.rate_limiter.reset()


@pytest.fixture
def source():
    return make_fixture()[0]


def payload(data, change):
    reader = PdfReader(io.BytesIO(data)); writer = PdfWriter(clone_from=reader)
    obj = writer._root_object['/CapomaticSource'].get_object()
    parsed = json.loads(obj.get_data()); change(parsed)
    stream = DecodedStreamObject(); stream.set_data(json.dumps(parsed, ensure_ascii=False).encode())
    writer._root_object[NameObject('/CapomaticSource')] = writer._add_object(stream.flate_encode())
    out=io.BytesIO();writer.write(out);return out.getvalue()


@pytest.mark.parametrize('fifths,shift,expected', [
    (0, -1, ['B4', 'D#5', 'G#4', 'E4']),
    (5, 1, ['C5', 'E5', 'A4', 'F4']),
    (0, 0, ['C5', 'E5', 'A4', 'F4']),
])
def test_complete_source_to_pdf_png_and_semantic_guard(fifths, shift, expected, monkeypatch, tmp_path):
    def forbidden(*a, **kw):
        raise AssertionError('MuseScore must not run')
    monkeypatch.setattr(core, 'render_pdf', forbidden)
    data, profile, xml = make_fixture(fifths)
    result = native.recognize(data)
    snapshot = result.source_layout.pages[0].png
    images, reports, targets = native.compose(data, shift)
    output = images[0]; report=reports[0]
    original = Image.open(io.BytesIO(snapshot)).convert('RGB')
    _, source_payload=native.inspect(data)
    alpha=native._read_layers(PdfReader(io.BytesIO(data)).pages[0], profile['size'])
    lyric_support=np.asarray(alpha[2])>0
    assert np.array_equal(np.asarray(original)[lyric_support], np.asarray(output)[lyric_support])
    assert report['lyrics']['pixel_difference']==0
    assert len(report['lyrics']['regions'])==2
    assert report['fixed_anchor_displacement_px']==0
    assert all(v<=.5 for v in report['note_anchor_max_error_xy_px'])
    assert report['integrity']['ok'] and report['serialized_integrity']['ok']
    assert [n.pitch.nameWithOctave for n in converter.parseData(targets[0].decode(),format='musicxml').recurse().notes]==expected
    if shift:
        assert output.tobytes()!=original.tobytes()
    else:
        assert output.tobytes()==original.tobytes()
    pdf=native.lossless_pdf(images,[p.metadata for p in result.source_layout.pages])
    embedded=PdfReader(io.BytesIO(pdf)).pages[0]['/Resources']['/XObject']['/PageRaster'].get_object()
    assert embedded.get_data()==output.convert('RGB').tobytes()
    assert native.pdf_metadata(pdf)==native.pdf_metadata(data)
    path=tmp_path/'output.pdf';path.write_bytes(pdf)
    core._run(['pdftocairo','-r','300','-singlefile','-png',str(path),str(tmp_path/'actual')],30,tmp_path,'PDF pixels')
    assert Image.open(tmp_path/'actual.png').convert('RGB').tobytes()==output.convert('RGB').tobytes()
    assert result.source_layout.source==data and result.source_layout.pages[0].png==snapshot


def test_actual_notehead_y_and_old_music_removal(source):
    images,reports,_=native.compose(source,-1)
    heads=[o for o in reports[0]['target_objects'] if o['kind']=='whole-note']
    # Independently specified treble positions for B4, D#5, G#4 and E4.
    assert [o['target_anchor'][1] for o in heads]==[228,204,252,276]
    assert [o['target_anchor'][0] for o in heads]==[550,825,1100,1375]
    reader,profile=native.inspect(source)
    old=native._read_layers(reader.pages[0],profile['pages'][0]['layout']['size'])
    from music21 import key
    score, events, fifths=native._score(profile['pages'][0]['musicxml'].encode())
    from backend.omr_v3.transpose import transpose_score
    transpose_score(score,-1)
    target,_,_=native.layers(profile['pages'][0]['layout'],score,list(score.recurse().notes),5)
    removed=(np.asarray(old[1])>0)&(np.asarray(target[1])==0)&(np.asarray(old[0])==0)
    assert np.count_nonzero(removed)>0
    assert np.all(np.asarray(images[0])[removed]==255)
    assert reports[0]['source_ink_safety']['reconstructed_staff_pixels']>0


def test_cached_http_png_and_zip_are_nonzero_outputs(client, source, monkeypatch):
    def no_omr(*a,**kw): raise AssertionError('Native profile must verify its own source objects')
    monkeypatch.setattr(core,'process',no_omr)
    detection=client.post('/detect',files={'image':('controlled.pdf',source)})
    assert detection.status_code==200
    details=detection.json(); ident=details['detection_id']
    assert details['semantic_ready'] and details['geometry_ready'] and details['lyric_layer_ready']
    assert not details['render_ready']  # target has not been planned
    before=_cache_get(ident)['score'].source_layout
    response=client.post('/render',data={'detection_id':ident,'semitones':-1,'output_format':'png'})
    assert response.status_code==200 and response.headers['x-capomatic-identity']=='false'
    assert Image.open(io.BytesIO(response.content)).size==(1600,700)
    zip_response=client.post('/render',data={'detection_id':ident,'semitones':-1,'output_format':'zip'})
    assert zip_response.status_code==200
    assert _cache_get(ident)['score'].source_layout==before
    zero=client.post('/render',data={'detection_id':ident,'semitones':0,'output_format':'png'})
    assert zero.status_code==200 and zero.headers['x-capomatic-identity']=='true'
    assert Image.open(io.BytesIO(zero.content)).tobytes()==Image.open(io.BytesIO(before.pages[0].png)).tobytes()


@pytest.mark.parametrize('alter', ['pitch','unknown-layer','content'])
def test_forged_provenance_is_not_edit_authority(source, alter):
    if alter=='pitch':
        forged=payload(source,lambda p:p['pages'][0].__setitem__('musicxml',p['pages'][0]['musicxml'].replace('<step>C</step>','<step>D</step>')))
    else:
        reader=PdfReader(io.BytesIO(source));writer=PdfWriter(clone_from=reader)
        page=writer.pages[0]
        if alter=='unknown-layer':
            page['/Resources']['/XObject'][NameObject('/Unknown')]=page['/Resources']['/XObject']['/Lyrics']
        else:
            stream=DecodedStreamObject();stream.set_data(page.get_contents().get_data()+b'0 0 10 10 re f\n')
            page[NameObject('/Contents')]=writer._add_object(stream)
        out=io.BytesIO();writer.write(out);forged=out.getvalue()
    with pytest.raises(core.ScoreError):native.recognize(forged)


def test_korean_ink_touching_low_note_is_rejected():
    data,profile,xml=make_fixture()
    score=converter.parseData(xml.decode(),format='musicxml')
    score.recurse().notes.first().pitch.nameWithOctave='C3'
    xml=score.write('musicxml').read_bytes()
    with pytest.raises(core.ScoreError,match='MUSIC_LYRIC_COLLISION'):
        native.source_pdf([profile],[xml])


def test_unknown_stem_and_rhythm_never_omitted():
    _,profile,xml=make_fixture()
    score=converter.parseData(xml.decode(),format='musicxml')
    score.recurse().notes.first().quarterLength=1
    with pytest.raises(core.ScoreError,match='UNSUPPORTED'):
        native.source_pdf([profile],[score.write('musicxml').read_bytes()])


def test_supported_source_cannot_silently_render_unsupported_flat_signature(client,source):
    d=client.post('/detect',files={'image':('controlled.pdf',source)}).json()
    r=client.post('/render',data={'detection_id':d['detection_id'],'semitones':1})
    assert r.status_code==422
    assert 'UNSUPPORTED_FLAT_SIGNATURE_ANCHOR' in r.text


def test_multpage_atomic_failure_and_complete_pdf(client):
    _,profile,xml=make_fixture()
    bad=copy.deepcopy(profile);bad['bar_x']=[250,695,970,1245,1520]
    source=native.source_pdf([profile,bad],[xml,xml])
    d=client.post('/detect',files={'image':('multi.pdf',source)})
    assert d.status_code==200
    ident=d.json()['detection_id']
    rejected=client.post('/render',data={'detection_id':ident,'semitones':-1,'output_format':'pdf'})
    assert rejected.status_code==422 and not rejected.content.startswith(b'%PDF')
    assert 'KEY_SIGNATURE_FIXED_LAYOUT_COLLISION' in rejected.text
    good=native.source_pdf([profile,profile],[xml,xml]);result=native.recognize(good)
    images,reports,_=native.compose(good,-1)
    pdf=native.lossless_pdf(images,[p.metadata for p in result.source_layout.pages])
    assert len(PdfReader(io.BytesIO(pdf)).pages)==2


def test_identity_of_ordinary_pdf_does_not_claim_transposition(client,tmp_path,monkeypatch):
    writer=PdfWriter();writer.add_blank_page(300,400);out=io.BytesIO();writer.write(out);data=out.getvalue()
    from backend.omr_v3.source_layout import SourceLayoutBundle
    result=core.Result(b'',None,None,{},source_layout=SourceLayoutBundle(data,'.pdf',(None,)))
    monkeypatch.setattr(api,'recognize',lambda *a:result)
    d=client.post('/detect',files={'image':('ordinary.pdf',data)}).json()
    r=client.post('/render',data={'detection_id':d['detection_id'],'semitones':0})
    assert r.status_code==200 and r.content==data and r.headers['x-capomatic-identity']=='true'
    assert client.post('/render',data={'detection_id':d['detection_id'],'semitones':1}).status_code==422


@pytest.mark.parametrize('role', ['Music','Lyrics'])
def test_single_antialias_pixel_outside_declared_glyph_is_not_erased(source,role):
    reader=PdfReader(io.BytesIO(source));writer=PdfWriter(clone_from=reader)
    image=writer.pages[0]['/Resources']['/XObject']['/'+role].get_object()
    old=image['/SMask'].get_object();raw=bytearray(old.get_data());raw[25*1600+25]=1
    alpha=DecodedStreamObject();alpha.update({k:v for k,v in old.items() if k not in ['/Filter','/Length']})
    alpha.set_data(bytes(raw));image[NameObject('/SMask')]=writer._add_object(alpha)
    out=io.BytesIO();writer.write(out)
    with pytest.raises(core.ScoreError,match='SOURCE_LAYER_CANONICAL_MISMATCH'):
        native.recognize(out.getvalue())


def test_native_cache_owner_and_expiration(client,source):
    import time
    d=client.post('/detect',files={'image':('controlled.pdf',source)}).json()
    ident=d['detection_id']; cached=_cache_get(ident);cached['owner']='somebody-else'
    assert client.post('/render',data={'detection_id':ident,'semitones':-1}).status_code==404
    cached['expires_at']=time.monotonic()-1
    assert client.post('/render',data={'detection_id':ident,'semitones':-1}).status_code==404
    assert ident not in _detection_cache


def test_invalid_native_claim_does_not_fall_back_to_identity(client,source):
    broken=payload(source,lambda p:p['pages'][0].__setitem__('musicxml','<invalid/>'))
    detection=client.post('/detect',files={'image':('broken.pdf',broken)})
    assert detection.status_code==422
    ident=detection.json()['detail']['detection_id']
    assert client.post('/render',data={'detection_id':ident,'semitones':0}).status_code==422
