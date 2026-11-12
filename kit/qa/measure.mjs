// Where things really land on screen: the bounding boxes of elements matching a selector at given times (3D turns,
// perspective and the camera included), for checking margins and gaps without a render.
//   node kit/qa/measure.mjs <index.html> <selector> <t1,t2,...>
import puppeteer from "puppeteer-core";
import path from "node:path";

const [src, sel, times] = process.argv.slice(2);
if (!times) { console.error("usage: node kit/qa/measure.mjs <index.html> <selector> <t1,t2,...>"); process.exit(2); }
const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true,
  args: ["--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
await page.goto("file://" + path.resolve(src), { waitUntil: "domcontentloaded" });
await page.waitForFunction(() => window.__timelines && Object.keys(window.__timelines).length > 0, { timeout: 60000 });
for (const t of times.split(",").map(Number)) {
  const rows = await page.evaluate((t, sel) => {
    Object.values(window.__timelines)[0].seek(t, false);
    const root = document.getElementById("root") || document.body, rr = root.getBoundingClientRect();
    return [...document.querySelectorAll(sel)].filter((e) => e.checkVisibility({ opacityProperty: true, visibilityProperty: true })).map((e) => {
      const r = e.getBoundingClientRect();
      return `${String(e.textContent || e.id || e.className).replace(/\s+/g, " ").trim().slice(0, 22).padEnd(22)} x ${Math.round(r.left - rr.left)}..${Math.round(r.right - rr.left)}  y ${Math.round(r.top - rr.top)}..${Math.round(r.bottom - rr.top)}`;
    });
  }, t, sel);
  console.log(`t ${t}`); rows.forEach((r) => console.log("  " + r));
}
await browser.close();
