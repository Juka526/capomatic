import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';

import { LETTER_PATHS, M_INDEX } from '../lib/logo-geometry.mjs';
import { REST_M_PATH, STOP_ENERGY, mPath, pluckEnergy, pluckFrame, pluckVibration } from '../lib/logo-pluck.mjs';

const sha256 = (s) => createHash('sha256').update(s).digest('hex');

test('the rest shape is exactly the m path of the approved static logo', () => {
  // sha256 of the data-m path in the design handoff's capomatic-logo.svg.
  assert.equal(sha256(REST_M_PATH), 'e1d972bc126cd83dd0c6edcc1a9cbb1df3b1dd50361974908f22dc3b2ddb4b2d');
  assert.equal(LETTER_PATHS.length, 9);
  assert.equal(LETTER_PATHS[M_INDEX], null);
});

test('the string ends are fixed', () => {
  for (const t of [0, 0.1, 0.37, 1]) {
    const v = pluckVibration(t);
    assert.ok(Math.abs(v(0)) < 1e-9);
    assert.ok(Math.abs(v(1)) < 1e-9);
  }
});

test('the bottoms of the stems never move', () => {
  const baseline = (d) => [...d.matchAll(/[ML](-?[\d.]+) (-?[\d.]+)/g)]
    .map(([, x, y]) => [x, y]).filter(([, y]) => Number(y) >= 0).map((p) => p.join(' '));
  const frame = mPath(pluckVibration(0.05));
  assert.notEqual(frame, REST_M_PATH);
  assert.deepEqual(baseline(frame), baseline(REST_M_PATH));
});

test('the vibration decays and stops at the energy threshold', () => {
  assert.equal(pluckEnergy(0), 26);
  assert.ok(pluckEnergy(1) < pluckEnergy(0.5));
  assert.notEqual(pluckFrame(0.2), null);
  const stopAt = [...Array(1000).keys()].map((i) => i / 100).find((t) => pluckEnergy(t) <= STOP_ENERGY);
  assert.ok(stopAt > 3 && stopAt < 6, `stops at ${stopAt}s`);
  assert.equal(pluckFrame(stopAt), null);
});
