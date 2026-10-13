import assert from 'node:assert/strict';
import test from 'node:test';
import jsQR from 'jsqr';
import { supportUrl } from '../lib/support-link.mjs';
import { createSupportQr } from '../lib/support-qr.mjs';

test('the generated SVG QR decodes to the exact configured support URL', () => {
  for (const configured of [
    'https://example.com/support',
    'https://example.com/support?note=coffee%20%26%20cake&amount=1000#thanks',
  ]) {
    const url = supportUrl(configured, 'web');
    const qr = createSupportQr(url);
    const scale = 6;
    const width = qr.size * scale;
    const pixels = new Uint8ClampedArray(width * width * 4).fill(255);
    for (const [, x, y] of qr.path.matchAll(/M(\d+),(\d+)h1v1h-1z/g)) {
      assert.ok(Number(x) >= 4 && Number(x) < qr.size - 4);
      assert.ok(Number(y) >= 4 && Number(y) < qr.size - 4);
      for (let dy = 0; dy < scale; dy++) {
        for (let dx = 0; dx < scale; dx++) {
          const offset = ((Number(y) * scale + dy) * width + Number(x) * scale + dx) * 4;
          pixels[offset] = pixels[offset + 1] = pixels[offset + 2] = 0;
        }
      }
    }
    const decoded = jsQR(pixels, width, width);
    assert.ok(decoded, 'QR must be readable');
    assert.equal(decoded.data, url);
  }
});
