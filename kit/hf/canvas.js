/*
 * kit/hf/canvas.js: one big studio canvas with a camera (2026-10-20, films/chakra-redline v2). Built after the owner
 * called a slide-style edit "awesomely stupid" and after studying premium talking-head edits frame by frame:
 * Enrico Tartarotti (a white seamless studio, macro UI, a gradient highlighter, exploded 3D layers, a glowing beam
 * between two ideas), Ali Abdaal (a 3D tri-fold of panels with his live video in one, speaker cards with a glow,
 * stat cards), Ishan Sharma (giant condensed type behind the figure, the speaker shrinking into a card beside a
 * headline, one card branching into three), Think School (one diagram that builds on one canvas). Their common
 * thread is that nothing is a slide. Everything sits on one lit stage, and a camera moves between the parts:
 *
 *   const C = HF.canvas(K, ROOT, { w: 5760, h: 3240 });              // the world (px); the camera starts at its centre
 *   C.cam(t, { x, y, z }, { dur, ease })                              // glide / push / whip (motion blur by speed)
 *   const L = C.layer("mid")                                           // layers: bg 0.2, far 0.75, mid 1, near 1.2 parallax
 *   C.window(L, x, y, w, h, { img, url, ry, rx })                       a light browser window in 3D
 *   C.card(L, x, y, w, h, t, { html, ry, from, drift, hold })           a 3D card that lands (z -420, rotateY) and drifts
 *                                                                       (drift: the turn after it lands, 2.2 when unset,
 *                                                                       false = none; whitespace caps it at 0: driftMax)
 *   C.highlight(L, [x, y, w, h], t)                                     a gradient highlighter sweep (multiply)
 *   C.beam(L, [[x, y], ...], t, { dur })                                a glowing gradient line that draws
 *   C.big(L, "GRINDING DSA", x, y, t, { size })                         giant condensed caps (put on "far": behind him)
 *   C.speaker("cutout", [{ t, mode: "stage" | "card", x, y, s, w, h, at }], { plate: "room" })   his cut-out on the stage
 *                                                                       (a soft floor shadow), or his real room in a glowing card
 *                                                                       (a card shot's `at`: its own focus in source px, e.g. a
 *                                                                       screen recording's cam bubble or the post's video;
 *                                                                       `off`: the card hidden, and the next shot fades it in
 *                                                                       over its dur: a card that arrives with its footage)
 *   C.speaker(id, [{ t, mode: "frame", full }], { clean, lens, ride, primary })   v11 (2026-10-22): the seated frame (full
 *                                                                       bleed or a large card, inside the take's clean rect),
 *                                                                       the lens (HF.motion.lens: the camera on him inside
 *                                                                       every shape; on for D.lens.track), his shape riding
 *                                                                       the camera; window.__speaker (the engine contract)
 *   C.chart(L, x, y, w, h, { pts, keys: [{ t, u, dur }], land })        a line chart: gradient stroke, a glowing tip that
 *                                                                       draws in steps (u 0..1) and lands with a pop
 *   C.at("far", { x, y, z }, sx, sy)                                    a layer's px that sit at screen px (sx, sy) for a camera
 *   C.blocks(L, [[x, y, w, h, colour]], t)                              pastel blocks that pop in (decor, for depth on "far")
 *   C.dof(a, b, { fade: [t, dur] })                                     a macro lens: the frame's edges blurred, sharp centre
 *   C.adopt(st, "marker-highlight")                                     a catalog piece (film.py MOUNTS) rides the camera: it
 *                                                                       moves into st, a flat station (station with [x, y]),
 *                                                                       its box then in the station's px
 *   C.takeover(a, b, { kind: "type" | "diagram" | "evidence" | "list", in, out, ... })   v11 (2026-10-22, kit/hf/trans.js): a
 *                                                                       full-screen scene with him off (absent, never cut out):
 *                                                                       a plate in the look's paper over the canvas, the scene
 *                                                                       on its own camera, his shape off at a and back at b (the
 *                                                                       shape he had); { mount } / { build } for any scene. Its
 *                                                                       transitions (zoom, card, match, fade, cut) and HF.trans
 *                                                                       (T.zoomThrough, T.chapter, ...) are kit/hf/trans.js's
 * Rules: one accent gradient (C.G) on a warm paper seamless (C.PAPER); entrances ease out (HF.E.in), moves on screen ease in-out (HF.E.move), exits ease
 * in; camera moves 0.5-1.2 s; a held frame keeps a slow push (never a still slide); sound on every move that carries
 * meaning (a whoosh under the camera, a pop when a card lands), all of it pure functions of time.
 *
 * Looks (2026-10-22): HF.canvas(K, ROOT, { look: "whitespace" }) paints the same stage white (kit/presets/whitespace):
 * every colour, surface and type the canvas draws comes from the look's stage tokens (core.js HF.LOOKS[look].stage,
 * read back as C.stage), and its CSS classes read them as CSS variables (--cv-*). The default stays canvas_studio, whose
 * tokens are the literals this file had, so its pages render pixel-identically. On whitespace C.G is one solid accent
 * (a beam is an ink line with an accent head, the highlighter a tint marker, the chart one accent stroke), C.PAPER is a
 * white cyclorama with neutral blocks, and his shape has an e3 shadow instead of the glow ring and the pastel back block.
 * Cards and windows land, then hold still (the stage's driftMax 0, whatever drift a template passes; the camera carries
 * the energy), and a film's o.palette acc becomes the stage's one accent too (a solid-accent stage follows HF.C.acc),
 * so the page never shows two.
 * { look: false }: the frame applied its own look; the stage is that look's if it has one, else canvas_studio's.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit || !HF.keyed) throw new Error("kit/hf/canvas.js needs core.js first");
  const NS = "http://www.w3.org/2000/svg";
  // canvas_studio's stage (core.js HF.LOOKS.canvas_studio.stage): the module-level defaults (HF.canvas.G). A canvas reads
  // its own look's stage (ST below), so these are only what a page gets with no look that has one.
  const ST0 = HF.LOOKS.canvas_studio.stage;
  const G = { a: ST0.grad[0], b: ST0.grad[1], c: ST0.grad[2] };          // the one accent gradient (violet -> rose -> amber)
  // the studio: a warm paper seamless (a cool grey one read as a template; the critic, 2026-10-20), pastel blocks for depth
  // The classes read the look's stage as CSS variables (set per canvas in HF.canvas); each fallback is canvas_studio's
  // value, so a page whose variables are unset draws exactly what it drew before 2026-10-22.
  const CSS = `
    .cv-win { position: absolute; border-radius: 22px; background: var(--cv-win-bg, #fff); overflow: hidden; transform-style: preserve-3d;
      box-shadow: var(--cv-win-shadow, 0 1px 0 rgba(255,255,255,.9) inset, 0 0 0 1px rgba(20,20,40,.08), 0 30px 80px rgba(30,30,60,.16), 0 8px 22px rgba(30,30,60,.08)); }
    .cv-bar { position: absolute; left: 0; top: 0; right: 0; height: 54px; background: var(--cv-bar, #F4F4F7); border-bottom: 1px solid var(--cv-bar-line, #E7E7EC);
      display: flex; align-items: center; gap: 10px; padding: 0 22px; }
    .cv-bar i { width: 14px; height: 14px; border-radius: 50%; display: inline-block; }
    .cv-url { margin-left: 18px; flex: 1; height: 32px; border-radius: 9px; background: var(--cv-url, #fff); border: 1px solid var(--cv-url-line, #E5E5EA);
      font: 500 18px/30px var(--cv-label, "Atkinson", sans-serif); color: var(--cv-url-ink, #6b6b75); padding: 0 14px; white-space: nowrap; overflow: hidden; }
    .cv-card { position: absolute; border-radius: 28px; background: var(--cv-card-bg, rgba(255,255,255,.92)); transform-style: preserve-3d;
      box-shadow: var(--cv-card-shadow, 0 0 0 1px rgba(20,20,40,.07), 0 30px 70px rgba(30,30,60,.14), 0 6px 18px rgba(30,30,60,.07)); }
    .cv-big { position: absolute; font-family: var(--cv-big-font, "ArchivoCond", sans-serif); font-weight: var(--cv-big-w, 900); text-transform: var(--cv-big-case, uppercase);
      line-height: var(--cv-big-lh, .86); letter-spacing: var(--cv-big-track, -0.01em); white-space: nowrap; color: var(--cv-big-ink, #16161C); }
    .cv-t { font-family: var(--cv-t-font, "Schibsted", sans-serif); font-weight: var(--cv-t-w, 800); color: var(--cv-t-ink, #16161C); letter-spacing: var(--cv-t-track, -0.02em); }
    .cv-s { font-family: var(--cv-s-font, "Atkinson", sans-serif); font-weight: var(--cv-s-w, 700); color: var(--cv-s-ink, #4A4A55); }
    .cv-chip { position: absolute; display: inline-flex; align-items: center; gap: 12px; padding: 12px 20px; border-radius: 999px; background: var(--cv-chip-bg, #fff);
      box-shadow: var(--cv-chip-shadow, 0 0 0 1px rgba(20,20,40,.08), 0 10px 30px rgba(30,30,60,.12)); font: var(--cv-chip-w, 700) 32px/1 var(--cv-label, "Atkinson", sans-serif);
      color: var(--cv-chip-ink, #2a2a33); white-space: nowrap; }`;
  // the turn a landed card / window / chip keeps making (pure; tests/test_looks_whitespace.py): the template's drift or
  // 2.2 (false or 0 = none), capped by the stage's driftMax (whitespace 0: it lands once, then holds still, whatever a
  // template copied from canvas_studio passes, e.g. its clue cards' drift: 1.2; the restraint rule, review 2026-10-22).
  // A template's drift: 0 used to read as 2.2 (falsy); no film passed it (grep, 2026-10-22), so 0 now means none.
  const driftOf = (x, S) => {
    let d = x.drift != null ? x.drift : 2.2;
    if (d && S.driftMax != null) d = Math.sign(d) * Math.min(Math.abs(d), S.driftMax);
    return d || 0;
  };
  // the stage's accent (pure; tested): { G (the three stops), head (the beam's node, the chart tip's fallback), hl (the
  // marker's colour, null: the gradient) }. A solid-accent stage (whitespace: its three stops agree) follows the accent
  // the frame really has: a film's o.palette acc (HF.lookOver) replaces the stops, the head and the marker's tint (17 %
  // of it on white; 17 % of #5646D6 is #E2E0F8, next to the look's #E4DFFF), so the page keeps ONE accent instead of
  // the kit's in the beams and the film's in the cards. canvas_studio's stops differ (its gradient is its own, as it
  // always was), and with no palette acc is the stop itself: both keep the stage exactly as it is.
  const accentOf = (S, acc) => {
    const g = S.grad, solid = g[0] === g[1] && g[1] === g[2];
    const re = solid && acc && String(acc).toLowerCase() !== String(g[0]).toLowerCase() ? acc : null;
    return { G: re ? { a: re, b: re, c: re } : { a: g[0], b: g[1], c: g[2] }, head: re && S.beam.head === g[0] ? re : S.beam.head,
      hl: re && S.hl.bg ? `color-mix(in srgb, ${re} 17%, #FFFFFF)` : S.hl.bg || null };
  };
  // the stage's CSS variables (the classes above), from a look's stage tokens
  const stageVars = (S) => ({ "win-bg": S.win.bg, "win-shadow": S.win.shadow, bar: S.win.bar, "bar-line": S.win.barLine, url: S.win.url, "url-line": S.win.urlLine,
    "url-ink": S.win.urlInk, label: S.label, "card-bg": S.card.bg, "card-shadow": S.card.shadow, "big-font": S.big.font, "big-w": S.big.weight, "big-case": S.big.case,
    "big-lh": S.big.lh, "big-track": S.big.track, "big-ink": S.big.ink, "t-font": S.t.font, "t-w": S.t.weight, "t-ink": S.t.ink, "t-track": S.t.track,
    "s-font": S.s.font, "s-w": S.s.weight, "s-ink": S.s.ink, "chip-bg": S.chip.bg, "chip-shadow": S.chip.shadow, "chip-ink": S.chip.ink, "chip-w": S.chip.weight || 700 });

  HF.canvas = function (K, ROOT, o = {}) {
    const tl = K.tl, Q = K.Q, el = K.el, WD = K.width, HT = K.height;
    const CW = o.w || WD * 3, CH = o.h || HT * 3;
    if (!document.getElementById("hf-canvas-css")) { const s = document.createElement("style"); s.id = "hf-canvas-css"; s.textContent = CSS; document.head.append(s); }
    // the kit's components take the canvas's ink, type and accent: canvas_studio, or o.look ("whitespace")
    if (o.look !== false) HF.look(typeof o.look === "string" ? o.look : "canvas_studio", HF.lookOver(o.palette));
    // this canvas's stage: the look's (canvas_studio, whitespace), or canvas_studio's for a look that has none
    const ST = HF.LOOK.stage || ST0;
    const { G, head: HEAD, hl: HLBG } = accentOf(ST, HF.C.acc);           // the stage's accent (a film's palette on whitespace)
    const GRAD = `linear-gradient(90deg, ${G.a} 0%, ${G.b} 70%, ${G.c} 100%)`;   // one solid colour when the three stops agree
    const PAPER = { seamless: ST.seamless, edge: ST.edge, pastel: ST.pastel };
    Object.entries(stageVars(ST)).forEach(([k, v]) => document.documentElement.style.setProperty("--cv-" + k, String(v)));
    ROOT.style.background = PAPER.edge;
    // ---------------------------------------------------------------- the studio: a white seamless, lit from the front
    const back = el(ROOT, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:0;background:${PAPER.seamless}`);
    back.dataset.decor = "1";
    // the camera's view: every layer is inside, each with its own parallax (depth); the motion blur filter rides on it
    const svg = document.createElementNS(NS, "svg"); svg.setAttribute("width", 0); svg.setAttribute("height", 0); svg.style.position = "absolute";
    svg.innerHTML = `<defs><filter id="cv-mb" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur id="cv-mbg" stdDeviation="0 0"/></filter>
      <linearGradient id="cv-g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${G.a}"/><stop offset=".7" stop-color="${G.b}"/><stop offset="1" stop-color="${G.c}"/></linearGradient></defs>`;
    ROOT.append(svg);
    const view = el(ROOT, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:2;overflow:hidden`);
    const P = { bg: 0.2, far: 0.75, mid: 1, spk: 1, near: 1.2 };
    const Z = { bg: 1, far: 2, mid: 3, spk: 5, near: 6 };
    const layers = {};
    Object.keys(P).forEach((n) => { layers[n] = el(view, `left:0;top:0;width:${CW}px;height:${CH}px;transform-origin:0 0;z-index:${Z[n]};transform-style:preserve-3d;perspective:2200px`); });
    // ---------------------------------------------------------------- transitions (kit/hf/trans.js, 2026-10-22)
    // ZM: zooms about a point on the page (a zoom-through's dive into an element or his eyes, and the landing from 3x on
    // the far side of the cut): { t0, t1, k0, k1, ease, pt () -> [x, y] }, the scale in log space. They move the view and
    // his shape together (a camera move: everything in frame zooms, his footage blurs with the speed like the canvas).
    // A page with none (every page before 2026-10-22) writes nothing new: no transform, no extra blur.
    const ZM = [];
    const zoomAt = (t) => {
      for (const z of ZM) if (t >= z.t0 - 1e-6 && t < z.t1 - 1e-6) {
        if (z.busy) continue;                                           // its point is being measured (through this view)
        const e = (z.ef = z.ef || (typeof z.ease === "function" ? z.ease : gsap.parseEase(z.ease || "expo.in")))(Math.min(1, Math.max(0, (t - z.t0) / (z.t1 - z.t0))));
        if (!z.p && typeof z.pt === "function") { z.busy = true; try { z.p = z.pt(); } finally { z.busy = false; } }
        const p = z.p || z.pt;
        return { k: z.k0 * Math.pow(z.k1 / z.k0, e), px: p[0], py: p[1] };
      }
      return null;
    };
    // a landing (a zoom from its peak down, k0 > k1): the speed blur covers its cut frame, half the next, and the view and
    // his shape are sharp from the third (fix round 2026-10-23: the landing sat at the 22 px cap for ~5 frames). -> the
    // factor on the blur at t (1 outside every landing)
    const landF = (t) => { let f = 1; for (const z of ZM) if (z.k0 > z.k1 && t >= z.t0 - 1e-6 && t < z.t1 - 1e-6) f = Math.min(f, Math.max(0, 1 - ((t - z.t0) * (K.fps || 30)) / 2)); return f; };
    // the maps HF.trans.rectAt reads (an element's page rect at any t): each layer's camera (with its parallax) and the view's zoom
    Object.keys(P).forEach((n) => { layers[n].__trMap = (t) => { const s = state(t), p = P[n], z = 1 + (s.z - 1) * p, cx = c0.x + (s.x - c0.x) * p, cy = c0.y + (s.y - c0.y) * p;
      return { k: z, ox: WD / 2 - cx * z, oy: HT / 2 - cy * z }; }; });
    view.__trMap = (t) => { const z = zoomAt(t); return z ? { k: z.k, ox: (1 - z.k) * z.px, oy: (1 - z.k) * z.py } : { k: 1, ox: 0, oy: 0 }; };
    // ---------------------------------------------------------------- the camera
    const c0 = { x: o.x != null ? o.x : CW / 2, y: o.y != null ? o.y : CH / 2, z: o.z || 1 };
    const keys = [];
    let at = null;
    // a whip (0.7 s or less) lands on the nearest beat within 0.12 s when the page has a music map (D.music); x.beat = false
    // keeps t. Slower glides and pushes are left alone.
    // x.log false: a transition logs itself (kit/hf/trans.js), so this key stays out of the camera's own log below;
    // x.cut: a hard cut (trans.js): the frame before it takes no blur from the jump
    const cam = (t, v, x = {}) => { const d0 = x.dur || 0.9; if (x.beat !== false && d0 <= 0.7) t = HF.music.snap(t + d0, { early: 0.12, late: 0.12 }) - d0;
      keys.push(Object.assign({ t: Q(t), dur: x.dur || 0.9, ease: x.ease || HF.E.move, v }, x.log === false ? { nolog: true } : {}, x.cut ? { cut: true } : {})); at = null;
      if (x.sfx !== false && (x.whoosh || (x.dur || 0.9) <= 0.7)) K.sfx(x.whoosh || "whoosh/whoosh__fast-transitions-swoosh__mixkit-3115", t + (x.dur || 0.9) * 0.45, x.db != null ? x.db : -20); };
    // slow pushes while a frame holds (added to z). Each one lets go during the next camera move after it, eased with
    // that move (kept for good, they added up: 1.22x by the end of v2, and cards fell off the frame's edges)
    const pushes = [];
    const state = (t) => { if (!at) { at = HF.keyed(keys, c0, { log: o.logZoom === false ? [] : ["z"] });   // zoom at an even pace
        for (const p of pushes) { const nx = keys.filter((k) => k.t >= p.b - 0.05).sort((x, y) => x.t - y.t)[0];
          p.rel = nx ? { t: nx.t, dur: nx.dur, e: typeof nx.ease === "function" ? nx.ease : gsap.parseEase(nx.ease) } : null; } }
      const s = at(t);
      for (const p of pushes) if (t > p.a) {
        const u = Math.min(1, (t - p.a) / (p.b - p.a));
        let k = p.dz * (0.5 - 0.5 * Math.cos(Math.PI * u));
        if (p.rel && t > p.rel.t) k *= 1 - p.rel.e(Math.min(1, (t - p.rel.t) / p.rel.dur));
        s.z += k;
      }
      return s; };
    const mbg = svg.querySelector("#cv-mbg");
    // a hard cut (C.cam x.cut, trans.js) landing within the next frame: the frame before it is measured against itself,
    // so the jump between two stations is not read as speed (pages before 2026-10-22 have none: unchanged)
    const cutNext = (t) => keys.some((k) => k.cut && k.t > t - 1e-6 && k.t < t + 1 / 30 + 1e-6);
    K.onFrame((t) => {
      const s = state(t), s2 = keys.length && cutNext(t) ? s : state(t + 1 / 30);
      Object.keys(P).forEach((n) => {
        const p = P[n], z = 1 + (s.z - 1) * p, cx = c0.x + (s.x - c0.x) * p, cy = c0.y + (s.y - c0.y) * p;
        layers[n].style.transform = `translate(${WD / 2}px,${HT / 2}px) scale(${z.toFixed(5)}) translate(${(-cx).toFixed(2)}px,${(-cy).toFixed(2)}px)`;
      });
      // motion blur from the camera's speed (screen px per frame), along the move; a zoom blurs a little both ways
      const vx = Math.abs(s2.x - s.x) * s.z, vy = Math.abs(s2.y - s.y) * s.z, vz = Math.abs(s2.z - s.z) * 900;
      // a transition's zoom about a point (ZM): the view scales about it, and its rate blurs like the camera's zoom
      let zb = 0;
      if (ZM.length) {
        const zz = zoomAt(t), z2 = zoomAt(t + 1 / 30), k = zz ? zz.k : 1;
        view.style.transformOrigin = "0 0";                             // the matrix is about the page's origin
        view.style.transform = zz ? `matrix(${k.toFixed(5)},0,0,${k.toFixed(5)},${((1 - k) * zz.px).toFixed(2)},${((1 - k) * zz.py).toFixed(2)})` : "none";
        // (capped at 10 px: at the camera's 22 the element it dives into dissolved before the cut; the fixture's stills)
        if (zz) zb = Math.min(10, (Math.abs((z2 ? z2.k : 1) - k) / k) * 700 * 0.3);
      }
      const lf = ZM.length ? landF(t) : 1;                              // a landing is sharp from its third frame
      const bx = Math.min(22, vx * 0.45 + vz * 0.3 + zb) * lf, by = Math.min(22, vy * 0.45 + vz * 0.3 + zb) * lf;
      if (bx + by > 0.6) { mbg.setAttribute("stdDeviation", `${bx.toFixed(2)} ${by.toFixed(2)}`); view.style.filter = "url(#cv-mb)"; }
      else view.style.filter = "none";
    });
    // a slow push while holding (never a still slide): dz over [a, b] on top of the keyed camera
    const hold = (a, b, dz = 0.04) => { pushes.push({ a, b: Math.max(a + 0.3, b), dz }); at = null; };
    // the camera's scene changes for window.__trans (kit/hf/trans.js; precheck's transition budget), read when the page
    // asks: a jump within a frame is a cut, a pan of a quarter frame or more a whip (0.7 s or less) or a glide, a zoom
    // of 1.8x or more a zoom; pushes, pulls and small reframes are moves inside a scene. A cut that lands within 0.1 s
    // of the end of a move is that move (a push into a card and the hard cut on its peak are one zoom-through).
    const camTrans = () => {
      const out = [];
      // (a move made under a takeover's plate is no transition: nobody sees it. The plate covers from a on a cut or a zoom,
      // from the end of the morph or the fade otherwise, and from a to b + its out when a full-bleed shape hands over to
      // it (coverFrom / coverTo, trans.js: the same window the view is hidden in); a template's move "at a + 0.01" lands
      // on a's frame once C.cam quantizes it, and read as a cut beside the takeover's own zoom. T.cardToGraphic (primary)
      // has no plate)
      const under = (k) => TK.some((x) => x.on != null && !x.primary && k.t >= (x.coverFrom ? x.coverFrom() : Math.max(x.off != null ? x.off : x.a, x.a + (x.fadeIn || 0))) - 1e-3 &&
        k.t + k.dur <= (x.coverTo ? x.coverTo() : x.on) + 1e-6);
      keys.filter((k) => !k.nolog && !under(k)).sort((p, q) => p.t - q.t).forEach((k) => {
        const a = state(k.t - 1e-4), b = state(k.t + k.dur), pan = Math.hypot(b.x - a.x, b.y - a.y) * Math.max(a.z, b.z), zr = Math.max(b.z / a.z, a.z / b.z);
        const kind = k.dur <= 0.05 ? (pan >= 0.25 * WD || zr >= 1.3 ? "cut" : null) : pan >= 0.25 * WD ? (k.dur <= 0.7 ? "whip" : "glide") : zr >= 1.8 ? "zoom" : null;
        if (!kind) return;
        const last = out[out.length - 1];
        if (last && kind === "cut" && k.t - last.end <= 0.1) { last.end = k.t + k.dur; return; }
        out.push({ t: +k.t.toFixed(3), kind, why: `C.cam ${kind} (${k.dur.toFixed(2)} s)`, end: k.t + k.dur });
      });
      return out.map(({ t, kind, why }) => ({ t, kind, why }));
    };
    if (HF.trans && HF.trans.source && o.trans !== false) HF.trans.source(camTrans);

    // ---------------------------------------------------------------- pieces
    const show = (e, a, b) => K.show(e, a, b);
    const land3d = (e, t, x = {}) => {                                   // a 3D landing: from depth and a turn, settling
      const ry = x.ry || 0, rx = x.rx || 0;
      e.style.visibility = "hidden";
      tl.set(e, { visibility: "visible" }, Q(t));
      tl.fromTo(e, { opacity: 0, rotateY: ry + (x.fromRy != null ? x.fromRy : -32), rotateX: rx + (x.fromRx || 8), z: x.fromZ != null ? x.fromZ : -420, y: x.fromY || 40, filter: "blur(10px)" },
        { opacity: 1, rotateY: ry, rotateX: rx, z: 0, y: 0, filter: "blur(0px)", duration: x.dur || 0.9, ease: HF.E.in, immediateRender: false }, Q(t));
      const dr = driftOf(x, ST);                                         // whitespace: 0, it lands once and holds still
      if (dr) tl.to(e, { rotateY: ry + dr, duration: x.hold || 6, ease: "sine.inOut", immediateRender: false }, Q(t + (x.dur || 0.9)));
      if (x.sfx !== false) K.sfx(x.sfx || "pop", t + 0.12, x.db != null ? x.db : -24);
    };
    const window3d = (L, x, y, w, h, wo = {}) => {
      const d = el(L, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;transform:rotateY(${wo.ry || 0}deg) rotateX(${wo.rx || 0}deg)`, "", "cv-win");
      const dots = ST.win.dots;                                          // traffic lights: colour on canvas_studio, one grey on whitespace
      const bar = el(d, "", `<i style="background:${dots[0]}"></i><i style="background:${dots[1]}"></i><i style="background:${dots[2]}"></i><div class="cv-url">${HF.esc(wo.url || "")}</div>`, "cv-bar");
      bar.dataset.decor = "1";
      const body = el(d, `left:0;top:54px;width:${w}px;height:${h - 54}px;overflow:hidden;background:${ST.win.bg} url(${wo.img}) ${wo.pos || "center top"}/${wo.fit || "cover"} no-repeat`);
      d.body = body;
      return d;
    };
    const card = (L, x, y, w, h, t, co = {}) => {
      const d = el(L, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;transform:rotateY(${co.ry || 0}deg) rotateX(${co.rx || 0}deg)`, co.html || "", "cv-card");
      if (t != null) land3d(d, t, co);
      return d;
    };
    // a highlighter sweep behind text (a box in the layer's px): the accent gradient, multiplied over the page (on
    // whitespace a solid tint marker at full strength: multiply keeps the ink under it black)
    const highlight = (L, b, t, x = {}) => {
      const d = el(L, `left:${b[0]}px;top:${b[1]}px;width:${b[2]}px;height:${b[3]}px;background:${HLBG || GRAD};opacity:${x.op || ST.hl.op};mix-blend-mode:${ST.hl.blend};border-radius:6px;transform-origin:0 50%`);
      d.dataset.decor = "1";
      tl.fromTo(d, { scaleX: 0 }, { scaleX: 1, duration: x.dur || 0.5, ease: HF.E.in, immediateRender: true }, Q(t));
      if (x.sfx !== false) K.sfx("ui/ui__select-click__mixkit-1109", t, -26);
      return d;
    };
    // a glowing beam through points: the gradient stroke draws on, a soft glow under it, a bright head while it moves.
    // On a stage with beam.line (whitespace) it is a plain ink line with no glow (x.glow is ignored), no wider than
    // beam.wMax whatever w a template asks for, and the head is a solid accent node in a white ring.
    let uid = 0;                                                         // svg ids: never a decimal time (an invalid selector)
    const beam = (L, pts, t, x = {}) => {
      const id = "b" + (++uid), SB = ST.beam, bw = Math.min(x.w || SB.w, SB.wMax || Infinity), stroke = SB.line || `url(#${id}g)`;
      const s = document.createElementNS(NS, "svg"); s.setAttribute("width", CW); s.setAttribute("height", CH); s.style.cssText = "position:absolute;left:0;top:0;overflow:visible;pointer-events:none";
      s.dataset.decor = "1";
      const A = pts[0], B = pts[pts.length - 1], kc = (B[0] - A[0]) * (x.curve === true ? 0.5 : x.curve || 0);
      const d = x.curve ? `M${A[0]} ${A[1]} C${A[0] + kc} ${A[1]} ${B[0] - kc} ${B[1]} ${B[0]} ${B[1]}` : "M" + pts.map((p) => p.join(" ")).join(" L");
      const dotR = SB.dotR || bw * 1.1, dotW = SB.dotW || bw * 0.55;
      s.innerHTML = `<defs><linearGradient id="${id}g" gradientUnits="userSpaceOnUse" x1="${pts[0][0]}" y1="0" x2="${pts[pts.length - 1][0]}" y2="0"><stop offset="0" stop-color="${G.a}"/><stop offset=".7" stop-color="${G.b}"/><stop offset="1" stop-color="${G.c}"/></linearGradient>
        <filter id="${id}f" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="${x.glow || 14}"/></filter></defs>
        ${SB.glow ? `<path d="${d}" fill="none" stroke="${stroke}" stroke-width="${bw * 2.4}" stroke-linecap="round" stroke-linejoin="round" filter="url(#${id}f)" opacity="${SB.glow}"/>` : ""}
        <path d="${d}" fill="none" stroke="${stroke}" stroke-width="${bw}" stroke-linecap="round" stroke-linejoin="round"/>
        ${x.dot ? `<circle r="${dotR}" fill="${HEAD}" stroke="${SB.ring || G.b}" stroke-width="${dotW}" opacity="0"/>` : ""}`;
      L.append(s);
      const paths = [...s.querySelectorAll("path")], main = paths[paths.length - 1], len = main.getTotalLength(), dur = x.dur || 0.8;
      const ef = typeof (x.ease || HF.E.move) === "function" ? x.ease || HF.E.move : gsap.parseEase(x.ease);
      paths.forEach((p) => { p.style.strokeDasharray = `${len} ${len}`; p.style.strokeDashoffset = len; tl.to(p, { strokeDashoffset: 0, duration: dur, ease: ef, immediateRender: false }, Q(t)); });
      if (x.dot) {                                                       // a bright head that travels with the draw and stays as a node
        const dot = s.querySelector("circle");
        K.onFrame((tt) => { const u = Math.max(0, Math.min(1, (tt - t) / dur)), q = main.getPointAtLength(len * ef(u));
          dot.setAttribute("cx", q.x.toFixed(1)); dot.setAttribute("cy", q.y.toFixed(1)); dot.setAttribute("opacity", tt >= t ? 1 : 0); });
      }
      if (x.sfx !== false) K.sfx(x.sfxName || "whoosh/whoosh__technology-transition-slide__mixkit-3120", t + (x.dur || 0.8) * 0.4, -22);
      return s;
    };
    const big = (L, text, x, y, t, bo = {}) => {
      const d = el(L, `left:${x}px;top:${y}px;font-size:${bo.size || 300}px;${bo.color ? "color:" + bo.color + ";" : ""}${bo.align === "center" ? "transform:translateX(-50%);" : ""}`, HF.esc(text), "cv-big");
      if (t != null) {
        d.style.visibility = "hidden"; tl.set(d, { visibility: "visible" }, Q(t));
        tl.fromTo(d, { opacity: 0, y: 60, scale: 1.06, filter: "blur(14px)" }, { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", duration: bo.dur || 0.7, ease: HF.E.emph, immediateRender: false }, Q(t));
      }
      return d;
    };
    // ---------------------------------------------------------------- the speaker: on the stage, or in a glowing card
    // shots [{ t, mode, x, y, s, w, h, dur }]: "stage" = his cut-out stands at (x, y = his face) at scale s, on the
    // studio; "card" = the same live cut-out inside a rounded card (w x h, centred on x, y) with a soft gradient behind
    // him and a glow on the edge (Ali Abdaal's tri-fold / speaker card). Changes animate (0.7 s, ease-out expo) unless
    // { cut: true }. fo.at: his face in the take px; fo.src: the take's size. fo.plate: the id of a <video> of the whole
    // graded frame (kit/look/cutout.py --plate): the card shows his real room from it, always covering the card (a
    // cut-out on a gradient inside a card reads as a sticker, and a short frame left a strip under him; the critic)
    // "frame" (2026-10-22, v11: the seated frame, never a cut-out): his take full bleed ({ mode: "frame", full: true }) or
    // a large card (w x h, centred on x, y, default the frame's centre; radius 28; default size 87.5 % of the page width,
    // 16:9 on a landscape page (1680 x 945 at 1920) and 4:5 on a portrait one (945 x 1181 at 1080)), its crop kept inside
    // the take's clean rect (s.clean or fo.clean: [x0, y0, x1, y1] in the track's px, the plain wall; or { <clip>: rect }
    // per take: the piece playing at t, so a cut into another take re-crops on the cut, where the lens reframes anyway)
    // so no move shows the clutter beside it. fx / fy: where his face (at) sits in the shape (0.5 / 0.42); zoom: over
    // the clean rect's cover. Between full bleed and the card: the lift (0.55 s in-out: the card shrinks while its
    // shadow grows from none, whitespace's e3).
    // fo.lens: the camera on him inside every shape (HF.motion.lens: pushes, pull-outs, arcs, settles, punches on
    // stressed words, the jump reframe; eye-anchored, clamped to cover and to the clean rect, capped by the track's
    // zoom budget). Default: on for the page's face track (D.lens, kit/film's build: on unless film.py sets LENS = False),
    // off for every other speaker (a screen recording); false = off; { calm, budget: "sharp" | "soft" | x, track, stress,
    // plan, faces, faces_px } = on with those. Its eyes come from D.lens.faces (kit/film's build: the face track per output
    // frame in the TRACK's px, faces_px its size; scaled to fo.src here), never from D.faces (page px on a Reel: review
    // 2026-10-22). With the lens off the page draws exactly what it drew before 2026-10-22.
    // fo.ride: his shape rides the canvas camera (C.hold pushes, slow zooms) and stays pinned during whips and pans.
    // fo.primary: the speaker window.__speaker reports; default the page's face track (the speaker whose id is
    // D.lens.track), else the last speaker() call (window.__faceRect stays the last call's, as before).
    let primary = -1, primaryMe = null;
    const MO = HF.motion;
    const speaker = (id, shots, fo = {}) => {
      const v = document.getElementById(id);
      if (!v) throw new Error("HF.canvas.speaker: no <video id=" + id + ">");
      const SRC = fo.src || [WD, HT], F = fo.at || [SRC[0] / 2, SRC[1] * 0.45];
      const pv = fo.plate ? document.getElementById(fo.plate) : null;
      if (fo.plate && !pv) throw new Error("HF.canvas.speaker: no <video id=" + fo.plate + ">");
      const box = el(ROOT, `left:0;top:0;width:10px;height:10px;z-index:4;overflow:hidden;transform-origin:0 0`);
      const bgc = el(box, `left:0;top:0;width:100%;height:100%;background:${ST.fill};opacity:0`);
      bgc.dataset.decor = "1";
      if (pv) box.append(pv);
      box.append(v);
      [v, pv].forEach((x) => x && Object.assign(x.style, { position: "absolute", left: "0px", top: "0px", width: SRC[0] + "px", height: SRC[1] + "px", transformOrigin: "0 0" }));
      // fo.back: a pastel block offset behind his card ([dx, dy, colour]): colour and depth that belong to the card. A
      // stage without back blocks (whitespace: depth from the shadow alone) ignores it, so a template can keep asking
      const bk = fo.back && ST.back ? el(ROOT, `left:0;top:0;width:10px;height:10px;z-index:4;opacity:0;background:${PAPER.pastel[fo.back[2]] || fo.back[2]}`) : null;
      if (bk) { bk.dataset.decor = "1"; ROOT.insertBefore(bk, box); }
      // the ring: canvas_studio's glow ring, whitespace's e3 shadow (it sits over the box and draws only outside it)
      const ring = el(ROOT, `left:0;top:0;width:10px;height:10px;z-index:4;pointer-events:none;border-radius:36px;opacity:0;box-shadow:${ST.ring || "none"}`);
      ring.dataset.decor = "1";
      let coverEl = null;                                                 // the plate over his card while it morphs (into / from)
      const DD = MO.data() || {}, DL = DD.lens || null, pcs = K.pieces || [];
      // the primary speaker (the one window.__speaker reports): fo.primary (2), else the page's face track (1: D.lens.track;
      // a screen recording added after his own speaker no longer takes the contract, review 2026-10-22), else the last
      // call (0). Claimed here, before his shots are merged: only the primary's card morphs into a takeover's card and
      // grows back out of it (every other speaker fades off and back), and a speaker that loses the claim is merged again
      const lvl = fo.primary ? 2 : DL && DL.track === id ? 1 : 0, me = {}, claim = lvl >= primary;
      if (claim) { primary = lvl; primaryMe = me; if (TK.length) SPK.forEach((f) => f()); }
      // the takeovers (C.takeover, T.cardToGraphic; kit/hf/trans.js) write his off shots and returns into the template's
      // (takeoverShots below; replan() redoes it when one is added after this call). None: the template's shots as given.
      // What the merge drops (a template shot inside a takeover) is said once in the console, in window.__lens[id].log and
      // in window.__takeovers[i].dropped (review 2026-10-22: a shot dropped by a mis-timed return left no trace)
      let tkLog = [];
      const said = new Set();
      const merge = () => {
        const r = takeoverShots(shots, TK, { morph: primaryMe === me });
        tkLog = r.log;
        r.log.forEach((l) => { if (!said.has(l)) { said.add(l); console.warn(`HF.canvas.speaker ${id}: ${l}`); } });
        TK.forEach((k, j) => { if (k.rec) k.rec.dropped = (k.rec.dropped || []).filter((d) => d.speaker !== id).concat(r.dropped.filter((d) => d.tk === j).map((d) => ({ speaker: id, t: d.t }))); });
        return r.shots;
      };
      let ss = merge();
      const clipAt = (t) => { let p = null; for (const q of pcs) { if (q.out_a <= t + 1e-4) p = q; else break; } return p ? p.clip : null; };
      const FULLR = [0, 0, SRC[0], SRC[1]];
      const rectOf = (s, t) => { const c = s.clean || fo.clean; return cleanRect(c, c && !Array.isArray(c) ? clipAt(t) : null, FULLR); };
      // his footage seated in a shape bw x bh at scale vs (one scale: aspect-locked): his face point P at the centre across
      // and 42 % down, but the top of his head (P's y - 0.675 head, as __faceRect draws it) at least 10 % of the shape's
      // height below its top, as far as cover allows (fix round 2026-10-23: a card morphing into a tile of another
      // aspect cropped his head) -> { vx, vy }
      const seat = (bw, bh, vs, P) => { const cl = (n, lo) => Math.min(0, Math.max(lo, n)), hd = (fo.head || 300) * 0.675;
        return { vx: cl(bw / 2 - P[0] * vs, bw - SRC[0] * vs), vy: cl(Math.max(bh * 0.42 - P[1] * vs, 0.1 * bh - (P[1] - hd) * vs), bh - SRC[1] * vs) }; };
      const geo = (s, t) => {                                           // -> { bx, by, bw, bh, r, card, vs, vx, vy, op, nof }
        if (s.into) {                                                   // his card in a graphic's frame (trans.js): its page rect
          const R = HF.trans.rectAt(s.into, s.intoAt != null ? s.intoAt : t != null ? t : s.t), bw = Math.max(2, R.w), bh = Math.max(2, R.h);
          const vs = Math.max(bw / SRC[0], bh / SRC[1]), P = s.at || F;
          return Object.assign({ bx: R.x, by: R.y, bw, bh, r: s.r != null ? s.r : R.r, card: 1, vs, op: s.off ? 0 : 1, nof: 0 }, seat(bw, bh, vs, P));
        }
        if (s.mode === "frame") {                                       // the seated frame: full bleed or the large card
          const full = !!s.full, { bx, by, bw, bh } = frameBox(s, WD, HT);
          const R = rectOf(s, t != null ? t : s.t), vs = Math.max(bw / (R[2] - R[0]), bh / (R[3] - R[1])) * (s.zoom || 1), P = s.at || F;
          const vx = Math.min(-R[0] * vs, Math.max(bw - R[2] * vs, bw * (s.fx != null ? s.fx : 0.5) - P[0] * vs));
          const vy = Math.min(-R[1] * vs, Math.max(bh - R[3] * vs, bh * (s.fy != null ? s.fy : 0.42) - P[1] * vs));
          return { bx, by, bw, bh, r: full ? 0 : s.r != null ? s.r : 28, card: full ? 0 : 1, vs, vx, vy, op: s.off ? 0 : 1, nof: 1 };
        }
        if (s.mode === "card") {
          const bw = s.w || 520, bh = s.h || 620, bx = s.x - bw / 2, by = s.y - bh / 2;
          const vs = Math.max(s.s || Math.max(bw / (SRC[0] * 0.45), bh / (SRC[1] * 0.95)), bw / SRC[0], bh / SRC[1]);   // always covers
          const cl = (n, lo) => Math.min(0, Math.max(lo, n));
          const P = s.at || F;                                          // a shot's own focus (a cam bubble, a post's video)
          return { bx, by, bw, bh, r: s.r != null ? s.r : 36, card: 1, vs, vx: cl(bw / 2 - P[0] * vs, bw - SRC[0] * vs), vy: cl(bh * (s.fy || 0.42) - P[1] * vs, bh - SRC[1] * vs), op: s.off ? 0 : 1, nof: 0 };
        }
        const vs = s.s || 1;                                              // stage: the box is the whole frame
        return { bx: 0, by: 0, bw: WD, bh: HT, r: 0, card: 0, vs, vx: s.x - F[0] * vs, vy: (s.foot != null ? s.foot : HT) - SRC[1] * vs, op: s.off ? 0 : 1, nof: 0 };
      };
      // does his shape cover the whole frame at t (the shot in force there, at its own size: a full-bleed seated frame, or
      // a card the size of the page)? A takeover's soft entrance and exit ask (C._covers, kit/hf/trans.js): the canvas
      // under a covering shape was never on screen, so the takeover's plate is opaque from a and only his shape moves
      // (review 2026-10-22: station copy his full frame had hidden ghosted over his face). The stage (a cut-out on the
      // seamless, transparent around him) never covers
      const covering = (t) => {
        let k = 0; while (k + 1 < ss.length && ss[k + 1].t <= t + 1e-6) k++;
        const s = ss[k];
        if (!s || s.off || !(s.into || s.mode === "frame" || s.mode === "card")) return false;
        const g = geo(s, t);
        return g.bx <= 0.5 && g.by <= 0.5 && g.bx + g.bw >= WD - 0.5 && g.by + g.bh >= HT - 0.5;
      };
      const lerp = (a, b, u) => { const r = {}; for (const k in a) r[k] = a[k] + (b[k] - a[k]) * u; return r; };
      const lift = (s, p) => s.mode === "frame" || !!(p && p.mode === "frame");
      const durOf = (k) => (!k || ss[k].cut ? 0 : ss[k].dur || (lift(ss[k], ss[k - 1]) ? 0.55 : 0.7));
      // the shape at t: { g, k (the shot), u (the eased progress while it moves in from shot k - 1, else null) }
      const pose = (t) => {
        let k = 0; while (k + 1 < ss.length && ss[k + 1].t <= t + 1e-6) k++;
        const s = ss[k], g = geo(s, t);
        if (!k || s.cut) return { g, k, u: null };
        const lf = lift(s, ss[k - 1]), d = s.dur || (lf ? 0.55 : 0.7), u = Math.min(1, Math.max(0, (t - s.t) / d));
        const ef = s.ease ? (typeof s.ease === "function" ? s.ease : gsap.parseEase(s.ease)) : lf ? HF.E.move : HF.E.in;
        if (u >= 1) return { g, k, u: null };
        const e = ef(u);
        const gA = geo(ss[k - 1], t), gl = lerp(gA, g, e);
        if (s.from) gl.op = 1;                                          // growing back out of a graphic: the cover hides him first
        if (s.into || s.from) {
          // a morph into / out of a graphic changes the shape's aspect: the footage keeps its zoom over cover between the
          // two shapes' (a plain blend read 1.26x over cover mid-morph on the fixture), a cover crop, his face 42 % down
          // (one scale: the footage keeps its aspect, and seat() keeps 10 % over his head in every in-between shape)
          const cov = (q) => Math.max(q.bw / SRC[0], q.bh / SRC[1]), zA = gA.vs / cov(gA), zB = g.vs / cov(g), P = s.at || F;
          // (and never so close that his head, 1.25 head sizes tall, takes more than 75 % of the in-between shape's height)
          const vs = Math.max(cov(gl), Math.min(cov(gl) * (zA + (zB - zA) * e), (0.75 * gl.bh) / (1.25 * (fo.head || 300))));
          Object.assign(gl, { vs }, seat(gl.bw, gl.bh, vs, P));
        }
        return { g: gl, k, u: e };
      };
      const now = (t) => pose(t).g;
      // ---- ride (fo.ride): the shape follows the canvas camera from the camera it landed under; a whip (<= 0.7 s) or a
      // pan of more than a quarter frame takes it back to its screen place over the move, and it re-anchors there
      const RIDE = !!fo.ride;
      let RW = null, RWn = -1;
      const rideWins = () => {
        if (RW && RWn === keys.length + 1e4 * ZM.length) return RW;
        RWn = keys.length + 1e4 * ZM.length;
        RW = keys.filter((k) => { if (k.dur <= 0.7) return true; const a = state(k.t), b = state(k.t + k.dur); return Math.hypot(b.x - a.x, b.y - a.y) * b.z > 0.25 * WD; })
          .map((k) => [k.t, k.t + k.dur]).concat(ZM.map((z) => [z.t0, z.t1])).sort((p, q) => p[0] - q[0]);   // a transition's zoom is a whip too
        return RW;
      };
      const rideT = (ref0, t) => {                                       // screen p -> a * p + (bx, by)
        let ref = ref0, r = 1, tc = t;
        // inside a whip the ride eases out from where the camera was when the whip began (the whip's own pan never drags
        // him: measured on the fixture, following it swung his circle 100 px mid-whip)
        for (const [a, b] of rideWins()) { if (b <= t + 1e-6) ref = Math.max(ref, b); else if (a <= t) { r = 1 - HF.E.move(Math.min(1, (t - a) / (b - a))); tc = a; } }
        const c = state(tc), c0 = state(Math.min(ref, tc)), zr = c.z / c0.z;
        return { a: 1 + r * (zr - 1), x: r * ((c0.x - c.x) * c.z + (WD / 2) * (1 - zr)), y: r * ((c0.y - c.y) * c.z + (HT / 2) * (1 - zr)) };
      };
      const ride = (g, ps, t) => {
        let T = rideT(ss[ps.k].t + durOf(ps.k), t);
        if (ps.u != null && ps.k) { const T0 = rideT(ss[ps.k - 1].t + durOf(ps.k - 1), t), m = (p, q) => p + (q - p) * ps.u; T = { a: m(T0.a, T.a), x: m(T0.x, T.x), y: m(T0.y, T.y) }; }
        return Object.assign({}, g, { bx: T.a * g.bx + T.x, by: T.a * g.by + T.y, bw: T.a * g.bw, bh: T.a * g.bh, r: T.a * g.r, vs: T.a * g.vs, vx: T.a * g.vx, vy: T.a * g.vy });
      };
      // ---- the lens (fo.lens; D.lens)
      const LZ = fo.lens === false ? null : fo.lens || (DL && DL.on && DL.track === id) ? Object.assign({}, DL || {}, typeof fo.lens === "object" ? fo.lens : {}) : null;
      const TN = LZ && LZ.track && LZ.track !== (DL && DL.track) ? LZ.track : id;            // its work/tracks.json entry
      const TI = DD.tracks && DD.tracks[TN] && typeof DD.tracks[TN] === "object" ? DD.tracks[TN] : null;
      const HEAD = fo.head || 300;
      const circ = (g) => g.r >= Math.min(g.bw, g.bh) / 2 - 1 && Math.abs(g.bw - g.bh) < 1;
      // per shot: the eyes the lens anchors on (the face track's median over the hold, else at / F), the clean rect (a
      // frame shot's; the take at t while it plays, rectAt) and the zoom budgets (the shape's own, MO.lensBudget: sharp
      // kmax / zoom, and the soft allowance ksoft / zsoft that only a jump reframe the sharp one can't pay spends)
      const FX = LZ && Array.isArray(LZ.faces) ? LZ.faces : null;        // the face track per output frame, its px
      const FP = FX ? (typeof fo.lens === "object" && fo.lens.faces ? fo.lens.faces_px : LZ.faces_px) || SRC : SRC;
      const fsx = SRC[0] / FP[0], fsy = SRC[1] / FP[1];                  // its px -> this <video>'s px (fo.src)
      const rectAt = (s, t) => (s.mode === "frame" ? rectOf(s, t) : FULLR);
      // the budgets per hold (MO.holdBudget): the tracks.json kind playing in it (D.pieces over the hold: E-M1, the
      // poorest one there, not the track's poorest overall) and full bleed's tier (E-M2: "auto" spends soft_zoom on a
      // full-bleed seated frame or a card the size of the page, MO.LENS.full)
      const infoOf = (s, k) => {
        const t0 = s.t + durOf(k), g = geo(s, t0), t1 = k + 1 < ss.length ? ss[k + 1].t : DD.total || t0 + 600, P = s.at || F;
        const ey0 = MO.eyesOver(FX, t0, t1, (LZ && LZ.fps) || K.fps || 30, null);
        const ey = ey0 ? { eye: [ey0.eye[0] * fsx, ey0.eye[1] * fsy], size: ey0.size * fsx } : MO.eyesOver(null, t0, t1, 30, [P[0], P[1], HEAD]);
        const full = !s.into && (s.mode === "frame" || s.mode === "card") && g.bx <= 0.5 && g.by <= 0.5 && g.bx + g.bw >= WD - 0.5 && g.by + g.bh >= HT - 0.5;
        const cover = Math.max(g.bw / SRC[0], g.bh / SRC[1]);
        const b = MO.holdBudget(TI, { pieces: DD.pieces || pcs, t0, t1, Hc: SRC[1] * cover, cover, vs: g.vs, budget: LZ ? LZ.budget : null, full, lens: !!LZ });
        return { g, t0, t1, eye: ey.eye, size: ey.size || HEAD, rect: rectAt(s, t0), kmax: b.kmax, zoom: b.zoom, ksoft: b.ksoft, zsoft: b.zsoft, cover, kind: b.kind, mode: b.mode };
      };
      let info = ss.map(infoOf);
      // a frame shot whose clean rect is too small for the shape's aspect: its base framing alone passes the zoom budget
      // (the lens then holds still and window.__speaker reports zoom over max_zoom for the whole shot). Said once here and
      // in window.__lens[id].log, naming the shot (review 2026-10-22: [2400, 600, 3840, 2160] full bleed read x2.67)
      const warnsOf = () => {
        const out = [];
        ss.forEach((s, k) => {
          const I = info[k], z = I.g.vs / I.cover;
          if (s.mode !== "frame" || s.off || z <= I.zoom + 1e-3) return;          // I.zoom: the budget in force (sharp, soft or x)
          out.push(`${s.t.toFixed(2)} frame shot ${k}: its clean rect frames x${z.toFixed(2)} over cover, past the zoom budget x${I.zoom.toFixed(2)}${I.zsoft > I.zoom + 1e-6 ? ` (soft x${I.zsoft.toFixed(2)})` : ""}: loosen the rect or use a card`);
        });
        return out;
      };
      let warns = warnsOf();
      warns.forEach((w) => console.warn(`HF.canvas.speaker ${id}: ${w}`));
      // a template's own jump-cut shot (the pre-v11 inline "every other join x1.12" loop: { ...shot, t: join, s, cut:
      // true }) keeps the shape and only reframes: one hold with the shot before it, so the lens carries its state across
      // the join instead of starting again at x1 (review 2026-10-22: rebuilt with the lens, oss-editor's 4.30 s step
      // read x1.052, not x1.12), and the lens leaves that join to the template's step (no second reframe on top)
      const sameShape = (k) => {
        if (!k || !ss[k].cut || ss[k].off || ss[k - 1].off || (ss[k].mode || "") !== (ss[k - 1].mode || "")) return false;
        const a = info[k].g, b = info[k - 1].g;
        return ["bx", "by", "bw", "bh", "r"].every((q) => Math.abs(a[q] - b[q]) < 0.5);
      };
      let LP = null, LPn = -1;
      const lensPlan = () => {
        if (LP && LPn === keys.length + 1e4 * ZM.length) return LP;
        LPn = keys.length + 1e4 * ZM.length;
        const holds = [], own = [];
        ss.forEach((s, k) => {
          const I = info[k], last = holds[holds.length - 1];
          if (s.off || I.t1 - I.t0 <= 0.05) return;
          if (last && last.lastShot === k - 1 && sameShape(k)) {          // the template's jump shot: the same hold goes on
            Object.assign(last, { t1: I.t1, kmax: Math.min(last.kmax, I.kmax), ksoft: Math.min(last.ksoft, I.ksoft), lastShot: k });
            own.push(s.t);
            return;
          }
          holds.push({ t0: I.t0, t1: I.t1, w: I.g.bw, h: I.g.bh, kmax: I.kmax, ksoft: I.ksoft, shot: k, lastShot: k, enter: !k ? "start" : s.cut ? "cut" : ss[k - 1].off ? "back" : "move",
            open: I.g.vx + I.eye[0] * I.g.vs < I.g.bw / 2 ? 1 : -1 });
        });
        const cuts = (HF.box ? HF.box.cutsOf(pcs).map((c) => c.t) : []).filter((c) => !own.some((x) => Math.abs(x - c) < 0.05));
        LP = MO.lens({ holds, words: K.words_ || [], stress: LZ.stress || [], plan: LZ.plan || [], cuts,
          // (a zoom's landing from its peak, k0 > k1, is tagged "land": the lens lands in on its cut and pulls out after it)
          whips: keys.filter((x) => x.dur <= 0.7).map((x) => [x.t, x.t + x.dur]).concat(ZM.map((z) => [z.t0, z.t1, z.k0 > z.k1 ? "land" : null])), fps: K.fps || 30, calm: LZ.calm, rules: LZ.rules });
        own.forEach((x) => LP.log.push(`${x.toFixed(2)} join: the template's own cut shot reframes it (one hold with the shot before)`));
        LP.log.push(...warns, ...tkLog);
        LP.log.sort((a, b) => parseFloat(a) - parseFloat(b));
        (window.__lens = window.__lens || {})[id] = LP;
        return LP;
      };
      // the lens state, the shot's info (blended while the shape moves) and the footage's transform at t
      const shotAt = (t) => {
        const ps = pose(t), g = RIDE ? ride(ps.g, ps, t) : ps.g;
        let I = info[ps.k];
        if (ps.u != null && ps.k) { const A = info[ps.k - 1], m = (p, q) => p + (q - p) * ps.u;
          I = Object.assign({}, I, { eye: [m(A.eye[0], I.eye[0]), m(A.eye[1], I.eye[1])], size: m(A.size, I.size), kmax: m(A.kmax, I.kmax), zoom: m(A.zoom, I.zoom),
            ksoft: m(A.ksoft, I.ksoft), zsoft: m(A.zsoft, I.zsoft) }); }
        if (!LZ) return { ps, g, I, st: null, fr: null, M: [g.vs, 0, 0, g.vs, g.vx, g.vy], s: g.vs };
        // the clean rect: the shot's (a frame shot's for the take playing at t); while the shape moves in, blended from the
        // last shot's by the move's progress, so the new rect never clamps the old framing in one frame (review
        // 2026-10-22: circle -> frame with a clean rect jumped his face 113 px on the move's first frame)
        let rect = rectAt(ss[ps.k], t);
        if (ps.u != null && ps.k) { const A = rectAt(ss[ps.k - 1], t); rect = rect.map((x, i) => A[i] + (x - A[i]) * ps.u); }
        const st = lensPlan().at(t, ps.u);
        const fr = MO.lensFrame({ bw: g.bw, bh: g.bh, vs: g.vs, vx: g.vx, vy: g.vy, circle: circ(g) }, st, { src: SRC, eye: I.eye, rect, smax: g.vs * (st.soft ? I.ksoft : I.kmax) });
        return { ps, g, I, st, fr, M: fr.m, s: fr.s };
      };
      K.onFrame((t) => {
        const S = shotAt(t), g = S.g;
        Object.assign(box.style, { left: g.bx.toFixed(1) + "px", top: g.by.toFixed(1) + "px", width: g.bw.toFixed(1) + "px", height: g.bh.toFixed(1) + "px",
          borderRadius: g.r.toFixed(1) + "px", opacity: g.op.toFixed(3) });
        const m = S.fr ? `matrix(${S.M.slice(0, 4).map((x) => x.toFixed(5)).join(",")},${S.M[4].toFixed(2)},${S.M[5].toFixed(2)})`
          : `matrix(${g.vs.toFixed(5)},0,0,${g.vs.toFixed(5)},${g.vx.toFixed(2)},${g.vy.toFixed(2)})`;
        v.style.transform = m;
        // on the stage a soft shadow seats him on the seamless; in a card the room plate takes over (a seated frame: never)
        v.style.filter = g.card < 0.99 && !(g.nof > 0.5) ? `drop-shadow(0 ${(40 / g.vs).toFixed(1)}px ${(80 / g.vs).toFixed(1)}px rgba(30,30,60,${(0.18 * (1 - g.card)).toFixed(3)}))` : "none";
        if (pv) { pv.style.transform = m; pv.style.opacity = g.card.toFixed(3); v.style.opacity = (1 - g.card).toFixed(3); }
        else bgc.style.opacity = g.card.toFixed(3);
        if (bk) Object.assign(bk.style, { left: (g.bx + fo.back[0]).toFixed(1) + "px", top: (g.by + fo.back[1]).toFixed(1) + "px", width: g.bw.toFixed(1) + "px",
          height: g.bh.toFixed(1) + "px", borderRadius: g.r.toFixed(1) + "px", opacity: (g.card * g.op).toFixed(3) });
        Object.assign(ring.style, { left: g.bx.toFixed(1) + "px", top: g.by.toFixed(1) + "px", width: g.bw.toFixed(1) + "px", height: g.bh.toFixed(1) + "px",
          borderRadius: g.r.toFixed(1) + "px", opacity: (g.card * g.op).toFixed(3) });
        // the cover (trans.js): a plate in the graphic's colour over the whole shape while his card morphs into it (it
        // rises over the move's last 70 %) or grows back out of it (it clears over the first 60 %): never a transparent
        // edge, and always opaque (bgOf)
        if (coverEl) {
          const s = ss[S.ps.k], u = S.ps.u, co = u == null ? 0 : s.into ? smooth01((u - 0.3) / 0.6) : s.from ? 1 - smooth01(u / 0.6) : 0;
          Object.assign(coverEl.style, { left: g.bx.toFixed(1) + "px", top: g.by.toFixed(1) + "px", width: g.bw.toFixed(1) + "px", height: g.bh.toFixed(1) + "px",
            borderRadius: g.r.toFixed(1) + "px", opacity: (co * g.op).toFixed(3), background: co > 0 ? bgOf(s.into || s.from) : "transparent" });
          // on the plate, the graphic's own contents (its build-time copy, snapOf, fitted at one scale, centred): his face
          // crossfades into what the tile shows and back out of it, never through a blank plate (fix round 2026-10-23:
          // ~6 frames of an empty white tile at the end of the card in and the start of the card out)
          const src = co > 0.002 ? s.into || s.from : null, c = src ? snapOf(src, s.into ? "in" : "out") : null;
          [...coverEl.children].forEach((x) => { if (x !== c) x.remove(); });
          if (c) {
            const w0 = src.offsetWidth || 1, h0 = src.offsetHeight || 1, k = Math.min(g.bw / w0, g.bh / h0);
            c.style.transform = `translate(${((g.bw - w0 * k) / 2).toFixed(2)}px,${((g.bh - h0 * k) / 2).toFixed(2)}px) scale(${k.toFixed(5)})`;
            if (c.parentNode !== coverEl) coverEl.append(c);
          }
        }
        // a transition's zoom about a point (ZM): his shape zooms with the view (a camera move), blurred by its speed
        if (ZM.length) {
          const zz = zoomAt(t), z2 = zoomAt(t + 1 / 30);
          [box, ring, bk, coverEl].forEach((e) => {
            if (!e) return;
            if (!zz) { e.style.transform = "none"; return; }
            const ex = parseFloat(e.style.left) || 0, ey = parseFloat(e.style.top) || 0;
            e.style.transformOrigin = "0 0";
            e.style.transform = `matrix(${zz.k.toFixed(5)},0,0,${zz.k.toFixed(5)},${((1 - zz.k) * (zz.px - ex)).toFixed(2)},${((1 - zz.k) * (zz.py - ey)).toFixed(2)})`;
          });
          const zb = zz ? Math.min(14, (Math.abs((z2 ? z2.k : 1) - zz.k) / zz.k) * 700 * 0.15) * landF(t) : 0;
          box.style.filter = zb > 0.6 ? `blur(${zb.toFixed(2)}px)` : "none";
        }
      });
      ss.forEach((s, i) => { if (i && !s.cut && s.sfx !== false) K.sfx("whoosh/whoosh__air-woosh__mixkit-1489", s.t + 0.15, -24); });
      // his head on the page: the face point (F, or the eyes' face with the lens) through the footage's transform
      const headAt = (S) => {
        const g = S.g, M = S.M, c = S.fr ? [S.I.eye[0], S.I.eye[1] + MO.EYE_K * S.I.size] : F, hw = (S.fr ? S.I.size : HEAD) * S.s / 2;
        return { cx: g.bx + M[0] * c[0] + M[2] * c[1] + M[4], cy: g.by + M[1] * c[0] + M[3] * c[1] + M[5], hw };
      };
      window.__faceRect = (t) => { if (!LZ) { const g = now(t); if (g.op < 0.5) return null; const cx = g.bx + g.vx + F[0] * g.vs, cy = g.by + g.vy + F[1] * g.vs, hw = (fo.head || 300) * g.vs / 2;
          return { left: Math.max(g.bx, cx - hw), right: Math.min(g.bx + g.bw, cx + hw), top: Math.max(g.by, cy - hw * 1.35), bottom: Math.min(g.by + g.bh, cy + hw * 1.15) }; }
        const S = shotAt(t), g = S.g;
        if (g.op < 0.5) return null;
        // his head's centre kept inside the shape, so the box is never inverted (left <= right, top <= bottom) even when the
        // eyes sit off it (review 2026-10-22: wrong-unit faces gave left 472 > right 450)
        const h = headAt(S), hw = h.hw, cx = Math.min(g.bx + g.bw, Math.max(g.bx, h.cx)), cy = Math.min(g.by + g.bh, Math.max(g.by, h.cy));
        return { left: Math.max(g.bx, cx - hw), right: Math.min(g.bx + g.bw, cx + hw), top: Math.max(g.by, cy - hw * 1.35), bottom: Math.min(g.by + g.bh, cy + hw * 1.15) }; };
      // the window.__speaker contract (kit/hf/README "window.__speaker"; kit/qa/speaker.mjs reads it)
      const sample = (t) => {
        const S = shotAt(t), g = S.g, I = S.I;
        const on = g.op >= 0.5 && g.bx < WD && g.by < HT && g.bx + g.bw > 0 && g.by + g.bh > 0;
        const sh = ss[S.ps.u != null && S.ps.u < 0.5 && S.ps.k ? S.ps.k - 1 : S.ps.k], gs = geo(sh);
        const kind = !on ? "off" : sh.mode === "frame" ? (sh.full ? "full" : "frame") : sh.mode === "card" ? (circ(gs) ? "circle" : gs.bw * gs.bh < 0.1 * WD * HT ? "corner" : "card") : "full";
        let face = null;
        if (on) {
          const { cx, cy, hw } = headAt(S), x0 = Math.max(g.bx, cx - hw), x1 = Math.min(g.bx + g.bw, cx + hw), y0 = Math.max(g.by, cy - hw * 1.35), y1 = Math.min(g.by + g.bh, cy + hw * 1.15);
          if (x1 > x0 + 1 && y1 > y0 + 1) face = { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
        }
        // max_zoom: the cap in force (the soft allowance while a soft jump reframe holds: soft true)
        const soft = !!(S.st && S.st.soft) && I.zsoft > I.zoom + 1e-6;
        let rect = on ? { x: g.bx, y: g.by, w: g.bw, h: g.bh } : null;
        // through a transition's zoom (ZM) his shape and face are where the zoom puts them; zoom stays the framing's own
        // (a zoom-through is a camera move through the frame, not a closer framing of him)
        const zz = ZM.length && on ? zoomAt(t) : null;
        if (zz) { const zr = (r) => r && { x: zz.px + zz.k * (r.x - zz.px), y: zz.py + zz.k * (r.y - zz.py), w: r.w * zz.k, h: r.h * zz.k }; rect = zr(rect); face = zr(face); }
        // zoom: over the cover of his shape as planned (S.ps.g), so the page camera's zoom on it (fo.ride: his shape rides a
        // camera push, v11-sample's p7 x1.15) counts: those source px are as magnified as a lens push's (fix round
        // 2026-10-23: it read the lens alone, over the ridden shape's own cover, and the SPEAKER gate missed the push)
        const gp = S.ps.g;
        return { on, kind, rect, face, zoom: +(S.s / Math.max(gp.bw / SRC[0], gp.bh / SRC[1])).toFixed(4),
          lens: S.st ? S.st.move : "", track: TN, max_zoom: TI ? +(soft ? I.zsoft : I.zoom).toFixed(4) : null, soft };
      };
      // the primary speaker (claimed above) publishes the contract
      if (claim) window.__speaker = sample;
      // a takeover added after this call (C.takeover, T.cardToGraphic), or another speaker taking the primary claim: his
      // shots are merged again and the lens re-planned (the whoosh of a template shot it drops was already queued: declare
      // takeovers before C.speaker for exact sound)
      const replan = () => {
        ss = merge(); info = ss.map(infoOf); warns = warnsOf(); LP = null; LPn = -1; RW = null; RWn = -1;
        if (!coverEl && ss.some((s) => s.into || s.from)) { coverEl = el(ROOT, `left:0;top:0;width:10px;height:10px;z-index:4;pointer-events:none;opacity:0;overflow:hidden`); coverEl.dataset.decor = "1"; }
        ss.forEach((s) => { if (s.into) snapOf(s.into, "in"); if (s.from) snapOf(s.from, "out"); });
      };
      // the graphic's contents on the cover: a copy of it taken here, at build time (when the takeover registers), never
      // during a seek (an onFrame reads other elements before or after GSAP renders them, by seek direction: a copy taken
      // per frame was not a pure function of t). "in" (his card morphs into it): as the scene opens, the parts that land
      // later still hidden; "out" (he grows back out of it): as it ends, every part landed. Inert (no video, no ids, nothing
      // the runtime or a mount lookup takes for a clip); fitted per frame at one scale, centred (aspect kept)
      const SNAP = new Map();
      const snapOf = (src, how) => {
        if (!src || src.nodeType !== 1) return null;
        const key = (SNAP.get(src) || SNAP.set(src, {}).get(src));
        if (key[how]) return key[how];
        const c = src.cloneNode(true);
        c.querySelectorAll("video").forEach((e) => e.remove());
        [c, ...c.querySelectorAll("*")].forEach((e) => {
          ["id", "data-composition-id", "data-composition-src", "data-start", "data-duration", "data-track-index", "data-mount"].forEach((n) => e.removeAttribute(n));
          if (e.classList) e.classList.remove("clip", "hf-mount");
          if (how === "out" && e !== c && e.style && e.style.visibility === "hidden") e.style.visibility = "";
        });
        Object.assign(c.style, { position: "absolute", left: "0px", top: "0px", margin: "0", visibility: "visible", clipPath: "none", filter: "none", opacity: "1",
          background: "transparent", boxShadow: "none", transformOrigin: "0 0" });
        c.dataset.decor = "1";
        return (key[how] = c);
      };
      if (ss.some((s) => s.into || s.from)) replan();
      SPK.push(replan); COV.push(covering);
      return { box, now, at: sample, lens: () => (LZ ? lensPlan() : null), shots: () => ss };
    };
    // the takeovers on this canvas (kit/hf/trans.js writes them: { a, off, on, into, from, fromDur, fadeIn, fadeOut,
    // coverFrom, coverTo }), the speakers to re-plan when one is added after them, and each speaker's covering(t)
    const TK = [], SPK = [], COV = [];
    const smooth01 = (u) => { u = Math.max(0, Math.min(1, u)); return u * u * (3 - 2 * u); };
    // the cover's colour: the graphic's own background, made opaque (canvas_studio's cards are rgba(255,255,255,.92): a
    // cover in that let his face through as a ghost on the first frame of "out card", review 2026-10-22; at 92 % white
    // over the warm paper the card reads about #FEFEFE, so opaque white is within 2 levels of what the eye sees there)
    const opaque = (c) => { const m = /^rgba\(\s*([^,]+),\s*([^,]+),\s*([^,]+),/.exec(c || ""); return m ? `rgb(${m[1]}, ${m[2]}, ${m[3]})` : c; };
    const bgOf = (e) => { if (!e) return opaque(ST.card.bg); if (e.__trBg == null) { const c = getComputedStyle(e).backgroundColor;
      e.__trBg = opaque(c && c !== "rgba(0, 0, 0, 0)" && c !== "transparent" ? c : ST.card.bg); } return e.__trBg; };
    // ---------------------------------------------------------------- a line chart: gradient stroke, area, glowing tip
    const chart = (L, x, y, w, h, co = {}) => {
      const pts = co.pts.map(([u, v]) => [x + u * w, y + (1 - v) * h]), a = "c" + (++uid);
      // the reveal: one draw (at, dur) or steps keys [{ t, u, dur, ease }] (u = how much of the width is drawn)
      const ks = co.keys || [{ t: co.at, u: 1, dur: co.dur || 2, ease: co.ease }];
      const prog = HF.keyed(ks.map((k) => ({ t: k.t, dur: k.dur || 1, ease: k.ease || HF.E.move, v: { u: k.u } })), { u: 0 });
      const at0 = ks[0].t, last = ks[ks.length - 1], done = last.t + (last.dur || 1), land = co.land, pop = gsap.parseEase("back.out(2)");
      const s = document.createElementNS(NS, "svg"); s.setAttribute("width", CW); s.setAttribute("height", CH); s.style.cssText = "position:absolute;left:0;top:0;overflow:visible";
      s.dataset.decor = "1";
      const d = "M" + pts.map((p) => p.map((n) => n.toFixed(1)).join(" ")).join(" L");
      const area = d + ` L${(x + w).toFixed(1)} ${y + h} L${x} ${y + h} Z`;
      // the stage's chart tokens: canvas_studio a gradient stroke over a fading area with a glow and a halo; whitespace one
      // accent stroke over a flat tint (areaEnd = area: no fade), no glow, no halo, a hairline grid and a 2 px base
      const SC = ST.chart, aEnd = SC.areaEnd != null ? SC.areaEnd : 0;
      s.innerHTML = `<defs><linearGradient id="cg${a}" gradientUnits="userSpaceOnUse" x1="${x}" y1="0" x2="${x + w}" y2="0"><stop offset="0" stop-color="${G.a}"/><stop offset=".7" stop-color="${G.b}"/><stop offset="1" stop-color="${G.c}"/></linearGradient>
        <linearGradient id="ca${a}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${G.b}" stop-opacity="${SC.area}"/><stop offset="1" stop-color="${G.b}" stop-opacity="${aEnd}"/></linearGradient>
        <clipPath id="cc${a}"><rect x="${x - 20}" y="${y - 40}" width="0" height="${h + 80}"/></clipPath>
        <filter id="cf${a}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="10"/></filter></defs>
        <g stroke="${SC.grid}" stroke-width="2">${[0.25, 0.5, 0.75].map((f) => `<line x1="${x}" x2="${x + w}" y1="${y + h * f}" y2="${y + h * f}" stroke-dasharray="6 10"/>`).join("")}</g>
        <line x1="${x}" x2="${x + w}" y1="${y + h}" y2="${y + h}" stroke="${SC.base}" stroke-width="${SC.baseW || 3}"/>
        <g clip-path="url(#cc${a})"><path d="${area}" fill="url(#ca${a})"/>${SC.glow ? `<path d="${d}" fill="none" stroke="url(#cg${a})" stroke-width="22" stroke-linecap="round" stroke-linejoin="round" filter="url(#cf${a})" opacity="${SC.glow}"/>` : ""}
        <path d="${d}" fill="none" stroke="url(#cg${a})" stroke-width="${SC.w}" stroke-linecap="round" stroke-linejoin="round"/></g>
        <circle r="26" fill="${G.b}" opacity="${SC.halo ? ".25" : "0"}" filter="url(#cf${a})"/><circle r="12" fill="none" stroke="${G.b}" stroke-width="4" opacity="0"/><circle r="12" fill="${SC.dot || HEAD}" stroke="${G.b}" stroke-width="6"/>`;
      L.append(s);
      const rect = s.querySelector("clipPath rect"), [halo, ring, dot] = s.querySelectorAll("circle");
      const L2 = [0]; for (let i = 1; i < pts.length; i++) L2.push(L2[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
      K.onFrame((t) => {
        const e = prog(t).u, xx = x - 20 + (w + 40) * e;
        rect.setAttribute("width", Math.max(0, xx - (x - 20)).toFixed(1));
        let px = pts[0][0], py = pts[0][1];
        for (let i = 1; i < pts.length; i++) { if (pts[i][0] >= xx) { const f = (xx - pts[i - 1][0]) / ((pts[i][0] - pts[i - 1][0]) || 1); px = xx; py = pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * Math.max(0, Math.min(1, f)); break; } px = pts[i][0]; py = pts[i][1]; }
        const on = t >= at0 ? 1 : 0, pulse = t > done ? 1 + 0.12 * Math.sin((t - done) * 6) : 1;
        [halo, ring, dot].forEach((c) => { c.setAttribute("cx", Math.min(px, x + w).toFixed(1)); c.setAttribute("cy", py.toFixed(1)); });
        halo.setAttribute("opacity", on ? SC.halo : 0); dot.setAttribute("opacity", on);
        halo.setAttribute("r", (26 * pulse).toFixed(1));
        // the landing: the tip grows with an overshoot and a ring goes out once
        const lu = land != null ? (t - land) / 0.6 : -1;
        dot.setAttribute("r", (12 + (lu >= 0 ? 6 * pop(Math.min(1, lu / 0.75)) : 0)).toFixed(2));
        ring.setAttribute("opacity", lu >= 0 && lu <= 1 ? (0.8 * (1 - lu)).toFixed(3) : 0); ring.setAttribute("r", (14 + 50 * Math.max(0, Math.min(1, lu))).toFixed(1));
      });
      if (co.sfx !== false) K.sfx("riser/riser__short-space-stutter-intro-riser__mixkit-1144", co.sfxAt != null ? co.sfxAt : at0, -26);
      if (land != null && co.landSfx !== false) K.sfx(co.landSfx || "pop", land, -20, true);
      return s;
    };
    const chip = (L, x, y, html, t, x2 = {}) => { const d = el(L, `left:${x}px;top:${y}px`, html, "cv-chip"); if (t != null) land3d(d, t, Object.assign({ fromRy: 0, fromZ: -160, dur: 0.6, drift: false, db: -26 }, x2)); return d; };
    // a layer's own px that sit at screen px (sx, sy) when the camera is at v ({ x, y, z }): place things on far/near layers
    const onLayer = (n, v, sx, sy) => { const p = P[n], z = 1 + ((v.z || 1) - 1) * p, cx = c0.x + (v.x - c0.x) * p, cy = c0.y + (v.y - c0.y) * p;
      return [cx + (sx - WD / 2) / z, cy + (sy - HT / 2) / z]; };
    // pastel blocks (decor): [[x, y, w, h, colour]] that pop in one after another; on "far" they give the stage depth.
    // A stage with one block colour (whitespace: neutral grey) draws every block in it, a template's hex included
    const blocks = (L, list, t, x = {}) => list.map(([bx, by, bw, bh, col], i) => {
      const d = el(L, `left:${bx}px;top:${by}px;width:${bw}px;height:${bh}px;border-radius:${x.r || 24}px;background:${ST.blocks || PAPER.pastel[col] || col}`);
      d.dataset.decor = "1";
      if (t != null) { const ti = t + i * (x.stagger || 0.07); d.style.visibility = "hidden"; tl.set(d, { visibility: "visible" }, Q(ti));
        tl.fromTo(d, { scale: 0.55, opacity: 0 }, { scale: 1, opacity: 1, duration: x.dur || 0.4, ease: "back.out(1.6)", immediateRender: false }, Q(ti)); }
      return d;
    });
    // a macro lens over the view: the edges blurred, the centre sharp (a radial mask on a backdrop blur); fade: [t, dur]
    const dof = (a, b, x = {}) => {
      const m = `radial-gradient(ellipse ${x.rx || 44}% ${x.ry || 40}% at ${x.cx || 50}% ${x.cy || 46}%, transparent 40%, #000 100%)`;
      const d = el(ROOT, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:3;pointer-events:none;backdrop-filter:blur(${x.blur || 7}px);-webkit-backdrop-filter:blur(${x.blur || 7}px);mask-image:${m};-webkit-mask-image:${m}`);
      d.dataset.decor = "1";
      K.show(d, a, b);
      if (x.fade) tl.to(d, { opacity: 0, duration: x.fade[1], ease: "power1.in", immediateRender: false }, Q(x.fade[0]));
      return d;
    };
    // a station: a group on a layer that exists only while the camera is near it (precheck reads only what can be on
    // screen, and the renderer skips the rest). Pass [a, b] with the camera's travel in and out included. With st (the
    // station's centre in the layer's px) it is one flat frame (WD x HT) there: children use screen px, and 3D turns
    // are seen from the frame's own centre only (with preserve-3d the layer's far-away perspective adds to it and
    // pushes cards off the frame's edge)
    const station = (a, b, n = "mid", st = null) => {
      const d = el(layers[n], st ? `left:${st[0] - WD / 2}px;top:${st[1] - HT / 2}px;width:${WD}px;height:${HT}px;perspective:${o.persp || 2000}px`
        : `left:0;top:0;width:${CW}px;height:${CH}px;transform-style:preserve-3d`);
      K.show(d, a, b); return d; };
    // a HyperFrames catalog piece (film.py MOUNTS, kit/hf/mounts.py) is written into the page over the camera, in screen
    // px; moved into a flat station it rides the camera's whips and pushes (tested 2026-10-20). Pieces by name (the first
    // mount of it), index (mount-<i>) or element. (Found by a fixed selector and the name compared in script: a
    // template-literal selector fails `hyperframes lint` (template_literal_selector), 2026-10-22)
    const adopt = (parent, ...pieces) => pieces.map((p) => {
      const e = typeof p === "number" ? document.getElementById("mount-" + p)
        : typeof p === "string" ? HF.canvas.mountOf(p) : p;
      if (!e) throw new Error(`C.adopt: no mount ${p} on this page (film.py MOUNTS)`);
      parent.append(e); return e; });
    // the kit's shared pieces on this stage (HF.parts, 2026-10-20): the UI cards (C.ui.pr, C.ui.checklist, ...) and evidence
    // (C.scoreboard, C.flow, C.focus) in the canvas look. Put them in a flat station (station(a, b, n, st)) so their page px
    // are screen px; C.parts.layer(a, b, station, { float: 0, push: 0 }) makes a layer C.focus can zoom. C.parts.FRONT (stamps,
    // pointers, lower thirds) sits over the camera, in screen px.
    const PT = HF.parts ? HF.parts(K, ROOT, { z: 7 }) : null;
    // ---------------------------------------------------------------- takeovers (2026-10-22, kit v11; kit/hf/trans.js)
    // C.takeover(a, b, { kind | mount | build, in, out, ... }): a full-screen scene with him off (absent, never cut out):
    // a plate in the look's paper over the canvas, the scene on its own camera, his shape off at a and back at b (the
    // shape he had before). trans.js builds the scene and its transitions; here the canvas keeps his side (TK, the
    // speakers' re-plan) and the zooms about a point (ZM) that the view and his shape share.
    const API = { layers, layer: (n) => layers[n], station, adopt, at: onLayer, blocks, dof, cam, hold, state, window: window3d, card, land3d, highlight, beam, big, speaker, chart, chip,
      G, GRAD, PAPER, stage: ST, look: HF.LOOK.name, CW, CH, view, back, root: ROOT, c0,
      parts: PT, ui: PT ? PT.ui : {}, scoreboard: PT && PT.scoreboard, flow: PT && PT.flow, focus: PT && PT.focus,
      takeover: (a, b, x = {}) => { if (!HF.takeover || !HF.takeover.canvas) throw new Error("C.takeover needs kit/hf/trans.js (vendor.py MODULES)"); return HF.takeover.canvas(K, API, a, b, x); },
      zoomAt, _tk: TK, _replan: () => SPK.forEach((f) => f()), _zoom: (z) => { ZM.push(z); }, _covers: (t) => COV.some((f) => f(t)) };
    return API;
  };
  // his shots with the takeovers written in (pure; tests/test_takeover.py). tks: [{ a, off, on, into, from, fromDur, fadeIn,
  // fadeOut, primary }] (trans.js): his shape leaves at `off` (a cut, or a fade over fadeIn from a; with `into` his card
  // first morphs over [a, off] into that element's frame, then is off), every template shot in [a, on - 0.05) is dropped
  // (the log names them), and at `on` the shape he had before a returns (a cut, a fade over fadeOut, or grown back out
  // of `from` over fromDur), unless the template has a shot within 0.05 s of `on` (that one is the return) or on is null
  // (a card that stays the graphic). Inserted shots carry tk (the takeover's number) and sfx false (no whoosh of their
  // own: the transition makes the sound). No takeovers: the template's shots, sorted, as before.
  // Every speaker on the canvas goes off for a takeover (the scene has the whole frame), but o.morph false (a speaker
  // that is not the primary one: a screen recording beside him) never morphs: it fades off over [a, off] and back over
  // fromDur instead, and a takeover with primary: true (T.cardToGraphic: his card becomes one graphic, the frame stays)
  // leaves it alone. A speaker already off at a (hidden between its own shots) stays off: no morph and no return, its
  // own next shot brings it back (review 2026-10-22: a screen speaker hidden at a reappeared beside his face, morphed
  // into the scene's card and stayed on after b). -> { shots, log: [text], dropped: [{ tk (index in tks), t }] }
  const takeoverShots = (shots, tks, o = {}) => {
    let out = shots.slice().sort((p, q) => p.t - q.t);
    const log = [], dropped = [], morph = o.morph !== false;
    if (!tks || !tks.length) return { shots: out, log, dropped };
    const plain = (s) => { const c = Object.assign({}, s); delete c.into; delete c.intoAt; delete c.from; delete c.tk; delete c.dur; delete c.ease; return c; };
    tks.map((k, j) => [k, j]).filter(([k]) => morph || !k.primary).sort((p, q) => p[0].a - q[0].a).forEach(([k, j], i) => {
      const n = i + 1, on = k.on != null ? k.on : null, span = `takeover ${n} (${k.a.toFixed(2)}-${on != null ? on.toFixed(2) : "..."})`;
      // the shape in force at a: the last shot before it, else the first (a speaker is drawn in its first shot's shape
      // from 0; that shape is kept before a when the takeover's off shot would otherwise become the first)
      const before = out.filter((s) => s.t < k.a - 1e-6), last = before.length ? before[before.length - 1] : out[0] || { mode: "card", t: 0 };
      const base = plain(last), hidden = !!last.off;
      const drop = out.filter((s) => s.t >= k.a - 1e-6 && (on == null ? s.t < k.off + 1e-6 : s.t < on - 0.05));
      drop.forEach((s) => { dropped.push({ tk: j, t: s.t }); log.push(`${s.t.toFixed(2)} ${span}: dropped his shot at ${s.t.toFixed(2)} (he is off${on != null && on - s.t < 0.35 ? `; a return meant for ${on.toFixed(2)}? put it within 0.05 s of it` : ""})`); });
      out = out.filter((s) => drop.indexOf(s) < 0);
      const ins = [];
      if (!before.length && out.length && k.a > 1e-6 && !hidden) ins.push(Object.assign({}, base, { t: 0, cut: true, sfx: false, tk: n }));
      if (hidden) {
        ins.push(Object.assign({}, base, { t: k.a, off: true, cut: true, sfx: false, tk: n }));
        if (k.into && morph) log.push(`${k.a.toFixed(2)} ${span}: his shape is already off at ${k.a.toFixed(2)}, so nothing morphs into the scene's card (it lands on its own)`);
        out = out.concat(ins).sort((p, q) => p.t - q.t);
        return;
      }
      const fade = (d) => (d > 0 ? { dur: d, ease: "power1.inOut" } : {});
      if (k.into && morph) {
        ins.push(Object.assign({}, base, { t: k.a, mode: "card", into: k.into, intoAt: k.off, dur: Math.max(0.05, k.off - k.a), ease: "power3.inOut", cut: false, off: false, sfx: false, tk: n }));
        ins.push(Object.assign({}, base, { t: k.off, mode: "card", into: k.into, intoAt: k.off, off: true, cut: true, sfx: false, tk: n }));
      } else {
        const fi = k.into ? Math.max(0.05, k.off - k.a) : k.fadeIn;      // (not the primary: off over the morph's time)
        ins.push(Object.assign({}, base, { t: k.a, off: true, cut: !(fi > 0), sfx: false, tk: n }, fade(fi)));
      }
      if (on != null && !out.some((s) => Math.abs(s.t - on) <= 0.05)) {
        if (k.from && morph) {
          ins.push(Object.assign({}, base, { t: on - 0.001, mode: "card", into: k.from, intoAt: on, off: true, cut: true, sfx: false, tk: n }));
          ins.push(Object.assign({}, base, { t: on, off: false, cut: false, from: k.from, dur: k.fromDur || 0.55, ease: "power3.inOut", sfx: false, tk: n }));
        } else {
          const fo = k.from ? k.fromDur || 0.55 : k.fadeOut;
          ins.push(Object.assign({}, base, { t: on, off: false, cut: !(fo > 0), sfx: false, tk: n }, fade(fo)));
        }
      }
      out = out.concat(ins).sort((p, q) => p.t - q.t);
    });
    return { shots: out, log, dropped };
  };
  // the seated frame's shape (pure; tests/test_lens.py): full bleed, or the large card: s.w x s.h, by default 87.5 % of
  // the page width at 16:9 on a landscape page (1680 x 945 at 1920, the v11 default) and 4:5 on a portrait one (945 x
  // 1181 at 1080: a fixed 1680 spilled 300 px off each side of a Reel, review 2026-10-22), centred on s.x, s.y
  const frameBox = (s, WD, HT) => {
    if (s.full) return { bx: 0, by: 0, bw: WD, bh: HT };
    const bw = s.w || Math.round(0.875 * WD), bh = s.h || Math.round(bw * (HT > WD ? 5 / 4 : 9 / 16));
    return { bx: (s.x != null ? s.x : WD / 2) - bw / 2, by: (s.y != null ? s.y : HT / 2) - bh / 2, bw, bh };
  };
  // a frame shot's clean rect (pure): c = [x0, y0, x1, y1] for every take, or { <clip>: rect } per take, the take playing
  // (clip); none (or a take the map leaves out) is the whole source
  const cleanRect = (c, clip, full) => (!c ? full : Array.isArray(c) ? c : c[clip] || full);
  // the first catalog mount of that name on the page (kit/hf/mounts.py writes a div of class hf-mount, data-mount=name; the
  // literal markup is kept out of this file: render4k.py reads it in a page as "this page has catalog pieces"), or
  // null: a fixed selector, the name compared in script (lint: no template-literal selectors)
  HF.canvas.mountOf = (name) => [...document.querySelectorAll(".hf-mount")].find((m) => m.dataset.mount === String(name)) || null;
  HF.canvas.G = G;
  HF.canvas.driftOf = driftOf;
  HF.canvas.accentOf = accentOf;
  HF.canvas.frameBox = frameBox;
  HF.canvas.cleanRect = cleanRect;
  HF.canvas.takeoverShots = takeoverShots;
})(typeof window !== "undefined" ? window : globalThis);
