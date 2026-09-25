import assert from 'node:assert/strict';
import test from 'node:test';

import {
  chooseSaveStrategy,
  dataUrlToBlob,
  isInAppBrowser,
  isIOS,
} from '../lib/download-image.mjs';

const UA = {
  iphoneSafari: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
  ipadOS: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15',
  macSafari: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15',
  androidChrome: 'Mozilla/5.0 (Linux; Android 15; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36',
  kakaoIOS: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 KAKAOTALK 25.7.0',
  kakaoAndroid: 'Mozilla/5.0 (Linux; Android 15; SM-S928N Build/AP3A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/140.0.0.0 Mobile Safari/537.36;KAKAOTALK 2510700',
  instagram: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 390.0.0.0',
  naverApp: 'Mozilla/5.0 (Linux; Android 15; SM-S928N Build/AP3A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/140.0.0.0 Mobile Safari/537.36 NAVER(inapp; search; 2000; 12.10.1)',
  desktopChrome: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
};

// 1x1 transparent PNG.
const PNG_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

test('dataUrlToBlob decodes a base64 PNG data URI byte-for-byte', async () => {
  const blob = dataUrlToBlob(`data:image/png;base64,${PNG_B64}`);
  assert.equal(blob.type, 'image/png');
  const bytes = Buffer.from(await blob.arrayBuffer());
  assert.deepEqual(bytes, Buffer.from(PNG_B64, 'base64'));
  assert.deepEqual([...bytes.subarray(0, 4)], [0x89, 0x50, 0x4e, 0x47]);
});

test('dataUrlToBlob rejects values that are not data URLs', () => {
  assert.throws(() => dataUrlToBlob('https://example.com/a.png'), TypeError);
  assert.throws(() => dataUrlToBlob(''), TypeError);
});

test('in-app browsers are detected, regular browsers are not', () => {
  for (const ua of [UA.kakaoIOS, UA.kakaoAndroid, UA.instagram, UA.naverApp]) {
    assert.equal(isInAppBrowser(ua), true, ua);
  }
  for (const ua of [UA.iphoneSafari, UA.androidChrome, UA.desktopChrome, UA.macSafari]) {
    assert.equal(isInAppBrowser(ua), false, ua);
  }
});

test('iOS includes iPadOS desktop user agents only when touch is present', () => {
  assert.equal(isIOS(UA.iphoneSafari), true);
  assert.equal(isIOS(UA.ipadOS, 5), true);
  assert.equal(isIOS(UA.macSafari, 0), false);
  assert.equal(isIOS(UA.androidChrome, 5), false);
});

test('save strategy per platform', () => {
  assert.equal(chooseSaveStrategy({ userAgent: UA.kakaoIOS, canShareFiles: true }), 'overlay');
  assert.equal(chooseSaveStrategy({ userAgent: UA.kakaoAndroid, maxTouchPoints: 5, canShareFiles: true }), 'overlay');
  assert.equal(chooseSaveStrategy({ userAgent: UA.iphoneSafari, maxTouchPoints: 5, canShareFiles: true }), 'share');
  assert.equal(chooseSaveStrategy({ userAgent: UA.ipadOS, maxTouchPoints: 5, canShareFiles: true }), 'share');
  // Old iOS without file sharing still gets a real download attempt.
  assert.equal(chooseSaveStrategy({ userAgent: UA.iphoneSafari, maxTouchPoints: 5, canShareFiles: false }), 'anchor');
  assert.equal(chooseSaveStrategy({ userAgent: UA.androidChrome, maxTouchPoints: 5, canShareFiles: true }), 'anchor');
  assert.equal(chooseSaveStrategy({ userAgent: UA.desktopChrome, canShareFiles: true }), 'anchor');
  assert.equal(chooseSaveStrategy({ userAgent: UA.macSafari, maxTouchPoints: 0, canShareFiles: true }), 'anchor');
});
