import assert from 'node:assert/strict';
import test from 'node:test';

import { sentryOptions } from '../lib/sentry-options.mjs';

test('tags events with the exact release and environment', () => {
  const options = sentryOptions({ dsn: 'https://k@o0.ingest.sentry.io/1', release: 'abc123', environment: 'preview' });
  assert.equal(options.enabled, true);
  assert.equal(options.release, 'abc123');
  assert.equal(options.environment, 'preview');
});

test('keeps PII and session replay disabled', () => {
  const options = sentryOptions({ dsn: 'https://k@o0.ingest.sentry.io/1' });
  assert.equal(options.sendDefaultPii, false);
  assert.equal(options.replaysSessionSampleRate, 0);
  assert.equal(options.replaysOnErrorSampleRate, 0);
});

test('is disabled without a DSN', () => {
  const options = sentryOptions({ dsn: '', release: '', environment: '' });
  assert.equal(options.enabled, false);
  assert.equal(options.release, undefined);
  assert.equal(options.environment, 'development');
});
