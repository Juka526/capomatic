export type SaveStrategy = 'overlay' | 'share' | 'anchor';

export function isInAppBrowser(userAgent?: string | null): boolean;
export function isIOS(userAgent?: string | null, maxTouchPoints?: number): boolean;
export function chooseSaveStrategy(env: {
  userAgent?: string | null;
  maxTouchPoints?: number;
  canShareFiles?: boolean;
}): SaveStrategy;
export function dataUrlToBlob(dataUrl: string): Blob;
