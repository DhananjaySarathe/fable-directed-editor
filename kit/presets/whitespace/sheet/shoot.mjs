// The whitespace still sheet (kit/presets/whitespace/README.md §6): builds the pages (build.py here), takes a still of
// each scene per look and tiles them into <look>_sheet.png (3 x 2: hook, statement, diagram / evidence, chart,
// overview) in output/temp/demos/whitespace_sheet/. It also checks the restraint rule "elements land once, then stay
// still": a landed card or window must not move between two later times on whitespace (canvas_studio's cards drift,
// as they always did, and are only reported). Exit 1 on a page error or a whitespace card that moves.
//
//   node kit/presets/whitespace/sheet/shoot.mjs [look ...]        (default: whitespace canvas_studio)
//   (build with --room first for his real room in the card: uv run python kit/presets/whitespace/sheet/build.py --room <take>)
import puppeteer from "puppeteer-core";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../../../..");
const OUT = path.join(ROOT, "output/temp/demos/whitespace_sheet");
const looks = process.argv.slice(2).length ? process.argv.slice(2) : ["whitespace", "canvas_studio"];
execFileSync("python3", [path.join(HERE, "build.py"), ...looks], { cwd: ROOT, stdio: "inherit" });
const TIMES = [3, 6.5, 11, 15, 19.5, 22.5];                  // one per scene, each after its pieces have landed
const STILL = [[10.8, 11.8], [13.6, 15.6], [17.4, 19.8]];     // pairs after the diagram, the window and the chart panel land

const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true,
  args: ["--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"], protocolTimeout: 120000 });
let bad = 0;
for (const look of looks) {
  const p = await b.newPage(), errs = [];
  p.on("pageerror", (e) => errs.push(String(e.message || e)));
  await p.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  await p.goto("file://" + path.join(OUT, look + ".html"), { waitUntil: "domcontentloaded" });
  await p.waitForFunction(() => window.__timelines && Object.keys(window.__timelines).length > 0, { timeout: 90000 });
  // never an unguarded fonts.ready: a page with a missing face can hang it forever
  await p.evaluate(() => Promise.race([document.fonts ? document.fonts.ready : null, new Promise((r) => setTimeout(r, 4000))]));
  // seek the timeline and the room clip (to t, so his card shows a frame), then wait for the seek
  const seek = (t) => p.evaluate(async (t) => {
    window.__timelines.ws.seek(t, false);
    await Promise.all([...document.querySelectorAll("video")].map((v) => new Promise((r) => {
      const go = () => { const tt = Math.min(t, (v.duration || 24) - 0.1); if (Math.abs(v.currentTime - tt) < 0.01) return r();
        v.addEventListener("seeked", () => r(), { once: true }); v.currentTime = tt; setTimeout(r, 3000); };
      if (v.readyState >= 1) go(); else { v.addEventListener("loadedmetadata", go, { once: true }); v.load(); setTimeout(r, 5000); } })));
  }, t);
  const shots = [];
  for (const t of TIMES) {
    await seek(t);
    await new Promise((r) => setTimeout(r, 350));
    const f = path.join(OUT, `${look}_${t}.png`);
    await p.screenshot({ path: f });
    shots.push(f);
  }
  // the restraint check: every landed card / window keeps one transform between the two times of a pair
  let moved = 0;
  for (const [a, z] of STILL) {
    const grab = async (t) => { await seek(t); return p.evaluate(() => [...document.querySelectorAll(".cv-card, .cv-win")]
      .map((e) => getComputedStyle(e).visibility === "visible" && +getComputedStyle(e).opacity > 0.99 ? getComputedStyle(e).transform : null)); };
    const A = await grab(a), Z = await grab(z);
    moved += A.filter((m, i) => m && Z[i] && m !== Z[i]).length;
  }
  if (look === "whitespace" && moved) bad++;
  execFileSync("ffmpeg", ["-v", "error", "-y", ...shots.flatMap((f) => ["-i", f]), "-filter_complex",
    shots.map((_, i) => `[${i}:v]scale=960:540[s${i}]`).join(";") + ";" + shots.map((_, i) => `[s${i}]`).join("") + "xstack=inputs=6:layout=0_0|960_0|1920_0|0_540|960_540|1920_540",
    path.join(OUT, `${look}_sheet.png`)]);
  if (errs.length) bad++;
  console.log(`${look}: ${TIMES.length} stills, ${path.join(OUT, look + "_sheet.png")}; landed cards that moved: ${moved}` +
    (look === "whitespace" ? (moved ? " (FAIL: they land once, then stay still)" : " (ok)") : " (drift is this look's own)") +
    (errs.length ? "; page errors: " + errs.slice(0, 3).join(" | ") : "; no page errors"));
  await p.close();
}
await b.close();
process.exit(bad ? 1 : 0);
