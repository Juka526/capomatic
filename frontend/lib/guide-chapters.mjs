// Scene ("chapter") lookup for the single how-to video. Chapter start times
// come from guide.chapters.json, written by scripts/record-guide.mjs.

/**
 * Validate a chapters file. Returns the chapters ({ start, end }, ascending,
 * first at 0) or [] when the data is missing or malformed.
 */
export function parseChapters(data) {
  const list = Array.isArray(data?.chapters) ? data.chapters : null;
  if (!list || list.length === 0) return [];
  const chapters = list.map((c) => ({ start: Number(c?.start), end: Number(c?.end) }));
  const ok = chapters.every((c, i) => Number.isFinite(c.start) && Number.isFinite(c.end) && c.start >= 0 && c.end > c.start
    && (i === 0 || c.start >= chapters[i - 1].end - 1e-6));
  return ok ? chapters : [];
}

/** Index of the chapter playing at `time` (0 before the first start or with no chapters). */
export function chapterAt(time, chapters) {
  let index = 0;
  for (let i = 0; i < chapters.length; i++) {
    if (time >= chapters[i].start) index = i;
  }
  return index;
}

/** Start of the chapter after the one at `time`, or null on the last chapter. */
export function nextChapterStart(time, chapters) {
  const next = chapters[chapterAt(time, chapters) + 1];
  return next ? next.start : null;
}

/** Start of the chapter before the one at `time`, or null on the first chapter. */
export function previousChapterStart(time, chapters) {
  const i = chapterAt(time, chapters);
  return i > 0 ? chapters[i - 1].start : null;
}
