#!/usr/bin/env node
// Records the how-to guide videos by driving the real app. Re-run it whenever
// the UI changes; nothing is recorded by hand.
//
// Output: frontend/public/guide/{mobile,desktop}/{ko,en}/step{1..5}.{webm,mp4,jpg}
//   webm = VP9, mp4 = H.264 (Safari), jpg = poster. No audio. Target <= 400 KB each.
//
// Local tools only (none of these are app dependencies):
//   - ffmpeg with libvpx-vp9 + libx264 on PATH   (brew install ffmpeg)
//   - playwright-core installed outside the app: npm install --prefix /tmp/pw playwright-core
//   - Google Chrome (override with --chrome <path>)
//
// Run:
//   1. Backend on :8011 with CORS_ORIGINS including the app origin (see CLAUDE.md).
//   2. cd frontend && NEXT_PUBLIC_API_URL=http://127.0.0.1:8011 npx next build --webpack \
//        && npx next start -H 127.0.0.1 -p 3101
//   3. PLAYWRIGHT_CORE=/tmp/pw/node_modules/playwright-core node scripts/record-guide.mjs \
//        --app http://127.0.0.1:3101 --api http://127.0.0.1:8011 [--only mobile/ko/2]
//
// Reproducibility:
//   - Input is fixtures/images/친구야.jpeg (key D). /detect is called once per run
//     (detection ids live in the backend's memory) and every recording replays that
//     response through page.route after a fixed 1.2 s delay, so the scan effect shows
//     and timing never varies. /render calls hit the real backend.
//   - Frames come from CDP Page.startScreencast, resampled to a fixed 30 fps, then
//     ffmpeg. (Playwright's recordVideo is too blurry for this.)
//   - A fake cursor (desktop) or touch ring (mobile) is drawn in the page so viewers
//     can follow each action; the real click happens once it arrives.
//   - The last 0.35 s crossfades into the first frame so the loop is seamless.
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SHEET = join(ROOT, "fixtures/images/친구야.jpeg");
const OUT = join(ROOT, "frontend/public/guide");
const FPS = 30;
const MAX_BYTES = 400 * 1024;
const DETECT_DELAY_MS = 1200;

const argv = process.argv.slice(2);
const opt = (name, fallback) => { const i = argv.indexOf(`--${name}`); return i >= 0 ? argv[i + 1] : fallback; };
const APP = opt("app", "http://127.0.0.1:3101");
const API = opt("api", "http://127.0.0.1:8011");
const CHROME = opt("chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome");
const ONLY = opt("only", "").split("/").filter(Boolean); // device[/lang[/step]]

const { chromium } = await import(process.env.PLAYWRIGHT_CORE ? join(process.env.PLAYWRIGHT_CORE, "index.mjs") : "playwright-core");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const DEVICES = {
  mobile: {
    context: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true },
    out: [720, 1120], // 9:14
  },
  desktop: {
    context: { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2 },
    out: [1280, 800], // 16:10
  },
};
// Mobile videos are a 9:14 window (390 x 607 CSS px) of the 390 x 844 screen.
const MOBILE_CROP_H = Math.round(390 * 14 / 9);
const MOBILE_CROP_TOP = 844 - MOBILE_CROP_H; // bottom-aligned: the board and the upload button stay in frame

const L = {
  ko: {
    busy: ["업데이트 중", "렌더링 중"], saved: "PNG 저장됨", above: "위에", replace: "교체",
    original: "원본 보기", rendered: "결과 보기", semitoneDown: "반음 내리기", capoUp: "카포 한 프렛 올리기",
    fret: (n) => `카포 ${n}프렛 선택`,
  },
  en: {
    busy: ["Updating", "Rendering"], saved: "PNG saved", above: "Above", replace: "Replace",
    original: "View Original", rendered: "View Rendered", semitoneDown: "Transpose down one semitone", capoUp: "Move capo up one fret",
    fret: (n) => `Select capo fret ${n}`,
  },
};

// In-page overlay: cursor, touch ring, toast, download bubble. Never intercepts events.
const OVERLAY = String.raw`
(() => {
  if (window.__rec) return;
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const layer = () => {
    let el = document.getElementById("__rec_layer");
    if (!el) {
      el = document.createElement("div");
      el.id = "__rec_layer";
      el.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:2147483647";
      document.documentElement.appendChild(el);
    }
    return el;
  };
  let cursor = null, pos = { x: 0, y: 0 };
  const font = "-apple-system,'Apple SD Gothic Neo',sans-serif";
  const rec = {
    cursorAt(x, y) {
      if (!cursor) {
        cursor = document.createElement("div");
        cursor.style.cssText = "position:absolute;left:0;top:0;width:26px;height:30px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35));transform-origin:3px 3px";
        cursor.innerHTML = '<svg width="26" height="30" viewBox="0 0 26 30"><path d="M3 2l18 16.5-8.2.8 4.8 9.3-3.6 1.8-4.8-9.3L3 27z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
        layer().appendChild(cursor);
      }
      pos = { x, y };
      cursor.style.translate = (x - 3) + "px " + (y - 3) + "px";
    },
    moveTo(x, y, ms) {
      const from = { ...pos };
      return new Promise((done) => {
        const t0 = performance.now();
        const tick = (now) => {
          const t = Math.min(1, (now - t0) / ms), k = ease(t);
          rec.cursorAt(from.x + (x - from.x) * k, from.y + (y - from.y) * k);
          t < 1 ? requestAnimationFrame(tick) : done();
        };
        requestAnimationFrame(tick);
      });
    },
    press() {
      cursor && cursor.animate([{ scale: 1 }, { scale: 0.84 }, { scale: 1 }], { duration: 220, easing: "ease-out" });
      const r = document.createElement("div");
      r.style.cssText = "position:absolute;border-radius:50%;left:" + (pos.x - 18) + "px;top:" + (pos.y - 18) + "px;width:36px;height:36px;background:rgba(224,93,0,.35)";
      layer().appendChild(r);
      r.animate([{ transform: "scale(.3)", opacity: 1 }, { transform: "scale(1.5)", opacity: 0 }], { duration: 480, easing: "ease-out" }).onfinish = () => r.remove();
    },
    tap(x, y) {
      const ring = document.createElement("div");
      ring.style.cssText = "position:absolute;left:" + (x - 22) + "px;top:" + (y - 22) + "px;width:44px;height:44px;border-radius:50%;background:rgba(26,26,46,.22);border:2px solid rgba(255,255,255,.9);box-shadow:0 2px 8px rgba(0,0,0,.25)";
      layer().appendChild(ring);
      ring.animate([
        { transform: "scale(1.1)", opacity: 0 },
        { transform: "scale(1)", opacity: 1, offset: .3 },
        { transform: "scale(.7)", opacity: 1, offset: .55 },
        { transform: "scale(1.6)", opacity: 0 },
      ], { duration: 600, easing: "ease-out" }).onfinish = () => ring.remove();
    },
    toast(text) {
      const t = document.createElement("div");
      t.textContent = "✓ " + text;
      t.style.cssText = "position:absolute;left:50%;bottom:" + (window.innerHeight * 0.5) + "px;translate:-50% 0;padding:11px 18px;border-radius:999px;background:#1a1a2e;color:#fff;font:600 15px " + font + ";box-shadow:0 8px 24px rgba(0,0,0,.25);white-space:nowrap";
      layer().appendChild(t);
      t.animate([{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }], { duration: 220, fill: "both" });
    },
    downloadBubble(name) {
      const b = document.createElement("div");
      b.style.cssText = "position:absolute;right:18px;top:62px;width:300px;padding:12px 14px;border-radius:12px;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,.22);display:flex;gap:10px;align-items:center;font:500 13px " + font + ";color:#1a1a2e";
      b.innerHTML = '<div style="width:32px;height:32px;border-radius:8px;background:#e8f0fe;display:grid;place-items:center;flex:none"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1a73e8" stroke-width="2.2" stroke-linecap="round"><path d="M12 4v11m0 0l-4.5-4.5M12 15l4.5-4.5M5 20h14"/></svg></div><div style="min-width:0"><div class="n" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600"></div><div style="color:#5f6368;font-size:12px;margin-top:2px">✓ Done</div></div>';
      b.querySelector(".n").textContent = name;
      layer().appendChild(b);
      b.animate([{ opacity: 0, transform: "translateY(-8px)" }, { opacity: 1, transform: "none" }], { duration: 220, fill: "both" });
    },
  };
  window.__rec = rec;
})();
`;

// --- capture --------------------------------------------------------------
async function startCapture(page) {
  const cdp = await page.context().newCDPSession(page);
  const frames = [];
  cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    frames.push({ t: metadata.timestamp, buf: Buffer.from(data, "base64") });
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
  });
  const { width, height } = page.viewportSize();
  const dpr = await page.evaluate(() => devicePixelRatio);
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, everyNthFrame: 1, maxWidth: width * dpr, maxHeight: height * dpr });
  const started = Date.now() / 1000;
  return async () => {
    const ended = Date.now() / 1000;
    await cdp.send("Page.stopScreencast");
    await cdp.detach();
    return { frames, started, ended };
  };
}

/** Screencast only sends frames on change; hold the latest frame to get a fixed 30 fps. */
function resample({ frames, started, ended }, dir) {
  if (!frames.length) throw new Error("no frames captured");
  const t0 = Math.max(started, frames[0].t);
  const count = Math.max(1, Math.round((ended - t0) * FPS));
  for (let i = 0, j = 0; i < count; i++) {
    while (j + 1 < frames.length && frames[j + 1].t <= t0 + i / FPS) j++;
    writeFileSync(join(dir, String(i).padStart(5, "0") + ".jpg"), frames[j].buf);
  }
  return count;
}

function ffmpeg(args) {
  const r = spawnSync("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args], { stdio: "inherit" });
  if (r.status !== 0) throw new Error("ffmpeg failed");
}

function encode(dir, count, device, step, target) {
  const [w, h] = DEVICES[device].out;
  // Frame size may differ from the DPR size; crop in proportions of the 390 x 844 screen.
  const crop = device === "mobile" ? `crop=iw:ih*${MOBILE_CROP_H}/844:0:ih*${MOBILE_CROP_TOP}/844,` : "";
  const prep = `${crop}scale=${w}:${h}:flags=lanczos,setsar=1,format=yuv420p`;
  const duration = count / FPS, fade = 0.35;
  const inputs = ["-framerate", `${FPS}`, "-i", join(dir, "%05d.jpg"), "-loop", "1", "-framerate", `${FPS}`, "-t", `${fade + 0.1}`, "-i", join(dir, "00000.jpg")];
  const filter = `[0:v]${prep}[a];[1:v]${prep}[b];[a][b]xfade=transition=fade:duration=${fade}:offset=${(duration - fade).toFixed(3)},trim=duration=${duration.toFixed(3)},format=yuv420p[v]`;
  const under = (ext, codec, crfs) => {
    for (const crf of crfs) {
      ffmpeg([...inputs, "-filter_complex", filter, "-map", "[v]", "-an", ...codec(crf), `${target}.${ext}`]);
      const size = statSync(`${target}.${ext}`).size;
      if (size <= MAX_BYTES || crf === crfs.at(-1)) return { crf, size };
    }
  };
  const webm = under("webm", (crf) => ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", `${crf}`, "-row-mt", "1", "-deadline", "good", "-cpu-used", "2"], [34, 38, 42, 46, 50, 54]);
  const mp4 = under("mp4", (crf) => ["-c:v", "libx264", "-preset", "slow", "-crf", `${crf}`, "-profile:v", "high", "-movflags", "+faststart"], [24, 26, 28, 30, 32, 34, 36]);
  // Poster: the step's outcome, ~70% into the clip.
  const poster = join(dir, String(Math.floor(count * 0.7)).padStart(5, "0") + ".jpg");
  ffmpeg(["-i", poster, "-vf", prep.replace(",format=yuv420p", ""), "-q:v", "4", `${target}.jpg`]);
  return { seconds: +duration.toFixed(2), webm, mp4, poster: statSync(`${target}.jpg`).size };
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

async function scrollTo(page, locator, block = "center") {
  const inView = await locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return r.top >= 70 && r.bottom <= window.innerHeight - 10;
  });
  if (inView) return;
  await locator.evaluate((el, b) => el.scrollIntoView({ behavior: "smooth", block: b }), block);
  await sleep(700);
}

/** Show the pointer, then click for real. Works for a locator or a point. */
async function act(page, device, target, { move = 480 } = {}) {
  let x, y;
  if (Array.isArray(target)) [x, y] = target;
  else {
    await scrollTo(page, target);
    const box = await target.boundingBox();
    x = box.x + box.width / 2; y = box.y + box.height / 2;
  }
  if (device === "desktop") {
    await page.evaluate(([x, y, ms]) => window.__rec.moveTo(x, y, ms), [x, y, move]);
    await sleep(100);
    await page.evaluate(() => window.__rec.press());
    await page.mouse.click(x, y);
  } else {
    await page.evaluate(([x, y]) => window.__rec.tap(x, y), [x, y]);
    await sleep(180);
    await page.touchscreen.tap(x, y);
  }
}

async function upload(page, device, shown_) {
  const target = shown(page, device === "mobile" ? ".m-drop" : ".primary-upload-cta");
  const chooser = page.waitForEvent("filechooser");
  if (shown_) await act(page, device, target); else await target.click();
  await (await chooser).setFiles(SHEET); // the OS picker never shows; the app sees a picked file
}

const waitDetected = (page) => page.waitForFunction(
  () => document.body.innerText.includes("✓") && !document.querySelector(".m-scan"), null, { timeout: 60000, polling: 100 });

async function detected(page, device) {
  await upload(page, device, false);
  await waitDetected(page);
}

async function pickFret(page, lang, fret) {
  await shown(page, `[aria-label="${L[lang].fret(fret)}"]`).click();
  await waitIdle(page, lang);
}

const STEPS = {
  // Upload -> pick the photo -> scan -> "✓ detected key D"
  1: {
    prepare: async () => {},
    perform: async (page, device) => {
      await sleep(600);
      await upload(page, device, true);
      await waitDetected(page);
      await sleep(1500);
    },
  },
  // Mobile: fret 2 -> chords change, key label -> "+" once -> capo 3. Desktop: fret 2 -> semitone button.
  2: {
    prepare: async (page, device) => {
      await detected(page, device);
      if (device === "desktop") await shown(page, ".fretboard-section").evaluate((el) => el.scrollIntoView({ block: "center" }));
    },
    perform: async (page, device, lang) => {
      await sleep(500);
      await act(page, device, shown(page, `[aria-label="${L[lang].fret(2)}"]`));
      await waitIdle(page, lang);
      await sleep(900);
      await act(page, device, shown(page, `[aria-label="${device === "mobile" ? L[lang].capoUp : L[lang].semitoneDown}"]`));
      await waitIdle(page, lang);
      await sleep(1500);
    },
  },
  // Above -> Replace -> a quick look at the original.
  3: {
    prepare: async (page, device, lang) => {
      await detected(page, device);
      await pickFret(page, lang, 2);
      if (device === "desktop") await shown(page, ".result-card").evaluate((el) => el.scrollIntoView({ block: "start" }));
    },
    perform: async (page, device, lang) => {
      await act(page, device, button(page, new RegExp(`^${L[lang].above}$`)));
      await waitIdle(page, lang); await sleep(800);
      await act(page, device, button(page, new RegExp(`^${L[lang].replace}$`)));
      await waitIdle(page, lang); await sleep(700);
      await act(page, device, button(page, L[lang].original));
      await sleep(800);
      await act(page, device, button(page, L[lang].rendered));
      await sleep(1000);
    },
  },
  // Delete a chord with ✕ -> "+ Add at position" -> tap the sheet -> type -> Add.
  4: {
    prepare: async (page, device, lang) => {
      await detected(page, device);
      await pickFret(page, lang, 2);
      await shown(page, ".chord-editor").evaluate((el) => el.scrollIntoView({ block: "center" }));
    },
    perform: async (page, device, lang) => {
      await act(page, device, page.locator(".chord-editor span > button").filter({ visible: true }).first());
      await sleep(450);
      await act(page, device, button(page, "+ Add at position"));
      await sleep(300);
      const sheet = shown(page, device === "mobile" ? ".m-page img" : ".result-card img");
      await sheet.evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "start" }));
      await sleep(650);
      const box = await sheet.boundingBox();
      await act(page, device, [box.x + box.width * 0.6, Math.max(box.y + box.height * 0.13, 150)]);
      await sleep(350);
      await page.keyboard.type("Em7", { delay: 150 });
      await sleep(300);
      await act(page, device, button(page, /^Add$/), { move: 380 });
      await sleep(500);
      // Back to the chord list (mobile) so the loop restarts where it began; the desktop clip is long enough already.
      if (device === "mobile") await shown(page, ".chord-editor").evaluate((el) => el.scrollIntoView({ behavior: "smooth", block: "center" }));
      await sleep(device === "mobile" ? 1200 : 650);
    },
  },
  // PNG download -> mobile: a "saved" toast (no share sheet), desktop: the browser's download bubble.
  5: {
    prepare: async (page, device, lang) => {
      await detected(page, device);
      await pickFret(page, lang, 2);
      if (device === "desktop") await button(page, "PNG").evaluate((el) => el.scrollIntoView({ block: "center" }));
    },
    perform: async (page, device, lang) => {
      await sleep(700);
      await act(page, device, button(page, "PNG"));
      await sleep(400);
      if (device === "mobile") await page.evaluate((t) => window.__rec.toast(t), L[lang].saved);
      else await page.evaluate(() => window.__rec.downloadBubble("transposed_replace_친구야.png"));
      await sleep(2200);
    },
  },
};

// --- main ----------------------------------------------------------------
const form = new FormData();
form.append("image", new Blob([readFileSync(SHEET)], { type: "image/jpeg" }), "친구야.jpeg");
const res = await fetch(`${API}/detect`, { method: "POST", body: form });
if (!res.ok) throw new Error(`/detect failed: ${res.status}`);
const detectBody = await res.text();
console.log("detected key", JSON.parse(detectBody).original_key);

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
const results = [];
for (const device of ["mobile", "desktop"]) {
  for (const lang of ["ko", "en"]) {
    for (const step of [1, 2, 3, 4, 5]) {
      if ((ONLY[0] && ONLY[0] !== device) || (ONLY[1] && ONLY[1] !== lang) || (ONLY[2] && +ONLY[2] !== step)) continue;
      const context = await browser.newContext({ ...DEVICES[device].context, acceptDownloads: true, reducedMotion: "reduce" });
      // The guide must not open over its own recording; reduced motion keeps the logo still.
      await context.addInitScript(() => { try { localStorage.setItem("tc-guide-dismissed", "1"); } catch {} });
      await context.addInitScript(OVERLAY);
      await context.route(/\/detect$/, async (route) => {
        await sleep(DETECT_DELAY_MS);
        await route.fulfill({ status: 200, contentType: "application/json", body: detectBody, headers: { "access-control-allow-origin": "*" } });
      });
      const page = await context.newPage();
      await page.goto(`${APP}/`, { waitUntil: "networkidle" });
      // Switch language with the app's own KO/EN toggle.
      await shown(page, `button[aria-label="${lang === "ko" ? "한국어 KO" : "English EN"}"]`).click();
      await sleep(400);
      await STEPS[step].prepare(page, device, lang);
      if (device === "desktop") await page.evaluate(() => window.__rec.cursorAt(innerWidth * 0.7, innerHeight * 0.6));
      await sleep(400);
      const stop = await startCapture(page);
      await sleep(400);
      await STEPS[step].perform(page, device, lang);
      const captured = await stop();
      const dir = mkdtempSync(join(tmpdir(), "guide-frames-"));
      const outDir = join(OUT, device, lang);
      mkdirSync(outDir, { recursive: true });
      const r = encode(dir, resample(captured, dir), device, step, join(outDir, `step${step}`));
      rmSync(dir, { recursive: true, force: true });
      results.push({ device, lang, step, ...r });
      console.log(`${device}/${lang}/step${step}  ${r.seconds}s  webm ${(r.webm.size / 1024) | 0}KB crf${r.webm.crf}  mp4 ${(r.mp4.size / 1024) | 0}KB crf${r.mp4.crf}  jpg ${(r.poster / 1024) | 0}KB`);
      await context.close();
    }
  }
}
await browser.close();
