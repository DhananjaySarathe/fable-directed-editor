// node kit/hf/demos/takeover/shoot.mjs [page ...] [--out <dir>]    (pages: output/temp/demos/takeover/<page>.html; default
// whitespace canvas_studio studio_whitespace). For every transition the page logs (window.__trans) it takes five stills:
// 0.3 s before it, the last frame before the cut, the cut, +0.2 s and +0.55 s (a zoom-through's start / peak / end, a
// fade's or a morph's start / middle / end), and puts them in one row of <out>/<page>_sheet.png, with the speaker
// contract (window.__speaker kind) under each still. It also checks what a takeover promises: window.__speaker reports
// "off" in the middle of every takeover and "on" a second after it, and the budget (HF.trans.check) holds. Exit 1 on a
// page error or a broken promise. Videos are hidden; fonts.ready is awaited with a guard (a missing face can hang it).
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const HERE = path.dirname(fileURLToPath(import.meta.url)), REPO = path.resolve(HERE, "../../../..");
const puppeteer = createRequire(path.join(REPO, "package.json"))("puppeteer-core");
const args = process.argv.slice(2), oi = args.indexOf("--out");
const OUT = oi >= 0 ? path.resolve(args[oi + 1]) : path.join(REPO, "output/temp/demos/takeover/shots");
const pages = (oi >= 0 ? args.filter((_, i) => i !== oi && i !== oi + 1) : args);
const PAGES = path.join(REPO, "output/temp/demos/takeover");
fs.mkdirSync(OUT, { recursive: true });
const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true,
  args: ["--allow-file-access-from-files"], protocolTimeout: 180000 });
let bad = 0;
for (const name of pages.length ? pages : ["whitespace", "canvas_studio", "studio_whitespace", "reel_whitespace"]) {
  const p = await b.newPage(), errs = [], warns = [];
  p.on("pageerror", (e) => errs.push(String(e.message || e)));
  p.on("console", (m) => { if (m.type() === "warning" || m.type() === "error") warns.push(m.text()); });
  const portrait = /reel/.test(name), [VW, VH] = portrait ? [1080, 1920] : [1920, 1080];
  await p.setViewport({ width: VW, height: VH, deviceScaleFactor: 1 });
  await p.goto("file://" + path.join(PAGES, name + ".html"), { waitUntil: "domcontentloaded" });
  await p.waitForFunction(() => window.__timelines && Object.keys(window.__timelines).length > 0, { timeout: 90000 });
  await p.evaluate(() => Promise.race([document.fonts ? document.fonts.ready : null, new Promise((r) => setTimeout(r, 4000))]));
  const info = await p.evaluate(() => ({ trans: window.__trans ? window.__trans() : [], check: HF.trans.check(window.__trans()), takeovers: window.__takeovers || [] }));
  const seek = async (t) => { await p.evaluate((t) => { document.querySelectorAll("video").forEach((v) => (v.style.visibility = "hidden"));
    Object.values(window.__timelines)[0].seek(t, false); }, t); await new Promise((r) => setTimeout(r, 300)); };
  const spk = (t) => p.evaluate((t) => { const s = window.__speaker ? window.__speaker(t) : null; return s ? { on: s.on, kind: s.kind, lens: s.lens, zoom: s.zoom } : null; }, t);
  // the promises: off inside each takeover, on again a second after it
  const promises = [];
  for (const k of info.takeovers) {
    const mid = await spk((k.a + k.b) / 2), after = await spk(k.b + 1);
    promises.push({ a: k.a, b: k.b, kind: k.kind, mid: mid && mid.kind, after: after && after.kind, ok: !!(mid && !mid.on && after && after.on) });
  }
  const rows = [], dir = path.join(OUT, name);
  fs.mkdirSync(dir, { recursive: true });
  for (const tr of info.trans) {
    const ts = [tr.t - 0.3, tr.t - 1 / 30, tr.t, tr.t + 0.2, tr.t + 0.55].map((t) => +Math.max(0, t).toFixed(3));
    const shots = [];
    for (const t of ts) {
      await seek(t);
      const f = path.join(dir, `${tr.kind}_${tr.t.toFixed(2)}_${t.toFixed(3)}.png`);
      await p.screenshot({ path: f });
      shots.push({ t, f, s: await spk(t) });
    }
    rows.push({ tr, shots });
  }
  // the sheet: one row per transition, built as a page and screenshotted (no image library needed)
  const html = `<html><body style="margin:0;background:#e9e9ee;font:600 15px/1.2 -apple-system,Helvetica,sans-serif;color:#16161c">` + rows.map((r) =>
    `<div style="display:flex;align-items:flex-start;gap:6px;padding:8px 10px"><div style="width:150px;flex:none;padding-top:70px"><b style="font-size:20px">${r.tr.kind}</b><br>${r.tr.t.toFixed(2)} s<br><span style="font-weight:400">${r.tr.why}</span></div>` +
    r.shots.map((s) => `<div style="width:340px"><img src="file://${s.f}" style="width:${portrait ? 108 : 340}px;height:191px;display:block;border:1px solid #c8c8d0"><div style="padding:3px 2px">${s.t.toFixed(3)} s · ${s.s ? s.s.kind + (s.s.lens ? " · " + s.s.lens : "") : "-"}</div></div>`).join("") + `</div>`).join("") + `</body></html>`;
  const sheetHtml = path.join(dir, "sheet.html");
  fs.writeFileSync(sheetHtml, html);
  const q = await b.newPage();
  await q.setViewport({ width: 1900, height: 400, deviceScaleFactor: 1 });
  await q.goto("file://" + sheetHtml, { waitUntil: "load" });
  await q.screenshot({ path: path.join(OUT, `${name}_sheet.png`), fullPage: true });
  await q.close();
  const report = { page: name, errs, warns, trans: info.trans, check: info.check, promises, rows: rows.map((r) => ({ tr: r.tr, shots: r.shots.map((s) => ({ t: s.t, s: s.s })) })) };
  fs.writeFileSync(path.join(OUT, `${name}.json`), JSON.stringify(report, null, 1));
  const broken = promises.filter((x) => !x.ok);
  console.log(`${name}: ${info.trans.length} transitions [${info.trans.map((x) => `${x.t.toFixed(1)} ${x.kind}`).join(", ")}]`);
  console.log(`  budget: ${info.check.ok ? "ok" : info.check.findings.join("; ")}; whips ${Math.round(100 * info.check.whips)} %`);
  console.log(`  takeovers: ${promises.map((x) => `${x.a}-${x.b} ${x.kind} mid ${x.mid} after ${x.after}`).join(" | ")}${broken.length ? "  BROKEN" : "  ok"}`);
  console.log(`  ${errs.length ? "page errors: " + errs.slice(0, 3).join(" | ") : "no page errors"}${warns.length ? `; warnings: ${warns.slice(0, 4).join(" | ")}` : ""}`);
  console.log(`  sheet: ${path.join(OUT, name + "_sheet.png")}`);
  if (errs.length || broken.length || !info.check.ok) bad++;
  await p.close();
}
await b.close();
process.exit(bad ? 1 : 0);
