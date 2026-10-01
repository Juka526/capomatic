import assert from 'node:assert/strict';
import test from 'node:test';

import { chapterAt, nextChapterStart, parseChapters, previousChapterStart } from '../lib/guide-chapters.mjs';

const chapters = parseChapters({
  duration: 30,
  chapters: [
    { start: 0, end: 6 }, { start: 6, end: 13.5 }, { start: 13.5, end: 20 }, { start: 20, end: 26 }, { start: 26, end: 30 },
  ],
});

test('chapterAt switches exactly at each start', () => {
  assert.equal(chapterAt(0, chapters), 0);
  assert.equal(chapterAt(5.999, chapters), 0);
  assert.equal(chapterAt(6, chapters), 1);
  assert.equal(chapterAt(13.49, chapters), 1);
  assert.equal(chapterAt(13.5, chapters), 2);
  assert.equal(chapterAt(29.99, chapters), 4);
  assert.equal(chapterAt(30, chapters), 4);
  // After the loop the video is back at 0: step 1 again.
  assert.equal(chapterAt(0, chapters), 0);
  assert.equal(chapterAt(-1, chapters), 0);
});

test('next and previous jump to neighbouring chapter starts', () => {
  assert.equal(nextChapterStart(0, chapters), 6);
  assert.equal(nextChapterStart(5.999, chapters), 6);
  assert.equal(nextChapterStart(6, chapters), 13.5);
  assert.equal(nextChapterStart(27, chapters), null); // last chapter: the modal closes instead
  assert.equal(previousChapterStart(0, chapters), null);
  assert.equal(previousChapterStart(6, chapters), 0);
  assert.equal(previousChapterStart(14, chapters), 6);
  assert.equal(previousChapterStart(29.9, chapters), 20);
});

test('missing or malformed chapter data gives no chapters', () => {
  for (const bad of [null, undefined, {}, { chapters: [] }, { chapters: 'x' },
    { chapters: [{ start: 0, end: 5 }, { start: 3, end: 8 }] }, // overlap
    { chapters: [{ start: 'a', end: 5 }] },
    { chapters: [{ start: 2, end: 1 }] },
    { chapters: [{ start: -1, end: 1 }] }]) {
    assert.deepEqual(parseChapters(bad), []);
  }
  assert.equal(chapterAt(10, []), 0);
  assert.equal(nextChapterStart(10, []), null);
  assert.equal(previousChapterStart(10, []), null);
});
