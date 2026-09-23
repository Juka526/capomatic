import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeReturnTo } from '../lib/safe-return-to.mjs';

test('keeps internal Auth0 return paths', () => {
  assert.equal(normalizeReturnTo('/history?from=login'), '/history?from=login');
});

test('rejects protocol-relative and absolute redirects', () => {
  assert.equal(normalizeReturnTo('//evil.example'), '/');
  assert.equal(normalizeReturnTo('/\\evil.example'), '/');
  assert.equal(normalizeReturnTo('/safe\n//evil.example'), '/');
  assert.equal(normalizeReturnTo('https://evil.example'), '/');
});

test('falls back for missing or malformed app state', () => {
  assert.equal(normalizeReturnTo(undefined), '/');
  assert.equal(normalizeReturnTo(42), '/');
});
