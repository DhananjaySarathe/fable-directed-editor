// node kit/hf/demos/diagram/shoot.mjs [page ...] [--out <dir>]   (pages: output/temp/demos/diagram/<page>.html, from
// build.py; default: every page). Per page: stills at its check times into <out>/<page>/, one sheet <out>/<page>_sheet.png;
// the geometry gate (HF.diagram.verify on every window.__diagrams entry with gate: true) and the console's budget notes;
// seek purity (the same t reached forward, backward and by a jump gives the same DOM). Exit 1 on a page error, a
// geometry finding or an impure seek. Videos are hidden; fonts.ready is awaited with a guard.
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const HERE = path.dirname(fileURLToPath(import.meta.url)), REPO = path.resolve(HERE, "../../../..");
const puppeteer = createRequire(path.join(REPO, "package.json"))("puppeteer-core");
const args = process.argv.slice(2), oi = args.indexOf("--out");
const PAGES = path.join(REPO, "output/temp/demos/diagram");
const OUT = oi >= 0 ? path.resolve(args[oi + 1]) : path.join(PAGES, "shots");
const pages = oi >= 0 ? args.filter((_, i) => i !== oi && i !== oi + 1) : args;
// the check times: each scene complete and still, and mid-build (a step, an edge drawing, the token on its way)
const TIMES = {
  flat: [1.2, 2.6, 6.8, 8.2, 11.5, 13.8, 15.2, 18.5, 20.8, 22.6, 25.2, 27.8],
  portrait: [1.0, 2.6, 4.2, 7.8],
  legacy_old: [1.2, 3.0, 4.8, 6.0, 7.5, 9.8], legacy_fixed: [1.2, 3.0, 4.8, 6.0, 7.5, 9.8],
  takeover_whitespace: [3.5, 4.6, 5.5, 6.4, 8.5, 10.6, 11.6], takeover_canvas_studio: [3.5, 4.6, 5.5, 6.4, 8.5, 10.6, 11.6],
};
fs.mkdirSync(OUT, { recursive: true });
const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true,
  args: ["--allow-file-access-from-files"], protocolTimeout: 180000 });
let bad = 0;
for (const name of pages.length ? pages : Object.keys(TIMES)) {
  const p = await b.newPage(), errs = [], warns = [];
  p.on("pageerror", (e) => errs.push(String(e.message || e)));
  p.on("console", (m) => { if (m.type() === "warning" || m.type() === "error") warns.push(m.text()); });
  const portrait = name === "portrait", [VW, VH] = portrait ? [1080, 1920] : [1920, 1080];
  await p.setViewport({ width: VW, height: VH, deviceScaleFactor: 1 });
  await p.goto("file://" + path.join(PAGES, name + ".html"), { waitUntil: "domcontentloaded" });
  await p.waitForFunction(() => window.__timelines && Object.keys(window.__timelines).length > 0, { timeout: 90000 });
  await p.evaluate(() => Promise.race([document.fonts ? document.fonts.ready : null, new Promise((r) => setTimeout(r, 4000))]));
  const ts = TIMES[name] || [1, 3, 5];
  // geometry: every flat diagram through the gate
  const geo = await p.evaluate(() => (window.__diagrams || []).map((d) => ({ id: d.id, style: d.style, type: d.type, gate: d.gate, nodes: d.nodes.length,
    edges: d.edges.length, findings: d.gate ? HF.diagram.verify(d) : [] })));
  // seek purity: every visible element's state at each check time, reached forward, backward and by a jump from the end
  // (an element nobody sees may keep a tween's start values from one direction and not the other, GSAP's
  // immediateRender false, or a token's last position at opacity 0: those count as hidden)
  const pure = await p.evaluate((ts) => {
    const tl = Object.values(window.__timelines)[0], end = tl.duration(), els = [...document.querySelectorAll("#root div, #root svg *, #root img")];
    const seen = (e) => { let o = 1; for (let x = e; x && x.nodeType === 1; x = x.parentNode) { const cs = getComputedStyle(x);
      if (cs.visibility === "hidden" || cs.display === "none") return 0; o *= +cs.opacity * (x.getAttribute && x.getAttribute("opacity") != null ? +x.getAttribute("opacity") : 1); } return o; };
    const state = (t) => { tl.seek(t, false); return els.map((e) => {
      const cs = getComputedStyle(e), o = seen(e); if (o < 0.001) return "h";
      return [o.toFixed(3), e.style.transform || "", e.getAttribute("cx") || "", e.getAttribute("cy") || "", e.style.strokeDashoffset || "",
        cs.backgroundColor, cs.borderTopColor, cs.color].join("|"); }).join(";"); };
    const fwd = ts.map(state), back = ts.slice().reverse().map(state).reverse(), jump = ts.map((t) => { tl.seek(end - 0.01, false); return state(t); });
    return { back: fwd.every((x, i) => x === back[i]), jump: fwd.every((x, i) => x === jump[i]),
      bad: ts.filter((t, i) => fwd[i] !== back[i] || fwd[i] !== jump[i]) };
  }, ts);
  const dir = path.join(OUT, name);
  fs.mkdirSync(dir, { recursive: true });
  const shots = [];
  for (const t of ts) {
    await p.evaluate((t) => { document.querySelectorAll("video").forEach((v) => (v.style.visibility = "hidden")); Object.values(window.__timelines)[0].seek(t, false); }, t);
    await new Promise((r) => setTimeout(r, 300));
    const f = path.join(dir, `${name}_${t.toFixed(2)}.png`);
    await p.screenshot({ path: f });
    shots.push({ t, f });
  }
  const w = portrait ? 270 : 600, h = portrait ? 480 : 338;
  const html = `<html><body style="margin:0;background:#e9e9ee;font:600 15px/1.2 -apple-system,Helvetica,sans-serif;color:#16161c;display:flex;flex-wrap:wrap;gap:8px;padding:8px;width:${portrait ? 1180 : 1840}px">` +
    shots.map((s) => `<div><img src="file://${s.f}" style="width:${w}px;height:${h}px;display:block;border:1px solid #c8c8d0"><div style="padding:3px 2px">${name} · ${s.t.toFixed(2)} s</div></div>`).join("") + "</body></html>";
  const sheet = path.join(dir, "sheet.html");
  fs.writeFileSync(sheet, html);
  const q = await b.newPage();
  await q.setViewport({ width: portrait ? 1200 : 1860, height: 400, deviceScaleFactor: 1 });
  await q.goto("file://" + sheet, { waitUntil: "load" });
  await q.screenshot({ path: path.join(OUT, `${name}_sheet.png`), fullPage: true });
  await q.close();
  const findings = geo.flatMap((d) => d.findings.map((x) => `${d.id}: ${x}`));
  fs.writeFileSync(path.join(OUT, `${name}.json`), JSON.stringify({ page: name, errs, warns, geo, pure }, null, 1));
  console.log(`${name}: ${geo.length} diagrams [${geo.map((d) => `${d.id} ${d.style}${d.type ? " " + d.type : ""} ${d.nodes}n/${d.edges}e`).join(", ")}]`);
  console.log(`  geometry: ${findings.length ? findings.join(" | ") : "ok"}; seek: ${pure.back && pure.jump ? "pure" : "IMPURE at " + pure.bad.join(", ")}`);
  console.log(`  ${errs.length ? "page errors: " + errs.slice(0, 3).join(" | ") : "no page errors"}${warns.length ? `; notes: ${warns.slice(0, 6).join(" | ")}` : ""}`);
  console.log(`  sheet: ${path.join(OUT, name + "_sheet.png")}`);
  if (errs.length || findings.length || !(pure.back && pure.jump)) bad++;
  await p.close();
}
await b.close();
process.exit(bad ? 1 : 0);
