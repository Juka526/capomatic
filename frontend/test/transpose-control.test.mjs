import assert from 'node:assert/strict';
import test from 'node:test';

import { capoFromSemitones, mobileStepper, shiftSummary } from '../lib/transpose-control.mjs';

test('capo is the negated shift only inside frets 1-7', () => {
  assert.equal(capoFromSemitones(0), 0);
  assert.equal(capoFromSemitones(-1), 1);
  assert.equal(capoFromSemitones(-7), 7);
  assert.equal(capoFromSemitones(-8), 0);
  assert.equal(capoFromSemitones(-11), 0);
  assert.equal(capoFromSemitones(1), 0);
  assert.equal(capoFromSemitones(11), 0);
});

test('+ raises the capo and - lowers it inside the capo range', () => {
  const at0 = mobileStepper(0);
  assert.deepEqual(at0.label, { kind: 'capo', capo: 0 });
  assert.deepEqual(at0.plus, { next: -1, disabled: false, action: 'capoUp' });
  assert.deepEqual(at0.minus, { next: 1, disabled: false, action: 'keyUp' });

  const capo1 = mobileStepper(-1);
  assert.deepEqual(capo1.label, { kind: 'capo', capo: 1 });
  assert.equal(capo1.minus.action, 'capoDown');
  assert.equal(capo1.minus.next, 0);
});

test('past fret 7, + keeps lowering the key without a capo', () => {
  const capo7 = mobileStepper(-7);
  assert.deepEqual(capo7.label, { kind: 'capo', capo: 7 });
  assert.deepEqual(capo7.plus, { next: -8, disabled: false, action: 'keyDown' });

  const minus8 = mobileStepper(-8);
  assert.equal(minus8.capo, 0);
  assert.deepEqual(minus8.label, { kind: 'keyDown', semitones: -8 });
  assert.equal(minus8.minus.action, 'keyUp');
  assert.equal(minus8.minus.next, -7);
});

test('below fret 0, - keeps raising the key without a capo', () => {
  const plus1 = mobileStepper(1);
  assert.deepEqual(plus1.label, { kind: 'keyUp', semitones: 1 });
  assert.deepEqual(plus1.plus, { next: 0, disabled: false, action: 'keyDown' });
  assert.equal(plus1.minus.action, 'keyUp');
});

test('the ends of the API range disable the matching button', () => {
  const low = mobileStepper(-11);
  assert.equal(low.plus.disabled, true);
  assert.equal(low.minus.disabled, false);
  const high = mobileStepper(11);
  assert.equal(high.minus.disabled, true);
  assert.equal(high.plus.disabled, false);
});

test('header summary shows the capo inside the range, semitones outside', () => {
  assert.deepEqual(shiftSummary(-2), { kind: 'capo', capo: 2 });
  assert.deepEqual(shiftSummary(-9), { kind: 'semitones', semitones: -9 });
  assert.deepEqual(shiftSummary(2), { kind: 'semitones', semitones: 2 });
});
