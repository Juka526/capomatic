import assert from 'node:assert/strict';
import test from 'node:test';

import { pngDownloadName } from '../lib/download-name.mjs';

test('always ends in .png, replacing the source extension', () => {
  assert.equal(pngDownloadName('replace', '친구야.jpeg'), 'transposed_replace_친구야.png');
  assert.equal(pngDownloadName('above', 'sheet.PNG'), 'transposed_above_sheet.png');
  assert.equal(pngDownloadName('replace', 'my.song.v2.jpg'), 'transposed_replace_my.song.v2.png');
});

test('handles names without an extension and missing names', () => {
  assert.equal(pngDownloadName('replace', 'scan'), 'transposed_replace_scan.png');
  assert.equal(pngDownloadName('above', ''), 'transposed_above_output.png');
  assert.equal(pngDownloadName('above', undefined), 'transposed_above_output.png');
});
