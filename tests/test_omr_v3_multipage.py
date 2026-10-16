"""Real Poppler splitting/combination with controlled page conversion outcomes."""
import io
import shutil
from unittest.mock import patch

import pytest
from PIL import Image

from backend.omr_v3 import core

pytestmark = pytest.mark.skipif(not all(shutil.which(x) for x in
                               ('pdfinfo', 'pdfseparate', 'pdfunite')), reason='Poppler unavailable')


def _pdf(count=3):
    pages = [Image.new('RGB', (100 + i * 10, 200), 'white') for i in range(count)]
    out = io.BytesIO()
    pages[0].save(out, format='PDF', save_all=True, append_images=pages[1:])
    return out.getvalue()


@pytest.mark.parametrize('failure', [False, True])
def test_ordered_mixed_document_and_partial_failure(failure, tmp_path):
    seen = []

    def convert(data, suffix, semitones, mode, **kwargs):
        seen.append(data)
        number = len(seen)
        if failure and number == 2:
            raise core.ScoreError('chord_only:insufficient_chord_coverage')
        result_mode = 'chord_only' if number == 2 else 'full_score'
        return core.Result(_pdf(1), b'<score/>', b'<original/>', {},
                           {'decision': {'reason': str(number)}}, mode=result_mode)

    with patch.object(core, '_process_page', side_effect=convert):
        result = core.process(_pdf(), '.pdf', 2)
    assert len(seen) == 3 and len(set(seen)) == 3
    assert [p['page'] for p in result.report['pages']] == [1, 2, 3]
    assert [p['mode'] for p in result.report['pages']] == [
        'full_score', 'failure' if failure else 'chord_only', 'full_score']
    assert result.mode == ('partial_failure' if failure else 'mixed')
    assert result.report['document']['complete'] is not failure
    output = tmp_path / 'out.pdf'
    output.write_bytes(result.pdf)
    assert core._pdf_pages(output, 30, tmp_path) == 3
    # Split input pages retain original widths; no lexical page reordering.
    for index, data in enumerate(seen):
        page = tmp_path / f'{index}.pdf'
        page.write_bytes(data)
        info = core._run(['pdfinfo', str(page)], 30, tmp_path, 'test').stdout
        assert f'{100 + index * 10} x 200'.encode() in info


def test_page_limit_precedes_omr():
    with patch.object(core, '_process_page', side_effect=AssertionError('must not run')):
        with pytest.raises(core.ScoreError, match='1 to 10'):
            core.process(_pdf(11), '.pdf', 2)


def test_integrity_failure_aborts_document():
    with patch.object(core, '_process_page', side_effect=core.ScoreError('integrity failed', 500)):
        with pytest.raises(core.ScoreError) as exc:
            core.process(_pdf(2), '.pdf', 2)
    assert exc.value.status == 500
