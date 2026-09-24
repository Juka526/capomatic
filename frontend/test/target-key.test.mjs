import assert from 'node:assert/strict';
import test from 'node:test';

import { computeTargetKey } from '../lib/target-key.mjs';

test('uses the same canonical target-key spelling as the backend', () => {
  assert.equal(computeTargetKey('C#', 2), 'Eb');
  assert.equal(computeTargetKey('Gb', -1), 'F');
  assert.equal(computeTargetKey('A#', 1), 'B');
  assert.equal(computeTargetKey('F#', 0), 'F#');
});

test('handles negative shifts and unknown keys', () => {
  assert.equal(computeTargetKey('C', -2), 'Bb');
  assert.equal(computeTargetKey('X', 2), 'X');
});
