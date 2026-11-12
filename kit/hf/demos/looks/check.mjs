// Phase 3 check (kit/refs/AUDIT_2026-10-20.md §6): the same components in every look must read. Per look page
// (kit/hf/demos/looks/build.py) and per scene, it measures every visible run of text against the background it really
// sits on (the composited background colours of its ancestors over the world), finds broken markup (unfilled "${...}",
// a style attribute cut short by a quote), and
// collects page errors. It saves a still per scene and one contact sheet (output/temp/demos/looks/sheet.png).
// Exit 1 if any text is under 3:1 (big type; precheck already gates size) or anything else fails.
//
//   node kit/hf/demos/looks/check.mjs [look ...]
import puppeteer from "puppeteer-core";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../../../..");
const OUT = path.join(ROOT, "output/temp/demos/looks");
// "whitespace:studio" = the whitespace look through HF.studio { look } (its page is whitespace_studio/, its look whitespace)
const looks = process.argv.slice(2).length ? process.argv.slice(2) : ["pastel_box", "canvas_studio", "redline", "night", "paper_studio", "paper_collage", "whitespace", "whitespace:studio"];
execFileSync("python3", [path.join(HERE, "build.py"), ...looks], { cwd: ROOT, stdio: "inherit" });
const TIMES = [[2.6, "pr + stamp"], [6.6, "checklist + note"], [10.8, "scoreboard + flow"], [14.4, "code + compare"], [18.6, "sketch + stickman"]];
fs.mkdirSync(path.join(OUT, "shots"), { recursive: true });

// in the page: every visible text run, its colour and the colour behind it, and the contrast ratio
const measure = () => {
  const root = document.getElementById("root");
  const shown = (e) => e.checkVisibility({ opacityProperty: true, visibilityProperty: true });
  const alpha = (e) => { let a = 1; for (let p = e; p && p !== root; p = p.parentElement) a *= +getComputedStyle(p).opacity; return a; };
  const rgba = (s) => { const m = String(s).match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [v[0], v[1], v[2], v[3] == null ? 1 : v[3]]; };
  const over = (top, bot) => [0, 1, 2].map((k) => top[k] * top[3] + bot[k] * (1 - top[3])).concat(1);
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const world = rgba(getComputedStyle(root).backgroundColor) || [255, 255, 255, 1];
  const base = world[3] ? world : rgba(getComputedStyle(document.documentElement).getPropertyValue("--paper").trim().replace(/^#(..)(..)(..)$/, (m, r, g, b) => `rgb(${parseInt(r, 16)},${parseInt(g, 16)},${parseInt(b, 16)})`)) || [255, 255, 255, 1];
  // the background a text sits on: its ancestors' background colours composited over the world, ignoring gradients and
  // pictures (a card's own colour is what the text needs to read against). A layer with only a picture behind it is skipped.
  const bgOf = (e) => {
    const chain = [];
    for (let p = e; p && p !== root; p = p.parentElement) chain.push(p);
    let c = base.slice();
    for (const p of chain.reverse()) { const b = rgba(getComputedStyle(p).backgroundColor); if (b && b[3] > 0) c = over(b, c); }
    return c;
  };
  const out = [], tmpl = [];
  for (const e of root.querySelectorAll("*")) {
    if (e.closest("[data-decor]")) continue;
    if ((e.getAttribute("style") || "").includes("${")) tmpl.push(e.getAttribute("style").slice(0, 80));
    // a style="..." cut short by a quote inside it (a font token with double quotes, 2026-10-20) leaves CSS as attribute names
    const junk = [...e.attributes].filter((a) => /[;:,()'"]|^sans-serif|^serif|^monospace|^cursive/.test(a.name));
    if (junk.length) tmpl.push(`<${e.tagName.toLowerCase()} ${junk.map((a) => a.name).join(" ")}>`);
    const own = [...e.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim();
    if (!own || !shown(e) || alpha(e) < 0.6) continue;
    if (own.includes("${")) tmpl.push(own.slice(0, 80));
    const r = e.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.right < 0 || r.left > 1920 || r.bottom < 0 || r.top > 1080) continue;
    const cs = getComputedStyle(e), fg = rgba(e instanceof SVGElement ? cs.fill : cs.color);
    if (!fg || fg[3] < 0.05) continue;
    const bg = bgOf(e), col = over(fg, bg);
    out.push({ text: own.slice(0, 36), ratio: +ratio(col, bg).toFixed(2), px: parseFloat(cs.fontSize) || 0, fg: cs.color, family: cs.fontFamily.split(",")[0] });
  }
  return { texts: out, tmpl, look: document.documentElement.dataset.look || "paper_studio" };
};

const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true,
  args: ["--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"] });
let bad = 0;
const shots = [];
for (const look of looks) {
  const page = await browser.newPage(), errs = [];
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  page.on("pageerror", (e) => errs.push(String(e.message || e)));
  await page.goto("file://" + path.join(OUT, look.replace(":", "_"), "index.html"), { waitUntil: "load" });
  await page.waitForFunction(() => window.__timelines && Object.keys(window.__timelines).length > 0, { timeout: 60000 }).catch(() => {});
  // fonts.ready behind a 4 s guard: a page with a face that never loads can hang it forever
  await page.evaluate(() => Promise.race([document.fonts ? document.fonts.ready : null, new Promise((r) => setTimeout(r, 4000))]));
  const lines = [];
  let low = [], fams = new Set(), texts = 0, tm = [], got = null;
  for (const [t, what] of TIMES) {
    await page.evaluate((t) => { const tl = Object.values(window.__timelines || {})[0]; if (tl) tl.seek(t, false); }, t);
    await new Promise((r) => setTimeout(r, 120));
    const m = await page.evaluate(measure).catch((e) => { errs.push(String(e)); return { texts: [], tmpl: [] }; });
    got = m.look;
    texts += m.texts.length; tm.push(...m.tmpl);
    m.texts.forEach((x) => fams.add(x.family));
    const lo = m.texts.filter((x) => x.ratio < 3);
    low.push(...lo.map((x) => `${t}s "${x.text}" ${x.ratio}:1 (${x.fg})`));
    const f = path.join(OUT, "shots", `${looks.indexOf(look)}_${look.replace(":", "_")}_${String(t).replace(".", "_")}.png`);
    await page.screenshot({ path: f });
    shots.push(f);
    const min = m.texts.length ? Math.min(...m.texts.map((x) => x.ratio)) : null;
    lines.push(`    ${String(t).padStart(4)} s ${what.padEnd(18)} ${String(m.texts.length).padStart(3)} texts, lowest contrast ${min == null ? "-" : min + ":1"}`);
  }
  await page.close();
  const want = look.split(":")[0], ok = !errs.length && !low.length && !tm.length && got === want;
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"}  ${look.padEnd(17)} ${texts} texts in ${[...fams].join(" / ")}${got !== want ? `  (the page's look is ${got})` : ""}`);
  lines.forEach((l) => console.log(l));
  low.slice(0, 8).forEach((l) => console.log("      low contrast: " + l));
  [...new Set(tm)].slice(0, 4).forEach((l) => console.log("      broken markup (unfilled ${...} or a cut style attribute): " + l));
  errs.slice(0, 4).forEach((l) => console.log("      page error: " + l));
}
await browser.close();
// the contact sheet: one row per look, one column per scene
const sheet = path.join(OUT, "sheet.png");
const list = path.join(OUT, "shots.txt");
fs.writeFileSync(list, shots.map((f) => `file '${f}'`).join("\n") + "\n");
execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", list, "-vf", `scale=640:360,tile=${TIMES.length}x${looks.length}:padding=6:color=white`, "-frames:v", "1", sheet]);
console.log(`\nsheet: ${sheet}`);
console.log(bad ? `${bad} look(s) FAIL` : "all looks ok");
process.exit(bad ? 1 : 0);
