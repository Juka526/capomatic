// Optional "buy the developer a coffee" link. Off unless the build sets an
// https URL, and never shown in the Toss mini app build.
export function supportUrl(value, appTarget) {
  if (appTarget === 'toss' || typeof value !== 'string') return null;
  try {
    const url = new URL(value.trim());
    return url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
}
