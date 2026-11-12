// Repro checks for the kit bugs in kit/refs/AUDIT_2026-10-20.md §3 (all hit on films/xchakra, 2026-10-20). Each line
// prints ok or FAIL with what was measured; exit 1 if any bug is back. Since 2026-10-22 (kit v11) also the planning
// gates: plan_check's schema 2 budgets (visual_plan_v2.json, clean and broken) and precheck's SPEAKER / DENSITY /
// transitions sections on the speaker fixture (src/speaker.html, with window.__speaker and with only __faceRect).
//
//   node kit/hf/demos/audit/check.mjs            # builds the fixture pages (build.py) first; ~20 s
import puppeteer from "puppeteer-core";
import { execFileSync } from "node:child_process";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));          // (a URL's pathname keeps "%20" for the space in the repo path)
const ROOT = path.resolve(HERE, "../../../..");
const OUT = path.join(ROOT, "output/temp/demos/audit");
const sh = (cmd, args, o = {}) => execFileSync(cmd, args, { cwd: ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], ...o });
sh("python3", [path.join(HERE, "build.py")]);

let bad = 0;
const check = (name, ok, got) => { if (!ok) bad++; console.log(`${ok ? "ok  " : "FAIL"}  ${name}${got != null ? `  (${got})` : ""}`); };

const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true,
  args: ["--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"] });
async function open(name) {
  const page = await browser.newPage(), errs = [];
  page.on("pageerror", (e) => errs.push(String(e.message || e)));
  await page.goto("file://" + path.join(OUT, name, "index.html"), { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => window.__timelines && Object.keys(window.__timelines).length > 0, { timeout: 60000 });
  return { page, errs };
}
// in the page: seek, then measure
const at = (page, t, fn) => page.evaluate((t, src) => { Object.values(window.__timelines)[0].seek(t, false); return (0, eval)(src)(window.__audit); }, t, `(${fn})`);
const accents = (A) => [A.acc1, A.acc2].map((b) => ({ text: b.textContent.replace(/\s+/g, " ").trim(),
  it: [...b.querySelectorAll("span > span")].filter((s) => s.style.fontStyle === "italic").map((s) => s.textContent) }));
const accOk = (r) => !r.some((x) => x.text.includes("*")) && r[0].it.join(" ") === "HackerRank?" && r[1].it.join(" ") === "several words";

// ---------------------------------------------------------------- 16:9 (HF.studio)
{
  const { page, errs } = await open("studio");
  const r = await at(page, 2, accents);
  check("studio line(): *word* and *several words* accents, no literal *", accOk(r), r.map((x) => `"${x.text}" [${x.it.join(", ")}]`).join(" / "));
  const z = await at(page, 0, () => [3.8, 4.25].map((t) => { const s = HF.box.at(window.__box.plan, t); return { w: Math.round(s.w * 1920), zoom: +s.zoom.toFixed(3) }; }));
  check("studio box: a jump cut inside a card reframes (footage zoom changes, still a card)", z[0].w < 1700 && z[1].w < 1700 && Math.abs(z[1].zoom - z[0].zoom) > 0.05,
    `3.8 s: w ${z[0].w} zoom ${z[0].zoom}; 4.25 s: w ${z[1].w} zoom ${z[1].zoom}`);
  const st = await at(page, 0, (A) => [3, 5.6].map((t) => { Object.values(window.__timelines)[0].seek(t, false); return +getComputedStyle(A.strikeEnd).opacity; }));
  check("studio strike(..., until): up while drawn, gone after its end", st[0] > 0.9 && st[1] < 0.05, `opacity at 3 s ${st[0]}, at 5.6 s ${st[1]}`);
  const t0 = await at(page, 0, (A) => A.say.t0);
  check("studio say() returns t0 (the first word's time)", t0 === 0.5, t0);
  // precheck on the page: the chapter card over the face is not "text over the face"; HF.code's title bar is window chrome;
  // the strike with no end is a linger; the ambition section prints
  const pc = (() => { try { return sh("node", ["kit/qa/precheck.mjs", path.join(OUT, "studio/index.html"), "--no-ambition"]); } catch (e) { return e.stdout || ""; } })();
  // the finding lines only (the last line also names the HIGH kinds since 2026-10-22: "precheck FAIL: ... [linger ...]")
  const found = pc.split("\n").filter((l) => /^\s+(HIGH|MEDIUM)\s/.test(l));
  const faceInChapter = found.filter((l) => /\bface\b/.test(l) && /00:(09|10|11)\./.test(l));
  check("precheck: text on an opaque chapter card over the face is not a face finding", !faceInChapter.length, faceInChapter[0] || "none");
  const smallTitle = found.filter((l) => /small/.test(l) && /solution\.py/.test(l));
  check("precheck: HF.code's title bar (window chrome) is not 'small'", !smallTitle.length, smallTitle[0] || "none");
  const lingers = found.filter((l) => /linger/.test(l));
  check("precheck: a strike on FRONT with no end is a 'linger'; the one with an end is not", lingers.length === 1 && /00:01\.[0-4]/.test(lingers[0]), lingers.map((l) => l.trim().slice(0, 70)).join(" | ") || "none");
  check("precheck: prints the ambition section", /ambition: components/.test(pc) && /ambition: layouts/.test(pc) && /ambition: longest stretch/.test(pc) && /moves\/min/.test(pc),
    (pc.match(/ambition: layouts[^\n]*/) || ["missing"])[0]);
  check("studio page: no page errors", !errs.length, errs[0]);
  await page.close();
}
// ---------------------------------------------------------------- 9:16 (HF.reel, a 16:9 camera)
{
  const { page, errs } = await open("reel");
  const v = await at(page, 1, () => { const v = document.getElementById("aroll"); return [v.offsetWidth, v.offsetHeight]; });
  check("reel src: [1920, 1080] keeps a 16:9 camera 16:9 (not forced portrait)", v[0] === 1920 && v[1] === 1080, v.join("x"));
  const w = await at(page, 1, (A) => ({ a: A.say.items.map((s) => s._a), ids: A.say.items.map((s) => s.dataset.w), t0: A.say.t0 }));
  check("reel say(): words record their times (_a), ids (data-w) and t0", w.a.every((x) => typeof x === "number") && w.ids.join() === "0,1,2" && w.t0 === 0.5,
    `_a ${w.a.join(", ")}; ids ${w.ids.join(",")}; t0 ${w.t0}`);
  const r = await at(page, 2, accents);
  check("reel line(): *word* and *several words* accents, no literal *", accOk(r), r.map((x) => `"${x.text}" [${x.it.join(", ")}]`).join(" / "));
  const st = await at(page, 0, (A) => [2.5, 4.0].map((t) => { Object.values(window.__timelines)[0].seek(t, false); return +getComputedStyle(A.strikeEnd).opacity; }));
  check("reel strike(..., until): gone after its end", st[0] > 0.9 && st[1] < 0.05, `opacity at 2.5 s ${st[0]}, at 4 s ${st[1]}`);
  const z = await at(page, 0, () => [3.8, 4.25].map((t) => { const s = HF.box.at(window.__box.plan, t); return { h: Math.round(s.h * 1920), zoom: +s.zoom.toFixed(3) }; }));
  check("reel box: a jump cut inside a card reframes", z[0].h < 1700 && Math.abs(z[1].zoom - z[0].zoom) > 0.05, `3.8 s: zoom ${z[0].zoom}; 4.25 s: zoom ${z[1].zoom}`);
  check("reel page: no page errors", !errs.length, errs[0]);
  await page.close();
}
await browser.close();

// ---------------------------------------------------------------- the pipeline pieces
const mods = sh("python3", ["-c", "import sys; sys.path.insert(0, 'kit/hf'); import vendor; print(' '.join(dict.fromkeys(vendor.MODULES)))"]).trim().split(" ");
check("vendor.MODULES has the Reel kit (reel.js, footage.js, agent.js, night_reel.js)", ["reel.js", "footage.js", "agent.js", "night_reel.js"].every((m) => mods.includes(m)));
const run = (cmd, args) => { try { return { ok: true, out: sh(cmd, args) }; } catch (e) { return { ok: false, out: String(e.stdout || "") + String(e.stderr || e) }; } };
{ const r = run("uv", ["run", "python", "-m", "kit.cut.relisten", "--help"]);
  check("kit.cut.relisten: a film's own joins re-listened from its edl.json (no take analysis)", r.ok && /usage: .*EDL\.json MEDIA/.test(r.out), r.out.trim().split("\n").pop().slice(0, 90)); }
{ const r = run("python3", ["kit/hf/render4k.py", "output/temp/demos/audit/studio", "--plan"]);
  check("kit/hf/render4k.py: the chunked 4K renderer is a kit tool (any project, --plan)", r.ok && /1 chunks, 780 frames/.test(r.out), r.out.trim().split("\n").pop()); }
{ const r = run("python3", ["kit/hf/tools/registry.py", "--check"]);
  check("registry.json lists every component the kit defines, each with looks", r.ok && /^ok/.test(r.out.trim()), r.out.trim().split("\n")[0]); }
{ const r = run("python3", ["kit/hf/plan_check.py", "kit/hf/demos/audit/visual_plan.json"]);
  check("plan_check.py accepts the new registry ids (a plan using them)", r.ok, r.out.trim().split("\n").pop()); }
// ---------------------------------------------------------------- kit v11 planning (2026-10-22)
// schema 2: a clean long-form plan passes; the same plan broken on purpose trips each budget
{ const r = run("python3", ["kit/hf/plan_check.py", "kit/hf/demos/audit/visual_plan_v2.json"]);
  check("plan_check schema 2: a clean long-form plan (15-30 % face off, cam moves, varied transitions) passes", r.ok && /^PASS/m.test(r.out), r.out.trim().split("\n").pop());
  const plan = JSON.parse(fs.readFileSync(path.join(HERE, "visual_plan_v2.json"), "utf8")), by = Object.fromEntries(plan.passages.map((p) => [p.id, p]));
  by.p1.face = "off";                                  // the hook off his face
  by.p4.face = "off";                                  // p3 + p4: 17 s away
  // zoom twice in a row (p14 -> p15: both face on; a takeover's same-kind in and out, p13 -> p14, is one bracket)
  by.p14.transition = "zoom"; by.p15.transition = "zoom";
  by.p10.cam = "hold";                                 // 15 s held on him
  by.p8.groups = 5;                                    // heavy
  by.p2.music = "drop";                                // a drop on a calm long-form bed
  fs.mkdirSync(path.join(OUT, "plans"), { recursive: true });
  const bad = path.join(OUT, "plans/visual_plan_v2_bad.json");
  fs.writeFileSync(bad, JSON.stringify(plan));
  const b = run("python3", ["kit/hf/plan_check.py", bad]);
  const want = [/ERROR .*p1: face off at 0\.0 s: the hook opens on his face/, /ERROR .*p3\+p4: away from him 17\.0 s/, /WARN .*p14 -> p15: transition 'zoom' twice in a row/,
    /WARN .*p10: cam 'hold' on him for 15\.0 s/, /WARN .*p8: heavy: 5 visual groups/, /WARN .*long-form beds are calm .*p2 \(drop\)/];
  const miss = want.filter((w) => !w.test(b.out));
  check("plan_check schema 2: the broken plan trips the hook, away, repeat, hold, heavy and calm-bed rules (exit 3)", !b.ok && !miss.length,
    miss.length ? "missing " + miss.map(String).join(" ") : (b.out.match(/^FAIL: [^\n]*/m) || [b.out.trim().split("\n").pop()])[0]);
}
// precheck's SPEAKER / DENSITY / transitions sections on the speaker fixture (src/speaker.html): the contract, then the
// __faceRect fallback a page from before v11 gives
{ const pc = (name) => run("node", ["kit/qa/precheck.mjs", path.join(OUT, name, "index.html")]).out;
  const s = pc("speaker"), f = pc("speaker_fallback"), bh = pc("speaker_boxhidden"), pl = pc("speaker_plate");
  const has = (out, re) => re.test(out);
  check("precheck speaker (contract): framing HIGH 0-21.4 s, the declared hold at 30-40 s is not a finding", has(s, /HIGH\s+framing\s+00:00\.0-00:21\.4/) && !has(s, /framing\s+00:30\.0/),
    (s.match(/^.*framing .*$/m) || ["none"])[0].trim().slice(0, 90));
  check("precheck speaker (contract): away 13 s HIGH, upscale over the tracks.json budget, the shares", has(s, /HIGH\s+away\s+00:40\.0-00:53\.0/) && has(s, /MEDIUM\s+upscale/)
    && has(s, /speaker: face on 68%, off 32%, full frame 17%; takeovers 2 \(6\.0 s, 13\.0 s\)/) && has(s, /\[window\.__speaker\]/), (s.match(/speaker: face on[^\n]*/) || ["none"])[0]);
  check("precheck density: > 3 groups for 7 s MEDIUM, 7 groups HIGH; captions and decor don't count", has(s, /MEDIUM\s+density\s+00:05\.0-00:12\.0/) && has(s, /HIGH\s+density\s+00:14\.0-00:17\.4/)
    && has(s, /density: visual groups per sample p50 0, p90 5, max 7/), (s.match(/density: [^\n]*/) || ["none"])[0]);
  check("precheck transitions: window.__trans by kind, 'whip' twice in a row is MEDIUM", has(s, /transitions: 5 \(whip 2, cut 2, zoom 1\), whips 40%, 1 repeats/) && has(s, /MEDIUM\s+trans\s+00:20\.0-00:24\.0/),
    (s.match(/transitions: [^\n]*/) || ["none"])[0]);
  check("precheck layout from __speaker: card left + card right are one layout (52 % -> HIGH), the split printed", has(s, /HIGH\s+layout .*"card beside" for 52 %/)
    && has(s, /ambition: layouts card beside 52% \(right 40%, left 12%\)/), (s.match(/ambition: layouts[^\n]*/) || ["none"])[0]);
  // review 2026-10-22: kit/film prints only the tail of precheck's output, so the last line repeats the verdict and
  // names every HIGH
  // (run() appends the exit error after stdout: find the summary and check nothing of precheck's comes after it)
  const L = s.split("\n"), iSum = L.findIndex((l) => /^precheck (PASS|WARN|FAIL):/.test(l)), last = iSum >= 0 ? L[iSum] : "missing";
  check("precheck: the last line repeats the verdict with every HIGH (kit/film prints the tail)",
    iSum > L.findIndex((l) => /^  transitions:/.test(l)) && !L.slice(iSum + 1).some((l) => /^\s{2}\S/.test(l))
    && /^precheck FAIL: \d+ HIGH \[/.test(last) && /framing 00:00\.0/.test(last) && /away 00:40\.0/.test(last) && /layout 00:00\.0/.test(last), last.slice(0, 110));
  check("precheck speaker fallback (__faceRect only): same face shares, no zoom, the undeclared 10 s hold is MEDIUM, away estimated (MEDIUM)",
    has(f, /\[__faceRect fallback: on \/ off estimated/) && has(f, /speaker: face on 68%, off 32%, full frame n\/a/) && has(f, /MEDIUM\s+framing\s+00:30\.0-00:40\.0/)
    && has(f, /MEDIUM\s+away\s+00:40\.0-00:53\.0 .*estimated \(no window\.__speaker\)/) && !has(f, /HIGH\s+away/) && !has(f, /upscale/) && has(f, /zoom not published/),
    (f.match(/speaker: face on[^\n]*/) || ["none"])[0]);
  // review 2026-10-22: the page's own face decides on / off (claude-makes-claude: the box hidden over a full-frame A-roll),
  // and a full-bleed room plate of him is him (oss-editor-reels-a's hook); a full-bleed screen recording is not
  check("precheck speaker fallback: a hidden __box over a full-frame A-roll with his __faceRect is face on 100 %, layout 'full'",
    has(bh, /speaker: face on 100%, off 0%, full frame 100%; takeovers 0/) && !/\b(away|hook)\b/.test(bh.split("ambition:")[0]) && has(bh, /ambition: layouts full 100%/) && !has(bh, /off \(graphic\)/),
    (bh.match(/speaker: face on[^\n]*/) || ["none"])[0]);
  check("precheck speaker fallback: a room plate opening the hook is him; a screen recording takeover is not",
    !has(pl, /\bhook\b/) && has(pl, /speaker: face on 68%, off 32%, full frame >= 5%; takeovers 2 \(6\.0 s, 13\.0 s\)/), (pl.match(/speaker: face on[^\n]*/) || ["none"])[0]);
}
console.log(bad ? `\n${bad} FAIL` : "\nall ok");
process.exit(bad ? 1 : 0);
