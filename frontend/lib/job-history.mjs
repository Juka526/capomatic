const MAX_JOB_HISTORY = 50;

function isNullableString(value) {
  return value === null || typeof value === 'string';
}

export function isJobHistoryEntry(value) {
  return Boolean(value)
    && typeof value === 'object'
    && typeof value.id === 'string'
    && isNullableString(value.song_name)
    && isNullableString(value.original_key)
    && isNullableString(value.target_key)
    && Number.isFinite(value.semitones)
    && typeof value.timestamp === 'string'
    && !Number.isNaN(Date.parse(value.timestamp));
}

export function parseJobHistory(raw) {
  try {
    const value = JSON.parse(raw || '[]');
    return Array.isArray(value)
      ? value.filter(isJobHistoryEntry).slice(0, MAX_JOB_HISTORY)
      : [];
  } catch {
    return [];
  }
}

export function prependJobHistory(raw, entry) {
  return [entry, ...parseJobHistory(raw)].slice(0, MAX_JOB_HISTORY);
}
