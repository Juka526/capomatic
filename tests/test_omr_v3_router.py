"""V3 score routes: feature flag, auth, rate limit and response packaging (OMR mocked)."""
import io
import json
import zipfile
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.omr_v3 import router as omr
from backend.omr_v3.core import Result

PDF = ('x.pdf', b'%PDF-1.4\n', 'application/pdf')
RESULT = Result(b'%PDF-1.4\n', b'<score-partwise/>', b'<score-partwise/>', {'total': 10.0},
                {'warnings': [{'type': 'bar_length'}], 'warning': 'check'})


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(omr.router)
    monkeypatch.setenv('CAPOMATIC_ENABLE_OMR_V3', '1')
    monkeypatch.setenv('CAPOMATIC_OMR_REQUIRE_AUTH', '0')
    omr.rate_limiter.reset()
    yield TestClient(app)
    omr.rate_limiter.reset()


def test_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv('CAPOMATIC_ENABLE_OMR_V3')
    assert client.post('/api/v3/score/transpose.pdf', files={'file': PDF}).status_code == 404


def test_login_required_by_default(client, monkeypatch):
    monkeypatch.delenv('CAPOMATIC_OMR_REQUIRE_AUTH')
    r = client.post('/api/v3/score/transpose.pdf', files={'file': PDF})
    assert r.status_code == 401


def test_valid_token_is_accepted(client, monkeypatch):
    monkeypatch.delenv('CAPOMATIC_OMR_REQUIRE_AUTH')
    with patch('backend.auth.auth0.verify_token', AsyncMock(return_value={'sub': 'auth0|u1'})), \
            patch.object(omr, '_execute', return_value=RESULT):
        r = client.post('/api/v3/score/transpose.pdf', files={'file': PDF}, headers={'Authorization': 'Bearer t'})
    assert r.status_code == 200 and r.content.startswith(b'%PDF')
    assert r.headers['X-OMR-Accuracy'] == 'unverified' and r.headers['Cache-Control'] == 'no-store'


@pytest.mark.parametrize('data', [{'semitones': '12'}, {'semitones': '1', 'mode': 'capo'},
                                  {'semitones': '-8', 'mode': 'capo'}, {'mode': 'bogus'}])
def test_invalid_shift_or_mode(client, data):
    assert client.post('/api/v3/score/transpose.pdf', files={'file': PDF}, data=data).status_code == 422


def test_invalid_file_is_rejected_before_rate_limit(client, monkeypatch):
    monkeypatch.setenv('CAPOMATIC_OMR_RATE_LIMIT', '1/3600')
    for _ in range(3):
        r = client.post('/api/v3/score/transpose.pdf', files={'file': ('x.pdf', b'nope', 'application/pdf')})
        assert r.status_code == 422


def test_rate_limit(client, monkeypatch):
    monkeypatch.setenv('CAPOMATIC_OMR_RATE_LIMIT', '2/3600')
    with patch.object(omr, '_execute', return_value=RESULT):
        codes = [client.post('/api/v3/score/transpose.pdf', files={'file': PDF}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_busy_worker_returns_429(client):
    assert omr._slot.acquire(blocking=False)
    try:
        with patch.object(omr, 'process', return_value=RESULT):
            r = client.post('/api/v3/score/transpose.pdf', files={'file': PDF})
    finally:
        omr._slot.release()
    assert r.status_code == 429 and 'Retry-After' in r.headers


def test_zip_contains_pdf_musicxml_and_report(client):
    with patch.object(omr, '_execute', return_value=RESULT) as run:
        r = client.post('/api/v3/score/transpose.zip', files={'file': PDF}, data={'semitones': '-2', 'mode': 'capo'})
    assert r.status_code == 200
    assert run.call_args.args[2:] == (-2, 'capo')
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert set(z.namelist()) == {'transposed.pdf', 'transposed.musicxml', 'recognized.musicxml', 'conversion-report.json'}
        report = json.loads(z.read('conversion-report.json'))
    assert report['mode'] == 'capo' and report['semitones'] == -2 and report['warnings']


def test_unexpected_error_is_generic_500(client):
    with patch.object(omr, '_execute', side_effect=RuntimeError('/tmp/secret/path')):
        r = client.post('/api/v3/score/transpose.pdf', files={'file': PDF})
    assert r.status_code == 500 and 'secret' not in r.text


def test_main_app_registers_router_and_keeps_v1_routes():
    from backend.api.main import app

    paths = {route.path for route in app.routes}
    assert {'/detect', '/render', '/overlay', '/health'} <= paths
    assert {'/api/v3/score/transpose.pdf', '/api/v3/score/transpose.zip'} <= paths
