from scripts.scan_review_compare import compare


def test_tie_disagreement_is_not_hidden_by_matching_pitch_duration():
    data = b'<score-partwise><part><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><tie type="start"/></note></measure></part></score-partwise>'
    report = compare(data, [{'measure': '1', 'event_index': 0, 'expected': {'pitch': 'C4', 'duration': '1/2', 'ties': []}}])
    assert report['status'] == 'SOURCE_REVIEW_DISAGREEMENT'
    assert report['full_page_accuracy'] is None


def test_rest_event_cardinality_and_duration_are_compared():
    data = b'<score-partwise><part><measure number="4"><attributes><divisions>4</divisions></attributes><note><rest/><duration>2</duration></note><note><rest/><duration>2</duration></note></measure></part></score-partwise>'
    report = compare(data, [{'measure': '4', 'expected': [{'pitch': 'R', 'duration': '4', 'ties': []}]}])
    assert report['checks'][0]['disagreement']


def test_multiple_voices_are_not_flattened_into_an_event_sequence():
    import pytest
    data = b'<score-partwise><part><measure number="4"><note><rest/><duration>1</duration><voice>1</voice></note><backup><duration>1</duration></backup><note><rest/><duration>1</duration><voice>2</voice></note></measure></part></score-partwise>'
    with pytest.raises(ValueError, match='multivoice'):
        compare(data, [{'measure': '4', 'expected': [{'pitch': 'R'}]}])


def test_vacuous_or_negative_index_checks_are_rejected():
    import pytest
    data = b'<score-partwise><part/></score-partwise>'
    for checks in ([], [{'measure':'1','event_index':-1,'expected':{'pitch':'R'}}],
                   [{'measure':'1','event_index':0,'expected':{}}]):
        with pytest.raises(ValueError):
            compare(data, checks)


def test_selected_negative_check_does_not_claim_other_measures_were_read():
    data = b'<score-partwise><part><measure number="1"><note><rest/><duration>1</duration></note></measure><measure number="2"><backup><duration>1</duration></backup></measure></part></score-partwise>'
    report = compare(data, [{'measure':'1','event_index':0,'expected':{'pitch':'C4'}}])
    assert report['status'] == 'SOURCE_REVIEW_DISAGREEMENT'
    assert report['checked_measures'] == ['1']
    assert report['other_measures_unverified'] and report['full_page_accuracy'] is None
