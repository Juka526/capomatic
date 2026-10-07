import assert from 'node:assert/strict';
import { readdir, readFile, stat } from 'node:fs/promises';
import { join } from 'node:path';

async function filesIn(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(entries.map(entry => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? filesIn(path) : [path];
  }));
  return files.flat();
}

const files = await filesIn('out');
for (const route of ['index.html', 'privacy/index.html', 'terms/index.html', '404.html']) {
  const html = await readFile(join('out', route), 'utf8');
  assert.match(html, /data-app-target="toss"/, `${route}: expected Toss export`);
  assert.doesNotMatch(html, /href="(?:https?:|\/history)|target="_blank"/, `${route}: external/history link`);
  assert.doesNotMatch(html, /Auth0|Vercel Analytics/, `${route}: web-only privacy text`);
}
assert.equal(await stat('out/history/index.html').then(() => true, () => false), false, 'History must not be exported');
for (const path of files.filter(path => path.endsWith('.js'))) {
  const js = await readFile(path, 'utf8');
  assert.doesNotMatch(js, /auth0-spa-js|auth0\.com|oauth\/token|authorize\?/, `${path}: Auth0 code`);
  assert.doesNotMatch(js, /\beval\s*\(|\bnew\s+Function\s*\(/, `${path}: dynamic code execution`);
  assert.doesNotMatch(js, /ait-devtools-panel|data-ait-devtools/, `${path}: development tools`);
  assert.doesNotMatch(js, /chord-editor/, `${path}: chord editing UI`);
}
console.log(`Toss export checked: ${files.length} files; no Auth0, external page links, history HTML, chord editing UI, or eval calls.`);
