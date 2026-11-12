/* kit/hf/kinetic.js — v8 motion: motion tokens, real springs, staggers and kinetic type (needs core.js).
 *
 *   HF.E.in / .emph / .out / .move          eases (cubic beziers): entrances, hero entrances, exits, repositioning
 *   HF.spring(HF.SPRING.snappy)             -> { ease, duration, land }: a damped spring as a GSAP ease
 *   HF.stagger(n, per, cap)                 -> offsets: per item, the whole run capped (2 frames each, 0.5 s max)
 *   HF.land(K, el, t, { from, spring, sfx })  an entrance that animates 3 properties with offsets and lands on a spring
 *   HF.leave(K, el, t, { to })              an exit as designed as the entrance (accelerates away, shorter)
 *   const kt = HF.kinetic(K, parent, { text: "Four *hours* to edit", at: t, style: "slam", x, y, w, size })
 *     styles: slam, pop, rise, track; cascade (letters flip up out of each word's mask) and focus (each word pulls from
 *     blur into focus), 2026-10-20, set in the look's display face (face: "look"; any style can take it)
 *   const kt = HF.kinetic(K, parent, { from: 120, to: 126, stress: [123], style: "rise" })   // timed to the speech
 *   kt.out(t)                               // every word leaves, 1 frame apart
 *   HF.morph(K, parent, ["x", "check"], [t], { x, y, size, color })   one stroke icon becomes the next (MorphSVG):
 *                                           a cross into a tick on a verdict, play into pause; names from HF.ICON or path data
 *   HF.drawIcon(K, parent, "rocket", t, { x, y, size, color, dur })   an icon draws itself on, stroke by stroke (DrawSVG):
 *                                           any HF.ICON or Lucide name (kit/hf/lucide.js), instead of fading in
 *   HF.shake(K, el, t, { strength, wiggles })   a designed "no": a quick decaying side-to-side shake (CustomWiggle) and the
 *                                           fail sound, for a wrong answer, a failed run, a rejected idea
 *
 * Why (research, 2026-10-07): designer motion differs from programmatic motion in its curves (no stock eases), in
 * animating several properties with offsets, in springs that settle instead of tweens that stop, in staggers with a
 * capped total, in exits as designed as entrances, and in sound that lands on the motion's landing frame (0–1 frame
 * early, never late). The numbers below are Apple's fluid-interface springs (damping ratio + response) and the
 * easings.net / Material 3 curves.
 *
 * Exact: every value is a pure function of timeline time (closed-form springs, no requestAnimationFrame, no
 * Math.random), so any frame seeks to the same picture. Opt-in: core.js keeps preset_paper_studio's calm defaults.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/kinetic.js needs core.js first");

  // ---------------------------------------------------------------- 1. curves
  // cubic-bezier(x1, y1, x2, y2) as an ease: solve x(s) = p for s (Newton, then bisection), return y(s)
  HF.bezier = function (x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const X = (s) => ((ax * s + bx) * s + cx) * s, Y = (s) => ((ay * s + by) * s + cy) * s, dX = (s) => (3 * ax * s + 2 * bx) * s + cx;
    return function (p) {
      if (p <= 0) return 0;
      if (p >= 1) return 1;
      let s = p;
      for (let i = 0; i < 8; i++) {
        const e = X(s) - p, d = dX(s);
        if (Math.abs(e) < 1e-7) return Y(s);
        if (Math.abs(d) < 1e-6) break;
        s -= e / d;
      }
      let lo = 0, hi = 1;
      s = p;
      for (let i = 0; i < 40; i++) {
        const x = X(s);
        if (Math.abs(x - p) < 1e-7) break;
        if (x < p) lo = s; else hi = s;
        s = (lo + hi) / 2;
      }
      return Y(s);
    };
  };
  HF.E = {
    in: HF.bezier(0.16, 1, 0.3, 1),       // ease-out-expo: entrances (fast start, long soft landing)
    emph: HF.bezier(0.05, 0.7, 0.1, 1),   // Material 3 emphasized decelerate: hero titles, big reveals
    out: HF.bezier(0.7, 0, 0.84, 0),      // ease-in-expo: exits accelerate away
    move: HF.bezier(0.65, 0, 0.35, 1),    // in-out: moving something already on screen
  };
  HF.T = { in: 0.55, hero: 0.8, out: 0.26, move: 0.6, per: 2, cap: 0.5 };   // seconds; stagger per item in frames

  // ---------------------------------------------------------------- 2. springs
  // Apple's model: dampingRatio 1 = no bounce (UI), < 1 bounces (only for things with momentum); response = the
  // period of the undamped oscillation in seconds (smaller = snappier).
  HF.SPRING = {
    ui: { ratio: 1, response: 0.4 },        // cards, panels, UI: settles without overshoot
    snappy: { ratio: 0.82, response: 0.32 }, // slams and badges: a ~1 % overshoot, fast
    thrown: { ratio: 0.68, response: 0.42 }, // things with momentum (pops, stickers): ~5 % overshoot
    soft: { ratio: 1, response: 0.65 },      // big, slow, heavy things (full-screen panels)
  };
  const springCache = new Map();
  HF.spring = function (o = HF.SPRING.ui, eps = 0.0008) {
    const ratio = o.ratio != null ? o.ratio : 1, response = o.response || 0.4;
    const key = ratio + "|" + response + "|" + eps;
    if (springCache.has(key)) return springCache.get(key);
    const w0 = (2 * Math.PI) / response, z = ratio;
    let y;                                   // displacement from the target, 1 at t=0, at rest (v=0)
    if (z < 1) {
      const wd = w0 * Math.sqrt(1 - z * z), k = (z * w0) / wd;
      y = (t) => Math.exp(-z * w0 * t) * (Math.cos(wd * t) + k * Math.sin(wd * t));
    } else if (z === 1) {
      y = (t) => Math.exp(-w0 * t) * (1 + w0 * t);
    } else {
      const s = Math.sqrt(z * z - 1), r1 = -w0 * (z - s), r2 = -w0 * (z + s);
      y = (t) => (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r2 - r1);
    }
    // settle: the last time |y| exceeds eps (sampled finely), so the ease ends exactly at rest
    let settle = 0, overshoot = 0, land = null;
    for (let t = 0; t < 6; t += 1 / 600) {
      const v = y(t);
      if (Math.abs(v) > eps) settle = t;
      overshoot = Math.max(overshoot, -v);
      if (land == null && v <= 0.02) land = t;    // the visible "landing": within 2 % of the target
    }
    const duration = Math.max(1 / 30, settle + 1 / 600);
    const ease = (p) => (p <= 0 ? 0 : p >= 1 ? 1 : 1 - y(p * duration));
    const out = { ease, duration, land: land == null ? duration : land, overshoot };
    springCache.set(key, out);
    return out;
  };

  // ---------------------------------------------------------------- 3. stagger
  // offsets for n items: `per` seconds apart, the whole run squeezed under `cap` (hierarchy: the first item leads)
  HF.stagger = (n, per = HF.T.per / 30, cap = HF.T.cap) => {
    const step = n > 1 ? Math.min(per, cap / (n - 1)) : 0;
    return Array.from({ length: n }, (_, i) => i * step);
  };

  // ---------------------------------------------------------------- 4. entrances and exits
  const springOf = (s) => (typeof s === "string" ? HF.spring(HF.SPRING[s]) : s && s.ease ? s : HF.spring(s || HF.SPRING.ui));

  // an entrance: opacity fades fast, the transform lands on a spring, blur clears with an expo ease; scale leads by
  // a frame so the move reads as one push, not three tweens
  HF.land = function (K, el, t, o = {}) {
    const tl = K.tl, Q = K.Q, f = 1 / K.fps;
    const sp = springOf(o.spring || "ui");
    const from = { y: 36, x: 0, scale: 0.96, rotation: 0, blur: 10, ...(o.from || {}) };
    if (t <= 0) return t;                    // already in place on frame 1 (never animate at time 0)
    tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: Math.min(0.2, sp.duration), ease: HF.E.in }, Q(t));
    tl.fromTo(el, { scale: from.scale }, { scale: 1, duration: sp.duration, ease: sp.ease }, Q(t));
    tl.fromTo(el, { x: from.x, y: from.y, rotation: from.rotation }, { x: 0, y: 0, rotation: 0, duration: sp.duration, ease: sp.ease }, Q(t + f));
    if (from.blur) tl.fromTo(el, { filter: `blur(${from.blur}px)` }, { filter: "blur(0px)", duration: Math.min(0.45, sp.duration), ease: HF.E.in }, Q(t));
    const landed = t + f + sp.land;
    if (o.sfx) K.sfx(o.sfx, Math.max(0, landed - f), o.sfxDb);   // sound leads the landing by a frame, never lags
    return landed;
  };

  HF.leave = function (K, el, t, o = {}) {
    const to = { y: -24, x: 0, scale: 1, blur: 8, ...(o.to || {}) }, dur = o.dur || HF.T.out;
    K.tl.to(el, { opacity: 0, x: to.x, y: to.y, scale: to.scale, filter: `blur(${to.blur}px)`, duration: dur, ease: HF.E.out,
      immediateRender: false }, K.Q(t));
    return t + dur;
  };

  // ---------------------------------------------------------------- 5. kinetic type
  const FACES = { anton: '"Anton", "Inter", sans-serif', montserrat: '"Montserrat", "Inter", sans-serif',
    serif: '"InstrumentSerif", serif', inter: '"Inter", sans-serif' };
  const STYLE = {                             // per style: face, weight, case, tracking, default sfx
    slam: { face: "anton", weight: 400, upper: true, track: "0.01em", sfx: "hit" },
    pop: { face: "montserrat", weight: 900, upper: true, track: "-0.01em", sfx: "pop" },
    rise: { face: "serif", weight: 400, upper: false, track: "-0.01em", sfx: null },
    track: { face: "montserrat", weight: 800, upper: true, track: "0.02em", sfx: "swish" },
    // 2026-10-20: letters flip up into place inside each word's mask, one frame apart (always split by character)
    cascade: { face: "look", weight: 800, upper: false, track: "-0.015em", sfx: null, chars: true },
    // 2026-10-20: each word pulls from a soft blur into focus as it is said (a rack focus on the line)
    focus: { face: "look", weight: 700, upper: false, track: "-0.01em", sfx: null },
  };

  HF.kinetic = function (K, parent, o = {}) {
    const tl = K.tl, Q = K.Q, f = 1 / K.fps, C = HF.C;
    const style = o.style || "slam", S = STYLE[style];
    if (!S) throw new Error(`HF.kinetic: unknown style ${style} (slam, pop, rise, track, cascade, focus)`);
    const split = o.split || (S.chars ? "char" : null);
    const masked = style === "rise" || style === "cascade";
    // the words: from a word-id range of the cut (text + spoken times), or from a string with *stress and | breaks
    let items;
    if (o.from != null) {
      const ws = K.words_.filter((w) => w.i >= o.from && w.i <= (o.to != null ? o.to : o.from));
      if (!ws.length) throw new Error(`HF.kinetic: no words ${o.from}..${o.to} in the cut`);
      const stress = new Set(o.stress || []);
      items = ws.map((w) => ({ text: String(w.text).replace(/[.,!?;:]+$/, o.keepPunct ? "$&" : ""), t: w.t, stress: stress.has(w.i), br: false }));
    } else {
      // "*word*", "*word" and "*several words*" are stressed: a span opens at a leading * when a later word closes it
      const toks = [];
      String(o.text || "").split("|").forEach((line, li) => line.trim().split(/\s+/).filter(Boolean).forEach((tok, k) => toks.push({ tok, br: li > 0 && k === 0 })));
      let open = false;
      items = toks.map(({ tok, br }, k) => {
        const starts = tok.startsWith("*"), ends = tok.length > 1 && tok.endsWith("*");
        const stress = open || starts;
        if (starts && !ends && toks.slice(k + 1).some((x) => x.tok.endsWith("*"))) open = true;
        if (ends) open = false;
        return { text: tok.replace(/^\*|\*$/g, ""), stress, br, t: null };
      });
    }
    // when each word comes in: spoken time minus a frame (the eye leads the ear), or `at` + a capped stagger
    const lead = o.lead != null ? o.lead : f;
    if (Array.isArray(o.at)) items.forEach((it, k) => { it.t = o.at[Math.min(k, o.at.length - 1)]; });
    else if (o.at != null || items.some((it) => it.t == null)) {
      const offs = HF.stagger(items.length, o.per != null ? o.per : (style === "track" ? 1 : 3) / K.fps, o.cap != null ? o.cap : HF.T.cap);
      items.forEach((it, k) => { it.t = (o.at || 0) + offs[k]; });
    } else items.forEach((it) => { it.t = Math.max(0, it.t - lead); });

    const size = o.size || 140, acc = o.accent || C.acc, color = o.color || C.ink;
    // face "look": the film's display face and weight (HF.F, set by the frame's look), so the type belongs to the look
    const face = o.face || S.face, lookFace = face === "look";
    const box = K.el(parent, `left:${o.x != null ? o.x : 60}px; top:${o.y != null ? o.y : 600}px; width:${o.w || K.width - 120}px;` +
      `font-family:${lookFace ? HF.F.display : FACES[face] || face}; font-weight:${o.weight || (lookFace ? HF.F.displayWeight || S.weight : S.weight)}; font-size:${size}px; line-height:${o.lh || 1.02};` +
      `color:${color}; text-align:${o.align || "center"}; letter-spacing:${S.track}; ${(o.upper != null ? o.upper : S.upper) ? "text-transform:uppercase;" : ""}`);
    // consecutive stressed words share one highlight box ("4 HOURS" is one phrase, not two stickers)
    const boxed = (o.stressStyle || "box") === "box";
    let group = null;
    const words = items.map((it, k) => {
      if (it.br) { box.append(document.createElement("br")); group = null; }
      const wrap = document.createElement("span");
      wrap.style.cssText = "display:inline-block; position:relative; vertical-align:bottom; margin:0 0.11em;" +
        (masked ? "overflow:hidden; padding:0.04em 0.06em 0.16em; margin-bottom:-0.12em;" : "") + (style === "cascade" ? "perspective:600px;" : "");
      let hl = null;
      if (it.stress && boxed) {
        if (!group || !items[k - 1] || !items[k - 1].stress) {
          group = document.createElement("span");
          group.style.cssText = "display:inline-block; position:relative; isolation:isolate; white-space:nowrap; vertical-align:bottom;";
          hl = document.createElement("span");
          hl.style.cssText = `position:absolute; left:0.02em; right:0.02em; top:0.06em; bottom:0.02em; background:${acc}; z-index:-1;` +
            `border-radius:${o.radius != null ? o.radius : 0.06}em; transform-origin:0% 50%; transform:rotate(${o.tilt != null ? o.tilt : -2}deg)`;
          group.append(hl);
          box.append(group);
        }
      } else group = null;
      const inner = document.createElement("span");
      inner.style.cssText = "display:inline-block; will-change:transform;";
      if (it.stress) inner.style.color = boxed ? (o.onAccent || "#ffffff") : acc;   // every word in a box, not just the first
      if (split === "char") [...it.text].forEach((ch, j) => { const c = document.createElement("span"); c.style.display = "inline-block"; c.dataset.kc = j; c.textContent = ch; inner.append(c); });
      else inner.textContent = it.text;
      wrap.append(inner);
      (it.stress && boxed ? group : box).append(wrap);
      return { ...it, wrap, inner, hl, group: it.stress && boxed ? group : null };
    });

    // motion per style; char split staggers the letters inside each word (1 frame, the word capped at 0.25 s)
    const sfxMode = o.sfx === undefined ? "stress" : o.sfx;          // "each" | "stress" | "first" | null | false
    const sfxName = o.sfxName || S.sfx;
    let lastLand = 0;
    words.forEach((w, k) => {
      const targets = split === "char" ? [...w.inner.children] : [w.inner];
      const offs = HF.stagger(targets.length, f, 0.25);
      const big = w.stress ? (o.stressScale || 1.0) : 1;
      let landed = w.t;
      targets.forEach((el, j) => {
        const t = w.t + offs[j];
        if (t <= 0) return;
        if (style === "rise") {
          // hidden until it rises: under its mask the 6 px blur bled up into view as a faint dashed line (kit-v10-sample
          // critic round 3, 2026-10-20)
          tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 2 * f, ease: "none" }, Q(t));
          tl.fromTo(el, { yPercent: 112, filter: "blur(6px)" }, { yPercent: 0, filter: "blur(0px)", duration: HF.T.in + 0.1, ease: HF.E.in }, Q(t));
          landed = Math.max(landed, t + 0.18);
        } else if (style === "slam") {
          const sp = HF.spring(HF.SPRING.snappy);
          tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 2 * f, ease: "none" }, Q(t));
          tl.fromTo(el, { scale: 1.9 * big, filter: "blur(10px)" }, { scale: big, filter: "blur(0px)", duration: sp.duration, ease: sp.ease }, Q(t));
          landed = Math.max(landed, t + sp.land);
        } else if (style === "pop") {
          const sp = HF.spring(HF.SPRING.thrown);
          tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 3 * f, ease: "none" }, Q(t));
          tl.fromTo(el, { scale: 0.35, y: 40 }, { scale: big, y: 0, duration: sp.duration, ease: sp.ease }, Q(t));
          landed = Math.max(landed, t + sp.land);
        } else if (style === "cascade") {        // up from under the word's mask, tipping forward into place
          const sp = HF.spring(HF.SPRING.snappy);
          tl.fromTo(el, { yPercent: 105, rotateX: -80, transformOrigin: "50% 100%", opacity: 0 },
            { yPercent: 0, rotateX: 0, opacity: 1, duration: sp.duration, ease: sp.ease }, Q(t));
          landed = Math.max(landed, t + sp.land);
        } else if (style === "focus") {          // a rack focus: soft and slightly large, then sharp
          tl.fromTo(el, { opacity: 0, filter: "blur(16px)", scale: 1.12 },
            { opacity: 1, filter: "blur(0px)", scale: 1, duration: HF.T.hero, ease: HF.E.emph }, Q(t));
          landed = Math.max(landed, t + 0.28);
        } else if (style === "track") {
          tl.fromTo(el, { opacity: 0, filter: "blur(14px)", letterSpacing: "0.32em" },
            { opacity: 1, filter: "blur(0px)", letterSpacing: "0em", duration: HF.T.hero, ease: HF.E.emph }, Q(t));
          landed = Math.max(landed, t + 0.3);
        }
      });
      if (w.hl && w.t > 0) w.hlAt = Math.max(w.t + 3 * f, landed - 2 * f);     // the box draws once its first word lands
      const wantSfx = sfxMode === "each" || (sfxMode === "stress" && w.stress) || (sfxMode === "first" && k === 0);
      if (sfxName && wantSfx && w.t > 0) K.sfx(sfxName, Math.max(0, landed - f), o.sfxDb);
      lastLand = Math.max(lastLand, landed);
    });
    words.forEach((w) => { if (w.hl && w.hlAt != null) tl.fromTo(w.hl, { scaleX: 0 }, { scaleX: 1, duration: 0.32, ease: HF.E.in }, Q(w.hlAt)); });
    // a slam lands with a small impact on the whole line (3 px, settles in ~0.2 s)
    if (style === "slam" && o.impact !== false && words.length && words[0].t > 0) {
      const sp = HF.spring({ ratio: 0.45, response: 0.12 });
      words.forEach((w) => { if (w.stress) tl.fromTo(box, { y: 7 }, { y: 0, duration: sp.duration, ease: sp.ease, immediateRender: false }, Q(w.t + HF.spring(HF.SPRING.snappy).land)); });
    }
    const api = {
      box, words, landed: lastLand,
      out(t, dir = 1) {                      // leave 1 frame apart, in reading order (dir -1: last word first)
        const order = dir < 0 ? words.slice().reverse() : words;
        order.forEach((w, k) => HF.leave(K, w.inner, t + k * f, { to: { y: masked ? 0 : -30, blur: 8 } }));
        if (masked) order.forEach((w, k) => tl.to(w.inner, { yPercent: -110, duration: HF.T.out, ease: HF.E.out, immediateRender: false }, Q(t + k * f)));
        words.forEach((w) => { if (w.hl) tl.to(w.hl, { scaleX: 0, transformOrigin: "100% 50%", duration: HF.T.out, ease: HF.E.out, immediateRender: false }, Q(t)); });
        return t + (order.length - 1) * f + HF.T.out;
      },
    };
    return api;
  };
  // ---------------------------------------------------------------- 6. icon morphs and the "no" shake (2026-10-20)
  // GSAP's MorphSVG and CustomWiggle (vendor.py LIBS; free under the standard GSAP license). Both are tweens on the paused
  // timeline: any frame seeks to the same picture. Without the plugins (an older vendor/ folder) morph crossfades and
  // shake uses a damped sine, so a page never breaks.
  const pathsOf = (svg, icon) => {                          // an HF.ICON name or raw path data -> one compound "d"
    if (/^[Mm]/.test(icon)) return icon;
    if (!HF.iconSvg(icon)) throw new Error("HF.morph: no icon " + icon);
    svg.innerHTML = HF.iconSvg(icon);
    const ds = [...svg.children].map((el) => {
      if (el.tagName === "path") return el.getAttribute("d");
      if (root.MorphSVGPlugin) { const p = root.MorphSVGPlugin.convertToPath(el)[0]; return p && p.getAttribute("d"); }
      return null;
    }).filter(Boolean);
    svg.innerHTML = "";
    return ds.join(" ");
  };
  HF.morph = function (K, parent, icons, times, o = {}) {
    const C = HF.C, tl = K.tl, Q = K.Q, size = o.size || 160;
    const box = K.el(parent, `left:${o.x || 0}px;top:${o.y || 0}px;width:${size}px;height:${size}px;opacity:${o.at != null ? 0 : 1}`);
    const NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("width", size); svg.setAttribute("height", size);
    svg.style.cssText = "position:absolute;left:0;top:0;overflow:visible";
    box.append(svg);
    const ds = icons.map((ic) => pathsOf(svg, ic));
    const mk = (d) => { const p = document.createElementNS(NS, "path"); p.setAttribute("d", d); p.setAttribute("fill", "none");
      p.setAttribute("stroke", o.color || C.ink); p.setAttribute("stroke-width", o.width || 2.2); p.setAttribute("stroke-linecap", "round");
      p.setAttribute("stroke-linejoin", "round"); svg.append(p); return p; };
    const path = mk(ds[0]);
    if (root.MorphSVGPlugin) gsap.registerPlugin(root.MorphSVGPlugin);
    ds.slice(1).forEach((d, k) => {
      const t = times[Math.min(k, times.length - 1)], dur = o.dur || 0.5;
      const col = o.colors && o.colors[k + 1];
      if (root.MorphSVGPlugin) tl.to(path, { morphSVG: { shape: d, type: o.type || "linear" }, duration: dur, ease: HF.E.emph, immediateRender: false }, Q(t));
      else { const nx = mk(d); tl.fromTo(nx, { opacity: 0 }, { opacity: 1, duration: dur, immediateRender: false }, Q(t)); tl.to(path, { opacity: 0, duration: dur, immediateRender: false }, Q(t)); }
      if (col) tl.to(path, { stroke: col, duration: dur, ease: "none", immediateRender: false }, Q(t));
      tl.fromTo(box, { scale: 1 }, { scale: 1.12, duration: dur * 0.45, ease: HF.E.out, yoyo: true, repeat: 1, immediateRender: false }, Q(t));
      if (o.sfx !== false) K.sfx(o.sfxName || "ui/ui__modern-click-box-check__mixkit-1120", t + dur * 0.5, o.db != null ? o.db : -18);
    });
    if (o.at != null) tl.fromTo(box, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.35, ease: HF.E.in, immediateRender: false }, Q(o.at));
    return { box, svg, path };
  };
  HF.drawIcon = function (K, parent, name, t, o = {}) {
    const inner = HF.iconSvg(name);
    if (!inner) throw new Error("HF.drawIcon: no icon " + name);
    const size = o.size || 140, dur = o.dur || 0.7;
    const box = K.el(parent, `left:${o.x || 0}px;top:${o.y || 0}px;width:${size}px;height:${size}px`);
    box.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${o.color || HF.C.ink}" stroke-width="${o.width || 2}" stroke-linecap="round" stroke-linejoin="round" style="overflow:visible">${inner}</svg>`;
    const parts = [...box.querySelectorAll("path, rect, circle, line, polyline, polygon, ellipse")];
    const offs = HF.stagger(parts.length, 3 / K.fps, dur * 0.5);
    if (root.DrawSVGPlugin) gsap.registerPlugin(root.DrawSVGPlugin);
    parts.forEach((p, k) => {
      if (root.DrawSVGPlugin) K.tl.fromTo(p, { drawSVG: "0% 0%" }, { drawSVG: "0% 100%", duration: dur, ease: HF.E.in, immediateRender: true }, K.Q(t + offs[k]));
      else K.tl.fromTo(p, { opacity: 0 }, { opacity: 1, duration: dur, ease: "none", immediateRender: true }, K.Q(t + offs[k]));
    });
    return { box, parts };
  };
  HF.shake = function (K, el, t, o = {}) {
    const n = o.wiggles || 5, dur = o.dur || 0.45, s = o.strength || 14;
    let ease;
    if (root.CustomEase && root.CustomWiggle) {
      gsap.registerPlugin(root.CustomEase, root.CustomWiggle);
      ease = root.CustomWiggle.create("hfShake" + n, { wiggles: n, type: "easeOut" });
    } else ease = (p) => Math.sin(p * n * 2 * Math.PI) * (1 - p);
    K.tl.to(el, { x: "+=" + s, duration: dur, ease, immediateRender: false }, K.Q(t));
    if (o.sfx !== false) K.sfx(o.sfxName || "ui/ui__wrong-answer-fail-notification__mixkit-946", t, o.db != null ? o.db : -16, true);
    return t + dur;
  };
})(typeof window !== "undefined" ? window : globalThis);
