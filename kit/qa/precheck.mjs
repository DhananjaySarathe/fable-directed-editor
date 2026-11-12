// Pre-render layout check of a built HyperFrames page: catches in ~2 min what used to cost a 4K render to find.
//
//   node kit/qa/precheck.mjs <hf>/index.html [--fps=5] [--from=0] [--to=<s>] [--json=<out.json>] [--allow=12.0-14.5,...]
//                            [--holds-out=<holds.json>] [--min-text=<px>]
//
// Works on 16:9 (1920x1080) and 9:16 (1080x1920) pages: the frame size comes from the page's root.
// The page is stepped forward in time (like the renderer, never jumping back) at --fps and measured at every step:
//   offscreen   visible text outside the safe frame (24 px in from the sides, 20 px from top/bottom; chrome exempt) HIGH
//   small       text a phone can't read: rendered size under --min-text (32 px on 16:9, 36 px on 9:16) for >= 0.8 s.
//               Labels marked data-decor, .lbl kickers and window title bars are exempt (a .mono label is not: its
//               words are read). Zoom in (S.focus) or set it bigger. Judged per card or line: half its letters under the floor = MEDIUM, half under 75 % of
//               it = HIGH (one small timestamp in a readable card is fine). Measured with a 0.5 px tolerance: the
//               drawn size is the font size x its scale, read from rounded layout widths, so 32 px type on a canvas
//               station reads 31.6-31.9 px and is not small                                                 MEDIUM
//   under-box   text on a layer under the speaker box, covered by it (the box is opaque video)               MEDIUM
//   read        a block of 4+ words (not spoken type) that leaves before it can be read: on screen for less than
//               0.6 s + 0.24 s a word (about 250 words a minute)                                               MEDIUM
//   face        text over the speaker's face (the box's face zone: 42 % down the box, from window.__box.rect)  HIGH
//   overlap     two separate text blocks overlapping (one over the other)                                     MEDIUM
//   on-card     text over a card it is not part of (mark intended overlays with data-over, e.g. a stamp)      MEDIUM
//   blank       the box hidden and nothing on screen but the world for >= 0.6 s                               HIGH (>= 1 s) / MEDIUM
//   error       page errors while building or seeking                                                         HIGH
//   linger      a part placed straight on a full-frame layer (a strike, a stamp, a note, a toast) still up after 20 s:
//               it was never given an end (films/xchakra draft 2: two red strike lines for 4 minutes)            HIGH
//   mount       a HyperFrames catalog piece (film.py MOUNTS) this check could not fill, so its text went unchecked MEDIUM
// Catalog pieces are filled in here the way HyperFrames' compiler fills them, so every check above reads their text
// too; a piece counts as one block (like a card) and its findings start "catalog <piece>:".
// Ambition (2026-10-20, kit/refs/AUDIT_2026-10-20.md: films used ~4 of ~60 components). Printed for every page, gated
// (HIGH) unless --no-ambition:
//   layout      the speaker in one layout for more than 35 % of the runtime (full, a card beside, corner, off). From
//               window.__box, else window.__speaker's kind (so the canvas look is covered too). The sides are one
//               layout since 2026-10-22 (OWNER_DEFAULTS §1 "a card beside the graphic"): card left + card right add up
//               on a page that publishes window.__speaker. A page from before keeps its per-side HIGH and gets the
//               merged share as MEDIUM (kit/qa/speaker.mjs layoutGate), so what passed then does not stop now
//   variety     fewer distinct visual components in the film's script than the length needs (Reels 4; long-form 1.2 a
//               minute, 6-10 since 2026-10-22), counted from kit/hf/registry.json. MEDIUM only: the density gate below
//               outranks it (a calm film is not made busier to pass a count); plan them first (kit/refs/SCENES.md)
//   still       the longest stretch with nothing new entering the frame (a block, a card, a line of type, a box move,
//               and since 2026-10-22 a framing change on him or a transition in window.__trans):
//               over 10 s on 16:9 / 5 s on 9:16 HIGH, over 6 s / 3 s MEDIUM (captions and single words don't count)
// Speaker (2026-10-22, kit v11; kit/qa/speaker.mjs). Read from window.__speaker(t) = { on, kind, rect, face, zoom, lens }
// (the engine contract), else estimated the way pages published it before (the section says which): the page's own
// __faceRect (else the face zone of a shown __box) decides on / off, __box names the kind while it is shown, and a
// full-bleed <video> of his footage (face, aroll, room...: a full-frame A-roll, a room plate) is him. Gated like ambition:
//   framing     his framing unchanged while he is on (the face centre moves < 2 % of the frame and its scale < 4 %)
//               for over 8 s MEDIUM, over 15 s HIGH, unless the lens declared a hold (lens "hold"). Time he is on with
//               no face, rect or zoom to frame by is unmeasured (printed), never "unchanged"; time in a corner (kind
//               "corner": a box under 10 % of the frame) is not judged, as plan_check's cam rules skip a corner
//   away        he is off screen for more than 12 s in one go                     HIGH (estimated, no __speaker: MEDIUM)
//   hook        his face is off in the first 3 s                                                              MEDIUM
//   faceoff     long-form only: the face-off share outside 15-30 % (takeovers, kit/refs/SCENES.md §9)         MEDIUM
//               (on a page without __speaker these three say "estimated": on / off there is a guess)
//   upscale     his footage scaled past the source's budget. Needs __speaker's zoom. The budget (speaker.mjs
//               budgetsOf): the max_zoom the sample publishes (over by up to 5 % MEDIUM, more HIGH), else the
//               tracks.json contract from D.tracks: max(1, sharp_px / the shape's height), with the sharp_px of the
//               kind playing at t (D.pieces) winning over the track's, and its soft tier (max(r, 1 + soft x min(r, 1)));
//               over sharp MEDIUM, over soft HIGH (box pages with the lens off, redline.js, HF.camera punches); else the
//               track's max_zoom; 1.2 when there is no tracks.json
//   pace        more than 15 THOUGHT moves a minute on him (over 20 s or more of framed time)                 MEDIUM
//   It prints face-on / off / full-frame shares, THOUGHT MOVES PER MINUTE while he is on (want 7.5-15: one every
//   4-8 s; a framing change within 0.3 s of a join the lens reframed, window.__lens[id].jumps, is a jump-cut reframe:
//   counted apart, never against the pace), every framing change a minute (the old number), the longest unchanged
//   framing, the longest time away, the zoom against its budget, and a NOTE listing the stretches where the soft
//   allowance was in force (__speaker.soft: mild softening the lens chose; look at those frames).
// Takeovers (window.__takeovers, kit/hf/trans.js): each 4-12 s, at least 3 s of his face between two, and every template
//   shot a takeover dropped (dropped: [{ speaker, t }])                                                       MEDIUM
// Diagrams (window.__diagrams, kit/hf/diagram.js): every entry with gate: true (flat) through HF.diagram.verify, timed
//   by its show windows: two connectors sharing a port and a line behind a box HIGH, every other finding MEDIUM.
// Density (2026-10-22, "holistic, not heavy"): top-level visual groups on screen per sample (cards, chips, windows,
//   big type, mounts, media and [data-group] parts over 0.3 % of the frame; captions, chrome, the world, data-decor and
//   his shape don't count): more than 3 for over 2 s MEDIUM, more than 5 for over 2 s HIGH. Gated like ambition. A
//   large group (8 % of the frame or more: a diagram, a stack, a takeover's scene, a big card) counts by what it holds:
//   its items (the outermost cards, chips, nodes and media inside it, and every line of visible text not in one of
//   them; a window's title bar and data-decor excepted) count one group per 3, so a frame whose one block holds 11 text
//   items is 4 groups. Loose text inside a takeover (window.__takeovers' [data-takeover] root) that no group holds
//   counts the same way.
// Transitions: window.__trans ([{ t, kind, why, pair?, until? }], logged by the engine's transitions) is reported by
//   kind; a bracket (two entries sharing a pair id, one kind, nothing between: a takeover's in and out) counts once,
//   folded here if the page did not; the same kind twice in a row (cuts may repeat) and whips over 40 % are MEDIUM.
//   Pages without it print "none published".
// --no-ambition (films made before 2026-10-22: kit/film passes it by the film's date) prints every ambition, speaker and
// density HIGH as MEDIUM.
// Findings are merged into spans with a timecode and the text involved. Exit 3 when anything HIGH is found. The last
// line repeats the verdict with every HIGH by kind ("precheck FAIL: 3 HIGH [framing 06:07.6 07:12.0, density 01:10.6],
// 9 MEDIUM"): kit/film and kit/reel print only the tail of this output.
// --holds-out writes the reading holds for qa.py --holds: every stretch where readable text (4+ words, not spoken type,
// big enough) is on screen, with the time it needs, plus the holds the page declared (S.hold, layer({ read: true })).
// A still frame while the viewer reads is a hold, not a freeze; nothing should float just to pass the freeze check.
// It does not judge motion or sound: render a 1080p draft and run kit/qa/qa.py for those (frozen holds, flashes,
// dropouts), and for anything that only shows in the frame-by-frame renderer.
import puppeteer from "puppeteer-core";
import fs from "node:fs";
import path from "node:path";
import * as SP from "./speaker.mjs";

const args = process.argv.slice(2);
const opt = (k, d) => { const a = args.find((x) => x.startsWith(`--${k}=`)); return a ? a.split("=").slice(1).join("=") : d; };
const src = args.find((a) => !a.startsWith("--"));
if (!src) { console.error("usage: node kit/qa/precheck.mjs <index.html> [--fps=5] [--json=out.json]"); process.exit(2); }
const fps = +opt("fps", 5), from = +opt("from", 0), jsonOut = opt("json", null), holdsOut = opt("holds-out", null);
const allow = (opt("allow", "") || "").split(",").filter(Boolean).map((r) => r.split("-").map(Number));
const allowed = (t) => allow.some(([a, b]) => t >= a && t <= b);
const gateAmbition = !args.includes("--no-ambition");
// --doc (kit/presets/documentary only; kit/film passes it for PRESET = "documentary"): a documentary holds longer on a
// face or a shot and opens cold, so still is 10-15 s (not 6-10), away HIGH only past 30 s, and one dominant layout
// (interviews full frame) is MEDIUM. Every other page is judged exactly as before
const docMode = args.includes("--doc");

const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true,
  args: ["--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
const errs = [];
page.on("pageerror", (e) => errs.push(String(e.message || e)));
await page.goto("file://" + path.resolve(src), { waitUntil: "domcontentloaded" });
await page.waitForFunction(() => window.__timelines && Object.keys(window.__timelines).length > 0, { timeout: 60000 });
// the frame: the root's own size (a 9:16 Reel is 1080x1920)
const [FW, FH] = await page.evaluate(() => { const r = document.getElementById("root") || document.body;
  return [+(r.dataset.width || r.offsetWidth || 1920), +(r.dataset.height || r.offsetHeight || 1080)]; });
if (FW !== 1920 || FH !== 1080) await page.setViewport({ width: FW, height: FH, deviceScaleFactor: 1 });
const minText = +opt("min-text", FH > FW ? 36 : 32);          // EDITING.md §11 (the 32 px floor from the first critic run)
const total = await page.evaluate(() => Object.values(window.__timelines)[0].duration());
const to = Math.min(total, +opt("to", total));

// HyperFrames catalog pieces (film.py MOUNTS, kit/hf/mounts.py) are sub-compositions HyperFrames fills when it compiles
// the page, so this load sees each mount empty and their text went unchecked. Fill them the way the compiler does
// (2026-10-20): the piece's markup inside its mount, its CSS's #root and its script's getElementById("root") pointed at
// that copy, its variables from the mount's data-variable-values, its timeline kept apart and seeked in its own time
// while the mount is on screen (window.__pcSeek, called by the probe). A piece that can't be filled is reported, not fatal.
const fillMounts = (pieces) => {
  window.__pcMounts = [];
  for (const p of pieces) {
    const host = document.getElementById(p.id), a = +host.dataset.start;
    const m = { name: host.dataset.mount, a, b: a + +host.dataset.duration, el: host, tl: null, err: p.err || null };
    window.__pcMounts.push(m);
    if (!p.html) continue;
    try {
      const doc = new DOMParser().parseFromString(p.html, "text/html"), tpl = doc.querySelector("template");
      const frag = tpl ? tpl.content : doc.body, rid = "pc-" + p.id, scoped = (css) => css.replace(/#root\b/g, "#" + rid);
      // a piece keeps its <style> and <script> inside its root or beside it in the template (agent-cursor,
      // cursor-text-select, cursor-zoom-follow): take them all, in order
      const code = [...frag.querySelectorAll("script")].map((s) => s.textContent);
      const piece = document.importNode(frag.querySelector("[data-composition-id]"), true);
      piece.id = rid;
      piece.querySelectorAll("script").forEach((s) => s.remove());
      piece.querySelectorAll("style").forEach((s) => { s.textContent = scoped(s.textContent); });
      [...frag.querySelectorAll("style")].filter((s) => !s.closest("[data-composition-id]"))
        .forEach((s) => { const c = document.createElement("style"); c.textContent = scoped(s.textContent); host.append(c); });
      host.append(piece);
      // and its rules under its mount, as HyperFrames' scopeCssToComposition does (hyperframes 0.8.181): every selector
      // becomes a descendant of the mount; a bare *, html, body and :root, @keyframes and @font-face stay global
      const scopeRules = (rules) => { for (const r of rules) {
        if (r instanceof CSSStyleRule) r.selectorText = r.selectorText.split(",").map((s) => s.trim())
          .map((s) => (s === "*" || /^(html|body|:root)$/i.test(s) ? s : `#${host.id} ${s}`)).join(", ");
        else if (r.cssRules && !(r instanceof CSSKeyframesRule)) scopeRules(r.cssRules);
      } };
      host.querySelectorAll("style").forEach((s) => s.sheet && scopeRules(s.sheet.cssRules));
      let vars = {};
      try { vars = JSON.parse(host.dataset.variableValues || "{}"); } catch (e) { vars = {}; }
      const bind = (t, k) => { const v = Reflect.get(t, k, t); return typeof v === "function" && !/^[A-Z]/.test(String(k)) ? v.bind(t) : v; };
      const doc2 = new Proxy(document, { get: (t, k) => {
        if (k === "getElementById") return (id) => (id === "root" ? piece : piece.querySelector("#" + CSS.escape(id)) || document.getElementById(id));
        if (k === "querySelector" || k === "querySelectorAll") return (sel) => document[k](scoped(String(sel)));
        if (k === "documentElement") return doc.documentElement;                // the piece's own <html>: its declared defaults
        return bind(t, k); } });
      const reg = new Proxy({}, { set: (o, k, tl) => { o[k] = tl; m.tl = tl; return true; } });   // the piece's own __timelines
      const win = new Proxy(window, {
        get: (t, k) => (k === "__hyperframes" ? { getVariables: () => vars } : k === "__hfVariables" ? vars : k === "__timelines" ? reg
          : k === "document" ? doc2 : bind(t, k)),
        set: (t, k, v) => (k === "__timelines" ? true : Reflect.set(t, k, v)) });
      for (const c of code) new Function("document", "window", "globalThis", c)(doc2, win, win);
    } catch (e) { m.err = String(e.message || e); }
  }
  window.__pcSeek = (t) => { for (const m of window.__pcMounts) {
    const on = t >= m.a - 1e-6 && t < m.b;
    m.el.style.visibility = on ? "" : "hidden";
    if (on && m.tl) m.tl.seek(Math.max(0, t - m.a), false);
  } };
};
const pieces = (await page.evaluate(() => [...document.querySelectorAll(".hf-mount[data-composition-src]")].map((m) => ({ id: m.id, src: m.dataset.compositionSrc }))))
  .map((m) => { try { return { ...m, html: fs.readFileSync(path.join(path.dirname(path.resolve(src)), m.src), "utf8") }; } catch (e) { return { ...m, html: null, err: e.message }; } });
let mountState = [];
if (pieces.length) {
  await page.evaluate(fillMounts, pieces);
  // some pieces build their timeline once the fonts are in (document.fonts.ready): give them a moment
  await page.waitForFunction(() => window.__pcMounts.every((m) => m.tl || m.err), { timeout: 15000 }).catch(() => {});
  mountState = await page.evaluate(() => window.__pcMounts.map((m) => ({ name: m.name, a: m.a, ok: !!m.tl, err: m.err })));
}

// one measurement at time t, inside the page
const probe = (t, FW, FH, minText) => {
  const tl = Object.values(window.__timelines)[0];
  tl.seek(t, false);
  if (window.__pcSeek) window.__pcSeek(t);                                        // the catalog pieces, in their own time
  const root = document.getElementById("root") || document.body;
  const layers = [...root.children];
  // zOf and alpha are memoised for this one measurement (the page does not change inside it): the text, ambition and
  // density passes ask about the same elements and ancestors many times, and getComputedStyle is the cost (2026-10-22)
  const zMemo = new Map(), aMemo = new Map();
  const zOf = (e) => { let p = e; while (p && p.parentElement !== root) p = p.parentElement; if (!p) return 0;
    let z = zMemo.get(p); if (z === undefined) { z = +(getComputedStyle(p).zIndex || 0); zMemo.set(p, z); } return z; };
  const shown = (e) => e.checkVisibility({ opacityProperty: true, visibilityProperty: true, contentVisibilityAuto: true });
  const alpha = (e) => { if (!e || e === root) return 1; let a = aMemo.get(e);
    if (a === undefined) { a = +getComputedStyle(e).opacity * alpha(e.parentElement); aMemo.set(e, a); } return a; };
  const R = (r) => ({ x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) });
  const box4 = (l, t, r, b) => ({ left: l, top: t, right: r, bottom: b, width: Math.max(0, r - l), height: Math.max(0, b - t) });
  // what is left of a rect after every clipping ancestor below #root (overflow, clip-path inset): masks, wipes, cards
  // (each ancestor's clip box is worked out once per measurement: many leaves share the same cards and masks)
  const clipMemo = new Map();
  const clipOf = (p) => {
    let c = clipMemo.get(p);
    if (c !== undefined) return c;
    const cs = getComputedStyle(p), m = cs.clipPath.match(/^inset\(([^)]*)\)/);
    if (cs.overflow === "visible" && !m) c = null;
    else {
      const b = p.getBoundingClientRect();
      let l = b.left, t = b.top, rr = b.right, bb = b.bottom;
      if (m) {
        const v = m[1].split(/\s+/).slice(0, 4).map((x) => x.trim());
        while (v.length < 4) v.push(v[v.length === 1 ? 0 : v.length - 2]);
        const px = (x, full) => (x.endsWith("%") ? (parseFloat(x) / 100) * full : parseFloat(x) || 0);
        t += px(v[0], b.height); rr -= px(v[1], b.width); bb -= px(v[2], b.height); l += px(v[3], b.width);
      }
      c = [l, t, rr, bb];
    }
    clipMemo.set(p, c);
    return c;
  };
  const clipTo = (e, r) => {
    let x0 = r.left, y0 = r.top, x1 = r.right, y1 = r.bottom;
    for (let p = e.parentElement; p && p !== root; p = p.parentElement) {
      const c = clipOf(p);
      if (!c) continue;
      x0 = Math.max(x0, c[0]); y0 = Math.max(y0, c[1]); x1 = Math.min(x1, c[2]); y1 = Math.min(y1, c[3]);
      if (x1 <= x0 || y1 <= y0) return box4(0, 0, 0, 0);
    }
    return box4(x0, y0, x1, y1);
  };
  // the glyphs' own box (a label div can be far wider than its text)
  const glyphs = (e) => { let u = null;
    for (const n of e.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { const rg = document.createRange(); rg.selectNodeContents(n);
      const r = rg.getBoundingClientRect(); if (r.width && r.height) u = u ? box4(Math.min(u.left, r.left), Math.min(u.top, r.top), Math.max(u.right, r.right), Math.max(u.bottom, r.bottom)) : box4(r.left, r.top, r.right, r.bottom); }
    return u; };
  const chromeZ = Math.max(...layers.map((l) => +(getComputedStyle(l).zIndex || 0)));
  // text leaves: elements with their own text, visible, not in the chrome, not clipped away by a mask
  const texts = [];
  root.querySelectorAll("*").forEach((e) => {
    if (e.tagName === "SCRIPT" || e.tagName === "STYLE") return;
    const own = [...e.childNodes].filter((n) => n.nodeType === 3 && n.textContent.trim()).map((n) => n.textContent.trim()).join(" ");
    if (!own) return;
    const z = zOf(e);
    if (z >= chromeZ || z <= 1) return;
    if (!shown(e) || alpha(e) < 0.3) return;                                      // fading ghosts below 30 % don't read
    const er = e.getBoundingClientRect();
    if (er.width < 1 || er.height < 1) return;                                    // not rendered (an SVG group set to display:none)
    const g = glyphs(e);
    if (!g || g.width < 2 || g.height < 2) return;
    const r = clipTo(e, g);                                                       // masks, wipes and cards clip it
    if (r.width < 4 || r.height < 4) return;
    // a catalog piece is one unit, like a card: judged by most of its text, never overlapping itself, named in findings
    const mnt = e.closest(".hf-mount");
    const block = mnt || e.closest(".sv,.card,.chip,.pill,[data-over],[data-block]") || e.parentElement;   // data-block: one text unit (a stamped headline)
    const card = e.closest(".card,.chip");
    // the size it is drawn at: font size times every scale above it (an entrance, a push, a focus zoom, a station). The
    // smaller of the two axes: a rotated box grows its bounding rect on both, a 3D tilt shrinks the one it leans on.
    // SVG text has no offset box (it read as scale 1 before, whatever the viewBox drew it at): its own bbox in user units
    let sc = 1;
    if (e.offsetWidth > 0 && e.offsetHeight > 0) sc = Math.min(er.width / e.offsetWidth, er.height / e.offsetHeight);
    else if (typeof e.getBBox === "function") { try { const bb = e.getBBox(); if (bb.width > 0 && bb.height > 0) sc = Math.min(er.width / bb.width, er.height / bb.height); } catch (x) { sc = 1; } }
    const px = parseFloat(getComputedStyle(e).fontSize) * sc;
    const spoken = !!(e.closest("[data-w]") || e.querySelector("[data-w]"));
    // exempt: data-decor, .lbl kickers and window title bars (EDITING.md §11). Not .mono (review 2026-10-23, v11-sample
    // draft 1): it is a typeface, and the mechanism's own words (diagram edge labels, a takeover's kicker) set in it at
    // 27-30 px passed as decor while the critic read them under the floor
    const decor = !!e.closest("[data-decor],.lbl,.tbar");
    texts.push({ kc: e.dataset ? e.dataset.kc : undefined, e, text: own.slice(0, 40), pre: mnt ? `catalog ${mnt.dataset.mount}: ` : "", r, block, card,
      over: !!e.closest("[data-over]"), px, spoken, decor, letter: !!mnt && own.length === 1 });
  });
  const out = [];
  // per block (a card, a chip, a type line): its words, the smallest size it is drawn at, spoken or not, and how much of
  // its text is under the phone floor (a card is judged by most of its text, not by one small timestamp)
  const blocks = new Map();
  for (const t1 of texts) {
    const b = t1.block;
    if (!b.__pcid) b.__pcid = (window.__pcn = (window.__pcn || 0) + 1);
    // a catalog piece is labelled by its text in reading order (its leaves split a line around the marked word)
    const k = b.__pcid, cur = blocks.get(k) || { id: k, words: 0, px: 1e9, spoken: false, decor: true, n: 0, lo: 0, vlo: 0, rect: t1.r,
      text: t1.pre ? (t1.pre + b.innerText.replace(/\s+/g, " ").trim()).slice(0, 72) : "", pre: t1.pre };
    // a kinetic char split (kit/hf/kinetic.js marks each letter data-kc), or a piece's letter spans: one word per word
    cur.words += (t1.kc != null && t1.kc !== "0") || t1.letter ? 0 : t1.text.split(/\s+/).filter(Boolean).length; cur.px = Math.min(cur.px, t1.px);
    cur.spoken = cur.spoken || t1.spoken; cur.decor = cur.decor && t1.decor;
    if (!t1.pre && cur.text.length < 48) cur.text = (cur.text + " " + t1.text).trim().slice(0, 48);
    // (0.5 px tolerance: px is the font size x a scale read off rounded layout widths, so 32 px on a canvas station
    // measures 31.6-31.9; review 2026-10-22, a false 'small' at exactly the floor)
    if (!t1.decor && !t1.spoken) { const n = t1.text.replace(/[^\p{L}\p{N}]/gu, "").length; cur.n += n; if (t1.px < minText - 0.5) cur.lo += n; if (t1.px < 0.75 * minText - 0.5) cur.vlo += n; }
    blocks.set(k, cur);
  }
  for (const b of blocks.values()) {
    if (b.n < 3 || b.lo < 0.5 * b.n) continue;
    out.push({ kind: "small", sev: b.vlo >= 0.5 * b.n ? "HIGH" : "MEDIUM", px: Math.round(b.px), text: b.text, key: b.pre || undefined, rect: R(b.rect) });
  }
  out.push({ kind: "_blocks", list: [...blocks.values()].filter((b) => !b.decor) });
  for (const t1 of texts) {
    const r = t1.r;
    if (t1.decor) continue;                                                       // texture may bleed off the frame
    if (r.left < 24 || r.right > FW - 24 || r.top < 20 || r.bottom > FH - 20) {
      const line = t1.pre + (t1.block.textContent || t1.text).replace(/\s+/g, " ").trim().slice(0, 48);
      if (!out.some((f) => f.kind === "offscreen" && f.text === line)) out.push({ kind: "offscreen", sev: "HIGH", text: line, key: t1.pre || undefined, rect: R(r) });
    }
  }
  // the face zone of the speaker box (HF.box: cover crop, face at 42 % of the box height)
  const bx = window.__box && window.__box.rect ? window.__box.rect(t) : null;
  // the speaker contract (2026-10-22): window.__speaker(t) = { on, kind, rect, face, zoom, lens } in page px, from any
  // engine. Read once here: the face check below uses its face when the page has no __faceRect
  const XYWH = (r) => (r && Number.isFinite(+r.w) && Number.isFinite(+r.h) && +r.w > 0 && +r.h > 0 ? { x: +r.x, y: +r.y, w: +r.w, h: +r.h } : null);
  let spk = null;
  if (typeof window.__speaker === "function") {
    try { const s = window.__speaker(t);
      if (s) spk = { src: "__speaker", on: !!s.on, kind: s.on ? String(s.kind || "?") : "off", rect: XYWH(s.rect), face: XYWH(s.face),
        zoom: Number.isFinite(+s.zoom) && s.zoom != null ? +s.zoom : null, lens: String(s.lens || ""), track: s.track || null,
        max_zoom: Number.isFinite(+s.max_zoom) && s.max_zoom != null ? +s.max_zoom : null, soft: s.soft === true };
    } catch (e) { spk = null; }
  }
  let face = null;
  if (typeof window.__faceRect === "function") face = window.__faceRect(t);   // the page knows the real face (night_reel.js)
  else if (spk && spk.on && spk.face) face = { left: spk.face.x, top: spk.face.y, right: spk.face.x + spk.face.w, bottom: spk.face.y + spk.face.h };
  else if (bx && bx.op > 0.5 && bx.w > 120) {
    const fw = Math.min(bx.w, bx.h) * 0.34, fh = bx.h * 0.4;
    face = { left: bx.cx - fw / 2, right: bx.cx + fw / 2, top: bx.cy - bx.h / 2 + bx.h * 0.42 - fh / 2, bottom: bx.cy - bx.h / 2 + bx.h * 0.42 + fh / 2 };
  }
  // text on an opaque full-frame card (a chapter or title card, [data-cover]) is above the box: the face is not visible
  const opaqueBg = (x) => { const c = getComputedStyle(x); const m = c.backgroundColor.match(/rgba?\(([^)]+)\)/);
    const a = m ? (m[1].split(",")[3] != null ? +m[1].split(",")[3] : 1) : 0; return a > 0.9 || (c.backgroundImage !== "none" && !c.backgroundImage.includes("gradient(")); };
  // per ancestor, once a measurement: is it a full-frame opaque card itself, and which of its children are
  const coverMemo = new Map();
  const coverOf = (p) => {
    let c = coverMemo.get(p);
    if (c !== undefined) return c;
    const r = p.getBoundingClientRect(), full = (x) => x.width >= 0.9 * FW && x.height >= 0.9 * FH;
    if (!full(r)) c = null;
    else c = { self: opaqueBg(p), kids: opaqueBg(p) ? [] : [...p.children].filter((k) => full(k.getBoundingClientRect()) && opaqueBg(k) && shown(k)) };
    coverMemo.set(p, c);
    return c;
  };
  const onCover = (e) => {
    if (e.closest("[data-cover]")) return true;
    for (let p = e.parentElement; p && p !== root; p = p.parentElement) {
      const c = coverOf(p);
      if (!c) continue;
      if (c.self) return true;
      if (c.kids.some((k) => !k.contains(e))) return true;
    }
    return false;
  };
  if (face) {
    for (const t1 of texts) {
      if (onCover(t1.e)) continue;
      const r = t1.r, ix = Math.max(0, Math.min(r.right, face.right) - Math.max(r.left, face.left)), iy = Math.max(0, Math.min(r.bottom, face.bottom) - Math.max(r.top, face.top));
      if (ix * iy > 0.25 * r.width * r.height && !t1.over) out.push({ kind: "face", sev: "HIGH", text: t1.pre + t1.text, key: t1.pre || undefined, rect: R(r) });
    }
  }
  // text the speaker box covers: it is on a layer under the box and the box sits on it (the box is opaque video)
  if (bx && bx.op > 0.5 && bx.w > 120) {
    const v = document.getElementById("aroll") || root.querySelector("video");
    const boxZ = v ? zOf(v) : 0;
    const br = { left: bx.cx - bx.w / 2, right: bx.cx + bx.w / 2, top: bx.cy - bx.h / 2, bottom: bx.cy + bx.h / 2 };
    for (const t1 of texts) {
      if (zOf(t1.e) >= boxZ || t1.decor) continue;
      const r = t1.r, ix = Math.max(0, Math.min(r.right, br.right) - Math.max(r.left, br.left)), iy = Math.max(0, Math.min(r.bottom, br.bottom) - Math.max(r.top, br.top));
      if (ix * iy > 0.5 * r.width * r.height) out.push({ kind: "under-box", sev: "MEDIUM", text: t1.pre + (t1.block.textContent || t1.text).replace(/\s+/g, " ").trim().slice(0, 44), key: t1.pre || undefined, rect: R(r) });
    }
  }
  // overlaps between separate blocks, and text over a card it isn't part of
  const inter = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
  for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
    const a = texts[i], b = texts[j];
    if (a.block === b.block || a.block.contains(b.block) || b.block.contains(a.block) || a.over || b.over || a.decor || b.decor) continue;   // texture (data-decor) may sit under anything
    const k = inter(a.r, b.r), small = Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
    if (k > 0.2 * small) out.push({ kind: "overlap", sev: "MEDIUM", text: `${a.pre}${a.text} / ${b.pre}${b.text}`,
      key: a.pre || b.pre ? `${a.pre || a.text} / ${b.pre || b.text}` : undefined, rect: R(a.r) });
  }
  const cards = [...root.querySelectorAll(".card")].filter((c) => zOf(c) < chromeZ && shown(c) && alpha(c) > 0.5);
  for (const t1 of texts) {
    if (t1.over) continue;
    for (const c of cards) {
      if (c.contains(t1.e) || (t1.card && (t1.card.contains(c) || c.contains(t1.card)))) continue;
      const cr = clipTo(c, c.getBoundingClientRect());
      if (inter(t1.r, cr) > 0.3 * t1.r.width * t1.r.height && zOf(t1.e) >= zOf(c)) { out.push({ kind: "on-card", sev: "MEDIUM", text: t1.pre + t1.text, key: t1.pre || undefined, rect: R(t1.r) }); break; }
    }
  }
  // blank: no big visible thing besides the world, the grain and the chrome
  let content = 0;
  if (bx && bx.op > 0.3 && bx.w * bx.h > 60000) content++;
  else if (spk && spk.on && spk.rect && spk.rect.w * spk.rect.h > 60000) content++;   // he is on, from __speaker (HF.doc's
  else for (const L of layers) {                                                      // full-frame interview has no box)
    const z = +(getComputedStyle(L).zIndex || 0);
    if (z <= 1 || z >= chromeZ || L.tagName === "VIDEO") continue;
    for (const e of L.querySelectorAll("*")) {
      const r0 = e.getBoundingClientRect();
      if (r0.width * r0.height < 20000) continue;
      const r = clipTo(e, r0);
      if (r.width * r.height < 20000 || r.right < 0 || r.left > FW || r.bottom < 0 || r.top > FH) continue;
      const cs = getComputedStyle(e);
      const painted = cs.backgroundColor !== "rgba(0, 0, 0, 0)" || cs.backgroundImage !== "none" || e.tagName === "svg" || e.tagName === "CANVAS" || e.tagName === "IMG" || (e.textContent || "").trim();
      if (painted && shown(e) && alpha(e) > 0.3) { content++; break; }
    }
    if (content) break;
  }
  if (!content) out.push({ kind: "blank", sev: "MEDIUM", text: "", rect: null });
  // ---- ambition: the box's layout, a signature of what is on screen, and the parts placed straight on a full-frame layer
  const amb = { kind: "_amb", slot: null, sig: [], persist: [] };
  // inked: something of it can be seen. A part with text needs a visible run of text (a say() line whose words are all
  // still hidden is not on screen); a graphic goes by its own visibility.
  const hasText = (x) => [...x.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
  // (once a measurement: every element with its own text marks its ancestors as holding text, and as holding visible
  // text when it is shown at 30 % or more; inked(e) then reads two sets instead of walking e's subtree each time)
  let inkT = null, inkV = null;
  const inked = (e) => {
    if (!inkT) {
      inkT = new Set(); inkV = new Set();
      for (const x of root.querySelectorAll("*")) {
        if (!hasText(x)) continue;
        const v = shown(x) && alpha(x) >= 0.3;
        for (let p = x; p && p !== root.parentElement; p = p.parentElement) {
          if (inkT.has(p) && (!v || inkV.has(p))) break;
          inkT.add(p); if (v) inkV.add(p);
        }
      }
    }
    return !inkT.has(e) || inkV.has(e);
  };
  if (bx && window.__box) {
    if (bx.op < 0.5) amb.slot = "off (graphic)";
    else if (bx.w >= 0.9 * FW && bx.h >= 0.9 * FH) amb.slot = "full";
    else {
      const a = (bx.w * bx.h) / (FW * FH), size = a >= 0.28 ? "card" : a >= 0.1 ? "small card" : "corner";
      const pos = FW > FH ? (bx.cx < 0.42 * FW ? "left" : bx.cx > 0.58 * FW ? "right" : "centre") : (bx.cy < 0.42 * FH ? "top" : bx.cy > 0.58 * FH ? "bottom" : "centre");
      amb.slot = `${size} ${pos}`;
    }
    amb.sig.push(`box:${amb.slot}:${Math.round(bx.cx / 40)},${Math.round(bx.cy / 40)},${Math.round(bx.w / 40)}`);
  }
  for (const L of layers) {
    const z = +(getComputedStyle(L).zIndex || 0);
    if (z <= 1 || z >= chromeZ || L.tagName === "VIDEO" || L.closest("[data-decor]") || L.querySelector("#aroll")) continue;
    for (const c of L.children) {                                                  // placed straight on the layer
      if (c.tagName === "VIDEO" || c.dataset.decor || !shown(c) || alpha(c) < 0.3 || !inked(c)) continue;
      const r = clipTo(c, c.getBoundingClientRect());
      if (r.width * r.height < 4) continue;
      if (!c.__lid) c.__lid = (window.__lidn = (window.__lidn || 0) + 1);
      amb.persist.push({ id: c.__lid, frac: +((r.width * r.height) / (FW * FH)).toFixed(4), label: `${String(c.className || c.tagName).slice(0, 18)} ${(c.textContent || "").replace(/\s+/g, " ").trim().slice(0, 28)}`.trim() });
    }
    for (const e of L.querySelectorAll("div,svg,img,video,canvas")) {              // something new: blocks, graphics, media, type
      if (e.closest(".cap,[data-decor]") || !shown(e) || alpha(e) < 0.3) continue;
      const big = ["card", "chip", "cv-card", "cv-chip", "strike"].some((k) => e.classList.contains(k)) || e.tagName !== "DIV";   // cv-: the canvas's own
      if (!big && !e.classList.contains("sv")) { const r = e.getBoundingClientRect(); if (r.width * r.height < 40000) continue; }
      if (!inked(e)) continue;
      const r = clipTo(e, e.getBoundingClientRect());
      if (r.width < 8 || r.height < 4) continue;
      if (!e.__sid) e.__sid = (window.__sidn = (window.__sidn || 0) + 1);
      amb.sig.push(e.__sid);
    }
  }
  // ---- the speaker (2026-10-22, kit/qa/speaker.mjs): the contract when the page publishes it, else estimated from what
  // pages published before (speaker.mjs fallbackSpeaker, put on the page as window.__pcFallback): the page's own face
  // (__faceRect, else the box's face zone) decides on / off, __box names the kind while it is shown, and a full-bleed
  // <video> of his own footage (the room plate, a full-frame A-roll) counts as him. No zoom or lens without the contract
  if (!spk) {
    const f = face ? { x: face.left, y: face.top, w: face.right - face.left, h: face.bottom - face.top } : null;
    let plate = null;
    for (const v of document.querySelectorAll("video")) {
      const file = (v.getAttribute("src") || "").split(/[/?#]/).filter(Boolean).pop() || "";
      if (!window.__pcFaceTrack.test(v.id || "") && !window.__pcFaceTrack.test(file.replace(/\.[^.]+$/, ""))) continue;
      if (!shown(v) || alpha(v) < 0.5) continue;
      const vr = v.getBoundingClientRect(), r = clipTo(v, vr);
      const w = Math.min(FW, r.right) - Math.max(0, r.left), h = Math.min(FH, r.bottom) - Math.max(0, r.top);
      if (w > 0 && h > 0 && w * h >= 0.9 * FW * FH) { plate = { x: vr.left, y: vr.top, w: vr.width, h: vr.height }; break; }   // its own rect: a push moves it
    }
    // the box's footage zoom (HF.box.at: 1 = cover) shows a jump-cut reframe inside a still card; it moves the framing
    // only (fz): an old page has no zoom budget, so the upscale check stays with the contract's zoom
    let fz = null;
    try { if (typeof window.__faceRect !== "function" && bx && window.__box && window.__box.plan && window.HF && HF.box && HF.box.at) fz = +HF.box.at(window.__box.plan, t).zoom || null; } catch (e) { fz = null; }
    spk = window.__pcFallback({ faceRect: typeof window.__faceRect === "function", face: f, box: bx, boxed: !!window.__box, plate, fz, FW, FH });
  }
  amb.spk = spk;
  // ---- density (2026-10-22, "holistic, not heavy"): the top-level visual groups on screen. A group is the outermost
  // card, chip, window, block of big type, catalog mount, graphic (svg/img/canvas) or [data-group] part that is visible
  // and covers 0.3 % of the frame or more; captions (.cap), the chrome, the world (z <= 1), data-decor and his shape
  // (an unclassed box around a <video>) are not. Type blocks (.sv, .cv-big) count once a word of them is in.
  // A large group (LARGE of the frame or more: a diagram, a stack, a takeover's scene) counts by what it holds (review
  // 2026-10-22: a whole stack read as one group however much it held, and text landing inside a block already up was
  // never counted): its items, one group per PER of them. An item: an outermost card, chip, node ([data-node],
  // [data-item]), window or medium inside it that can be seen, or a line of visible text no such item holds (inline
  // spans, kinetic words and letters walk up to their line; a title bar and data-decor don't count)
  const GSEL = ".cv-card,.cv-chip,.cv-win,.cv-big,.card,.chip,.pill,.sv,.hf-mount,[data-group],svg,img,canvas";
  const USEL = GSEL + ",[data-node],[data-item]", LARGE = 0.08, PER = 3;
  const INLINE = /^(SPAN|B|I|EM|STRONG|U|S|MARK|SMALL|SUB|SUP|CODE|A|TSPAN)$/;
  const lineOf = (x, stop) => { let p = x; while (p.parentElement && p.parentElement !== stop && (INLINE.test(p.tagName) || (p.dataset && (p.dataset.w != null || p.dataset.kc != null)))) p = p.parentElement; return p; };
  const readable = texts.filter((t1) => !t1.e.closest(".cap,[data-decor],.tbar"));
  const itemsIn = (G, skip) => {
    const units = [];
    for (const x of G.querySelectorAll(USEL)) {
      const up = x.parentElement && x.parentElement.closest(USEL);
      if ((up && up !== G && G.contains(up)) || (skip && skip.some((s) => s.contains(x))) || x.closest(".cap,[data-decor]")) continue;
      if (!shown(x) || alpha(x) < 0.3 || !inked(x)) continue;
      const r = clipTo(x, x.getBoundingClientRect());
      if (r.width < 8 || r.height < 8 || (r.width * r.height) / (FW * FH) < 0.001) continue;
      units.push(x);
    }
    const lines = new Set();
    for (const t1 of readable) {
      if (!G.contains(t1.e) || units.some((u) => u.contains(t1.e)) || (skip && skip.some((s) => s.contains(t1.e)))) continue;
      lines.add(lineOf(t1.e, G));
    }
    return units.length + lines.size;
  };
  const groups = [], tops = [];
  let gn = 0;
  for (const e of root.querySelectorAll(GSEL)) {
    const up = e.parentElement && e.parentElement.closest(GSEL);
    if ((up && up !== root && root.contains(up)) || e.closest(".cap,[data-decor]")) continue;   // outermost only
    const z = zOf(e);
    if (z >= chromeZ || z <= 1 || !shown(e)) continue;
    const r = clipTo(e, e.getBoundingClientRect());
    const w = Math.min(FW, r.right) - Math.max(0, r.left), h = Math.min(FH, r.bottom) - Math.max(0, r.top);
    if (w < 8 || h < 8 || (w * h) / (FW * FH) < 0.003 || alpha(e) < 0.3) continue;
    if ((e.classList.contains("sv") || e.classList.contains("cv-big")) && !inked(e)) continue;
    tops.push(e);
    const cls = typeof e.className === "string" ? e.className.split(/\s+/).find((c) => /^(cv-|card|chip|pill|sv|hf-mount)/.test(c)) : null;
    const name = (e.dataset && (e.dataset.group || e.dataset.mount)) || (cls ? `${cls}${(e.textContent || "").trim() ? " " + e.textContent.replace(/\s+/g, " ").trim().slice(0, 16) : ""}` : e.tagName.toLowerCase());
    const items = (w * h) / (FW * FH) >= LARGE ? itemsIn(e) : 0, k = Math.max(1, Math.ceil(items / PER));
    groups.push(k > 1 ? `${name} x${k} (${items} items)` : name);
    gn += k;
  }
  // a takeover's loose text: lines inside its [data-takeover] root that no counted group holds
  for (const T of root.querySelectorAll("[data-takeover]")) {
    if (!shown(T) || alpha(T) < 0.3 || zOf(T) >= chromeZ) continue;
    const items = itemsIn(T, tops.filter((g) => T.contains(g)));
    if (!items) continue;
    const k = Math.ceil(items / PER);
    groups.push(`takeover ${T.dataset.takeover} loose${k > 1 ? ` x${k}` : ""} (${items} items)`);
    gn += k;
  }
  amb.groups = groups;
  amb.gn = gn;
  out.push(amb);
  return out;
};

const raw = [], seen = [], ambS = [];   // seen: per sample, the readable blocks on screen (reading time + holds); ambS: ambition samples

const step = 1 / fps;
const t0 = Date.now();
// the speaker fallback (kit/qa/speaker.mjs) runs inside the probe: its source and the names of his footage go on the page
await page.evaluate((fn, re, flags) => { window.__pcFallback = (0, eval)(`(${fn})`); window.__pcFaceTrack = new RegExp(re, flags); },
  SP.fallbackSpeaker.toString(), SP.FACE_TRACK.source, SP.FACE_TRACK.flags);
for (let t = from; t <= to + 1e-6; t += step) {
  const tt = Math.round(t * 1000) / 1000;
  if (allowed(tt)) continue;
  let res;
  try { res = await page.evaluate(probe, tt, FW, FH, minText); } catch (e) { errs.push(`probe at ${tt}: ${e.message}`); continue; }
  for (const f of res) { if (f.kind === "_blocks") seen.push({ t: tt, list: f.list }); else if (f.kind === "_amb") ambS.push({ t: tt, ...f }); else raw.push({ t: tt, ...f }); }
}
const declared = await page.evaluate(() => window.__holds || []);
const pace = await page.evaluate(() => window.__pace || null);
// the engine's transition log (window.__trans: [{ t, kind, why, pair?, until? }], or a function returning it) and the
// zoom budget per track (work/tracks.json, which the build loads as D.tracks: { name: { max_zoom, sharp_px, soft_zoom,
// soft, kinds, w, h, ... } }; a page from before keeps D.tracks as { name: "assets/<file>" }, which has no budget), with
// D.pieces (which kind of footage plays when) for the per-kind contract
const transList = await page.evaluate(() => { try { const T = typeof window.__trans === "function" ? window.__trans() : window.__trans;
  return Array.isArray(T) ? T.map((x) => Object.assign({ t: +(x.t != null ? x.t : x.at), kind: String(x.kind || x.type || "?"), why: String(x.why || "") },
    x.pair != null ? { pair: x.pair } : {}, x.until != null && Number.isFinite(+x.until) ? { until: +x.until } : {})) : null; } catch (e) { return null; } });
const { trackInfo, edlPieces } = await page.evaluate(() => { try { const T = typeof D !== "undefined" && D && D.tracks ? D.tracks : {};
  const num = (v) => (v != null && Number.isFinite(+v) ? +v : undefined), pick = (v) => ({ max_zoom: num(v.max_zoom), sharp_px: num(v.sharp_px), soft_zoom: num(v.soft_zoom) });
  const info = Object.fromEntries(Object.entries(T).filter(([, v]) => v && typeof v === "object" && (Number.isFinite(+v.max_zoom) || Number.isFinite(+v.sharp_px)))
    .map(([k, v]) => [k, { ...pick(v), soft: num(v.soft), w: num(v.w), h: num(v.h),
      kinds: v.kinds && typeof v.kinds === "object" ? Object.fromEntries(Object.entries(v.kinds).filter(([, x]) => x && typeof x === "object").map(([q, x]) => [q, pick(x)])) : undefined }]));
  const P = typeof D !== "undefined" && D && Array.isArray(D.pieces) ? D.pieces.map((p) => ({ kind: p.kind, out_a: +p.out_a })).filter((p) => Number.isFinite(p.out_a)) : null;
  return { trackInfo: info, edlPieces: P }; } catch (e) { return { trackInfo: {}, edlPieces: null }; } });
// the joins the lens reframed (window.__lens[id].jumps: [{ t, ... }]), the takeovers (window.__takeovers) and the flat
// diagrams' geometry gate (HF.diagram.verify on every window.__diagrams entry with gate: true)
const joins = await page.evaluate(() => { try { return Object.values(window.__lens || {}).flatMap((L) => (L && Array.isArray(L.jumps) ? L.jumps : []))
  .map((j) => +j.t).filter(Number.isFinite); } catch (e) { return []; } });
const takeoverList = await page.evaluate(() => { try { return (window.__takeovers || []).map((x) => ({ a: +x.a, b: +x.b, kind: x.kind || null, in: x.in || null, out: x.out || null,
  dropped: Array.isArray(x.dropped) ? x.dropped.map((d) => ({ speaker: d && d.speaker != null ? String(d.speaker) : null, t: +(d && d.t) })) : [] })); } catch (e) { return []; } });
const diagramGate = await page.evaluate(() => { try { if (!window.HF || !HF.diagram || typeof HF.diagram.verify !== "function") return [];
  return (window.__diagrams || []).filter((d) => d && d.gate).map((d) => ({ id: d.id || null, type: d.type || null, title: d.title || null,
    show: (d.show || []).map(([a, b]) => [+a, b == null ? null : +b]), lines: HF.diagram.verify(d) })); } catch (e) { return [{ id: null, show: [], lines: [`the gate itself failed: ${e.message}`] }]; } });
await browser.close();

// reading time: a block of 4+ words (not spoken type) must stay long enough to read
const need = (w) => Math.min(8, 0.6 + 0.24 * w);
const vis = new Map();                  // block id -> [{a, b, words, text, px}]
for (const smp of seen) for (const b of smp.list) {
  if (b.spoken || b.words < 4) continue;
  const runs = vis.get(b.id) || [];
  const last = runs[runs.length - 1];
  if (last && smp.t - last.b <= step * 1.5 + 1e-6) { last.b = smp.t; last.words = Math.max(last.words, b.words); }
  else runs.push({ a: smp.t, b: smp.t, words: b.words, text: b.text, px: b.px });
  vis.set(b.id, runs);
}
for (const runs of vis.values()) for (const r of runs) {
  const dur = r.b - r.a + step;
  if (r.b + step >= to - 1e-6) continue;                                       // still up at the end of the range
  if (dur < 0.8 * need(r.words)) raw.push({ t: r.a, kind: "read", sev: "MEDIUM", text: `${r.words} words up ${dur.toFixed(1)} s (needs ~${need(r.words).toFixed(1)} s): ${r.text}`, rect: null, _a: r.a, _b: r.b });
}
// HyperFrames catalog mounts (kit/hf/mounts.py) are sub-compositions HyperFrames fills at render time, so this page load
// sees them empty: read them from the HTML. Each counts as something new entering the frame (the still check), and one
// whose variables carry text is a reading hold for qa.py (the viewer reads the quote, the notes, the chat).
const MOUNTS = [...fs.readFileSync(src, "utf8").matchAll(/<div id="mount-\d+"[^>]*>/g)].map((m) => {
  const at = (k) => { const r = m[0].match(new RegExp(`${k}="([^"]*)"`)); return r ? r[1] : null; };
  let vars = {};
  try { vars = JSON.parse((at("data-variable-values") || "{}").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&#x27;/g, "'")); } catch (e) { vars = {}; }
  const a = +at("data-start"), b = a + +at("data-duration");
  const words = ["text", "title", "lines", "messages", "label", "phrase", "detail_text", "headline"]
    .map((k) => String(vars[k] || "")).join(" ").split(/[\s|:]+/).filter((w) => w.length > 1).length;
  return { name: at("data-mount"), a, b, words };
});
// reading holds for qa.py: stretches with readable text on screen, the time they need, plus the declared holds
if (holdsOut) {
  const H = [];
  for (const smp of seen) {
    const rd = smp.list.filter((b) => !b.spoken && b.words >= 4 && b.px >= minText - 0.5);
    if (!rd.length) continue;
    const last = H[H.length - 1];
    if (last && smp.t - last.b <= step * 1.5 + 1e-6) { last.b = smp.t; rd.forEach((b) => (last._ids[b.id] = b.words)); }
    else { const o = { a: smp.t, b: smp.t, _ids: {}, why: "reading: " + rd[0].text }; rd.forEach((b) => (o._ids[b.id] = b.words)); H.push(o); }
  }
  const hs = H.map((h) => ({ a: +h.a.toFixed(2), b: +(h.b + step).toFixed(2), need: +Math.min(12, 0.6 + 0.24 * Object.values(h._ids).reduce((x, y) => x + y, 0)).toFixed(1), why: h.why }))
    .concat(declared.map((d) => ({ ...d, declared: true })))
    .concat(MOUNTS.filter((m) => m.words >= 4).map((m) => ({ a: +m.a.toFixed(2), b: +m.b.toFixed(2), need: +Math.min(12, 0.6 + 0.24 * m.words).toFixed(1), why: `reading: catalog ${m.name}` })));
  fs.writeFileSync(holdsOut, JSON.stringify(hs.sort((x, y) => x.a - y.a), null, 0));
  console.log(`holds: ${hs.length} (${declared.length} declared) -> ${holdsOut}`);
}

// merge consecutive samples of the same finding into spans
const spans = [];
for (const f of raw) {
  const key = `${f.kind}|${f.key || f.text}`;                                  // a catalog piece: by the piece
  const last = spans.findLast((s) => s.key === key && f.t - s.b <= step * 1.5 + 1e-6);
  if (f.kind === "read") { spans.push({ key, kind: f.kind, sev: f.sev, text: f.text, rect: null, a: f._a, b: f._b, fixed: true }); continue; }
  if (last) { last.b = f.t; last.text = f.text; if (f.px) last.px = Math.min(last.px, f.px); if (f.sev === "HIGH") last.sev = "HIGH"; }
  else spans.push({ key, kind: f.kind, sev: f.sev, text: f.text, rect: f.rect, a: f.t, b: f.t, px: f.px });
}
for (const s of spans) {
  s.dur = +(s.b - s.a + step).toFixed(2);
  if (s.kind === "blank") s.sev = s.dur >= 1.0 ? "HIGH" : s.dur >= 0.6 ? "MEDIUM" : "NIT";
  if (s.kind === "overlap" || s.kind === "on-card" || s.kind === "offscreen" || s.kind === "face" || s.kind === "under-box") s.sev = s.dur >= 0.4 ? s.sev : "NIT";
  if (s.kind === "small") s.sev = s.dur >= 0.8 ? s.sev : "NIT";
}
const kept = spans.filter((s) => s.sev !== "NIT");
// ---------------------------------------------------------------- ambition (2026-10-20, kit/refs/AUDIT_2026-10-20.md)
const portrait = FH > FW, runtime = Math.max(step, to - from);
const AMB = [];
// linger: a part placed straight on a full-frame layer that stays up (no end): small parts over 20 s
{
  const runs = new Map();
  for (const smp of ambS) for (const p of smp.persist) {
    const r = runs.get(p.id);
    if (r && smp.t - r.b <= step * 1.5 + 1e-6) { r.b = smp.t; r.frac = Math.max(r.frac, p.frac); }
    else if (!r || smp.t - r.b > step * 1.5 + 1e-6) runs.set(p.id, { a: smp.t, b: smp.t, frac: p.frac, label: p.label });
  }
  for (const r of runs.values()) if (r.b - r.a + step >= 20 && r.frac < 0.2 && !(r.b + step >= to - 1e-6 && r.a > to - Math.min(30, 0.2 * runtime)))   // a sign-off up to the end is fine
    kept.push({ kind: "linger", sev: "HIGH", text: `up ${(r.b - r.a + step).toFixed(0)} s with no end (give it an end or put it in a layer): ${r.label}`, a: r.a, b: r.b, dur: +(r.b - r.a + step).toFixed(2) });
}
// ---------------------------------------------------------------- the speaker, density, transitions (2026-10-22)
const spkS = ambS.map((s) => ({ t: s.t, ...s.spk }));
const SPK = SP.speakerStats(spkS, { step, FW, FH, tracks: trackInfo, pieces: edlPieces, joins });
const longForm = !portrait && runtime >= 120;
for (const f of SP.speakerFindings(SPK, { longForm, a: from, b: to })) AMB.push(f);
// takeovers straight from window.__takeovers (lengths, the face gap, dropped template shots): MEDIUM
for (const f of SP.takeoverFindings(takeoverList)) if (f.b >= from - 1e-6 && f.a <= to + 1e-6) kept.push(f);
// the flat diagrams' geometry (HF.diagram.verify): a shared port or a line behind a box HIGH, the rest MEDIUM; timed by
// each entry's show windows (none: the whole range). A defect of the drawing, not ambition: --no-ambition leaves it
for (const d of diagramGate) {
  const wins = (d.show && d.show.length ? d.show : [[from, to]]).map(([a, b]) => [Math.max(from, a), Math.min(to, b == null ? to : b)]).filter(([a, b]) => b > a);
  const nm = `diagram${d.type ? " " + d.type : ""}${d.title ? ` "${d.title}"` : d.id ? " " + d.id : ""}`;
  for (const line of d.lines || []) {
    // shared: two connectors on one point (verify's "N px from where ... fan the ports" with N within its 3 px stack)
    const gap = line.match(/ (\d+) px from where .*fan the ports/), shared = !!gap && +gap[1] <= 3;
    for (const [a, b] of wins) kept.push({ kind: "diagram", sev: shared || /passes behind/.test(line) ? "HIGH" : "MEDIUM", a, b, dur: +(b - a).toFixed(2), text: `${nm}: ${line}` });
  }
}
const DEN = SP.densityStats(ambS.map((s) => ({ t: s.t, n: s.gn != null ? s.gn : s.groups.length, labels: s.groups })), step);
for (const f of DEN.findings) AMB.push(f);
const TR = transList ? SP.transStats(transList) : null;
if (TR) for (const f of TR.findings) kept.push(f);
// layout share: the box's slot, else the slot __speaker's kind gives (the canvas look). A hidden box while the page's own
// face says he is on (claude-makes-claude's full-frame A-roll) is his slot, not a graphic. The gate (speaker.mjs
// layoutGate): the sides are one layout on a page that publishes __speaker (HIGH); a page from before v11 keeps its
// per-side HIGH and gets the merged share as MEDIUM, so a film that passed then (kit/film/example) does not stop now
const slots = {};
for (const smp of ambS) {
  let slot = smp.slot || null;
  if (smp.spk && (smp.spk.src === "__speaker" ? !slot : slot === "off (graphic)" && smp.spk.on)) slot = SP.slotOf(smp.spk, FW, FH);
  if (slot) slots[slot] = (slots[slot] || 0) + step;
}
const LAY = SP.layoutGate(slots, runtime, { contract: !!(SPK && SPK.src === "__speaker"), a: from, b: to });
const shareList = LAY.list, sides = LAY.sides;
for (const f of LAY.findings) AMB.push(f);
// still: the longest stretch with nothing new entering the frame. A framing change on him (the speaker section) and a
// transition (window.__trans) are change too: the camera carries the energy, not more elements (SCENES.md §10)
const moved = [...(SPK && SPK.changes ? SPK.changes : []), ...(TR ? TR.times : [])];
let lastEvent = from, longest = 0, la = from, prev = new Set();
for (const smp of ambS) {
  const cur = new Set(smp.sig);
  const fresh = [...cur].some((x) => !prev.has(x)) || MOUNTS.some((m) => m.a > smp.t - step - 1e-6 && m.a <= smp.t + 1e-6)
    || moved.some((x) => x > smp.t - step - 1e-6 && x <= smp.t + 1e-6);
  if (fresh) { if (smp.t - lastEvent > longest) { longest = smp.t - lastEvent; la = lastEvent; } lastEvent = smp.t; }
  prev = cur;
}
if (to - lastEvent > longest) { longest = to - lastEvent; la = lastEvent; }
const [stillHigh, stillMed] = portrait ? [5, 3] : docMode ? [15, 10] : [10, 6];
if (longest > stillMed) AMB.push({ kind: "still", sev: longest > stillHigh ? "HIGH" : "MEDIUM", text: `${longest.toFixed(1)} s with nothing new entering the frame (max ${stillMed}-${stillHigh} s): land a card, a line, a move`, a: la, b: la + longest, dur: +longest.toFixed(2) });
// variety: the distinct visual components the film's own script calls (not the inlined kit)
const html = fs.readFileSync(src, "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]).filter((x) => x.includes("__timelines[") && /const D = /.test(x));
const film = scripts.length ? scripts[scripts.length - 1] : "";
// the components are kit/hf/registry.json's (kit/hf/tools/registry.py): each entry's `match` (and the factory it `needs`)
// found in the film's script; words-only ids (say, line, kinetic...) and the speaker camera/box and quiet don't count
const REG = JSON.parse(fs.readFileSync(new URL("../hf/registry.json", import.meta.url), "utf8")).components || {};
const NOT_VISUAL = new Set(["box", "camera", "quiet"]);
const comps = new Set();
for (const [id, c] of Object.entries(REG)) {
  if (c.words_only || NOT_VISUAL.has(id) || !c.match) continue;
  const where = c.scope === "html" ? html : film;                     // catalog mounts sit in the page's HTML (kit/hf/mounts.py)
  if (new RegExp(c.match).test(where) && (!c.needs || new RegExp(c.needs).test(where))) comps.add(id);
}
// the minimum (2026-10-22): Reels 4; long-form 1.2 a minute, 6-10 (calm long-form). MEDIUM: the density gate outranks it
const minutes = runtime / 60, compNeed = runtime < 120 ? 4 : Math.min(10, Math.max(6, Math.round(1.2 * minutes)));
if (film && comps.size < compNeed) AMB.push({ kind: "variety", sev: "MEDIUM", text: `${comps.size} distinct visual components in the script (needs ${compNeed} for ${minutes.toFixed(1)} min): pick by what each passage does, never to fill a frame (kit/refs/SCENES.md; python3 kit/hf/tools/registry.py --unused)`, a: from, b: to, dur: 0 });
if (docMode) for (const f of AMB) if (f.sev === "HIGH" && (f.kind === "layout" || (f.kind === "away" && f.dur <= 30))) { f.sev = "MEDIUM"; f.text += " (documentary: MEDIUM)"; }
for (const f of AMB) { if (!gateAmbition && f.sev === "HIGH") f.sev = "MEDIUM"; kept.push(f); }
if (errs.length) kept.unshift({ kind: "error", sev: "HIGH", text: [...new Set(errs)].slice(0, 5).join(" | "), a: 0, b: 0, dur: 0 });
// a catalog piece this check could not fill: its text went unchecked (look at its frames), the render may still be fine
for (const m of mountState) if (!m.ok) kept.push({ kind: "mount", sev: "MEDIUM", text: `catalog ${m.name}: not checked (${m.err || "it never registered a timeline"})`, a: m.a, b: m.a, dur: 0 });
const order = { HIGH: 0, MEDIUM: 1 };
kept.sort((x, y) => order[x.sev] - order[y.sev] || x.a - y.a);
const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${(s % 60).toFixed(1).padStart(4, "0")}`;
const high = kept.filter((s) => s.sev === "HIGH").length;
console.log(`${high ? "FAIL" : kept.length ? "WARN" : "PASS"}: ${path.basename(path.dirname(path.resolve(src)))}  ${Math.round(to - from)} s at ${fps} fps in ${((Date.now() - t0) / 1000).toFixed(0)} s: ${high} HIGH, ${kept.length - high} MEDIUM`);
for (const s of kept) console.log(`  ${s.sev.padEnd(6)} ${s.kind.padEnd(9)} ${mmss(s.a)}-${mmss(s.b)} (${s.a.toFixed(2)}-${s.b.toFixed(2)} s)  ${s.px ? s.px + " px: " : ""}${s.text}${s.rect ? `  @${s.rect.x},${s.rect.y} ${s.rect.w}x${s.rect.h}` : ""}`);
if (mountState.length) console.log(`  catalog pieces: ${mountState.filter((m) => m.ok).length}/${mountState.length} filled and checked [${mountState.map((m) => m.name).join(", ")}]`);
console.log(`  ambition: components ${comps.size}/${compNeed} [${[...comps].sort().join(", ")}]`);
const pct = (x) => `${Math.round(100 * x)}%`;
if (shareList.length) console.log(`  ambition: layouts ${shareList.map(([k, v]) => `${k} ${pct(v / runtime)}` + (sides[k] ? ` (${Object.entries(sides[k]).map(([s, x]) => `${s.split(" ").pop()} ${pct(x / runtime)}`).join(", ")})` : "")).join(", ")}`);
console.log(`  ambition: longest stretch with nothing new ${longest.toFixed(1)} s at ${mmss(la)}` + (pace ? `; box: face ${Math.round(100 * pace.faceShare)}%, full ${Math.round(100 * pace.fullShare)}%, ${pace.perMin} moves/min, longest away ${pace.maxAway} s` : ""));
// SPEAKER: where he is and how the camera moves on him (kit/qa/speaker.mjs)
if (!SPK || SPK.none) console.log("  speaker: none published (no window.__speaker, __faceRect or __box): face, framing and zoom not measured");
else {
  const via = SPK.src === "__speaker" ? "window.__speaker" : `${SPK.src} fallback: on / off estimated, no zoom or lens (no window.__speaker)`;
  console.log(`  speaker: face on ${pct(SPK.on)}, off ${pct(SPK.off)}` + (SPK.full != null ? `, full frame ${SPK.fullMin ? ">= " : ""}${pct(SPK.full)}` : ", full frame n/a")
    + `; takeovers ${SPK.takeovers.length}${SPK.takeovers.length ? ` (${SPK.takeovers.map((r) => r.dur.toFixed(1) + " s").slice(0, 8).join(", ")})` : ""}, longest away ${SPK.longestAway.toFixed(1)} s  [${via}]`);
  // the pace (P-S4): thought moves are what the 7.5-15 a minute want is about; a reframe on a jump cut is the cut's own
  // move (counted apart); every framing change is the number precheck has always printed
  console.log(`  speaker: ${SPK.thoughtPerMin} thought moves per minute while he is on (want ${SP.SPEAKER.want[0]}-${SP.SPEAKER.want[1]}: one every 4-8 s; `
    + `${SPK.thought} over ${SPK.judged.toFixed(1)} s framed), plus ${SPK.joinMoves} jump-cut reframes (${SPK.joinPerMin} a minute, not counted against the pace${joins.length ? "" : ": no window.__lens joins on this page"}); `
    + `${SPK.perMin} framing changes a minute in all`);
  console.log("  speaker: " + (SPK.longest ? `longest unchanged framing ${SPK.longest.dur.toFixed(1)} s at ${mmss(SPK.longest.a)}${SPK.longest.declared ? " (a declared hold)" : ""}` : "no framing measured")
    + (SPK.unmeasured > 0 ? ` (${SPK.unmeasured.toFixed(1)} s on with no face, rect or zoom: unmeasured)` : "")
    + (SPK.corner > 0 ? ` (${SPK.corner.toFixed(1)} s in a corner: framing not judged)` : "")
    + `; zoom ${SPK.zoom ? `max ${SPK.zoom.max.toFixed(2)}x (budget ${SPK.zoom.budget.toFixed(2)}x${SPK.zoom.soft != null ? `, soft ${SPK.zoom.soft.toFixed(2)}x` : ""}`
      + `${SPK.zoom.how === "sample" ? ": the page's own cap" : SPK.zoom.how === "contract" ? ": tracks.json's sharp_px for this shape" : Object.keys(trackInfo).length ? "" : ", the default: no tracks.json in D.tracks"})` : "not published"}`);
  if (SPK.softRuns && SPK.softRuns.length)
    console.log(`  NOTE   the soft allowance was in force (__speaker.soft: mild softening the lens chose for a jump reframe or a drift) at `
      + SPK.softRuns.slice(0, 8).map((r) => `${mmss(r.a)}-${mmss(r.b)}`).join(", ") + (SPK.softRuns.length > 8 ? ` +${SPK.softRuns.length - 8}` : "") + ": look at those frames");
}
if (takeoverList.length) console.log(`  takeovers: ${takeoverList.map((x) => `${x.kind || "?"} ${x.a.toFixed(1)}-${x.b.toFixed(1)} s (${(x.b - x.a).toFixed(1)} s, in ${x.in || "?"}, out ${x.out || "?"}`
  + `${x.dropped.length ? `, ${x.dropped.length} shots dropped` : ""})`).join(", ")}  [window.__takeovers]`);
if (diagramGate.length) console.log(`  diagrams: ${diagramGate.length} flat (gated), ${diagramGate.reduce((n, d) => n + (d.lines || []).length, 0)} geometry findings  [HF.diagram.verify]`);
console.log(`  density: visual groups per sample p50 ${DEN.p50}, p90 ${DEN.p90}, max ${DEN.max} at ${mmss(DEN.at)}; more than ${SP.DENSITY.med} for ${pct(DEN.share)} of the runtime`);
console.log(TR ? `  transitions: ${TR.n}${TR.n ? ` (${Object.entries(TR.kinds).sort((x, y) => y[1] - x[1]).map(([k, v]) => `${k} ${v}`).join(", ")})` : ""}, whips ${pct(TR.whips)}, ${TR.repeats.length} repeats`
  : "  transitions: none published (window.__trans)");
// the verdict again on the last line, with every HIGH by kind and time: kit/film and kit/reel print only the tail of
// this output, and a long-form page's MEDIUM lines can push the first line and the HIGH ones out of it (review 2026-10-22)
// (by kind, in order of first time: up to 3 distinct start times each, then a count)
{
  const byKind = new Map();
  for (const s of kept) if (s.sev === "HIGH") { const ts = byKind.get(s.kind) || []; if (!ts.includes(mmss(s.a))) ts.push(mmss(s.a)); byKind.set(s.kind, ts); }
  const list = [...byKind].map(([k, ts]) => `${k} ${ts.slice(0, 3).join(" ")}${ts.length > 3 ? ` +${ts.length - 3}` : ""}`).join(", ");
  console.log(`precheck ${high ? "FAIL" : kept.length ? "WARN" : "PASS"}: ${high} HIGH${high ? ` [${list}]` : ""}, ${kept.length - high} MEDIUM`);
}
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify({ total, fps, findings: kept, catalog: mountState,
  ambition: { components: [...comps], need: compNeed, layouts: Object.fromEntries(shareList), longestStill: longest, pace },
  // perMin / moves: every framing change (as before); thoughtPerMin / thought: the pace, jump-cut reframes (joinMoves) apart
  speaker: SPK && !SPK.none ? { src: SPK.src, est: SPK.est, on: SPK.on, off: SPK.off, full: SPK.full, fullMin: SPK.fullMin, unmeasured: SPK.unmeasured, corner: SPK.corner, perMin: SPK.perMin, moves: SPK.moves,
    thoughtPerMin: SPK.thoughtPerMin, thought: SPK.thought, joinPerMin: SPK.joinPerMin, joinMoves: SPK.joinMoves, judged: SPK.judged, joins: joins.length, longest: SPK.longest,
    longestAway: SPK.longestAway, takeovers: SPK.takeovers, hookOff: SPK.hookOff, zoom: SPK.zoom, soft: SPK.softRuns, stretches: SPK.stretches.filter((s) => s.dur > SP.SPEAKER.med) } : null,
  takeovers: takeoverList, diagrams: diagramGate,
  density: { p50: DEN.p50, p90: DEN.p90, max: DEN.max, at: DEN.at, share: DEN.share },
  transitions: TR ? { n: TR.n, kinds: TR.kinds, whips: TR.whips, repeats: TR.repeats } : null }, null, 1));
process.exit(high ? 3 : 0);
