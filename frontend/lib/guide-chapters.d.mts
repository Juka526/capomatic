export interface Chapter { start: number; end: number }
export function parseChapters(data: unknown): Chapter[];
export function chapterAt(time: number, chapters: Chapter[]): number;
export function nextChapterStart(time: number, chapters: Chapter[]): number | null;
export function previousChapterStart(time: number, chapters: Chapter[]): number | null;
