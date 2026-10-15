"""V3 score pipeline: input validation, rasterisation and tool isolation (no OMR binaries needed)."""
import io
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from backend.omr_v3 import core
from backend.omr_v3.core import ScoreError, process, validate


def _png(w=100, h=100) -> bytes:
    buf = io.BytesIO()
    Image.new('L', (w, h), 255).save(buf, format='PNG')
    return buf.getvalue()


@pytest.mark.parametrize('data,suffix', [
    (b'bad', '.pdf'), (b'bad', '.png'), (b'bad', '.jpg'), (b'bad', '.mxl'), (b'123', '.exe'),
    (b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e "boom">]><x>&e;</x>', '.musicxml'),
])
def test_validate_rejects_bad_input(data, suffix):
    with pytest.raises(ScoreError):
        validate(data, suffix)


def test_validate_rejects_oversized_upload():
    with pytest.raises(ScoreError) as exc:
        validate(b'%PDF-' + b'a' * core.MAX_BYTES, '.pdf')
    assert exc.value.status == 413


def test_validate_accepts_small_png_and_musicxml_doctype():
    validate(_png(), '.png')
    validate(b'<?xml version="1.0"?><!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
             b'"http://www.musicxml.org/dtds/partwise.dtd"><score-partwise/>', '.musicxml')


@pytest.mark.parametrize('semitones,mode', [(12, 'key'), (-12, 'key'), (1, 'capo'), (-8, 'capo'), (0, 'other')])
def test_process_rejects_bad_shift_before_any_work(semitones, mode):
    with pytest.raises(ScoreError):
        process(_png(), '.png', semitones, mode)


def test_pdf_page_guard(tmp_path):
    with patch.object(core, '_bin', return_value='pdfinfo'), \
            patch.object(core, '_run', return_value=core.subprocess.CompletedProcess([], 0, b'Pages: 2\n', b'')):
        with pytest.raises(ScoreError, match='exactly one PDF page'):
            core.rasterize(tmp_path / 'x.pdf', '.pdf', tmp_path / 'p.png', 10, tmp_path)


def test_small_images_are_upscaled_for_omr(tmp_path):
    src = tmp_path / 'small.png'
    src.write_bytes(_png(745, 1054))
    info = core.rasterize(src, '.png', tmp_path / 'page.png', 10, tmp_path)
    assert info['scale'] == 4.0  # ceil(2400 / 745), capped at MAX_UPSCALE
    with Image.open(tmp_path / 'page.png') as im:
        assert im.size == (745 * 4, 1054 * 4) and im.mode == 'L'


def test_large_images_keep_their_size(tmp_path):
    src = tmp_path / 'big.png'
    src.write_bytes(_png(2481, 300))
    assert core.rasterize(src, '.png', tmp_path / 'page.png', 10, tmp_path)['scale'] == 1.0


def test_tool_environment_does_not_leak_secrets(tmp_path):
    secrets = {'ANTHROPIC_API_KEY': 'x', 'SENTRY_DSN': 'y', 'AUTH0_DOMAIN': 'z', 'HF_TOKEN': 't'}
    with patch.dict(os.environ, secrets):
        env = core._tool_env(tmp_path)
    assert not set(secrets) & set(env)
    assert env['HOME'] == str(tmp_path) and env['QT_QPA_PLATFORM'] == 'offscreen'


def test_tool_timeout_kills_the_process_group(tmp_path):
    with pytest.raises(ScoreError) as exc:
        core._run([sys.executable, '-c', 'import time; time.sleep(30)'], 0.5, tmp_path, 'sleeper')
    assert exc.value.status == 504


def test_tool_failure_is_reported_without_output(tmp_path):
    with pytest.raises(ScoreError) as exc:
        core._run([sys.executable, '-c', 'import sys; print("secret path /x"); sys.exit(3)'], 10, tmp_path, 'tool')
    assert str(exc.value) == 'tool failed'


def test_missing_binary_is_503(tmp_path):
    with patch.dict(os.environ, {'CAPOMATIC_AUDIVERIS_BIN': 'definitely-not-installed-xyz'}):
        with pytest.raises(ScoreError) as exc:
            core._bin('CAPOMATIC_AUDIVERIS_BIN', 'audiveris')
    assert exc.value.status == 503


def _mxl(files: dict) -> bytes:
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


def test_mxl_zip_bomb_and_entities_are_rejected():
    validate(_mxl({'score.xml': b'<score-partwise/>'}), '.mxl')
    with pytest.raises(ScoreError) as exc:
        validate(_mxl({'score.xml': b'0' * (core.MAX_MXL_UNCOMPRESSED + 1)}), '.mxl')
    assert exc.value.status == 413
    with pytest.raises(ScoreError):
        validate(_mxl({'score.xml': b'<!DOCTYPE x [<!ENTITY a "b">]><x/>'}), '.mxl')
