export const GUIDE_DISMISSED_KEY: 'tc-guide-dismissed';
export const GUIDE_STEP_COUNT: 5;
export function shouldAutoOpenGuide(input: { storedValue: string | null; pathname: string; hasFile: boolean }): boolean;
export function readGuideDismissed(getStorage: () => Pick<Storage, 'getItem'>): string | null;
export function writeGuideDismissed(getStorage: () => Pick<Storage, 'setItem'>): boolean;
export function guideMedia(device: 'mobile' | 'desktop', lang: string): { mp4: string; poster: string; chapters: string };
