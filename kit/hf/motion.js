/* kit/hf/motion.js — the A-roll camera: a motion vocabulary, a director that picks moves from the edit, and an
 * evaluator that gives the camera transform at any time. Pure math (no DOM, no randomness): the same file runs in
 * the page (HF.camera uses it) and in Node (kit/motion/bake.py asks it for the motion-blur sub-frames).
 *
 *   const P = HF.motion.direct({ pieces, words, fps: 30, framing: { intro: "W", demo: "PIP" }, format: "long",
 *                                tags: { punch: [ids], joke: [ids], story: [[id0, id1]], section: [ids] },
 *                                faces: [[cx, cy, size], ...] });   // optional per-frame face track (output frames)
 *   HF.motion.at(P, t)        -> { m: [a, b, c, d, e, f], clip, view, top, move }   CSS matrix() of the A-roll, origin 0 0
 *   HF.motion.samples(P, f)   -> [m, ...]   sub-frame matrices for motion blur at output frame f ([m] = no blur)
 *   HF.motion.windows(P)      -> [{ f0, f1, view, top, frames: [[m, ...], ...] }]   the frames that need blur
 *   node kit/motion/plan.cjs in.json out.json   plan + blur windows as JSON (in = the direct() options)
 *
 * The vocabulary (long-form defaults; "reel" is denser, see RULES):
 *   reframe   hard cut between two framings (wide 1.0 <-> tight 1.15 in W) at a new thought; held for the thought
 *   punch     hard cut to 1.22-1.32 just before a stressed word, held to the end of the line, hard cut back
 *   ease      eased punch: x1.18 in 15 frames (power3.out), 180 deg shutter blur, held to the end of the line
 *   snap      crash zoom to 1.4 in 5 frames (expo out .16,1,.3,1) with a 3% overshoot settling in 8 frames, 270 deg
 *             shutter blur and a landing shake (1% of the height, 0.4 deg, 7 frames, 9/11.3/7.4 Hz); a swish cue
 *   push      slow push +5-10% over a 4-10 s story passage (sine in-out), then a hard cut back out
 *   zoomx     zoom transition: 100 -> 300% in 6 frames (expo in) into a section cut, 300 -> 100% out (expo out), 330 deg
 *   drift     every held framing creeps in ~0.6%/s, easing out at +3% (a held shot is never a still)
 * Scale is interpolated in log space and the eyes (not the top-left corner) are interpolated, so the face never swims.
 * Composition: eyes on the upper third with a sliver of headroom (3% above the hair), the face at the layout's x (W/M/C centre, SR right,
 * SL left), clamped so the picture always covers the frame.
 *
 * The lens (2026-10-22, v11; the section at the end): the camera on him INSIDE a shape (canvas speakers, HF.box), not a
 * full-frame A-roll: HF.motion.lens plans pushes / pull-outs / arcs / settles / punches / jump reframes, P.at(t) gives
 * { k, dx, dy, rot, move }, HF.motion.lensFrame turns that into the footage's matrix for one shape (cover clamp, roll,
 * clean rect, zoom budget), HF.motion.jumps is the one jump-cut reframe. kit/hf/README.md "The lens".
 */
(function (root) {
  const HF = root.HF || (root.HF = {});
  const MO = (HF.motion = {});
  MO.version = "2.1.0";                                                  // 2.1: the lens

  // films' face = [cx, cy, size]: YuNet box centre and head width (films/*/face_track.py). Measured on jobs/ew2: YuNet's
  // eye landmarks sit 0.20 head widths above the box centre (40 frames); the top of the (thick) hair ~1.1 (5 frames).
  const EYE_K = 0.2, HEAD_K = 1.1;
  MO.EYE_K = EYE_K;
  MO.HEAD_K = HEAD_K;

  // ---------------------------------------------------------------- easing
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const X = (t) => ((ax * t + bx) * t + cx) * t, Y = (t) => ((ay * t + by) * t + cy) * t, DX = (t) => (3 * ax * t + 2 * bx) * t + cx;
    return (x) => {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      let t = x;
      for (let i = 0; i < 8; i++) {
        const e = X(t) - x, d = DX(t);
        if (Math.abs(e) < 1e-9) return Y(t);
        if (Math.abs(d) < 1e-6) break;
        t -= e / d;
        if (t < 0 || t > 1) break;
      }
      let lo = 0, hi = 1;
      t = x;
      for (let i = 0; i < 60; i++) { const v = X(t); if (Math.abs(v - x) < 1e-9) break; if (v < x) lo = t; else hi = t; t = (lo + hi) / 2; }
      return Y(t);
    };
  }
  const EASE = {
    none: (p) => p,
    sine: bezier(0.37, 0, 0.63, 1),                                       // sine in-out
    p3out: (p) => 1 - Math.pow(1 - p, 3),                                 // power3.out
    p3inout: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    expo: bezier(0.16, 1, 0.3, 1),                                        // expo out, the snap
    expoIn: (p) => (p <= 0 ? 0 : Math.pow(2, 10 * p - 10)),
    expoOut: (p) => (p >= 1 ? 1 : 1 - Math.pow(2, -10 * p)),
  };
  MO.EASE = EASE;
  MO.bezier = bezier;
  const clamp01 = (p) => Math.max(0, Math.min(1, p));

  // ---------------------------------------------------------------- rules and scales
  MO.RULES = {
    long: {
      hold: 3.0,               // a reframe needs the framing held this long (a thought, never A/B on every cut)
      holdMax: 9.0,            // a framing held longer than this may reframe at a clause cut
      minThought: 1.2,         // ... and needs this much of the new thought left to hold
      drift: 0.006, driftCap: 0.03,
      third: 1 / 3, headroom: 0.03,
      punch: { gap: 16, s: [1.22, 1.32], mult: 1.2, hold: [0.8, 3.2], lead: 2 },        // ~1 per 15-20 s
      ease: { frames: 15, mult: 1.18, lead: 0.24, shutter: 180, max: 8 },
      snap: { gap: 25, s: 1.4, frames: 5, overshoot: 0.03, settle: 8, lead: 3, shutter: 270, max: 24,
        shake: { amp: 0.01, rot: 0.4, frames: 7, hz: [9.0, 11.3, 7.4] } },
      push: { gap: 30, rate: 0.012, amount: [0.05, 0.1], len: [4, 14] },
      zoomx: { frames: 6, peak: 3.0, shutter: 330, max: 32 },
      auto: true,
    },
    reel: {
      hold: 1.5, holdMax: 4.5, minThought: 0.8,
      drift: 0.008, driftCap: 0.035,
      third: 1 / 3, headroom: 0.03,
      punch: { gap: 6, s: [1.28, 1.4], mult: 1.25, hold: [0.6, 2.4], lead: 2 },
      ease: { frames: 12, mult: 1.2, lead: 0.2, shutter: 180, max: 8 },
      snap: { gap: 10, s: 1.5, frames: 4, overshoot: 0.03, settle: 8, lead: 3, shutter: 270, max: 24,
        shake: { amp: 0.012, rot: 0.5, frames: 7, hz: [9.0, 11.3, 7.4] } },
      push: { gap: 15, rate: 0.015, amount: [0.05, 0.1], len: [3, 10] },
      zoomx: { frames: 6, peak: 3.0, shutter: 330, max: 32 },
      auto: true,
    },
  };
  // framing variants per layout: [wide, tight]; a reframe flips between them (>= 1.12x apart: less reads as a glitch)
  MO.SCALES = { W: [1.0, 1.15], M: [1.12, 1.26], C: [1.24, 1.36], SR: [1.2, 1.34], SL: [1.2, 1.34], P: [1.0, 1.15] };
  const FULL = { W: 1, M: 1, C: 1, P: 1, H: 1 }, SIDE = { SR: 1, SL: 1 }, SMALL = { PIP: 1, OFF: 1 };
  MO.FULL = FULL; MO.SIDE = SIDE; MO.SMALL = SMALL;
  const MAXS = 1.5;                                                       // never past this outside a zoom transition
  // sound cues (kit/sfx): [file, seconds from the file's start to its peak (lined up with the move), gain dB]
  // [file, its measured peak (s: kept for reference; since 2026-10-11 kit/audio/mix.py aligns the peak to the cue itself), dB]
  MO.SFX = { snap: ["whoosh/whoosh__fast-transitions-swoosh__mixkit-3115", 0.114, -20],
    zoomx: ["whoosh/whoosh__fast-small-sweep-transition__mixkit-166", 0.336, -23] };

  function merge(a, b) {
    const o = Array.isArray(a) ? a.slice() : Object.assign({}, a);
    for (const k in b || {}) o[k] = b[k] && typeof b[k] === "object" && !Array.isArray(b[k]) && a && typeof a[k] === "object" ? merge(a[k], b[k]) : b[k];
    return o;
  }
  const find = (arr, t) => {                                              // the item with t0 <= t < t1 (sorted, no overlap)
    let lo = 0, hi = arr.length - 1, k = -1;
    // 0.1 ms tolerance: edit lists store cut times to 4 decimals, so a cut on frame 1211 (40.36666 s) reads 40.3667 and a
    // 1e-9 tolerance switched the shot one frame after the picture cut (a one-frame pop, critic round 3)
    while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m].t0 <= t + 1e-4) { k = m; lo = m + 1; } else hi = m - 1; }
    return k < 0 ? arr[0] : arr[k];
  };

  // ---------------------------------------------------------------- composition
  function clampXY(P, view, s, x, y) {
    const [VW, VH] = view, [SW, SH] = P.src;
    const x0 = VW - SW * s, y0 = VH - SH * s;
    return [x0 > 0 ? x0 / 2 : Math.min(0, Math.max(x0, x)), y0 > 0 ? y0 / 2 : Math.min(0, Math.max(y0, y))];
  }
  // where the framing at scale s puts the picture: eyes on the upper third (with headroom), face at the layout's x
  function place(P, sh, s, face) {
    const view = sh.view || P.view, [VW, VH] = view, R = P.R;
    const [cx, cy, sz] = face, ey = cy - EYE_K * sz;
    const tx = sh.layout === "SR" ? VW * 0.651 : sh.layout === "SL" ? VW * 0.333 : VW / 2;
    const ty = Math.max(VH * R.third, R.headroom * VH + (HEAD_K - EYE_K) * sz * s);
    const [x, y] = clampXY(P, view, s, tx - cx * s, ty - ey * s);
    return { s, x, y };
  }
  const eyes = (face) => [face[0], face[1] - EYE_K * face[2]];
  // between two framings of the same face: log-space scale, the eyes move in a straight line
  function blend(P, sh, A, B, e, face) {
    const s = A.s * Math.pow(B.s / A.s, e), [ax, ay] = eyes(face);
    const px = A.x + ax * A.s + (B.x + ax * B.s - A.x - ax * A.s) * e, py = A.y + ay * A.s + (B.y + ay * B.s - A.y - ay * A.s) * e;
    const [x, y] = clampXY(P, sh.view || P.view, s, px - ax * s, py - ay * s);
    return { s, x, y };
  }
  // zoom about the eyes from a framing (zoom transitions)
  function about(P, sh, A, s, face) {
    const [ax, ay] = eyes(face), px = A.x + ax * A.s, py = A.y + ay * A.s;
    const [x, y] = clampXY(P, sh.view || P.view, s, px - ax * s, py - ay * s);
    return { s, x, y };
  }
  function smallState(P, layout, face) {                                // the corner face (PIP) / hidden (OFF)
    // a much bigger face (a close selfie pickup) gets its own scale and offset: the corner scale of the main take
    // crops its hairline (pip.bigW: face widths above this, pip.bigScale / pip.bigDy for them)
    const B = P.pip, big = B.bigW && face[2] > B.bigW, s = big ? B.bigScale : B.scale, half = B.s / 2 / s, [cx, cy] = face,
      fy = cy + (big ? B.bigDy : B.dy), [SW, SH] = P.src;
    return { s, x: B.x + B.s / 2 - cx * s, y: B.y + B.s / 2 - fy * s, clip: [fy - half, SW - cx - half, SH - fy - half, cx - half, B.radius / s] };
  }
  // the drift: ~rate per second at first, easing out at +cap (never a hard stop)
  const drift = (R, dt) => 1 + R.driftCap * (1 - Math.exp(-(R.drift * Math.max(0, dt)) / R.driftCap));

  // ---------------------------------------------------------------- the evaluator
  function moveAt(P, t) {
    for (const m of P.moves) if (t >= m.t0 - 1e-4 && t < m.t1 - 1e-4) return m;
    return null;
  }
  function stateAt(P, t) {
    const sh = find(P.shots, t), pc = find(P.pieces, t), face = pc.face, R = P.R;
    const view = sh.view || P.view, top = sh.top != null ? sh.top : P.top;
    const out = (st, extra) => Object.assign({ rot: 0, dx: 0, dy: 0, clip: null, view, top, layout: sh.layout, face }, st, extra || {});
    if (SMALL[sh.layout]) return out(smallState(P, sh.layout, face));
    const base = (tt) => sh.s * drift(R, tt - sh.t0);
    const m = moveAt(P, t);
    if (!m) return out(place(P, sh, base(t), face));
    const fps = P.fps;
    if (m.kind === "punch") return out(place(P, sh, m.s * drift(R, t - m.t0), face), { move: m.kind });
    if (m.kind === "push") {
      const e = EASE.sine(clamp01((t - m.t0) / (m.t1 - m.t0)));
      return out(place(P, sh, base(m.t0) * Math.pow(1 + m.amount, e), face), { move: m.kind });
    }
    if (m.kind === "ease") {
      const d = m.frames / fps;
      if (t < m.t0 + d) return out(blend(P, sh, place(P, sh, m.s0 || base(m.t0), face), place(P, sh, m.s, face), EASE.p3out((t - m.t0) / d), face), { move: m.kind });
      return out(place(P, sh, m.s * drift(R, t - m.t0 - d), face), { move: m.kind });
    }
    if (m.kind === "snap") {
      const d1 = m.frames / fps, d2 = m.settle / fps, peak = m.s * (1 + m.overshoot);
      let st;
      if (t < m.t0 + d1) st = blend(P, sh, place(P, sh, m.s0 || base(m.t0), face), place(P, sh, peak, face), EASE.expo((t - m.t0) / d1), face);
      else if (t < m.t0 + d1 + d2) st = blend(P, sh, place(P, sh, peak, face), place(P, sh, m.s, face), EASE.sine((t - m.t0 - d1) / d2), face);
      else st = place(P, sh, m.s * drift(R, t - m.t0 - d1 - d2), face);
      return out(st, Object.assign({ move: m.kind }, shake(P, sh, m, t - m.t0 - d1, st, face)));
    }
    if (m.kind === "zoomx") {
      const d = m.frames / fps, B = place(P, sh, base(t), face);
      const e = t < m.tc ? EASE.expoIn(clamp01((t - m.t0) / d)) : 1 - EASE.expoOut(clamp01((t - m.tc) / d));
      return out(about(P, sh, B, B.s * Math.pow(m.peak, e), face), { move: m.kind });
    }
    return out(place(P, sh, base(t), face));
  }
  // landing shake: a sum of sines (fixed frequencies, zero phase: it starts from rest), exponential decay, limited by
  // the slack the clamp leaves so the frame edge never shows
  function shake(P, sh, m, dt, st, face) {
    const k = m.shake;
    if (!k || dt < 0 || dt >= k.frames / P.fps) return {};
    const [VW, VH] = sh.view || P.view, [SW, SH] = P.src, dur = k.frames / P.fps;
    const env = Math.exp(-dt / (dur / 3)) * (1 - dt / dur), w = (f) => Math.sin(2 * Math.PI * f * dt);
    const slx = Math.min(-st.x, st.x - (VW - SW * st.s)), sly = Math.min(-st.y, st.y - (VH - SH * st.s));
    let rot = k.rot * env * w(k.hz[2]), rm = (Math.abs(rot) * Math.PI / 180) * Math.hypot(VW, VH);
    if (rm > Math.min(slx, sly)) { rot = 0; rm = 0; }                    // no room to roll: translate only
    const sx = Math.max(0, slx - rm), sy = Math.max(0, sly - rm), A = k.amp * VH * env;
    const dy = Math.max(-sy, Math.min(sy, A * (0.6 * w(k.hz[0]) + 0.4 * w(k.hz[1]))));
    const dx = Math.max(-sx, Math.min(sx, 0.6 * A * (0.6 * w(k.hz[1]) + 0.4 * w(k.hz[2]))));
    const [ax, ay] = eyes(face);
    return { dx, dy, rot, pivot: [st.x + ax * st.s, st.y + ay * st.s] };
  }
  function matrixOf(c) {
    const th = (c.rot || 0) * Math.PI / 180, co = Math.cos(th), si = Math.sin(th), s = c.s;
    const [px, py] = c.pivot || [0, 0], dx = c.dx || 0, dy = c.dy || 0;
    return [s * co, s * si, -s * si, s * co, co * (c.x - px) - si * (c.y - py) + px + dx, si * (c.x - px) + co * (c.y - py) + py + dy];
  }
  function lerpState(A, B, e) {
    const L = (a, b) => a + (b - a) * e, clip = A.clip || B.clip ? (A.clip || [0, 0, 0, 0, 0]).map((v, i) => L(v, (B.clip || [0, 0, 0, 0, 0])[i])) : null;
    return Object.assign({}, B, { s: L(A.s, B.s), x: L(A.x, B.x), y: L(A.y, B.y), rot: 0, dx: 0, dy: 0, pivot: null, clip, move: "layout" });
  }
  const css = (clip) => (clip ? `inset(${clip.slice(0, 4).map((v) => v.toFixed(1) + "px").join(" ")} round ${clip[4].toFixed(1)}px)` : "inset(0px 0px 0px 0px round 0px)");
  MO.at = function (P, t) {
    let c = null;
    for (const tr of P.trans) if (t >= tr.t0 && t < tr.t1) { c = lerpState(tr.from, tr.to, EASE.p3inout((t - tr.t0) / (tr.t1 - tr.t0))); break; }
    if (!c) c = stateAt(P, t);
    c.m = matrixOf(c);
    c.clipCss = css(c.clip);
    return c;
  };

  // ---------------------------------------------------------------- motion blur sub-frames
  const BLUR = { ease: "ease", snap: "snap", zoomx: "zoomx" };
  function inv(m) {
    const [a, b, c, d, e, f] = m, det = a * d - b * c;
    return [d / det, -b / det, -c / det, a / det, (c * f - d * e) / det, (b * e - a * f) / det];
  }
  const ap = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  function disp(A, B, view) {                                            // largest on-screen travel between two matrices
    const Ai = inv(A), [VW, VH] = view;
    let d = 0;
    for (const [x, y] of [[0, 0], [VW, 0], [0, VH], [VW, VH], [VW / 2, VH / 2]]) {
      const [u, v] = ap(Ai, x, y), [X, Y] = ap(B, u, v);
      d = Math.max(d, Math.hypot(X - x, Y - y));
    }
    return d;
  }
  MO.disp = disp;
  // the continuous stretch of camera around t (no hard cut inside): sub-frames never cross a cut
  function span(P, t, m) {
    const pc = find(P.pieces, t), sh = find(P.shots, t);
    let lo = Math.max(pc.t0, sh.t0, m.t0), hi = Math.min(pc.t1, sh.t1, m.t1);
    if (m.kind === "zoomx") { if (t < m.tc) hi = Math.min(hi, m.tc); else lo = Math.max(lo, m.tc); }
    return [lo, hi];
  }
  MO.samples = function (P, f, opt) {
    const t = f / P.fps, c = MO.at(P, t), m = moveAt(P, t);
    if (!m || !BLUR[m.kind] || P.trans.some((tr) => t >= tr.t0 && t < tr.t1)) return [c.m];
    const cfg = P.R[m.kind], h = cfg.shutter / 360 / P.fps / 2, [lo, hi] = span(P, t, m), eps = 1e-6;
    const ta = Math.max(lo, t - h), tb = Math.min(hi - eps, t + h);
    if (tb <= ta) return [c.m];
    const A = MO.at(P, ta).m, B = MO.at(P, tb).m, d = disp(A, B, c.view);
    if (d < 1) return [c.m];
    const n = Math.min((opt && opt.max) || cfg.max, Math.max(2, Math.ceil(d / 1.5)));
    const out = [];
    for (let k = 0; k < n; k++) out.push(MO.at(P, ta + ((tb - ta) * k) / (n - 1)).m);
    return out;
  };
  MO.windows = function (P, opt) {
    const W = [];
    for (const m of P.moves) {
      if (!BLUR[m.kind]) continue;
      for (let f = Math.floor(m.t0 * P.fps - 1e-6); f <= Math.ceil(m.t1 * P.fps); f++) {
        const ss = MO.samples(P, f, opt);
        if (ss.length < 2) continue;
        const c = MO.at(P, f / P.fps), last = W[W.length - 1];
        if (last && last.f1 === f && last.view[0] === c.view[0] && last.view[1] === c.view[1]) { last.f1 = f + 1; last.frames.push(ss); }
        else W.push({ f0: f, f1: f + 1, view: c.view, top: c.top, frames: [ss] });
      }
    }
    return W;
  };

  // ---------------------------------------------------------------- the director
  const END = /[.?!…]["'”’)\]]*$/, CLAUSE = /[,;:—–]["'”’)\]]*$/;
  const INTENS = /^(never|ever|always|best|worst|super|insane|crazy|huge|massive|exactly|only|zero|free|expensive|cheap|magic(al)?|awesome|loved?|hate|nothing|everything|seamless)$/i;
  function autoEmphasis(words) {                                          // stressed-word guesses, scored
    const out = [];
    words.forEach((w, k) => {
      const bare = w.text.replace(/[^\w$%.-]/g, "");
      let sc = 0;
      if (INTENS.test(bare)) sc += 1;
      if (/\d|\$|%/.test(w.text)) sc += 2;
      const prev = words[k - 1], prev2 = words[k - 2];
      if (prev && prev2 && prev.text.replace(/\W/g, "").toLowerCase() === bare.toLowerCase() && prev2.text.replace(/\W/g, "").toLowerCase() === bare.toLowerCase()) sc += 2;
      if (sc) out.push({ w, score: sc });
    });
    return out;
  }

  MO.direct = function (o) {
    const format = o.format || (o.mode === "panel" ? "reel" : "long");
    const R = merge(MO.RULES[format], o.rules || {});
    const fps = o.fps || 30, Q = (t) => Math.round(t * fps) / fps;
    const SC = Object.assign({}, MO.SCALES, o.scales || {});
    const H = o.height || (o.view ? o.view[1] : 1080);
    const panel = o.mode === "panel", top = panel ? (o.top != null ? o.top : 880) : 0;
    const view = panel ? [o.width || 1080, H - top] : o.view || [o.width || 1920, H];
    const layoutOf = (tag) => {
      if (panel) return (o.framing && o.framing[tag]) || "P";             // panel: "P", or "H" (full screen) per tag
      if (!o.framing) return "W";
      const L = o.framing[tag];
      if (!L) throw new Error("HF.motion: no framing for tag " + tag);
      return L;
    };
    const pieces = (o.pieces || []).map((p, i) => ({ i, t0: p.out_a, t1: p.out_b, face: p.face, tag: p.tag, layout: layoutOf(p.tag) }));
    if (!pieces.length) throw new Error("HF.motion: no pieces");
    const t0 = o.from != null ? o.from : pieces[0].t0, tEnd = o.until != null ? o.until : pieces[pieces.length - 1].t1;
    const words = (o.words || []).filter((w) => w.text && w.t != null && w.t >= t0 - 0.05 && w.t < tEnd).slice().sort((a, b) => a.t - b.t);
    const byId = new Map(words.map((w, k) => [w.i, k]));
    const tags = o.tags || {};
    const P = {
      v: 2, fps, src: o.src || [1920, 1080], view, top, mode: panel ? "panel" : "frame", format, R,
      pip: Object.assign({ x: 1556, y: 716, s: 316, scale: 0.5, radius: 26, dy: 70 }, o.pip || {}),
      pieces: pieces.map((p) => ({ t0: p.t0, t1: p.t1, face: p.face })), shots: [], moves: [], trans: [], cues: [], log: [],
    };
    if (o.pipRadius != null) P.pip.radius = o.pipRadius;
    if (o.pipScale != null) P.pip.scale = o.pipScale;
    P.pieces[0].t0 = Math.min(P.pieces[0].t0, 0);
    P.pieces[P.pieces.length - 1].t1 = 1e9;
    const pieceAt = (t) => find(pieces, t);
    const say = (t, what) => P.log.push(`${t.toFixed(2)} ${what}`);

    // ---- boundaries: every cut, and every sentence start (a camera cut on continuous footage sits mid-pause)
    const B = [];
    pieces.forEach((p, i) => {
      if (!i) return;
      const before = words.filter((w) => w.t < p.t0 - 0.01).pop();
      const kind = p.tag !== pieces[i - 1].tag ? "scene" : before && END.test(before.text) ? "thought" : before && CLAUSE.test(before.text) ? "clause" : "mid";
      B.push({ t: p.t0, kind, cut: true });
    });
    words.forEach((w, k) => {
      if (!k || !END.test(words[k - 1].text)) return;
      const w0 = words[k - 1];
      if (B.some((b) => b.cut && b.t > w0.e - 0.05 && b.t <= w.t + 0.05)) return;    // a cut already sits in this pause
      B.push({ t: w.t - w0.e > 0.07 ? Q((w0.e + w.t) / 2) : Q(w.t - 0.03), kind: "thought", cut: false });
    });
    const secT = (tags.section || []).map((x) => (typeof x === "number" ? (byId.has(x) ? words[byId.get(x)].t : null) : x && x.t != null ? x.t : null)).filter((x) => x != null);
    secT.forEach((ts) => {
      const near = B.filter((b) => b.t <= ts + 0.02 && b.t > ts - 0.8).sort((a, b) => b.t - a.t)[0];
      if (near) near.kind = "section";
      else B.push({ t: Q(ts - 0.05), kind: "section", cut: false });
    });
    B.sort((a, b) => a.t - b.t);
    const isNew = (b) => b.kind === "thought" || b.kind === "scene" || b.kind === "section";
    const nextNew = (t) => { const b = B.find((x) => x.t > t + 1e-6 && isNew(x)); return b ? b.t : tEnd; };

    // ---- 1. shot times: a new framing only at a new thought, held at least R.hold (never A/B on every cut)
    let cur = null;
    const open = (t, layout, why) => {
      if (cur) cur.t1 = t;
      cur = { t0: t, t1: 1e9, layout, v: 0, s: 1, why };
      if (panel && layout === "H") Object.assign(cur, { view: [view[0], H], top: 0 });
      P.shots.push(cur);
    };
    open(Math.min(t0, 0), pieceAt(t0).layout, "start");
    if (panel && o.hook) {                                                 // 9:16 hook: the face full screen first
      Object.assign(cur, { layout: "H", view: [view[0], H], top: 0, why: "hook (full screen)" });
      open(o.hook[1], "P", "after the hook");
    }
    for (const b of B) {
      if (panel && o.hook && b.t < o.hook[1] + 0.05) continue;
      const L = pieceAt(b.t + 1e-6).layout;
      if (L !== cur.layout) { open(b.t, L, "layout"); continue; }
      if (SMALL[L]) continue;
      const held = b.t - cur.t0, left = nextNew(b.t) - b.t;
      if (b.kind === "section") open(b.t, L, "section");
      else if (isNew(b) && held >= R.hold && left >= R.minThought) open(b.t, L, `reframe (${b.kind})`);
      else if (b.kind === "clause" && b.cut && held >= R.holdMax && left >= R.minThought) open(b.t, L, "reframe (long hold)");
    }
    const shotAt = (t) => find(P.shots, t);
    const prevShot = (sh) => P.shots[P.shots.indexOf(sh) - 1];
    const nextShot = (sh) => P.shots[P.shots.indexOf(sh) + 1];
    const cuts = [...new Set([...pieces.slice(1).map((p) => p.t0), ...P.shots.slice(1).map((s) => s.t0)])].sort((a, b) => a - b);

    // ---- 2. moves (where and what): tagged first, then guesses; budgets; no overlaps
    const lineEnd = (k) => { let j = k; while (j < words.length - 1 && !END.test(words[j].text)) j++; return words[j].e + 0.12; };
    // full-screen windows ("H") take no moves, unless o.fullMoves (a panel Reel whose talking beats are full screen)
    const fits = (L, kind) => (FULL[L] && (L !== "H" || o.fullMoves)) || (SIDE[L] && (kind === "punch" || kind === "ease" || kind === "push"));
    const touch = (x, y) => Math.abs(x - y) < 1e-6;                      // back to back on the same cut is fine
    const busy = (a, b, pad = 0.3) => P.moves.some((m) => a < m.t1 + pad && b > m.t0 - pad && !touch(b, m.t0) && !touch(a, m.t1));
    const family = { punch: 1, ease: 1, snap: 1 };
    const gapOK = (t, kind) => P.moves.every((m) => (m.kind === "zoomx" ? Math.abs(m.tc - t) >= 3 : !family[m.kind] ||
      Math.abs(m.t0 - t) >= (kind === "snap" && m.kind === "snap" ? Math.max(R.punch.gap, R.snap.gap) : R.punch.gap)));
    const LPAD = o.layoutPad != null ? o.layoutPad : 0.7;                 // moves stay this clear of a layout change
    const nearLayout = (a, b) => P.shots.some((s, i) => i && s.t0 > a - LPAD && s.t0 < b + LPAD && s.layout !== P.shots[i - 1].layout);
    const add = (m) => { P.moves.push(m); P.moves.sort((x, y) => x.t0 - y.t0); return true; };
    function proposePunch(k, kind, why) {
      const w = words[k], sh = shotAt(w.t);
      if (!fits(sh.layout, kind)) return false;
      let a = Q(w.t - (kind === "snap" ? R.snap.lead / fps : kind === "ease" ? R.ease.lead : R.punch.lead / fps));
      const before = cuts.filter((c) => c <= a + 1e-6 && c > a - 0.6).pop();
      if (before != null && before >= sh.t0) a = before;                  // a cut just before: cut on the cut (no double cut)
      if (a - sh.t0 < 0.6) a = sh.t0;
      let b = Math.min(lineEnd(k), sh.t1, a + R.punch.hold[1] + (kind === "ease" ? R.ease.frames / fps : 0));
      const after = cuts.find((c) => c >= b - 1e-6 && c < b + 0.6 && c <= sh.t1);
      if (after != null) b = after;                                        // cut back out on the next cut
      if (b - a < R.punch.hold[0] || busy(a, b) || !gapOK(a, kind) || nearLayout(a, b)) return false;
      return add({ kind, t0: a, t1: b, why, word: w.i });
    }
    function proposePush(a, b, why) {
      const sh = shotAt(a + 1e-6), len = b - a;
      if (!fits(sh.layout, "push") || shotAt(b - 1e-3) !== sh || len < R.push.len[0] || len > R.push.len[1] || busy(a, b) || nearLayout(a, b)) return false;
      if (P.moves.some((m) => m.kind === "push" && Math.abs(m.t0 - a) < R.push.gap)) return false;
      return add({ kind: "push", t0: a, t1: b, amount: +Math.max(R.push.amount[0], Math.min(R.push.amount[1], R.push.rate * len)).toFixed(4), why });
    }
    const kOf = (id) => (byId.has(id) ? byId.get(id) : -1);
    B.filter((b) => b.kind === "section").forEach((b) => {                // zoom transitions at sections
      const d = R.zoomx.frames / fps, A = shotAt(b.t - 1e-3), C = shotAt(b.t + 1e-6);
      if (!FULL[A.layout] || !FULL[C.layout] || A.layout === "H" || b.t - d < t0) return;
      add({ kind: "zoomx", t0: Q(b.t - d), t1: Q(b.t + d), tc: b.t, frames: R.zoomx.frames, peak: R.zoomx.peak, why: "section" });
      P.cues.push({ name: MO.SFX.zoomx[0], t: +b.t.toFixed(3), db: MO.SFX.zoomx[2] });   // kit/audio/mix.py puts the peak here
    });
    (tags.joke || []).forEach((id) => kOf(id) >= 0 && proposePunch(kOf(id), "snap", "joke"));
    (tags.punchline || []).forEach((id) => kOf(id) >= 0 && proposePunch(kOf(id), "punch", "punchline"));
    (tags.punch || tags.emphasis || []).forEach((id) => kOf(id) >= 0 && proposePunch(kOf(id), "punch", "emphasis"));
    (tags.ease || []).forEach((id) => kOf(id) >= 0 && proposePunch(kOf(id), "ease", "tagged"));
    (tags.story || []).forEach(([i0, i1]) => {
      const k0 = kOf(i0), k1 = kOf(i1);
      if (k0 < 0 || k1 < 0) return;
      const a = B.filter((b) => b.t <= words[k0].t + 0.02).map((b) => b.t).pop();
      const end = B.find((b) => b.t >= words[k1].e - 0.02);
      proposePush(a != null && words[k0].t - a < 0.8 ? a : Q(words[k0].t - 0.1), end && end.t - words[k1].e < 0.8 ? end.t : Q(words[k1].e + 0.15), "story");
    });
    if (o.auto != null ? o.auto : R.auto) {
      autoEmphasis(words).sort((a, b) => b.score - a.score || a.w.t - b.w.t).forEach(({ w }) => proposePunch(byId.get(w.i), "punch", `auto "${w.text}"`));
      const th = [t0, ...B.filter(isNew).map((b) => b.t), tEnd];
      th.slice(0, -1).map((a, i) => [a, th[i + 1]]).sort((x, y) => y[1] - y[0] - (x[1] - x[0])).forEach(([a, b]) => proposePush(a, b, "auto (long thought)"));
    }
    // never the same move twice in a row: punch <-> ease, a second snap eases, a second push in a row is dropped
    const seq = P.moves.filter((m) => m.kind !== "zoomx");
    for (let i = 1; i < seq.length; i++) {
      const a = seq[i - 1], m = seq[i];
      if (a.kind !== m.kind) continue;
      if (m.kind === "push") m.drop = true;
      else if (m.kind === "ease") Object.assign(m, { kind: "punch", why: m.why + ", hard (no repeat)" });
      else {
        const sh = shotAt(m.t0 + 1e-6), t = Math.max(sh.t0, Q(m.t0 - (R.ease.lead - R.punch.lead / fps)));
        Object.assign(m, { kind: "ease", t0: t, why: m.why + ", eased (no repeat)" });
      }
    }
    P.moves = P.moves.filter((m) => !m.drop);

    // ---- 3. framing variants: flip at each reframe, unless the cut would be under 1.1x (e.g. after a push or a punch)
    const STEP = 1.1;
    const moveIn = (sh) => P.moves.filter((m) => m.t0 >= sh.t0 - 1e-6 && m.t0 < sh.t1 - 1e-6);
    const endScale = (sh) => {                                             // the framing a shot cuts away from
      const m = moveIn(sh).filter((x) => x.t1 >= sh.t1 - 1e-6 && x.kind !== "zoomx").pop();
      if (m && family[m.kind]) return m.s || Math.max(R.punch.s[0], m.kind === "snap" ? R.snap.s : 0);
      if (m && m.kind === "push") return sh.s * drift(R, m.t0 - sh.t0) * (1 + m.amount);
      return sh.s * drift(R, sh.t1 - sh.t0);
    };
    P.shots.forEach((sh, i) => {
      const ps = P.shots[i - 1], V = SC[sh.layout] || SC.W;
      if (SMALL[sh.layout]) return;
      if (sh.layout === "H") { sh.s = (H / P.src[1]) * (o.hScale || 1.08); return; }
      if (!ps || ps.layout !== sh.layout || sh.why === "section") { sh.v = 0; sh.s = V[0]; return; }
      const e = endScale(ps), ok = (v) => Math.max(V[v], e) / Math.min(V[v], e) >= STEP;
      sh.v = ok(1 - ps.v) ? 1 - ps.v : ok(ps.v) ? ps.v : 1 - ps.v;
      sh.s = V[sh.v];
    });
    // consecutive shots on the same framing are one shot (no drift restart, no cut)
    P.shots = P.shots.filter((sh, i) => {
      const ps = P.shots[i - 1];
      if (!ps || ps.layout !== sh.layout || ps.v !== sh.v || ps.view || sh.why === "section" || SMALL[sh.layout]) return true;
      if (P.moves.some((m) => Math.abs(m.t0 - sh.t0) < 1e-6 || Math.abs(m.t1 - sh.t0) < 1e-6)) return true;
      ps.t1 = sh.t1;
      return false;
    });
    for (let i = 0; i < P.shots.length; i++) {                             // keep t1 = next t0 after merging
      if (i + 1 < P.shots.length) P.shots[i].t1 = P.shots[i + 1].t0;
    }

    // ---- 4. how far each move goes: >= 1.1x from every framing it cuts from or back to, within the image limits
    const heldAt = (sh, t) => sh.s * drift(R, t - sh.t0);
    P.moves = P.moves.filter((m) => {
      if (m.kind === "push" || m.kind === "zoomx") return true;
      const sh = shotAt(m.t0 + 1e-6), ps = prevShot(sh), ns = nextShot(sh), L = sh.layout;
      const atStart = m.t0 <= sh.t0 + 1e-6 && ps && ps.layout === L && !SMALL[ps.layout];
      // a continuous move that opens a thought starts from the framing before it (one move, not a cut and a move)
      if (atStart && m.kind !== "punch") m.s0 = +endScale(ps).toFixed(4);
      const from = m.kind === "punch" ? (atStart ? endScale(ps) : heldAt(sh, m.t0)) : m.s0 || heldAt(sh, m.t0);
      const to = m.t1 >= sh.t1 - 1e-6 && ns && !SMALL[ns.layout] ? ns.s : heldAt(sh, m.t1);
      const lo = SIDE[L] ? sh.s * 1.12 : R.punch.s[0], hi = SIDE[L] ? 1.38 : R.punch.s[1] + 0.04;
      const want = m.kind === "snap" ? Math.max(R.snap.s, from * 1.2) : Math.min(R.punch.s[1], (m.kind === "ease" ? from * R.ease.mult : sh.s * R.punch.mult));
      const s = Math.max(lo, want, STEP * Math.max(from, to), m.kind === "ease" ? 0 : STEP * from);
      if (s > (m.kind === "snap" ? MAXS : hi)) return false;               // too soft on a 1080 source
      m.s = +s.toFixed(4);
      if (m.kind === "snap") Object.assign(m, { frames: R.snap.frames, overshoot: R.snap.overshoot, settle: R.snap.settle, shake: R.snap.shake });
      if (m.kind === "ease") m.frames = R.ease.frames;
      return true;
    });
    P.moves.forEach((m) => {
      if (m.kind === "snap") P.cues.push({ name: MO.SFX.snap[0], t: +(m.t0 + (m.frames / fps) / 2).toFixed(3), db: MO.SFX.snap[2] });   // peak mid-snap (mix.py aligns it)
      say(m.t0, `${m.kind}${m.s ? " " + (m.s0 ? m.s0.toFixed(2) + "->" : "") + m.s.toFixed(2) : m.amount ? " +" + (m.amount * 100).toFixed(0) + "%" : ""} until ${m.t1.toFixed(2)} (${m.why})`);
    });
    P.shots.forEach((s, i) => { if (i) say(s.t0, `${s.layout} ${s.s.toFixed(2)} (${s.why})`); });
    P.log.sort((a, b) => parseFloat(a) - parseFloat(b));
    P.cues.sort((a, b) => a.t - b.t);

    // ---- 5. the face each stretch of camera frames on: with a per-frame track (o.faces, [cx, cy, size] per output frame),
    // the median over each span between hard cuts (a 1.4x punch on the piece's median face clips a head that leans in)
    if (o.faces && o.faces.length) {
      const F = o.faces, hard = new Set([...pieces.map((p) => p.t0), ...P.shots.map((x) => x.t0)]);
      P.moves.forEach((m) => {
        if (m.kind === "zoomx") hard.add(m.tc);
        else if (m.kind !== "push") { hard.add(m.t1); if (m.kind === "punch") hard.add(m.t0); }
      });
      const med = (a) => { const b = a.slice().sort((x, y) => x - y); return b[b.length >> 1]; };
      P.pieces = [];
      pieces.forEach((p, i) => {
        const end = i + 1 < pieces.length ? pieces[i + 1].t0 : p.t1;
        const edges = [p.t0, ...[...hard].filter((c) => c > p.t0 + 1e-6 && c < end - 1e-6).sort((a, b) => a - b), end];
        for (let k = 0; k + 1 < edges.length; k++) {
          const f0 = Math.round(edges[k] * fps), fs = F.slice(f0, Math.max(f0 + 1, Math.round(edges[k + 1] * fps))).filter(Boolean);
          P.pieces.push({ t0: edges[k], t1: edges[k + 1], face: fs.length ? [0, 1, 2].map((q) => +med(fs.map((f) => f[q])).toFixed(1)) : p.face });
        }
      });
      P.pieces[0].t0 = Math.min(P.pieces[0].t0, 0);
      P.pieces[P.pieces.length - 1].t1 = 1e9;
    }

    // ---- layout transitions to and from the corner face: a 0.6 s eased move (like v1); everything else is a hard cut
    P.shots.forEach((s, i) => {
      if (i && !!SMALL[P.shots[i - 1].layout] !== !!SMALL[s.layout]) P.trans.push({ t0: Q(s.t0 - 0.22), t1: Q(s.t0 + 0.38), from: null, to: null, small: !!SMALL[s.layout] });
    });
    const all = P.trans;
    P.trans = [];
    all.forEach((tr) => {
      tr.from = MO.at(P, tr.t0);
      tr.to = MO.at(P, tr.t1);
      ["m", "clipCss"].forEach((k) => { delete tr.from[k]; delete tr.to[k]; });
    });
    P.trans = all;
    P.shots[P.shots.length - 1].t1 = 1e9;
    return P;
  };

  // ================================================================ the lens (2026-10-22, kit v11): the camera on HIM
  // The owner (2026-10-22): "I'm not seeing dynamic zoom". MO.direct above frames a full-frame A-roll; the lens is the
  // continuous, eased camera on his footage INSIDE whatever shape shows it: a canvas circle or card, the seated frame
  // (canvas.js mode "frame"), an HF.box card or full frame. Pure like direct() (no DOM, no randomness; tests/test_lens.py
  // runs it in node): MO.lens(o) plans, P.at(t) evaluates, MO.lensFrame() turns a state into the footage's CSS matrix for
  // one shape. The rules (decided 2026-10-22; measured misses: xchakra's 0.5 %/s drift and Reel A's 5 % over 4 s did not
  // read, so the range here is +6-12 % and a visible change every 4-8 s):
  //   - one move per thought: a hold (his shape steady) is cut into 4-8 s segments at sentence ends (and at a visual
  //     plan's passage starts), one move each, never the same move twice in a row: push +8-12 % across the thought
  //     (sine in-out, scale in log space), pull-out back to the base, arc (truck <= 3 % of the shape + roll <= 0.6 deg +
  //     scale +4 %: a slider moving round a seated speaker), settle 1.04 -> 1.0 in 1.2 s after a shape move, a whip or a
  //     takeover. A hold under 2.5 s keeps its framing. NO handheld shake.
  //   - punches on stressed words: x1.15 (never under x1.12: the decision's x1.12-1.18) over 13 frames (power3.out)
  //     landing ON the word, held to the end of its sentence (0.8-3.2 s), released over 0.5 s (sine); one per 12 s at
  //     most; never within 0.7 s of a shape move or a whip (direct()'s LPAD). A punch is a factor on the framing in
  //     force (base lens x jump reframe), so x1.12 is the step on screen. A hold with a candidate keeps x1.12 of its
  //     budget free for it (the base lens moves under kmax / 1.12), and a join before it keeps that room too; a punch
  //     the budget can't pay x1.12 is skipped and logged, never landed smaller (review 2026-10-22: x1.06-1.10 punches
  //     read as drift). Word times are the cut's (TIME_FIX'd / respelled: kit/film build's D.words).
  //   - jump cuts (picture joins inside a hold): THE kit reframe (MO.jumps). A join under a punch hides in it; elsewhere
  //     the framing alternates wide / close (x1.1) as an eased 0.25 s reframe, never a hard step; none within 0.45 s of a
  //     move. It replaces the films' inline "every other join x1.12" loops (oss-editor, xchakra) and HF.box.jumpShots
  //     (a canvas film that keeps its loop: canvas.js reads its same-shape cut shots as one hold and leaves those joins
  //     to the template's own step).
  //     A join the sharp budget can't reframe spends the soft allowance (h.ksoft: tracks.json's soft rule) rather than
  //     play bare (review 2026-10-22: on a 4K render full frame has no sharp room, and the old kit reframed every join
  //     x1.12 there); P.at marks those stretches soft (window.__speaker.soft, max_zoom = that allowance) and the log
  //     says so. rules.jump.soft = false keeps the sharp cap (the join then stays a bare cut, logged).
  //   - eye-anchored (the zoom keeps his eyes where the template put them), clamped to cover (no edge ever shows: a roll
  //     in a 16:9 rect costs ~3 % zoom a degree, added automatically; a circle rolls free), inside a clean rect when the
  //     shot gives one (canvas "frame": the plain wall, never the clutter beside it), and never past the source's budget
  //     (kmax per hold: work/tracks.json's max_zoom for that shape; 1.2 without one): a tight budget shrinks the moves,
  //     it never breaks the cap.
  //   - amplitude scales with the shape: nothing under 240 px, 40 % at 240 px, full from 540 px (a fast move in a small
  //     circle reads as jitter); punches only in shapes >= 360 px; o.calm scales every amplitude (0.6: calmer).
  //   - during a whip (a canvas camera move <= 0.7 s) the lens holds still, the whip is the move; it settles after.
  //
  //   const L = HF.motion.lens({ holds: [{ t0, t1, w, h, kmax, ksoft, enter: "start" | "move" | "cut" | "back", open: +-1 }],
  //                              words, stress: [ids], plan: [{ a, b, cam, punch }], cuts: [t], whips: [[a, b]], fps, calm });
  //                  (ksoft: the soft allowance as a cap on k, >= kmax; only a jump reframe the sharp budget can't pay spends it)
  //   L.at(t, u)  -> { k, dx, dy, rot, move, soft }   k: scale over the shape's base framing (punch and jump included, <=
  //                  kmax; <= ksoft while soft); dx, dy: the picture's shift as a fraction of the shape's width / height;
  //                  rot: roll (deg, about the eyes); move: "push" | "pull" | "punch" | "arc" | "settle" | "hold" | "" (the
  //                  window.__speaker lens field); soft: a jump reframe on the soft allowance is in effect.
  //                  Between two holds (his shape moving) it blends the two ends by u (the shape's own ease) or a sine.
  //   L.log, L.punches, L.jumps, L.holds   what it decided and why (P.log lines like direct()'s); a hold the base lens
  //                  leaves still has h.still (HF.box keeps its pre-v11 drift there)
  MO.LENS = {
    min: 2.5,                           // a hold (or a stretch between whips) shorter than this keeps its framing
    seg: [4, 8], target: 6,             // one move per 4-8 s thought, aiming at 6 s when sentence ends allow
    // push amount: 1.5 % a second of the thought, within 8-12 % (2026-10-22 fix pass: a push under +8 % did not read on
    // v11-sample's p7, 1.045 -> 1.051; the floor was 6 %). Where the room is smaller a push takes what it has (3 % at least)
    push: [0.08, 0.12], rate: 0.015,
    arc: { truck: 0.03, roll: 0.6, scale: 0.04 },
    drift: 0.03,                        // a plan's cam "drift": a slow +3 %
    settle: { k: 1.04, dur: 1.2 },
    // min: the least a punch lands at, and the room a hold with a candidate keeps free for it (x1.12-1.18 decided)
    // base: the least room (over the shape's framing) the base lens must keep for that, else the moves keep the budget
    punch: { s: 1.15, frames: 13, gap: 12, hold: [0.8, 3.2], release: 0.5, pad: 0.7, min: 1.12, size: 360, base: 1.06 },
    // soft: a join the sharp budget can't reframe (x1.06 at least) spends the hold's soft allowance (ksoft)
    jump: { s: 1.1, dur: 0.25, near: 0.45, min: 1.06, size: 240, soft: true },
    size: [240, 540], amp0: 0.4,        // shape min side (px): no lens under 240, 40 % amplitude at 240, 100 % from 540
    budget: 1.2,                        // the max zoom over cover when a track has no work/tracks.json entry
    // the default budget ("auto", E-M2, 2026-10-22): sharp in cards, circles and corners; at full bleed the lens's own
    // moves and punches spend this tier of tracks.json (soft: its soft_zoom rule, x1.24 at most on a native 4K track,
    // x1.12 on a 1080 one; "sharp": the strict budget, which leaves full bleed no room on any 4K render). One constant,
    // so the owner can flip it back; LENS = dict(budget="sharp") restores strict per film
    full: "soft",
    calm: 1,
  };
  // the budget mode a shape's lens takes (pure; tests/test_lens.py): budget (LENS's: "auto" | undefined, "sharp",
  // "soft" or a number) and whether the shape is full bleed -> "sharp" | "soft" | x (MO.lensBudget's mode)
  MO.lensMode = (budget, full, R = MO.LENS) => (typeof budget === "number" ? budget : budget === "sharp" || budget === "soft" ? budget
    : full && R.full === "soft" ? "soft" : "sharp");
  // the tracks.json entry a hold's budget reads (E-M1, pure): the poorest (lowest sharp_px) of the kinds playing in it
  // (kinds: piece kinds, D.pieces[].kind) that the track lists (tracks.json kinds[kind] = { sharp_px, max_zoom,
  // soft_zoom, soft? }; a kind the track shows black for has no entry and is skipped), its soft rule the track's when
  // the kind gives none; the track as is (its top level: the poorest kind of the whole track) without kinds, or when
  // none of the hold's kinds is listed. -> an object for MO.lensBudget (with .kind: the kind it read, or null)
  MO.trackKind = function (track, kinds) {
    if (!track || typeof track !== "object") return track;
    const K = track.kinds && typeof track.kinds === "object" ? track.kinds : null;
    const es = K ? [...new Set(kinds || [])].map((k) => [k, K[k]]).filter(([, e]) => e && typeof e === "object" && Number.isFinite(+e.sharp_px) && +e.sharp_px > 0) : [];
    if (!es.length) return Object.assign({}, track, { kind: null });
    const [k, e] = es.reduce((a, b) => (+b[1].sharp_px < +a[1].sharp_px ? b : a));
    return Object.assign({}, track, { sharp_px: +e.sharp_px, max_zoom: e.max_zoom != null ? +e.max_zoom : track.max_zoom,
      soft_zoom: e.soft_zoom != null ? +e.soft_zoom : track.soft_zoom, soft: e.soft != null ? +e.soft : track.soft, kind: k });
  };
  // the piece kinds playing over [a, b) (D.pieces: { kind, out_a, out_b }; a piece runs to the next one's out_a)
  MO.kindsOver = function (pieces, a, b) {
    const P = pieces || [], out = [];
    P.forEach((p, i) => {
      if (!p || p.kind == null) return;
      const e = i + 1 < P.length ? Math.max(p.out_b != null ? p.out_b : -Infinity, P[i + 1].out_a) : p.out_b != null ? p.out_b : Infinity;
      if (p.out_a < b - 1e-3 && e > a + 1e-3 && out.indexOf(p.kind) < 0) out.push(p.kind);
    });
    return out;
  };
  const LCAMS = { push: 1, pull: 1, arc: 1, hold: 1, drift: 1, punch: 1 };     // plan_check.py CAMS
  const L_ = (a, b, e) => a + (b - a) * e;
  const REST = { k: 1, dx: 0, dy: 0, rot: 0, move: "" };
  const mixS = (A, B, e) => ({ k: A.k * Math.pow(B.k / A.k, e), dx: L_(A.dx, B.dx, e), dy: L_(A.dy, B.dy, e), rot: L_(A.rot, B.rot, e) });
  // the amplitude a shape allows (min side m px), times the calm level
  MO.lensAmp = (m, R = MO.LENS, calm = 1) => (m < R.size[0] - 1e-6 ? 0 : Math.min(1, R.amp0 + (1 - R.amp0) * (m - R.size[0]) / (R.size[1] - R.size[0]))) * calm;

  // jump cuts -> eased reframes (THE kit function; MO.lens calls it, a page without the lens may too).
  //   cuts: [t]; holds: [{ t0, t1, w, h, kmax, ksoft?, kr(a, b) -> [min, max] of the base lens's k over [a, b] (none:
  //   [1, 1]) }]; o: { punches: [{ t0, t1, text? }], whips: [[a, b]], rules, log } -> [{ t, from, to, dur, why, soft }]:
  //   a factor on the base framing that eases from -> to over dur (power2.out) at the join. Wide and close alternate:
  //   from the base, the reframe goes in (x1.1) when the budget has room over the base lens until the next join that
  //   reframes, else out (/1.1) when the base lens is zoomed in that far, whichever is the bigger reframe; the next join
  //   goes back to the base. A punch that plays under the framing (it starts before the next join) lands ON it (MO.lens:
  //   the punch is a factor on the framing in force), so the in-step keeps that punch its x1.12 under the sharp cap
  //   (review 2026-10-22: an in-step 2 s before a stressed word left its punch a x1.02-1.05 step while the log said
  //   x1.15). Under 1.06 either way the soft allowance (h.ksoft, rules.jump.soft) is tried for the in-step (soft: true,
  //   and the step back from it too); under 1.06 even there it is left (logged): a smaller step reads as a glitch.
  MO.jumps = function (cuts, holds, o = {}) {
    const R = merge(MO.LENS, o.rules || {}), J = R.jump, out = [], log = o.log || [], PS = o.punches || [];
    const reads = (f) => Math.abs(Math.log(f)) >= Math.log(J.min) - 1e-9;
    // the joins that reframe: inside a hold, a shape big enough, away from its moves and the whips, not under a punch
    // (it hides in the punch's own step). Known first, so a framing's "until" is the next join that really changes it
    const live = [];
    (cuts || []).slice().sort((a, b) => a - b).forEach((c) => {
      const h = holds.find((x) => c >= x.t0 - 1e-6 && c < x.t1);
      if (!h) return;
      if (Math.min(h.w, h.h) < J.size) return log.push(`${c.toFixed(2)} join: not reframed (shape ${Math.round(Math.min(h.w, h.h))} px < ${J.size})`);
      if (c < h.t0 + J.near || c > h.t1 - J.near) return;                 // the shape's own move hides it
      if ((o.whips || []).some(([a, b]) => c > a - J.near && c < b + J.near)) return;
      if (PS.some((p) => c >= p.t0 - 0.1 && c <= p.t1)) return log.push(`${c.toFixed(2)} join: hidden under the punch`);
      live.push({ c, h });
    });
    const state = new Map();                                               // per hold: { f (the factor it holds now), soft }
    live.forEach(({ c, h }, i) => {
      const cur = state.has(h) ? state.get(h) : { f: 1, soft: false }, off = Math.abs(cur.f - 1) > 1e-4;
      let to = 1, soft = off && cur.soft;                                  // the step back from a soft framing is soft too
      if (!off) {
        const nx = live.slice(i + 1).find((x) => x.h === h), until = nx ? nx.c : h.t1, [lo, hi] = h.kr ? h.kr(c, until) : [1, 1];
        // the punches that will land on this framing: each keeps x1.12 over it under the sharp cap
        const pun = PS.filter((p) => p.t0 > c && p.t0 < until && p.t1 <= h.t1 + 1e-6)
          .map((p) => ({ p, cap: h.kmax / ((h.kr ? h.kr(p.t0, p.t1)[1] : 1) * Math.max(R.punch.min, p.need || 0)) }));   // need: MO.lens's on-screen x1.12
        const pcap = pun.length ? Math.min(...pun.map((x) => x.cap)) : Infinity;
        const pick = (cap) => { const up = Math.min(J.s, cap / hi, pcap), down = Math.max(1 / J.s, 1 / lo); return Math.log(up) >= -Math.log(down) ? up : down; };
        to = pick(h.kmax);
        if (!reads(to)) {
          const ks = Math.max(h.kmax, h.ksoft || 0), st = pick(ks);
          const why = pun.length && Math.min(J.s, ks / hi) > pcap + 1e-6 ? `; the punch on "${pun[0].p.text || "?"}" at ${pun[0].p.t0.toFixed(2)} needs its x${R.punch.min} on top` : "";
          if (J.soft === false || ks <= h.kmax + 1e-6 || !reads(st))
            return log.push(`${c.toFixed(2)} join: no zoom budget for a reframe (x${to.toFixed(3)}; x${J.min} reads${ks > h.kmax + 1e-6 && J.soft !== false ? `; soft allowance x${st.toFixed(3)}` : ""}${why}): a bare cut`);
          to = st; soft = true;
          log.push(`${c.toFixed(2)} join: the sharp budget can't reframe it (x${pick(h.kmax).toFixed(3)}): x${to.toFixed(3)} on the soft allowance (cap x${ks.toFixed(3)} over the base; a bare jump cut reads worse)`);
        } else if (pun.length && to > 1 && Math.min(J.s, h.kmax / hi) > to + 1e-6) log.push(`${c.toFixed(2)} join: in x${to.toFixed(3)} (the punch on "${pun[0].p.text || "?"}" lands on top of it)`);
      }
      out.push({ t: c, from: cur.f, to: +to.toFixed(4), dur: J.dur, why: off ? "join: back to the base" : to > 1 ? "join: in" : "join: out", soft });
      state.set(h, { f: +to.toFixed(4), soft });
    });
    return out;
  };

  MO.lens = function (o = {}) {
    const R = merge(MO.LENS, o.rules || {}), fps = o.fps || 30, calm = o.calm != null ? o.calm : R.calm;
    const words = (o.words || []).filter((w) => w && w.text && w.t != null).slice().sort((a, b) => a.t - b.t);
    const byId = new Map(words.map((w, k) => [w.i, k]));
    const whips = (o.whips || []).filter((x) => x && x[1] > x[0]).map((x) => [x[0], x[1], x[2] || null]).sort((a, b) => a[0] - b[0]);
    const plan = (o.plan || []).filter((p) => p && p.b > p.a).slice().sort((a, b) => a.a - b.a);
    const P = { R, fps, holds: [], punches: [], jumps: [], log: [] };
    const say = (t, what) => P.log.push(`${t.toFixed(2)} ${what}`);
    // thought boundaries: mid-pause after a sentence end (direct()'s rule), and the plan's passage starts
    const sent = [];
    words.forEach((w, k) => { if (k && END.test(words[k - 1].text)) { const w0 = words[k - 1]; sent.push(w.t - w0.e > 0.07 ? (w0.e + w.t) / 2 : w.t - 0.03); } });
    const pstarts = plan.map((p) => p.a);
    const planAt = (t) => plan.filter((p) => t >= p.a - 1e-6 && t < p.b).pop() || null;
    // punch candidates: a plan's cam "punch" passages first (their 'punch' word, else the passage's strongest word), then
    // the stress tags in time order. Known before the holds are planned, so a hold that has one keeps the punch's room
    const PU = R.punch, cands = [];
    plan.forEach((p) => {
      if (p.cam !== "punch") return;
      let id = p.punch;
      if (id == null) {
        const ws = words.filter((w) => w.t >= p.a && w.t < p.b), sc = autoEmphasis(ws).sort((x, y) => y.score - x.score || x.w.t - y.w.t);
        id = sc.length ? sc[0].w.i : (ws.find((w) => END.test(w.text)) || ws[ws.length - 1] || {}).i;
      }
      if (id != null) cands.push({ id, pri: 0, why: "plan punch" });
    });
    (o.stress || []).forEach((id) => cands.push({ id, pri: 1, why: "stressed" }));
    const tOf = (c) => (byId.has(c.id) ? words[byId.get(c.id)].t : 1e9);
    cands.sort((x, y) => x.pri - y.pri || tOf(x) - tOf(y));
    // prevKind: the last THOUGHT move (push / pull / arc / drift, a planned hold), carried across settles and holds, so
    // "never twice in a row" holds on screen: a settle at every landing used to reset it, and with his shape changing
    // every 5-8 s every hold went settle > push (pull-outs and arcs never came; review 2026-10-22). lastSeg: the last
    // segment's kind, settle included (a landing right after a settle doesn't settle again)
    // used: when each move last played (a counter); the next thought takes the least recently used move the framing
    // allows, never prevKind, so push / arc / pull all come round (ties: push, arc, pull)
    let prevKind = null, lastSeg = null, arcDir = 0, nUsed = 0;
    const used = { push: -1, arc: -1, pull: -1 };
    (o.holds || []).filter((h) => h && h.t1 > h.t0).slice().sort((a, b) => a.t0 - b.t0).forEach((h0) => {
      const h = Object.assign({ enter: "cut", open: 0 }, h0);
      h.m = Math.min(h.w || 0, h.h || 0);
      h.kmax = Math.max(1, h.kmax != null ? h.kmax : R.budget);
      h.ksoft = Math.max(h.kmax, h.ksoft || 0);
      h.amp = MO.lensAmp(h.m, R, calm);
      // a pull-out needs a framing it reads from: the push's least (8 % x amp; a 4 % pull after an arc read as drift)
      const pk = 1 + Math.max(0.03, R.push[0] * h.amp) - 1e-9;
      const lru = (k0, room) => ["push", "arc", "pull"].filter((k) => k !== prevKind && (k === "push" ? room > 0.03 : k === "pull" ? k0 >= pk : true))
        .sort((x, y) => used[x] - used[y])[0] || null;
      // the base lens leaves a stressed word's punch its least (x1.12) under the cap, when that still leaves the base a
      // real move (R.punch.base, x1.06: a 6 % pull or push reads; budget 1.2 leaves x1.071); in a tighter budget the moves keep their room (they are the ask: "I'm not
      // seeing dynamic zoom") and a punch lands only where the base is low enough, else it is skipped (logged). A jump
      // reframe needs no room: it goes out when the base is zoomed in (MO.jumps)
      const punchIn = h.m >= PU.size && cands.some((c) => { const t = tOf(c); return t > h.t0 + PU.pad && t < h.t1 - PU.pad; });
      h.kl = Math.max(1, punchIn && h.kmax / PU.min >= PU.base - 1e-9 ? h.kmax / PU.min : h.kmax);
      h.segs = [];
      let st = { k: 1, dx: 0, dy: 0, rot: 0 };
      const seg = (a, b, kind, to, x = {}) => {
        h.segs.push(Object.assign({ a, b, kind, from: st, to, ease: "sine" }, x)); st = to;
        if (kind === "settle") lastSeg = kind; else if (kind !== "" && kind !== "hold" || x.planned) prevKind = lastSeg = kind;
        if (used[kind] != null) used[kind] = ++nUsed;
      };
      if (!h.amp || h.kl < 1.03 || h.t1 - h.t0 < R.min) {                  // under 3 % a move doesn't read: hold
        h.still = true;
        seg(h.t0, h.t1, "", st);
        if (h.t1 - h.t0 >= R.min) say(h.t0, `lens: still (${!h.amp ? `shape ${Math.round(h.m)} px < ${R.size[0]}` : `zoom budget x${h.kmax.toFixed(3)} (the base lens needs x1.03)`})`);
        P.holds.push(h);
        return;
      }
      // the stretches between whips: a whip is the move (the lens holds still in it), then a settle. A whip tagged "land"
      // (canvas.js: a zoom-through's landing from 3x, [a, b, "land"]) is followed by a land-in-and-pull instead: the lens
      // cuts to a closer framing on the zoom's cut frame (inside its blur) and pulls out of it after the landing, so the
      // zoom-out carries on into his framing (fix round 2026-10-23: it settled 1.04 -> 1.0 and the landing read flat)
      const spans = [];
      let a = h.t0, wk0 = null;
      whips.forEach(([wa, wb, wk]) => { if (wb <= a || wa >= h.t1) return; if (wa > a) spans.push([a, wa, spans.length ? (wk0 === "land" ? "land" : "whip") : h.enter]); spans.push([Math.max(a, wa), Math.min(wb, h.t1), "freeze", wk]); a = Math.min(wb, h.t1); wk0 = wk; });
      if (a < h.t1) spans.push([a, h.t1, spans.length ? (wk0 === "land" ? "land" : "whip") : h.enter]);
      // the closer framing a pull-out starts from: +9 % x amp (the target thought's push), in the budget
      const pin0 = (sk) => Math.max(1, Math.min(h.kl / sk, 1 + Math.max(R.push[0], Math.min(R.push[1], R.rate * R.target)) * h.amp));
      for (let si = 0; si < spans.length; si++) {
        const [sa, sb, how, wk] = spans[si];
        if (how === "freeze") {
          const nx = spans[si + 1], pin = Math.min(h.kl, Math.max(pin0(1), st.k));
          if (wk === "land" && nx && nx[2] === "land" && nx[1] - nx[0] >= R.min && prevKind !== "pull" && pin >= pk) {
            st = { k: pin, dx: 0, dy: 0, rot: 0 };
            say(sa, `lens: lands in x${pin.toFixed(3)} on the zoom-through's cut (pulls out after it)`);
          }
          seg(sa, sb, "", st); continue;
        }
        let cur = sa, forced = null;
        if (how === "land" && st.k >= pk && prevKind !== "pull") forced = "pull";
        else if ((how === "move" || how === "back" || how === "whip" || how === "land") && lastSeg !== "settle") {   // a landing: 1.04 -> 1.0
          // the hold's first thought move is chosen here: when it is a pull-out (the rotation's, or the plan's cam for that
          // thought), the shape lands on a closer framing and pulls out from it (a settled 1.0 has nothing to pull out
          // from: a planned pull after a move used to turn into an arc, fix round 2026-10-23); any other plan cam wins
          const sk = 1 + (R.settle.k - 1) * h.amp, first = sb - sa >= R.settle.dur + R.min;
          const pmax = pin0(sk), pp0 = planAt(sa + R.settle.dur + 0.5);
          if (sa === h.t0 && first && !(pp0 && LCAMS[pp0.cam])) forced = lru(pmax, h.kl - 1);
          const pin = forced === "pull" || (sa === h.t0 && first && pp0 && pp0.cam === "pull") ? pmax : 1;
          if (sa === h.t0) st = { k: Math.min(h.kl, pin * sk), dx: 0, dy: 0, rot: 0 };
          const d = Math.min(R.settle.dur, sb - sa), end = sb - (sa + d) < R.min ? sb : sa + d;
          seg(sa, end, "settle", { k: Math.max(1, st.k / sk), dx: 0, dy: 0, rot: 0 }, { d, ease: "p2out" });
          cur = end;
        } else if (sa === h.t0 && sb - sa >= R.min) {                       // a cut or the page's start: a planned pull
          const pp0 = planAt(sa + 0.5);                                     // cuts in on the closer framing it pulls from
          if (pp0 && pp0.cam === "pull") st = { k: pin0(1), dx: 0, dy: 0, rot: 0 };
        }
        while (sb - cur >= R.min - 1e-6) {
          let b = sb;
          if (sb - cur > R.seg[1]) {
            const inR = (x) => x >= cur + R.seg[0] - 1e-6 && x <= cur + R.seg[1] + 1e-6 && sb - x >= R.min;
            const pc = pstarts.filter(inR), sc = sent.filter(inR), c = pc.length ? pc : sc;
            const near = (xs) => xs.reduce((m, x) => (Math.abs(x - cur - R.target) < Math.abs(m - cur - R.target) ? x : m));
            b = c.length ? near(c) : sb - (cur + R.target) < R.min ? sb : cur + R.target;
          }
          const pp = planAt((cur + b) / 2), want = pp && LCAMS[pp.cam] ? pp.cam : null;
          const room = h.kl / st.k - 1;
          let kind = want === "punch" ? "hold" : want;
          if (!kind) kind = forced || lru(st.k, room) || (prevKind === "arc" ? "push" : "arc");
          forced = null;
          if (kind === "pull" && st.k < 1.03) kind = "arc";                 // nothing to pull out from
          if (kind === "push" && room < 0.02) kind = st.k >= pk ? "pull" : "arc";   // no room left to push into
          if (kind === prevKind && (kind === "push" || kind === "pull" || kind === "arc")) {   // never twice in a row
            kind = kind === "arc" ? (st.k >= pk ? "pull" : "push") : "arc";
            say(cur, `lens: ${prevKind} again -> ${kind} (no repeat)`);
          }
          const len = b - cur, amt = Math.max(R.push[0], Math.min(R.push[1], R.rate * len)) * h.amp;
          let to;
          if (kind === "push") to = { k: Math.min(h.kl, st.k * (1 + amt)), dx: 0, dy: 0, rot: 0 };
          else if (kind === "pull") to = { k: 1, dx: 0, dy: 0, rot: 0 };
          else if (kind === "drift") to = { k: Math.min(h.kl, st.k * (1 + R.drift * h.amp)), dx: st.dx, dy: st.dy, rot: st.rot };
          else if (kind === "arc") {
            arcDir = arcDir ? -arcDir : h.open || 1;                         // first toward the open side, then alternating
            to = { k: Math.min(h.kl, st.k * (1 + R.arc.scale * h.amp)), dx: arcDir * R.arc.truck * h.amp, dy: 0, rot: arcDir * R.arc.roll * h.amp };
          } else to = st;                                                    // hold (a declared one: the plan said so)
          seg(cur, b, kind, to, { planned: !!want });
          say(cur, `lens ${kind}${kind === "push" || kind === "pull" || kind === "drift" ? ` x${h.segs[h.segs.length - 1].from.k.toFixed(3)}->x${to.k.toFixed(3)}` : kind === "arc" ? ` truck ${(to.dx * 100).toFixed(1)} % roll ${to.rot.toFixed(2)} deg` : ""} until ${b.toFixed(2)}${want ? " (plan)" : ""}`);
          cur = b;
        }
        if (cur < sb - 1e-6) {                                               // a tail under 2.5 s holds what it reached
          const last = h.segs[h.segs.length - 1];
          if (last && last.b >= cur - 1e-6 && last.kind !== "") { last.d = last.d || last.b - last.a; last.b = sb; }
          else seg(cur, sb, "", st);
        }
      }
      P.holds.push(h);
    });
    const H = P.holds;
    const holdAt = (t) => { for (const h of H) if (t >= h.t0 - 1e-6 && t < h.t1 - 1e-6) return h; return null; };
    const segAt = (h, t) => { for (const s of h.segs) if (t < s.b - 1e-9) return s; return h.segs[h.segs.length - 1]; };
    const EZ = { sine: EASE.sine, p2out: (p) => 1 - (1 - p) * (1 - p) };
    const baseAt = (h, t) => {
      const s = segAt(h, t), d = s.d || s.b - s.a, u = d > 0 ? clamp01((t - s.a) / d) : 1;
      return Object.assign(mixS(s.from, s.to, EZ[s.ease](u)), { move: s.kind });
    };
    // the base lens's [min, max] k over [a, b] of a hold: k is monotone inside a segment, so the ends of each segment's
    // part of [a, b] decide
    const krOf = (h) => (a, b) => {
      let lo = Infinity, hi = 1;
      h.segs.forEach((s) => {
        if (s.b <= a || s.a >= b) return;
        for (const x of [Math.max(a, s.a), Math.min(b, s.b) - 1e-6]) { const k = mixS(s.from, s.to, EZ[s.ease](clamp01((x - s.a) / (s.d || s.b - s.a || 1)))).k; lo = Math.min(lo, k); hi = Math.max(hi, k); }
      });
      return [Number.isFinite(lo) ? lo : 1, hi];
    };
    H.forEach((h) => { h.kr = krOf(h); });
    // the jump factor at t in a list of jump reframes, and whether a soft-allowance reframe is in effect (its close
    // framing, or the step back from it)
    const jumpOf = (js, h, t) => {
      let f = 1, soft = false;
      for (const j of js) {
        // dur 0 (rules.jump.dur, who-gonna-hire 2026-10-23): a hard step ON the join's frame, so the jump cut reads as a
        // camera cut; cut times are stored to 4 decimals, so the join's frame may sit up to half a frame before j.t
        const hard = !(j.dur > 0);
        if (j.t > t + (hard ? 0.5 / fps : 1e-9)) break;
        if (j.t >= h.t0 - 1e-6 && j.t < h.t1) { f = hard ? j.to : L_(j.from, j.to, 1 - (1 - clamp01((t - j.t) / j.dur)) ** 2); soft = !!j.soft && (j.to > 1 + 1e-6 || t < j.t + j.dur); }
      }
      return { f, soft };
    };
    // ---- punches (the candidates above). A punch is a factor ON the framing in force (the base lens times a jump
    // reframe), so its step on screen is its own size (review 2026-10-22: blended in place of an x1.1 jump framing, a
    // logged x1.15 showed as x1.02-1.05). Its size: x1.15, or what the sharp cap leaves over that framing, and never
    // under x1.12 measured on screen (the step from the frame before its ease-in to the word, a base pull-out under it
    // included); a candidate that can't reach x1.12 is skipped and logged. Order: each candidate's window and size on
    // the base lens (a candidate the budget can't pay never holds a slot: review 2026-10-22, it hid a later one that
    // could play), then one per R.punch.gap s (logged), then the jump reframes (a join hides only under a punch that
    // plays, and a join before a punch keeps that punch its room: MO.jumps), then each punch re-sized on the framing it
    // lands on; one dropped there re-runs the joins without it (a join it hid reframes again).
    const lineEnd = (k) => { let j = k; while (j < words.length - 1 && !END.test(words[j].text)) j++; return words[j].e + 0.12; };
    const sizeOf = (p, js) => {
      const h = H[p.hold], fr = (t) => baseAt(h, t).k * jumpOf(js, h, t).f, pre = p.t0 - 1 / fps;
      const f = Math.max(jumpOf(js, h, p.t0).f, jumpOf(js, h, p.t1).f), s = Math.min(PU.s, h.kmax / (h.kr(p.t0, p.t1)[1] * f));
      const r = fr(p.land) / fr(pre), need = PU.min / Math.min(1, r);        // the framing's own change over the ease-in
      return { s, need, ok: s >= need - 1e-6 };
    };
    const seen = new Set(), sized = [];
    cands.forEach((c) => {
      if (seen.has(c.id) || !byId.has(c.id)) return;
      seen.add(c.id);
      const k = byId.get(c.id), w = words[k], h = holdAt(w.t);
      if (!h || h.m < PU.size || !h.amp) return;
      const t0 = w.t - PU.frames / fps;
      let he = Math.max(w.t + PU.hold[0], Math.min(lineEnd(k), w.t + PU.hold[1])), t1 = he + PU.release;
      if (t0 < h.t0 + PU.pad) return say(w.t, `punch "${w.text}" skipped: within ${PU.pad} s of his shape's move`);
      if (t1 > h.t1 - PU.pad) { he = h.t1 - PU.pad - PU.release; t1 = h.t1 - PU.pad; if (he < w.t + PU.hold[0] - 1e-6) return say(w.t, `punch "${w.text}" skipped: his shape moves before it could hold`); }
      if (whips.some(([a, b]) => t0 < b + PU.pad && t1 > a - PU.pad)) return say(w.t, `punch "${w.text}" skipped: a whip within ${PU.pad} s`);
      const p = { t0, land: w.t, he, t1, s: PU.s, word: w.i, text: w.text, why: c.why, hold: H.indexOf(h) }, z = sizeOf(p, []);
      if (!z.ok) return say(w.t, `punch "${w.text}" skipped: the zoom budget pays x${z.s.toFixed(3)} there (a punch is x${PU.min} or more on screen)`);
      const near = sized.find((q) => Math.abs(q.t0 - t0) < PU.gap);
      if (near) return say(w.t, `punch "${w.text}" skipped: within ${PU.gap} s of the punch on "${near.text}" (${near.land.toFixed(2)})`);
      p.need = +z.need.toFixed(4);
      sized.push(p);
    });
    P.punches = sized.sort((a, b) => a.t0 - b.t0);
    // ---- jump cuts: the one kit reframe (under the punches that play), then the punches sized on the framing they land on
    let jlog = [];
    for (let pass = 0; pass < 4; pass++) {
      jlog = [];
      P.jumps = MO.jumps(o.cuts || [], H, { punches: P.punches, whips, rules: o.rules, log: jlog });
      const drop = [];
      P.punches.forEach((p) => { const z = sizeOf(p, P.jumps); if (z.ok) p.s = +z.s.toFixed(4); else drop.push([p, z]); });
      if (!drop.length) break;
      drop.forEach(([p, z]) => say(p.land, `punch "${p.text}" skipped: the jump framing there leaves x${z.s.toFixed(3)} (a punch is x${PU.min} or more on screen)`));
      P.punches = P.punches.filter((p) => !drop.some((d) => d[0] === p));
    }
    P.log.push(...jlog);
    P.punches.forEach((p) => say(p.t0, `punch x${p.s.toFixed(2)} landing on "${p.text}" at ${p.land.toFixed(2)}, held to ${p.he.toFixed(2)} (${p.why})`));
    P.jumps.forEach((j) => say(j.t, `${j.why} x${j.from.toFixed(3)}->x${j.to.toFixed(3)} over ${j.dur} s${j.soft ? " (soft allowance)" : ""}`));
    P.log.sort((a, b) => parseFloat(a) - parseFloat(b));
    // a punch's progress e (0..1) at t, or null: power3.out in, held, sine out
    const punchAt = (t) => {
      for (const p of P.punches) {
        if (t < p.t0 || t >= p.t1) continue;
        return { p, e: t < p.land ? EASE.p3out((t - p.t0) / (p.land - p.t0)) : t < p.he ? 1 : 1 - EASE.sine((t - p.he) / (p.t1 - p.he)) };
      }
      return null;
    };
    const jumpAt = (h, t) => jumpOf(P.jumps, h, t);
    // base x the jump reframe x the punch (a factor on top of both: s^e), capped by kmax (by the soft allowance while a
    // soft jump reframe holds; a punch never lands on a soft framing: its sizing caps it by kmax)
    const inHold = (h, t) => {
      const b = baseAt(h, t), pu = punchAt(t), jk = jumpAt(h, t), f = pu ? jk.f * Math.pow(pu.p.s, pu.e) : jk.f;
      return { k: Math.min(jk.soft ? h.ksoft : h.kmax, b.k * f), dx: b.dx, dy: b.dy, rot: b.rot, move: pu ? "punch" : b.move === "drift" ? "push" : b.move, soft: jk.soft };
    };
    P.at = (t, u) => {
      const h = holdAt(t);
      if (h) return inHold(h, t);
      let prev = null, next = null;
      for (const x of H) { if (x.t1 <= t + 1e-6) prev = x; else if (x.t0 > t - 1e-6) { next = x; break; } }
      if (next && (!prev || next.enter === "back")) return Object.assign(inHold(next, next.t0), { move: "" });
      if (!prev) return Object.assign({}, REST);
      const A = inHold(prev, prev.t1 - 1e-4);
      if (!next) return Object.assign(A, { move: "" });
      const B = inHold(next, next.t0), uu = u != null ? clamp01(u) : EASE.sine(clamp01((t - prev.t1) / (next.t0 - prev.t1)));
      // a soft jump framing the shape leaves with stays soft until it has blended away (precheck read the move out of a
      // soft card at x1.19 against the sharp x1.14: the fixture, 14.0 s)
      return Object.assign(mixS(A, B, uu), { move: "", soft: !!A.soft && uu < 1 });
    };
    // the segment kinds in order (tests: never the same move twice in a row)
    P.kinds = () => H.flatMap((h) => h.segs.map((s) => s.kind)).filter((k) => k && k !== "hold");
    return P;
  };

  // the footage's transform for one shape at one lens state (pure; tests: clamp-to-cover at extreme moves).
  //   g    { bw, bh, vs, vx, vy, circle }  the shape (px) and its base framing: box px = vs * source px + (vx, vy)
  //   st   { k, dx, dy, rot }               a lens state (MO.lens P.at)
  //   o    { src: [SW, SH], eye: [x, y] (source px: the zoom's anchor), rect: [x0, y0, x1, y1] (source px the picture
  //          must stay inside: a clean rect, default the whole source), smax (the most scale the budget allows) }
  //   -> { m: [a, b, c, d, e, f] (CSS matrix, origin 0 0), s, rot (deg: less than asked when the budget can't pay the
  //        cover zoom a roll costs), eye: [x, y] (where the eyes sit in the box), zoom: s / cover of the whole source }
  // Clamp: in the frame turned by -rot every box corner (a circle: its centre +- r) must map inside rect; that is an
  // axis-aligned interval per axis there, so the eyes' wanted position is clamped per axis and turned back.
  MO.lensFrame = function (g, st, o) {
    const [SW, SH] = o.src, E = o.eye, Rr = o.rect || [0, 0, SW, SH], rw = Rr[2] - Rr[0], rh = Rr[3] - Rr[1];
    const circ = !!g.circle && Math.abs(g.bw - g.bh) < 1;
    const sCov = (deg) => {
      const th = Math.abs(deg) * Math.PI / 180, c = Math.cos(th), s = Math.sin(th);
      return circ ? Math.max(g.bw / rw, g.bh / rh) : Math.max((g.bw * c + g.bh * s) / rw, (g.bw * s + g.bh * c) / rh);
    };
    const k = st.k || 1, sk = Math.max(g.vs * k, sCov(0)), cap = Math.max(o.smax != null ? o.smax : Infinity, sk);
    let rot = st.rot || 0;
    if (rot && sCov(rot) > cap) {                                          // roll less: the budget can't pay its cover
      let lo = 0, hi = Math.abs(rot);
      for (let i = 0; i < 24; i++) { const m = (lo + hi) / 2; if (sCov(m) <= cap) lo = m; else hi = m; }
      rot = Math.sign(rot) * lo;
    }
    const s = Math.max(sk, sCov(rot));
    const th = rot * Math.PI / 180, c = Math.cos(th), sn = Math.sin(th);
    const rm = (x, y) => [c * x + sn * y, -sn * x + c * y];                // turned by -rot
    let mnx, mxx, mny, mxy;
    if (circ) { const r = g.bw / 2, q = rm(g.bw / 2, g.bh / 2); mnx = q[0] - r; mxx = q[0] + r; mny = q[1] - r; mxy = q[1] + r; }
    else {
      const ps = [[0, 0], [g.bw, 0], [0, g.bh], [g.bw, g.bh]].map(([x, y]) => rm(x, y));
      mnx = Math.min(...ps.map((p) => p[0])); mxx = Math.max(...ps.map((p) => p[0]));
      mny = Math.min(...ps.map((p) => p[1])); mxy = Math.max(...ps.map((p) => p[1]));
    }
    const pe = [g.vx + E[0] * g.vs + (st.dx || 0) * g.bw, g.vy + E[1] * g.vs + (st.dy || 0) * g.bh], q = rm(pe[0], pe[1]);
    const lx = mxx - s * (Rr[2] - E[0]), hx = mnx + s * (E[0] - Rr[0]), ly = mxy - s * (Rr[3] - E[1]), hy = mny + s * (E[1] - Rr[1]);
    const qx = lx > hx ? (lx + hx) / 2 : Math.min(hx, Math.max(lx, q[0])), qy = ly > hy ? (ly + hy) / 2 : Math.min(hy, Math.max(ly, q[1]));
    const p = [c * qx - sn * qy, sn * qx + c * qy];
    const a = s * c, b = s * sn, cc = -s * sn, d = s * c;
    return { m: [a, b, cc, d, p[0] - (a * E[0] + cc * E[1]), p[1] - (b * E[0] + d * E[1])], s, rot, eye: p,
      zoom: s / Math.max(g.bw / SW, g.bh / SH) };
  };
  // a shape's zoom budget as a cap on the lens's k: tracks.json (o.track: { sharp_px, max_zoom, soft_zoom, soft }) for a
  // shape whose footage, at cover, is Hc page px tall (the whole source's height at cover). sharp_px gives the shape's own
  // budget, max(1, sharp_px / Hc) (a circle has more headroom than full frame); budget "soft" takes the softer allowance,
  // max(r, 1 + soft * min(r, 1)) (kit/film/cut.py soft_budget). -> { zoom (the budget over cover), kmax (over vs) }
  MO.lensBudget = function (track, Hc, cover, vs, mode) {
    let z = MO.LENS.budget;
    if (typeof mode === "number") z = mode;
    else if (track && Number.isFinite(+track.sharp_px) && +track.sharp_px > 0) {
      const r = +track.sharp_px / Math.max(1e-6, Hc);
      z = mode === "soft" ? Math.max(r, 1 + (Number.isFinite(+track.soft) ? +track.soft : 0.24) * Math.min(r, 1)) : Math.max(1, r);
    } else if (track && Number.isFinite(+(mode === "soft" ? track.soft_zoom : track.max_zoom))) z = +(mode === "soft" ? track.soft_zoom : track.max_zoom);
    return { zoom: z, kmax: Math.max(1, (z * cover) / vs) };
  };
  // one hold's budgets (E-M1 + E-M2; canvas.js infoOf and box.js lensPlan both call it, tests/test_lens.py): the track's
  // entry for the poorest kind of footage playing over [t0, t1) (D.pieces), in the hold's mode (MO.lensMode: "auto"
  // spends the soft tier at full bleed only; budget false: no lens, the sharp cap as published before).
  //   o: { pieces, t0, t1, Hc, cover, vs, budget, full, lens } -> { kmax, zoom (the cap in force), ksoft, zsoft (the
  //   soft allowance a jump reframe may spend), mode, kind (the tracks.json kind it read, or null) }
  MO.holdBudget = function (track, o) {
    const tk = MO.trackKind(track, MO.kindsOver(o.pieces, o.t0, o.t1));
    const mode = o.lens === false ? "sharp" : MO.lensMode(o.budget, !!o.full);
    const b = MO.lensBudget(tk, o.Hc, o.cover, o.vs, mode);
    const bs = o.lens === false || typeof mode === "number" || mode === "soft" ? b : MO.lensBudget(tk, o.Hc, o.cover, o.vs, "soft");
    return { kmax: b.kmax, zoom: b.zoom, ksoft: Math.max(b.kmax, bs.kmax), zsoft: Math.max(b.zoom, bs.zoom), mode, kind: tk && tk.kind != null ? tk.kind : null };
  };
  // the page's data (kit/film build.py's const D), when the page has it: the lens reads D.lens / D.tracks / D.faces
  MO.data = () => { try { return typeof D !== "undefined" && D ? D : root.D || null; } catch (e) { return root.D || null; } };
  // the eyes (source px) a stretch of footage frames on: the median of the per-frame face track over [a, b) (output
  // frames, [cx, cy, size] in the track's px), else the given focus point. Eyes = the box centre 0.2 head widths up
  MO.eyesOver = function (faces, a, b, fps, fallback) {
    if (faces && faces.length) {
      const f0 = Math.max(0, Math.round(a * fps)), f1 = Math.min(faces.length, Math.max(f0 + 1, Math.round(b * fps)));
      const fs = [];
      for (let f = f0; f < f1; f += Math.max(1, Math.floor((f1 - f0) / 90))) { const x = faces[f]; if (x && x[2] > 0) fs.push(x); }
      if (fs.length) { const med = (q) => { const v = fs.map((x) => x[q]).sort((p, r) => p - r); return v[v.length >> 1]; };
        return { eye: [med(0), med(1) - EYE_K * med(2)], size: med(2) }; }
    }
    return fallback ? { eye: [fallback[0], fallback[2] ? fallback[1] - EYE_K * fallback[2] : fallback[1]], size: fallback[2] || null } : null;
  };

})(typeof window !== "undefined" ? window : globalThis);
