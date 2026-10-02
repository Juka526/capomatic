// Camera math for scripts/record-guide.mjs, kept pure so it can be tested.
// A "shot" is { cx, cy, w }: the centre and width of the visible window in CSS px
// of the recorded viewport ("screen"). Its height is always w / aspect, where
// aspect is the output video's width / height. A shot wider or taller than the
// screen shows the background around it (the wide, framed view).

export const easeInOut = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/**
 * The wide shot. "contain" shows the whole screen with `margin` (fraction of
 * its size) on every side; "width" fills the output with the screen's full
 * width (no side bars) and shows as much height as the aspect allows.
 */
export function fullShot(screen, aspect, margin, fit = "contain") {
  const w = fit === "width"
    ? screen.w * (1 + 2 * margin)
    : Math.max(screen.w * (1 + 2 * margin), screen.h * (1 + 2 * margin) * aspect);
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

// --- calm camera planning ---------------------------------------------------
// The recording logs what each scene wants to show ("intents"); planCamera()
// turns them into few, slow camera moves after the fact.

export const CALM = {
  moveSeconds: 1.0, // every move eases over this long (0.9-1.2 s)
  minHold: 2.0, // still time between two moves
  minHoldAfterResult: 2.5, // still time after a result appears
  maxMovesPerChapter: 2,
  maxZoom: { mobile: 1.25, desktop: 1.5 },
  sameFraming: 0.25, // centres closer than this share of the screen ...
  sameZoom: 1.12, // ... and zooms within this ratio: keep the framing, don't pan
};

/** Page-scroll intervals from per-frame scroll positions ({ t, y }), padded and merged. */
export function scrollIntervals(samples, { pad = 0.1, gap = 0.3 } = {}) {
  const raw = [];
  for (let i = 1; i < samples.length; i++) {
    // Screencast sends no frames while nothing changes, so a change after a long
    // gap happened just before the later frame, not during the whole gap.
    if (samples[i].y !== samples[i - 1].y) raw.push({ t0: Math.max(samples[i - 1].t, samples[i].t - 0.1), t1: samples[i].t });
  }
  const out = [];
  for (const r of raw) {
    const last = out.at(-1);
    if (last && r.t0 - last.t1 <= gap) last.t1 = Math.max(last.t1, r.t1);
    else out.push({ ...r });
  }
  return out.map((r) => ({ t0: r.t0 - pad, t1: r.t1 + pad }));
}

/** Union of interval lists, sorted and merged. */
export function mergeIntervals(...lists) {
  const all = lists.flat().slice().sort((a, b) => a.t0 - b.t0);
  const out = [];
  for (const r of all) {
    const last = out.at(-1);
    if (last && r.t0 <= last.t1) last.t1 = Math.max(last.t1, r.t1);
    else out.push({ ...r });
  }
  return out;
}

/** Two framings close enough that moving between them would only be fidgeting. */
export function similarShots(a, b, screen, rules = CALM) {
  const zoom = Math.max(a.w, b.w) / Math.min(a.w, b.w);
  return Math.abs(a.cx - b.cx) <= rules.sameFraming * screen.w
    && Math.abs(a.cy - b.cy) <= rules.sameFraming * screen.h
    && zoom <= rules.sameZoom;
}

/** How much of `rect` (CSS px²) a shot shows. */
export function visibleArea(shot, rect, aspect) {
  const h = shot.w / aspect;
  const w = Math.min(rect.x + rect.w, shot.cx + shot.w / 2) - Math.max(rect.x, shot.cx - shot.w / 2);
  const v = Math.min(rect.y + rect.h, shot.cy + h / 2) - Math.max(rect.y, shot.cy - h / 2);
  return Math.max(0, w) * Math.max(0, v);
}

/** Does `shot` show the whole rect? */
export function shotContains(shot, rect, aspect) {
  const h = shot.w / aspect;
  return rect.x >= shot.cx - shot.w / 2 - 0.5 && rect.x + rect.w <= shot.cx + shot.w / 2 + 0.5
    && rect.y >= shot.cy - h / 2 - 0.5 && rect.y + rect.h <= shot.cy + h / 2 + 0.5;
}

/**
 * Plan the camera. `intents` are { t, roi, kind: "target" | "result" | "wide", pad?, maxZoom? }
 * on the video clock; `scrolls` are { t0, t1 } page-scroll intervals; `chapters`
 * are { start, end }. Each chapter is split at scrolls into segments, and each
 * segment gets one framing (all its intents in one shot). The camera never
 * moves during a scroll, holds at least minHold (minHoldAfterResult after a
 * result), skips framings similar to the current one and moves at most
 * maxMovesPerChapter times per chapter. Returns { initial, cues }.
 */
export function planCamera({ intents, scrolls, chapters, screen, aspect, full, maxZoom, pad = 0, rules = CALM }) {
  const frame = (items) => {
    const zoomCap = items.some((i) => i.kind === "wide") ? 1 : Math.min(maxZoom, ...items.map((i) => i.maxZoom ?? maxZoom));
    const p = Math.max(...items.map((i) => i.pad ?? pad));
    return shotFor(unionRect(items.map((i) => i.roi)), { screen, aspect, full, pad: p, maxZoom: zoomCap });
  };
  const inScroll = (t) => scrolls.some((s) => t >= s.t0 && t < s.t1);
  // Stay put only if the current framing is close to the new one and moving would not
  // show more of anything wanted (an area too big for any framing still counts by how much shows).
  const stays = (f, shot) => similarShots(f.shot, shot, screen, rules)
    && f.items.every((i) => visibleArea(shot, i.roi, aspect) >= visibleArea(f.shot, i.roi, aspect) - 1);
  const cues = [];
  let initial = null, cur = null, lastMoveEnd = 0, lastResult = -Infinity;

  for (const chapter of chapters) {
    // Segments: stretches of the chapter between page scrolls, and before/after
    // the first result (a result in another area may earn the second move).
    const firstResult = intents.find((i) => i.kind === "result" && i.t >= chapter.start && i.t < chapter.end);
    const breaks = mergeIntervals(
      scrolls.filter((s) => s.t1 > chapter.start && s.t0 < chapter.end),
      firstResult ? [{ t0: firstResult.t, t1: firstResult.t }] : [],
    );
    const cuts = [chapter.start, ...breaks.flatMap((s) => [s.t0, s.t1]), chapter.end]
      .map((t) => Math.min(chapter.end, Math.max(chapter.start, t)));
    const segments = [];
    for (let i = 0; i + 1 < cuts.length; i += 2) segments.push({ t0: cuts[i], t1: cuts[i + 1], items: [] });
    for (const it of intents.filter((i) => i.t >= chapter.start && i.t < chapter.end)) {
      // An intent logged during a scroll belongs to the stretch after it.
      const seg = segments.find((s) => it.t >= s.t0 && it.t < s.t1) ?? segments.find((s) => s.t0 >= it.t) ?? segments.at(-1);
      seg.items.push(it);
    }
    let framings = segments.filter((s) => s.items.length).map((s) => ({ ...s, shot: frame(s.items) }));
    if (!initial && framings.length) { initial = framings[0].shot; cur = initial; }
    // Too many framings for the move budget: one framing that holds everything up
    // to the last stretch, then the last stretch itself.
    const distinct = framings.filter((f, i) => !stays(f, i ? framings[i - 1].shot : cur));
    if (distinct.length > rules.maxMovesPerChapter) {
      const head = framings.slice(0, -1);
      framings = [
        { ...head[0], t1: head.at(-1).t1, items: head.flatMap((f) => f.items), shot: frame(head.flatMap((f) => f.items)) },
        framings.at(-1),
      ];
    }
    let moves = 0;
    for (const f of framings) {
      const results = f.items.filter((i) => i.kind === "result").map((i) => i.t);
      if (!stays(f, cur) && moves < rules.maxMovesPerChapter) {
        const t = Math.max(f.t0, lastMoveEnd + rules.minHold, lastResult + rules.minHoldAfterResult);
        const end = t + rules.moveSeconds;
        // Never move during a scroll, and only while this stretch is still on screen.
        if (end <= f.t1 && !inScroll(t) && !inScroll(end)) {
          cues.push({ t, dur: rules.moveSeconds, shot: f.shot });
          cur = f.shot; lastMoveEnd = end; moves++;
        }
      }
      if (results.length) lastResult = Math.max(lastResult, ...results);
    }
  }
  return { initial: initial ?? full, cues };
}

/** Calmness numbers for the PR: moves, holds, durations and zoom range. */
export function cameraStats({ initial, cues, chapters, full }) {
  const perChapter = chapters.map((c) => cues.filter((q) => q.t >= c.start && q.t < c.end).length);
  const holds = cues.slice(1).map((q, i) => q.t - (cues[i].t + cues[i].dur));
  const zooms = [initial, ...cues.map((q) => q.shot)].map((s) => full.w / s.w);
  return {
    moves: cues.length,
    movesPerChapter: perChapter,
    shortestHold: holds.length ? Math.min(...holds) : null,
    shortestMove: cues.length ? Math.min(...cues.map((q) => q.dur)) : null,
    zoomRange: [Math.min(...zooms), Math.max(...zooms)],
  };
}
