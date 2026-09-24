// Rendered results are always PNG, so the original extension (e.g. .jpeg)
// must not survive into the download name.
export function pngDownloadName(mode, originalName) {
  const stem = (originalName || '').replace(/\.[^./\\]+$/, '') || 'output';
  return `transposed_${mode}_${stem}.png`;
}
