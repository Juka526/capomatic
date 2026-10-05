import assert from 'node:assert/strict';
import test from 'node:test';

import { dependencyPaths, evaluateAudit } from '../scripts/audit-gate.mjs';

// tailwindcss -> chokidar -> braces, tailwindcss -> micromatch -> braces,
// tailwindcss -> fast-glob -> micromatch (nested) -> braces.
const lock = {
  packages: {
    '': { dependencies: { next: '1' }, devDependencies: { tailwindcss: '3' } },
    'node_modules/next': {},
    'node_modules/tailwindcss': { dependencies: { chokidar: '3', 'fast-glob': '3', micromatch: '4' } },
    'node_modules/chokidar': { dependencies: { braces: '3' } },
    'node_modules/micromatch': { dependencies: { braces: '3' } },
    'node_modules/fast-glob': { dependencies: { micromatch: '4' } },
    'node_modules/fast-glob/node_modules/micromatch': { dependencies: { braces: '3' } },
    'node_modules/braces': {},
  },
};
const braces = { url: 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm', name: 'braces', severity: 'high', title: 'braces DoS' };
const audit = (...via) => ({ vulnerabilities: { x: { via } } });
const exceptions = [{
  id: 'GHSA-vfj7-8cjw-p6xm', package: 'braces', review: '2026-12-01',
  paths: ['tailwindcss>chokidar>braces', 'tailwindcss>micromatch>braces', 'tailwindcss>fast-glob>micromatch>braces'],
}];

test('lockfile paths to a package, nested node_modules included', () => {
  assert.deepEqual(dependencyPaths(lock, 'braces').map((p) => p.join('>')).sort(), exceptions[0].paths.slice().sort());
});

test('the excepted advisory on the excepted paths passes', () => {
  const r = evaluateAudit(audit(braces), lock, exceptions);
  assert.deepEqual(r.failures, []);
  assert.equal(r.allowed.length, 1);
});

test('without the exception the same advisory fails', () => {
  assert.equal(evaluateAudit(audit(braces), lock, []).failures.length, 1);
});

test('the excepted advisory reached through another package fails', () => {
  const wider = structuredClone(lock);
  wider.packages[''].dependencies.picomatch = '1';
  wider.packages['node_modules/picomatch'] = { dependencies: { braces: '3' } };
  const r = evaluateAudit(audit(braces), wider, exceptions);
  assert.equal(r.failures.length, 1);
  assert.match(r.failures[0], /picomatch>braces/);
});

test('any other high or critical advisory still fails; moderate does not', () => {
  const other = { url: 'https://github.com/advisories/GHSA-aaaa-bbbb-cccc', name: 'braces', severity: 'critical', title: 'other' };
  const next = { url: 'https://github.com/advisories/GHSA-dddd-eeee-ffff', name: 'next', severity: 'high', title: 'next bug' };
  const moderate = { url: 'https://github.com/advisories/GHSA-1111-2222-3333', name: 'next', severity: 'moderate', title: 'minor' };
  const r = evaluateAudit(audit(braces, other, next, moderate), lock, exceptions);
  assert.equal(r.failures.length, 2);
  assert.equal(r.allowed.length, 1);
});
