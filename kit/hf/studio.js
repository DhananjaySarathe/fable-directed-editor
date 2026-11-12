/*
 * kit/hf/studio.js: the pastel-box film kit (kit/presets/pastel_box/README.md). One call sets up a film's whole frame
 * so a film's template is only its scenes:
 *
 *   const S = HF.studio(K, ROOT, st, { end: D.total, talk: D.talk, sections: [[t, "01 / label"]...],
 *                                      chrome: { left: "yourchannel · my video '26", footer: "edited by claude · html · gsap" } });
 *   const { C, Q, W, E, el, say, line, strike, layer, land, leave, card, chip, mono, beat, chapter, ui } = S;
 *   beat(0, "hero"); { const L = layer(0, W(11)); say(L, 1, 5, { x: 110, y: 800 }); }  ...
 *   S.focus(L, card, { at: W(40), until: W(52), line: row });   S.scoreboard(L, x, y, w, { rows });   S.quiet(a, b)
 *   S.endCard();   // handles default to HF.HANDLES (kit/brand.json); pass { handles: [...] } only to override
 *   S.box({ flips: { tag: () => el }, jumps: [266, 2474] });  K.finish(D.total);
 *
 * The world: one pastel aurora (lavender, peach, mint, butter), fine grain, editorial chrome (corner labels, section,
 * timecode, progress bar). The speaker is HF.box (kit/hf/box.js): beats -> the director's moves.
 * { look: "whitespace" } (2026-10-22, HF.studioLook): the same frame on a plain white page in that look's tokens.
 * Layers: WORLD z0, grain z1, BACK z3 (graphics beside / instead of the box), the box z4, FRONT z6 (type over the
 * face, stamps, pointers), CHAP z12 (chapter cards), CHROME z14.
 *
 * Every rule here cost a 4K render on films/ai-workflows (2026-10-10); keep them:
 *   - say()/line(): an exit cuts a still-running rise short. A rise that finished after its exit pinned the word on
 *     screen, in the frame-by-frame renderer only (snapshots and direct seeks looked right).
 *   - words are hidden before they rise and after they leave: a 34 px text-shadow on words parked outside their masks
 *     bled back in as faint smears that piled up on FRONT.
 *   - layer(): a held scene sways (+-6 px) and pushes (0.4 %/s, cap 3 %), the reference's numbers. Until 2026-10-10 it
 *     floated +-14 px and pushed to 7 % only to keep qa.py's freezedetect quiet; a reading hold is now declared instead
 *     (layer(a, b, par, { read: true }) or S.hold), and qa.py --holds accepts it. The aurora still orbits.
 *   - chapter cards drift while they hold; the next scene's first element lands as the card leaves (no blank world).
 *   - the chrome turns white only over a visible full-frame box (box.rect().op), never over the pastel world.
 *   - S.box(jumps): a hard 1.12x punch on pause trims inside one held full frame hides the jump cut. The box's own
 *     drift reaches 3 %, so the punch nets about 9 %. Skip a cut where a scribble outline is traced at full frame.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit || !HF.box) throw new Error("kit/hf/studio.js needs core.js and box.js first");

  const CSS = `
    .ui { font-family: var(--f-body); color: var(--ink); }
    .sv { font-family: var(--f-display); font-weight: var(--w-display); letter-spacing: var(--t-display); line-height: 1.0; white-space: nowrap; }
    .mono { font-family: var(--f-mono); }
    .card { position: absolute; border-radius: 28px; background: var(--card); overflow: hidden;
      box-shadow: var(--shadow); }
    .tbar { position: absolute; left: 0; top: 0; right: 0; height: 50px; display: flex; align-items: center; gap: 10px; padding: 0 20px;
      background: var(--sunk); border-bottom: 1px solid var(--line); font: 700 21px/1 var(--f-body); color: var(--text); }
    .tbar i { width: 12px; height: 12px; border-radius: 50%; background: #dad5cf; display: inline-block; }
    .tbar b { margin-left: 10px; }
    .pill { display: inline-flex; align-items: center; gap: 9px; padding: 8px 16px; border-radius: 999px; font: 700 20px/1 var(--f-body); white-space: nowrap; }
    .chip { position: absolute; display: inline-flex; align-items: center; gap: 12px; padding: 14px 22px; border-radius: 18px; background: var(--card);
      font: 700 26px/1 var(--f-body); color: var(--ink); white-space: nowrap; box-shadow: var(--shadow-soft); }
    .lbl { font: 600 16px/1 var(--f-mono); letter-spacing: 0.16em; text-transform: uppercase; color: var(--sub); white-space: nowrap; }
    .av { width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: #fff; font: 800 18px/1 var(--f-body); flex: none; }
    .who { font: 800 23px/1 var(--f-body); color: var(--ink); }
    .who small { font: 500 17px/1 var(--f-body); color: var(--mute); margin-left: 10px; }
    .txt { font: 500 25px/1.3 var(--f-body); color: var(--text); margin-top: 7px; }
    .mention { background: var(--acc-tint); color: var(--acc); border-radius: 6px; padding: 0 5px; font-weight: 700; }
    .orb { position: absolute; border-radius: 50%;
      background: radial-gradient(circle at 34% 30%, #ffffff 0%, #ffe3d3 16%, #ff9a5c 46%, #e2562b 78%, #b8401c 100%);
      box-shadow: 0 0 26px 6px rgba(255, 122, 61, 0.5), 0 0 70px 18px rgba(226, 86, 43, 0.22); }
    .orbi { position: relative; display: inline-block; border-radius: 50%; flex: none;
      background: radial-gradient(circle at 34% 30%, #ffffff 0%, #ffe3d3 16%, #ff9a5c 46%, #e2562b 78%, #b8401c 100%); }
    .cell { position: absolute; top: 0; height: 100%; display: flex; align-items: center; font: 500 22px/1 var(--f-body); color: var(--text); white-space: nowrap; }
    .strike { position: absolute; height: 7px; border-radius: 4px; background: var(--acc); transform-origin: 0 50%; }`;

  // the palette (preset.json "palette"); a film may override any key with o.palette
  const PALETTE = { ink: "#17161f", ink2: "#4d4b5c", mute: "#8e8ba0", acc: "#4f3be0", accTint: "#ece9ff", orb: "#ff7a3d",
    ok: "#16a34a", okSoft: "#dcf5e5", bad: "#d6455d", warm: "#e2562b", onVideo: "#ffc9ad", paper: "#f6f1ec",
    aurora: ["rgba(176,160,255,.85)", "rgba(255,190,160,.85)", "rgba(170,232,205,.75)", "rgba(255,226,170,.55)"] };
  // o.look (2026-10-22): HF.studio / HF.reel { look: "whitespace" } builds the same frame in another look. The frame's own
  // colours (S.C) come from that look's tokens instead of PALETTE, and its world is plain: the look's stage seamless
  // (core.js HF.LOOKS[look].stage) or its paper, with no aurora and no grain (both belong to pastel_box). Chapter cards,
  // the chrome, fromPill and the end card take the look's ink, lines and accent; his box gets a lighter shadow. The
  // default (no o.look, or "pastel_box") builds exactly what it built before. HF.reel reads the same helpers.
  HF.studioLook = (name) => {
    const L = HF.LOOKS[name];
    if (!L) throw new Error("HF.studio: unknown look " + name + " (one of " + Object.keys(HF.LOOKS).join(", ") + ")");
    const c = L.C, pastel = name === "pastel_box", stage = L.stage || null;
    return { name, pastel, stage,
      C: pastel ? {} : { ink: c.ink, ink2: c.ink2, mute: c.mute, acc: c.acc, accTint: c.accTint, ok: c.ok, okSoft: c.okTint, bad: c.bad, warm: c.warm,
        onVideo: c.onVideo, paper: c.paper, aurora: [] },
      world: pastel ? null : (stage ? stage.seamless : c.paper), edge: pastel ? null : (stage ? stage.edge : c.paper),
      chrome: pastel ? "rgba(60,56,90,.62)" : c.sub,                       // the corner labels over the world
      // a stressed word: italic in the accent in pastel_box's serif; upright in the accent in a sans look (Inter ships
      // no italic, and a synthetic slant read cheap on the white page: the colour is the one mark)
      stress: pastel || /Serif/.test(L.F.display) ? "italic" : "normal",
      boxShadow: pastel ? null : [0, 24, 64, 0.16] };                      // HF.box look.shadow: softer on a light plain world
  };

  // ======================================================================================================================
  // HF.parts(K, ROOT, { front, back, z }): the frame-independent pieces of the pastel-box kit, for any frame (2026-10-20,
  // kit/refs/AUDIT_2026-10-20.md §6). HF.studio builds its helpers from it, and a frame with no S (HF.canvas) gets the same
  // UI cards and evidence: P.ui.* (studio_ui.js), P.focus / P.scoreboard / P.flow / P.hold / P.quiet (evidence.js),
  // layer / land / leave / card / chip / mono / icon / tick / pop / arrow ... All of it reads the look's tokens (HF.look),
  // so it takes canvas, redline or night colours and type. front: the over-everything layer (default: a new one at z).
  HF.parts = function (K, ROOT, o = {}) {
    const tl = K.tl, Q = K.Q, E = HF.E, el = K.el, f1 = 1 / (K.fps || 30), WD = K.width, HT = K.height;
    if (!document.getElementById("hf-studio-css")) { const s = document.createElement("style"); s.id = "hf-studio-css"; s.textContent = CSS; document.head.append(s); }
    const FRONT = o.front || el(ROOT, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:${o.z || 7};pointer-events:none`);
    const BACK = o.back || FRONT;
    // ---------------------------------------------------------------- small helpers
    // a scene's graphics. Motion follows the reference (kit/refs/MOTION.md §2): a held scene sways a little (+-6 px, the
    // reference's +-0.6 % of the height) and pushes slowly (0.4 %/s, at most 3 %). x.read: a scene the viewer reads (code,
    // a long answer, a table) holds still and is declared a reading hold (qa.py --holds), so nothing moves just to pass a
    // freeze check. x.float / x.push override. It fades out over its last 0.16 s (x.fade; 0 = a hard end).
    // L._F is the focus wrapper (S.focus zooms it; the layer's own sway and push stay).
    const layer = (a, b, par = BACK, x = {}) => {
      const fl = el(par, `left:0;top:0;width:${WD}px;height:${HT}px`); K.show(fl, a - 0.02, b); fl._win = [a - 0.02, b];
      const fade = x.fade != null ? x.fade : 0.16;
      if (fade > 0 && b - a > fade * 3) tl.to(fl, { opacity: 0, duration: fade, ease: "none", immediateRender: false }, Q(b - fade));
      const ph = a * 0.37, amp = x.read ? 0 : x.float != null ? x.float : 6;
      if (amp) K.onFrame((t) => { if (t > a - 0.1 && t < b + 0.1) fl.style.transform = `translate(${(amp * Math.sin(t * 0.66 + ph)).toFixed(2)}px,${(amp * 0.65 * Math.cos(t * 0.53 + ph)).toFixed(2)}px)`; });
      const F = el(fl, `left:0;top:0;width:${WD}px;height:${HT}px`);
      const L = el(F, `left:0;top:0;width:${WD}px;height:${HT}px;transform-origin:50% 50%`), d = Math.max(0.3, b - a);
      const push = x.read ? 0 : x.push != null ? x.push : 0.004;
      if (push) tl.fromTo(L, { scale: 1 }, { scale: 1 + Math.min(0.03, push * d), duration: d, ease: "none", immediateRender: false }, Q(a));
      if (x.read) HF.hold(a + 0.6, b, typeof x.read === "string" ? x.read : "read");
      L._F = F;
      return L;
    };
    const land = (e, t, x = {}) => HF.land(K, e, t, { spring: x.spring || "ui", from: x.from || { y: 34, scale: 0.95, blur: 10 },
      sfx: x.sfx === undefined ? "pop" : x.sfx, sfxDb: x.db != null ? x.db : -26 });
    const leave = (e, t, x = {}) => HF.leave(K, e, t, x);
    const card = (par, x, y, w, h, html = "", style = "") => el(par, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;${style}`, html, "card ui");
    const chip = (par, x, y, html, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, html, "chip ui");
    const mono = (par, x, y, text, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, text, "hf-abs lbl");
    const orbI = (d) => `<span class="orbi" style="width:${d}px;height:${d}px"></span>`;
    const dot = (c, d = 28) => `<span style="width:${d}px;height:${d}px;border-radius:50%;background:${c};display:inline-block;flex:none"></span>`;
    const orbAt = (par, x, y, d = 46) => {
      const ob = el(par, `left:${x - d / 2}px;top:${y - d / 2}px;width:${d}px;height:${d}px`, "", "orb");
      K.onFrame((t) => { ob.style.transform = `scale(${(1 + 0.05 * Math.sin(t * 5.2)).toFixed(4)})`; });
      return ob;
    };
    const icon = (n, s = 30, c = HF.C.ink, w = 2.2) => HF.icon(n, s, c, w);
    const tick = (s = 22, c = HF.C.onFill || "#fff") => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 12.5l5 5 10-11"/></svg>`;
    const grow = (e, t, dur = 0.42) => tl.fromTo(e, { scaleX: 0 }, { scaleX: 1, duration: dur, ease: E.in, immediateRender: true }, Q(t));
    const growY = (e, t, dur = 0.42) => tl.fromTo(e, { scaleY: 0 }, { scaleY: 1, duration: dur, ease: E.in, immediateRender: true }, Q(t));
    const pop = (e, t) => tl.fromTo(e, { scale: 0 }, { scale: 1, duration: 0.35, ease: HF.spring(HF.SPRING.thrown).ease, immediateRender: true }, Q(t));
    const fadeOut = (e, t, d = 0.2) => tl.to(e, { opacity: 0, duration: d, immediateRender: false }, Q(t));
    const arrow = (par, x0, y0, x1, col = HF.C.acc) => {
      const a = el(par, `left:${x0}px;top:${y0 - 3}px;width:${x1 - x0}px;height:6px;border-radius:3px;background:${col};transform-origin:0 50%`);
      el(a, `right:-5px;top:-8px;width:0;height:0;border-left:16px solid ${col};border-top:11px solid transparent;border-bottom:11px solid transparent`);
      return a;
    };
    const svgLayer = (L) => { const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      s.setAttribute("width", WD); s.setAttribute("height", HT); s.setAttribute("viewBox", `0 0 ${WD} ${HT}`); s.style.cssText = "position:absolute;left:0;top:0;overflow:visible"; L.append(s); return s; };
    const P = { K, tl, Q, W: K.W, E, el, f1, C: HF.C, FRONT, BACK, layer, land, leave, card, chip, mono, orbI, dot, orbAt, icon, tick, grow, growY, pop,
      fadeOut, arrow, svgLayer };
    P.focus = (L, target, x = {}) => HF.focus(K, L, target, x);
    P.scoreboard = (par, x, y, w, so = {}) => HF.scoreboard(P, par, x, y, w, so);
    P.flow = (par, fo = {}) => HF.flow(P, par, fo);
    P.hold = HF.hold; P.quiet = HF.quiet;
    P.ui = HF.studioUI ? HF.studioUI(P) : {};
    return P;
  };

  HF.studio = function (K, ROOT, st, o = {}) {
    const tl = K.tl, Q = K.Q, W = K.W, E = HF.E, el = K.el, f1 = 1 / (K.fps || 30);
    const LK = HF.studioLook(o.look || "pastel_box");                         // o.look: the frame's look (HF.studioLook above)
    const C = Object.assign({}, PALETTE, LK.C, o.palette || {});
    const END = o.end, TALK = o.talk != null ? o.talk : o.end;
    if (END == null) throw new Error("HF.studio: pass { end: D.total }");
    if (!document.getElementById("hf-studio-css")) { const s = document.createElement("style"); s.id = "hf-studio-css"; s.textContent = CSS; document.head.append(s); }
    ROOT.querySelectorAll(".hf-paper,.hf-grain").forEach((e) => (e.style.display = "none"));
    HF.handFont();
    HF.look(LK.name, HF.lookOver(o.palette));                                 // every kit component takes this look's tokens
    ROOT.style.background = LK.pastel ? C.paper : LK.edge;
    const PILL = { cx: 960, cy: 540, w: 1920 * 0.14, h: 1080 * 0.085 };     // where a collapse lands (HF.box SLOTS pill)
    const landOfCollapse = (t) => t - 0.04 + HF.box.MOVES.collapse.dur;      // the director starts a collapse 0.04 s early

    // ---------------------------------------------------------------- the world: one pastel aurora, never still
    // (another look: its plain world, no aurora and no grain)
    const WORLD = el(ROOT, `left:0;top:0;width:1920px;height:1080px;z-index:0;background:${LK.pastel ? C.paper : LK.world};overflow:hidden`);
    if (LK.pastel) {
      const blob = (c, s) => el(WORLD, `left:0;top:0;width:${s}px;height:${s}px;border-radius:50%;background:radial-gradient(circle, ${c} 0%, rgba(255,255,255,0) 66%)`);
      const BL = [blob(C.aurora[0], 1500), blob(C.aurora[1], 1400), blob(C.aurora[2], 1300), blob(C.aurora[3], 1100)];
      const ORBIT = [[260, 160, 160, 90, 0.175, 0, 1500], [1700, 340, 140, 120, 0.15, 2, 1400], [600, 1080, 220, 70, 0.125, 4, 1300], [1450, 1000, 160, 90, 0.2, 1, 1100]];
      K.onFrame((t) => BL.forEach((b, i) => { const [cx, cy, ax, ay, w, ph, s] = ORBIT[i];
        b.style.transform = `translate(${(cx + ax * Math.sin(t * w + ph) - s / 2).toFixed(1)}px,${(cy + ay * Math.cos(t * w * 0.8 + ph) - s / 2).toFixed(1)}px)`; }));
      el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:1;opacity:.05;pointer-events:none;background-image:radial-gradient(rgba(0,0,0,.6) 1px, rgba(0,0,0,0) 1.4px);background-size:5px 5px");
    }
    st.cam.style.zIndex = "4";
    const BACK = el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:3");
    const FRONT = el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:6");
    const CHAP = el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:12");
    const CHROME = el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:14;pointer-events:none");
    CHROME.dataset.decor = "1";                                              // corner labels: decoration, not evidence (precheck)

    // ---------------------------------------------------------------- small helpers (HF.parts: the same pieces for every frame)
    const { layer, land, leave, card, chip, mono, orbI, dot, orbAt, icon, tick, grow, growY, pop, fadeOut, arrow, svgLayer } = HF.parts(K, ROOT, { front: FRONT, back: BACK });

    // ---------------------------------------------------------------- type: words rising in masks
    // a word rises in its mask from a; it is hidden before and after, so its shadow never bleeds into the mask
    const rise = (s, a) => { s.style.visibility = "hidden"; tl.set(s, { visibility: "visible" }, Q(a)); s._a = Q(a);
      const rw = gsap.fromTo(s, { yPercent: 112 }, { yPercent: 0, duration: 0.5, ease: E.in, immediateRender: true }); tl.add(rw, Q(a)); return [rw, Q(a)]; };
    // the words leave upward from t; a rise still running is cut short first (finishing after the exit, it pinned the word back)
    const wordsOut = (items, rises, t) => { items.forEach((s, k) => { const at = Q(t + k * 0.012), [rw, a] = rises[k];
        if (a + rw.duration() > at - 0.02) rw.duration(Math.max(f1, at - 0.02 - a));
        tl.to(s, { yPercent: -112, duration: 0.24, ease: E.out, immediateRender: false }, at);
        s._h = Q(Math.max(at + 0.27, a + f1)); tl.set(s, { visibility: "hidden" }, s._h); }); return t + 0.3; };
    const mask = () => { const m = document.createElement("span"); m.style.cssText = "display:inline-block;overflow:hidden;vertical-align:top;padding:0 0.04em 0.12em"; return m; };
    // the cut's words (from..to ids) on their spoken time (minus a frame); stressed ids italic in the accent.
    // o: x, y, w, size, color, align, lh, shadow (white type over video), stress [ids], br [ids to break before], accent
    function say(par, from, to, x = {}) {
      const ws = K.words_.filter((w) => w.i >= from && w.i <= to && w.text);
      const box = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;width:${x.w || 1700}px;font-size:${x.size || 110}px;color:${x.color || C.ink};text-align:${x.align || "left"};` +
        `line-height:${x.lh || 1.04};white-space:normal;${x.shadow ? "text-shadow:0 6px 34px rgba(0,0,0,.42),0 2px 6px rgba(0,0,0,.3);" : ""}`, "", "hf-abs sv");
      const stress = new Set(x.stress || []), brk = new Set(x.br || []), items = [], rises = [];
      if (x.stress) STRESS.push(...x.stress);                                // the lens's punch tags (S.box, 2026-10-22)
      ws.forEach((w) => {
        if (brk.has(w.i)) box.append(document.createElement("br"));
        const m = mask(), s = document.createElement("span"); s.style.display = "inline-block";
        s.textContent = String(w.text).replace(/,$/, ""); s.dataset.w = w.i;             // captions skip words already on screen
        if (stress.has(w.i)) { s.style.fontStyle = LK.stress; s.style.color = x.accent || (x.color === "#fff" ? C.onVideo : C.acc); }
        m.append(s); box.append(m); box.append(document.createTextNode(" "));
        rises.push(rise(s, Math.max(0.01, w.t - f1))); items.push(s);
      });
      return { box, items, t0: ws.length ? ws[0].t : null, out: (t) => wordsOut(items, rises, t) };
    }
    // a line that isn't spoken word for word (titles, labels): "|" breaks a line; "*word" or "*several words*" is the accent
    // (the same syntax as HF.kinetic: a trailing "*" closes the span and is never printed); rises from t0
    function line(par, text, t0, x = {}) {
      const box = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;width:${x.w || 1700}px;font-size:${x.size || 90}px;color:${x.color || C.ink};text-align:${x.align || "left"};line-height:${x.lh || 1.04};white-space:normal;${x.shadow ? "text-shadow:0 6px 34px rgba(0,0,0,.42);" : ""}`, "", "hf-abs sv");
      const items = [];
      text.split("|").forEach((ln, li) => {
        if (li) box.append(document.createElement("br"));
        HF.accentTokens(ln).forEach(({ text: tx, accent }) => {
          const m = mask(), s = document.createElement("span"); s.style.display = "inline-block"; s.textContent = tx;
          if (accent) { s.style.fontStyle = LK.stress; s.style.color = x.accent || C.acc; }
          m.append(s); box.append(m); box.append(document.createTextNode(" ")); items.push(s);
        });
      });
      const rises = items.map((s, k) => rise(s, t0 + k * (x.per || 0.06)));
      return { box, items, out: (t) => wordsOut(items, rises, t) };
    }
    // a strike-through drawn across, then the struck text dims (the reference's "noob-level"). until: when it leaves. Draw
    // it inside a layer() (it leaves with the layer) or pass until: on FRONT it otherwise stays up for the rest of the film
    // (films/xchakra draft 2: two red lines for 4 minutes; precheck now flags that as "linger")
    function strike(par, x, y, w, t, target, col = C.acc, until = null) {
      const s = el(par, `left:${x}px;top:${y}px;width:${w}px;background:${col}`, "", "hf-abs strike");
      tl.fromTo(s, { scaleX: 0 }, { scaleX: 1, duration: 0.32, ease: E.in, immediateRender: true }, Q(t));
      if (until != null) tl.to(s, { opacity: 0, duration: 0.15, immediateRender: false }, Q(until));
      if (target) tl.to(target, { opacity: 0.38, duration: 0.25, immediateRender: false }, Q(t + 0.12));
      K.sfx("click", t, -24);
      return s;
    }
    // a white card that grows out of the collapsed pill (the box's signature hand-off: beat(t, "graphic", { card: true }))
    function fromPill(L, t, x, y, w, h, bg = LK.pastel ? "rgba(255,255,255,.72)" : HF.C.card) {
      const c = el(L, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;border-radius:30px;background:${bg};box-shadow:${LK.pastel ? "0 40px 90px rgba(40,24,90,.13)" : HF.C.e2}`);
      HF.box.morph(K, c, PILL, { x, y, w, h }, landOfCollapse(t), 0.32, { fromBg: C.acc, bg });
      return c;
    }

    // ---------------------------------------------------------------- chrome: corner labels, section, timecode, progress
    const SECTIONS = (o.sections && o.sections.length ? o.sections : [[0, ""]]).slice().sort((a, b) => a[0] - b[0]);
    const ch = (x, y, al) => el(CHROME, `left:${x}px;top:${y}px;${al ? "width:600px;text-align:right;" : ""}font:600 15px/1 JBMono,monospace;letter-spacing:.16em;text-transform:uppercase;white-space:nowrap`);
    const cTL = ch(44, 34), cTR = ch(1276, 34, true), cBL = ch(44, 1036), cBR = ch(1276, 1036, true);
    const chrome = o.chrome || {};
    cTL.textContent = chrome.left || ""; cBL.textContent = chrome.footer != null ? chrome.footer : "edited by claude · html · gsap";
    const bar = el(CHROME, `left:0;top:1074px;width:1920px;height:6px;background:${C.acc};transform-origin:0 50%;opacity:.85`);
    const tc = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
    let boxRef = null;
    // a film rendered in parts (one composition per chapter): chrome.t0 = where this part starts in the film and
    // chrome.total = the whole film's length, so the timecode and the progress bar run across the joins
    const T0 = chrome.t0 || 0, TOT = chrome.total || END;
    K.onFrame((t) => {
      bar.style.transform = `scaleX(${((t + T0) / TOT).toFixed(5)})`;
      cBR.textContent = `${tc(t + T0)} / ${tc(TOT)}${chrome.badge === false ? "" : " · " + (chrome.badge || "4k")}`;
      cTR.textContent = (SECTIONS.filter((s) => s[0] <= t + 1e-6).pop() || SECTIONS[0])[1];
      const r = boxRef ? boxRef.rect(t) : null, onVideo = r && r.w > 1700 && r.op > 0.5;   // white only over a visible full-frame box
      const col = onVideo ? "rgba(255,255,255,.72)" : LK.chrome;
      [cTL, cTR, cBL, cBR].forEach((c) => (c.style.color = col));
    });

    // ---------------------------------------------------------------- chapter cards (full screen, over everything)
    // num "01".."03" or "+1"; k = which dash is lit (0-based, of `of`). Land the next scene's first element by t1.
    function chapter(t0, t1, num, title, sub, k, x = {}) {
      const of = x.of || 4;
      // with a music map (D.music), the card's hit (the wipe completing, t0 + 0.3) lands on the nearest downbeat
      // within 0.25 s; x.beat = false keeps t0 as given. No map: nothing moves.
      if (x.beat !== false) t0 = HF.music.snap(t0 + 0.3, { kind: "downbeat", early: 0.25, late: 0.25 }) - 0.3;
      const c = el(CHAP, "left:0;top:0;width:1920px;height:1080px;overflow:hidden;clip-path:inset(0 0 0 100%)");
      el(c, `background:${LK.pastel ? C.paper : LK.world}`, "", "hf-fill");
      // the drifting aurora behind the card is pastel_box's; another look's card is its plain world (two empty stand-ins
      // keep the drift tweens below as they are)
      const g1 = LK.pastel ? el(c, "left:-200px;top:-300px;width:1500px;height:1500px;border-radius:50%;background:radial-gradient(circle, rgba(176,160,255,.9) 0%, rgba(255,255,255,0) 64%)") : el(c, "left:0;top:0;width:0;height:0");
      const g2 = LK.pastel ? el(c, "left:1000px;top:200px;width:1300px;height:1300px;border-radius:50%;background:radial-gradient(circle, rgba(255,190,160,.85) 0%, rgba(255,255,255,0) 64%)") : el(c, "left:0;top:0;width:0;height:0");
      mono(c, 150, 300, x.kicker || (num === "+1" ? "bonus" : `${o.kicker || "part"} ${num}`), `font-size:20px;color:${C.acc}`);
      // the numeral: italic in the serif looks; a sans display (whitespace's Inter) stays upright (LK.stress)
      const n = el(c, `left:136px;top:330px;font-size:380px;color:${C.acc};font-style:${LK.stress}`, num, "hf-abs sv");
      // the title fits the 1180 px after the numeral (Instrument Serif averages ~0.31 em a character, a sans display
      // ~0.5 em; it drifts in from +160)
      // (pastel_box keeps 0.31 whatever look a later frame applied: HF.night / HF.redline films sized their titles so)
      const em = LK.pastel || /Serif/.test(HF.F.display) ? 0.31 : 0.5;
      const tsize = x.titleSize || Math.min(124, Math.floor(1180 / (em * Math.max(1, title.length))));
      const ti = el(c, `left:640px;top:${420 + (124 - tsize) * 0.6}px;font-size:${tsize}px;color:${C.ink}`, title, "hf-abs sv");
      const su = el(c, `left:646px;top:570px;font:500 38px/1.2 Inter;color:${C.ink2};white-space:nowrap`, sub || "", "hf-abs");
      const dash = (j) => LK.pastel ? (j === k ? C.acc : j < k ? "rgba(79,59,224,.45)" : "rgba(23,22,31,.14)") : (j <= k ? C.acc : HF.C.line);
      for (let j = 0; j < of; j++) el(c, `left:${150 + j * 74}px;top:770px;width:60px;height:8px;border-radius:4px;background:${dash(j)}${!LK.pastel && j < k ? ";opacity:.45" : ""}`);
      tl.to(c, { clipPath: "inset(0 0 0 0%)", duration: 0.32, ease: E.move, immediateRender: false }, Q(t0));
      tl.fromTo(n, { x: 90 }, { x: 0, duration: 0.9, ease: E.in, immediateRender: false }, Q(t0));
      tl.fromTo([ti, su], { x: 160 }, { x: 0, duration: 0.95, ease: E.in, immediateRender: false, stagger: 0.05 }, Q(t0 + 0.03));
      const hold = t1 - t0 + 0.3;                                             // the card drifts while it holds (never a still)
      tl.fromTo(g1, { x: 0, y: 0 }, { x: 150, y: 70, duration: hold, ease: "none", immediateRender: false }, Q(t0));
      tl.fromTo(g2, { x: 0, y: 0 }, { x: -130, y: -60, duration: hold, ease: "none", immediateRender: false }, Q(t0));
      tl.fromTo([n, ti, su], { scale: 1 }, { scale: 1.04, duration: hold, ease: "none", immediateRender: false }, Q(t0));
      tl.to(c, { clipPath: "inset(0 100% 0 0%)", duration: 0.3, ease: E.move, immediateRender: false }, Q(t1));
      // cue times are when each sound is heard (kit/audio/mix.py aligns the whooshes' peaks and the hit's attack):
      // the whooshes peak mid-wipe (the wipes run 0.32 s and 0.3 s), the hit lands as the wipe completes
      K.sfx("whoosh/whoosh__cinematic-whoosh-fast-transition__mixkit-1492", t0 + 0.16, -19);
      K.sfx("impact/impact__short-bass-hit__mixkit-2299", t0 + 0.3, -17);
      K.sfx("whoosh/whoosh__air-woosh__mixkit-1489", t1 + 0.15, -23);
      return c;
    }

    // ---------------------------------------------------------------- the speaker box: beats -> the director's moves
    // show: "hero" | "face" | "punch" | "beside" | "aside" | "graphic"; o: { side, card, section, tag } (box.js direct)
    const BEATS = [], FLIPS = {}, STRESS = [];
    const beat = (t, show, x = {}) => BEATS.push(Object.assign({ t: +Math.max(0, t).toFixed(3), show }, x));
    // flips: { tag: () => the card the face flips out of }. jumps: the picture cuts to reframe (default: every cut in
    // K.pieces, HF.box.cutsOf; or [first word id of each piece]; false: none). A cut inside a held shot gets a reframe on
    // the slot it is in (HF.box.jumpShots: full frame punches 1.12 / back out, a card alternates 1.0 / 1.1), so no jump cut
    // plays on identical framing. zoom: the full-frame punch (1.12 nets ~9 % over the box's 3 % drift)
    // lens (2026-10-22, v11): x.lens, else D.lens from kit/film's build (on unless film.py sets LENS = False); false = off.
    // With it the camera moves on him inside the box (HF.motion.lens via HF.box o.lens): the jumps above become its
    // eased reframes (no hard 1.12 steps, and they run on whatever shots the box gets, x.box.shots included; on the
    // sharp zoom budget, else the soft allowance, so no join plays bare where the old kit reframed it), a hold it leaves
    // still keeps the box's drift, and every say() stress id is a punch candidate (one per 12 s lands). Without it the
    // box is exactly what it was.
    function box(x = {}) {
      const plan = HF.box.direct({ beats: BEATS });
      const flips = Object.assign({}, FLIPS, x.flips || {});
      plan.shots.forEach((s) => { if (s.in === "flip" && flips[s.tag]) s.from = flips[s.tag](); });
      const pcs = K.pieces || [];
      const cuts = Array.isArray(x.jumps) ? x.jumps.map((w0) => { const p = pcs.find((q) => q.w && q.w[0] === w0);
        if (!p) throw new Error("HF.studio.box: no piece starts on word " + w0);
        return { t: p.out_a, w0 }; }) : x.jumps === false ? [] : HF.box.cutsOf(pcs);
      const DL = ((HF.motion && HF.motion.data()) || {}).lens || null, lz = x.lens === false ? null : x.lens || (DL && DL.on ? DL : null);
      if (!lz) HF.box.jumpShots(plan.shots, cuts, { beats: BEATS, fullZoom: x.zoom || 1.12 }).forEach((s) => plan.shots.push(s));
      plan.shots.sort((p, q) => p.t - q.t);
      const faceAt = x.faceAt || ((t) => { let p = pcs[0]; for (const q of pcs) { if (q.out_a <= t + 1e-4) p = q; else break; } return p && p.face; });
      const lens = lz ? Object.assign({}, DL || {}, typeof lz === "object" ? lz : {}, { cuts: cuts.map((c) => c.t), stress: [...((typeof lz === "object" && lz.stress) || []), ...STRESS] }) : null;
      boxRef = HF.box(K, st, Object.assign({ shots: plan.shots, faceAt, accent: C.acc, look: { shadow: LK.boxShadow || [0, 34, 80, 0.26] } }, lens ? { lens, end: END } : {}, x.box || {}));
      window.__box = boxRef; window.__boxlog = plan.log; window.__pace = HF.box.pace(boxRef.plan, END);
      return boxRef;
    }

    // ---------------------------------------------------------------- the end card (YouTube end-screen slots + handles)
    function endCard(x = {}) {
      const a = x.at != null ? x.at : TALK + 0.3;
      beat(a + 0.05, "graphic", { tag: "end" });
      const L = layer(a, END + 1);
      line(L, x.title || "see you in the *next one.", a + 0.15, { x: 0, y: 150, w: 1920, size: 120, align: "center", per: 0.1 });
      const slot = LK.pastel ? "border:4px dashed rgba(79,59,224,.35);background:rgba(255,255,255,.35)" : `border:3px dashed ${HF.C.mute};background:${HF.C.sunk}`;
      if (x.slots !== false) [0, 1].forEach((i) => { const s = el(L, `left:${300 + i * 700}px;top:380px;width:620px;height:350px;border-radius:26px;${slot}`);
        land(s, a + 0.3 + i * 0.12, { from: { y: 40, scale: 0.94, blur: 8 }, sfx: i ? null : "slide", db: -24 }); });
      const hs = x.handles || HF.HANDLES || [];                    // kit/brand.json via vendor.inline
      const hd = el(L, "left:0;top:800px;width:1920px;display:flex;justify-content:center;gap:24px",
        hs.map((h, i) => `<span class="pill" style="background:${i ? C.acc : C.ink};color:#fff;font-size:30px;padding:18px 30px">${h}</span>`).join(""), "hf-abs");
      land(hd, a + 0.6, { from: { y: 30, scale: 0.95, blur: 8 }, sfx: "pop", db: -22 });
      return L;
    }

    // burned captions for a muted feed (X, LinkedIn): caps = [{ t, e, ids, text }] (the captions.srt groups). A phrase
    // shows only while fewer than a third of its words are on screen as say() type; under the chapter cards, above the chrome
    function captions(caps, x = {}) {
      const L = el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:11;pointer-events:none");
      const cap = el(L, `left:960px;top:${x.y || 948}px;transform:translateX(-50%);max-width:1560px;padding:10px 24px;border-radius:16px;` +
        "background:rgba(17,16,26,.74);color:#fff;font:700 36px/1.25 Inter,sans-serif;text-align:center;white-space:nowrap;visibility:hidden", "");
      const spans = {};
      ROOT.querySelectorAll("[data-w]").forEach((sp) => { (spans[sp.dataset.w] = spans[sp.dataset.w] || []).push(sp); });
      // a word is on screen from its rise until it is hidden, while every scene layer around it is shown (pure time: the
      // live DOM lagged a frame behind in renders and was wrong after a direct seek)
      const onScreen = (id, t) => (spans[id] || []).some((sp) => {
        if (sp._a == null || t < sp._a || (sp._h != null && t >= sp._h)) return false;
        for (let p = sp.parentElement; p && p !== ROOT; p = p.parentElement) if (p._win && (t < p._win[0] || t >= p._win[1])) return false;
        return true;
      });
      // an element marked data-nocap (a hand-written note in the caption band, a CTA that says it already) hides the caption
      const quiet = [...ROOT.querySelectorAll("[data-nocap]")];
      const hush = (t) => quiet.some((e) => { for (let p = e; p && p !== ROOT; p = p.parentElement) if (p._win && (t < p._win[0] || t >= p._win[1])) return false;
        return e._nocap ? t >= e._nocap[0] && t < e._nocap[1] : true; });
      let cur = null;
      K.onFrame((t) => {
        const g = caps.find((c) => t >= c.t && t < c.e);
        if (!g) { cap.style.visibility = "hidden"; cur = null; return; }
        if (g !== cur) { cap.textContent = g.text; cur = g; }
        const shown = g.ids.filter((id) => onScreen(id, t)).length;
        cap.style.visibility = shown * 3 >= g.ids.length || hush(t) ? "hidden" : "visible";   // a third on screen: the gist is there
      });
      return cap;
    }

    const S = { K, tl, Q, W, E, el, f1, C, look: LK.name, END, TALK, PILL, landOfCollapse, WORLD, BACK, FRONT, CHAP, CHROME, captions,
      layer, land, leave, card, chip, mono, orbI, dot, orbAt, icon, tick, grow, growY, pop, fadeOut, arrow, svgLayer,
      rise, wordsOut, say, line, strike, fromPill, chapter, beat, BEATS, FLIPS, box, endCard };
    // evidence (kit/hf/evidence.js): zoom to what is being read, a running comparison, declared holds, music out for a moment
    S.focus = (L, target, x = {}) => HF.focus(K, L, target, x);
    S.scoreboard = (par, x, y, w, so = {}) => HF.scoreboard(S, par, x, y, w, so);
    S.flow = (par, fo = {}) => HF.flow(S, par, fo);                                   // one container through a workflow's states
    S.hold = HF.hold; S.quiet = HF.quiet;
    S.ui = HF.studioUI ? HF.studioUI(S) : {};
    // a takeover (2026-10-22, kit v11; kit/hf/trans.js): a full-screen scene with him off for [a, b] (a box beat
    // "takeover" until b: the director takes him off and brings back his previous shape), its scene on BACK under the box.
    // Before S.box(): the director reads the beats once there, so a later one never takes him off and his box would sit
    // over the scene (review 2026-10-22)
    S.takeover = (a, b, x = {}) => { if (!HF.takeover || !HF.takeover.box) throw new Error("S.takeover needs kit/hf/trans.js (vendor.py MODULES)");
      if (boxRef) throw new Error(`S.takeover(${a}, ${b}) after S.box(): declare takeovers before S.box() (the director plans his beats once)`);
      return HF.takeover.box(S, a, b, x); };
    S.trans = (x = {}) => HF.trans(K, S, x);                                          // T.chapter / T.match / T.zoomThrough on this frame
    return S;
  };
})(window);
