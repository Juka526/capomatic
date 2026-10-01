#!/usr/bin/env node
// Records the how-to guide videos by driving the real app. Re-run it whenever
// the UI changes; nothing is recorded by hand.
//
// Output, one continuous demo per device and language:
//   frontend/public/guide/{mobile,desktop}/{ko,en}/guide.mp4            H.264 yuv420p, 30 fps, faststart, no audio
//   frontend/public/guide/{mobile,desktop}/{ko,en}/guide.jpg            poster
//   frontend/public/guide/{mobile,desktop}/{ko,en}/guide.chapters.json  scene start/end times (seconds of the mp4)
//   Targets: mobile <= 1.5 MB, desktop <= 2 MB, but legibility wins: the CRF never
//   goes above the last of CRFS. Full timelines (frames, intents, scrolls, camera,
//   calmness numbers) go to tmp/guide-recording/.
//
// Local tools only (none of these are app dependencies):
//   - ffmpeg with libx264 on PATH   (brew install ffmpeg)
//   - playwright-core installed outside the app: npm install --prefix /tmp/pw playwright-core
//   - Google Chrome (override with --chrome <path>)
//
// Run:
//   1. Backend on :8011 with CORS_ORIGINS including the app origin (see CLAUDE.md).
//   2. cd frontend && NEXT_PUBLIC_API_URL=http://127.0.0.1:8011 npx next build --webpack \
//        && npx next start -H 127.0.0.1 -p 3101
//   3. PLAYWRIGHT_CORE=/tmp/pw/node_modules/playwright-core node scripts/record-guide.mjs \
//        --app http://127.0.0.1:3101 --api http://127.0.0.1:8011 [--only mobile/ko]
//
// How a video is made:
//   - The app runs untouched at a fixed viewport (no zoom or transform on the page):
//     mobile 390x844, desktop 1280x960 (4:3, so the desktop video fills the guide's
//     4:3 frame). CDP Page.startScreencast collects raw frames and page scroll positions.
//   - The whole flow (upload, capo, replace/above, fix a chord, save) is one recording.
//     Scenes log chapters, clicks and "intents" (what should be in view: a target
//     before a click, a result after it) on one clock (Node's performance.now).
//   - Afterwards planCamera() (guide-camera.mjs, tested in frontend/test/guide-camera.test.mjs)
//     turns the intents into few, slow moves: at most 2 per chapter, 1 s eases,
//     2 s holds (2.5 s after a result), none during a page scroll, zoom 1-1.25x on
//     mobile and 1-1.5x on desktop. Mobile's wide shot fills the full screen width.
//   - A Canvas compositor (a separate Chromium page) renders each 30 fps frame: the
//     screen cropped/scaled by the camera, then the cursor or tap ring at a fixed size.
//   - Input is fixtures/images/친구야.jpeg (key D). /detect is called once per run and
//     replayed through page.route after a fixed 1.2 s delay. /render hits the backend.
//   - Chapter times come from the recording log, never typed by hand. The video ends
//     on a wide hold and cuts back to the start.
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import {
  CALM, cameraAt, cameraStats, fullShot, mergeIntervals, planCamera, pointerAt, screenRectOut, scrollIntervals,
  shotContains, toOutput, unionRect,
} from "./guide-camera.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SHEET = join(ROOT, "fixtures/images/친구야.jpeg");
const OUT = join(ROOT, "frontend/public/guide");
const TIMELINES = join(ROOT, "tmp/guide-recording");
const FPS = 30;
const CRFS = [24, 26, 28, 30, 32, 34]; // first that fits the size target wins; never blurrier than the last
const DETECT_DELAY_MS = 1200;
const BACKGROUND = "#E4DED2";

const argv = process.argv.slice(2);
const opt = (name, fallback) => { const i = argv.indexOf(`--${name}`); return i >= 0 ? argv[i + 1] : fallback; };
const APP = opt("app", "http://127.0.0.1:3101");
const API = opt("api", "http://127.0.0.1:8011");
const CHROME = opt("chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome");
const ONLY = opt("only", "").split("/").filter(Boolean); // device[/lang]

const { chromium } = await import(process.env.PLAYWRIGHT_CORE ? join(process.env.PLAYWRIGHT_CORE, "index.mjs") : "playwright-core");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => performance.now() / 1000; // the one clock for actions, intents and frames

const DEVICES = {
  mobile: {
    context: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true },
    out: { w: 720, h: 1200 }, // 9:15, the guide's mobile frame
    margin: 0, fit: "width", maxZoom: CALM.maxZoom.mobile, pad: 16, radius: 0, maxBytes: 1.5 * 1024 * 1024,
  },
  desktop: {
    context: { viewport: { width: 1280, height: 960 }, deviceScaleFactor: 2 },
    out: { w: 1280, h: 960 }, // 4:3, the guide's desktop frame
    margin: 0.02, fit: "contain", maxZoom: CALM.maxZoom.desktop, pad: 60, radius: 12, maxBytes: 2 * 1024 * 1024,
  },
};
const POINTER_MOVE = 0.7; // seconds for the desktop pointer to travel to a target
const TAP_SLOW = 1.35; // mobile tap ring runs this much slower than a real tap, so it reads

const L = {
  ko: {
    busy: ["업데이트 중", "렌더링 중"], above: "위에", replace: "교체",
    original: "원본 보기", rendered: "결과 보기", capoUp: "카포 한 프렛 올리기",
    fret: (n) => `카포 ${n}프렛 선택`,
  },
  en: {
    busy: ["Updating", "Rendering"], above: "Above", replace: "Replace",
    original: "View Original", rendered: "View Rendered", capoUp: "Move capo up one fret",
    fret: (n) => `Select capo fret ${n}`,
  },
};

// --- recording ------------------------------------------------------------
/** Per-recording log on the now() clock: chapters, intents, clicks, pointer moves, scrolls. */
function makeTimeline(device, page) {
  const d = DEVICES[device];
  const vp = page.viewportSize();
  const screen = { w: vp.width, h: vp.height };
  const aspect = d.out.w / d.out.h;
  const full = fullShot(screen, aspect, d.margin, d.fit);
  const start = { x: screen.w * 0.7, y: screen.h * 0.62 };
  const tl = {
    device, screen, aspect, full, chapters: [], intents: [], clicks: [], moves: [], scrolls: [],
    pointer: start, pointerStart: start,
    /** What should be in view now: a target before a click, a result after it, or the wide shot. */
    want(roi, kind, o = {}) { tl.intents.push({ t: now(), roi, kind, ...o }); if (kind === "result") tl.mark("result"); },
    move(to, dur = POINTER_MOVE) { tl.moves.push({ t: now(), dur, from: tl.pointer, to }); tl.pointer = to; },
    click(at) { tl.clicks.push({ t: now(), x: at.x, y: at.y }); tl.mark("click"); },
    chapter(id) { tl.chapters.push({ id, t: now(), events: {} }); },
    /** First time a scene reaches `name` (click, result). */
    mark(name) { const c = tl.chapters.at(-1); if (c && c.events[name] == null) c.events[name] = now(); },
  };
  return tl;
}

async function rectOf(target) {
  if (!target.boundingBox) return target; // already a rect
  const b = await target.boundingBox();
  if (!b) throw new Error("target has no box");
  return { x: b.x, y: b.y, w: b.width, h: b.height };
}

const unionOf = async (targets) => unionRect(await Promise.all(targets.map(rectOf)));

async function waitScrollStable(page) {
  let last = -1, same = 0;
  while (same < 3) {
    const y = await page.evaluate(() => scrollY);
    same = y === last ? same + 1 : 0;
    last = y;
    await sleep(70);
  }
}

/** Run a scroll and log it, so the camera never moves while the page moves. */
async function scrolling(page, tl, fn) {
  const t0 = now();
  await fn();
  await sleep(150);
  await waitScrollStable(page);
  tl.scrolls.push({ t0, t1: now() });
}

/** Log a result that is now on screen, then let it be read. */
async function result(tl, targets, holdMs, o = {}) {
  tl.want(await unionOf(targets), "result", o);
  await sleep(holdMs);
}

/** Bring an element on screen. */
async function reveal(page, tl, locator, block = "center") {
  const inView = await locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return r.top >= 70 && r.bottom <= window.innerHeight - 10;
  });
  if (!inView) await scrolling(page, tl, () => locator.evaluate((el, b) => el.scrollIntoView({ behavior: "smooth", block: b }), block));
}

/**
 * Log the target (plus `context`) as wanted in view, bring the pointer to it,
 * then click/tap for real. `point` overrides the click position (CSS px).
 */
async function act(page, tl, target, { context = [], point, pad, maxZoom } = {}) {
  if (target.boundingBox) await reveal(page, tl, target);
  const box = await rectOf(target); // read after any scroll has settled
  const at = point ?? { x: box.x + box.w / 2, y: box.y + box.h / 2 };
  tl.want(await unionOf([box, ...context]), "target", { pad, maxZoom });
  if (tl.device === "desktop") {
    tl.move(at);
    await sleep(POINTER_MOVE * 1000 + 120);
    tl.click(at);
    await page.mouse.click(at.x, at.y);
  } else {
    await sleep(400);
    tl.click(at); // the ring presses onto the spot, then the finger "lands"
    await sleep(220 * TAP_SLOW);
    await page.touchscreen.tap(at.x, at.y);
  }
  return at;
}

// --- capture --------------------------------------------------------------
/**
 * Screencast timestamps are browser wall-clock seconds. They are mapped onto
 * now() with the smallest observed (arrival - timestamp) offset, i.e. the
 * least-delayed delivery, so frames line up with the logged actions. Each frame
 * also carries the page scroll position, which reveals the app's own scrolling.
 */
async function startCapture(page) {
  const cdp = await page.context().newCDPSession(page);
  const frames = [];
  cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    frames.push({ ts: metadata.timestamp, arrived: now(), y: metadata.scrollOffsetY, buf: Buffer.from(data, "base64") });
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
  });
  const { width, height } = page.viewportSize();
  const dpr = await page.evaluate(() => devicePixelRatio);
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 95, everyNthFrame: 1, maxWidth: width * dpr, maxHeight: height * dpr });
  const started = now();
  return async () => {
    const ended = now();
    await cdp.send("Page.stopScreencast");
    await cdp.detach();
    if (!frames.length) throw new Error("no frames captured");
    const offset = Math.min(...frames.map((f) => f.arrived - f.ts));
    for (const f of frames) f.t = f.ts + offset;
    return { frames, started, ended };
  };
}

// --- compositing ------------------------------------------------------------
const COMPOSITOR_HTML = (w, h) => `<!doctype html><body style="margin:0"><canvas id="c" width="${w}" height="${h}"></canvas><script>
const c = document.getElementById("c"), g = c.getContext("2d");
let img = null;
const ARROW = new Path2D("M3 2l18 16.5-8.2.8 4.8 9.3-3.6 1.8-4.8-9.3L3 27z");
window.setSource = async (b64) => { img = await createImageBitmap(await (await fetch("data:image/jpeg;base64," + b64)).blob()); };
const round = (x, y, w, h, r) => { g.beginPath(); g.roundRect(x, y, w, h, r); };
window.draw = ({ bg, s, radius, cursor, ripples, rings }) => {
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.fillStyle = bg; g.fillRect(0, 0, ${w}, ${h});
  g.save(); g.shadowColor = "rgba(40,30,10,.22)"; g.shadowBlur = 28; g.shadowOffsetY = 8;
  round(s.x, s.y, s.w, s.h, radius); g.fillStyle = "#fff"; g.fill(); g.restore();
  g.save(); round(s.x, s.y, s.w, s.h, radius); g.clip(); g.drawImage(img, s.x, s.y, s.w, s.h); g.restore();
  for (const r of ripples) { g.beginPath(); g.arc(r.x, r.y, r.r, 0, 7); g.fillStyle = "rgba(224,93,0," + r.a + ")"; g.fill(); }
  for (const r of rings) {
    g.save(); g.globalAlpha = r.a; g.beginPath(); g.arc(r.x, r.y, r.r, 0, 7);
    g.fillStyle = "rgba(26,26,46,.24)"; g.fill(); g.lineWidth = 3; g.strokeStyle = "rgba(255,255,255,.95)";
    g.shadowColor = "rgba(0,0,0,.3)"; g.shadowBlur = 8; g.stroke(); g.restore();
  }
  if (cursor) {
    g.save(); g.translate(cursor.x, cursor.y); g.scale(cursor.k, cursor.k); g.translate(-3, -3);
    g.shadowColor = "rgba(0,0,0,.35)"; g.shadowBlur = 5; g.shadowOffsetY = 2;
    g.fillStyle = "#fff"; g.fill(ARROW); g.shadowColor = "transparent";
    g.lineWidth = 1.6; g.lineJoin = "round"; g.strokeStyle = "#111"; g.stroke(ARROW); g.restore();
  }
  return c.toDataURL("image/jpeg", 0.95);
};
</script>`;

/** Pointer/tap decorations at time t (video clock), in output pixels (a fixed size whatever the zoom). */
function decorations(rec, t, shot, out) {
  const map = (p) => toOutput(p, shot, rec.aspect, out);
  const ripples = [], rings = [];
  if (rec.device === "desktop") {
    let k = 1;
    for (const c of rec.clicks) {
      const dt = t - c.t;
      if (dt >= 0 && dt < 0.22) k = 1 - 0.16 * Math.sin(Math.PI * dt / 0.22);
      if (dt >= 0 && dt < 0.5) ripples.push({ ...map(c), r: 8 + 22 * (dt / 0.5), a: +(0.4 * (1 - dt / 0.5)).toFixed(3) });
    }
    return { cursor: { ...map(pointerAt(rec.pointerStart, rec.moves, t)), k }, ripples, rings };
  }
  for (const c of rec.clicks) {
    const dt = (t - c.t) / TAP_SLOW;
    if (dt < 0 || dt > 0.62) continue;
    // Appear, press down onto the spot, then spread out and fade.
    const [r, a] = dt < 0.16 ? [26 - 4 * (dt / 0.16), dt / 0.16]
      : dt < 0.3 ? [22 - 6 * ((dt - 0.16) / 0.14), 1]
      : [16 + 20 * ((dt - 0.3) / 0.32), 1 - (dt - 0.3) / 0.32];
    rings.push({ ...map(c), r, a: +a.toFixed(3) });
  }
  return { cursor: null, ripples, rings };
}

async function composite(compositor, rec, frames, count, dir) {
  const d = DEVICES[rec.device];
  const log = [];
  let j = 0, loaded = -1;
  for (let i = 0; i < count; i++) {
    const t = i / FPS;
    while (j + 1 < frames.length && frames[j + 1].t <= t) j++;
    if (j !== loaded) { await compositor.evaluate((b64) => window.setSource(b64), frames[j].buf.toString("base64")); loaded = j; }
    const shot = cameraAt(rec.initial, rec.cues, t, rec.screen, rec.aspect);
    const s = screenRectOut(shot, rec.screen, rec.aspect, d.out);
    const radius = d.radius * (s.w / rec.screen.w);
    const url = await compositor.evaluate((a) => window.draw(a), { bg: BACKGROUND, s, radius, ...decorations(rec, t, shot, d.out) });
    writeFileSync(join(dir, String(i).padStart(5, "0") + ".jpg"), Buffer.from(url.split(",")[1], "base64"));
    log.push({ i, t: +t.toFixed(4), source: j, shot: { cx: +shot.cx.toFixed(2), cy: +shot.cy.toFixed(2), w: +shot.w.toFixed(2) } });
  }
  return log;
}

function ffmpeg(args) {
  const r = spawnSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args], { stdio: "inherit" });
  if (r.status !== 0) throw new Error("ffmpeg failed");
}

function encode(dir, count, posterIndex, target, maxBytes) {
  let crf, size;
  for (crf of CRFS) {
    ffmpeg(["-framerate", `${FPS}`, "-i", join(dir, "%05d.jpg"), "-c:v", "libx264", "-preset", "veryslow", "-crf", `${crf}`,
      "-vf", "scale=out_range=tv:flags=lanczos,format=yuv420p", "-color_range", "tv", "-profile:v", "high", "-r", `${FPS}`, "-movflags", "+faststart", "-an", `${target}.mp4`]);
    size = statSync(`${target}.mp4`).size;
    if (size <= maxBytes) break;
  }
  ffmpeg(["-i", join(dir, String(posterIndex).padStart(5, "0") + ".jpg"), "-q:v", "3", `${target}.jpg`]);
  return { seconds: +(count / FPS).toFixed(2), crf, size, poster: statSync(`${target}.jpg`).size };
}

// --- driving the app -------------------------------------------------------
const shown = (page, selector) => page.locator(selector).filter({ visible: true }).first();
const button = (page, text) => page.locator("button").filter({ hasText: text }).filter({ visible: true }).first();
const viewport = (page) => { const v = page.viewportSize(); return { x: 0, y: 0, w: v.width, h: v.height }; };

async function waitIdle(page, lang) {
  await page.waitForFunction((busy) => {
    const text = document.body.innerText;
    if (busy.some((b) => text.includes(b))) return false;
    const spin = document.querySelector(".m-spin");
    if (spin && spin.getClientRects().length) return false;
    return [...document.images].filter((i) => i.getClientRects().length && i.getBoundingClientRect().width > 100)
      .every((i) => i.complete && i.naturalWidth > 0);
  }, L[lang].busy, { timeout: 120000, polling: 100 });
}

const waitDetected = (page) => page.waitForFunction(
  () => document.body.innerText.includes("✓") && !document.querySelector(".m-scan"), null, { timeout: 60000, polling: 100 });

/** The part of an element inside the viewport, at most maxH tall from its visible top. */
async function onScreen(page, locator, maxH = Infinity) {
  const r = await rectOf(locator);
  const vh = page.viewportSize().height;
  const y = Math.max(r.y, 0);
  return { x: r.x, y, w: r.w, h: Math.max(1, Math.min(r.y + r.h, vh, y + maxH) - y) };
}

/** The bottom of the mobile sheet area plus the board: where changed chords and the capo show. */
async function boardAndSheetEnd(page, sheetPart = 200) {
  const board = await rectOf(shown(page, ".m-board"));
  return { x: 0, y: Math.max(0, board.y - sheetPart), w: board.w, h: board.h + Math.min(sheetPart, board.y) };
}

// One scene per guide step, played back to back in one recording. Pauses are
// long enough for the camera's holds; readability matters more than length.
const SCENES = [
  // 1. Upload -> pick the photo -> scan -> "✓ detected key D"
  async function upload(page, tl) {
    tl.chapter("upload");
    tl.want(viewport(page), "wide");
    await sleep(900);
    const target = shown(page, tl.device === "mobile" ? ".m-drop" : ".primary-upload-cta");
    const chooser = page.waitForEvent("filechooser");
    await act(page, tl, target);
    await (await chooser).setFiles(SHEET); // the OS picker never shows; the app sees a picked file
    await waitDetected(page);
    await sleep(300);
    if (tl.device === "mobile") await result(tl, [shown(page, ".m-bhead"), await boardAndSheetEnd(page)], 2600);
    else await result(tl, [shown(page, ".active-info-bar"), shown(page, ".fretboard-section")], 2600);
  },
  // 2. Fret 2 -> the changed sheet -> "+" moves the capo up one fret.
  async function capo(page, tl, lang) {
    tl.chapter("capo");
    const fret2 = shown(page, `[aria-label="${L[lang].fret(2)}"]`);
    const plus = shown(page, `[aria-label="${L[lang].capoUp}"]`);
    if (tl.device === "mobile") {
      const area = [shown(page, ".m-fretbox"), shown(page, ".m-controls")];
      await act(page, tl, fret2, { context: area });
      await waitIdle(page, lang);
      await result(tl, [await boardAndSheetEnd(page)], 2600);
      await act(page, tl, plus, { context: area });
      await waitIdle(page, lang);
      await result(tl, [await boardAndSheetEnd(page)], 2600);
    } else {
      // The app scrolls to the result once the first render lands; the camera holds still meanwhile.
      await act(page, tl, fret2, { context: [shown(page, ".transpose-selector")] });
      const t0 = now();
      await waitIdle(page, lang);
      await sleep(400);
      await waitScrollStable(page);
      tl.scrolls.push({ t0, t1: now() });
      await result(tl, [await onScreen(page, shown(page, ".result-card"), 560)], 2400);
      await act(page, tl, plus, { context: [shown(page, ".transpose-selector")] });
      await waitIdle(page, lang);
      await sleep(200);
      await result(tl, [shown(page, ".transpose-selector"), await onScreen(page, shown(page, ".result-card"), 420)], 2600);
    }
  },
  // 3. Above -> Replace -> a look at the original -> back to the result. The sheet stays in frame.
  async function mode(page, tl, lang) {
    tl.chapter("mode");
    let area;
    if (tl.device === "mobile") area = [await boardAndSheetEnd(page, 300)];
    else {
      const card = shown(page, ".result-card");
      await scrolling(page, tl, () => card.evaluate((el) => window.scrollBy({ top: el.getBoundingClientRect().top - 64, behavior: "smooth" })));
      area = [await onScreen(page, card, 640)];
    }
    await sleep(600);
    await act(page, tl, button(page, new RegExp(`^${L[lang].above}$`)), { context: area });
    await waitIdle(page, lang);
    await result(tl, area, 1600);
    await act(page, tl, button(page, new RegExp(`^${L[lang].replace}$`)), { context: area });
    await waitIdle(page, lang);
    await sleep(1200);
    await act(page, tl, button(page, L[lang].original), { context: area });
    await sleep(1400);
    await act(page, tl, button(page, L[lang].rendered), { context: area });
    await sleep(1100);
  },
  // 4. Delete a misread chord, place one on the sheet, re-render and show it there.
  async function fix(page, tl, lang) {
    tl.chapter("fix");
    const editor = shown(page, ".chord-editor");
    await reveal(page, tl, editor);
    await sleep(600);
    await act(page, tl, page.locator(".chord-editor span > button").filter({ visible: true }).first(), { context: [editor] });
    await sleep(900);
    await act(page, tl, button(page, "+ Add at position"), { context: [editor] });
    await sleep(500);
    const sheet = shown(page, tl.device === "mobile" ? ".m-page img" : ".result-card img");
    await scrolling(page, tl, () => sheet.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "start" })));
    await sleep(600);
    const box = await rectOf(sheet);
    const spot = { x: box.x + box.w * 0.6, y: Math.max(box.y + box.h * 0.13, 150) };
    const spotOnPage = { x: spot.x, y: spot.y + await page.evaluate(() => scrollY) };
    const spotRect = { x: spot.x - 80, y: spot.y - 60, w: 160, h: 120 };
    await act(page, tl, spotRect, { point: spot });
    await sleep(500);
    const popup = page.locator("div").filter({ has: page.locator("input[placeholder='e.g. Dm7']") }).last();
    tl.want(await unionOf([popup, spotRect]), "target");
    await sleep(400);
    await page.keyboard.type("Em7", { delay: 180 });
    await sleep(500);
    await act(page, tl, button(page, /^Add$/), { context: [popup] });
    await sleep(700);
    await act(page, tl, button(page, "Re-render with edits"), { context: [editor] });
    await waitIdle(page, lang);
    await sleep(300);
    // Show the new chord where it was placed on the sheet.
    await scrolling(page, tl, () => page.evaluate((y) => window.scrollTo({ top: Math.max(0, y - innerHeight * 0.35), behavior: "smooth" }), spotOnPage.y));
    const y = spotOnPage.y - await page.evaluate(() => scrollY);
    await result(tl, [{ x: spot.x - 120, y: y - 80, w: 240, h: 160 }], 2600);
  },
  // 5. PNG download. Desktop: Chrome's download indicator once Playwright sees the real
  // download. Mobile: only the tap; iOS's share sheet can't be automated, so the step
  // text tells iPhone users to choose "Save Image" there rather than faking it here.
  async function save(page, tl) {
    tl.chapter("save");
    if (tl.device === "mobile") await scrolling(page, tl, () => page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" })));
    await sleep(600);
    const png = button(page, "PNG");
    if (tl.device === "mobile") {
      await act(page, tl, png, { context: [shown(page, ".m-acts")] });
      await result(tl, [await boardAndSheetEnd(page)], 2600);
    } else {
      const download = page.waitForEvent("download");
      await act(page, tl, png);
      const name = (await download).suggestedFilename();
      await page.evaluate((n) => window.__rec.downloadBubble(n), name);
      await sleep(200);
      await result(tl, [png, page.locator("#__rec_bubble")], 2600);
    }
    // Outro: back to the top of the result, wide, hold; then the loop cuts to the start.
    await scrolling(page, tl, () => page.evaluate(() => { document.getElementById("__rec_bubble")?.remove(); window.scrollTo({ top: 0, behavior: "smooth" }); }));
    tl.want(viewport(page), "wide");
    await sleep(2000);
  },
];

// Chrome's download indicator, drawn only after Playwright saw the real download.
const DOWNLOAD_BUBBLE = String.raw`
window.__rec = {
  downloadBubble(name) {
    const b = document.createElement("div");
    b.id = "__rec_bubble";
    b.style.cssText = "position:fixed;right:18px;top:62px;width:300px;padding:12px 14px;border-radius:12px;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,.22);display:flex;gap:10px;align-items:center;font:500 13px -apple-system,'Apple SD Gothic Neo',sans-serif;color:#1a1a2e;z-index:2147483647;pointer-events:none";
    b.innerHTML = '<div style="width:32px;height:32px;border-radius:8px;background:#e8f0fe;display:grid;place-items:center;flex:none"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1a73e8" stroke-width="2.2" stroke-linecap="round"><path d="M12 4v11m0 0l-4.5-4.5M12 15l4.5-4.5M5 20h14"/></svg></div><div style="min-width:0"><div class="n" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600"></div><div style="color:#5f6368;font-size:12px;margin-top:2px">✓ Done</div></div>';
    b.querySelector(".n").textContent = name;
    document.documentElement.appendChild(b);
    b.animate([{ opacity: 0, transform: "translateY(-8px)" }, { opacity: 1, transform: "none" }], { duration: 220, fill: "both" });
  },
};
`;

// --- main ----------------------------------------------------------------
const form = new FormData();
form.append("image", new Blob([readFileSync(SHEET)], { type: "image/jpeg" }), "친구야.jpeg");
const res = await fetch(`${API}/detect`, { method: "POST", body: form });
if (!res.ok) throw new Error(`/detect failed: ${res.status}`);
const detectBody = await res.text();
console.log("detected key", JSON.parse(detectBody).original_key);

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const compositors = {};
for (const [device, d] of Object.entries(DEVICES)) {
  const ctx = await browser.newContext({ viewport: { width: d.out.w, height: d.out.h }, deviceScaleFactor: 1 });
  compositors[device] = await ctx.newPage();
  await compositors[device].setContent(COMPOSITOR_HTML(d.out.w, d.out.h));
}
mkdirSync(TIMELINES, { recursive: true });

for (const device of ["mobile", "desktop"]) {
  for (const lang of ["ko", "en"]) {
    if ((ONLY[0] && ONLY[0] !== device) || (ONLY[1] && ONLY[1] !== lang)) continue;
    const d = DEVICES[device];
    const context = await browser.newContext({ ...d.context, acceptDownloads: true, reducedMotion: "reduce" });
    // The guide must not open over its own recording; reduced motion keeps the logo still.
    await context.addInitScript(() => { try { localStorage.setItem("tc-guide-dismissed", "1"); } catch {} });
    await context.addInitScript(DOWNLOAD_BUBBLE);
    await context.route(/\/detect$/, async (route) => {
      await sleep(DETECT_DELAY_MS);
      await route.fulfill({ status: 200, contentType: "application/json", body: detectBody, headers: { "access-control-allow-origin": "*" } });
    });
    const page = await context.newPage();
    await page.goto(`${APP}/`, { waitUntil: "networkidle" });
    // Switch language with the app's own KO/EN toggle.
    await shown(page, `button[aria-label="${lang === "ko" ? "한국어 KO" : "English EN"}"]`).click();
    await sleep(400);
    const tl = makeTimeline(device, page);
    if (device === "desktop") await page.mouse.move(tl.pointer.x, tl.pointer.y);
    await sleep(400);
    const stop = await startCapture(page);
    for (const scene of SCENES) await scene(page, tl, lang);
    const captured = await stop();
    await context.close();

    // Everything onto the video clock (seconds from the first output frame).
    const count = Math.round((captured.ended - captured.started) * FPS);
    const duration = count / FPS;
    const rel = (t) => t - captured.started;
    const snap = (t) => +Math.min(duration, Math.max(0, Math.round(rel(t) * FPS) / FPS)).toFixed(3);
    const frames = captured.frames.map((f) => ({ ...f, t: rel(f.t) }));
    const chapters = tl.chapters.map((c, i) => ({
      id: c.id,
      start: i === 0 ? 0 : snap(c.t),
      end: i + 1 < tl.chapters.length ? snap(tl.chapters[i + 1].t) : +duration.toFixed(3),
      events: Object.fromEntries(Object.entries(c.events).map(([k, t]) => [k, snap(t)])),
    }));
    const intents = tl.intents.map((i) => ({ ...i, t: rel(i.t) }));
    const scrolls = mergeIntervals(
      scrollIntervals(frames.map((f) => ({ t: f.t, y: f.y }))),
      tl.scrolls.map((s) => ({ t0: rel(s.t0), t1: rel(s.t1) })),
    );
    const { initial, cues } = planCamera({
      intents, scrolls, chapters, screen: tl.screen, aspect: tl.aspect, full: tl.full, maxZoom: d.maxZoom, pad: d.pad,
    });
    const rec = {
      device, screen: tl.screen, aspect: tl.aspect, initial, cues,
      clicks: tl.clicks.map((c) => ({ ...c, t: rel(c.t) })),
      moves: tl.moves.map((m) => ({ ...m, t: rel(m.t) })), pointerStart: tl.pointerStart,
    };
    const stats = cameraStats({ initial, cues, chapters, full: tl.full });
    // Every click must land inside the frame.
    stats.clicksOutOfFrame = rec.clicks.filter((c) => !shotContains(cameraAt(initial, cues, c.t, tl.screen, tl.aspect), { x: c.x, y: c.y, w: 1, h: 1 }, tl.aspect)).length;

    const dir = mkdtempSync(join(tmpdir(), "guide-frames-"));
    const log = await composite(compositors[device], rec, frames, count, dir);
    const outDir = join(OUT, device, lang);
    mkdirSync(outDir, { recursive: true });
    // Poster: the opening shot, which is what step 1's text describes.
    const r = encode(dir, count, Math.round(0.3 * FPS), join(outDir, "guide"), d.maxBytes);
    writeFileSync(join(outDir, "guide.chapters.json"), JSON.stringify({ duration: +duration.toFixed(3), chapters }, null, 2) + "\n");
    if (process.env.KEEP_FRAMES) console.log("frames kept in", dir); else rmSync(dir, { recursive: true, force: true });
    writeFileSync(join(TIMELINES, `${device}-${lang}.json`), JSON.stringify({
      device, lang, fps: FPS, screen: tl.screen, out: d.out, full: tl.full, rules: CALM, chapters, stats,
      intents, scrolls, initial, cues, clicks: rec.clicks, moves: rec.moves,
      sourceFrames: frames.map((f) => ({ t: +f.t.toFixed(4), y: f.y })), frames: log,
    }, null, 1));
    const f2 = (n) => (n == null ? "-" : n.toFixed(2));
    console.log(`${device}/${lang}  ${r.seconds}s  mp4 ${(r.size / 1024) | 0}KB crf${r.crf}  jpg ${(r.poster / 1024) | 0}KB  chapters ${chapters.map((c) => c.start.toFixed(2)).join(" ")}`
      + `  | moves ${stats.moves} [${stats.movesPerChapter.join(",")}] hold>=${f2(stats.shortestHold)}s move>=${f2(stats.shortestMove)}s zoom ${f2(stats.zoomRange[0])}-${f2(stats.zoomRange[1])}x clicksOut ${stats.clicksOutOfFrame}`);
  }
}
await browser.close();
