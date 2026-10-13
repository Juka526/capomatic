import assert from 'node:assert/strict';
import test from 'node:test';

import { supportUrl } from '../lib/support-link.mjs';

test('renders nothing when the variable is unset, empty or not https', () => {
  assert.equal(supportUrl(undefined, undefined), null);
  assert.equal(supportUrl('', undefined), null);
  assert.equal(supportUrl('   ', undefined), null);
  assert.equal(supportUrl('http://example.com/support', undefined), null);
  assert.equal(supportUrl('javascript:alert(1)', undefined), null);
  assert.equal(supportUrl('not a url', undefined), null);
});

test('keeps an https link', () => {
  assert.equal(supportUrl('https://example.com/support', undefined), 'https://example.com/support');
  assert.equal(supportUrl('https://example.com/support', 'web'), 'https://example.com/support');
});

test('hides the link in the Toss mini app build', () => {
  assert.equal(supportUrl('https://example.com/support', 'toss'), null);
});
