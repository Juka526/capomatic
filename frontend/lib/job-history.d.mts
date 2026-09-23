export interface JobHistoryEntry {
  id: string;
  song_name: string | null;
  original_key: string | null;
  target_key: string | null;
  semitones: number;
  timestamp: string;
}

export function isJobHistoryEntry(value: unknown): value is JobHistoryEntry;
export function parseJobHistory(raw: string | null): JobHistoryEntry[];
export function prependJobHistory(raw: string | null, entry: JobHistoryEntry): JobHistoryEntry[];
