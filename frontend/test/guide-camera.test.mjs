import assert from 'node:assert/strict';
import test from 'node:test';

import {
  CALM, cameraAt, cameraStats, clampShot, easeInOut, fullShot, mergeIntervals, planCamera, pointerAt, screenRectOut,
  scrollIntervals, shotContains, shotFor, toOutput, unionRect,
} from '../../scripts/guide-camera.mjs';

const desktop = { screen: { w: 1280, h: 800 }, aspect: 16 / 10, out: { w: 1280, h: 800 } };
const mobile = { screen: { w: 390, h: 844 }, aspect: 9 / 14, out: { w: 720, h: 1120 } };
const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) <= eps, `${a} != ${b}`);
const inside = (shot, { screen, aspect }) => {
  const h = shot.w / aspect;
  if (shot.w <= screen.w) assert.ok(shot.cx - shot.w / 2 >= -1e-9 && shot.cx + shot.w / 2 <= screen.w + 1e-9);
  else near(shot.cx, screen.w / 2);
  if (h <= screen.h) assert.ok(shot.cy - h / 2 >= -1e-9 && shot.cy + h / 2 <= screen.h + 1e-9);
  else near(shot.cy, screen.h / 2);
};

test('easing runs 0 to 1, monotonic and clamped', () => {
  assert.equal(easeInOut(-1), 0);
  assert.equal(easeInOut(0), 0);
  assert.equal(easeInOut(1), 1);
  assert.equal(easeInOut(2), 1);
  near(easeInOut(0.5), 0.5);
  for (let t = 0; t < 1; t += 0.01) assert.ok(easeInOut(t + 0.01) >= easeInOut(t));
});

test('full shot shows the whole screen with the margin, at the output aspect', () => {
  const d = fullShot(desktop.screen, desktop.aspect, 0.04);
  near(d.w, 1280 * 1.08);
  // Mobile is narrower than 9:14, so the height decides and the sides show background.
  const m = fullShot(mobile.screen, mobile.aspect, 0.03);
  near(m.w / mobile.aspect, 844 * 1.06);
  assert.ok(m.w > 390);
});

test('a shot never leaves the screen, and a too-wide one is centred', () => {
  for (const cfg of [desktop, mobile]) {
    for (const w of [100, 300, 389, 390, 391, 600, 1280, 1500]) {
      for (const cx of [-500, 0, 100, 640, 5000]) {
        for (const cy of [-500, 0, 400, 5000]) inside(clampShot({ cx, cy, w }, cfg.screen, cfg.aspect), cfg);
      }
    }
  }
});

test('clamping is continuous where the window matches the screen width', () => {
  const a = clampShot({ cx: 50, cy: 400, w: 1280 - 1e-6 }, desktop.screen, desktop.aspect);
  const b = clampShot({ cx: 50, cy: 400, w: 1280 + 1e-6 }, desktop.screen, desktop.aspect);
  near(a.cx, b.cx, 1e-3);
});

test('a target shot contains the target plus padding, within the zoom limit', () => {
  const full = fullShot(desktop.screen, desktop.aspect, 0.04);
  const roi = { x: 1100, y: 700, w: 60, h: 40 }; // near the corner: clamping moves the centre
  const shot = shotFor(roi, { ...desktop, full, pad: 80, maxZoom: 1.8 });
  near(shot.w, full.w / 1.8);
  const left = shot.cx - shot.w / 2, top = shot.cy - shot.w / desktop.aspect / 2;
  assert.ok(left <= roi.x && left + shot.w >= roi.x + roi.w);
  assert.ok(top <= roi.y && top + shot.w / desktop.aspect >= roi.y + roi.h);
  inside(shot, desktop);
  // A large target can't be zoomed past the full shot.
  assert.equal(shotFor({ x: 0, y: 0, w: 2000, h: 900 }, { ...desktop, full, pad: 0 }).w, full.w);
});

test('output mapping: window corners hit the output corners for any DPR', () => {
  const shot = { cx: 400, cy: 300, w: 640 };
  const tl = toOutput({ x: 80, y: 100 }, shot, desktop.aspect, desktop.out);
  const br = toOutput({ x: 720, y: 500 }, shot, desktop.aspect, desktop.out);
  near(tl.x, 0); near(tl.y, 0); near(br.x, 1280); near(br.y, 800);
  // The screen rect is in CSS px, so the source frame's DPR never enters the maths.
  const r = screenRectOut(shot, desktop.screen, desktop.aspect, desktop.out);
  near(r.x, -160); near(r.w, 2560); near(r.h, 1600);
});

test('a clicked point stays inside its element after mapping', () => {
  const full = fullShot(mobile.screen, mobile.aspect, 0.03);
  const button = { x: 300, y: 700, w: 60, h: 44 };
  const shot = shotFor(button, { ...mobile, full, pad: 40, maxZoom: 1.45 });
  const c = toOutput({ x: 330, y: 722 }, shot, mobile.aspect, mobile.out);
  const a = toOutput({ x: 300, y: 700 }, shot, mobile.aspect, mobile.out);
  const b = toOutput({ x: 360, y: 744 }, shot, mobile.aspect, mobile.out);
  assert.ok(c.x > a.x && c.x < b.x && c.y > a.y && c.y < b.y);
  assert.ok(a.x >= 0 && b.x <= mobile.out.w && a.y >= 0 && b.y <= mobile.out.h);
});

test('camera moves smoothly through cues, even when one interrupts another', () => {
  const { screen, aspect } = desktop;
  const full = fullShot(screen, aspect, 0.04);
  const zoomA = { cx: 300, cy: 300, w: 760 }, zoomB = { cx: 900, cy: 500, w: 900 };
  const cues = [{ t: 1, dur: 0.5, shot: zoomA }, { t: 1.3, dur: 0.5, shot: zoomB }, { t: 3, dur: 0.6, shot: full }];
  assert.deepEqual(cameraAt(full, cues, 0, screen, aspect), clampShot(full, screen, aspect));
  const mid = cameraAt(full, cues, 1.29, screen, aspect).w; // interrupted half-way into zoomA
  assert.ok(mid < full.w && mid > 760);
  let prev = cameraAt(full, cues, 0, screen, aspect);
  for (let t = 0; t <= 4; t += 1 / 30) {
    const cur = cameraAt(full, cues, t, screen, aspect);
    assert.ok(Math.abs(cur.cx - prev.cx) < 110 && Math.abs(cur.cy - prev.cy) < 110 && Math.abs(cur.w - prev.w) < 130, `jump at ${t}`);
    inside(cur, desktop);
    prev = cur;
  }
  near(cameraAt(full, cues, 4, screen, aspect).w, full.w);
});

test('union and pointer helpers', () => {
  assert.deepEqual(unionRect([{ x: 10, y: 20, w: 10, h: 10 }, { x: 0, y: 25, w: 5, h: 20 }]), { x: 0, y: 20, w: 20, h: 25 });
  const moves = [{ t: 1, dur: 0.5, from: { x: 0, y: 0 }, to: { x: 100, y: 50 } }];
  assert.deepEqual(pointerAt({ x: 0, y: 0 }, moves, 0.5), { x: 0, y: 0 });
  assert.deepEqual(pointerAt({ x: 0, y: 0 }, moves, 2), { x: 100, y: 50 });
  near(pointerAt({ x: 0, y: 0 }, moves, 1.25).x, 50);
});

// --- calm camera ---------------------------------------------------------------

const phone = { screen: { w: 390, h: 844 }, aspect: 9 / 15 };
const phoneFull = fullShot(phone.screen, phone.aspect, 0, 'width');
const plan = (intents, { scrolls = [], chapters = [{ start: 0, end: 30 }] } = {}) =>
  planCamera({ intents, scrolls, chapters, ...phone, full: phoneFull, maxZoom: CALM.maxZoom.mobile, pad: 16 });
const box = (x, y, w = 60, h = 44) => ({ x, y, w, h });

test('calm rules are the agreed values', () => {
  assert.ok(CALM.moveSeconds >= 0.9 && CALM.moveSeconds <= 1.2);
  assert.ok(CALM.minHold >= 2 && CALM.minHoldAfterResult >= 2.5);
  assert.equal(CALM.maxMovesPerChapter, 2);
  assert.deepEqual(CALM.maxZoom, { mobile: 1.25, desktop: 1.5 });
});

test('the mobile wide shot fills the width: no side bars', () => {
  assert.equal(phoneFull.w, 390);
  const r = screenRectOut(clampShot(phoneFull, phone.screen, phone.aspect), phone.screen, phone.aspect, { w: 720, h: 1200 });
  near(r.x, 0); near(r.w, 720);
});

test('scroll intervals come from frame scroll positions', () => {
  const samples = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 2, 2.1].map((t, i) => ({ t, y: [0, 0, 50, 120, 120, 120, 120, 300][i] }));
  assert.deepEqual(scrollIntervals(samples, { pad: 0 }), [{ t0: 0.1, t1: 0.3 }, { t0: 2, t1: 2.1 }]);
  // A change after a quiet gap (no frames) is pinned to the later frame.
  assert.deepEqual(scrollIntervals([{ t: 1, y: 0 }, { t: 4, y: 10 }], { pad: 0 }), [{ t0: 3.9, t1: 4 }]);
  assert.deepEqual(mergeIntervals([{ t0: 0, t1: 1 }], [{ t0: 0.5, t1: 2 }, { t0: 3, t1: 4 }]), [{ t0: 0, t1: 2 }, { t0: 3, t1: 4 }]);
});

test('nearby targets share one framing: no pan between a fret and the + button', () => {
  const { cues } = plan([
    { t: 1, roi: box(20, 520, 360, 80), kind: 'target' },
    { t: 4, roi: box(300, 610), kind: 'target' },
    { t: 6, roi: box(0, 400, 390, 300), kind: 'result' },
  ]);
  assert.equal(cues.length, 0);
});

test('never moves during a scroll, holds between moves, at most 2 moves per chapter', () => {
  const scrolls = [{ t0: 5, t1: 6 }, { t0: 10, t1: 11 }, { t0: 15, t1: 16 }];
  const intents = [
    { t: 1, roi: box(0, 0, 390, 300), kind: 'target' },
    { t: 7, roi: box(0, 600, 390, 244), kind: 'target' },
    { t: 12, roi: box(0, 0, 390, 200), kind: 'result' },
    { t: 17, roi: box(0, 640, 390, 200), kind: 'result' },
  ];
  const { initial, cues } = plan(intents, { scrolls });
  assert.ok(cues.length <= CALM.maxMovesPerChapter);
  for (const q of cues) {
    assert.ok(!scrolls.some((s) => q.t < s.t1 && q.t + q.dur > s.t0), `move at ${q.t} overlaps a scroll`);
    assert.ok(q.dur >= 0.9 && q.dur <= 1.2);
  }
  const stats = cameraStats({ initial, cues, chapters: [{ start: 0, end: 30 }], full: phoneFull });
  if (stats.shortestHold != null) assert.ok(stats.shortestHold >= CALM.minHold);
  assert.ok(stats.zoomRange[1] <= CALM.maxZoom.mobile + 1e-9);
});

test('waits 2.5 s after a result before moving on', () => {
  const { cues } = plan([
    { t: 0.5, roi: box(0, 0, 390, 200), kind: 'result' },
    { t: 1, roi: box(0, 700, 390, 144), kind: 'target' },
  ], { scrolls: [{ t0: 0.7, t1: 0.9 }] }); // the second target is after a scroll: its own framing
  assert.equal(cues.length, 1);
  assert.ok(cues[0].t >= 0.5 + CALM.minHoldAfterResult);
});

test('zoom stays inside the range and the framing contains its targets', () => {
  const target = box(150, 400, 40, 40);
  const { initial } = plan([{ t: 1, roi: target, kind: 'target' }]);
  assert.ok(phoneFull.w / initial.w <= CALM.maxZoom.mobile + 1e-9);
  assert.ok(shotContains(initial, target, phone.aspect));
});

test('moves when the new framing shows more of a target, even one too tall to fit', () => {
  // Current framing is bottom-aligned; the wanted area runs from near the top to the middle.
  const { initial, cues } = plan([
    { t: 0.5, roi: box(0, 300, 390, 544), kind: 'target' },
    { t: 4, roi: box(100, 60, 200, 700), kind: 'target' },
  ], { scrolls: [{ t0: 3, t1: 3.5 }] });
  assert.equal(cues.length, 1);
  assert.ok(cues[0].shot.cy < initial.cy);
});
