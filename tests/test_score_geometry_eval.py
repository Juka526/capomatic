"""HTTP success for an identity must never count as real transposition."""
import json
import sys

import httpx

from scripts import score_geometry_eval


def test_identity_and_refusal_counts_are_separate(tmp_path, monkeypatch):
    files = []
    for number in range(5):
        path = tmp_path / f'{number}.pdf'
        path.write_bytes(b'%PDF-test-'+str(number).encode())
        files.append(path)
    calls = []
    class Client:
        def __init__(self, **kwargs):
            self.source = None
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def get(self, path):
            return httpx.Response(200, request=httpx.Request('GET', 'http://test/health'))
        def post(self, path, **kwargs):
            calls.append((path, kwargs))
            if path == '/detect':
                self.source = kwargs['files']['image'][1]
                return httpx.Response(200, json={'detection_id': 'id'})
            if kwargs['data']['semitones'] == 0:
                return httpx.Response(200, content=self.source,
                                      headers={'X-Capomatic-Identity': 'true'})
            return httpx.Response(422, json={'detail': {'report': {'render_ready': False}}})
    monkeypatch.setattr(httpx, 'Client', Client)
    output = tmp_path/'out'
    monkeypatch.setattr(sys, 'argv', ['score_geometry_eval', 'http://test',
                                    *map(str, files), '--out', str(output)])
    score_geometry_eval.main()
    report = json.loads((output/'evaluation.json').read_text())
    assert len(calls) == 30  # Five detect, fifteen PDF, ten PNG requests.
    assert len(report['rows']) == 15
    assert report['identity_http_200_count'] == 5
    assert report['nonzero_http_200_count'] == report['contract_pass_count'] == 0
    assert report['intended_422_count'] == 10
