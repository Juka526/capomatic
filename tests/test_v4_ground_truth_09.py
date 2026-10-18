"""Synthetic owner observations only; never real score annotations."""

import copy
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest
from PIL import Image
from scripts.research.gt08_review import COORDINATES
from scripts.research.gt09_owner_review import (
    ReviewStore,
    validate_case,
    encoded,
    sha,
    handler,
    ThreadingHTTPServer,
)


@pytest.fixture
def store(tmp_path):
    p = tmp_path / 'packet'
    p.mkdir()
    (p / 'instructions.txt').write_text('Synthetic fixture only')
    cases = []
    for i in range(5):
        ident = f'{i:020x}'
        image = p / (ident + '.png')
        Image.new('RGB', (4, 3), (200, 200, 200)).save(image)
        cases.append(
            dict(case_id=ident, image=image.name, sha256=sha(image.read_bytes()), width=4, height=3)
        )
    manifest = dict(
        version='gt08-text-review/1',
        coordinate_system=COORDINATES,
        cases=cases,
        instructions_sha256=sha((p / 'instructions.txt').read_bytes()),
    )
    (p / 'packet.json').write_bytes(encoded(manifest))
    return ReviewStore(p, tmp_path / 'owner', sha((p / 'packet.json').read_bytes()))


def case_value(case, label='UNKNOWN', finalized=False):
    return dict(
        case_id=case['case_id'],
        image_sha256=case['sha256'],
        width=4,
        height=3,
        runs=[[y, 0, 4, label] for y in range(3)],
        finalized=finalized,
        uncertainty_acknowledged=finalized,
    )


def filled(store):
    state = store.empty()
    state['cases'] = {k: case_value(c, finalized=True) for k, c in store.cases.items()}
    return state


def test_no_automatic_labels(store):
    assert store.load()['cases'] == {}
    assert not (store.output / 'owner-review-exports').exists()


def test_save_resume_and_source_unchanged(store):
    before = {p.name: p.read_bytes() for p in store.packet.iterdir()}
    state = store.empty()
    key, c = next(iter(store.cases.items()))
    state['cases'][key] = case_value(c, 'UNREVIEWED')
    saved = store.save(state)
    assert saved['revision'] == 1
    other = ReviewStore(store.packet, store.output, store.packet_sha)
    assert other.load() == saved
    assert before == {p.name: p.read_bytes() for p in store.packet.iterdir()}


def test_export_reproducible_owner_only(store):
    store.save(filled(store))
    a = store.export()
    assert store.export() == a
    d = json.loads(a)
    assert d['review_type'] == 'OWNER_REVIEW'
    assert d['evidence_status'] == 'NOT_INDEPENDENT_GROUND_TRUTH'
    assert d['composition_authorized'] is False
    assert len(d['cases']) == 5
    assert all(c['UNKNOWN'] == 12 for c in d['coverage'].values())
    assert len(list((store.output / 'owner-review-exports').iterdir())) == 1


@pytest.mark.parametrize(
    'field,value',
    [('width', 5), ('height', 4), ('case_id', 'bad'), ('image_sha256', '0' * 64), ('width', 4.0)],
)
def test_binding_rejected(store, field, value):
    c = next(iter(store.cases.values()))
    v = case_value(c)
    v[field] = value
    with pytest.raises(ValueError):
        validate_case(v, c)


@pytest.mark.parametrize(
    'runs',
    [
        [[0, 0, 4, 'TEXT']],
        [[0, 0, 4, 'TEXT'], [0, 3, 4, 'UNKNOWN']],
        [[0, -1, 4, 'TEXT']],
        [[0, 0, 5, 'TEXT']],
        [[0, 0.0, 4, 'TEXT']],
        [[0, False, 4, 'TEXT']],
        [[0, 0, 4, 'AI_LABEL']],
        [[0, 0, 2, 'TEXT'], [0, 2, 4, 'TEXT'], [1, 0, 4, 'TEXT'], [2, 0, 4, 'TEXT']],
    ],
)
def test_invalid_rle_rejected(store, runs):
    c = next(iter(store.cases.values()))
    v = case_value(c)
    v['runs'] = runs
    with pytest.raises(ValueError):
        validate_case(v, c)


def test_finalization_requires_explicit_uncertainty_ack_and_full_coverage(store):
    c = next(iter(store.cases.values()))
    v = case_value(c, 'UNREVIEWED', True)
    with pytest.raises(ValueError):
        validate_case(v, c)
    v = case_value(c, finalized=True)
    v['uncertainty_acknowledged'] = False
    with pytest.raises(ValueError):
        validate_case(v, c)
    assert validate_case(case_value(c, finalized=True), c)['UNKNOWN'] == 12


def test_missing_or_unfinalized_case_blocks_export(store):
    state = filled(store)
    state['cases'].pop(next(iter(state['cases'])))
    store.save(state)
    with pytest.raises(ValueError):
        store.export()
    state = store.load()
    key = next(iter(store.cases))
    state['cases'][key] = case_value(store.cases[key])
    store.save(state)
    with pytest.raises(ValueError):
        store.export()


def test_stale_tab_fails_without_overwriting(store):
    state = store.empty()
    store.save(state)
    before = store.state_path.read_bytes()
    with pytest.raises(ValueError):
        store.save(state)
    assert store.state_path.read_bytes() == before


def test_source_hash_change_blocks_save_and_export(store):
    store.save(filled(store))
    c = next(iter(store.cases.values()))
    (store.packet / c['image']).write_bytes(b'changed')
    with pytest.raises(ValueError):
        store.export()
    with pytest.raises(ValueError):
        store.save(store.empty())


def test_different_packet_and_gt08_storage_blocked(store, tmp_path):
    with pytest.raises(ValueError):
        ReviewStore(store.packet, tmp_path / 'wrong', '0' * 64)
    with pytest.raises(ValueError):
        ReviewStore(store.packet, tmp_path / 'gt08-output' / 'owner', store.packet_sha)


def test_live_http_routes_and_csrf_on_synthetic_packet(store):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(store, 'test-token'))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        assert b'OWNER_REVIEW' in urlopen(base).read()
        packet = json.load(urlopen(base + '/api/packet'))
        c = packet['cases'][0]
        assert (
            urlopen(base + '/case/' + c['case_id']).read()
            == (store.packet / c['image']).read_bytes()
        )
        with pytest.raises(HTTPError) as exc:
            urlopen(Request(base + '/api/state', data=encoded(store.empty()), method='POST'))
        assert exc.value.code == 403
        req = Request(
            base + '/api/state',
            data=encoded(filled(store)),
            headers={'X-Review-Token': 'test-token', 'Content-Type': 'application/json'},
            method='POST',
        )
        assert json.load(urlopen(req))['revision'] == 1
        req = Request(
            base + '/api/export',
            data=b'{}',
            headers={'X-Review-Token': 'test-token'},
            method='POST',
        )
        assert json.load(urlopen(req))['composition_authorized'] is False
        with pytest.raises(HTTPError):
            urlopen(base + '/../owner-state.json')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_interrupted_export_does_not_leave_partial_final_file(store, monkeypatch):
    from scripts.research import gt09_owner_review as tool

    store.save(filled(store))
    link = tool.os.link

    def interrupted(*args):
        raise OSError('synthetic publication failure')

    monkeypatch.setattr(tool.os, 'link', interrupted)
    with pytest.raises(OSError):
        store.export()
    assert not list((store.output / 'owner-review-exports').iterdir())
    monkeypatch.setattr(tool.os, 'link', link)
    assert store.export() == store.export()
