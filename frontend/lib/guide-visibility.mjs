// First-visit guide: shown automatically on the home page until the user picks
// "Don't show again". Skipping, closing and finishing do not store anything.
export const GUIDE_DISMISSED_KEY = 'tc-guide-dismissed';

/** Whether the home page should open the guide on its own. */
export function shouldAutoOpenGuide({ storedValue, pathname, hasFile }) {
  if (pathname !== '/' || hasFile) return false;
  return storedValue !== '1';
}

/**
 * Read the stored flag. `getStorage` is a function because merely touching
 * `window.localStorage` throws in some private modes and in-app browsers;
 * any failure reads as "not dismissed", so the guide keeps showing.
 */
export function readGuideDismissed(getStorage) {
  try {
    return getStorage().getItem(GUIDE_DISMISSED_KEY);
  } catch {
    return null;
  }
}

/** Store "don't show again". Returns false when storage is unavailable. */
export function writeGuideDismissed(getStorage) {
  try {
    getStorage().setItem(GUIDE_DISMISSED_KEY, '1');
    return true;
  } catch {
    return false;
  }
}
