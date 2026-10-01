// Camera math for scripts/record-guide.mjs, kept pure so it can be tested.
// A "shot" is { cx, cy, w }: the centre and width of the visible window in CSS px
// of the recorded viewport ("screen"). Its height is always w / aspect, where
// aspect is the output video's width / height. A shot wider or taller than the
// screen shows the background around it (the wide, framed view).

export const easeInOut = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** The wide shot: the whole screen with `margin` (fraction of its size) on every side. */
export function fullShot(screen, aspect, margin) {
  const w = Math.max(screen.w * (1 + 2 * margin), screen.h * (1 + 2 * margin) * aspect);
  return { cx: screen.w / 2, cy: screen.h / 2, w };
}

/**
 * Keep the window on the screen: along an axis where it is smaller than the
 * screen it may not leave it, along one where it is larger it is centred (the
 * background shows evenly). Continuous at the switch-over, so no jumps.
 */
export function clampShot(shot, screen, aspect) {
  const h = shot.w / aspect;
  const cx = shot.w <= screen.w ? clamp(shot.cx, shot.w / 2, screen.w - shot.w / 2) : screen.w / 2;
  const cy = h <= screen.h ? clamp(shot.cy, h / 2, screen.h - h / 2) : screen.h / 2;
  return { cx, cy, w: shot.w };
}

/** Smallest shot (within maxZoom of the full shot) that shows `roi` plus `pad` on each side. */
export function shotFor(roi, { screen, aspect, full, pad = 0, maxZoom = 1.8 }) {
  const needW = Math.max(roi.w + 2 * pad, (roi.h + 2 * pad) * aspect);
  const w = clamp(needW, full.w / maxZoom, full.w);
  return clampShot({ cx: roi.x + roi.w / 2, cy: roi.y + roi.h / 2, w }, screen, aspect);
}

/** Bounding box of several rects ({x, y, w, h}). */
export function unionRect(rects) {
  const x1 = Math.min(...rects.map((r) => r.x)), y1 = Math.min(...rects.map((r) => r.y));
  const x2 = Math.max(...rects.map((r) => r.x + r.w)), y2 = Math.max(...rects.map((r) => r.y + r.h));
  return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
}

/** Centre moves linearly; width moves geometrically so zooming feels even. */
export function lerpShot(a, b, k) {
  return { cx: a.cx + (b.cx - a.cx) * k, cy: a.cy + (b.cy - a.cy) * k, w: a.w * (b.w / a.w) ** k };
}

/**
 * Camera at time t. `cues` are { t, dur, shot } in time order; each starts from
 * wherever the camera is at its start, so an interrupted move never jumps.
 */
export function cameraAt(initial, cues, t, screen, aspect) {
  let from = initial, seg = null;
  for (const cue of cues) {
    if (cue.t > t) break;
    if (seg) from = lerpShot(seg.from, seg.to, easeInOut((cue.t - seg.t) / seg.dur));
    seg = { t: cue.t, dur: Math.max(cue.dur, 1e-6), from, to: cue.shot };
  }
  const shot = seg ? lerpShot(seg.from, seg.to, easeInOut((t - seg.t) / seg.dur)) : initial;
  return clampShot(shot, screen, aspect);
}

/** Map a CSS-px point of the screen to output pixels for the given shot. */
export function toOutput(pt, shot, aspect, out) {
  const left = shot.cx - shot.w / 2, top = shot.cy - shot.w / aspect / 2;
  const scale = out.w / shot.w;
  return { x: (pt.x - left) * scale, y: (pt.y - top) * scale };
}

/** Where the whole screen lands in the output, in output pixels (DPR does not matter here). */
export function screenRectOut(shot, screen, aspect, out) {
  const tl = toOutput({ x: 0, y: 0 }, shot, aspect, out);
  const scale = out.w / shot.w;
  return { x: tl.x, y: tl.y, w: screen.w * scale, h: screen.h * scale };
}

/** Pointer position at t from recorded moves { t, dur, from, to } (time order). */
export function pointerAt(start, moves, t) {
  let pos = start;
  for (const m of moves) {
    if (m.t > t) break;
    const k = easeInOut((t - m.t) / Math.max(m.dur, 1e-6));
    pos = { x: m.from.x + (m.to.x - m.from.x) * k, y: m.from.y + (m.to.y - m.from.y) * k };
  }
  return pos;
}
