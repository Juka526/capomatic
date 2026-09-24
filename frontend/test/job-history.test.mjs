import assert from 'node:assert/strict';
import test from 'node:test';
import { parseJobHistory, prependJobHistory } from '../lib/job-history.mjs';

const entry = (id) => ({
  id,
  song_name: 'Song',
  original_key: 'C',
  target_key: 'D',
  semitones: 2,
  timestamp: '2026-09-16T00:00:00.000Z',
});

test('rejects malformed history without throwing', () => {
  assert.deepEqual(parseJobHistory('{broken'), []);
  assert.deepEqual(parseJobHistory('{"id":"not-an-array"}'), []);
});

test('filters invalid entries and caps history at 50', () => {
  const raw = JSON.stringify([
    { ...entry('bad'), semitones: '2' },
    ...Array.from({ length: 60 }, (_, index) => entry(String(index))),
  ]);

  const parsed = parseJobHistory(raw);

  assert.equal(parsed.length, 50);
  assert.equal(parsed[0].id, '0');
  assert.equal(parsed[49].id, '49');
});

test('prepends a new entry to valid recovered history', () => {
  assert.deepEqual(
    prependJobHistory(JSON.stringify([entry('old')]), entry('new')).map(item => item.id),
    ['new', 'old'],
  );
});
