// Request helpers for the experimental V3 score page (/score-v3). Kept free of
// React so the rules match the backend and can be unit-tested with node --test.

export const SCORE_MAX_BYTES = 10 * 1024 * 1024;
export const SCORE_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.xml', '.musicxml', '.mxl'];
export const CAPO_MAX = 7;
export const KEY_SHIFT_LIMIT = 11;

/** Lower-case extension including the dot, or '' when there is none. */
export function fileExtension(name) {
  const dot = name.lastIndexOf('.');
  return dot < 0 ? '' : name.slice(dot).toLowerCase();
}

/** 'type' | 'size' | null — the same limits the API enforces. */
export function scoreFileProblem(name, size) {
  if (!SCORE_EXTENSIONS.includes(fileExtension(name))) return 'type';
  if (size <= 0 || size > SCORE_MAX_BYTES) return 'size';
  return null;
}

/**
 * Form fields for the API. Capo N keeps the notes and writes chords N
 * semitones lower (semitones = -N), the convention V1 uses; a key change moves
 * notes, key signature and chords together.
 */
export function shiftFields(mode, value) {
  const n = Math.trunc(Number(value)) || 0;
  if (mode === 'capo') {
    const capo = Math.min(CAPO_MAX, Math.max(0, n));
    return { mode: 'capo', semitones: capo === 0 ? 0 : -capo };
  }
  return { mode: 'key', semitones: Math.min(KEY_SHIFT_LIMIT, Math.max(-KEY_SHIFT_LIMIT, n)) };
}

/** Download name: original stem (filesystem-safe) + condition + extension. */
export function scoreDownloadName(original, fields, format) {
  const stem = original.replace(/\.[^.]+$/, '').replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_').slice(0, 80) || 'score';
  const tag = fields.mode === 'capo' ? `capo${-fields.semitones}` : `key${fields.semitones >= 0 ? '+' : ''}${fields.semitones}`;
  return `${stem}-${tag}.${format}`;
}
