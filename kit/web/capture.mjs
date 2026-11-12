// kit/web/capture.mjs: a real product's website as Reel material (2026-10-11, the owner: "when we are talking about
// instinct, show their logo, or just scroll their website... such references are really useful; going forward, do it").
//
//   node kit/web/capture.mjs <url> <out dir> [--width=390] [--dpr=2.77] [--wait=3000] [--el=<css selector>[,<selector>...]] [--el-dpr=6]
//   --desktop: a desktop browser (desktop user agent, 16:9 viewport) for 16:9 films, e.g. --desktop --width=1440 --dpr=2
//
// Writes, into <out dir>:
//   page.png        the full page at phone width (390 css px x 2.77 = 1080 px wide: a 9:16 frame's width), for a scroll
//   viewport.png    the first screen only (what you see on arrival)
//   el-<n>.png      each --el element alone at --el-dpr (a crisp logo / mark), on the page's own background
//   capture.json    { url, width, dpr, pageH, elements: [{ selector, rect }] } (rects in css px, for pans/zooms)
// A screenshot of the live page (no asset files fetched from the server). Use it as a reference shot of the product:
// the logo and the site as they are; never as a fake of the product's own UI.
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";

const [url, out] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const opt = (k, d) => { const a = process.argv.find((x) => x.startsWith(`--${k}=`)); return a ? a.split("=").slice(1).join("=") : d; };
if (!url || !out) { console.error("usage: node kit/web/capture.mjs <url> <out dir> [--width=390] [--dpr=2.77] [--wait=3000] [--el=sel,...]"); process.exit(2); }
const width = +opt("width", 390), dpr = +opt("dpr", 2.77), wait = +opt("wait", 3000), elDpr = +opt("el-dpr", 6);
const desktop = process.argv.includes("--desktop");
const vh = desktop ? Math.round(width * 9 / 16) : Math.round(width * 16 / 9);
const sels = (opt("el", "") || "").split(",").map((s) => s.trim()).filter(Boolean);
fs.mkdirSync(out, { recursive: true });

const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const page = await browser.newPage();
await page.setUserAgent(desktop ? "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
  : "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1");
await page.setViewport({ width, height: vh, deviceScaleFactor: dpr, isMobile: !desktop, hasTouch: !desktop });
await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
await new Promise((r) => setTimeout(r, wait));
await page.screenshot({ path: path.join(out, "viewport.png") });
await page.screenshot({ path: path.join(out, "page.png"), fullPage: true });
const pageH = await page.evaluate(() => document.documentElement.scrollHeight);
const elements = [];
for (const [n, sel] of sels.entries()) {
  const rect = await page.evaluate((s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect();
    return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height }; }, sel);
  if (!rect) { console.error(`no element for ${sel}`); continue; }
  elements.push({ selector: sel, rect });
  await page.setViewport({ width, height: vh, deviceScaleFactor: elDpr, isMobile: !desktop, hasTouch: !desktop });
  const pad = 2;
  await page.screenshot({ path: path.join(out, `el-${n}.png`), clip: { x: rect.x - pad, y: rect.y - pad, width: rect.w + 2 * pad, height: rect.h + 2 * pad } });
  await page.setViewport({ width, height: vh, deviceScaleFactor: dpr, isMobile: !desktop, hasTouch: !desktop });
}
fs.writeFileSync(path.join(out, "capture.json"), JSON.stringify({ url, width, dpr, pageH, elements }, null, 1));
console.log(`${url} -> ${out}: page.png (${Math.round(width * dpr)} px wide, ${pageH} css px tall), viewport.png, ${elements.length} element(s)`);
await browser.close();
