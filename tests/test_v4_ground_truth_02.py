"""Synthetic pixel, lineage, timing and blinded-packet controls; no Audiveris."""

from fractions import Fraction
from types import SimpleNamespace as NS

import pytest
from PIL import Image, ImageDraw

from scripts.research import ground_truth_02 as gt


def staff_image(mode='L', stem=False):
    image = Image.new('L', (300, 120), 255)
    d = ImageDraw.Draw(image)
    for y in (30, 40, 50, 60, 70):
        d.line((10, y, 290, y), fill=0)
    for x in (155, 290):
        d.line((x, 30, x, 70), fill=0, width=3)
    if stem:
        d.line((200, 30, 200, 70), fill=0)
        d.ellipse((188, 66, 200, 75), fill=0)
    return image if mode == 'L' else image.convert(mode)


def observation(image, stem=False):
    systems = gt.raster_systems(image)
    return {
        'pdf_page': 2,
        'source_sha256': 'synthetic',
        'visually_read_system_start_labels': [1],
        'accepted_internal_boundaries': {'1': [155.0]},
        'rejected_vertical_candidates': (
            {
                '1': [
                    {
                        'x': 200.0,
                        'classification': 'NOTE_STEM_NOT_BARLINE',
                        'reason': 'synthetic connected head',
                    }
                ]
            }
            if stem
            else {}
        ),
        'ending_context': {},
    }


def test_raster_staff_and_barline_registration_independent_of_omr():
    im = staff_image()
    before = im.tobytes()
    page = gt.registered_page(im, 'Bb', observation(im))
    assert [m['printed_measure'] for m in page['measures']] == [1, 2]
    assert page['measures'][0]['right']['x'] == 155
    assert page['measures'][0]['left']['type'] == 'SYSTEM_START_CONTEXT_EDGE'
    assert not page['measures'][0]['independent_human_verified']
    assert im.tobytes() == before


def test_identical_rgb_lossless_analysis_retains_original_mode_pixels():
    im = staff_image('RGB')
    before = im.tobytes()
    assert gt.raster_systems(im) == gt.raster_systems(staff_image())
    assert im.mode == 'RGB' and im.tobytes() == before
    im.putpixel((0, 0), (0, 1, 2))
    with pytest.raises(ValueError, match='identical RGB'):
        gt.raster_systems(im)


def test_full_staff_stem_requires_explicit_coordinator_classification():
    im = staff_image(stem=True)
    obs = observation(im, stem=True)
    assert len(gt.raster_systems(im)[0]['bar_proposals']) == 2
    page = gt.registered_page(im, 'Bb', obs)
    assert len(page['measures']) == 2
    assert any(r['classification'] == 'NOTE_STEM_NOT_BARLINE' for r in page['proposal_audit'])
    obs['rejected_vertical_candidates'] = {}
    with pytest.raises(ValueError, match='Unreviewed'):
        gt.registered_page(im, 'Bb', obs)


def test_wrong_printed_system_start_labels_fail_not_force_count():
    im = staff_image()
    obs = observation(im)
    obs['visually_read_system_start_labels'] = [5]
    with pytest.raises(ValueError, match='labels disagree'):
        gt.registered_page(im, 'Bb', obs)


def test_box_crossing_barline_is_ambiguous_not_nearest():
    im = staff_image()
    page = gt.registered_page(im, 'Bb', observation(im))
    assert gt.region_for_box(page, 1, (40, 65, 55, 80))[:2] == ('MATCHED', [1])
    assert gt.region_for_box(page, 1, (150, 65, 160, 80))[:2] == ('AMBIGUOUS', [1, 2])
    assert gt.region_for_box(page, 1, None)[0] == 'UNMATCHED'
    assert gt.region_for_box(page, 1, (float('nan'), 0, 1, 2))[0] == 'UNMATCHED'


def test_omr_stack_merger_reported_without_inventing_measure_or_retiming():
    im = staff_image()
    page = gt.registered_page(im, 'Bb', observation(im))
    staff = NS(
        id='s',
        system='sys',
        part='1',
        lines=tuple(((10, y), (290, y)) for y in (30, 40, 50, 60, 70)),
    )
    measure = NS(
        id='m',
        number='1',
        part='1',
        system='sys',
        bounds=(10, 30, 290, 70),
        duration=Fraction(8),
        source_xml='',
        stack_source_xml='',
    )
    graph = NS(staves=[staff], measures=[measure], symbols={})
    result = gt.segmentation(graph, page)
    assert result[0]['status'] == 'PARTIAL' and result[0]['printed_measures'] == [1, 2]
    assert (
        result[0]['missing_boundaries'][0]['cause']
        == 'PRINTED_BARLINE_NOT_PERSISTED_AS_SIG_BOUNDARY'
    )
    assert measure.duration == 8


def event(offset, duration=1, **changes):
    value = {
        'id': str(offset),
        'offset': Fraction(offset),
        'duration': Fraction(duration),
        'voice': None,
        'status': 'MATCHED',
        'chord_continuation': False,
        'kind': 'NOTE',
        'staff': 1,
        'printed_measures': [1],
        'local_offset': Fraction(offset),
        'chord_size': 1,
        'member': 0,
        'pitch': 'C4',
    }
    return value | changes


def test_bounded_physical_partition_can_rebase_only_complete_recognized_tile():
    rows = [event(6, 3), event(9, Fraction(1, 2)), event(Fraction(19, 2), Fraction(1, 2))]
    before = [r.copy() for r in rows]
    origin, reason = gt.tiled_origin(rows)
    assert origin == 6 and 'NOT_GROUND_TRUTH' in reason
    assert rows == before


@pytest.mark.parametrize(
    'rows',
    [
        [event(0, 3)],
        [event(0), event(2, 3)],
        [event(0, 3), event(3, 1, voice='2')],
        [event(0, 4, status='AMBIGUOUS')],
        [event(0, 4, chord_continuation=True)],
        [],
    ],
)
def test_gaps_overlaps_unknown_voice_and_incomplete_timing_fail_closed(rows):
    assert gt.tiled_origin(rows)[0] is None


def test_pairing_tests_pitch_after_structural_pairing_and_never_sets_truth():
    left = [event(0, 4, pitch='C4')]
    right = [event(0, 4, pitch='G4')]
    result = gt.pairing(left, right, {'0': 'B3'}, -1)
    assert result['paired_pitched_notes'] == 1 and result['interval_agreements'] == 0
    assert (
        result['independently_verified_denominator'] == 0
        and result['musical_accuracy_percentage'] is None
    )
    assert not result['pairs'][0]['frozen_target_spelling_agrees']


def test_pairing_does_not_resolve_duplicates_or_use_pitch_to_guess():
    left = [event(0, 4, pitch='C4')]
    right = [event(0, 4, pitch='B3'), event(0, 4, pitch='A3')]
    assert gt.pairing(left, right, {}, -1)['paired_pitched_notes'] == 0
    assert gt.pairing(left, [event(0, 4, voice='2')], {}, -1)['paired_pitched_notes'] == 0


def test_rest_geometry_requires_explicit_lineage_and_correct_staff():
    rest = NS(id='r', kind='rest', staff='s')
    m = NS(
        slots=[NS(id='slot', offset=Fraction(0), suspicious=False)],
        onsets=[('chord', 'slot', '1')],
        source_xml='<measure/>',
        page='sheet#1',
    )
    graph = NS(relations=[], symbols={'r': rest}, staves=[NS(id='s', number=1)])
    ev = {'offset': Fraction(0), 'voice': None, 'measure_rest': False, 'staff': 1}
    assert gt.rest_geometry(ev, graph, [m]) is None
    graph.relations = [NS(kind='contains', source='chord', target='r')]
    assert gt.rest_geometry(ev, graph, [m]) is rest
    ev['staff'] = 2
    assert gt.rest_geometry(ev, graph, [m]) is None


def packet_fixture(tmp_path):
    from scripts.research import gt02_reference_packet as packet

    source = tmp_path / 'immutable' / 'source.png'
    source.parent.mkdir()
    staff_image('RGB').save(source)
    page = gt.registered_page(Image.open(source), 'X', observation(Image.open(source)))
    page['source_sha256'] = gt.sha(source)
    registration = {'pages': {'X': page}}
    out = tmp_path / 'blind-packet'
    index = tmp_path / 'private.json'
    summary = packet.prepare({'X': source}, registration, out, index)
    return packet, source, registration, out, index, summary


def test_packet_native_pixels_neutral_forms_no_coordinator_answers(tmp_path):
    import json

    packet, source, reg, out, index, summary = packet_fixture(tmp_path)
    assert summary['actual_independent_submissions'] == 0 and summary['cases'] == 2
    metadata = json.loads((out / 'cases.json').read_text())
    image = Image.open(source)
    for case in metadata['cases']:
        with Image.open(out / case['focus_image']) as crop:
            expected = image.crop(case['focus_bounds_half_open'])
            assert crop.mode == expected.mode and crop.tobytes() == expected.tobytes()
        assert 'printed_measure' not in case and 'expected_match' not in case
    assert all(
        (out / name).stat().st_mode & 0o222 == 0
        for name in ['cases.json', 'blank-A.json', 'blank-B.json']
    )
    assert 'coordinator_read_text' not in ''.join(p.read_text() for p in out.glob('*.json'))
    packet.verify_packet(out, index)


def test_packet_rejects_answer_injection_and_blank_submissions(tmp_path):
    import json

    packet, source, reg, out, index, summary = packet_fixture(tmp_path)
    blank = json.loads((out / 'blank-A.json').read_text())
    with pytest.raises(ValueError):
        packet.validate_submission(blank, out, 'A')
    (out / 'answers.json').write_text('{"expected_pitch":"C4"}')
    with pytest.raises(ValueError, match='unexpected'):
        packet.verify_packet(out, index)


def signed_unknown_form(packet, out):
    import json

    data = json.loads((out / 'blank-A.json').read_text())
    data.update(
        status='SIGNED_INDEPENDENT_OBSERVATION',
        person_id='SYNTHETIC_TEST_ONLY',
        signed_at='2026-01-01T00:00:00Z',
    )
    data['independence'] = {
        'worked_on_GT01_GT02_or_architecture': False,
        'seen_predictions_omr_or_coordinator_answers': False,
        'seen_other_reader_submission': False,
        'expertise': 'Synthetic temporary test; not a human label',
        'training_page_sha256_exclusions': ['a' * 64],
        'independent_source_reading_attested': True,
    }
    for case in data['cases']:
        case.update(
            status='UNKNOWN',
            uncertainty='Synthetic inability to resolve; no fabricated musical observations',
        )
    return data


def test_unknowns_allowed_only_after_explicit_exclusion_and_independence_metadata(tmp_path):
    packet, source, reg, out, index, summary = packet_fixture(tmp_path)
    data = signed_unknown_form(packet, out)
    assert (
        packet.validate_submission(data, out, 'A')['status']
        == 'SCHEMA_VALID_NOT_ACCEPTED_GROUND_TRUTH'
    )
    data['independence']['seen_predictions_omr_or_coordinator_answers'] = True
    with pytest.raises(ValueError, match='exclusion'):
        packet.validate_submission(data, out, 'A')


def test_packet_cannot_write_private_mapping_into_source_evidence(tmp_path):
    packet, source, reg, out, index, summary = packet_fixture(tmp_path)
    with pytest.raises(ValueError, match='immutable'):
        packet.prepare({'X': source}, reg, tmp_path / 'other', source.parent / 'private.json')
    assert not (source.parent / 'private.json').exists()


def test_ambiguous_barline_event_blocks_both_neighboring_rhythm_tiles(tmp_path, monkeypatch):
    im = staff_image()
    page = gt.registered_page(im, 'X', observation(im))
    staff = NS(
        id='s',
        number=1,
        system='sys',
        part='1',
        lines=tuple(((10, y), (290, y)) for y in (30, 40, 50, 60, 70)),
    )
    boxes = {'h0': (40, 65, 55, 80), 'h1': (150, 65, 160, 80), 'h2': (240, 65, 255, 80)}
    graph = NS(
        staves=[staff],
        measures=[],
        symbols={k: NS(id=k, staff='s', geometry=NS(bbox=b)) for k, b in boxes.items()},
    )
    rows = [
        event(0, 4, id='n0', kind='NOTE', omr_number='1'),
        event(4, 2, id='n1', kind='NOTE', omr_number='1'),
        event(6, 4, id='n2', kind='NOTE', omr_number='1'),
    ]
    matches = NS(
        notes=[
            NS(
                note=NS(id='n' + str(i), pitch='C4', chord_size=1, member=0),
                status='MATCHED',
                head_id='h' + str(i),
                ownership_basis='DIRECT',
            )
            for i in range(3)
        ],
        summary=lambda: {},
    )
    monkeypatch.setattr(gt, 'reference_matches', lambda *_: matches)
    monkeypatch.setattr(gt, 'xml_events', lambda *_: [e.copy() for e in rows])
    result, _ = gt.mapped_events(tmp_path, graph, page)
    assert result[1]['status'] == 'AMBIGUOUS' and result[1]['printed_measures'] == [1, 2]
    assert result[0]['local_offset'] is None and result[2]['local_offset'] is None
    assert all(
        m['event_tile']['status'] == 'AMBIGUOUS_BOUNDARY_EVENT_BLOCKS_NEIGHBORING_TILE'
        for m in page['measures']
    )


def test_full_measure_rhythm_signature_can_disagree_without_pitch_selection():
    left = [event(0, 2, pitch='C4'), event(2, 2, pitch='D4')]
    right = [event(0, 1, pitch='B3'), event(1, 3, pitch='C4')]
    result = gt.pairing(left, right, {}, -1)
    assert result['measure_rhythm_statuses'] == {'PARTIAL': 1}
    assert result['paired_pitched_notes'] == 0
    assert result['frozen_prediction_spelling_agreements'] is None


def test_architecture_audit_cannot_write_into_gt01(tmp_path):
    from scripts.research.gt02_architecture_metrics import audit

    with pytest.raises(ValueError, match='separate'):
        audit(tmp_path, tmp_path / 'danger')


def test_architecture_audit_only_measures_frozen_targets_without_anchor_inference(
    tmp_path, monkeypatch
):
    import json, zipfile
    from scripts.research import gt02_architecture_metrics as arch

    root = tmp_path / 'gt01'
    study = tmp_path / 'gt02'
    study.mkdir()
    base = root / 'predictions/baseline-exec'
    (base / 'source').mkdir(parents=True)
    gt.dump(base / 'status.json', {'track_a': {'groups': {'VERIFIED_COMPLETE': 0}}})
    xml = b'<score-partwise><part id="p"><measure number="1"/></part></score-partwise>'
    with zipfile.ZipFile(base / 'source/audiveris.mxl', 'w') as z:
        z.writestr('score.xml', xml)
    for name in ['pre-ledger', 'recognized']:
        (base / 'source' / (name + '.musicxml')).write_bytes(xml)
    page = {
        'systems': [{'staff_lines_y': [0, 10, 20, 30, 40]}],
        'measures': [
            {
                'identity': 'printed-01',
                'system': 1,
                'printed_measure': 1,
                'left': {'x': 0},
                'right': {'x': 100},
            }
        ],
    }
    gt.dump(study / 'measure-registration.json', {'pages': {n: page for n in ['Bb', 'A', 'G']}})
    events = {n: [{'id': 'reference', 'symbol_id': 'head'}] for n in ['A', 'G']}
    comparisons = {
        n: {
            'pairs': [
                {'kind': 'NOTE', 'left_id': 'source', 'right_id': 'reference', 'printed_measure': 1}
            ]
        }
        for n in ['A', 'G']
    }
    gt.dump(
        study / 'note-correspondence-diagnostic.json',
        {'events': events, 'comparisons': comparisons},
    )
    for name in ['A', 'G']:
        gt.dump(base / name / 'track-a-mask-summary.json', {'metrics': {'approved_note_masks': 0}})
        gt.dump(
            base / name / 'track-b-geometry.json',
            {'notes': [{'semantic_id': 'source', 'target_x': 50, 'absolute_target_staff_y': 80}]},
        )
    monkeypatch.setattr(arch, 'verify_inputs', lambda _: {'synthetic_binding': 'test only'})
    monkeypatch.setattr(
        arch, 'load_visual_graph', lambda _: NS(symbols={'head': NS(geometry=NS(center=(52, 81)))})
    )
    before = gt.file_hashes(root)
    result = arch.audit(root, study)
    assert gt.file_hashes(root) == before
    assert result['track_b']['A']['candidate_note_x_residual_px']['mean'] == -2
    assert result['track_b']['A']['candidate_note_y_residual_px']['mean'] == -1
    assert (
        result['track_b']['A']['replacement_glyph_anchor']
        == 'UNDEFINED_NOT_INFERRED_FROM_HEAD_CENTER'
    )
    assert not result['track_b']['A']['renderer_b2']


def test_unobserved_positive_boundary_is_not_silently_ignored():
    im = staff_image()
    obs = observation(im)
    obs['accepted_internal_boundaries']['1'].append(220)
    with pytest.raises(ValueError, match='Confirmation'):
        gt.registered_page(im, 'X', obs)


def test_signed_submission_must_bind_exact_packet_cases(tmp_path):
    packet, source, reg, out, index, summary = packet_fixture(tmp_path)
    data = signed_unknown_form(packet, out)
    data['packet_cases_sha256'] = 'b' * 64
    with pytest.raises(ValueError, match='binding'):
        packet.validate_submission(data, out, 'A')


def test_wrong_experiment_identity_fails_before_reading_score_content(tmp_path):
    (tmp_path / 'baseline-manifest.json').write_text('{}')
    (tmp_path / 'baseline-public.pem').write_text('not the bound key')
    with pytest.raises(ValueError, match='identity'):
        gt.verify_inputs(tmp_path)
