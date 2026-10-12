import assert from 'node:assert/strict';
import test from 'node:test';

import {
  GUIDE_DISMISSED_KEY, readGuideDismissed, shouldAutoOpenGuide, writeGuideDismissed,
} from '../lib/guide-visibility.mjs';

const memory = (initial = {}) => {
  const data = { ...initial };
  return { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = String(v); }, data };
};
const throwing = () => { throw new Error('SecurityError'); };

test('opens on the home page until dismissed', () => {
  assert.equal(shouldAutoOpenGuide({ storedValue: null, pathname: '/', hasFile: false }), true);
  assert.equal(shouldAutoOpenGuide({ storedValue: '1', pathname: '/', hasFile: false }), false);
  // Only the exact stored value counts; anything else keeps showing the guide.
  assert.equal(shouldAutoOpenGuide({ storedValue: '0', pathname: '/', hasFile: false }), true);
});

test('never opens on other pages or once a file is picked', () => {
  for (const pathname of ['/history', '/privacy', '/terms']) {
    assert.equal(shouldAutoOpenGuide({ storedValue: null, pathname, hasFile: false }), false);
  }
  assert.equal(shouldAutoOpenGuide({ storedValue: null, pathname: '/', hasFile: true }), false);
});

test('storage failures read as not dismissed and report a failed write', () => {
  assert.equal(readGuideDismissed(throwing), null);
  assert.equal(readGuideDismissed(() => ({ getItem: throwing })), null);
  assert.equal(writeGuideDismissed(throwing), false);
  assert.equal(shouldAutoOpenGuide({ storedValue: readGuideDismissed(throwing), pathname: '/', hasFile: false }), true);
});

test('writing stores "1" under the guide key and reads back as dismissed', () => {
  const store = memory();
  assert.equal(readGuideDismissed(() => store), null);
  assert.equal(writeGuideDismissed(() => store), true);
  assert.equal(store.data[GUIDE_DISMISSED_KEY], '1');
  assert.equal(shouldAutoOpenGuide({ storedValue: readGuideDismissed(() => store), pathname: '/', hasFile: false }), false);
});
