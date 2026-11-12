// Scroll through a Markdown file rendered like an editor's dark preview (mermaid diagrams drawn), as an MP4.
// It stops on every "## " heading, so each section can be cut to a line of voice.
//
//   node kit/term/docscroll.mjs <file.md> <out.mp4> [--dwell 2.2] [--move 1.1] [--fps 60] [--title "ONBOARDING.md"]
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import { spawn } from "node:child_process";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const [mdFile, outFile] = args;
const DWELL = +opt("dwell", 2.2), MOVE = +opt("move", 1.1), FPS = +opt("fps", 60);
const TITLE = opt("title", mdFile.split("/").pop());
const md = fs.readFileSync(mdFile, "utf8");

const page = `<!doctype html><meta charset=utf-8><style>
:root{--bg:#1e1f24;--fg:#d7dae0;--mut:#8b919c;--line:#33363d;--code:#2a2c33;--acc:#6aa6ff}
html,body{margin:0;background:var(--bg);color:var(--fg)}
.bar{position:fixed;top:0;left:0;right:0;height:44px;background:#18191d;border-bottom:1px solid var(--line);
display:flex;align-items:center;gap:10px;padding:0 18px;font:13px -apple-system,Helvetica;color:var(--mut);z-index:2}
.bar b{color:var(--fg);font-weight:500;background:var(--bg);padding:12px 16px;border-top:2px solid var(--acc)}
main{max-width:1040px;margin:0 auto;padding:84px 56px 600px;font:17px/1.65 -apple-system,'Segoe UI',Helvetica,Arial}
h1{font-size:2em;border-bottom:1px solid var(--line);padding-bottom:.3em}h2{font-size:1.5em;border-bottom:1px solid var(--line);padding-bottom:.3em;margin-top:1.6em}
code{background:var(--code);padding:.15em .4em;border-radius:5px;font:86% Menlo,monospace}
pre:not(.mermaid){background:var(--code);padding:14px 16px;border-radius:8px;overflow:hidden}pre code{background:none;padding:0}
table{border-collapse:collapse;margin:14px 0;width:100%}td,th{border:1px solid var(--line);padding:7px 12px;text-align:left;vertical-align:top}
tr:nth-child(2n){background:#23252b}a{color:var(--acc)}blockquote{border-left:4px solid var(--line);margin:0;padding:0 16px;color:var(--mut)}
details{background:#23252b;border:1px solid var(--line);border-radius:6px;padding:6px 12px;margin:6px 0}
.mermaid{text-align:center;margin:18px 0;background:none}
</style><div class=bar><b>${TITLE.replace(/</g, "&lt;")}</b><span>Preview</span></div><main id=out></main>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>
const r = new marked.Renderer(); const base = r.code.bind(r);
r.code = (code, lang) => lang === 'mermaid' ? '<pre class="mermaid">' + code.replace(/</g,'&lt;') + '</pre>' : base(code, lang);
document.getElementById('out').innerHTML = marked.parse(${JSON.stringify(md)}, {renderer: r});
mermaid.initialize({startOnLoad:false, theme:'dark'});
window.ready = mermaid.run().then(() => true);
</script>`;

const chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const browser = await puppeteer.launch({ executablePath: chrome, headless: "new", args: ["--hide-scrollbars"] });
const tab = await browser.newPage();
await tab.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });
await tab.setContent(page, { waitUntil: "networkidle0" });
await tab.evaluate(() => window.ready);
const stops = await tab.evaluate(() => {
  const max = document.documentElement.scrollHeight - innerHeight;
  const ys = [0, ...[...document.querySelectorAll("main h2")].map(h => Math.max(0, h.offsetTop - 70))];
  return [...new Set(ys.map(y => Math.min(y, max)))].sort((a, b) => a - b);
});

// Path: dwell on each stop, eased move to the next.
const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const ys = [];
for (let i = 0; i < stops.length; i++) {
  for (let k = 0; k < Math.round(DWELL * FPS); k++) ys.push(stops[i]);
  if (i + 1 < stops.length) {
    const n = Math.round(MOVE * FPS);
    for (let k = 1; k <= n; k++) ys.push(stops[i] + (stops[i + 1] - stops[i]) * ease(k / n));
  }
}

const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
  "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
  "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", outFile],
  { stdio: ["pipe", "inherit", "inherit"] });
const write = buf => new Promise(r => (ff.stdin.write(buf) ? r() : ff.stdin.once("drain", r)));
let lastY = null, png = null;
for (const y of ys) {
  const yy = Math.round(y);
  if (yy !== lastY) { await tab.evaluate(v => window.scrollTo(0, v), yy); png = await tab.screenshot({ type: "png" }); lastY = yy; }
  await write(png);
}
ff.stdin.end();
await new Promise(r => ff.on("close", r));
await browser.close();
const t = s => (s / FPS).toFixed(1);
let acc = 0; const marks = stops.map((_, i) => { const m = t(acc); acc += Math.round(DWELL * FPS) + Math.round(MOVE * FPS); return m; });
process.stderr.write(`done: ${outFile} (${t(ys.length)} s); section stops at ${marks.join(", ")} s\n`);
