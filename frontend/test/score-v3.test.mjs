import assert from 'node:assert/strict';
import test from 'node:test';

import { scoreDownloadName, scoreFileProblem, shiftFields } from '../lib/score-v3.mjs';

test('file checks mirror the API limits', () => {
  assert.equal(scoreFileProblem('주님 난 알고 싶어요.PDF', 1000), null);
  assert.equal(scoreFileProblem('sheet.musicxml', 10), null);
  assert.equal(scoreFileProblem('sheet.gif', 10), 'type');
  assert.equal(scoreFileProblem('noext', 10), 'type');
  assert.equal(scoreFileProblem('big.png', 10 * 1024 * 1024 + 1), 'size');
  assert.equal(scoreFileProblem('empty.png', 0), 'size');
});

test('capo N is semitones -N and is clamped to 0..7', () => {
  assert.deepEqual(shiftFields('capo', 2), { mode: 'capo', semitones: -2 });
  assert.deepEqual(shiftFields('capo', 0), { mode: 'capo', semitones: 0 });
  assert.deepEqual(shiftFields('capo', 9), { mode: 'capo', semitones: -7 });
  assert.deepEqual(shiftFields('capo', -3), { mode: 'capo', semitones: 0 });
});

test('key shifts are clamped to the API range', () => {
  assert.deepEqual(shiftFields('key', '-2'), { mode: 'key', semitones: -2 });
  assert.deepEqual(shiftFields('key', 14), { mode: 'key', semitones: 11 });
  assert.deepEqual(shiftFields('key', 'x'), { mode: 'key', semitones: 0 });
});

test('download names keep Korean titles and describe the conversion', () => {
  assert.equal(scoreDownloadName('자유.pdf', { mode: 'key', semitones: -2 }, 'zip'), '자유-key-2.zip');
  assert.equal(scoreDownloadName('a/b:c.png', { mode: 'capo', semitones: -3 }, 'pdf'), 'a_b_c-capo3.pdf');
  assert.equal(scoreDownloadName('x.jpg', { mode: 'key', semitones: 2 }, 'pdf'), 'x-key+2.pdf');
});

import { fallbackKind, resultDownloadName } from '../lib/score-v3.mjs';

test('fallback reasons map to user explanations', () => {
  assert.equal(fallbackKind('preflight:staff_spacing_too_small'), 'lowResolution');
  assert.equal(fallbackKind('preflight:image_too_blurry,contrast_too_low'), 'blurry');
  assert.equal(fallbackKind('omr:too_many_inconsistent_bars'), 'unreliableRecognition');
  assert.equal(fallbackKind(null), 'unknown');
});

test('chord-only downloads are named as such', () => {
  const f = { mode: 'capo', semitones: -2 };
  assert.equal(resultDownloadName('자유.pdf', f, 'pdf', 'chord_only'), '자유-capo2-chords-only.pdf');
  assert.equal(resultDownloadName('자유.pdf', f, 'zip', 'full_score'), '자유-capo2.zip');
});
