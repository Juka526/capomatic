import assert from 'node:assert/strict';
import test from 'node:test';

import { capoFromSemitones, shiftSummary, stepperText, transposeStepper } from '../lib/transpose-control.mjs';

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
  const at0 = transposeStepper(0);
  assert.deepEqual(at0.label, { kind: 'capo', capo: 0 });
  assert.deepEqual(at0.plus, { next: -1, disabled: false, action: 'capoUp' });
  assert.deepEqual(at0.minus, { next: 1, disabled: false, action: 'keyUp' });

  const capo1 = transposeStepper(-1);
  assert.deepEqual(capo1.label, { kind: 'capo', capo: 1 });
  assert.equal(capo1.minus.action, 'capoDown');
  assert.equal(capo1.minus.next, 0);
});

test('past fret 7, + keeps lowering the key without a capo', () => {
  const capo7 = transposeStepper(-7);
  assert.deepEqual(capo7.label, { kind: 'capo', capo: 7 });
  assert.deepEqual(capo7.plus, { next: -8, disabled: false, action: 'keyDown' });

  const minus8 = transposeStepper(-8);
  assert.equal(minus8.capo, 0);
  assert.deepEqual(minus8.label, { kind: 'keyDown', semitones: -8 });
  assert.equal(minus8.minus.action, 'keyUp');
  assert.equal(minus8.minus.next, -7);
});

test('below fret 0, - keeps raising the key without a capo', () => {
  const plus1 = transposeStepper(1);
  assert.deepEqual(plus1.label, { kind: 'keyUp', semitones: 1 });
  assert.deepEqual(plus1.plus, { next: 0, disabled: false, action: 'keyDown' });
  assert.equal(plus1.minus.action, 'keyUp');
});

test('the ends of the API range disable the matching button', () => {
  const low = transposeStepper(-11);
  assert.equal(low.plus.disabled, true);
  assert.equal(low.minus.disabled, false);
  const high = transposeStepper(11);
  assert.equal(high.minus.disabled, true);
  assert.equal(high.plus.disabled, false);
});

test('header summary shows the capo inside the range, semitones outside', () => {
  assert.deepEqual(shiftSummary(-2), { kind: 'capo', capo: 2 });
  assert.deepEqual(shiftSummary(-9), { kind: 'semitones', semitones: -9 });
  assert.deepEqual(shiftSummary(2), { kind: 'semitones', semitones: 2 });
});

// Key names of the translation table, so the test checks which string each state picks.
const keys = {
  capoPosition: 'capoPosition', mKeyUpNoCapo: 'mKeyUpNoCapo', mOutOfRangeDown: 'mOutOfRangeDown',
  mSemitoneValue: (n) => `semitones(${n})`, mCapoUp: 'mCapoUp', mCapoDown: 'mCapoDown',
  mKeyDownStep: 'mKeyDownStep', mKeyUpStep: 'mKeyUpStep',
};
const text = (semitones) => stepperText(transposeStepper(semitones), keys);

test('stepper text at the boundaries (shared by mobile and desktop)', () => {
  assert.deepEqual(text(0), { caption: 'capoPosition', value: '0', plusLabel: 'mCapoUp', minusLabel: 'mKeyUpStep' });
  assert.deepEqual(text(-1), { caption: 'capoPosition', value: '1', plusLabel: 'mCapoUp', minusLabel: 'mCapoDown' });
  assert.deepEqual(text(-7), { caption: 'capoPosition', value: '7', plusLabel: 'mKeyDownStep', minusLabel: 'mCapoDown' });
  assert.deepEqual(text(-8), { caption: 'mOutOfRangeDown', value: 'semitones(-8)', plusLabel: 'mKeyDownStep', minusLabel: 'mKeyUpStep' });
  assert.deepEqual(text(-11), { caption: 'mOutOfRangeDown', value: 'semitones(-11)', plusLabel: 'mKeyDownStep', minusLabel: 'mKeyUpStep' });
  assert.deepEqual(text(1), { caption: 'mKeyUpNoCapo', value: 'semitones(1)', plusLabel: 'mKeyDownStep', minusLabel: 'mKeyUpStep' });
  assert.deepEqual(text(11), { caption: 'mKeyUpNoCapo', value: 'semitones(11)', plusLabel: 'mKeyDownStep', minusLabel: 'mKeyUpStep' });
});

test('walking + from 0 reaches capo 7, then -8 semitones; - from 0 reaches +1', () => {
  let s = 0;
  const values = [];
  for (let i = 0; i < 8; i++) { s = transposeStepper(s).plus.next; values.push(text(s).value); }
  assert.deepEqual(values, ['1', '2', '3', '4', '5', '6', '7', 'semitones(-8)']);
  assert.equal(text(transposeStepper(0).minus.next).value, 'semitones(1)');
});
