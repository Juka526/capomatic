import qrcode from 'qrcode-generator';

/** Encode the exact URL locally, with a four-module quiet zone for scanning. */
export function createSupportQr(url) {
  const qr = qrcode(0, 'M');
  qr.addData(url, 'Byte');
  qr.make();
  const modules = qr.getModuleCount();
  const path = [];
  for (let row = 0; row < modules; row++) {
    for (let column = 0; column < modules; column++) {
      if (qr.isDark(row, column)) path.push(`M${column + 4},${row + 4}h1v1h-1z`);
    }
  }
  return { size: modules + 8, path: path.join('') };
}
