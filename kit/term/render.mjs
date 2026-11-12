// Render a recording made by kit/term/rec.py to an MP4: each unique ANSI frame is drawn as a terminal in
// Chrome (puppeteer-core) and held for its real duration.
//
//   node kit/term/render.mjs <rec dir> <out.mp4> [--width 3840] [--fps 60] [--speed 1] [--from s] [--to s]
//
// --speed > 1 makes a time-lapse of a slice (e.g. --from 40 --to 300 --speed 8).
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const [dir, outFile] = args;
const WIDTH = +opt("width", 3840), FPS = +opt("fps", 60), SPEED = +opt("speed", 1);
const FROM = +opt("from", 0), TO = opt("to", null);
const meta = JSON.parse(fs.readFileSync(path.join(dir, "meta.json"), "utf8"));
const timeline = fs.readFileSync(path.join(dir, "timeline.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
const end = TO === null ? meta.duration : Math.min(+TO, meta.duration);

// ── ANSI → HTML ─────────────────────────────────────────────────────────────
const BG = "#16161e", FG = "#e6e6ec";
const BASE16 = ["#16161e", "#f7768e", "#9ece6a", "#e0af68", "#7aa2f7", "#bb9af7", "#7dcfff", "#c0caf5",
  "#565f89", "#ff7a93", "#b9f27c", "#ff9e64", "#7da6ff", "#c0a8ff", "#a4daff", "#ffffff"];
const c256 = n => {
  if (n < 16) return BASE16[n];
  if (n < 232) { n -= 16; const lv = [0, 95, 135, 175, 215, 255]; return `rgb(${lv[Math.floor(n / 36)]},${lv[Math.floor(n / 6) % 6]},${lv[n % 6]})`; }
  const g = 8 + (n - 232) * 10; return `rgb(${g},${g},${g})`;
};
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// Wide glyphs take two cells in the terminal; give them two cells here so columns stay aligned.
const WIDE = /(\p{Emoji_Presentation}|\p{Extended_Pictographic}️)/u;
const cells = s => esc(s).split(/(\p{Emoji_Presentation}️?|\p{Extended_Pictographic}️)/u)
  .map(p => (p && WIDE.test(p) ? `<i class=w>${p}</i>` : p)).join("");
function lineHtml(line) {
  const st = { fg: null, bg: null, b: 0, d: 0, i: 0, u: 0, inv: 0, s: 0 };
  let out = "", pos = 0;
  const span = t => {
    if (!t) return;
    let fg = st.fg || FG, bg = st.bg;
    if (st.inv) [fg, bg] = [bg || BG, st.fg || FG];
    const css = [`color:${fg}`];
    if (bg) css.push(`background:${bg}`);
    if (st.b) css.push("font-weight:700");
    if (st.d) css.push("opacity:.55");
    if (st.i) css.push("font-style:italic");
    const deco = [st.u && "underline", st.s && "line-through"].filter(Boolean);
    if (deco.length) css.push(`text-decoration:${deco.join(" ")}`);
    out += `<span style="${css.join(";")}">${cells(t)}</span>`;
  };
  const rx = /\x1b\[([0-9;:]*)m/g; let m;
  while ((m = rx.exec(line))) {
    span(line.slice(pos, m.index)); pos = rx.lastIndex;
    const p = (m[1] || "0").split(/[;:]/).map(x => +x || 0);
    for (let k = 0; k < p.length; k++) {
      const v = p[k];
      if (v === 0) Object.assign(st, { fg: null, bg: null, b: 0, d: 0, i: 0, u: 0, inv: 0, s: 0 });
      else if (v === 1) st.b = 1; else if (v === 2) st.d = 1; else if (v === 3) st.i = 1; else if (v === 4) st.u = 1;
      else if (v === 7) st.inv = 1; else if (v === 9) st.s = 1; else if (v === 22) st.b = st.d = 0;
      else if (v === 23) st.i = 0; else if (v === 24) st.u = 0; else if (v === 27) st.inv = 0; else if (v === 29) st.s = 0;
      else if (v >= 30 && v <= 37) st.fg = BASE16[v - 30]; else if (v >= 90 && v <= 97) st.fg = BASE16[v - 82];
      else if (v >= 40 && v <= 47) st.bg = BASE16[v - 40]; else if (v >= 100 && v <= 107) st.bg = BASE16[v - 92];
      else if (v === 39) st.fg = null; else if (v === 49) st.bg = null;
      else if ((v === 38 || v === 48) && k + 1 < p.length) {
        const key = v === 38 ? "fg" : "bg";
        if (p[k + 1] === 5) { st[key] = c256(p[k + 2]); k += 2; }
        else if (p[k + 1] === 2) { st[key] = `rgb(${p[k + 2]},${p[k + 3]},${p[k + 4]})`; k += 4; }
      }
    }
  }
  span(line.slice(pos));
  return out || "&nbsp;";
}
const OSC = /\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g;
const frameHtml = txt => {
  const lines = txt.replace(OSC, "").replace(/\n$/, "").split("\n");
  while (lines.length < meta.rows) lines.push("");
  return lines.slice(0, meta.rows).map(l => `<div>${lineHtml(l)}</div>`).join("");
};

// ── layout: fit cols × rows into WIDTH × WIDTH*9/16 ────────────────────────
const HEIGHT = Math.round(WIDTH * 9 / 16);
const PAD_X = Math.round(WIDTH * 0.03);
const fontPx = (WIDTH - 2 * PAD_X) / (meta.cols * 0.6021); // Menlo advance ≈ 0.602 em
const lineH = Math.min(fontPx * 1.2, (HEIGHT - 2 * PAD_X * 0.6) / meta.rows);
const page = `<!doctype html><meta charset=utf-8><style>
html,body{margin:0;background:${BG};width:${WIDTH}px;height:${HEIGHT}px;overflow:hidden}
#t{position:absolute;left:${PAD_X}px;top:${Math.round((HEIGHT - lineH * meta.rows) / 2)}px;
font:${fontPx.toFixed(3)}px/${lineH.toFixed(3)}px Menlo,'SF Mono',monospace;color:${FG};white-space:pre;
font-variant-ligatures:none;-webkit-font-smoothing:antialiased}
#t div{height:${lineH.toFixed(3)}px}
i.w{font-style:normal;display:inline-block;width:2ch;text-align:left}
</style><div id=t></div>`;

// ── render ──────────────────────────────────────────────────────────────────
const chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const browser = await puppeteer.launch({ executablePath: chrome, headless: "new", args: ["--hide-scrollbars"] });
const tab = await browser.newPage();
await tab.setViewport({ width: WIDTH, height: HEIGHT, deviceScaleFactor: 1 });
await tab.setContent(page);

const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
  "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-tune", "stillimage",
  "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", outFile],
  { stdio: ["pipe", "inherit", "inherit"] });
const write = buf => new Promise(r => (ff.stdin.write(buf) ? r() : ff.stdin.once("drain", r)));

// Output frame k shows the source frame whose time is the latest ≤ FROM + k*SPEED/FPS.
const total = Math.max(1, Math.round((end - FROM) / SPEED * FPS));
let idx = 0, shownFrame = -1, png = null, rendered = 0;
for (let k = 0; k < total; k++) {
  const t = FROM + k * SPEED / FPS;
  while (idx + 1 < timeline.length && timeline[idx + 1].t <= t) idx++;
  const f = timeline[idx].frame;
  if (f !== shownFrame) {
    const txt = fs.readFileSync(path.join(dir, "frames", `${String(f).padStart(5, "0")}.ansi`), "utf8");
    await tab.evaluate(h => { document.getElementById("t").innerHTML = h; }, frameHtml(txt));
    png = await tab.screenshot({ type: "png" });
    shownFrame = f; rendered++;
  }
  await write(png);
  if (k % (FPS * 10) === 0) process.stderr.write(`\r${(k / FPS).toFixed(0)}s / ${(total / FPS).toFixed(0)}s, ${rendered} frames drawn`);
}
ff.stdin.end();
await new Promise(r => ff.on("close", r));
await browser.close();
process.stderr.write(`\ndone: ${outFile} (${(total / FPS).toFixed(1)} s, ${rendered} unique frames)\n`);
