/*
 * kit/hf/trans.js: transitions and takeovers (2026-10-22, kit v11; gap items 2 and 13). The owner asked for
 * "out-of-the-box full-screen animation scenes where he is removed completely" and for better cuts and transitions.
 * Two parts, both pure functions of time on the paused timeline (seek any frame, same picture):
 *
 * TAKEOVERS: a full-screen scene with him off (absent, never cut out). The frame gives it its paper and a camera:
 *   const tk = C.takeover(a, b, { kind: "type", text: "Neat beats *busy.*", kicker: "the rule" })      // HF.canvas
 *   const tk = S.takeover(a, b, { kind: "list", title: "Three rules", items: [["one idea", t1], ...] })  // HF.studio / HF.reel
 *   kinds (HF.takeover.kinds; each one has motion inside: the takeover's own camera pushes while it holds):
 *     type      a statement: big type, one accent mark (text "*word" accents; mark { word, t, kind: "underline" |
 *               "strike" }; kicker, sub, then { text, at } a second line that cascades in). The HERO block films
 *               copy-pasted (a plate, giant caps, a strike, a grey-out) is this kind.
 *     diagram   a system diagram that builds with HF.diagram (nodes [{ id, label, icon, at }], edges [[from, to, t]],
 *               focus [[id, t]], layout row | column | grid); flat on whitespace (kit/refs/DIAGRAMS.md: nodes also take
 *               sub, tag, mono, focal, kind; edges { from, to, t, route, label, accent }; title is its eyebrow; type,
 *               hub), circles elsewhere
 *     evidence  a close-up of a window or screenshot with one highlighter mark (img or html, url, mark [x, y, w, h] in
 *               the window body's px, markAt, note (a source line), noteAt); the camera pushes into the mark
 *     list      3-4 points landing on their words (title, kicker, items [[text, t], ...]) on one card
 *     chapter   T.chapter's white beat (num, title)
 *   or { mount: "name" } (a catalog piece, film.py MOUNTS, full frame) or { build: (L, tk) => parts } (any scene: L is
 *   a 1920 x 1080 (1080 x 1920) layer in screen px under the takeover's camera).
 *   in:  "cut" (default; "zoom" when from is given) | "fade" | "zoom" (zoom through `from`: an element of the page, or
 *        "eyes" = his face when his shape is 500 px or larger) | "card" (his card morphs into the scene's first card:
 *        tk.parts.main or x.card) | "match" (x.match: the element of the page whose clone flies into tk.parts.main)
 *   out: "fade" (default) | "cut" | "zoom" (zoom through x.into, an element of the scene, and land on x.to: the next
 *        camera { x, y, z } or [x, y] on a canvas) | "card" (his card grows back out of the scene's last card)
 *   tk = { a, b, root, plate, L, cam (tk.cam.cam(t, { x, y, z }, { dur, ease }), tk.cam.hold(a, b, dz)), parts, main }
 *   His shape: on a canvas the takeover writes his shots for him (C.speaker reads them, whichever is called first): an
 *   off shot at a, every template shot inside [a, b) dropped (said in the console, window.__lens[id].log and
 *   window.__takeovers[i].dropped), and his previous shape back at b (a template shot within 0.05 s of b is the return).
 *   Only the primary speaker (the one window.__speaker reports) morphs in "card"; another speaker fades off and back,
 *   and one already off at a stays off until its own next shot. When a shape covers the whole frame as the takeover
 *   starts or as he comes back (his full-bleed seated frame), the plate is opaque from a (until b + its out) and only
 *   his shape dissolves or morphs over the scene: the canvas his frame hid never shows through. Takeovers may not
 *   overlap (it throws: he would never come back); under 3 s of his face between two is warned.
 *   On HF.studio / HF.reel it is a box beat (beat(a, "takeover", { until: b })): the director takes him off and brings
 *   back the shape he had before; declare it before S.box() (the director plans once). window.__speaker reports kind
 *   "off" while he is gone.
 *   Budgets (kit/refs/SCENES.md §9; plan_check plans them, precheck measures them): long-form 15-30 % of the runtime
 *   in takeovers of 4-12 s, at least 3 s of face between two, the hook opens on his face, never away more than 12 s.
 *
 * TRANSITIONS: const T = HF.trans(K, C) (or HF.trans(K, S) on HF.studio / HF.reel):
 *   T.zoomThrough(t, el, to, x)   the camera zooms ~3x into el (expo.in 0.3 s), hard-cuts on the peak (t) to `to` (a
 *                                 canvas camera { x, y, z } / [x, y], a station element, or a takeover), which arrives
 *                                 from 3x (expo.out 0.45 s); speed blur on both sides (his footage too: a camera move)
 *   T.match(t, elA, elB, x)       a box flies (FLIP, 0.5 s power3.inOut) from elA's rect onto elB's, their skins and
 *                                 their contents cross-fading in it (each content at one uniform scale: type never
 *                                 stretches), while the camera cuts underneath (x.cut: the next camera); elA and elB
 *                                 are hidden while it flies
 *   T.chapter(t0, t1, x)          zoom through the outgoing anchor (x.from; his eyes when his shape is 500 px or larger)
 *                                 into a white chapter beat: x.num + x.title (2-4 words), held 1.2-2.2 s, one soft
 *                                 whoosh and a low hit at -18 dB (t0 snapped to a downbeat within 0.12 s when D.music
 *                                 exists; t1 stays, so the template's shot at t1 is his return); x.to: the camera it
 *                                 lands on after
 *   T.cardToGraphic(t, el, x)     his card shrinks / morphs into el's frame (a plate in el's colour always covers the whole
 *                                 shape, never a transparent edge), then el is the graphic; x.until: his card grows back
 *                                 out of x.back (default el) then. Canvas only (HF.studio / HF.reel: beat(t, "graphic",
 *                                 { card: true }) and S.fromPill do it there)
 *   T.whip(t, to, x) / T.cut(t, to)   a logged camera whip / hard cut on a canvas
 *   T.pick(t, ["zoom", "match", "whip"])   the first kind that keeps the budget at t (below)
 * The budget (a per-film no-repeat rule): never the same kind twice in a row (cuts may repeat: a hard cut is the
 * absence of a transition), whips at most 40 % of the scene changes. Every transition is logged to window.__trans
 * ([{ t, kind, why }], a function: HF.trans.list()), canvas camera moves included (C.cam: whip, glide, zoom, cut, by
 * what they do); kit/qa/precheck.mjs reports it and plan_check.py plans it. HF.trans.check(list) is the same rule, pure.
 * A bracket (a takeover's in and out, T.cardToGraphic's morph and return: entries sharing a pair id) of one kind with
 * nothing between is one transition: it is published folded ({ ..., pair, until }), so precheck reads it once too.
 *
 * Kinds of transition and what each one means (kit/refs/SCENES.md §10): cut keeps the thought going; whip moves to the
 * next station of the same world; glide a slow travel there; zoom dives into the detail being explained; match carries
 * a shape from one scene into the next; card turns his card into the graphic (or back); chapter opens a new section;
 * fade is the soft return of his shape after a takeover. No shaders (HyperShader stays out, 2026-10-22).
 *
 * Also here: window.__speaker for HF.camera pages (scenes.js; the engine contract, kit/hf/README "window.__speaker"),
 * which publish it through a thin wrapper below until scenes.js does it itself.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit || !HF.keyed) throw new Error("kit/hf/trans.js needs core.js first");
  const NS = "http://www.w3.org/2000/svg";
  const clamp01 = (u) => Math.max(0, Math.min(1, u));
  const smooth = (u) => { u = clamp01(u); return u * u * (3 - 2 * u); };
  const easeOf = (e) => (typeof e === "function" ? e : root.gsap ? gsap.parseEase(e) : (u) => u);
  let uid = 0;

  // ================================================================== the log and the budget (pure)
  // kinds (kit/refs/SCENES.md §10, plan_check.TRANSITIONS plus glide and fade)
  const KINDS = ["cut", "whip", "glide", "zoom", "match", "card", "chapter", "fade"];
  const BUDGET = { whips: 0.4 };
  const LOG = [], SOURCES = [];
  let pairs = 0;
  // a bracket: the two ends of one move there and back (a takeover's in and its out, T.cardToGraphic's morph and its
  // return) share a pair id. Logged as the same kind with nothing between them they are one transition, folded into the
  // first entry (until: the return's time): the same move there and back is one idea, not a repeat (review 2026-10-22:
  // in "card" / out "card", the design's signature, and cardToGraphic with until failed the budget every time). A kind
  // between them, or a different kind at either end, leaves both entries as they are (pure)
  const fold = (L) => {
    const out = [];
    for (let i = 0; i < L.length; i++) {
      const p = L[i], q = L[i + 1];
      if (p.pair != null && q && q.pair === p.pair && q.kind === p.kind && p.until == null) { out.push(Object.assign({}, p, { until: q.t, why: `${p.why} + ${q.why} (one bracket)` })); i++; }
      else out.push(p);
    }
    return out;
  };
  const norm = (list) => (list || []).filter((x) => x && Number.isFinite(+x.t))
    .map((x) => Object.assign({ t: +x.t, kind: String(x.kind || "?"), why: x.why || "" }, x.pair != null ? { pair: x.pair } : {}, x.until != null ? { until: +x.until } : {}))
    .sort((a, b) => a.t - b.t);
  // -> { n, kinds: {kind: count}, repeats: [{ a, b, kind }], whips (share), ok, findings: [text] }. Same rule as
  // kit/qa/speaker.mjs transStats (precheck) and plan_check.py: a kind twice in a row (cuts excepted), whips over 40 %;
  // a bracket counts once (fold; window.__trans is published folded, so precheck reads the same list)
  const check = (list) => {
    const L = fold(norm(list));
    const kinds = {}, repeats = [], findings = [];
    L.forEach((x) => (kinds[x.kind] = (kinds[x.kind] || 0) + 1));
    // (after a bracket the repeat is named from its return, the end next to the second one)
    for (let i = 1; i < L.length; i++) if (L[i].kind === L[i - 1].kind && L[i].kind !== "cut") repeats.push({ a: L[i - 1].until != null ? L[i - 1].until : L[i - 1].t, b: L[i].t, kind: L[i].kind });
    const whips = L.length ? (kinds.whip || 0) / L.length : 0;
    repeats.forEach((r) => findings.push(`'${r.kind}' twice in a row (${r.a.toFixed(2)} s and ${r.b.toFixed(2)} s)`));
    if (L.length >= 3 && whips > BUDGET.whips + 1e-9) findings.push(`whips are ${Math.round(100 * whips)} % of ${L.length} transitions (max ${100 * BUDGET.whips} %)`);
    return { n: L.length, kinds, repeats, whips, ok: !findings.length, findings };
  };
  // the first kind of `want` that keeps the budget at t (its neighbours before and after t differ from it, unless it is a
  // cut, and one more whip keeps whips <= 40 %); none fits: "cut" (pure). Neighbours are read with brackets opened (a
  // kind inside one sits between its two ends)
  const pick = (list, t, want) => {
    const F = fold(norm(list)), L = F.flatMap((x) => (x.until != null ? [x, { t: x.until, kind: x.kind, why: x.why, pair: x.pair }] : [x]));
    const before = L.filter((x) => x.t < t - 1e-6).pop(), after = L.find((x) => x.t > t + 1e-6);
    const n = F.length + 1, wh = F.filter((x) => x.kind === "whip").length;
    for (const k of want || []) {
      if (k !== "cut" && ((before && before.kind === k) || (after && after.kind === k))) continue;
      if (k === "whip" && n >= 3 && (wh + 1) / n > BUDGET.whips + 1e-9) continue;
      return k;
    }
    return "cut";
  };
  const logIt = (t, kind, why, pair) => { if (KINDS.indexOf(kind) < 0) console.warn(`HF.trans: unknown kind ${kind} (one of ${KINDS.join(", ")})`);
    LOG.push(Object.assign({ t: +(+t).toFixed(3), kind, why: why || "" }, pair != null ? { pair } : {})); };
  // every entry: the transitions logged here, plus the sources (HF.canvas: its camera's scene changes), in time order,
  // brackets folded (what window.__trans publishes and precheck reads)
  const list = () => {
    const out = LOG.slice();
    SOURCES.forEach((f) => { try { out.push(...(f() || [])); } catch (e) { console.warn("HF.trans source: " + e.message); } });
    return fold(out.sort((a, b) => a.t - b.t));
  };
  // a takeover's span against the ones already on the frame (spans: [{ a, on }]): overlapping ones leave him off for
  // good (the second reads him as already off at its a, so nothing brings him back until his next template shot; review
  // 2026-10-22: off from 16 s to the end of the page) -> throws. Under 3 s of his face between two -> a warning (the
  // budget, kit/refs/SCENES.md §9). T.cardToGraphic's windows count: his card is the graphic there
  const FACE_GAP = 3;
  const overlap = (spans, a, b) => (spans || []).find((s) => s.on != null && a < s.on - 1e-6 && s.a < b - 1e-6) || null;
  const claim = (spans, a, b, what) => {
    const o = overlap(spans, a, b);
    if (o) throw new Error(`${what} ${a.toFixed(2)}-${b.toFixed(2)} overlaps the one at ${o.a.toFixed(2)}-${o.on.toFixed(2)}: he would stay off after it (end one before the next starts, with ${FACE_GAP} s of his face between)`);
    (spans || []).forEach((s) => { if (s.on == null) return; const gap = a >= s.on ? a - s.on : s.a - b;
      if (gap < FACE_GAP - 1e-6) console.warn(`${what} ${a.toFixed(2)}-${b.toFixed(2)}: ${gap.toFixed(2)} s of his face next to the one at ${s.a.toFixed(2)}-${s.on.toFixed(2)} (at least ${FACE_GAP} s between two)`); });
  };

  // ================================================================== where an element is on the page at t (pure)
  // Walks up the offsetParent chain (layout px: the 3D turns of cards are ignored, flat stations only) and applies the
  // maps of the containers that move their content: a canvas layer (the camera with its parallax), the canvas view (a
  // transition's zoom about a point) and a takeover's camera. Each publishes el.__trMap(t) -> { k, ox, oy } (its
  // content px -> its box px). Stops at the composition root ([data-composition-id]): page px.
  // -> { x, y, w, h, k (page px per element px), r (its corner radius on the page) }
  const rectAt = (el, t) => {
    if (!el || el.offsetParent === undefined) throw new Error("HF.trans.rectAt: not an element");
    let x = 0, y = 0, k = 1, e = el;
    while (e) {
      const m = e.__trMap ? e.__trMap(t) : null;
      if (m) { x = m.ox + m.k * x; y = m.oy + m.k * y; k *= m.k; }
      if (e.dataset && e.dataset.compositionId) break;
      x += e.offsetLeft; y += e.offsetTop;
      e = e.offsetParent;
    }
    const cs = root.getComputedStyle ? getComputedStyle(el) : null, r = cs ? parseFloat(cs.borderTopLeftRadius) || 0 : 0;
    return { x, y, w: el.offsetWidth * k, h: el.offsetHeight * k, k, r: r * k };
  };
  // el's top-left inside container (both laid out; no maps): a takeover's scene px
  const localIn = (el, box) => { let x = 0, y = 0, e = el; while (e && e !== box) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    return { x, y, w: el.offsetWidth, h: el.offsetHeight }; };
  // hide an element over predicates of time without fighting GSAP for its opacity or visibility: clip-path is a property
  // the kit never tweens, so this one writer owns it (the value outside every window is what the element had)
  const hideWhile = (K, el, when) => {
    if (!el.__trHide) { const own = el.style.clipPath || "", ws = (el.__trHide = []);
      K.onFrame((t) => { el.style.clipPath = ws.some((f) => f(t)) ? "inset(50%)" : own; }); }
    el.__trHide.push(when);
  };

  // ================================================================== a camera for a screen-space scene (takeovers)
  // HF.trans.camera(K, wrap, { z, x, y }): keyed like C.cam (zoom in log space), holds that push (C.hold: dz over [a, b],
  // sine), speed blur (a directional SVG blur from the move, as the canvas camera has). wrap.__trMap is its map.
  const camera = (K, wrap, o = {}) => {
    const W = K.width, H = K.height, c0 = { x: o.x != null ? o.x : W / 2, y: o.y != null ? o.y : H / 2, z: o.z || 1 };
    const keys = [], holds = [], lands = [];
    let at = null;
    // x.land: a landing from a zoom's peak (3x -> 1x): its speed blur hides the cut on its first frame, half on the second,
    // and the scene is sharp from the third (fix round 2026-10-23: it sat at the blur cap for ~5 frames)
    const cam = (t, v, x = {}) => { keys.push({ t: K.Q(t), dur: x.dur || 0.6, ease: x.ease || HF.E.move, v }); if (x.land) lands.push(K.Q(t)); at = null; };
    const landF = (t) => { const fps = K.fps || 30; let f = 1; for (const l of lands) if (t >= l - 1e-6 && t < l + ZOUT) f = Math.min(f, clamp01(1 - ((t - l) * fps) / 2)); return f; };
    const hold = (a, b, dz = 0.035) => { if (b > a + 0.2) holds.push({ a, b, dz }); };
    const state = (t) => { if (!at) at = HF.keyed(keys, c0, { log: ["z"] });
      const s = at(t);
      for (const h of holds) if (t > h.a) s.z *= 1 + h.dz * (0.5 - 0.5 * Math.cos(Math.PI * clamp01((t - h.a) / (h.b - h.a))));
      return s; };
    const id = "trc" + ++uid, svg = document.createElementNS(NS, "svg");
    svg.setAttribute("width", 0); svg.setAttribute("height", 0); svg.style.position = "absolute";
    svg.innerHTML = `<defs><filter id="${id}" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="0 0"/></filter></defs>`;
    wrap.parentNode.insertBefore(svg, wrap);
    const g = svg.querySelector("feGaussianBlur");
    wrap.style.transformOrigin = "0 0";
    const map = (s) => ({ k: s.z, ox: W / 2 - s.x * s.z, oy: H / 2 - s.y * s.z });
    wrap.__trMap = (t) => map(state(t));
    K.onFrame((t) => {
      const s = state(t), s2 = state(t + 1 / (K.fps || 30)), m = map(s);
      wrap.style.transform = `matrix(${m.k.toFixed(5)},0,0,${m.k.toFixed(5)},${m.ox.toFixed(2)},${m.oy.toFixed(2)})`;
      // speed blur: travel in screen px per frame, plus the zoom's rate (relative, so 3x -> 1x blurs like 1x -> 1/3x)
      const vx = Math.abs(s2.x - s.x) * s.z, vy = Math.abs(s2.y - s.y) * s.z, vz = (Math.abs(s2.z - s.z) / s.z) * 700;
      const lf = lands.length ? landF(t) : 1;
      const bx = Math.min(16, vx * 0.45 + vz * 0.3) * lf, by = Math.min(16, vy * 0.45 + vz * 0.3) * lf;   // (16: the type stays a shape)
      if (bx + by > 0.6) { g.setAttribute("stdDeviation", `${bx.toFixed(2)} ${by.toFixed(2)}`); wrap.style.filter = `url(#${id})`; } else wrap.style.filter = "none";
    });
    return { cam, hold, state, keys };
  };

  // ================================================================== the look a scene is drawn in
  // A canvas reads its stage (C.stage: canvas_studio's caps and gradient, whitespace's Inter and one accent); any other
  // frame reads the look's tokens (HF.C, HF.F) the frame applied.
  const lookOf = (H) => {
    const C = HF.C, F = HF.F, ST = H && H.stage ? H.stage : null;
    const solid = !ST || (ST.grad[0] === ST.grad[1] && ST.grad[1] === ST.grad[2]);
    return { paper: ST ? ST.seamless : C.paper, ink: C.ink, sub: C.sub || C.ink2, mute: C.mute, acc: C.acc, accTint: C.accTint, line: C.line,
      card: (ST && ST.card.bg) || C.card, sunk: C.sunk || "#F5F5F7", e1: C.e1, e2: (ST && ST.card.shadow) || C.e2, e3: (ST && ST.win.shadow) || C.e3,
      big: ST ? { font: ST.big.font, weight: ST.big.weight, case: ST.big.case, lh: ST.big.lh, track: ST.big.track, ink: ST.big.ink }
        : { font: F.display, weight: F.displayWeight || 700, case: "none", lh: "0.98", track: F.displayTrack || "-0.02em", ink: C.ink },
      title: ST ? { font: ST.t.font, weight: ST.t.weight, ink: ST.t.ink, track: ST.t.track } : { font: F.body, weight: 700, ink: C.ink, track: "-0.02em" },
      body: ST ? ST.s.font : F.body, mono: F.mono || "monospace",
      // the accent mark: canvas_studio's gradient (as its hero strike was), else the one solid accent
      mark: H && H.GRAD && !solid ? H.GRAD : C.acc, grad: H && H.GRAD && !solid ? H.GRAD : null,
      hl: ST ? (ST.hl.bg || null) : null, hlOp: ST ? ST.hl.op : 1, hlBlend: ST ? ST.hl.blend : "multiply", fill: C.onFill || "#fff" };
  };
  const kickerHTML = (LK, text, portrait) => `<div class="mono" style="font:500 ${portrait ? 30 : 27}px/1 ${LK.mono};letter-spacing:.14em;text-transform:uppercase;color:${LK.sub};white-space:nowrap">${HF.esc(text)}</div>`;
  // a land: from depth and blur, settling (the kit's entrance ease); pre = it is already there when the scene arrives
  const landIn = (K, e, t, x = {}) => {
    e.style.visibility = "hidden"; K.tl.set(e, { visibility: "visible" }, K.Q(t));
    K.tl.fromTo(e, { opacity: 0, y: x.y != null ? x.y : 40, scale: x.scale || 0.97, filter: `blur(${x.blur != null ? x.blur : 10}px)` },
      { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", duration: x.dur || 0.6, ease: x.ease || HF.E.in, immediateRender: false }, K.Q(t));
  };

  // ================================================================== takeover kinds
  // kind(ctx, x) -> parts { main (the element a card / zoom / match transition uses), ... }; ctx = { K, L, a, b, cam,
  // look, W, H, portrait }. Text sizes follow the white look's rules (kit/presets/whitespace README §2): body >= 32 px,
  // the kicker 26-30 px mono caps in sub (class mono: precheck's size floor exempts kickers), one accent mark a scene.
  const KINDS_TK = {};
  // the type kind's sizes (pure; tests/test_takeover.py): the statement's lines fit the frame's width at the font's
  // average character width (em: 0.34 for a serif, 0.5 for the sans and caps looks), capped at size; the cascading
  // `then` line at 0.55 of that, and never wider than the frame either (review 2026-10-22: "Neat." at 200 px set a
  // 47-character then at 110 px, about 2480 px wide on a 1920 page). An explicit then.size is the template's call
  const typeFit = (x, W, portrait, font) => {
    const lines = String(x.text || "").split("|"), em = /Serif/.test(font || "") ? 0.34 : 0.5, maxW = W - 2 * (x.margin || (portrait ? 70 : 120));
    const len = (s) => Math.max(1, String(s || "").replace(/\*/g, "").length);
    const size = Math.round(Math.min(x.size || (portrait ? 150 : 200), maxW / (em * Math.max(...lines.map(len)))));
    const ts = x.then ? x.then.size || Math.round(Math.min(size * 0.55, maxW / (em * len(x.then.text)))) : 0;
    return { lines, em, maxW, size, ts };
  };
  KINDS_TK.type = (c, x) => {
    const { K, L, a, look: LK, W, H } = c, tl = K.tl, Q = K.Q, el = K.el;
    const at = x.at != null ? x.at : c.pre ? a : a + 0.05, pre = at <= a + 1e-3;
    const { lines, size, ts } = typeFit(x, W, c.portrait, LK.big.font);
    const align = x.align || "center", lh = parseFloat(LK.big.lh) || 0.92;
    const blockH = size * lh * lines.length + (x.kicker ? 64 : 0) + (x.sub ? 90 : 0) + (x.then ? ts * 1.1 + 30 : 0);
    const left = align === "center" ? 0 : x.x != null ? x.x : 120, y = x.y != null ? x.y : Math.round(c.band[0] + (c.band[1] - c.band[0] - blockH) / 2);
    const group = el(L, `left:${left}px;top:${y}px;width:${align === "center" ? W : W - left - 60}px;text-align:${align}`);
    group.dataset.group = "takeover-type";
    const kick = x.kicker ? el(group, "margin-bottom:34px", kickerHTML(LK, x.kicker, c.portrait), "") : null;
    const line = el(group, `font-family:${LK.big.font};font-weight:${LK.big.weight};text-transform:${LK.big.case};line-height:${LK.big.lh};` +
      `letter-spacing:${LK.big.track};color:${LK.big.ink};font-size:${size}px;white-space:nowrap`, "", "");
    const words = [];
    lines.forEach((ln, li) => {
      if (li) line.append(document.createElement("br"));
      HF.accentTokens(ln).forEach(({ text, accent }) => {
        const s = document.createElement("span"); s.style.cssText = "position:relative;display:inline-block"; s.textContent = text;
        if (accent) { if (LK.grad) s.style.cssText += `;background:${LK.grad};-webkit-background-clip:text;background-clip:text;color:transparent`; else s.style.color = LK.acc; s.dataset.accent = "1"; }
        line.append(s, document.createTextNode(" ")); words.push(s);
      });
    });
    if (!pre) {
      if (kick) landIn(K, kick, at - 0.12, { y: 16, blur: 6, dur: 0.45 });
      line.style.visibility = "hidden"; tl.set(line, { visibility: "visible" }, Q(at));
      tl.fromTo(line, { opacity: 0, y: 50, scale: 1.05, filter: "blur(12px)" }, { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", duration: 0.6, ease: HF.E.emph, immediateRender: false }, Q(at));
    }
    let then = null;
    if (x.then) {                                                          // a second line that cascades in, word by word (ts: typeFit)
      then = el(group, `margin-top:30px;font-family:${LK.big.font};font-weight:${LK.big.weight};text-transform:${LK.big.case};line-height:1.05;letter-spacing:${LK.big.track};color:${LK.big.ink};font-size:${ts}px;white-space:nowrap`, "", "");
      HF.accentTokens(x.then.text).forEach(({ text, accent }, k) => {
        const m = document.createElement("span"); m.style.cssText = "display:inline-block;overflow:hidden;vertical-align:top;padding:0 0.04em 0.1em";
        const s = document.createElement("span"); s.style.cssText = "display:inline-block"; s.textContent = text;
        if (accent) { if (LK.grad) s.style.cssText += `;background:${LK.grad};-webkit-background-clip:text;background-clip:text;color:transparent`; else s.style.color = LK.acc; }
        m.append(s); then.append(m, document.createTextNode(" "));
        const t = x.then.at + k * (x.then.per || 0.05);
        s.style.visibility = "hidden"; tl.set(s, { visibility: "visible" }, Q(t));
        tl.fromTo(s, { yPercent: 110 }, { yPercent: 0, duration: 0.5, ease: HF.E.in, immediateRender: false }, Q(t));
      });
    }
    if (x.sub) { const su = el(group, `margin-top:34px;font:500 ${c.portrait ? 38 : 34}px/1.3 ${LK.body};color:${LK.sub}`, HF.esc(x.sub), ""); if (!pre) landIn(K, su, at + 0.25, { y: 14, blur: 6, dur: 0.5 }); }
    // the one mark: an underline or a strike drawn on a word as it is said (a child of the word: it sizes with it, so no
    // layout is measured before the fonts load); a strike greys the struck word out
    let mark = null;
    if (x.mark) {
      const mk = x.mark, wi = mk.word != null ? mk.word : Math.max(0, words.findIndex((w) => w.dataset.accent)), w = words[wi];
      if (!w) throw new Error(`HF.takeover type: no word ${mk.word} in "${x.text}"`);
      const strike = mk.kind === "strike", hgt = Math.max(8, Math.round(size * (strike ? 0.085 : 0.06)));
      mark = el(w, `left:-3%;width:106%;height:${hgt}px;top:${strike ? "50%" : "96%"};margin-top:${strike ? -hgt / 2 : 0}px;border-radius:${hgt / 2}px;background:${mk.color || LK.mark};transform-origin:0 50%`);
      mark.dataset.decor = "1";
      tl.fromTo(mark, { scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power3.inOut", immediateRender: true }, Q(mk.t));
      if (strike && mk.dim !== false) tl.to(w, { opacity: 0.32, duration: 0.3, immediateRender: false }, Q(mk.t + 0.2));
      if (mk.sfx !== false) K.sfx(mk.sfx || "click", mk.t + 0.05, mk.db != null ? mk.db : -24);
    }
    return { main: line, line, words, kicker: kick, group, mark, then };
  };
  KINDS_TK.chapter = (c, x) => {                                           // T.chapter's beat: the number, 2-4 words
    const parts = KINDS_TK.type(c, { text: x.title, kicker: x.num != null ? (x.kicker || "part") + " " + x.num : x.kicker, at: c.a, size: x.size || (c.portrait ? 130 : 170) });
    parts.group.dataset.group = "takeover-chapter";
    return parts;
  };
  KINDS_TK.list = (c, x) => {
    const { K, L, a, look: LK, W, H } = c, tl = K.tl, Q = K.Q, el = K.el, items = x.items || [];
    if (items.length < 3 || items.length > 4) console.warn(`HF.takeover list: ${items.length} points (3-4 read at a glance)`);
    const at = x.at != null ? x.at : c.pre ? a : a + 0.05, pre = at <= a + 1e-3, P = c.portrait;
    const cw = x.w || (P ? 940 : 1320), rowH = P ? 150 : 128, top = (x.title ? (P ? 200 : 170) : 70) + (x.kicker ? 50 : 0);
    const ch = x.h || top + rowH * items.length + 60, cx = x.x != null ? x.x : (W - cw) / 2, cy = x.y != null ? x.y : c.band[0] + Math.max(0, (c.band[1] - c.band[0] - ch) / 2);
    const card = el(L, `left:${cx}px;top:${cy}px;width:${cw}px;height:${ch}px;border-radius:30px;background:${LK.card};box-shadow:${LK.e2}`);
    card.dataset.group = "takeover-list";
    if (!pre) landIn(K, card, at, { y: 46, blur: 10, dur: 0.6 });
    if (x.kicker) el(card, `left:70px;top:64px`, kickerHTML(LK, x.kicker, P));
    const ti = x.title ? el(card, `left:70px;top:${x.kicker ? 110 : 64}px;width:${cw - 140}px;font-family:${LK.title.font};font-weight:${LK.title.weight};` +
      `letter-spacing:${LK.title.track};color:${LK.title.ink};font-size:${P ? 66 : 64}px;line-height:1.05;white-space:nowrap`, HF.esc(x.title)) : null;
    const rows = items.map(([text, t], i) => {
      const r = el(card, `left:70px;top:${top + 20 + i * rowH}px;width:${cw - 140}px;display:flex;align-items:baseline;gap:34px`,
        `<span class="mono" style="font:500 ${P ? 34 : 32}px/1 ${LK.mono};color:${LK.acc};flex:none">${String(i + 1).padStart(2, "0")}</span>` +
        `<span style="font-family:${LK.title.font};font-weight:${LK.title.weight};letter-spacing:${LK.title.track};font-size:${P ? 54 : 52}px;line-height:1.1;color:${LK.ink}">${HF.esc(text)}</span>`);
      landIn(K, r, t != null ? t : at + 0.3 + i * 0.5, { y: 26, blur: 8, dur: 0.5 });
      if (x.sfx !== false) K.sfx("pop", (t != null ? t : at + 0.3 + i * 0.5) + 0.08, -27);
      return r;
    });
    // the point being said is ink; the ones before it step back to sub (focus moves down the card as he talks)
    if (x.dim !== false) rows.forEach((r, i) => { const nx = items[i + 1]; if (nx && nx[1] != null) tl.to(r.lastChild, { color: LK.sub, duration: 0.3, immediateRender: false }, Q(nx[1])); });
    return { main: card, card, title: ti, rows };
  };
  KINDS_TK.evidence = (c, x) => {
    const { K, L, a, look: LK, W, H, cam } = c, tl = K.tl, Q = K.Q, el = K.el;
    const at = x.at != null ? x.at : c.pre ? a : a + 0.1, pre = at <= a + 1e-3, P = c.portrait;
    const w = x.w || (P ? 960 : 1240), h = x.h || (P ? 760 : 720), wx = x.x != null ? x.x : (W - w) / 2;
    const wy = x.y != null ? x.y : c.band[0] + Math.max(0, (c.band[1] - c.band[0] - h - (x.note ? 130 : 0)) / 2);
    const win = el(L, `left:${wx}px;top:${wy}px;width:${w}px;height:${h}px;border-radius:22px;overflow:hidden;background:${LK.card};box-shadow:${LK.e3}`);
    win.dataset.group = "takeover-evidence";
    const dots = (HF.LOOK.stage && HF.LOOK.stage.win.dots) || ["#DEDEE3", "#DEDEE3", "#DEDEE3"];
    const bar = el(win, `left:0;top:0;width:${w}px;height:54px;background:${LK.sunk};border-bottom:1px solid ${LK.line};display:flex;align-items:center;gap:10px;padding:0 22px;box-sizing:border-box`,
      dots.map((d) => `<i style="width:14px;height:14px;border-radius:50%;display:inline-block;background:${d}"></i>`).join("") +
      (x.url ? `<span style="margin-left:18px;font:500 20px/1 ${LK.body};color:${LK.sub};white-space:nowrap">${HF.esc(x.url)}</span>` : ""));
    bar.dataset.decor = "1";
    const body = el(win, `left:0;top:54px;width:${w}px;height:${h - 54}px;overflow:hidden;background:${LK.card}${x.img ? ` url(${x.img}) ${x.pos || "center top"}/${x.fit || "cover"} no-repeat` : ""}`, x.html || "");
    if (!pre) landIn(K, win, at, { y: 50, blur: 10, dur: 0.7, scale: 0.96 });
    if (!pre && x.sfx !== false) K.sfx("pop", at + 0.12, -25);
    let mark = null;
    if (x.mark) {
      const [mx, my, mw, mh] = x.mark, mt = x.markAt != null ? x.markAt : at + 0.9;
      mark = el(body, `left:${mx}px;top:${my}px;width:${mw}px;height:${mh}px;border-radius:6px;background:${LK.hl || LK.grad || LK.accTint};` +
        `opacity:${LK.hl || !LK.grad ? 1 : LK.hlOp};mix-blend-mode:${LK.hlBlend};transform-origin:0 50%`);
      mark.dataset.decor = "1";
      tl.fromTo(mark, { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: HF.E.in, immediateRender: true }, Q(mt));
      if (x.sfx !== false) K.sfx("ui/ui__select-click__mixkit-1109", mt, -26);
      // the camera leans into the marked line, as far as the window and its source line stay in frame (a 1.22x push
      // toward the mark took the note off the bottom on the fixture, 2026-10-22: precheck's read gate caught it)
      // (and never so far that the window outgrows the frame: on a Reel a 960 px window allows 1.04x; precheck caught it)
      const m = 40, box = [wx, wy, wx + w, wy + h + (x.note ? 34 + (P ? 100 : 90) : 0)];
      const z = Math.min(x.zoom || (x.note ? 1.14 : 1.22), (W - 2 * m) / (box[2] - box[0]), (H - 2 * m) / (box[3] - box[1]));
      if (x.push !== false && z > 1.02 && !P) {                         // (a Reel: no lean, its safe band is too tight)
        const px = wx + mx + mw / 2, py = wy + 54 + my + mh / 2;
        const fit = (p, lo, hi, D) => { const half = (D / 2 - m) / z; return hi - lo > 2 * half ? (lo + hi) / 2 : Math.min(lo + half, Math.max(hi - half, p)); };
        cam.cam(mt, { x: fit(px, box[0], box[2], W), y: fit(py, box[1], box[3], H), z }, { dur: 1.3, ease: HF.E.move });
      }
    }
    let note = null;
    if (x.note) {
      note = el(L, `left:${wx}px;top:${wy + h + 34}px;width:${w}px;font:600 ${P ? 36 : 32}px/1.25 ${LK.body};color:${LK.sub}`, HF.esc(x.note));
      landIn(K, note, x.noteAt != null ? x.noteAt : at + 0.5, { y: 14, blur: 6, dur: 0.5 });
    }
    return { main: win, win, body, mark, note };
  };
  KINDS_TK.diagram = (c, x) => {
    const { K, L, a, b, W, H } = c;
    if (!HF.diagram) throw new Error("HF.takeover diagram needs kit/hf/diagram.js");
    // flat (kit/refs/DIAGRAMS.md; engine-adopt, 2026-10-22) is the whitespace look's diagram: hairline boxes on a grid,
    // its own eyebrow kicker, a loop's way back dashed under the row with its meaning on it. The other looks keep the
    // icon circles (or x.shape "card"), with v11's two fixes: the boxes inside 120 px margins, a reverse edge on its own port
    const flat = HF.diagram.styleOf(x) === "flat";
    const nodes = (x.nodes || []).map((n) => ({ id: n.id, label: n.label, icon: n.icon, sub: n.sub, x: n.x, y: n.y, kicker: "", tag: n.tag, mono: n.mono, focal: n.focal, kind: n.kind }));
    // edges: [from, to, t, bend] or { from, to, t, route, dash, label, accent } (flat) / { from, to, t, curve }
    const edges = (x.edges || []).map((e) => (Array.isArray(e) ? (flat ? { from: e[0], to: e[1] } : [e[0], e[1], e[3] || 0]) : Object.assign({}, e)));
    const dg = HF.diagram(K, L, { x: 0, y: c.band[0], w: W, h: c.band[1] - c.band[0], layout: x.layout || (c.portrait ? "column" : "row"), nodes, edges,
      style: x.style, shape: x.shape || (flat ? undefined : "circle"), steps: flat ? x.steps : false, drift: false, labelSize: x.labelSize || 54, pad: x.pad, rowY: x.rowY,
      margin: x.margin != null ? x.margin : 120, ports: "fan", title: flat ? x.title : undefined, type: x.type, hub: x.hub, gap: x.gap, portrait: c.portrait });
    dg.view.dataset.group = "takeover-diagram";
    // the title: a kicker over the diagram (HF.diagram's own title is a 16 px label, under the white look's floor); a
    // flat diagram draws its own, over its first box
    if (x.title && !flat) { const kt = K.el(L, `left:0;top:${x.titleY || (c.portrait ? c.band[0] : 170)}px;width:${W}px;text-align:center`, kickerHTML(c.look, x.title, c.portrait));
      if (!c.pre) landIn(K, kt, a + 0.1, { y: 14, blur: 6, dur: 0.45 }); }
    dg.show(a - 0.02, b + 0.6);
    // flat: one item a step (0.48 s) and edges drawing one after another by default (DIAGRAMS.md motion)
    (x.nodes || []).forEach((n, i) => dg.reveal(n.id, n.at != null ? n.at : a + 0.2 + i * (flat ? 0.48 : 0.4)));
    (x.edges || []).forEach((e, i) => { const ar = Array.isArray(e), t = ar ? e[2] : e.t;
      dg.connect(ar ? e[0] : e.from, ar ? e[1] : e.to, t != null ? t : a + 0.6 + (flat ? i * 0.3 : 0)); });
    (x.flows || []).forEach((f) => dg.flow(f[0], f[1], f[2], f[3] || {}));
    (x.focus || []).forEach(([id, t]) => (id === "*" ? dg.overview(t) : dg.focus(id, t)));
    return { main: dg.nodes[nodes[0].id].el, dg, nodes: dg.nodes };
  };

  // ================================================================== a takeover on a canvas (C.takeover)
  // Layers: the takeover sits at z 3 (over the canvas view z 2, under his shape z 4 and the canvas's front z 7), so his
  // card can morph into the scene's first card above the plate (in "card") and fade back in over it (out "fade"). The
  // canvas view is hidden while the plate covers it (precheck counts only what can be seen; the renderer skips it).
  const IN = { cut: 0, zoom: 0, fade: 0.35, card: 0.55, match: 0.5 }, OUT = { cut: 0, zoom: 0, fade: 0.4, card: 0.55 };
  const PEAK = 3, ZIN = 0.3, ZOUT = 0.45;
  const SND = { zoom: ["whoosh/whoosh__fast-small-sweep-transition__mixkit-166", -22], card: ["swish", -24], match: ["swish", -24], fade: null, cut: null };
  const scene = (K, H, a, b, x, plate, parent, z) => {
    const WD = K.width, HT = K.height, el = K.el;
    const rootEl = el(parent, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:${z};overflow:hidden;pointer-events:none`);
    rootEl.dataset.takeover = x.kind || (x.mount ? "mount" : "build");
    const fade = el(rootEl, `left:0;top:0;width:${WD}px;height:${HT}px`);
    const pl = plate ? el(fade, `left:0;top:0;width:${WD}px;height:${HT}px;background:${plate}`) : null;
    if (pl) pl.dataset.decor = "1";
    const wrap = el(fade, `left:0;top:0;width:${WD}px;height:${HT}px`);
    const L = el(wrap, `left:0;top:0;width:${WD}px;height:${HT}px`);
    return { rootEl, fade, plate: pl, wrap, L };
  };
  const content = (K, H, tk, x) => {
    // pre: the transition brings the scene (cut, zoom, card, match: a cut lands on the scene, never on an empty plate;
    // looked at on the fixture, 2026-10-22), so its pieces are already there at a unless x.at says; a fade lands them
    const pre = tk.in !== "fade";
    // band: where the scene's content sits vertically (a Reel: y 270..1250, clear of Instagram's UI, kit/hf/reel.js)
    const portrait = K.height > K.width, band = x.band || (portrait ? [270, 1250] : [0, K.height]);
    const ctx = { K, L: tk.L, a: tk.a, b: tk.b, cam: tk.cam, look: lookOf(H), W: K.width, H: K.height, portrait, band, tk, pre };
    if (x.build) return x.build(tk.L, tk) || {};
    if (x.mount) {                                                         // a catalog piece (film.py MOUNTS), full frame
      // (a fixed selector, the name compared in script: `hyperframes lint` fails a template-literal selector)
      const m = typeof x.mount === "string" ? [...document.querySelectorAll(".hf-mount")].find((e) => e.dataset.mount === x.mount) || null : x.mount;
      if (!m) throw new Error(`HF.takeover: no mount ${x.mount} on this page (film.py MOUNTS)`);
      Object.assign(m.style, { left: "0px", top: "0px", zIndex: "1" }); tk.L.append(m);
      return { main: m };
    }
    const f = KINDS_TK[x.kind || "type"];
    if (!f) throw new Error(`HF.takeover: unknown kind ${x.kind} (one of ${Object.keys(KINDS_TK).join(", ")})`);
    return f(ctx, x);
  };
  // the takeover camera's slow push over the hold (C.hold's 3-4 %): x.push, a number over 0; 0, null or anything else
  // takes the default 0.035 (fix round 2026-10-23: a takeover written with push: 0 held a still frame for its whole
  // 4-12 s); only push: false keeps it still
  const pushOf = (x) => (x.push === false ? 0 : typeof x.push === "number" && x.push > 0 ? x.push : 0.035);
  const checkLen = (a, b, x) => { const d = b - a;
    if (x.kind !== "chapter" && (d < 4 - 1e-6 || d > 12 + 1e-6)) console.warn(`HF.takeover ${x.kind || ""} at ${a.toFixed(2)}: ${d.toFixed(1)} s (a takeover is 4-12 s; a longer one splits on a face beat)`); };
  // an element of the scene named by the template: an element, a part's name ("main", "line", "card", "win"), or a
  // function of the parts ((p) => p.rows[2]), since the scene is built inside the call
  const elOf = (tk, v, dflt) => (v == null ? dflt : typeof v === "function" ? v(tk.parts) : typeof v === "string" ? (tk.parts[v] || null) : v);

  HF.takeover = function () { throw new Error("HF.takeover: use C.takeover (HF.canvas) or S.takeover (HF.studio / HF.reel)"); };
  HF.takeover.kinds = KINDS_TK;
  HF.takeover.IN = IN; HF.takeover.OUT = OUT; HF.takeover.PEAK = PEAK; HF.takeover.pushOf = pushOf;
  HF.takeover.canvas = function (K, C, a, b, x = {}) {
    const tl = K.tl, Q = K.Q, fps = K.fps || 30;
    a = Q(a); b = Q(b);
    const kin = x.in || (x.from ? "zoom" : "cut"), kout = x.out || (x.into && x.to ? "zoom" : "fade");
    if (!(kin in IN)) throw new Error(`C.takeover: in "${kin}" (one of ${Object.keys(IN).join(", ")})`);
    if (!(kout in OUT)) throw new Error(`C.takeover: out "${kout}" (one of ${Object.keys(OUT).join(", ")})`);
    checkLen(a, b, x);
    claim(C._tk, a, b, x.kind === "chapter" ? "T.chapter" : "C.takeover");
    const din = x.inDur || IN[kin], dout = x.outDur || OUT[kout];
    const sc = scene(K, C, a, b, x, x.paper || C.PAPER.seamless, C.root, x.z || 3);
    K.show(sc.rootEl, a, b + dout);                                       // out "zoom" / "cut": gone on the cut frame itself
    // its camera: arrives from the zoom's peak (in "zoom"), pushes while it holds, leaves into x.into (out "zoom")
    const cam = camera(K, sc.wrap, kin === "zoom" ? { z: PEAK, x: x.at ? x.at[0] : undefined, y: x.at ? x.at[1] : undefined } : {});
    const tk = { a, b, in: kin, out: kout, root: sc.rootEl, plate: sc.plate, L: sc.L, cam, parts: {} };
    if (kin === "zoom") cam.cam(a, { x: K.width / 2, y: K.height / 2, z: 1 }, { dur: ZOUT, ease: "expo.out", land: true });
    tk.parts = content(K, C, tk, x) || {};
    tk.main = tk.parts.main || null;
    cam.hold(a + (kin === "zoom" ? ZOUT : din), b - (kout === "zoom" ? ZIN : 0), pushOf(x));
    sc.rootEl.__tk = tk;
    // ---- the scene's opacities: one writer, a pure function of t (nothing else writes them). sc.fade (the whole
    // takeover) fades in over din on in "fade" and out over dout on out "fade"; sc.plate (the paper under the scene)
    // fades in over din on "card" (0.25 s on "match") and clears over 0.3 s on out "card". When a shape covers the whole
    // frame as the takeover starts (covA: his full-bleed seated frame) or comes back covering it (covB), the canvas under
    // the plate was never on screen there: the plate is opaque from a (until b + dout) and only his shape moves over the
    // scene: a true dissolve, or his frame shrinking into the card on paper (review 2026-10-22: station copy his full
    // frame had hidden ghosted over his face for 0.3-0.55 s on every soft entrance and exit). Asked lazily (C._covers,
    // canvas.js): the speakers are usually made after the takeovers
    const covA = () => (kin === "fade" || kin === "card" || kin === "match") && !!(C._covers && C._covers(a - 1e-3));
    const covB = () => (kout === "fade" || kout === "card") && !!(C._covers && C._covers(b + 0.051));
    const io = easeOf("power1.inOut"), pin = kin === "match" ? 0.25 : din;
    K.onFrame((t) => {
      if (t < a - 1e-6 || t > b + dout + 1e-6) return;                     // (K.show hides the takeover there)
      const cA = t < a + pin + 1e-6 && covA(), cB = t >= b - 1e-6 && covB();
      let f = 1, p = 1;
      if (kin === "fade" && !cA) f = io(clamp01((t - a) / din));
      if ((kin === "card" || kin === "match") && !cA) p = io(clamp01((t - a) / pin));
      if (t >= b - 1e-6 && kout === "fade" && !cB) f *= 1 - io(clamp01((t - b) / dout));
      if (t >= b - 1e-6 && kout === "card" && !cB) p *= 1 - io(clamp01((t - b) / 0.3));
      sc.fade.style.opacity = f.toFixed(4);
      if (sc.plate) sc.plate.style.opacity = p.toFixed(4);
    });
    // ---- in
    const T = HF.trans._canvas(K, C), TT = HF.trans(K, C);
    let into = null, from = null;
    if (kin === "zoom") T.zoomIn(a, x.eyes ? "eyes" : x.from || "eyes", { sfx: x.sfx, fallback: x.eyes ? x.from : null });
    if (kin === "card") { into = elOf(tk, x.card, tk.main); if (!into) throw new Error("C.takeover in \"card\": the scene has no card (pass card: el)"); hideWhile(K, into, (t) => t < a + din - 1e-6); }
    if (kin === "match") { const [A, B] = Array.isArray(x.match) ? x.match : [x.match]; if (!A) throw new Error("C.takeover in \"match\": pass match: el (the page's element that flies into the scene)");
      TT.match(a, A, B || tk.main, { log: false, sfx: x.sfx }); }
    // ---- out (the plate and the scene's fade: the writer above)
    if (kout === "fade") cam.hold(b, b + dout, 0.04);                     // it leaves toward the viewer as it fades
    if (kout === "card") { from = elOf(tk, x.cardOut || x.card, tk.parts.last || tk.main);
      if (!from) throw new Error("C.takeover out \"card\": the scene has no card (pass cardOut: el)");
      hideWhile(K, from, (t) => t >= b - 1e-6);
      [...sc.L.children].forEach((ch) => { if (ch !== from && !ch.contains(from)) tl.to(ch, { opacity: 0, duration: 0.25, immediateRender: false }, Q(b)); }); }
    if (kout === "zoom") T.zoomOut(b, tk, elOf(tk, x.into, tk.main), x.to, { sfx: x.sfx, at: x.toAt });
    // the canvas under the plate: hidden while it is covered (not when the template drives C.view itself: x.view false),
    // and while a covering shape hands over to the opaque plate (covA: from a; covB: until b + dout), so precheck reads
    // only what can be seen (the clip-path writer: GSAP owns its autoAlpha)
    const covered = a + (kin === "card" ? din : kin === "fade" ? din : kin === "match" ? 0.25 : 0);
    if (x.view !== false && b - covered > 0.1) { tl.set(C.view, { autoAlpha: 0 }, Q(covered)); tl.set(C.view, { autoAlpha: 1 }, Q(b));
      if (covered > a + 1e-6 || dout > 0) hideWhile(K, C.view, (t) => (t >= a - 1e-6 && t < covered - 1e-6 && covA()) || (t >= b - 1e-6 && t < b + dout - 1e-6 && covB())); }
    // ---- his shape (C.speaker reads these; a speaker made before this call is re-planned). rec: this takeover's entry in
    // window.__takeovers; the merge fills rec.dropped ([{ speaker, t }]: the template shots that fell inside it)
    const rec = { a, b, kind: x.kind || (x.mount ? "mount" : "build"), in: kin, out: kout, dropped: [] };
    (root.__takeovers = root.__takeovers || []).push(rec);
    // coverFrom / coverTo: when the plate covers the view (canvas.js's camera log: a move inside is no transition)
    C._tk.push({ a, off: kin === "card" ? a + din : a, on: b, into, from, fromDur: dout, fadeIn: kin === "fade" ? din : kin === "match" ? 0.2 : 0,
      fadeOut: kout === "fade" ? dout : 0, kind: x.kind || "build", rec, coverFrom: () => (covA() ? a : covered), coverTo: () => (covB() ? b + dout : b) });
    C._replan();
    // ---- the log and the sound (its in and out are one bracket: the same kind both ways counts once, fold)
    if (x.log !== false) { const pr = ++pairs; logIt(a, kin, `takeover ${x.kind || ""} in`.replace("  ", " "), pr); logIt(b, kout, `takeover ${x.kind || ""} out`.replace("  ", " "), pr); }
    if (x.sfx !== false) { if ((kin === "card" || kin === "match") && SND[kin]) K.sfx(SND[kin][0], a + 0.1, SND[kin][1]);
      if (kout === "card") K.sfx(SND.card[0], b + 0.1, SND.card[1]); }
    return tk;
  };

  // ================================================================== a takeover on HF.studio / HF.reel (S.takeover)
  // The box director takes him off at a and brings back the shape he had (box.js beat "takeover" with until: b); the
  // scene sits on BACK (under the box, over the world: the world is the plate, white on whitespace, the aurora on
  // pastel_box). in: "cut" | "fade" (the box dissolves) | "card" (the box collapses into the pill and the scene's card
  // grows out of it) | "zoom" (a hard cut, the scene arrives from 3x); out: "fade" | "cut" | "zoom" (into x.into).
  // the box's moves as transition kinds (a blend from or to off is a fade; the pill and the flip turn his card into the
  // graphic; a slide leaves like a whip pan; a swing is his card entering)
  const BOXT = { cut: "cut", dissolve: "fade", grow: "fade", shrink: "fade", move: "fade", collapse: "card", flip: "card", slide: "whip", swing: "card", tiles: "cut" };
  const BOXTK = new WeakMap();                                             // each HF.studio / HF.reel's takeover spans (claim)
  HF.takeover.box = function (S, a, b, x = {}) {
    const K = S.K, tl = K.tl, Q = K.Q;
    a = Q(a); b = Q(b);
    const kin = x.in || "cut", kout = x.out || "fade";
    if (!(kin in IN) || kin === "match") throw new Error(`S.takeover: in "${kin}" (cut, fade, card or zoom)`);
    if (!(kout in OUT) || kout === "card") throw new Error(`S.takeover: out "${kout}" (fade, cut or zoom)`);
    checkLen(a, b, x);
    if (!BOXTK.has(S)) BOXTK.set(S, []);
    claim(BOXTK.get(S), a, b, x.kind === "chapter" ? "T.chapter" : "S.takeover");
    BOXTK.get(S).push({ a, on: b });
    const dout = x.outDur || OUT[kout];
    // his return: the shape he had, faded back in over the scene's fade (the box's blend from off: "grow"), or on the cut
    S.beat(a, "takeover", { until: b, move: { cut: "cut", fade: "dissolve", card: "collapse", zoom: "cut" }[kin], card: kin === "card", tag: "takeover",
      backMove: x.backMove || { fade: "grow", cut: "cut", zoom: "cut" }[kout] });
    // the plate: the frame's own world (white on whitespace), so the scene has the whole frame over anything else on BACK;
    // pastel_box keeps its aurora alive behind the scene (no plate); x.plate: a colour, or false for none
    const plate = x.plate === false ? null : x.plate || (S.look === "pastel_box" ? null : S.WORLD.style.background || HF.C.paper);
    const sc = scene(K, S, a, b, x, plate, S.BACK, 2);
    K.show(sc.rootEl, a, b + dout);
    const cam = camera(K, sc.wrap, kin === "zoom" ? { z: PEAK } : {});
    const tk = { a, b, in: kin, out: kout, root: sc.rootEl, plate: sc.plate, L: sc.L, cam, parts: {} };
    sc.rootEl.__tk = tk;
    if (kin === "zoom") { cam.cam(a, { x: K.width / 2, y: K.height / 2, z: 1 }, { dur: ZOUT, ease: "expo.out", land: true }); if (x.sfx !== false) K.sfx(SND.zoom[0], a - 0.1, SND.zoom[1]); }
    tk.parts = content(K, null, tk, x) || {};
    tk.main = tk.parts.main || null;
    cam.hold(a + (kin === "zoom" ? ZOUT : 0.3), b - (kout === "zoom" ? ZIN : 0), pushOf(x));
    if (kin === "fade") tl.fromTo(sc.fade, { opacity: 0 }, { opacity: 1, duration: IN.fade, ease: "power1.inOut", immediateRender: false }, Q(a));
    if (kin === "card" && tk.main) {                                       // the box's signature: the pill becomes the card
      const r = localIn(tk.main, sc.L);
      HF.box.morph(K, tk.main, S.PILL, { x: r.x, y: r.y, w: r.w, h: r.h }, S.landOfCollapse(a), 0.32, { fromBg: S.C.acc, bg: getComputedStyle(tk.main).backgroundColor || HF.C.card });
    }
    if (kout === "fade") { tl.to(sc.fade, { opacity: 0, duration: dout, ease: "power1.inOut", immediateRender: false }, Q(b)); cam.hold(b, b + dout, 0.04); }
    if (kout === "zoom") { const into = elOf(tk, x.into, tk.main), r = localIn(into, sc.L);
      cam.cam(b - ZIN, { x: r.x + r.w / 2, y: r.y + r.h / 2, z: PEAK }, { dur: ZIN, ease: "expo.in" });
      if (x.sfx !== false) K.sfx(SND.zoom[0], b - 0.1, SND.zoom[1]); }
    // the log: the box's real moves (the director picks them at S.box()), read when the page asks
    if (x.log !== false) { const pr = ++pairs; SOURCES.push(() => {
      const P = root.__box && root.__box.plan;
      const near = (t) => P && P.keys ? P.keys.filter((k) => Math.abs(k.t - t) < 0.35).sort((p, q) => Math.abs(p.t - t) - Math.abs(q.t - t))[0] : null;
      const ki = near(a), ko = near(b);
      return [{ t: a, kind: kin === "zoom" ? "zoom" : ki ? BOXT[ki.kind] || "cut" : kin, why: `takeover ${x.kind || ""} in (box ${ki ? ki.kind : "?"})`, pair: pr },
        { t: b, kind: kout === "zoom" ? "zoom" : ko ? BOXT[ko.kind] || "fade" : kout, why: `takeover ${x.kind || ""} out (box ${ko ? ko.kind : "?"})`, pair: pr }];
    }); }
    (root.__takeovers = root.__takeovers || []).push({ a, b, kind: x.kind || (x.mount ? "mount" : "build"), in: kin, out: kout });
    return tk;
  };

  // ================================================================== the canvas side of the transitions
  // (shared by C.takeover and T): zoom about a point on the page (C._zoom: the view and his shape, with speed blur),
  // the canvas camera's hard cut (C.cam cut: no blur from the jump itself), FLIP clones
  HF.trans = function (K, H, o = {}) {
    const canvas = !!(H && H.cam && H.state && H._zoom), boxed = !!(H && H.beat && H.BEATS);
    const tl = K.tl, Q = K.Q, fps = K.fps || 30, WD = K.width, HT = K.height;
    const CV = canvas ? HF.trans._canvas(K, H) : null;
    const T = {
      log: (t, kind, why) => logIt(t, kind, why),
      list, check: () => check(list()), pick: (t, want) => pick(list(), t, want),
      // the camera zooms ~3x into el and hard-cuts on the peak (t) to `to`, which arrives from 3x
      zoomThrough(t, el, to, x = {}) {
        t = Q(t);
        if (to && to.cam && to.L) throw new Error("T.zoomThrough into a takeover: C.takeover(a, b, { in: \"zoom\", from: el }) does it");
        const tkFrom = el && el.nodeType ? takeoverOf(el) : null;
        if (tkFrom) {                                                      // inside one takeover: dive into el, land on `to` (its px)
          tkFrom.cam.cam(t - ZIN, Object.assign(centreIn(el, tkFrom), { z: PEAK }), { dur: ZIN, ease: "expo.in" });
          if (to != null) { const v = Array.isArray(to) ? { x: to[0], y: to[1] } : to.nodeType ? centreIn(to, tkFrom) : to;
            tkFrom.cam.cam(t - 1 / fps, { x: v.x, y: v.y, z: PEAK }, { dur: 0.001, ease: "none" });
            tkFrom.cam.cam(t, { z: v.z || 1 }, { dur: ZOUT, ease: "expo.out", land: true }); }
        } else if (canvas) { CV.zoomIn(t, el, { sfx: false }); CV.land(t, to, x); }
        else throw new Error("T.zoomThrough: el is on no canvas and in no takeover");
        if (x.sfx !== false) K.sfx(SND.zoom[0], t - 0.1, SND.zoom[1]);
        if (x.log !== false) logIt(t, "zoom", x.why || "zoom-through");
      },
      // a clone of elA flies onto elB while the camera cuts underneath (x.cut: the next canvas camera)
      match(t, A, B, x = {}) {
        t = Q(t);
        if (!A || !B) throw new Error("T.match: two elements");
        const dur = x.dur || 0.5, e = easeOf(x.ease || "power3.inOut"), ov = K.el(overlay(K, H), `left:0;top:0;width:${WD}px;height:${HT}px`);
        hideWhile(K, A, (u) => u >= t - 1e-6 && u < t + dur - 1e-6);
        hideWhile(K, B, (u) => u >= t - 1e-6 && u < t + dur - 1e-6);
        if (canvas && x.cut) CV.cut(t, x.cut);
        // the flight: a box that moves and resizes from A's rect to B's, its corner radius eased between theirs and each
        // one's skin (background, border, shadow) cross-fading under it; inside, clipped to it, each one's content at ONE
        // scale (the smaller of the box's two ratios to its own size), centred: type never stretches when the two rects
        // differ in aspect (review 2026-10-22: a chip flying onto a card drew its label 2x taller than wide, its pill an oval)
        let rA = null, rB = null, kA = null, kB = null;
        const skin = (src) => { const cs = getComputedStyle(src); return { background: cs.background, boxShadow: cs.boxShadow, border: cs.border }; };
        K.onFrame((u) => {
          ov.innerHTML = "";
          if (u < t - 1e-6 || u >= t + dur - 1e-6) return;
          if (!rA) { rA = rectAt(A, t - 1 / fps); rB = rectAt(B, t + dur); kA = skin(A); kB = skin(B); }   // pure: fixed times
          const p = e(clamp01((u - t) / dur)), r = { x: rA.x + (rB.x - rA.x) * p, y: rA.y + (rB.y - rA.y) * p, w: rA.w + (rB.w - rA.w) * p, h: rA.h + (rB.h - rA.h) * p };
          // the corner as a share of the box's shorter side (a pill's 999 px is 0.5 of its height), so a pill becomes a
          // card's corner along the way instead of staying a stadium for most of the flight
          const fr = (q) => Math.min(0.5, q.r / Math.max(1, Math.min(q.w, q.h))), rad = (fr(rA) + (fr(rB) - fr(rA)) * p) * Math.min(r.w, r.h);
          const ops = [1 - smooth((p - 0.25) / 0.5), smooth((p - 0.25) / 0.5)];
          const box = (css) => K.el(ov, `left:${r.x.toFixed(2)}px;top:${r.y.toFixed(2)}px;width:${r.w.toFixed(2)}px;height:${r.h.toFixed(2)}px;border-radius:${rad.toFixed(2)}px;box-sizing:border-box;${css}`);
          [kA, kB].forEach((k, i) => { if (ops[i] > 0.002) Object.assign(box(`opacity:${ops[i].toFixed(3)}`).style, k); });
          const clip = box("overflow:hidden");
          [A, B].forEach((src, i) => {
            if (ops[i] <= 0.002) return;
            const c = src.cloneNode(true), w0 = src.offsetWidth || 1, h0 = src.offsetHeight || 1, s = Math.min(r.w / w0, r.h / h0);
            c.querySelectorAll("video").forEach((v) => v.remove());
            Object.assign(c.style, { position: "absolute", left: "0px", top: "0px", margin: "0", visibility: "visible", clipPath: "none", filter: "none", transformOrigin: "0 0",
              background: "transparent", boxShadow: "none", borderColor: "transparent",               // (its skin is the box's)
              opacity: ops[i].toFixed(3), transform: `translate(${((r.w - w0 * s) / 2).toFixed(2)}px,${((r.h - h0 * s) / 2).toFixed(2)}px) scale(${s.toFixed(5)})` });
            clip.append(c);
          });
        });
        if (x.sfx !== false) K.sfx(SND.match[0], t + 0.08, SND.match[1]);
        if (x.log !== false) logIt(t, "match", x.why || "match cut");
      },
      // zoom through the outgoing anchor into a white chapter beat (2-4 words, 1.2-2.2 s)
      chapter(t0, t1, x = {}) {
        // only t0 moves to the downbeat (within 0.12 s: the hit lands on it); t1 stays where the template put it, so the
        // template's shot at t1 is still his return (review 2026-10-22: moving both by the snap dropped that shot when the
        // snap went later, and flashed his old shape for 2-3 frames when it went earlier). The hold changes by the snap
        // (and never onto another takeover: a snap that would overlap one keeps t0, claim throws on a real overlap)
        if (x.beat !== false && HF.music) { const s = HF.music.snap(t0, { kind: "downbeat", early: 0.12, late: 0.12 }), sp = canvas ? H._tk : boxed ? BOXTK.get(H) : null;
          if (!overlap(sp, s, t1) || overlap(sp, t0, t1)) t0 = s; }
        const n = String(x.title || "").split(/\s+/).filter(Boolean).length;
        if (n < 2 || n > 4) console.warn(`T.chapter at ${t0.toFixed(2)}: "${x.title}" is ${n} words (2-4)`);
        if (t1 - t0 < 1.2 - 1e-6 || t1 - t0 > 2.2 + 1e-6) console.warn(`T.chapter at ${t0.toFixed(2)}: held ${(t1 - t0).toFixed(2)} s (1.2-2.2)`);
        const common = { kind: "chapter", num: x.num, title: x.title, kicker: x.kicker, plate: x.plate || "#FFFFFF", paper: x.plate || "#FFFFFF", sfx: false, log: false, push: 0.03 };
        let tk;
        if (canvas) tk = H.takeover(t0, t1, Object.assign(common, { in: "zoom", eyes: x.eyes !== false, from: x.from, out: x.to ? "zoom" : "cut", into: x.to ? "line" : undefined, to: x.to }));
        else if (boxed) tk = H.takeover(t0, t1, Object.assign(common, { in: "zoom", out: x.to === false ? "cut" : "fade" }));
        else throw new Error("T.chapter: on a canvas (HF.canvas) or HF.studio / HF.reel");
        // one soft whoosh into it and a low hit as it lands (-17..-19 dB: a mark, not a drop)
        K.sfx("whoosh/whoosh__air-woosh__mixkit-1489", t0 - 0.15, x.whooshDb != null ? x.whooshDb : -19);
        K.sfx("impact/impact__short-bass-hit__mixkit-2299", t0, x.hitDb != null ? x.hitDb : -18, true);
        logIt(t0, "chapter", x.why || `chapter ${x.num != null ? x.num + " " : ""}${x.title || ""}`.trim());
        if (canvas && x.to) logIt(t1, "zoom", "out of the chapter beat");
        return tk;
      },
      // his card morphs into el's frame (el is then the graphic); x.until: his card grows back out of x.back (or el)
      cardToGraphic(t, el, x = {}) {
        if (!canvas) throw new Error("T.cardToGraphic: on a canvas (HF.studio / HF.reel: beat(t, \"graphic\", { card: true }) + S.fromPill)");
        t = Q(t);
        const dur = x.dur || IN.card, back = x.back || el;
        if (x.until != null) claim(H._tk, t, Q(x.until), "T.cardToGraphic");
        hideWhile(K, el, (u) => u < t + dur - 1e-6);
        if (x.until != null) hideWhile(K, back, (u) => u >= x.until - 1e-6);
        // primary: only his own card takes part (a screen recording beside him stays as it is: the frame is not taken over)
        H._tk.push({ a: t, off: t + dur, on: x.until != null ? Q(x.until) : null, into: el, from: x.until != null ? back : null, fromDur: x.backDur || OUT.card, fadeIn: 0, fadeOut: 0, kind: "card", primary: true });
        H._replan();
        if (x.sfx !== false) K.sfx(SND.card[0], t + 0.1, SND.card[1]);
        // the morph and its return are one bracket (fold): "card" there and back counts once in the budget
        if (x.log !== false) { const pr = ++pairs; logIt(t, "card", x.why || "his card becomes the graphic", pr); if (x.until != null) logIt(x.until, "card", "his card grows back out of the graphic", pr); }
      },
      whip(t, to, x = {}) {
        if (!canvas) throw new Error("T.whip: on a canvas");
        const v = Array.isArray(to) ? { x: to[0], y: to[1], z: to[2] || 1 } : to;
        H.cam(t, v, Object.assign({ dur: 0.55, ease: "expo.inOut" }, x, { log: false }));
        logIt(t, "whip", x.why || "whip");
      },
      cut(t, to, x = {}) {
        if (canvas && to != null) CV.cut(Q(t), to);
        logIt(Q(t), "cut", x.why || "cut");
      },
    };
    return T;
  };
  const takeoverOf = (el) => { for (let e = el; e; e = e.parentElement) if (e.dataset && e.dataset.takeover && e.__tk) return e.__tk; return null; };
  const centreIn = (el, tk) => { const r = localIn(el, tk.L); return { x: r.x + r.w / 2, y: r.y + r.h / 2 }; };
  const overlay = (K, H) => {
    if (overlay.el && overlay.el.isConnected) return overlay.el;
    const rootEl = (H && (H.root || (H.FRONT && H.FRONT.parentNode))) || document.querySelector("[data-composition-id]");
    overlay.el = K.el(rootEl, `left:0;top:0;width:${K.width}px;height:${K.height}px;z-index:9;pointer-events:none;overflow:hidden`);
    overlay.el.dataset.decor = "1";
    return overlay.el;
  };
  // the canvas half: zoom about a page point (ZM) into an element / his eyes; land a canvas camera from 3x; a hard cut
  HF.trans._canvas = function (K, C) {
    const Q = K.Q, fps = K.fps || 30, WD = K.width, HT = K.height;
    const cut = (t, to) => { const v = Array.isArray(to) ? { x: to[0], y: to[1], z: to[2] || 1 } : to.nodeType ? stationCentre(to) : to;
      C.cam(t - 1 / fps, v, { dur: 0.01, sfx: false, beat: false, log: false, cut: true }); };
    const stationCentre = (st) => { const L = st.parentNode, r = { x: st.offsetLeft + st.offsetWidth / 2, y: st.offsetTop + st.offsetHeight / 2 };
      const n = Object.keys(C.layers).find((k) => C.layers[k] === L) || "mid", p = { bg: 0.2, far: 0.75, mid: 1, spk: 1, near: 1.2 }[n] || 1;
      const c0 = C.c0 || { x: C.CW / 2, y: C.CH / 2 };
      return { x: c0.x + (r.x - c0.x) / p, y: c0.y + (r.y - c0.y) / p, z: 1 }; };
    // the point the zoom dives into, at the zoom's start: an element's centre, or his face (his shape >= 500 px; else
    // fallback: an element, or the frame's centre)
    const pointOf = (what, t, fallback) => () => {
      if (what === "eyes") {
        const s = typeof root.__speaker === "function" ? root.__speaker(t) : null;
        if (s && s.on && s.face && s.rect && Math.min(s.rect.w, s.rect.h) >= 500) return [s.face.x + s.face.w / 2, s.face.y + s.face.h * 0.45];
        return fallback ? pointOf(fallback, t)() : [WD / 2, HT / 2];
      }
      if (Array.isArray(what)) return what;
      const r = rectAt(what, t); return [r.x + r.w / 2, r.y + r.h / 2];
    };
    return {
      cut,
      zoomIn(t, what, x = {}) {
        t = Q(t);
        C._zoom({ t0: t - ZIN, t1: t, k0: 1, k1: PEAK, ease: "expo.in", pt: pointOf(what, t - ZIN, x.fallback), why: "zoom in" });
        if (x.sfx !== false) K.sfx(SND.zoom[0], t - 0.1, SND.zoom[1]);
      },
      // after a peak at t: the canvas camera cuts to `to` and arrives from 3x about the frame's centre (or x.at)
      land(t, to, x = {}) {
        t = Q(t);
        if (to != null) cut(t, to);
        C._zoom({ t0: t, t1: t + ZOUT, k0: PEAK, k1: 1, ease: "expo.out", pt: () => x.at || [WD / 2, HT / 2], why: "zoom out" });
      },
      // out of a takeover: its camera dives into `into` (scene px), then the canvas lands on `to` from 3x
      zoomOut(b, tk, into, to, x = {}) {
        if (!into) throw new Error("C.takeover out \"zoom\": nothing to zoom into (pass into: el)");
        tk.cam.cam(b - ZIN, Object.assign(centreIn(into, tk), { z: PEAK }), { dur: ZIN, ease: "expo.in" });
        this.land(b, to, x);
        if (x.sfx !== false) K.sfx(SND.zoom[0], b - 0.1, SND.zoom[1]);
      },
    };
  };

  // ================================================================== HF.camera pages publish window.__speaker
  // HF.camera (scenes.js: the A-roll full frame with layouts W / M / C / SR / SL / PIP / OFF) predates the contract; this
  // wrapper adds it without changing what the page draws: { on, kind (full; card for a side panel; corner for PIP; off),
  // rect (the visible A-roll), face (the piece's face through the camera), zoom (over cover), lens (push / punch / "") }.
  // A page whose other engine already published window.__speaker keeps that one.
  if (HF.camera && !HF.camera.__speaker) {
    const cam0 = HF.camera;
    HF.camera = function (K, st) {
      const P = cam0.apply(this, arguments);
      if (typeof root.__speaker !== "function" && HF.motion && HF.motion.at) root.__speaker = HF.trans.cameraSpeaker(K, st, P);
      return P;
    };
    Object.assign(HF.camera, cam0, { __speaker: true });
  }
  HF.trans.cameraSpeaker = (K, st, P) => (t) => {
    const W = K.width, H = K.height, c = HF.motion.at(P, t), [SW, SH] = P.src || [W, H], m = c.m;
    if (c.layout === "OFF") return { on: false, kind: "off", rect: null, face: null, zoom: null, lens: "" };
    const top = P.mode === "panel" ? c.top || 0 : 0, cl = c.clip || [0, 0, 0, 0, 0];
    const p = (x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5] + top];
    const A = p(cl[3], cl[0]), B = p(SW - cl[1], SH - cl[2]);
    const view = c.view || P.view || [W, H];
    const x0 = Math.max(0, A[0]), y0 = Math.max(top, A[1]), x1 = Math.min(view[0], B[0]), y1 = Math.min(top + view[1], B[1]);
    const rect = { x: x0, y: y0, w: Math.max(0, x1 - x0), h: Math.max(0, y1 - y0) }, area = (rect.w * rect.h) / (W * H);
    const kind = area > 0.9 ? "full" : c.layout === "PIP" || area < 0.1 ? "corner" : "card";
    let face = null;
    if (c.face) { const [fx, fy, fz] = c.face, q = p(fx, fy), hw = ((fz || 300) * Math.hypot(m[0], m[1])) / 2;
      const fx0 = Math.max(rect.x, q[0] - hw), fx1 = Math.min(rect.x + rect.w, q[0] + hw), fy0 = Math.max(rect.y, q[1] - hw * 1.35), fy1 = Math.min(rect.y + rect.h, q[1] + hw * 1.15);
      if (fx1 > fx0 + 1 && fy1 > fy0 + 1) face = { x: fx0, y: fy0, w: fx1 - fx0, h: fy1 - fy0 }; }
    const s = Math.hypot(m[0], m[1]), cover = Math.max(view[0] / SW, view[1] / SH);
    // HF.camera declares no holds: an idle or drifting frame is "" so precheck judges its framing (a "hold" here exempted
    // every HF.camera page from the dynamic-zoom gate, review 2026-10-22); a zoomx or a layout change is a transition
    const lens = c.move === "push" ? "push" : c.move === "punch" || c.move === "ease" || c.move === "snap" ? "punch" : "";
    return { on: true, kind, rect, face, zoom: +(s / cover).toFixed(4), lens };
  };

  HF.trans.KINDS = KINDS; HF.trans.BUDGET = BUDGET;
  HF.trans.check = check; HF.trans.pick = pick; HF.trans.log = logIt; HF.trans.list = list; HF.trans.fold = fold;
  HF.trans.overlap = overlap; HF.trans.claim = claim; HF.takeover.typeFit = typeFit;
  HF.trans.source = (f) => SOURCES.push(f);
  HF.trans.rectAt = rectAt; HF.trans.localIn = localIn; HF.trans.hideWhile = hideWhile; HF.trans.camera = camera; HF.trans.lookOf = lookOf;
  HF.trans._reset = () => { LOG.length = 0; SOURCES.length = 0; pairs = 0; };   // tests
  root.__trans = list;
})(typeof window !== "undefined" ? window : globalThis);
