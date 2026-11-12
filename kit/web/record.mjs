// kit/web/record.mjs: a frame-exact screen recording of a live website, for 16:9 films (2026-10-17, films/ai-portfolio).
//
// Why: the owner's films need the real product on screen, big and sharp (EDITING.md §11), and a desktop screen
// recording needs a macOS permission that isn't always there. Real-time capture of a 4K page drops frames, and
// HeadlessExperimental.beginFrame (the usual deterministic path) is not supported on macOS. So the page runs on a
// virtual clock instead: performance.now, Date, requestAnimationFrame and timers are replaced before any page script
// runs, every CSS animation, transition and Web Animation is paused and set to the clock each frame, and the frame is
// only captured once the page has caught up. A 60 fps recording is therefore perfectly smooth at any resolution, and
// the same script gives the same video twice.
//
//   node kit/web/record.mjs <url> <out.mp4> [--width=1920 --height=1080 --dpr=2 --fps=60 --dur=8]
//        [--scheme=dark|light] [--date=2026-10-17T05:13:00+05:30] [--warm=2500] [--hide=<css>,<css>]
//        [--steps=<steps.json>] [--cursor] [--crf=12] [--frames=<dir>] [--debug: the page's console errors -> stderr]
//
// --steps: a JSON list of actions on the recording's clock (seconds from the first frame), done in order:
//   { "t": 1.0, "do": "scroll", "to": 1200, "dur": 2.4, "ease": "inOut" }   scroll the page (to = px or a CSS selector)
//   { "t": 3.0, "do": "move", "x": 900, "y": 500, "dur": 0.6 }              move the pointer (hover states follow);
//   { "t": 3.0, "do": "move", "sel": "figure.portrait", "dx": 0, "dy": -40 }   or to an element's centre (+ offset).
//                                                                          The pointer is hidden until its first move,
//                                                                          which enters from fromDx/fromDy (260, 160) px
//   { "t": 3.7, "do": "click" }                                              press and release at the pointer
//   { "t": 4.0, "do": "type", "text": "whoami", "cps": 14 }                  type into the focused element
//   { "t": 5.0, "do": "key", "key": "Enter", "mods": ["Meta"] }               a key or a shortcut
//   { "t": 6.0, "do": "eval", "js": "document.body.classList.add('x')" }    anything else
// --cursor draws a macOS-style pointer (with a click ring) at the pointer position, baked into the frames.
// --date sets the page's clock (what a live local-time widget shows); default: now.
// Writes <out.mp4> (x264, yuv420p, CRF --crf, the page's pixels: width*dpr x height*dpr) and <out>.json (the
// timeline: url, size, fps, steps, the scroll position and pointer per frame, so a film can annotate the recording).
import puppeteer from "puppeteer-core";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const [url, out] = args.filter((a) => !a.startsWith("--"));
const opt = (k, d) => { const a = args.find((x) => x.startsWith(`--${k}=`)); return a ? a.split("=").slice(1).join("=") : d; };
if (!url || !out) { console.error("usage: node kit/web/record.mjs <url> <out.mp4> [--dur=8 --fps=60 --steps=steps.json ...]"); process.exit(2); }
const W = +opt("width", 1920), H = +opt("height", 1080), DPR = +opt("dpr", 2), FPS = +opt("fps", 60), DUR = +opt("dur", 8);
const SCHEME = opt("scheme", "dark"), WARM = +opt("warm", 2500), CRF = opt("crf", "12");
const DATE = opt("date", "") ? new Date(opt("date")).getTime() : Date.now();
const HIDE = ["nextjs-portal", "#__next-build-watcher", "[data-nextjs-toast]", ...(opt("hide", "") || "").split(",").filter(Boolean)];
const STEPS = opt("steps", "") ? JSON.parse(fs.readFileSync(opt("steps"), "utf8")) : [];
const CURSOR = args.includes("--cursor");
const FRAMES = opt("frames", "");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

// ---- the virtual clock, installed before any page script (evaluateOnNewDocument) ----
const CLOCK = (dateBase) => {
  const realPerf = performance.now.bind(performance), realST = window.setTimeout.bind(window), realCT = window.clearTimeout.bind(window);
  window.__realRAF = window.requestAnimationFrame.bind(window);
  const RealDate = Date, perf0 = realPerf();
  let v = 0, nextId = 1e6;
  const timers = new Map(), rafs = new Map(), seen = new WeakMap();
  const vperf = () => perf0 + v;
  performance.now = vperf;
  function VDate(...a) { if (!(this instanceof VDate)) return new RealDate(dateBase + v).toString(); return a.length ? new RealDate(...a) : new RealDate(dateBase + v); }
  VDate.prototype = RealDate.prototype; VDate.now = () => dateBase + v; VDate.UTC = RealDate.UTC; VDate.parse = RealDate.parse;
  Object.setPrototypeOf(VDate, RealDate); window.Date = VDate;
  // timers: a delay under 5 ms is "next tick" plumbing (React, Next's router): it runs in real time, so the page can
  // boot while the clock stands still; anything longer waits for the clock
  window.setTimeout = (fn, d = 0, ...a) => {
    const id = nextId++;
    if (!(d >= 5)) { const r = realST(() => { timers.delete(id); typeof fn === "function" && fn(...a); }, 0); timers.set(id, { real: r }); return id; }
    timers.set(id, { due: v + d, fn, a, every: 0 }); return id;
  };
  window.setInterval = (fn, d = 0, ...a) => { const id = nextId++; timers.set(id, { due: v + Math.max(5, d), fn, a, every: Math.max(5, d) }); return id; };
  window.clearTimeout = window.clearInterval = (id) => { const t = timers.get(id); if (t && t.real) realCT(t.real); timers.delete(id); };
  window.requestAnimationFrame = (cb) => { const id = nextId++; rafs.set(id, cb); return id; };
  // framer-motion and motion run opacity/transform fades as Web Animations when Element.prototype has its own
  // "animate", and they set each one's startTime from performance.now(): our clock, while the document timeline is
  // frozen in real time, so an in-view reveal waited as long as the recording had run and then lost its end value
  // (Argon's site, 2026-10-17: every section blank after a scroll 5 s in). Moved one prototype up, element.animate()
  // still works for any page that calls it, but those libraries take their JS path, which runs on this clock exactly.
  const nativeAnimate = Element.prototype.animate;
  if (nativeAnimate && !window.__keepWaapi) {
    delete Element.prototype.animate;
    Object.defineProperty(Node.prototype, "animate", { value: nativeAnimate, configurable: true, writable: true });
  }
  window.cancelAnimationFrame = (id) => rafs.delete(id);
  const sync = () => {                                   // every animation follows the clock from when it was first seen
    for (const an of document.getAnimations()) {
      let s = seen.get(an);
      if (!s) { s = { at: v, base: an.currentTime || 0 }; seen.set(an, s); }
      const rate = an.playbackRate || 1;
      try { an.currentTime = s.base + (v - s.at) * rate; } catch (e) { /* an animation with no timeline */ }
    }
  };
  window.__vclock = {
    now: () => v,
    advance(ms) {
      const end = v + ms;
      for (let guard = 0; guard < 10000; guard++) {                  // timers in due order, intervals re-armed
        let id = null, best = null;
        for (const [k, t] of timers) if (t.due !== undefined && t.due <= end + 1e-6 && (!best || t.due < best.due)) { id = k; best = t; }
        if (!best) break;
        v = Math.max(v, best.due);
        if (best.every) best.due += best.every; else timers.delete(id);
        try { typeof best.fn === "function" ? best.fn(...best.a) : (0, eval)(best.fn); } catch (e) { console.error(e); }
      }
      v = end;
      const cbs = [...rafs.values()]; rafs.clear();
      const ts = vperf();
      for (const cb of cbs) { try { cb(ts); } catch (e) { console.error(e); } }
      sync();
    },
    sync,
  };
};

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true,
  args: ["--hide-scrollbars", "--force-color-profile=srgb", "--disable-background-timer-throttling", "--disable-renderer-backgrounding"] });
const page = await browser.newPage();
const cdp = await page.createCDPSession();
await page.setViewport({ width: W, height: H, deviceScaleFactor: DPR });
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: SCHEME }, { name: "prefers-reduced-motion", value: "no-preference" }]);
await page.evaluateOnNewDocument(CLOCK, DATE);
await cdp.send("Animation.enable");
await cdp.send("Animation.setPlaybackRate", { playbackRate: 0 });       // nothing moves until the clock says so
page.on("pageerror", (e) => console.error("[page]", e.message));
if (args.includes("--debug")) page.on("console", (m) => { if (["error", "warn", "warning"].includes(m.type())) console.error(`[console.${m.type()}]`, m.text().slice(0, 400)); });
await page.goto(url, { waitUntil: "networkidle2", timeout: 120000 });
await page.addStyleTag({ content: `${HIDE.join(",")}{display:none!important} html{scroll-behavior:auto!important}` });
// images load now (eager), so nothing pops in mid-recording; in-view effects still wait for the scroll
await page.evaluate(() => document.querySelectorAll("img[loading=lazy]").forEach((i) => { i.loading = "eager"; }));
await page.waitForNetworkIdle({ idleTime: 500, timeout: 30000 }).catch(() => {});
await new Promise((r) => setTimeout(r, WARM));                           // hydration and effects, clock still at 0
if (CURSOR) {
  await page.evaluate(() => {
    const c = document.createElement("div");
    c.id = "__rec_cursor";
    c.innerHTML = `<svg width="30" height="30" viewBox="0 0 24 24" style="filter:drop-shadow(0 1.5px 2px rgba(0,0,0,.45))"><path d="M5 2.5v16.2l4.1-3.9 2.6 6.1 2.9-1.2-2.6-6h5.7z" fill="#fff" stroke="#111" stroke-width="1.3" stroke-linejoin="round"/></svg><i></i>`;
    Object.assign(c.style, { position: "fixed", left: "0", top: "0", zIndex: 2147483647, pointerEvents: "none", width: "30px", height: "30px", transform: "translate(-100px,-100px)" });
    const ring = c.querySelector("i");
    Object.assign(ring.style, { position: "absolute", left: "-14px", top: "-14px", width: "36px", height: "36px", borderRadius: "50%", border: "2px solid rgba(255,255,255,.9)", opacity: "0", boxShadow: "0 0 0 1px rgba(0,0,0,.25)" });
    document.documentElement.appendChild(c);
  });
}

const ease = { linear: (u) => u, inOut: (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2), out: (u) => 1 - Math.pow(1 - u, 3), in: (u) => u * u * u };
const targetY = async (to) => typeof to === "number" ? to : page.evaluate((s) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().top + scrollY - 80 : 0; }, to);
for (const s of STEPS) if (s.do === "scroll") s._to = await targetY(s.to);

const [ow, oh] = [Math.round(W * DPR), Math.round(H * DPR)];
fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
if (FRAMES) fs.mkdirSync(FRAMES, { recursive: true });
const enc = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", String(FPS), "-i", "-",
  "-vf", `scale=${ow}:${oh}:flags=lanczos,format=yuv420p`, "-c:v", "libx264", "-crf", CRF, "-preset", "slow", "-tune", "animation",
  "-g", String(FPS), "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });

const nFrames = Math.round(DUR * FPS), dt = 1000 / FPS;
const done = new Set(), log = [];
let ptr = { x: W * 0.62, y: H * 0.55 }, scroll0 = await page.evaluate(() => scrollY), clickAt = -1, shown = false;
const t0 = Date.now();
for (let f = 0; f < nFrames; f++) {
  const t = f / FPS;
  for (const [i, s] of STEPS.entries()) {                          // actions due by this frame
    if (s.t > t + 1e-6) continue;
    if (s.do === "scroll") {
      if (!s._from && s._from !== 0) s._from = await page.evaluate(() => scrollY);
      const u = Math.min(1, (t - s.t) / Math.max(1e-3, s.dur || 1));
      const y = s._from + (s._to - s._from) * (ease[s.ease || "inOut"] || ease.inOut)(u);
      await page.evaluate((yy) => window.scrollTo(0, yy), Math.round(y));
      continue;
    }
    if (s.do === "move") {
      if (!s._from) {
        s._from = { ...ptr };
        if (s.sel) { const r = await page.evaluate((q) => { const e = document.querySelector(q); if (!e) return null; const b = e.getBoundingClientRect();
            return { x: b.left + b.width * 0.5, y: b.top + b.height * 0.5 }; }, s.sel);
          if (r) { s.x = r.x + (s.dx || 0); s.y = r.y + (s.dy || 0); } else console.error(`no element for ${s.sel}`); }
        if (!shown) s._from = { x: s.x + (s.fromDx != null ? s.fromDx : 260), y: s.y + (s.fromDy != null ? s.fromDy : 160) };   // the pointer enters
        shown = true;
      }
      const u = Math.min(1, (t - s.t) / Math.max(1e-3, s.dur || 0.6));
      const e = ease.inOut(u);
      ptr = { x: s._from.x + (s.x - s._from.x) * e, y: s._from.y + (s.y - s._from.y) * e };
      await page.mouse.move(ptr.x, ptr.y);
      continue;
    }
    if (done.has(i)) continue;
    if (s.do === "type") {                                           // one character per 1/cps s
      const n = Math.min(s.text.length, Math.floor((t - s.t) * (s.cps || 14)) + 1);
      s._n = s._n || 0;
      while (s._n < n) { await page.keyboard.type(s.text[s._n]); s._n++; }
      if (s._n >= s.text.length) done.add(i);
      continue;
    }
    done.add(i);
    if (s.do === "click") { await page.mouse.click(ptr.x, ptr.y); clickAt = t; }
    else if (s.do === "key") { for (const m of s.mods || []) await page.keyboard.down(m); await page.keyboard.press(s.key); for (const m of (s.mods || []).reverse()) await page.keyboard.up(m); }
    else if (s.do === "eval") await page.evaluate(s.js);
  }
  if (CURSOR) {
    const ring = clickAt >= 0 && t - clickAt < 0.45 ? 1 - (t - clickAt) / 0.45 : 0;
    await page.evaluate((x, y, r, on) => { const c = document.getElementById("__rec_cursor"); if (!c) return;
      c.style.transform = `translate(${x - 5}px,${y - 2.5}px)`; c.style.visibility = on ? "visible" : "hidden"; const i = c.firstElementChild.nextElementSibling;
      i.style.opacity = String(r); i.style.transform = `scale(${1.4 - 0.6 * r})`; }, ptr.x, ptr.y, ring, shown);
  }
  if (f > 0) await page.evaluate((ms) => window.__vclock.advance(ms), dt); else await page.evaluate(() => window.__vclock.sync());
  // let the page lay out and paint this state (two real frames; IntersectionObserver callbacks run here), then sync
  // again so any animation those callbacks started is already on the clock
  await page.evaluate(() => new Promise((r) => window.__realRAF(() => window.__realRAF(r))));
  await page.evaluate(() => window.__vclock.sync());
  const shot = await cdp.send("Page.captureScreenshot", { format: "jpeg", quality: 95, optimizeForSpeed: false, fromSurface: true });
  const buf = Buffer.from(shot.data, "base64");
  if (FRAMES && f % FPS === 0) fs.writeFileSync(path.join(FRAMES, `f${String(f).padStart(5, "0")}.jpg`), buf);
  if (!enc.stdin.write(buf)) await new Promise((r) => enc.stdin.once("drain", r));
  log.push({ f, scrollY: await page.evaluate(() => Math.round(scrollY)), ptr: [Math.round(ptr.x), Math.round(ptr.y)] });
  if (f % FPS === 0) process.stdout.write(`\r${path.basename(out)} ${t.toFixed(1)}/${DUR}s (${((Date.now() - t0) / 1000).toFixed(0)} s)   `);
}
enc.stdin.end();
await new Promise((r) => enc.on("close", r));
fs.writeFileSync(out.replace(/\.mp4$/, "") + ".json", JSON.stringify({ url, width: W, height: H, dpr: DPR, fps: FPS, dur: DUR,
  scheme: SCHEME, date: new Date(DATE).toISOString(), steps: STEPS.map(({ _from, _to, _n, ...s }) => s), frames: log }, null, 0));
console.log(`\n${url} -> ${out} (${ow}x${oh}, ${nFrames} frames at ${FPS} fps, ${((Date.now() - t0) / 1000).toFixed(0)} s)`);
await browser.close();
