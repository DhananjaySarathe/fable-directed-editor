/*
 * kit/hf/reel.js: the 9:16 pastel-box Reel kit (HF.reel), the vertical sibling of kit/hf/studio.js (16:9). One call sets
 * up the Reel's whole frame, so a Reel's template is only its scenes:
 *
 *   const S = HF.reel(K, ROOT, st, { end: D.total, talk: D.talk, faces: D.faces, label: "yourchannel · audit" });
 *   const { C, Q, W, E, el, layer, land, leave, card, chip, mono, say, line, strike, fromPill, beat, FLIPS, sc, ui } = S;
 *   beat(0, "hero"); say(S.FRONT, 0, 7, { x: 60, y: 300, size: 120, stress: [4] });  ...
 *   S.box();  S.captions();  K.finish(D.total);
 *
 * Grammar (kit/refs/MOTION.md, measured on the reference the owner chose): the speaker is a moving box (HF.box: full ->
 * tilted card -> pill that becomes the next graphic -> the back of a flipping card -> tiles), one pastel aurora world,
 * serif words landing on the spoken word with the stressed word italic in the accent, tiny mono labels, a thin
 * progress bar, shapes that turn into the next idea, a visual change every 0.5-1.5 s.
 *
 * Reel rules on top of the reference:
 *   - every spoken word is on screen once: in a say() line (serif, big) or, where no say() covers it, in the captions
 *     (S.captions() builds them last from what say() did not cover), so a muted viewer gets the whole talk;
 *   - text lives in x 60..1020, y 270..1250 (Instagram covers the bottom and the right-hand buttons);
 *   - a held scene sways and pushes a little (the reference's numbers); a scene to read is still and declared a hold
 *     (layer(..., { read: true }) / S.hold; qa.py --holds); words are hidden before they rise and after they leave
 *     (the frame-by-frame renderer pinned unfinished rises; text-shadow smears outside masks);
 *   - scenes in S.sc are generic and made-up (no real logos, no numbers the speaker didn't say).
 * Layers: WORLD z0, grain z1, BACK z3, the box z4, FRONT z6, CAPS z9, TOP z11, CHROME z14 (box tiles z20).
 */
(function (root) {
  const HF = root.HF;
  // studio.js: HF.studioLook (o.look); vendor.MODULES always inlines it before reel.js
  if (!HF || !HF.kit || !HF.box || !HF.studioLook) throw new Error("kit/hf/reel.js needs core.js, box.js and studio.js first");
  const WD = 1080, HT = 1920;
  // Reel slots: the small face card sits higher than box.js's 9:16 default (critic 2026-10-10: at cy .77 his mouth fell
  // under Instagram's caption area); the face lands near y 1250. A Reel may still pass o.slots.
  const REEL_SLOTS = { bottomSmall: { cx: 0.5, cy: 0.675, w: 0.56, h: 0.25, rot: 2.2 } };
  const FILLER = /^(uh|um|uhm|erm|hmm|ah)[,.]?$/i;

  const CSS = `
    .ui { font-family: var(--f-body); color: var(--ink); }
    .sv { font-family: var(--f-display); font-weight: var(--w-display); letter-spacing: var(--t-display); line-height: 1.0; white-space: nowrap; }
    .mono { font-family: var(--f-mono); }
    .card { position: absolute; border-radius: 34px; background: var(--card); overflow: hidden;
      box-shadow: var(--shadow); }
    .tbar { position: absolute; left: 0; top: 0; right: 0; height: 66px; display: flex; align-items: center; gap: 12px; padding: 0 26px;
      background: var(--sunk); border-bottom: 1px solid var(--line); font: 700 27px/1 var(--f-body); color: var(--text); }
    .tbar i { width: 15px; height: 15px; border-radius: 50%; background: #dad5cf; display: inline-block; }
    .tbar b { margin-left: 10px; }
    .pill { display: inline-flex; align-items: center; gap: 10px; padding: 10px 20px; border-radius: 999px; font: 700 26px/1 var(--f-body); white-space: nowrap; }
    .chip { position: absolute; display: inline-flex; align-items: center; gap: 14px; padding: 18px 28px; border-radius: 24px; background: var(--card);
      font: 700 36px/1 var(--f-body); color: var(--ink); white-space: nowrap; box-shadow: var(--shadow-soft); }
    .lbl { font: 600 22px/1 var(--f-mono); letter-spacing: 0.16em; text-transform: uppercase; color: var(--sub); white-space: nowrap; }
    .av { width: 58px; height: 58px; border-radius: 15px; display: flex; align-items: center; justify-content: center; color: #fff; font: 800 22px/1 var(--f-body); flex: none; }
    .who { font: 800 34px/1 var(--f-body); color: var(--ink); }
    .who small { font: 500 26px/1 var(--f-body); color: var(--mute); margin-left: 10px; }
    .txt { font: 500 36px/1.3 var(--f-body); color: var(--text); margin-top: 8px; }   /* the 36 px phone floor (precheck) */
    .mention { background: var(--acc-tint); color: var(--acc); border-radius: 6px; padding: 0 5px; font-weight: 700; }
    .orb { position: absolute; border-radius: 50%;
      background: radial-gradient(circle at 34% 30%, #ffffff 0%, #ffe3d3 16%, #ff9a5c 46%, #e2562b 78%, #b8401c 100%);
      box-shadow: 0 0 26px 6px rgba(255, 122, 61, 0.5), 0 0 70px 18px rgba(226, 86, 43, 0.22); }
    .orbi { position: relative; display: inline-block; border-radius: 50%; flex: none;
      background: radial-gradient(circle at 34% 30%, #ffffff 0%, #ffe3d3 16%, #ff9a5c 46%, #e2562b 78%, #b8401c 100%); }
    .cell { position: absolute; top: 0; height: 100%; display: flex; align-items: center; font: 500 32px/1 var(--f-body); color: var(--text); white-space: nowrap; }
    .strike { position: absolute; height: 9px; border-radius: 5px; background: var(--acc); transform-origin: 0 50%; }
    .cap { position: absolute; left: 60px; width: 960px; text-align: center; font: 800 52px/1.18 var(--f-body); color: var(--ink); white-space: normal; }
    .cap span.w { display: inline-block; padding: 6px 10px; margin: 0 1px; border-radius: 14px; }
    .cap .plate { display: inline; background: var(--plate); box-decoration-break: clone; -webkit-box-decoration-break: clone;
      padding: 4px 10px; border-radius: 18px; box-shadow: 0 14px 34px rgba(40,24,90,.18); }`;

  const PALETTE = { ink: "#17161f", ink2: "#4d4b5c", mute: "#8e8ba0", acc: "#4f3be0", accTint: "#ece9ff", orb: "#ff7a3d",
    ok: "#16a34a", okSoft: "#dcf5e5", bad: "#d6455d", warm: "#e2562b", onVideo: "#ffc9ad", paper: "#f6f1ec",
    aurora: ["rgba(176,160,255,.85)", "rgba(255,190,160,.85)", "rgba(170,232,205,.75)", "rgba(255,226,170,.55)"] };

  HF.reel = function (K, ROOT, st, o = {}) {
    const tl = K.tl, Q = K.Q, W = K.W, E = HF.E, el = K.el, f1 = 1 / (K.fps || 30);
    // o.look (2026-10-22): another look than pastel_box ("whitespace"): its tokens and a plain world (studio.js
    // HF.studioLook). The scene helpers in S.sc keep their own content colours (generic mock UIs).
    const LK = HF.studioLook(o.look || "pastel_box");
    const C = Object.assign({}, PALETTE, LK.C, o.palette || {});
    const END = o.end, TALK = o.talk != null ? o.talk : o.end;
    if (END == null) throw new Error("HF.reel: pass { end: D.total }");
    if (!document.getElementById("hf-reel-css")) { const s = document.createElement("style"); s.id = "hf-reel-css"; s.textContent = CSS; document.head.append(s); }
    ROOT.querySelectorAll(".hf-paper,.hf-grain").forEach((e) => (e.style.display = "none"));
    if (HF.handFont) HF.handFont();
    HF.look(LK.name, HF.lookOver(o.palette));                                 // every kit component takes this look's tokens
    ROOT.style.background = LK.pastel ? C.paper : LK.edge;
    // the A-roll's own frame (o.src, px): a portrait take by default ([1080, 1920]); a 16:9 camera passes src [1920, 1080] and
    // the box crops it around the face (films/xchakra/shorts, 2026-10-20: forced to portrait, a 16:9 camera framed the wall).
    // The faces (o.faces) and the pieces' face are in the same px.
    const SRC = o.src || [WD, HT];
    const v = st.wrap.querySelector("video");
    if (v) v.style.cssText = `position:absolute;left:0;top:0;width:${SRC[0]}px;height:${SRC[1]}px`;
    st.wrap.style.width = SRC[0] + "px"; st.wrap.style.height = SRC[1] + "px";
    Object.entries(Object.assign({}, REEL_SLOTS, o.slots || {})).forEach(([k, v]) => { HF.box.SLOTS["9:16"][k] = Object.assign({}, HF.box.SLOTS["9:16"][k] || {}, v); });
    const PS = HF.box.SLOTS["9:16"].pill;
    const PILL = { cx: PS.cx * WD, cy: PS.cy * HT, w: PS.w * WD, h: PS.h * HT };
    const landOfCollapse = (t) => t - 0.04 + HF.box.MOVES.collapse.dur;

    // ---------------------------------------------------------------- the world: one pastel aurora, never still
    // (another look: its plain world, no aurora and no grain)
    const WORLD = el(ROOT, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:0;background:${LK.pastel ? C.paper : LK.world};overflow:hidden`);
    if (LK.pastel) {
      const blob = (c, s) => el(WORLD, `left:0;top:0;width:${s}px;height:${s}px;border-radius:50%;background:radial-gradient(circle, ${c} 0%, rgba(255,255,255,0) 66%)`);
      const BL = [blob(C.aurora[0], 1500), blob(C.aurora[1], 1400), blob(C.aurora[2], 1300), blob(C.aurora[3], 1100)];
      const ORBIT = [[160, 300, 140, 160, 0.42, 0, 1500], [940, 760, 120, 200, 0.36, 2, 1400], [260, 1560, 180, 120, 0.31, 4, 1300], [880, 1700, 140, 160, 0.48, 1, 1100]];
      K.onFrame((t) => BL.forEach((b, i) => { const [cx, cy, ax, ay, w, ph, s] = ORBIT[i];
        b.style.transform = `translate(${(cx + ax * Math.sin(t * w + ph) - s / 2).toFixed(1)}px,${(cy + ay * Math.cos(t * w * 0.8 + ph) - s / 2).toFixed(1)}px)`; }));
      el(ROOT, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:1;opacity:.05;pointer-events:none;background-image:radial-gradient(rgba(0,0,0,.6) 1px, rgba(0,0,0,0) 1.4px);background-size:5px 5px`);
    }
    st.cam.style.zIndex = "4";
    const full = (z) => el(ROOT, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:${z}`);
    const BACK = full(3), FRONT = full(6), CAPS = full(9), TOP = full(11), CHROME = full(14);
    CHROME.style.pointerEvents = "none"; CHROME.dataset.decor = "1";

    // ---------------------------------------------------------------- small helpers
    // a scene's graphics: a held scene sways (+-10 px, ~0.6 % of the height, the reference) and pushes slowly (0.4 %/s, at
    // most 3 %); x.read holds still and declares a reading hold (qa.py --holds). L._F is the focus wrapper (S.focus).
    const layer = (a, b, par = BACK, x = {}) => {
      const fl = el(par, `left:0;top:0;width:${WD}px;height:${HT}px`); K.show(fl, a - 0.02, b); fl._win = [a - 0.02, b];
      const ph = a * 0.37, amp = x.read ? 0 : x.float != null ? x.float : 10;
      if (amp) K.onFrame((t) => { if (t > a - 0.1 && t < b + 0.1) fl.style.transform = `translate(${(amp * 0.85 * Math.sin(t * 0.66 + ph)).toFixed(2)}px,${(amp * Math.cos(t * 0.53 + ph)).toFixed(2)}px)`; });
      const F = el(fl, `left:0;top:0;width:${WD}px;height:${HT}px`);
      const L = el(F, `left:0;top:0;width:${WD}px;height:${HT}px;transform-origin:50% 40%`), d = Math.max(0.3, b - a);
      const push = x.read ? 0 : x.push != null ? x.push : 0.004;
      if (push) tl.fromTo(L, { scale: 1 }, { scale: 1 + Math.min(0.03, push * d), duration: d, ease: "none", immediateRender: false }, Q(a));
      if (x.read) HF.hold(a + 0.6, b, typeof x.read === "string" ? x.read : "read");
      L._F = F;
      return L;
    };
    const land = (e, t, x = {}) => HF.land(K, e, t, { spring: x.spring || "ui", from: x.from || { y: 40, scale: 0.95, blur: 10 },
      sfx: x.sfx === undefined ? "pop" : x.sfx, sfxDb: x.db != null ? x.db : -26 });
    const leave = (e, t, x = {}) => HF.leave(K, e, t, x);
    const card = (par, x, y, w, h, html = "", style = "") => el(par, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;${style}`, html, "card ui");
    const chip = (par, x, y, html, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, html, "chip ui");
    const mono = (par, x, y, text, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, text, "hf-abs lbl");
    const orbI = (d) => `<span class="orbi" style="width:${d}px;height:${d}px"></span>`;
    const dot = (c, d = 28) => `<span style="width:${d}px;height:${d}px;border-radius:50%;background:${c};display:inline-block;flex:none"></span>`;
    const orbAt = (par, x, y, d = 56) => {
      const ob = el(par, `left:${x - d / 2}px;top:${y - d / 2}px;width:${d}px;height:${d}px`, "", "orb");
      K.onFrame((t) => { ob.style.transform = `scale(${(1 + 0.05 * Math.sin(t * 5.2)).toFixed(4)})`; });
      return ob;
    };
    const icon = (n, s = 36, c = C.ink, w = 2.2) => HF.icon(n, s, c, w);
    const tick = (s = 26, c = "#fff") => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 12.5l5 5 10-11"/></svg>`;
    const grow = (e, t, dur = 0.42) => tl.fromTo(e, { scaleX: 0 }, { scaleX: 1, duration: dur, ease: E.in, immediateRender: true }, Q(t));
    const growY = (e, t, dur = 0.42) => tl.fromTo(e, { scaleY: 0 }, { scaleY: 1, duration: dur, ease: E.in, immediateRender: true }, Q(t));
    const pop = (e, t) => tl.fromTo(e, { scale: 0 }, { scale: 1, duration: 0.35, ease: HF.spring(HF.SPRING.thrown).ease, immediateRender: true }, Q(t));
    const fadeOut = (e, t, d = 0.2) => tl.to(e, { opacity: 0, duration: d, immediateRender: false }, Q(t));
    const arrow = (par, x0, y0, x1, col = C.acc) => {
      const a = el(par, `left:${x0}px;top:${y0 - 3}px;width:${x1 - x0}px;height:7px;border-radius:4px;background:${col};transform-origin:0 50%`);
      el(a, `right:-6px;top:-9px;width:0;height:0;border-left:18px solid ${col};border-top:12px solid transparent;border-bottom:12px solid transparent`);
      return a;
    };

    // ---------------------------------------------------------------- type: words rising in masks
    const rise = (s, a) => { s.style.visibility = "hidden"; tl.set(s, { visibility: "visible" }, Q(a)); s._a = Q(a);   // _a/_h: when it is on screen
      const rw = gsap.fromTo(s, { yPercent: 112 }, { yPercent: 0, duration: 0.45, ease: E.in, immediateRender: true }); tl.add(rw, Q(a)); return [rw, Q(a)]; };
    const wordsOut = (items, rises, t) => { items.forEach((s, k) => { const at = Q(t + k * 0.012), [rw, a] = rises[k];
        if (a + rw.duration() > at - 0.02) rw.duration(Math.max(f1, at - 0.02 - a));
        tl.to(s, { yPercent: -112, duration: 0.22, ease: E.out, immediateRender: false }, at);
        s._h = Q(Math.max(at + 0.25, a + f1)); tl.set(s, { visibility: "hidden" }, s._h); }); return t + 0.28; };
    const mask = () => { const m = document.createElement("span"); m.style.cssText = "display:inline-block;overflow:hidden;vertical-align:top;padding:0 0.05em 0.14em"; return m; };
    const COVERED = new Set();
    // his words (from..to ids) on their spoken time minus a frame; stressed ids italic in the accent.
    // x: x, y, w, size, color, align, lh, shadow, stress [ids], br [ids], accent, nocap (don't count as captioned)
    function say(par, from, to, x = {}) {
      const ws = K.words_.filter((w) => w.i >= from && w.i <= to && w.text);
      const box = el(par, `left:${x.x != null ? x.x : 60}px;top:${x.y || 300}px;width:${x.w || 960}px;font-size:${x.size || 110}px;color:${x.color || C.ink};text-align:${x.align || "left"};` +
        `line-height:${x.lh || 1.02};white-space:normal;${x.shadow ? "text-shadow:0 6px 34px rgba(0,0,0,.45),0 2px 6px rgba(0,0,0,.3);" : ""}`, "", "hf-abs sv");
      const stress = new Set(x.stress || []), brk = new Set(x.br || []), items = [], rises = [];
      if (x.stress) STRESS.push(...x.stress);                                // the lens's punch tags (S.box, 2026-10-22)
      ws.forEach((w) => {
        if (brk.has(w.i)) box.append(document.createElement("br"));
        const m = mask(), s = document.createElement("span"); s.style.display = "inline-block";
        s.textContent = String(w.text).replace(/[,]$/, ""); s.dataset.w = w.i;            // spoken type (precheck, captions)
        if (stress.has(w.i)) { s.style.fontStyle = LK.stress; s.style.color = x.accent || (x.color === "#fff" ? C.onVideo : C.acc); }
        m.append(s); box.append(m); box.append(document.createTextNode(" "));
        rises.push(rise(s, Math.max(0.01, w.t - f1))); items.push(s);
        if (!x.nocap) COVERED.add(w.i);
      });
      return { box, items, t0: ws.length ? ws[0].t : null, out: (t) => wordsOut(items, rises, t) };
    }
    // a line that isn't spoken word for word: "|" breaks; "*word" or "*several words*" is the accent (HF.accentTokens); rises from t0
    function line(par, text, t0, x = {}) {
      const box = el(par, `left:${x.x != null ? x.x : 60}px;top:${x.y || 300}px;width:${x.w || 960}px;font-size:${x.size || 96}px;color:${x.color || C.ink};text-align:${x.align || "left"};line-height:${x.lh || 1.02};white-space:normal;${x.shadow ? "text-shadow:0 6px 34px rgba(0,0,0,.45);" : ""}`, "", "hf-abs sv");
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
    // until: when it leaves (draw it in a layer() or pass until: on FRONT it would stay up for the rest of the Reel)
    function strike(par, x, y, w, t, target, col = C.acc, until = null) {
      const s = el(par, `left:${x}px;top:${y}px;width:${w}px;background:${col}`, "", "hf-abs strike");
      tl.fromTo(s, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: E.in, immediateRender: true }, Q(t));
      if (until != null) tl.to(s, { opacity: 0, duration: 0.15, immediateRender: false }, Q(until));
      if (target) tl.to(target, { opacity: 0.38, duration: 0.25, immediateRender: false }, Q(t + 0.12));
      K.sfx("click", t, -24);
      return s;
    }
    // a card that grows out of the collapsed pill (beat(t, "graphic", { card: true }))
    function fromPill(L, t, x, y, w, h, bg = LK.pastel ? "rgba(255,255,255,.78)" : HF.C.card) {
      const c = el(L, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;border-radius:36px;background:${bg};box-shadow:${LK.pastel ? "0 40px 90px rgba(40,24,90,.13)" : HF.C.e2};overflow:hidden`);
      HF.box.morph(K, c, PILL, { x, y, w, h }, landOfCollapse(t), 0.32, { fromBg: C.acc, bg, radius: 36 });
      return c;
    }

    // ---------------------------------------------------------------- chrome: labels + the progress bar (top: IG covers the bottom)
    const SECTIONS = (o.sections && o.sections.length ? o.sections : [[0, ""]]).slice().sort((a, b) => a[0] - b[0]);
    const ch = (x, y, al) => el(CHROME, `left:${x}px;top:${y}px;${al ? "width:520px;text-align:right;" : ""}font:600 19px/1 JBMono,monospace;letter-spacing:.16em;text-transform:uppercase;white-space:nowrap`);
    const cTL = ch(48, 222), cTR = ch(512, 222, true);
    cTL.textContent = o.label || "";
    const bar = el(CHROME, `left:0;top:0;width:${WD}px;height:8px;background:${C.acc};transform-origin:0 50%;opacity:.9`);
    let boxRef = null;
    K.onFrame((t) => {
      bar.style.transform = `scaleX(${(t / END).toFixed(5)})`;
      cTR.textContent = (SECTIONS.filter((s) => s[0] <= t + 1e-6).pop() || SECTIONS[0])[1];
      const r = boxRef ? boxRef.rect(t) : null, onVideo = r && r.w > 1000 && r.op > 0.5;
      const col = onVideo ? "rgba(255,255,255,.78)" : LK.chrome;
      [cTL, cTR].forEach((c) => (c.style.color = col));
    });

    // ---------------------------------------------------------------- the speaker box (HF.box, 9:16 slots)
    const BEATS = [], FLIPS = {}, STRESS = [];
    const beat = (t, show, x = {}) => BEATS.push(Object.assign({ t: +Math.max(0, t).toFixed(3), show }, x));
    const faces = o.faces || null;                                   // per output frame [x, y, w] in source px (smoothed)
    // lens (2026-10-22, v11; as in studio.js): x.lens, else D.lens from kit/film's build; false = off. The jump cuts then
    // become the lens's eased reframes (no hard 1.12 steps; the soft allowance when the sharp budget can't pay one), a
    // hold it leaves still keeps the box's drift, and say()'s stress ids are its punch candidates. The face circle
    // (CIRCLE, { pill: 1 } untinted) is a lens shape too
    function box(x = {}) {
      const plan = HF.box.direct({ beats: BEATS, format: "9:16" });
      const flips = Object.assign({}, FLIPS, x.flips || {});
      plan.shots.forEach((s) => { if (s.in === "flip" && flips[s.tag]) s.from = flips[s.tag](); });
      // box.js hides a flipped card with visibility, but its words set visibility:visible themselves: fade the card too
      plan.shots.forEach((s) => { if (s.in === "flip" && s.from) tl.set(s.from, { opacity: 0 }, Q(s.t + HF.box.MOVES.flip.dur)); });
      // x.fullZoom: zoom every full-frame shot a little, so the cover crop has room to put the face at 42 % of the height
      // (a square A-roll fills 1920 px exactly, so at zoom 1 the face stays wherever the take framed it)
      if (x.fullZoom) plan.shots.forEach((s) => { if (s.at === "full" && s.zoom == null) s.zoom = x.fullZoom; });
      (x.extra || []).forEach((s) => plan.shots.push(s));             // e.g. { t, at: "full", in: "cut", zoom: 1.3 }: a hard punch-in
      plan.shots.sort((a, b) => a.t - b.t);
      const pcs = K.pieces || [];
      const DL = ((HF.motion && HF.motion.data()) || {}).lens || null, lz = x.lens === false ? null : x.lens || (DL && DL.on ? DL : null);
      // jump cuts inside a held shot reframe (as in studio.js): x.jumps false = none; default = every picture cut in the pieces
      const cuts = x.jumps === false ? [] : Array.isArray(x.jumps) ? x.jumps.map((t) => ({ t })) : HF.box.cutsOf(pcs);
      if (x.jumps !== false && !lz) {
        HF.box.jumpShots(plan.shots, cuts, { beats: BEATS, fullZoom: x.zoom || 1.12 }).forEach((s) => plan.shots.push(s));
        plan.shots.sort((a, b) => a.t - b.t);
      }
      // (with the lens the face carries its size too: the lens anchors on the eyes, 0.2 head widths above the box centre)
      const faceAt = x.faceAt || (faces ? (t) => { const f = faces[Math.max(0, Math.min(faces.length - 1, Math.floor(t * (K.fps || 30))))]; return lz ? [f[0], f[1], f[2]] : [f[0], f[1]]; }
        : (t) => { let p = pcs[0]; for (const q of pcs) { if (q.out_a <= t + 1e-4) p = q; else break; } return p && p.face; });
      const lens = lz ? Object.assign({}, DL || {}, typeof lz === "object" ? lz : {}, { cuts: cuts.map((c) => c.t), stress: [...((typeof lz === "object" && lz.stress) || []), ...STRESS] }) : null;
      boxRef = HF.box(K, st, Object.assign({ shots: plan.shots, faceAt, accent: C.acc, src: SRC, format: "9:16", look: { shadow: LK.boxShadow || [0, 34, 80, 0.26], radius: 36 } },
        lens ? { lens, end: END } : {}, x.box || {}));
      window.__box = boxRef; window.__boxlog = plan.log; window.__pace = HF.box.pace(boxRef.plan, END);
      return boxRef;
    }

    // ---------------------------------------------------------------- captions: every word say() did not show
    // o.y(t) -> top of the caption block (default 1110); o.skip [[a, b]] output-time ranges with no captions
    function captions(x = {}) {
      const yAt = x.y || (() => 1110), skip = x.skip || [], hide = new Set(x.hide || []);     // hide: a kept stutter's repeat
      const BRK = (x.breaks || []).slice().sort((p, q) => p - q);          // sorted: "the next break" below is the first one after a page
      const ws = K.words_.filter((w) => w.text && !COVERED.has(w.i) && !hide.has(w.i) && !FILLER.test(String(w.text).trim()) && !skip.some(([a, b]) => w.t >= a && w.t < b));
      const covT = K.words_.filter((w) => COVERED.has(w.i)).map((w) => w.t).sort((a, b) => a - b);
      const nextCovered = (t) => { const c = covT.find((x) => x > t + 0.01); return c != null ? c : 1e9; };
      const pages = [];
      let cur = [];
      ws.forEach((w, k) => {
        const prev = cur[cur.length - 1];
        // x.breaks: times where a page must end (layout changes: a page never straddles two layouts' caption slots)
        const brk = prev && (cur.length >= (x.max || 4) || w.t - prev.e > 0.45 || /[.?!]$/.test(prev.text) || w.i !== prev.i + 1 || w.t - cur[0].t > 1.7 ||
          BRK.some((bt) => prev.t < bt && w.t >= bt - 0.05));
        if (brk) { pages.push(cur); cur = []; }
        cur.push(w);
      });
      if (cur.length) pages.push(cur);
      // a one-word page that would only flash (< 0.3 s before the next page, or before a layout change) joins its
      // neighbour when the two are consecutive words with no layout change between (critic 2026-10-18: "is", "mujhko.")
      const noBrk = (p, q) => !BRK.some((bt) => p < bt && q >= bt - 0.05);
      for (let n = 0; n < pages.length; n++) {
        const pg = pages[n]; if (pg.length !== 1) continue;
        const w = pg[0], next = pages[n + 1], prev = pages[n - 1];
        const nb = BRK.find((bt) => bt > w.t + 0.01);
        const until = Math.min(next ? next[0].t : w.e + 0.6, nb != null ? nb - 0.04 : 1e9);
        if (until - w.t >= 0.3) continue;
        if (prev && prev[prev.length - 1].i + 1 === w.i && noBrk(prev[prev.length - 1].t, w.t)) { prev.push(w); pages.splice(n, 1); n--; }
        else if (next && w.i + 1 === next[0].i && noBrk(w.t, next[0].t)) { next.unshift(w); pages.splice(n, 1); n--; }
      }
      pages.forEach((pg, n) => {
        // a page clears when the next page starts, 0.6 s after its last word, or as soon as the serif type takes over
        const a = Math.max(0, pg[0].t - f1), nx = pg[pg.length - 1], next = pages[n + 1];   // never before 0 (a negative start left page 1 stuck on screen)
        const nb = BRK.find((bt) => bt > nx.t + 0.01);                       // ...and clears before the next layout change
        const b = Math.min(next ? next[0].t - f1 : nx.e + 0.5, nx.e + 0.6, Math.max(nx.e, nextCovered(nx.t) - f1), nb != null ? Math.max(nx.e, nb - 0.04) : 1e9);
        const c = el(CAPS, `top:${yAt(a, b)}px`, "", x.cls || "cap");            // o.y(start, end): the page's whole time on screen
        const plate = document.createElement("span"); plate.className = "plate"; c.append(plate);
        const spans = pg.map((w) => { const s = document.createElement("span"); s.className = "w"; s.textContent = String(w.text).replace(/[,]$/, ""); plate.append(s); plate.append(document.createTextNode(" ")); return s; });
        K.show(c, a, b);
        tl.fromTo(c, { y: 18, scale: 0.94 }, { y: 0, scale: 1, duration: 0.18, ease: E.in, immediateRender: false }, Q(a));
        pg.forEach((w, k) => {                                        // the word being said: accent text
          tl.set(spans[k], { color: x.active || C.acc }, Q(w.t - f1));                     // x.base / x.active: caption colours
          tl.set(spans[k], { color: x.base || C.ink }, Q(Math.min(w.e, pg[k + 1] ? pg[k + 1].t - f1 : w.e + 0.2)));
        });
      });
      window.__caps = pages.length;
      return pages;
    }

    const S = { K, tl, Q, W, E, el, f1, C, look: LK.name, END, TALK, PILL, landOfCollapse, WORLD, BACK, FRONT, CAPS, TOP, CHROME, WD, HT,
      layer, land, leave, card, chip, mono, orbI, dot, orbAt, icon, tick, grow, growY, pop, fadeOut, arrow,
      rise, wordsOut, say, line, strike, fromPill, beat, BEATS, FLIPS, box, captions, COVERED,
      cover: (a, b) => K.words_.forEach((w) => { if (w.i >= a && w.i <= b) COVERED.add(w.i); }) };   // shown by a graphic
    S.focus = (L, target, x = {}) => HF.focus(K, L, target, x);                       // kit/hf/evidence.js
    S.scoreboard = (par, x, y, w, so = {}) => HF.scoreboard(S, par, x, y, w, so);
    S.flow = (par, fo = {}) => HF.flow(S, par, fo);                                   // one container through a workflow's states
    S.hold = HF.hold; S.quiet = HF.quiet;
    S.ui = HF.studioUI ? HF.studioUI(S) : {};
    S.sc = HF.reelScenes ? HF.reelScenes(S) : {};
    // a takeover (2026-10-22, kit v11; kit/hf/trans.js; as in studio.js): a full-screen scene with him off for [a, b];
    // before S.box() (the director reads the beats once there)
    S.takeover = (a, b, x = {}) => { if (!HF.takeover || !HF.takeover.box) throw new Error("S.takeover needs kit/hf/trans.js (vendor.py MODULES)");
      if (boxRef) throw new Error(`S.takeover(${a}, ${b}) after S.box(): declare takeovers before S.box() (the director plans his beats once)`);
      return HF.takeover.box(S, a, b, x); };
    S.trans = (x = {}) => HF.trans(K, S, x);
    return S;
  };

  // ======================================================================================================================
  // HF.reelScenes(S): the Reel scene library. Each takes (par, ...) and page px; times in s (pass W(id) for a word).
  // Build once, reuse: add a scene here when a Reel needs a new one, never inline a one-off in a template twice.
  //
  //   sc.ideaCards(par, { x, y, w, h, n, at, labels, locked, per })  -> { cards, unlock(t, rows) }   ranked idea cards
  //   sc.prompt(par, x, y, w, h, { title, text, at, cps, typeAt, sub })   a prompt card that types its text
  //   sc.connect(par, x, y, w, { rows: [{ name, icon, color, onAt }], at, title })   a connectors card, switches flip on
  //   sc.scanGrid(par, x, y, w, { cols, rows, at, scanAt, scanDur, doneAt })   recent-video thumbnails scanned + ticked
  //   sc.week(par, x, y, w, { days, at, marks: [{ at, every }] })   a week strip; marks light the days on a cadence
  //   sc.clock(par, cx, cy, { from: "6:59", to: "7:00", at, flipAt, label })   a big digital clock that flips
  //   sc.notif(par, x, y, w, { app, title, body, at, icon })   a phone notification that drops in
  //   sc.shot(par, x, y, w, src, { srcW, srcH, at, blur: [[x, y, w, h]], radius })   a screenshot card, private boxes blurred
  //   sc.toolPair(par, x, y, { a: [name, color], b: [name, color], at, per })   two app tiles with an "or" between
  //   sc.bars(par, x, y, w, h, { values, labels, at, color })   a small bar chart that grows (values are shapes, not data)
  // ======================================================================================================================
  HF.reelScenes = function (S) {
    const { K, tl, Q, E, el, C, card, chip, mono, land, pop, tick, icon, orbI, dot } = S;
    const sc = {};

    sc.ideaCards = (par, o = {}) => {
      const n = o.n || 3, w = o.w || 300, h = o.h || 420, gap = o.gap || 30, x0 = o.x != null ? o.x : (S.WD - n * w - (n - 1) * gap) / 2, y = o.y || 700;
      const cols = o.colors || [C.orb, "#0f9d8a", C.acc];
      const cards = [];
      for (let i = 0; i < n; i++) {
        const c = card(par, x0 + i * (w + gap), y, w, h, `<div class="sv" style="position:absolute;left:28px;top:18px;font-size:120px;color:${cols[i % cols.length]};font-style:italic">#${i + 1}</div>
          <div class="lk" style="position:absolute;left:28px;right:28px;top:170px">${[0.95, 0.75, 0.85].map((f) => `<div style="height:22px;border-radius:11px;background:#ece9f2;margin-bottom:18px;width:${f * 100}%"></div>`).join("")}</div>
          <div class="lb" style="position:absolute;left:28px;bottom:26px">${o.labels ? `<span class="pill" style="background:${C.accTint};color:${C.acc}">${o.labels[i] || ""}</span>` : ""}</div>
          <div class="lock" style="position:absolute;right:24px;top:30px;width:58px;height:58px;border-radius:50%;background:${C.ink};display:flex;align-items:center;justify-content:center">${icon("lock", 30, "#fff", 2.4)}</div>`);
        c.style.transformOrigin = "50% 100%";
        if (o.at != null) land(c, o.at + i * (o.per || 0.14), { from: { y: 90, scale: 0.86, blur: 12, rotation: (i - 1) * 6 }, spring: "thrown", sfx: i ? "pop" : "slide", db: -21 });
        if (o.locked === false) c.querySelector(".lock").style.display = "none";
        cards.push(c);
      }
      // unlock: the locks pop off, the grey lines turn into rows of text (rows: [[label, value], ...] per card or one list for all)
      const unlock = (t, rows, per = 0.16) => cards.forEach((c, i) => {
        const tt = t + i * per, lk = c.querySelector(".lock"), lines = c.querySelector(".lk");
        tl.to(lk, { scale: 0, rotation: 40, duration: 0.22, ease: E.out, immediateRender: false }, Q(tt));
        tl.to(lines, { opacity: 0, duration: 0.15, immediateRender: false }, Q(tt + 0.05));
        const rs = (Array.isArray(rows[0]) && Array.isArray(rows[0][0])) ? rows[i] : rows;
        const box = el(c, "left:28px;right:20px;top:160px", rs.map(([k, v]) => `<div style="display:flex;gap:10px;align-items:baseline;margin-bottom:16px;white-space:nowrap">
          <b style="font:800 25px Inter;color:${C.acc}">${k}</b><span style="font:600 25px Inter;color:#2a2935">${v || ""}</span></div>`).join(""));
        box.style.opacity = 0;
        tl.fromTo(box, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.3, ease: E.in, immediateRender: false }, Q(tt + 0.1));
        tl.fromTo(c, { scale: 1 }, { scale: 1.06, duration: 0.12, yoyo: true, repeat: 1, ease: "power1.out", immediateRender: false }, Q(tt));
        K.sfx(i ? "pop" : "ui/ui__select-click__mixkit-1109", tt, -20);
      });
      return { cards, unlock };
    };

    sc.prompt = (par, x, y, w, h, o = {}) => {
      const c = card(par, x, y, w, h, `<div class="tbar">${orbI(26)}<b>${o.title || "prompt"}</b>${o.sub ? `<span class="mono" style="margin-left:auto;font-size:19px;color:#8e8ba0">${o.sub}</span>` : ""}</div>`);
      if (o.at != null) land(c, o.at, { from: o.from || { y: 60, scale: 0.94, blur: 10 }, spring: "snappy", sfx: "slide", db: -22 });
      const tx = el(c, `left:36px;top:96px;width:${w - 72}px;font:500 ${o.size || 33}px/1.42 JBMono,monospace;color:#2a2935;white-space:pre-wrap`, "");
      const end = K.typeText(tx, o.text || "", o.typeAt != null ? o.typeAt : (o.at || 0) + 0.3, o.cps || 40, true);
      K.sfx("typing/typing__electronic-typing__mixkit-1397", (o.typeAt != null ? o.typeAt : (o.at || 0) + 0.3), -27);
      return { card: c, text: tx, end };
    };

    sc.connect = (par, x, y, w, o = {}) => {
      const rows = o.rows || [];
      const c = card(par, x, y, w, 110 + rows.length * 128, `<div class="tbar">${icon("gear", 28, "#3a3946", 2.2)}<b>${o.title || "Connectors"}</b></div>`);
      if (o.at != null) land(c, o.at, { from: o.from || { y: 60, scale: 0.94, blur: 10 }, spring: "snappy", sfx: "slide", db: -22 });
      const sw = rows.map((r, i) => {
        const row = el(c, `left:30px;top:${92 + i * 128}px;width:${w - 60}px;height:108px;border-radius:22px;background:#f7f5f2`);
        el(row, "left:24px;top:24px;display:flex;align-items:center;gap:20px", `<span style="width:60px;height:60px;border-radius:16px;background:${r.color || C.ink};display:flex;align-items:center;justify-content:center">${icon(r.icon || "play", 32, "#fff", 2.4)}</span>
          <span style="font:700 34px Inter;color:${C.ink}">${r.name}</span>`);
        const s = el(row, "right:24px;top:24px;width:110px;height:60px;border-radius:30px;background:#d8d4e6");
        const kn = el(s, "left:6px;top:6px;width:48px;height:48px;border-radius:50%;background:#fff;box-shadow:0 4px 10px rgba(0,0,0,.2)");
        if (r.onAt != null) {
          tl.to(s, { backgroundColor: C.ok, duration: 0.18, immediateRender: false }, Q(r.onAt));
          tl.to(kn, { x: 50, duration: 0.22, ease: E.in, immediateRender: false }, Q(r.onAt));
          K.sfx("ui/ui__select-click__mixkit-1109", r.onAt, -19);
        }
        return { row, sw: s };
      });
      return { card: c, rows: sw };
    };

    sc.scanGrid = (par, x, y, w, o = {}) => {
      const cols = o.cols || 3, rws = o.rows || 3, g = 18, tw = (w - (cols - 1) * g) / cols, th = tw * (o.ratio || 1.32);
      const box = el(par, `left:${x}px;top:${y}px;width:${w}px;height:${rws * th + (rws - 1) * g}px`);
      const hues = ["#c9b8ff", "#ffc9b0", "#b6ead3", "#ffe1a8", "#d8d0ff", "#ffd6c9", "#c6eedc", "#fbe3b6", "#cfc6ff"];
      const tiles = [];
      for (let r = 0; r < rws; r++) for (let k = 0; k < cols; k++) {
        const i = r * cols + k;
        const t = el(box, `left:${k * (tw + g)}px;top:${r * (th + g)}px;width:${tw}px;height:${th}px;border-radius:22px;overflow:hidden;background:linear-gradient(160deg,${hues[i % hues.length]},#ffffff);box-shadow:0 14px 34px rgba(40,24,90,.14)`,
          `<div style="position:absolute;left:50%;top:44%;margin:-28px 0 0 -28px;width:56px;height:56px;border-radius:50%;background:rgba(23,22,31,.78);display:flex;align-items:center;justify-content:center">${icon("play", 26, "#fff", 2.6)}</div>
           <div style="position:absolute;left:16px;right:16px;bottom:16px;height:14px;border-radius:7px;background:rgba(23,22,31,.16)"></div>`);
        if (o.at != null) land(t, o.at + ((r + k) % 5) * 0.05, { from: { y: 40, scale: 0.85, blur: 8 }, sfx: i ? null : "slide", db: -23 });
        tiles.push(t);
      }
      if (o.scanAt != null) {
        const H = rws * th + (rws - 1) * g, dur = o.scanDur || 1.6;
        const beam = el(box, `left:-20px;top:0;width:${w + 40}px;height:10px;border-radius:5px;background:${C.acc};box-shadow:0 0 30px 8px rgba(79,59,224,.45);opacity:0`);
        tl.to(beam, { opacity: 1, duration: 0.1, immediateRender: false }, Q(o.scanAt));
        tl.fromTo(beam, { y: 0 }, { y: H, duration: dur, ease: "none", immediateRender: false }, Q(o.scanAt));
        tl.to(beam, { opacity: 0, duration: 0.15, immediateRender: false }, Q(o.scanAt + dur));
        K.sfx("riser/riser__cinematic-synth-riser__mixkit-645", o.scanAt, -26);
        tiles.forEach((t, i) => {
          const r = Math.floor(i / cols), at = o.scanAt + dur * (r + 0.6) / rws;
          const ok = el(t, `right:12px;top:12px;width:46px;height:46px;border-radius:50%;background:${C.ok};display:flex;align-items:center;justify-content:center`, tick(26));
          tl.set(ok, { scale: 0 }, 0); pop(ok, at + (i % cols) * 0.04);
          if (i % cols === 0) K.sfx("check", at, -25);
        });
      }
      return { box, tiles };
    };

    sc.week = (par, x, y, w, o = {}) => {
      const days = o.days || ["M", "T", "W", "T", "F", "S", "S"], n = days.length, g = 14, dw = (w - (n - 1) * g) / n;
      const box = el(par, `left:${x}px;top:${y}px;width:${w}px;height:${dw + 50}px`);
      const ds = days.map((d, i) => {
        const c = el(box, `left:${i * (dw + g)}px;top:0;width:${dw}px;height:${dw + 40}px;border-radius:22px;background:#fff;box-shadow:0 12px 30px rgba(40,24,90,.12)`,
          `<div style="position:absolute;left:0;right:0;top:14px;text-align:center;font:700 26px Inter;color:#8e8ba0">${d}</div>
           <div class="dt" style="position:absolute;left:50%;top:58px;margin-left:-${dw * 0.28}px;width:${dw * 0.56}px;height:${dw * 0.56}px;border-radius:50%;background:#ece9f2"></div>`);
        if (o.at != null) land(c, o.at + i * 0.045, { from: { y: 30, scale: 0.9, blur: 6 }, sfx: i ? null : "slide", db: -24 });
        return c;
      });
      // marks: [{ at, every, color }] light every Nth day (from day 0), the previous mark's days dim back
      const marks = o.marks || [];
      marks.forEach((m, mi) => {
        ds.forEach((c, i) => {
          const dt = c.querySelector(".dt"), on = i % m.every === 0, t = m.at + i * 0.06;
          tl.to(dt, { backgroundColor: on ? (m.color || C.acc) : "#ece9f2", scale: on ? 1 : 0.8, duration: 0.2, ease: E.in, immediateRender: false }, Q(t));
          if (on) K.sfx(i ? "pop" : "check", t, i ? -28 : -23);
        });
      });
      return { box, days: ds };
    };

    sc.clock = (par, cx, cy, o = {}) => {
      const w = o.w || 620, h = o.h || 300;
      const c = card(par, cx - w / 2, cy - h / 2, w, h, `${o.label ? `<div class="lbl" style="position:absolute;left:0;right:0;top:26px;text-align:center">${o.label}</div>` : ""}`, "background:#17161f");
      const dig = (txt, top) => el(c, `left:0;top:${top}px;width:${w}px;text-align:center;font:800 170px/1 Inter;color:#fff;letter-spacing:-.04em`, txt);
      const a = dig(o.from || "6:59", 70), b = dig(o.to || "7:00", 70);
      a.style.color = "#fff"; b.style.color = C.onVideo;
      tl.set(b, { yPercent: 100, opacity: 0 }, 0);
      if (o.at != null) land(c, o.at, { from: { y: 50, scale: 0.9, blur: 10 }, spring: "snappy", sfx: "slide", db: -22 });
      if (o.flipAt != null) {
        tl.to(a, { yPercent: -100, opacity: 0, duration: 0.22, ease: E.out, immediateRender: false }, Q(o.flipAt));
        tl.to(b, { yPercent: 0, opacity: 1, duration: 0.3, ease: E.in, immediateRender: false }, Q(o.flipAt + 0.02));
        K.sfx("ui/ui__confirmation-tone__mixkit-2867", o.flipAt, -19);
      }
      return c;
    };

    sc.notif = (par, x, y, w, o = {}) => {
      if (o.scale && o.scale !== 1) {                        // a bigger banner: the card is laid out at w / scale and scaled up
        const wrap = el(par, `left:${x}px;top:${y}px;width:${w / o.scale}px;height:170px;transform:scale(${o.scale});transform-origin:0 0`);
        return sc.notif(wrap, 0, 0, w / o.scale, Object.assign({}, o, { scale: 1 }));
      }
      const c = card(par, x, y, w, 170, `<div style="position:absolute;left:26px;top:26px;display:flex;gap:20px;align-items:flex-start">
          <div class="av" style="background:${o.color || C.acc};width:64px;height:64px;border-radius:17px">${o.icon ? icon(o.icon, 34, "#fff", 2.4) : orbI(36)}</div>
          <div><div style="display:flex;gap:12px;align-items:baseline"><span class="who" style="font-size:28px">${o.app || "Assistant"}</span><span style="font:500 22px Inter;color:#8b8a96">${o.when || "now"}</span></div>
          <div style="font:700 30px/1.25 Inter;color:${C.ink};margin-top:8px">${o.title || ""}</div>
          ${o.body ? `<div style="font:500 26px/1.25 Inter;color:#55536a;margin-top:4px">${o.body}</div>` : ""}</div></div>`, "border-radius:30px;background:rgba(255,255,255,.96)");
      if (o.at != null) land(c, o.at, { from: o.from || { y: -80, scale: 0.92, blur: 10 }, spring: "snappy", sfx: "pop", db: -18 });
      return c;
    };

    sc.shot = (par, x, y, w, src, o = {}) => {
      const sw = o.srcW || 1000, sh = o.srcH || 625, s = w / sw, h = Math.round(sh * s);
      const c = el(par, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;border-radius:${o.radius || 26}px;overflow:hidden;background:#111;box-shadow:0 40px 90px rgba(40,24,90,.28),0 0 0 1px rgba(40,24,90,.08)`);
      const img = el(c, `left:0;top:0;width:${w}px;height:${h}px;background:url(${src}) 0 0/${w}px ${h}px no-repeat`);
      (o.blur || []).forEach(([bx, by, bw, bh]) => el(c, `left:${bx * s}px;top:${by * s}px;width:${bw * s}px;height:${bh * s}px;backdrop-filter:blur(${o.blurPx || 14}px);-webkit-backdrop-filter:blur(${o.blurPx || 14}px);background:rgba(40,40,46,.25)`));
      if (o.at != null) { if (o.tilt) HF.tiltIn(K, c, o.at, { rot: o.tilt, dur: 0.6 }); else land(c, o.at, { from: { y: 80, scale: 0.9, blur: 12 }, spring: "snappy", sfx: "slide", db: -21 }); }
      return { card: c, img, scale: s, h };
    };

    sc.toolPair = (par, x, y, o = {}) => {
      const tile = (name, col, mark) => `<div style="display:flex;flex-direction:column;align-items:center;gap:18px">
        <div style="width:190px;height:190px;border-radius:48px;background:${col};display:flex;align-items:center;justify-content:center;box-shadow:0 26px 60px rgba(40,24,90,.22)">${mark}</div>
        <div style="font:800 40px Inter;color:${o.light ? "#fff" : C.ink};${o.light ? "text-shadow:0 4px 18px rgba(0,0,0,.55)" : ""}">${name}</div></div>`;
      const [an, ac, am] = o.a || ["Claude", "#d97757", icon("spark", 96, "#fff", 2.2)], [bn, bc, bm] = o.b || ["ChatGPT", "#10a37f", icon("chat", 92, "#fff", 2.2)];
      const A = el(par, `left:${x}px;top:${y}px`, tile(an, ac, am || icon("spark", 96, "#fff", 2.2)));
      const or = el(par, `left:${x + 300}px;top:${y + 60}px;font-size:84px;font-style:italic;color:${o.light ? "#fff" : C.mute};${o.light ? "text-shadow:0 4px 18px rgba(0,0,0,.5)" : ""}`, "or", "hf-abs sv");
      const B = el(par, `left:${x + 440}px;top:${y}px`, tile(bn, bc, bm || icon("chat", 92, "#fff", 2.2)));
      if (o.at != null) { land(A, o.at, { from: { y: 60, scale: 0.8, blur: 10 }, spring: "thrown", sfx: "pop", db: -20 });
        land(or, o.at + (o.per || 0.5) * 0.5, { from: { y: 20, scale: 0.8, blur: 6 }, sfx: null });
        land(B, o.at + (o.per || 0.5), { from: { y: 60, scale: 0.8, blur: 10 }, spring: "thrown", sfx: "pop", db: -20 }); }
      return { A, B, or };
    };

    // a full-frame hero hit: a flash, the text slams in huge (Anton), holds, then flies out (o.out) - for payoffs
    sc.slam = (text, t, o = {}) => {
      const L = el(S.TOP, `left:0;top:0;width:${S.WD}px;height:${S.HT}px`);
      K.show(L, t - 0.02, o.out != null ? o.out + 0.3 : t + 1.2);
      if (o.bg) { const bg = el(L, `left:0;top:0;width:${S.WD}px;height:${S.HT}px;background:${o.bg}`); tl.fromTo(bg, { opacity: 0 }, { opacity: o.bgOp || 0.92, duration: 0.08, immediateRender: false }, Q(t)); if (o.out != null) tl.to(bg, { opacity: 0, duration: 0.2, immediateRender: false }, Q(o.out)); }
      const fl = el(L, `left:0;top:0;width:${S.WD}px;height:${S.HT}px;background:#fff`);
      tl.fromTo(fl, { opacity: 0.7 }, { opacity: 0, duration: 0.28, immediateRender: false }, Q(t));
      const tx = el(L, `left:0;top:${o.y || 640}px;width:${S.WD}px;text-align:center;font:400 ${o.size || 300}px/0.9 Anton,Inter,sans-serif;color:${o.color || C.acc};letter-spacing:-.01em;${o.shadow ? "text-shadow:0 14px 50px rgba(0,0,0,.35);" : ""}`, text);
      const sp = HF.spring(HF.SPRING.snappy);
      tl.fromTo(tx, { scale: 2.2, opacity: 0 }, { scale: 1, opacity: 1, duration: sp.duration, ease: sp.ease, immediateRender: true }, Q(t));
      tl.fromTo(tx, { y: 0 }, { y: -18, duration: 1.2, ease: "none", immediateRender: false }, Q(t + 0.2));
      if (o.out != null) tl.to(tx, { scale: 0.6, opacity: 0, y: -120, duration: 0.24, ease: E.out, immediateRender: false }, Q(o.out));
      K.sfx("impact/impact__exciting-fast-hit__mixkit-2180", t, o.db || -13);
      return { L, tx };
    };

    sc.bars = (par, x, y, w, h, o = {}) => {
      const vs = o.values || [0.35, 0.6, 0.45, 0.9, 0.55], n = vs.length, g = 16, bw = (w - (n - 1) * g) / n;
      return vs.map((v, i) => {
        const b = el(par, `left:${x + i * (bw + g)}px;top:${y + h * (1 - v)}px;width:${bw}px;height:${h * v}px;border-radius:14px;background:${(o.hi || []).includes(i) ? C.acc : o.color || "#cfc8ea"};transform-origin:50% 100%`);
        if (o.at != null) tl.fromTo(b, { scaleY: 0 }, { scaleY: 1, duration: 0.5, ease: E.in, immediateRender: true }, Q(o.at + i * 0.06));
        return b;
      });
    };
    return sc;
  };
})(window);
