export const SCORE_MAX_BYTES: number;
export const SCORE_EXTENSIONS: string[];
export const CAPO_MAX: number;
export const KEY_SHIFT_LIMIT: number;
export type ShiftFields = { mode: 'key' | 'capo'; semitones: number };
export function fileExtension(name: string): string;
export function scoreFileProblem(name: string, size: number): 'type' | 'size' | null;
export function shiftFields(mode: 'key' | 'capo', value: number | string): ShiftFields;
export function scoreDownloadName(original: string, fields: ShiftFields, format: 'zip' | 'pdf'): string;
