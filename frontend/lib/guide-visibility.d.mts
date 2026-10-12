export const GUIDE_DISMISSED_KEY: 'tc-guide-dismissed';
export function shouldAutoOpenGuide(input: { storedValue: string | null; pathname: string; hasFile: boolean }): boolean;
export function readGuideDismissed(getStorage: () => Pick<Storage, 'getItem'>): string | null;
export function writeGuideDismissed(getStorage: () => Pick<Storage, 'setItem'>): boolean;
