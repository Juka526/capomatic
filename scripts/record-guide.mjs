#!/usr/bin/env node
// Records the how-to guide videos by driving the real app. Re-run it whenever
// the UI changes; nothing is recorded by hand.
//
// Output, one continuous demo per device and language:
//   frontend/public/guide/{mobile,desktop}/{ko,en}/guide.mp4            H.264 yuv420p, 30 fps, faststart, no audio
//   frontend/public/guide/{mobile,desktop}/{ko,en}/guide.jpg            poster
//   frontend/public/guide/{mobile,desktop}/{ko,en}/guide.chapters.json  scene start/end times (seconds of the mp4)
//   Target <= 1.5 MB per video, but legibility wins: the CRF never goes above the last of CRFS.
//   Full timelines (frame times, camera, actions) go to tmp/guide-recording/.
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
// How a clip is made:
//   - The app runs untouched at a fixed viewport (no zoom or transform on the page).
//     CDP Page.startScreencast collects raw frames while the script drives it.
//   - Every action logs what it did on one clock (Node's performance.now): pointer
//     moves, clicks/taps and camera cues (zoom to the target before a click, to the
//     result after it, wide before any scroll, wide at the end). Screencast
//     timestamps are converted onto that clock (see startCapture).
//   - A Canvas compositor (a separate Chromium page) renders each 30 fps output
//     frame: background, the screen cropped/scaled by the camera, then the cursor
//     or tap ring at a fixed output size. The camera maths is in guide-camera.mjs
//     (tested in frontend/test/guide-camera.test.mjs).
//   - Input is fixtures/images/친구야.jpeg (key D). /detect is called once per run
//     (detection ids live in the backend's memory) and every recording replays that
//     response through page.route after a fixed 1.2 s delay. /render hits the backend.
//   - The whole flow (upload, capo, replace/above, fix a chord, save) is one
//     recording. Each scene logs its start, key click and result; chapter times
//     in guide.chapters.json come from that log, never typed by hand.
//   - The video opens and closes on a wide shot, so the loop is a plain cut.
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { cameraAt, fullShot, pointerAt, screenRectOut, shotFor, toOutput, unionRect } from "./guide-camera.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SHEET = join(ROOT, "fixtures/images/친구야.jpeg");
const OUT = join(ROOT, "frontend/public/guide");
const TIMELINES = join(ROOT, "tmp/guide-recording");
const FPS = 30;
const MAX_BYTES = 1.5 * 1024 * 1024;
const CRFS = [24, 26, 28, 30, 32, 34]; // first that fits MAX_BYTES wins; never blurrier than the last
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
const now = () => performance.now() / 1000; // the one clock for actions, camera and frames

// Camera starting values; scenes tune them through focus()/act() options.
const DEVICES = {
  mobile: {
    context: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true },
    out: { w: 720, h: 1120 }, // 9:14
    margin: 0.025, maxZoom: 1.45, pad: 16, radius: 26,
  },
  desktop: {
    context: { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2 },
    out: { w: 1280, h: 800 }, // 16:10
    margin: 0.04, maxZoom: 1.8, pad: 80, radius: 12,
  },
};
const MOVE = 0.55; // seconds for a camera move, and for the pointer travelling with it

const L = {
  ko: {
    busy: ["업데이트 중", "렌더링 중"], above: "위에", replace: "교체",
    original: "원본 보기", rendered: "결과 보기", semitoneDown: "반음 내리기", capoUp: "카포 한 프렛 올리기",
    fret: (n) => `카포 ${n}프렛 선택`,
  },
  en: {
    busy: ["Updating", "Rendering"], above: "Above", replace: "Replace",
    original: "View Original", rendered: "View Rendered", semitoneDown: "Transpose down one semitone", capoUp: "Move capo up one fret",
    fret: (n) => `Select capo fret ${n}`,
  },
};

// --- recording ------------------------------------------------------------
/** Per-clip log of everything the compositor needs, all on the now() clock. */
function makeTimeline(device, page) {
  const d = DEVICES[device];
  const vp = page.viewportSize();
  const screen = { w: vp.width, h: vp.height };
  const aspect = d.out.w / d.out.h;
  const full = fullShot(screen, aspect, d.margin);
  const start = { x: screen.w * 0.7, y: screen.h * 0.62 };
  const tl = {
    device, screen, aspect, full, cues: [], moves: [], clicks: [], pointer: start, pointerStart: start, chapters: [],
    cam(shot, dur = MOVE) { tl.cues.push({ t: now(), dur, shot }); },
    wide(dur = MOVE) { tl.cam(full, dur); },
    shotFor(roi, o = {}) { return shotFor(roi, { screen, aspect, full, pad: o.pad ?? d.pad, maxZoom: o.maxZoom ?? d.maxZoom }); },
    move(to, dur = MOVE) { tl.moves.push({ t: now(), dur, from: tl.pointer, to }); tl.pointer = to; },
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

async function waitScrollStable(page) {
  let last = -1, same = 0;
  while (same < 3) {
    const y = await page.evaluate(() => scrollY);
    same = y === last ? same + 1 : 0;
    last = y;
    await sleep(70);
  }
}

/** Frame a set of elements/rects (usually the result of an action). */
async function focus(tl, targets, o = {}) {
  const rects = await Promise.all(targets.map(rectOf));
  tl.cam(tl.shotFor(unionRect(rects), o), o.dur ?? MOVE);
  await sleep((o.dur ?? MOVE) * 1000);
}

/** Bring an element on screen. The camera goes wide first so it never chases a scroll. */
async function reveal(page, tl, locator, block = "center") {
  const inView = await locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return r.top >= 70 && r.bottom <= window.innerHeight - 10;
  });
  if (inView) return;
  tl.wide(0.45);
  await sleep(450);
  await locator.evaluate((el, b) => el.scrollIntoView({ behavior: "smooth", block: b }), block);
  await sleep(150);
  await waitScrollStable(page);
}

/** Scroll so an element's top sits just under the desktop nav (camera wide first). */
async function alignTop(page, tl, locator, offset = 64) {
  tl.wide(0.45);
  await sleep(450);
  await locator.evaluate((el, o) => window.scrollBy({ top: el.getBoundingClientRect().top - o, behavior: "smooth" }), offset);
  await sleep(150);
  await waitScrollStable(page);
}

/**
 * Frame the target (plus `context`) while the pointer travels to it, then
 * click/tap for real. `point` overrides the click position (CSS px).
 */
async function act(page, tl, target, { context = [], point, pad, maxZoom, camera = true } = {}) {
  if (target.boundingBox) await reveal(page, tl, target);
  const box = await rectOf(target); // read after any scroll has settled
  const at = point ?? { x: box.x + box.w / 2, y: box.y + box.h / 2 };
  const rects = [box, ...(await Promise.all(context.map(rectOf)))];
  if (camera) tl.cam(tl.shotFor(unionRect(rects), { pad, maxZoom }));
  if (tl.device === "desktop") {
    tl.move(at);
    await sleep(MOVE * 1000 + 80);
    tl.click(at);
    await page.mouse.click(at.x, at.y);
  } else {
    await sleep(camera ? MOVE * 1000 : 150);
    tl.click(at); // the ring presses onto the spot, then the finger "lands"
    await sleep(160);
    await page.touchscreen.tap(at.x, at.y);
  }
  return at;
}

async function finish(tl) {
  tl.wide();
  await sleep(MOVE * 1000 + 800);
}

// --- capture --------------------------------------------------------------
/**
 * Screencast timestamps are browser wall-clock seconds. They are mapped onto
 * now() with the smallest observed (arrival - timestamp) offset, i.e. the
 * least-delayed delivery, so frames line up with the logged actions.
 */
async function startCapture(page) {
  const cdp = await page.context().newCDPSession(page);
  const frames = [];
  cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    frames.push({ ts: metadata.timestamp, arrived: now(), buf: Buffer.from(data, "base64") });
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

/** Pointer/tap decorations at time t, in output pixels (a fixed size whatever the zoom). */
function decorations(tl, t, shot, out) {
  const map = (p) => toOutput(p, shot, tl.aspect, out);
  const ripples = [], rings = [];
  if (tl.device === "desktop") {
    let k = 1;
    for (const c of tl.clicks) {
      const dt = t - c.t;
      if (dt >= 0 && dt < 0.22) k = 1 - 0.16 * Math.sin(Math.PI * dt / 0.22);
      if (dt >= 0 && dt < 0.5) ripples.push({ ...map(c), r: 8 + 22 * (dt / 0.5), a: +(0.4 * (1 - dt / 0.5)).toFixed(3) });
    }
    return { cursor: { ...map(pointerAt(tl.pointerStart, tl.moves, t)), k }, ripples, rings };
  }
  for (const c of tl.clicks) {
    const dt = t - c.t;
    if (dt < 0 || dt > 0.62) continue;
    // Appear, press down onto the spot, then spread out and fade.
    const [r, a] = dt < 0.16 ? [26 - 4 * (dt / 0.16), dt / 0.16]
      : dt < 0.3 ? [22 - 6 * ((dt - 0.16) / 0.14), 1]
      : [16 + 20 * ((dt - 0.3) / 0.32), 1 - (dt - 0.3) / 0.32];
    rings.push({ ...map(c), r, a: +a.toFixed(3) });
  }
  return { cursor: null, ripples, rings };
}

async function composite(compositor, tl, captured, dir) {
  const { frames, started, ended } = captured;
  const d = DEVICES[tl.device];
  const count = Math.round((ended - started) * FPS);
  const log = [];
  let j = 0, loaded = -1;
  for (let i = 0; i < count; i++) {
    const t = started + i / FPS;
    while (j + 1 < frames.length && frames[j + 1].t <= t) j++;
    if (j !== loaded) { await compositor.evaluate((b64) => window.setSource(b64), frames[j].buf.toString("base64")); loaded = j; }
    const shot = cameraAt(tl.full, tl.cues, t, tl.screen, tl.aspect);
    const s = screenRectOut(shot, tl.screen, tl.aspect, d.out);
    const radius = d.radius * (s.w / tl.screen.w);
    const url = await compositor.evaluate((a) => window.draw(a), { bg: BACKGROUND, s, radius, ...decorations(tl, t, shot, d.out) });
    writeFileSync(join(dir, String(i).padStart(5, "0") + ".jpg"), Buffer.from(url.split(",")[1], "base64"));
    log.push({ i, t: +(t - started).toFixed(4), source: j, shot: { cx: +shot.cx.toFixed(2), cy: +shot.cy.toFixed(2), w: +shot.w.toFixed(2) } });
  }
  return { count, log };
}

function ffmpeg(args) {
  const r = spawnSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args], { stdio: "inherit" });
  if (r.status !== 0) throw new Error("ffmpeg failed");
}

function encode(dir, count, posterIndex, target) {
  let crf, size;
  for (crf of CRFS) {
    ffmpeg(["-framerate", `${FPS}`, "-i", join(dir, "%05d.jpg"), "-c:v", "libx264", "-preset", "veryslow", "-crf", `${crf}`,
      "-vf", "scale=out_range=tv:flags=lanczos,format=yuv420p", "-color_range", "tv", "-profile:v", "high", "-r", `${FPS}`, "-movflags", "+faststart", "-an", `${target}.mp4`]);
    size = statSync(`${target}.mp4`).size;
    if (size <= MAX_BYTES) break;
  }
  ffmpeg(["-i", join(dir, String(posterIndex).padStart(5, "0") + ".jpg"), "-q:v", "3", `${target}.jpg`]);
  return { seconds: +(count / FPS).toFixed(2), crf, size, poster: statSync(`${target}.jpg`).size };
}

// --- driving the app -------------------------------------------------------
const shown = (page, selector) => page.locator(selector).filter({ visible: true }).first();
const button = (page, text) => page.locator("button").filter({ hasText: text }).filter({ visible: true }).first();

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

/** Pick the sheet through the real file chooser (it never shows; the app sees a picked file). */
async function upload(page, tl) {
  const target = shown(page, tl?.device === "mobile" ? ".m-drop" : tl ? ".primary-upload-cta" : ".m-drop, .primary-upload-cta");
  const chooser = page.waitForEvent("filechooser");
  if (tl) await act(page, tl, target, { maxZoom: tl.device === "mobile" ? 1.2 : 1.6 });
  else await target.click();
  await (await chooser).setFiles(SHEET);
}

async function onScreen(page, locator, maxH = Infinity) {
  const r = await rectOf(locator);
  const vh = page.viewportSize().height;
  const y = Math.max(r.y, 0);
  return { x: r.x, y, w: r.w, h: Math.max(1, Math.min(r.y + r.h, vh, y + maxH) - y) };
}

/** The strip of sheet just above the mobile board, where the changed chords show. */
async function sheetAboveBoard(page, height = 230) {
  const board = await rectOf(shown(page, ".m-board"));
  return { x: 0, y: Math.max(0, board.y - height), w: board.w, h: Math.min(height, board.y) };
}

// One scene per guide step, played back to back in one recording.
const SCENES = [
  // 1. Upload -> pick the photo -> scan -> "✓ detected key D"
  async function upload_(page, tl) {
    tl.chapter("upload");
    await sleep(600);
    await upload(page, tl);
    await sleep(200);
    tl.wide(); // the original sheet and the scan, together
    await waitDetected(page);
    await sleep(300);
    if (tl.device === "mobile") await focus(tl, [shown(page, ".m-bhead"), await sheetAboveBoard(page, 160)]);
    else await focus(tl, [shown(page, ".active-info-bar")], { pad: 140 });
    tl.mark("result");
    await sleep(1300);
  },
  // 2. Fret 2 -> the changed sheet -> "+" moves the capo up one fret.
  async function capo(page, tl, lang) {
    tl.chapter("capo");
    const fret2 = shown(page, `[aria-label="${L[lang].fret(2)}"]`);
    const plus = shown(page, `[aria-label="${L[lang].capoUp}"]`);
    if (tl.device === "mobile") {
      const area = [shown(page, ".m-fretbox"), shown(page, ".m-stepper")];
      const result = async () => [await sheetAboveBoard(page), shown(page, ".m-stepper")];
      await act(page, tl, fret2, { context: area });
      await waitIdle(page, lang);
      await focus(tl, await result());
      tl.mark("result");
      await sleep(1200);
      await act(page, tl, plus, { context: area });
      await waitIdle(page, lang);
      await focus(tl, await result());
      await sleep(1300);
    } else {
      // The app scrolls to the result as soon as the first render lands, so go wide right after the click.
      await act(page, tl, fret2, { context: [shown(page, ".transpose-selector")], maxZoom: 1.5 });
      await sleep(250);
      tl.wide(0.45);
      await waitIdle(page, lang);
      await sleep(300);
      await waitScrollStable(page);
      await focus(tl, [await onScreen(page, shown(page, ".result-card"), 430)], { pad: 24 });
      tl.mark("result");
      await sleep(1100);
      await act(page, tl, plus, { context: [shown(page, ".transpose-selector")], maxZoom: 1.5 });
      await waitIdle(page, lang);
      await sleep(200);
      await focus(tl, [shown(page, ".transpose-selector"), await onScreen(page, shown(page, ".result-card"), 300)], { pad: 24 });
      await sleep(1300);
    }
  },
  // 3. Above -> Replace -> a look at the original -> back to the result. The sheet stays in frame.
  async function mode(page, tl, lang) {
    tl.chapter("mode");
    let area;
    if (tl.device === "mobile") area = [await sheetAboveBoard(page, 260), shown(page, ".m-acts")];
    else {
      await alignTop(page, tl, shown(page, ".result-card"));
      area = [await onScreen(page, shown(page, ".result-card"), 520)];
    }
    const o = { context: area, pad: tl.device === "mobile" ? 16 : 20 };
    await act(page, tl, button(page, new RegExp(`^${L[lang].above}$`)), o);
    await waitIdle(page, lang);
    tl.mark("result");
    await sleep(1000);
    await act(page, tl, button(page, new RegExp(`^${L[lang].replace}$`)), { ...o, camera: false });
    await waitIdle(page, lang);
    await sleep(700);
    await act(page, tl, button(page, L[lang].original), { ...o, camera: false });
    await sleep(900);
    await act(page, tl, button(page, L[lang].rendered), { ...o, camera: false });
    await sleep(700);
  },
  // 4. Delete a misread chord, place one on the sheet, re-render and show it there.
  async function fix(page, tl, lang) {
    tl.chapter("fix");
    const editor = shown(page, ".chord-editor");
    await reveal(page, tl, editor);
    await act(page, tl, page.locator(".chord-editor span > button").filter({ visible: true }).first(), { context: [editor], pad: 24 });
    await sleep(600);
    await act(page, tl, button(page, "+ Add at position"), { context: [editor], camera: false });
    await sleep(300);
    const sheet = shown(page, tl.device === "mobile" ? ".m-page img" : ".result-card img");
    tl.wide(0.45);
    await sleep(450);
    await sheet.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "start" }));
    await sleep(150);
    await waitScrollStable(page);
    const box = await rectOf(sheet);
    const spot = { x: box.x + box.w * 0.6, y: Math.max(box.y + box.h * 0.13, 150) };
    const spotOnPage = { x: spot.x, y: spot.y + await page.evaluate(() => scrollY) };
    await act(page, tl, { x: spot.x - 60, y: spot.y - 40, w: 120, h: 80 }, { point: spot, pad: tl.device === "mobile" ? 40 : 160 });
    await sleep(350);
    const popup = page.locator("div").filter({ has: page.locator("input[placeholder='e.g. Dm7']") }).last();
    await focus(tl, [popup, { x: spot.x - 20, y: spot.y - 20, w: 40, h: 40 }], { pad: 30, maxZoom: tl.device === "mobile" ? 1.45 : 2 });
    await page.keyboard.type("Em7", { delay: 150 });
    await sleep(300);
    await act(page, tl, button(page, /^Add$/), { camera: false });
    await sleep(600);
    await act(page, tl, button(page, "Re-render with edits"), { context: [editor], pad: 24 });
    await waitIdle(page, lang);
    await sleep(300);
    // Show the new chord where it was placed on the sheet.
    tl.wide(0.45);
    await sleep(450);
    await page.evaluate((y) => window.scrollTo({ top: Math.max(0, y - innerHeight * 0.35), behavior: "smooth" }), spotOnPage.y);
    await sleep(150);
    await waitScrollStable(page);
    const y = spotOnPage.y - await page.evaluate(() => scrollY);
    await focus(tl, [{ x: spot.x - 90, y: y - 50, w: 180, h: 100 }], { pad: tl.device === "mobile" ? 60 : 200, maxZoom: tl.device === "mobile" ? 1.45 : 1.8 });
    tl.mark("result");
    await sleep(1300);
  },
  // 5. PNG download. Desktop: Chrome's download indicator once Playwright sees the real
  // download. Mobile: only the tap; iOS's share sheet can't be automated, so the step
  // text tells iPhone users to choose "Save Image" there rather than faking it here.
  async function save(page, tl) {
    tl.chapter("save");
    const png = button(page, "PNG");
    if (tl.device === "mobile") {
      await act(page, tl, png, { context: [shown(page, ".m-acts")] });
      tl.mark("result");
      await sleep(1500);
    } else {
      const download = page.waitForEvent("download");
      await act(page, tl, png);
      const name = (await download).suggestedFilename();
      await page.evaluate((n) => window.__rec.downloadBubble(n), name);
      await sleep(200);
      await focus(tl, [png, page.locator("#__rec_bubble")], { pad: 40 });
      tl.mark("result");
      await sleep(1300);
    }
    // Outro: wide, back to the top of the result, hold; then the loop cuts to the start.
    tl.wide();
    await sleep(MOVE * 1000);
    await page.evaluate(() => { document.getElementById("__rec_bubble")?.remove(); window.scrollTo({ top: 0, behavior: "smooth" }); });
    await sleep(150);
    await waitScrollStable(page);
    await sleep(800);
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
    const context = await browser.newContext({ ...DEVICES[device].context, acceptDownloads: true, reducedMotion: "reduce" });
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

    const dir = mkdtempSync(join(tmpdir(), "guide-frames-"));
    const { count, log } = await composite(compositors[device], tl, captured, dir);
    const duration = count / FPS;
    // Times on the mp4's clock, snapped to frames.
    const rel = (t) => +Math.min(duration, Math.max(0, Math.round((t - captured.started) * FPS) / FPS)).toFixed(3);
    const chapters = tl.chapters.map((c, i) => ({
      id: c.id,
      start: i === 0 ? 0 : rel(c.t),
      end: i + 1 < tl.chapters.length ? rel(tl.chapters[i + 1].t) : +duration.toFixed(3),
      events: Object.fromEntries(Object.entries(c.events).map(([k, t]) => [k, rel(t)])),
    }));
    const outDir = join(OUT, device, lang);
    mkdirSync(outDir, { recursive: true });
    // Poster: the opening wide shot, which is what step 1's text describes.
    const r = encode(dir, count, Math.round(0.3 * FPS), join(outDir, "guide"));
    writeFileSync(join(outDir, "guide.chapters.json"), JSON.stringify({ duration: +duration.toFixed(3), chapters }, null, 2) + "\n");
    if (process.env.KEEP_FRAMES) console.log("frames kept in", dir); else rmSync(dir, { recursive: true, force: true });
    const raw = (t) => +(t - captured.started).toFixed(4);
    writeFileSync(join(TIMELINES, `${device}-${lang}.json`), JSON.stringify({
      device, lang, fps: FPS, screen: tl.screen, out: DEVICES[device].out, full: tl.full, chapters,
      sourceFrames: captured.frames.map((f) => raw(f.t)),
      cues: tl.cues.map((c) => ({ ...c, t: raw(c.t) })), moves: tl.moves.map((m) => ({ ...m, t: raw(m.t) })),
      clicks: tl.clicks.map((c) => ({ ...c, t: raw(c.t) })), frames: log,
    }, null, 1));
    console.log(`${device}/${lang}  ${r.seconds}s  mp4 ${(r.size / 1024) | 0}KB crf${r.crf}  jpg ${(r.poster / 1024) | 0}KB  chapters ${chapters.map((c) => c.start.toFixed(2)).join(" ")}`);
  }
}
await browser.close();
