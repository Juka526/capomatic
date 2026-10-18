"""Persisted-state extraction cannot authorize ownership or invent missing masks."""

import io
import zipfile

import pytest
from PIL import Image

from backend.omr_v4.ink import pixels_from_runs
from backend.omr_v4.source_ink import PINNED_BUILD
from backend.omr_v4.v3_evidence import extract_evidence, reconstruct_no_staff, sha
from omr_v4_fixtures import sheet_xml


def fixture(tmp_path, *, staff=True, binary=True, dimensions=(400, 300)):
    source = tmp_path / 'source.png'
    Image.new('RGB', dimensions, 'white').save(source)
    xml = sheet_xml().replace('<line>', '<line glyph="900" thickness="1">')
    glyph = '<glyph id="900" left="20" top="80"><run-table orientation="HORIZONTAL" width="3" height="1"><runs>3</runs></run-table></glyph>'
    xml = xml.replace('</sheet>', f'<glyph-index>{glyph if staff else ""}</glyph-index></sheet>')
    omr = tmp_path / 'recognized.omr'
    with zipfile.ZipFile(omr, 'w') as z:
        z.writestr('book.xml', f'<book software-build="{PINNED_BUILD}"/>')
        z.writestr('sheet#1/sheet#1.xml', xml)
        if binary:
            image = Image.new('L', (400, 300), 255)
            for x in range(20, 23):
                image.putpixel((x, 80), 0)
            image.putpixel((23, 80), 0)
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            z.writestr('sheet#1/BINARY.png', buffer.getvalue())
    return source, omr


def extract(source, omr, out, **kw):
    return extract_evidence(
        source,
        omr,
        out,
        expected_source_sha=kw.get('source_sha', sha(source.read_bytes())),
        expected_omr_sha=sha(omr.read_bytes()),
    )


def test_exact_extraction_staff_decode_and_determinism(tmp_path):
    source, omr = fixture(tmp_path)
    before = source.read_bytes()
    a, b = tmp_path / 'a', tmp_path / 'b'
    manifest = extract(source, omr, a)
    extract(source, omr, b)
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {
        p.name: p.read_bytes() for p in b.iterdir()
    }
    assert source.read_bytes() == before == (a / 'source.png').read_bytes()
    with zipfile.ZipFile(omr) as z:
        assert z.read('sheet#1/BINARY.png') == (a / 'binary.png').read_bytes()
    import json

    staff = json.loads((a / 'staff-evidence.json').read_text())
    assert pixels_from_runs(staff[0]['attributed_runs']) == {(20, 80), (21, 80), (22, 80)}
    with Image.open(a / 'no-staff.png') as im:
        assert im.getpixel((20, 80)) == 255
        assert im.getpixel((23, 80)) == 0
    assert manifest['edit_authorization'] is False
    assert manifest['no_staff']['historical_runtime_equality'].startswith('UNVERIFIED')
    assert manifest['files']['binary.png']['status'] == 'EXACT_PERSISTED_RESOURCE'
    assert 'NOT_RUNTIME_CAPTURE' in manifest['files']['no-staff.png']['status']
    for name, info in manifest['files'].items():
        assert sha((a / name).read_bytes()) == info['sha256']


@pytest.mark.parametrize('failure', ['hash', 'dimensions', 'staff', 'binary'])
def test_missing_or_mismatched_provenance_fails_closed(tmp_path, failure):
    source, omr = fixture(
        tmp_path,
        staff=failure != 'staff',
        binary=failure != 'binary',
        dimensions=(10, 10) if failure == 'dimensions' else (400, 300),
    )
    out = tmp_path / 'out'
    with pytest.raises((ValueError, KeyError)):
        extract(
            source, omr, out, source_sha='wrong' if failure == 'hash' else sha(source.read_bytes())
        )
    assert not out.exists()


def test_no_staff_replay_does_not_infer_logical_gaps_or_mutate_input():
    image = Image.new('L', (6, 3), 0)
    output = reconstruct_no_staff(image, {(1, 1), (4, 1)})
    assert [output.getpixel((x, 1)) for x in range(6)] == [0, 255, 0, 0, 255, 0]
    assert image.getpixel((1, 1)) == 0
    with pytest.raises(ValueError):
        reconstruct_no_staff(image, {(6, 1)})


def test_attribution_is_evidence_not_new_ownership(tmp_path):
    from backend.omr_v4.v3_evidence import attribute_handoff
    from backend.omr_v4.visual_graph import load_visual_graph
    from omr_v4_fixtures import book

    graph = load_visual_graph(book(tmp_path))
    group = {
        'ownership_evidence_status': 'VERIFIED_PARTIAL',
        'members': ['sheet#1:1'],
        'group_id': 'g',
        'remote_continuation': [[20, 20, 23]],
        'blockers': ['MOVING_ATTACHMENT:AMBIGUOUS_OR_NONLOCAL'],
        'attachments': [{'symbol_id': 'sheet#1:50'}],
    }
    binary = Image.new('L', (400, 300), 255)
    binary.putpixel((20, 20), 0)
    # The slur glyph is source evidence for a different class, not group ownership.
    from dataclasses import replace

    slur = replace(graph.symbols['sheet#1:50'], attributes=(('glyph', '999'),))
    graph = replace(graph, symbols={**graph.symbols, slur.id: slur})
    result = attribute_handoff(
        graph, {'sheet#1:999': {(20, 20)}}, set(), binary, {'groups': [group]}, binary
    )
    assert result['distinct_explained_remote_pixels'] == 1
    assert result['fully_explained_groups'] == 0
    row = result['groups'][0]
    assert row['attribution']['OUTSIDE_PERSISTED_BINARY'] == 2
    assert row['attachments'][0]['category'] == 'EXPLICIT_RELATION_AND_GEOMETRY_AVAILABLE'
    assert row['attachments'][0]['group_ownership_proven'] is False
    assert row['eligibility_unchanged'] is True
    assert 'edit_authorized' not in row


def test_diagnostic_wrapper_binds_existing_snapshots_without_rerunning(tmp_path):
    import json
    from backend.omr_v4.masks import raster_digest
    from scripts.omr_v4.extract_v3_evidence import extract as bundle

    source, omr = fixture(tmp_path)
    (tmp_path / 'source-ink-1.9c').mkdir()
    (tmp_path / 'refinement-handoff').mkdir()
    evidence = {'processed': []}
    (tmp_path / 'source-ink-1.9c/ink-evidence.json').write_text(json.dumps(evidence))
    (tmp_path / 'source-ink-1.9c/ink-summary.json').write_text(
        json.dumps(
            {
                'input_sha256': {
                    'source.png': sha(source.read_bytes()),
                    'recognized.omr': sha(omr.read_bytes()),
                }
            }
        )
    )
    with Image.open(source) as im:
        digest = raster_digest(im)
    (tmp_path / 'refinement-handoff/handoff.json').write_text(
        json.dumps(
            {
                'groups': [],
                'source_digest': digest,
                'ownership_evidence_digest': sha(
                    json.dumps(evidence, sort_keys=True, allow_nan=False).encode()
                ),
            }
        )
    )
    (tmp_path / 'semantic-report.json').write_text(
        json.dumps({'repair_provenance': [], 'semantic_integrity': {'overall': 'warning'}})
    )
    (tmp_path / 'pre-ledger.musicxml').write_bytes(b'<score-partwise/>')
    (tmp_path / 'recognized.musicxml').write_bytes(b'<score-partwise/>')
    bundle(tmp_path, tmp_path / 'bundle')
    manifest = json.loads((tmp_path / 'bundle/manifest.json').read_text())
    assert manifest['files']['pre-ledger.musicxml']['status'] == 'EXTERNAL_V3_SNAPSHOT_COPY'
    assert (
        json.loads((tmp_path / 'bundle/integrity-report.json').read_text())['semantic_integrity'][
            'overall'
        ]
        == 'warning'
    )
    # Invalid historical binding must not leave an apparently usable bundle.
    handoff_path = tmp_path / 'refinement-handoff/handoff.json'
    handoff = json.loads(handoff_path.read_text())
    handoff['source_digest'] = 'wrong'
    handoff_path.write_text(json.dumps(handoff))
    with pytest.raises(ValueError, match='Handoff source'):
        bundle(tmp_path, tmp_path / 'bad')
    assert not (tmp_path / 'bad').exists()
