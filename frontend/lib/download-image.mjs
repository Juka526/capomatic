// Rendered results arrive from /render as base64 PNG data URIs. Mobile
// browsers handle <a download href="data:..."> poorly: in-app browsers block
// it, iOS Safari ignores it or saves to Files, and large data URIs can fail
// on Android. Saving therefore goes through a Blob and a per-platform path.

const IN_APP_RE = /KAKAOTALK|NAVER\(inapp|Instagram|FBAN|FBAV|FB_IAB|Line\/|DaumApps|everytimeApp|; wv\)/i;

export function isInAppBrowser(userAgent) {
  return IN_APP_RE.test(userAgent || '');
}

export function isIOS(userAgent, maxTouchPoints = 0) {
  const ua = userAgent || '';
  // iPadOS reports a desktop Mac user agent; touch support gives it away.
  return /iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && maxTouchPoints > 1);
}

// 'overlay': show the image for long-press saving (only option in in-app browsers)
// 'share'  : native share sheet, whose "Save Image" puts it in Photos on iOS
// 'anchor' : regular file download (desktop, Android Chrome)
export function chooseSaveStrategy({ userAgent, maxTouchPoints = 0, canShareFiles = false }) {
  if (isInAppBrowser(userAgent)) return 'overlay';
  if (isIOS(userAgent, maxTouchPoints) && canShareFiles) return 'share';
  return 'anchor';
}

// Synchronous on purpose: iOS rejects navigator.share() once the tap's user
// activation has been spent on an await.
export function dataUrlToBlob(dataUrl) {
  const match = /^data:([^;,]*)((?:;[^;,]*)*?)(;base64)?,(.*)$/s.exec(dataUrl || '');
  if (!match) throw new TypeError('Expected a data: URL');
  const [, mime, , isBase64, payload] = match;
  const binary = isBase64 ? atob(payload) : decodeURIComponent(payload);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: mime || 'application/octet-stream' });
}
