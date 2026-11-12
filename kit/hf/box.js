/* kit/hf/box.js — the speaker box: the A-roll as an object that moves around a designed stage.
 *
 * camera (motion.js) frames *inside* the footage. box moves the footage itself: full frame -> a tilted card beside the
 * content -> a small card -> a pill that becomes the next graphic -> the back of a flipping card -> tiles that shatter
 * to reveal the face. Learned from a measured reference edit (kit/refs/MOTION.md §1: every move of its box tracked
 * frame by frame); the numbers below are those measurements, not guesses.
 *
 *   const B = HF.box(K, st, { shots: [{ t: 0, at: "full" }, { t: 4.1, at: "right", in: "shrink" }, ...], face: [960, 430] });
 *   const B = HF.box(K, st, { shots: HF.box.direct({ beats, total }).shots });   // or let the director choose the moves
 *   B.rect(t)  -> { cx, cy, w, h, rot, op }   where the box is (for placing content beside it) and how visible
 *   HF.box.morph(K, el, fromRect, toRect, t, dur)   a graphic grows out of the pill (or any rect) into its own place
 *
 * A shot = { t, at, in, dur, dir, from, zoom, tint }:
 *   t     when the move starts (s); it lands at t + dur. Put it on the word, not after it.
 *   at    a slot (SLOTS below: full, center, right, left, rightSmall, leftSmall, pip, pill, off) or { cx, cy, w, h, rot }
 *   in    how it gets there (MOVES below); default "auto" picks from the two states (grow / shrink / move)
 *   from  "flip" only: the element (a card) whose back is the video; it turns away as the video turns in
 *   zoom  extra zoom of the footage inside the box (1 = cover); tint = accent wash 0..1 held on this shot
 *
 * Use HF.box *or* HF.camera's layouts for the speaker, not both (both write the A-roll transform). Framing inside the
 * box is a cover crop that keeps the face at 42 % of the box height, with the same drift as the camera (+0.6 %/s, cap 3 %).
 * With o.lens (2026-10-22, v11: HF.studio / HF.reel pass kit/film's D.lens) the footage inside the box is moved by
 * HF.motion.lens instead of that drift wherever the lens moves (a hold it leaves still keeps the drift): the box moves
 * the shape, the lens the picture in it (BX.lensPlan below). The page publishes window.__speaker (the engine contract,
 * kit/hf/README.md "The lens").
 * Everything is a pure function of time (K.onFrame), so any frame seeks exactly.
 */
(function (root) {
  const HF = root.HF || (root.HF = {});
  const BX = {};
  BX.version = "1.0.0";

  // ---------------------------------------------------------------- slots (fractions of the frame), measured
  // 16:9 reference: centre card 60 % wide at -2.2 deg; right card 47 % x 74 % (~1.13:1); left 44 % x 65 %; small left
  // 33 % x 56 % (~1.06:1); the pill ~14 % x 8.5 %. Cards change aspect as they move (16:9 -> ~square), which is part
  // of the feel: a card beside text is nearly square, a hero card is 16:9.
  BX.SLOTS = {
    "16:9": {
      full: { cx: 0.5, cy: 0.5, w: 1, h: 1, rot: 0 },
      center: { cx: 0.5, cy: 0.49, w: 0.6, h: 0.6, rot: -2.2 },
      right: { cx: 0.685, cy: 0.5, w: 0.47, h: 0.74, rot: 1.8 },
      left: { cx: 0.27, cy: 0.5, w: 0.44, h: 0.65, rot: -1.8 },
      rightSmall: { cx: 0.795, cy: 0.5, w: 0.33, h: 0.56, rot: 2.2 },
      leftSmall: { cx: 0.205, cy: 0.5, w: 0.33, h: 0.56, rot: -2.2 },
      pip: { cx: 0.855, cy: 0.79, w: 0.2, h: 0.27, rot: 0 },
      pill: { cx: 0.5, cy: 0.5, w: 0.14, h: 0.085, rot: 0, tint: 1, pill: 1 },
      // the corner (2026-10-17, from the owner's reference): the speaker up in a top corner, straight, while a screen
      // recording takes the rest of the frame and the explanation stacks in the column under him
      topRight: { cx: 0.835, cy: 0.27, w: 0.29, h: 0.4, rot: 0 },
      topLeft: { cx: 0.165, cy: 0.27, w: 0.29, h: 0.4, rot: 0 },
    },
    "9:16": {
      full: { cx: 0.5, cy: 0.5, w: 1, h: 1, rot: 0 },
      center: { cx: 0.5, cy: 0.5, w: 0.84, h: 0.46, rot: -2.2 },
      top: { cx: 0.5, cy: 0.31, w: 0.86, h: 0.36, rot: -1.8 },
      bottom: { cx: 0.5, cy: 0.71, w: 0.86, h: 0.4, rot: 1.8 },
      bottomSmall: { cx: 0.5, cy: 0.77, w: 0.56, h: 0.27, rot: 2.2 },
      pip: { cx: 0.76, cy: 0.83, w: 0.36, h: 0.2, rot: 0 },
      pill: { cx: 0.5, cy: 0.5, w: 0.3, h: 0.05, rot: 0, tint: 1, pill: 1 },
      // the corner for 9:16 (2026-10-18, films/ai-portfolio/shorts): his face up in a top corner of the safe band, straight,
      // while a screen recording or a board fills the frame under it
      cornerR: { cx: 0.785, cy: 0.235, w: 0.36, h: 0.2, rot: 0 },
      cornerL: { cx: 0.215, cy: 0.235, w: 0.36, h: 0.2, rot: 0 },
    },
  };

  // ---------------------------------------------------------------- the moves, measured (duration s, ease)
  // grow    card -> bigger / full: 0.27 s, power2.inOut (the reference's punch to full: 8 frames, even speed)
  // shrink  full/card -> smaller card: 0.12 s, expo out (3-4 frames; almost all travel in the first 2)
  // move    card -> another card place of similar size: 0.18 s, expo out
  // collapse full/card -> the accent pill: wash in over the first 40 %, 0.3 s power3.inOut; a graphic then grows out
  //         of the pill (HF.box.morph). The reference's signature: used twice in 46 s.
  // flip    a card turns on its vertical axis and its back is the video: 0.24 s (0.12 out, 0.12 in), perspective
  // swing   enters like a door opening on its near edge: 0.15 s, expo out (rotateY 70 -> 0, opacity in the first 30 %)
  // slide   exits off the side it sits on with 3 deg more tilt: 0.12 s, power2.in; entering from a side: expo out
  // dissolve exits by shrinking to 92 %, blur and fade: 0.17 s, power2.in (the next scene grows out of the same place)
  // tiles   accent tiles cover the frame in 0.3 s before t, the cut happens under them, they fly apart in 0.35 s
  // cut     instant
  const BEZ = (x1, y1, x2, y2) => (HF.motion && HF.motion.bezier ? HF.motion.bezier(x1, y1, x2, y2) : (p) => p);
  const E = {
    lin: (p) => p,
    p2inout: (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2),
    p3inout: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    p2in: (p) => p * p,
    p2out: (p) => 1 - (1 - p) * (1 - p),
    expo: null,
  };
  E.expo = (p) => { if (!E._expo) E._expo = BEZ(0.16, 1, 0.3, 1); return E._expo(p); };
  BX.EASE = E;
  BX.MOVES = {
    grow: { dur: 0.27, ease: "p2inout" },
    shrink: { dur: 0.12, ease: "expo" },
    move: { dur: 0.18, ease: "expo" },
    collapse: { dur: 0.3, ease: "p3inout" },
    flip: { dur: 0.24, ease: "p2out" },
    swing: { dur: 0.15, ease: "expo" },
    slide: { dur: 0.12, ease: "p2in" },
    dissolve: { dur: 0.17, ease: "p2in" },
    tiles: { dur: 0.35, ease: "expo", cover: 0.3 },
    cut: { dur: 0, ease: "lin" },
  };
  // idle: a held card is never still: tilt sways +-0.4 deg (period 5.3 s) and it floats +-0.6 % of the height (4.1 s).
  // Measured in the reference: tilt -1.6..-2.4 deg and y +-1.3 % over a 5.5 s hold. Full frame drifts in instead.
  BX.IDLE = { rot: 0.4, rotT: 5.3, y: 0.006, yT: 4.1, drift: 0.006, driftCap: 0.03 };
  BX.LOOK = { radius: 28, shadow: [0, 30, 70, 0.3], persp: 1800, faceY: 0.42 };

  const clamp01 = (p) => Math.max(0, Math.min(1, p));
  const lerp = (a, b, p) => a + (b - a) * p;
  const fullness = (s) => clamp01((Math.min(s.w, s.h) - 0.6) / 0.4);       // 1 = full frame, 0 = a card

  function slotOf(fmt, at, prev) {
    if (at === "off") return Object.assign({}, prev || BX.SLOTS[fmt].center, { op: 0 });
    const s = typeof at === "string" ? BX.SLOTS[fmt][at] : at;
    if (!s) throw new Error("HF.box: no slot " + at + " in " + fmt);
    return Object.assign({ rot: 0, tint: 0, pill: 0, op: 1, ry: 0, blur: 0, sc: 1 }, s);
  }
  // which move fits two states when the shot says "auto"
  function autoMove(A, B) {
    if (B.op === 0) return "dissolve";
    if (A.op === 0) return "swing";
    if (B.pill) return "collapse";
    const a = A.w * A.h, b = B.w * B.h;
    if (b > a * 1.15) return "grow";
    if (b < a / 1.15) return "shrink";
    return "move";
  }

  // ---------------------------------------------------------------- the plan: shots -> keyed states (pure)
  BX.plan = function (o) {
    const fmt = o.format || (o.width && o.height && o.height > o.width ? "9:16" : "16:9");
    const shots = o.shots.slice().sort((a, b) => a.t - b.t);
    if (!shots.length) throw new Error("HF.box: no shots");
    const keys = [];
    let prev = null;
    shots.forEach((sh, i) => {
      const B = slotOf(fmt, sh.at, prev);
      if (sh.tint != null) B.tint = sh.tint;
      B.zoom = sh.zoom || 1;
      let kind = !prev ? "cut" : sh.in && sh.in !== "auto" ? sh.in : autoMove(prev, B);
      if (kind === "collapse" && B.op === 0) {                             // collapse "off": land on the pill, then hand over
        Object.assign(B, slotOf(fmt, "pill"), { ghost: 1 });
      }
      if (kind === "slide" && B.op === 0) {                                // exit off the side it sits on
        const dir = sh.dir || (prev.cx < 0.5 ? -1 : 1);
        Object.assign(B, prev, { cx: prev.cx + dir * (prev.w / 2 + 0.55), rot: prev.rot + dir * 3, op: 1, ghost: 1 });
      }
      const M = BX.MOVES[kind];
      if (!M) throw new Error("HF.box: no move " + kind);
      const dur = sh.dur != null ? sh.dur : M.dur;
      keys.push({ i, t: sh.t, dur, kind, ease: M.ease, to: B, from: null, dir: sh.dir, fromEl: sh.from || null, tag: sh.tag || "" });
      prev = B.ghost ? Object.assign({}, B, { op: 0 }) : B;
    });
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i], nx = keys[i + 1];
      if (nx && nx.t < k.t + k.dur + 0.05) throw new Error(`HF.box: shot at ${nx.t}s starts before the move at ${k.t}s lands (${(k.t + k.dur).toFixed(2)}s)`);
    }
    // lens: the footage's camera is HF.motion.lens (box(): o.lens), which replaces the linear drift below
    return { format: fmt, keys, width: o.width || (fmt === "9:16" ? 1080 : 1920), height: o.height || (fmt === "9:16" ? 1920 : 1080), lens: !!o.lens };
  };

  function idle(P, k, t, S) {                                            // sway + float on cards, drift on the footage
    const I = BX.IDLE, card = 1 - fullness(S), held = Math.max(0, t - (k.t + k.dur));
    const out = Object.assign({}, S);
    out.rot += card * I.rot * Math.sin((2 * Math.PI * t) / I.rotT);
    out.cy += card * I.y * Math.sin((2 * Math.PI * t) / I.yT + 1.1);
    // the lens moves the footage instead, in the holds where it moves (k.lensMoves, BX.lensPlan); a hold it leaves still
    // (no zoom budget, a small shape) keeps this drift, so turning the lens on never takes motion away (review 2026-10-22)
    out.zoom = P.lens && k.lensMoves ? S.zoom || 1 : (S.zoom || 1) * (1 + Math.min(I.driftCap, I.drift * held));
    return out;
  }
  function blendS(A, B, p) {
    const o = {};
    for (const k of ["cx", "cy", "w", "h", "rot", "tint", "pill", "op", "ry", "blur", "sc", "zoom"]) o[k] = lerp(A[k] != null ? A[k] : k === "op" || k === "sc" || k === "zoom" ? 1 : 0, B[k] != null ? B[k] : k === "op" || k === "sc" || k === "zoom" ? 1 : 0, p);
    return o;
  }

  // the box state at time t: { cx, cy, w, h, rot, ry, tint, pill, op, blur, sc, zoom, origin, fromEl: { ry, op } }
  BX.at = function (P, t) {
    const ks = P.keys;
    let i = ks.length - 1;
    while (i > 0 && t < ks[i].t) i--;
    const k = ks[i];
    const steady = (j, tt) => {                                           // state of shot j held at time tt (idle applied)
      const kj = ks[j];
      const S = kj.to.ghost ? Object.assign({}, kj.to, { op: 0 }) : kj.to;
      return idle(P, kj, tt, S);
    };
    if (i === 0 || t >= k.t + k.dur || k.dur === 0) {
      if (t < k.t && i === 0) return Object.assign(steady(0, t), { kind: "hold" });
      return Object.assign(steady(i, t), { kind: "hold" });
    }
    const A = steady(i - 1, k.t), raw = clamp01((t - k.t) / k.dur), e = E[k.ease](raw);
    let S;
    switch (k.kind) {
      case "collapse": {
        S = blendS(A, k.to, e);
        S.tint = lerp(A.tint || 0, 1, clamp01(raw / 0.4));
        break;
      }
      case "flip": {                                                      // first half: the old face (or `from` card) turns away
        if (raw < 0.5) {
          const q = E.p2in(raw / 0.5);
          if (k.fromEl) { S = Object.assign({}, k.to, { op: 0 }); S.fromRy = 90 * q; }
          else { S = Object.assign({}, A, { ry: 90 * q }); }
        } else {
          const q = E.p2out((raw - 0.5) / 0.5);
          S = Object.assign({}, k.to, { ry: -90 * (1 - q) });
          if (k.fromEl) S.fromRy = 90;
        }
        S.zoom = k.to.zoom || 1;
        break;
      }
      case "swing": {
        S = Object.assign({}, k.to, { ry: (k.dir === -1 ? -70 : 70) * (1 - e), op: clamp01(raw / 0.3), origin: k.dir === -1 ? "100% 50%" : "0% 50%" });
        break;
      }
      case "dissolve": {
        S = Object.assign({}, A, { sc: lerp(1, 0.92, e), blur: 10 * e, op: 1 - e });
        break;
      }
      case "tiles": {                                                     // the cut is hidden under the tiles
        S = Object.assign({}, k.to);
        break;
      }
      default:
        S = blendS(A, k.to, e);
    }
    S.kind = k.kind;
    return S;
  };

  // tiles over the frame at time t, for any "tiles" shot: [{ x, y, w, h, s, op, rot }] in px (empty when none)
  BX.TILES = { cols: 8, rows: 5, gap: 10, radius: 18 };
  const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  BX.tilesAt = function (P, t) {
    const T = BX.TILES, out = [];
    P.keys.forEach((k) => {
      if (k.kind !== "tiles") return;
      const c0 = k.t - BX.MOVES.tiles.cover, c1 = k.t + k.dur + 0.2;
      if (t < c0 || t > c1) return;
      const tw = (P.width - T.gap * (T.cols + 1)) / T.cols, th = (P.height - T.gap * (T.rows + 1)) / T.rows;
      for (let r = 0; r < T.rows; r++) for (let c = 0; c < T.cols; c++) {
        const n = r * T.cols + c, d = hash(n + k.t), d2 = hash(n * 7 + 3 + k.t);
        const x = T.gap + c * (tw + T.gap), y = T.gap + r * (th + T.gap);
        const inA = c0 + d * 0.16, inP = clamp01((t - inA) / 0.14);
        const outA = k.t + d2 * 0.2, outP = clamp01((t - outA) / 0.18);
        if (inP <= 0) continue;
        const ein = E.expo(inP), eout = E.p2in(outP);
        const dx = (c - (T.cols - 1) / 2) * 26 * eout, dy = (r - (T.rows - 1) / 2) * 30 * eout;
        out.push({ x: x + dx, y: y + dy, w: tw, h: th, s: lerp(0.4, 1, ein) * lerp(1, 0.25, eout), op: ein * (1 - eout), rot: (d - 0.5) * 8 * eout });
      }
    });
    return out;
  };

  // inner framing: a cover crop of the 1920x1080 footage into a w x h box, the face at faceY of the box height
  BX.inner = function (bw, bh, face, zoom, src) {
    const SW = (src && src[0]) || 1920, SH = (src && src[1]) || 1080;
    const s = Math.max(bw / SW, bh / SH) * (zoom || 1);
    let tx = bw / 2 - face[0] * s, ty = bh * BX.LOOK.faceY - face[1] * s;
    tx = Math.min(0, Math.max(bw - SW * s, tx));
    ty = Math.min(0, Math.max(bh - SH * s, ty));
    return { s, tx, ty };
  };

  // ---------------------------------------------------------------- the director: beats -> shots
  // beats: [{ t, show, side, section, card, end }] in time order, one per visual idea (from the visual plan):
  //   show "face"     nothing else on screen: the face carries it          -> full
  //        "punch"    the emotional line / payoff: back to the face, hard  -> full (grow, or tiles at a section)
  //        "beside"   content on one side (side: where the CONTENT is)      -> the card on the other side
  //        "aside"    small content (a word, a pill)                        -> the small card on the other side
  //        "hero"     the face as a centred card under/over a title         -> center
  //        "graphic"  a full-screen explanation                             -> off (collapse into it / slide away)
  //        "corner"   a big screen recording + notes (side: where the SCREEN is) -> topRight / topLeft (16:9),
  //                   cornerR / cornerL (9:16: the face up in a top corner, the screen under it)
  //        "takeover" a full-screen scene with him removed (2026-10-22, kit v11; kit/hf/trans.js S.takeover) -> off, as
  //                   "graphic"; until: when he comes back (BX.takeoverBeats: the beats inside are dropped and his
  //                   previous show returns at until, by backMove if given, unless a beat already sits there)
  //   section  true at a chapter change; card  true when the graphic starts (or ends) as a card at the box's place
  // Rules (kit/refs/MOTION.md §2): moves 0.1-0.3 s, holds >= 1.2 s, tiles <= 1 per 20 s and only on a return to the
  // face at a section, flip <= 1 per 25 s and only from a card, collapse is the signature (full -> graphic that starts
  // as a card), a card leaves off its own side, the face comes back at least every 12 s of talk (18 s before v11).
  // the takeover beats' returns (pure; tests/test_takeover.py): a { show: "takeover", until } beat drops the beats in
  // (t, until - 0.05) and, unless a beat sits within [until - 0.05, until + 0.3], adds his previous show at until (the
  // last beat before it that shows him; "face" if none) with its side and zoom. -> { beats, log }
  BX.takeoverBeats = function (beats) {
    let out = beats.slice().sort((a, b) => a.t - b.t);
    const log = [];
    out.filter((b) => b.show === "takeover" && b.until != null).forEach((tb) => {
      const drop = out.filter((b) => b !== tb && b.t > tb.t && b.t < tb.until - 0.05);
      drop.forEach((b) => log.push([b.t, b.show, "note", `inside the takeover ${tb.t}-${tb.until}: dropped`]));
      out = out.filter((b) => drop.indexOf(b) < 0);
      if (out.some((b) => b !== tb && b.t >= tb.until - 0.05 && b.t <= tb.until + 0.3)) return;
      const prev = out.filter((b) => b.t < tb.t && b.show !== "graphic" && b.show !== "takeover").pop();
      const back = { t: tb.until, show: prev ? prev.show : "face", tag: "takeover-back" };
      if (prev && prev.side) back.side = prev.side;
      if (prev && prev.zoom != null) back.zoom = prev.zoom;
      if (tb.backMove) back.move = tb.backMove;
      out.push(back);
      out = out.sort((a, b) => a.t - b.t);
    });
    return { beats: out, log };
  };
  BX.direct = function (o) {
    const fmt = o.format || "16:9", TB = BX.takeoverBeats(o.beats), beats = TB.beats, shots = [], log = TB.log.slice();
    const side16 = { beside: { left: "right", right: "left" }, aside: { left: "rightSmall", right: "leftSmall" } };
    const side9 = { beside: { top: "bottom", bottom: "top" }, aside: { top: "bottomSmall", bottom: "top" } };
    let lastTiles = -1e9, lastFlip = -1e9, prevAt = null, prevT = -1e9, lastFace = 0;
    beats.forEach((b, i) => {
      let at;
      const S = fmt === "9:16" ? side9 : side16;
      if (b.show === "face" || b.show === "punch") at = "full";
      else if (b.show === "beside") at = S.beside[b.side || (fmt === "9:16" ? "top" : "left")];
      else if (b.show === "aside") at = S.aside[b.side || (fmt === "9:16" ? "top" : "left")];
      else if (b.show === "hero") at = "center";
      else if (b.show === "graphic" || b.show === "takeover") at = "off";
      else if (b.show === "corner") at = fmt === "9:16" ? ((b.side || "left") === "left" ? "cornerR" : "cornerL") : ((b.side || "left") === "left" ? "topRight" : "topLeft");
      else throw new Error("HF.box.direct: unknown show " + b.show);
      if (!prevAt) { shots.push({ t: b.t, at, in: "cut", zoom: b.zoom }); log.push([b.t, at, "cut", "first"]); prevAt = at; prevT = b.t; if (at !== "off") lastFace = b.t; return; }
      if (at === prevAt) return;
      if (b.t - prevT < 1.2) log.push([b.t, at, "note", `hold before it only ${(b.t - prevT).toFixed(2)} s`]);
      let mv, why;
      const fromOff = prevAt === "off", toOff = at === "off";
      if (b.move) { mv = b.move; why = "set by the beat"; }                  // e.g. move: "cut" on a picture cut into take 3
      else if (toOff) {
        if (prevAt === "full" && b.card) { mv = "collapse"; why = "full -> a graphic that starts as a card: the face becomes it"; }
        else if (prevAt !== "full" && prevAt !== "center") { mv = "slide"; why = "a side card leaves off its own side"; }
        else { mv = "dissolve"; why = "the graphic grows out of where the face was"; }
      } else if (fromOff) {
        if (at === "full" && b.section && b.t - lastTiles >= 20) { mv = "tiles"; lastTiles = b.t; why = "back to the face at a new section"; }
        else if (b.card && at !== "full" && b.t - lastFlip >= 25) { mv = "flip"; lastFlip = b.t; why = "the graphic's last card turns over into the face"; }
        else if (at === "full") { mv = "grow"; why = "back to the face"; }
        else { mv = "swing"; why = "the card swings in on its near edge"; }
        if (b.t - lastFace > 12) log.push([b.t, at, "note", `face absent ${(b.t - lastFace).toFixed(1)} s (> 12 s)`]);
      } else {
        if (at === "full" && b.show === "punch" && b.section && b.t - lastTiles >= 20) { mv = "tiles"; lastTiles = b.t; why = "punch at a section"; }
        else { mv = autoMove(slotOf(fmt, prevAt), slotOf(fmt, at)); why = `${prevAt} -> ${at}`; }
      }
      const t = mv === "tiles" || mv === "cut" ? b.t : Math.max(prevT + 0.3, b.t - (mv === "grow" ? 0.1 : 0.04));   // land on the word
      // a takeover's return that blends in (grow / move / shrink): the hidden state it blends from is first put on the
      // return's own slot, so his shape fades in where it lands, not out of the pill a collapse left (a lilac blob grew
      // over the scene on the fixture, 2026-10-22)
      if (b.tag === "takeover-back" && fromOff && (mv === "grow" || mv === "move" || mv === "shrink") && typeof at === "string" && BX.SLOTS[fmt][at])
        shots.push({ t: +(t - 0.06).toFixed(3), at: Object.assign({}, BX.SLOTS[fmt][at], { op: 0 }), in: "cut", tag: "takeover-reset", zoom: b.zoom });   // (BX.plan: 0.05 s apart)
      shots.push({ t: +t.toFixed(3), at, in: mv, tag: b.tag || "", zoom: b.zoom });   // b.zoom: the footage zoom inside this slot
      log.push([+t.toFixed(3), at, mv, why]);
      prevAt = at; prevT = t; if (!toOff) lastFace = t;
    });
    return { shots, log };
  };

  // ---------------------------------------------------------------- jump cuts inside a held shot (2026-10-20)
  // cuts: [{ t }] picture cuts (a pause trim, a dropped line). Each one inside a held shot (no beat and no director move
  // within `near` s: a move already hides the cut) gets a reframe on the slot it is in: full frame punches in to fullZoom
  // (1.12 nets ~9 % over the drift) or back out, a card alternates its footage zoom 1.0 / cardZoom. The active shot is the
  // latest one by TIME, never the array's last element (pushed shots sit at the end: every in-card jump on films/xchakra
  // first became a full-frame punch, 11 precheck HIGHs).
  BX.jumpShots = function (shots, cuts, o = {}) {
    const near = o.near != null ? o.near : 0.45, beats = o.beats || [], out = [], all = shots.slice();
    cuts.slice().sort((p, q) => p.t - q.t).forEach((c) => {
      if (beats.some((b) => Math.abs(b.t - c.t) < near)) return;
      if (shots.some((x) => Math.abs(x.t - c.t) < near)) return;          // a planned move (or a film's own jump) is there already
      const cur = all.filter((x) => x.t <= c.t + 1e-4).reduce((m, x) => (!m || x.t >= m.t ? x : m), null);
      if (!cur || cur.at === "off" || cur.at === "pill") return;
      const z = (cur.zoom || 1) > 1.05 ? 1 : cur.at === "full" ? o.fullZoom || 1.12 : o.cardZoom || 1.1;
      const sh = { t: +c.t.toFixed(3), at: cur.at, in: "cut", zoom: z, tag: "jump" };
      out.push(sh); all.push(sh);
    });
    return out;
  };
  // the picture cuts of a cut list: where a piece doesn't continue the previous piece's source (same take, contiguous)
  BX.cutsOf = function (pieces) {
    const take = (p) => (p.clip != null ? p.clip : p.take != null ? p.take : p.src != null ? p.src : 0);
    const out = [];
    (pieces || []).forEach((p, k) => {
      if (!k || p.src_a == null || p.out_a == null) return;
      const q = pieces[k - 1];
      if (take(p) === take(q) && Math.abs(p.src_a - q.src_b) < 0.02 && Math.abs(p.out_a - q.out_b) < 0.02) return;
      out.push({ t: p.out_a, w0: p.w ? p.w[0] : null });
    });
    return out;
  };

  // pace of a plan over [0, total]: what share shows the face, how long it is away, move count and lengths
  BX.pace = function (P, total) {
    let face = 0, full = 0, gap = 0, maxGap = 0;
    const dt = 1 / 30;
    for (let t = 0; t < total; t += dt) {
      const S = BX.at(P, t), on = S.op > 0.5;
      if (on) { face += dt; if (fullness(S) > 0.9) full += dt; maxGap = Math.max(maxGap, gap); gap = 0; } else gap += dt;
    }
    maxGap = Math.max(maxGap, gap);
    const moves = P.keys.filter((k) => k.dur > 0);
    return { faceShare: +(face / total).toFixed(3), fullShare: +(full / total).toFixed(3), maxAway: +maxGap.toFixed(2), moves: moves.length,
      perMin: +((moves.length / total) * 60).toFixed(1), meanMove: +(moves.reduce((a, k) => a + k.dur, 0) / Math.max(1, moves.length)).toFixed(3) };
  };

  // ---------------------------------------------------------------- the lens on the box (2026-10-22, kit v11)
  // o.lens (HF.studio / HF.reel pass D.lens from kit/film's build; true or { calm, budget, track, stress, plan, cuts }):
  // HF.motion.lens moves the footage inside every steady box (full frame, cards and the untinted face circle, HF.reel's
  // CIRCLE { pill: 1 }; not the accent pill, not off): pushes, pull-outs, arcs, settles after each box move, punches on
  // stressed words and the jump reframe on picture joins (lens.cuts), eye-anchored, clamped to cover, capped by the
  // track's zoom budget (D.tracks[track], the box's own size). It replaces the box's linear drift (BX.IDLE.drift) in the
  // holds where it moves (the key gets lensMoves); a hold it leaves still keeps the drift, which then counts against
  // the soft allowance like a soft jump reframe (box(): max_zoom). The card's sway and float stay. -> the plan, and per
  // key its budgets (sharp kmax / zoom, soft ksoft / zsoft); null without o.lens (the page is then exactly what it was).
  BX.lensPlan = function (P, o, K) {
    if (!o.lens || !HF.motion || !HF.motion.lens) return null;
    const MO = HF.motion, LZ = typeof o.lens === "object" ? o.lens : {}, DD = MO.data() || {}, W = P.width, H = P.height;
    const SRC = o.src || [1920, 1080], TN = LZ.track || (DD.lens && DD.lens.track) || "aroll";
    const TI = DD.tracks && DD.tracks[TN] && typeof DD.tracks[TN] === "object" ? DD.tracks[TN] : null;
    const end = o.end || DD.total || 1e4, holds = [], info = [];
    P.keys.forEach((k, i) => {
      const t0 = k.t + k.dur, t1 = i + 1 < P.keys.length ? P.keys[i + 1].t : end, S = BX.at(P, Math.min(t1 - 1e-3, t0 + 1e-3));
      const bw = S.w * W, bh = S.h * H, cover = Math.max(bw / SRC[0], bh / SRC[1]), zoom = S.zoom || 1;
      // the kind of footage in this hold (D.pieces, E-M1) and full bleed's tier (E-M2, MO.LENS.full: "auto" spends soft_zoom
      // on a full box only)
      const b = MO.holdBudget(TI, { pieces: DD.pieces || (K && K.pieces), t0, t1, Hc: SRC[1] * cover, cover, vs: cover * zoom, budget: LZ.budget, full: fullness(S) > 0.9 });
      info[i] = { kmax: b.kmax, zoom: b.zoom, ksoft: b.ksoft, zsoft: b.zsoft, kind: b.kind, mode: b.mode };
      // his face shows unless the accent wash covers it (the pill a graphic grows from): the tint, not the pill flag
      if (k.to.ghost || S.op < 0.5 || (S.tint || 0) >= 0.5 || t1 - t0 <= 0.05) return;
      const prev = i ? P.keys[i - 1].to : null;
      holds.push({ t0, t1, w: bw, h: bh, kmax: b.kmax, ksoft: info[i].ksoft, key: i,
        enter: !i ? "start" : k.kind === "cut" ? "cut" : prev && (prev.op === 0 || prev.ghost) ? "back" : "move" });
    });
    const L = MO.lens({ holds, words: (K && K.words_) || [], stress: LZ.stress || [], plan: LZ.plan || [], cuts: LZ.cuts || [], whips: [],
      fps: (K && K.fps) || 30, calm: LZ.calm, rules: LZ.rules });
    L.holds.forEach((h) => { if (!h.still) P.keys[h.key].lensMoves = true; });
    return { L, info, TN, TI, SRC };
  };
  // is his face on screen in box state S, and as what (pure; the window.__speaker on / kind fields; tests/test_lens.py):
  // shown unless hidden (op < 0.5) or the accent wash covers it (tint >= 0.5: the pill a graphic grows from). The tint
  // decides, not the pill flag: HF.reel's CIRCLE { pill: 1 } has tint 0 and is a 330-420 px face circle (review
  // 2026-10-22: it read as off while BX.pace counted it on, a false precheck "away"). kind: "full" (fullness > 0.9),
  // "circle" (a square pill), "corner" (under 10 % of the frame), else "card"; "off" when not on
  BX.speakerKind = function (S, W, H) {
    const op = S.op != null ? S.op : 1, bw = S.w * W, bh = S.h * H;
    if (!(op >= 0.5 && (S.tint || 0) < 0.5 && bw > 4 && bh > 4)) return { on: false, kind: "off" };
    return { on: true, kind: fullness(S) > 0.9 ? "full" : S.pill > 0.5 && Math.abs(bw - bh) < 2 ? "circle" : (bw * bh) / (W * H) < 0.1 ? "corner" : "card" };
  };
  // the key at t and its eased progress while it moves (null when steady): the lens blends two holds by it
  const keyAt = (P, t) => {
    let i = P.keys.length - 1;
    while (i > 0 && t < P.keys[i].t) i--;
    const k = P.keys[i], live = i > 0 && k.dur > 0 && t >= k.t && t < k.t + k.dur;
    return { i, u: live ? E[k.ease](clamp01((t - k.t) / k.dur)) : null };
  };

  // ---------------------------------------------------------------- the page: drive st.cam as the box
  function box(K, st, o) {
    const P = BX.plan(Object.assign({ width: K.width, height: K.height }, o));
    const W = K.width, H = K.height, face = o.face || [960, 430], faceAt = o.faceAt || null, L = Object.assign({}, BX.LOOK, o.look || {});
    const LP = BX.lensPlan(P, o, K);
    if (LP) (window.__lens = window.__lens || {}).box = LP.L;
    const SRC = (LP && LP.SRC) || o.src || [1920, 1080];
    // the footage at t: the base cover crop (BX.inner), the lens on it, and the face that framing uses
    const footage = (t, S, bw, bh) => {
      const f = faceAt ? faceAt(t) : face, I = BX.inner(bw, bh, f, S.zoom, o.src);
      if (!LP) return { f, I, M: [I.s, 0, 0, I.s, I.tx, I.ty], s: I.s, st: null, zoom: null };
      const ka = keyAt(P, t), A = LP.info[ka.i], B = ka.u != null ? LP.info[ka.i - 1] : null, m = (q) => (B ? B[q] + (A[q] - B[q]) * ka.u : A[q]);
      // the cap in force: the sharp budget, or the soft allowance while a soft jump reframe holds or the box drifts (a
      // hold the lens leaves still, on either side of a move); the total zoom over cover never passes it (the drift
      // grows the base, so the lens's k gives way), and never goes under the box's own framing
      const st0 = LP.L.at(t, ka.u), still = !P.keys[ka.i].lensMoves || (B && !P.keys[ka.i - 1].lensMoves);
      const soft = !!st0.soft || !!still, zoom = soft ? m("zsoft") : m("zoom"), cov = Math.max(bw / SRC[0], bh / SRC[1]);
      const st = Object.assign({}, st0, { k: Math.max(1, Math.min(st0.k, (zoom * cov) / I.s)) }), eye = [f[0], f[2] ? f[1] - HF.motion.EYE_K * f[2] : f[1]];
      const fr = HF.motion.lensFrame({ bw, bh, vs: I.s, vx: I.tx, vy: I.ty, circle: S.pill > 0.5 && Math.abs(bw - bh) < 1 }, st, { src: SRC, eye, smax: zoom * cov });
      return { f, I, M: fr.m, s: fr.s, st, zoom, soft: soft && m("zsoft") > m("zoom") + 1e-6 };
    };
    const acc = o.accent || (HF.C && HF.C.acc) || "#e2562b";
    const { cam, wrap } = st;
    Object.assign(cam.style, { overflow: "hidden", filter: "none", transformOrigin: "50% 50%", willChange: "transform" });
    const wash = K.el(cam, `left:0;top:0;width:100%;height:100%;background:${acc};opacity:0;z-index:3;pointer-events:none`);
    const tilesL = K.el(st.full || st.root, `left:0;top:0;width:${W}px;height:${H}px;z-index:20;pointer-events:none`);
    const tiles = [];
    const T = BX.TILES;
    for (let n = 0; n < T.cols * T.rows; n++) tiles.push(K.el(tilesL, `left:0;top:0;border-radius:${T.radius}px;background:${acc};opacity:0;box-shadow:0 18px 40px rgba(20,10,60,.25)`));
    const fromEls = P.keys.filter((k) => k.fromEl).map((k) => k.fromEl);
    fromEls.forEach((el) => { el.style.backfaceVisibility = "hidden"; });
    K.onFrame((t) => {
      const S = BX.at(P, t), card = 1 - fullness(S);
      const bw = S.w * W, bh = S.h * H, x = S.cx * W - bw / 2, y = S.cy * H - bh / 2;
      const r = S.pill ? lerp(L.radius * card, bh / 2, S.pill) : L.radius * card;
      cam.style.left = x.toFixed(2) + "px"; cam.style.top = y.toFixed(2) + "px";
      cam.style.width = bw.toFixed(2) + "px"; cam.style.height = bh.toFixed(2) + "px";
      cam.style.borderRadius = r.toFixed(1) + "px";
      cam.style.transformOrigin = S.origin || "50% 50%";
      cam.style.transform = `perspective(${L.persp}px) rotateY(${(S.ry || 0).toFixed(2)}deg) rotate(${S.rot.toFixed(3)}deg) scale(${(S.sc || 1).toFixed(4)})`;
      cam.style.opacity = (S.op != null ? S.op : 1).toFixed(3);
      cam.style.filter = S.blur > 0.05 ? `blur(${S.blur.toFixed(1)}px)` : "none";
      const sh = L.shadow;
      cam.style.boxShadow = card > 0.01 ? `${sh[0]}px ${sh[1] * card}px ${sh[2] * card}px rgba(25,15,55,${(sh[3] * card).toFixed(3)})` : "none";
      wash.style.opacity = (S.tint || 0).toFixed(3);
      const Fo = footage(t, S, bw, bh), M = Fo.M;
      wrap.style.transform = LP ? `matrix(${M.slice(0, 4).map((x) => x.toFixed(5)).join(",")},${M[4].toFixed(2)},${M[5].toFixed(2)})`
        : `matrix(${Fo.I.s.toFixed(5)},0,0,${Fo.I.s.toFixed(5)},${Fo.I.tx.toFixed(2)},${Fo.I.ty.toFixed(2)})`;
      wrap.style.clipPath = "none";
      P.keys.forEach((k) => {
        if (!k.fromEl) return;
        const live = t >= k.t && t < k.t + k.dur;
        if (live) { k.fromEl.style.transform = `perspective(${L.persp}px) rotateY(${(S.fromRy || 0).toFixed(2)}deg)`; }
        else if (t >= k.t + k.dur) { k.fromEl.style.visibility = "hidden"; }
      });
      const TL = BX.tilesAt(P, t);
      tiles.forEach((d, n) => {
        const q = TL[n];
        if (!q) { d.style.opacity = "0"; return; }
        Object.assign(d.style, { left: q.x.toFixed(1) + "px", top: q.y.toFixed(1) + "px", width: q.w.toFixed(1) + "px", height: q.h.toFixed(1) + "px",
          opacity: q.op.toFixed(3), transform: `scale(${q.s.toFixed(4)}) rotate(${q.rot.toFixed(2)}deg)` });
      });
    });
    if (o.sfx !== false) P.keys.forEach((k) => {
      const at = Math.max(0, k.t - 0.04);
      // heard times (kit/audio/mix.py lines the whoosh's peak up with the cue): mid-move
      if (k.kind === "tiles") K.sfx("swish", k.t + 0.1, -21);
      else if (k.kind === "collapse" || k.kind === "flip" || k.kind === "swing") K.sfx("swish", at + 0.08, -22);
      else if (k.kind === "slide" || k.kind === "shrink" || k.kind === "grow") K.sfx("slide", at, -25);
    });
    window.__box = P;
    // the window.__speaker contract (kit/hf/README "window.__speaker"; kit/qa/speaker.mjs): his box and face on the page
    // (the box's tilt ignored: <= 2.6 deg). While the box is hidden and another engine's window.__faceRect sees his
    // face (a Reel that plays the A-roll full frame itself, films/claude-makes-claude), that face is the answer: he is on
    // (box.js never sets __faceRect, so any is another engine's). His face shows unless the accent wash covers it: the
    // tint decides, not the pill flag (HF.reel's CIRCLE is { pill: 1, tint 0 }, a 330-420 px face circle; review
    // 2026-10-22: it read as off and BX.pace as on). A square pill is a "circle". soft: the cap in force (max_zoom) is
    // the track's soft allowance (a soft jump reframe, or the drift of a hold the lens leaves still)
    const speakerAt = (t) => {
      const S = BX.at(P, t), bw = S.w * W, bh = S.h * H, x = S.cx * W - bw / 2, y = S.cy * H - bh / 2;
      const { on, kind } = BX.speakerKind(S, W, H);
      const tn = LP ? LP.TN : (o.lens && o.lens.track) || null;
      if (!on) {
        const fr = typeof window.__faceRect === "function" ? window.__faceRect(t) : null;
        if (fr) return { on: true, kind: "full", rect: null, face: { x: fr.left, y: fr.top, w: fr.right - fr.left, h: fr.bottom - fr.top }, zoom: null, lens: "", track: tn, max_zoom: null };
        return { on: false, kind: "off", rect: null, face: null, zoom: null, lens: "", track: tn, max_zoom: null };
      }
      const Fo = footage(t, S, bw, bh), M = Fo.M, f = Fo.f, hw = (f[2] || o.head || 330) * Fo.s / 2;
      const cx = x + M[0] * f[0] + M[2] * f[1] + M[4], cy = y + M[1] * f[0] + M[3] * f[1] + M[5];
      const x0 = Math.max(x, cx - hw), x1 = Math.min(x + bw, cx + hw), y0 = Math.max(y, cy - hw * 1.35), y1 = Math.min(y + bh, cy + hw * 1.15);
      return { on: true, kind, rect: { x, y, w: bw, h: bh }, face: x1 > x0 + 1 && y1 > y0 + 1 ? { x: x0, y: y0, w: x1 - x0, h: y1 - y0 } : null,
        zoom: +(Fo.s / Math.max(bw / SRC[0], bh / SRC[1])).toFixed(4), lens: Fo.st ? Fo.st.move : "", track: tn, max_zoom: LP && LP.TI ? +Fo.zoom.toFixed(4) : null,
        soft: !!Fo.soft };
    };
    window.__speaker = speakerAt;
    return { plan: P, lens: LP ? LP.L : null, speaker: speakerAt,
      rect: (t) => { const S = BX.at(P, t); return { cx: S.cx * W, cy: S.cy * H, w: S.w * W, h: S.h * H, rot: S.rot, op: S.op != null ? S.op : 1 }; } };
  }

  // a graphic grows out of a rect (the pill, the box) into its own place: FLIP-style, 0.3 s power3.out by default.
  // el must be absolutely placed at `to` ({ x, y, w, h } px, its natural layout); from = { cx, cy, w, h } or { x, y, w, h };
  // o.fromBg (e.g. the accent: it is still the pill) -> o.bg, o.radius, o.fromRadius, o.ease
  box.morph = function (K, el, from, to, t, dur = 0.3, o = {}) {
    const fx = from.cx != null ? from.cx - from.w / 2 : from.x, fy = from.cy != null ? from.cy - from.h / 2 : from.y;
    el.style.transformOrigin = "0 0";
    K.tl.fromTo(el, { x: fx - to.x, y: fy - to.y, scaleX: from.w / to.w, scaleY: from.h / to.h, borderRadius: o.fromRadius != null ? o.fromRadius : Math.min(from.w, from.h) / 2, opacity: 1 },
      { x: 0, y: 0, scaleX: 1, scaleY: 1, borderRadius: o.radius != null ? o.radius : 28, duration: dur, ease: o.ease || "power3.out", immediateRender: false }, K.Q(t));
    if (o.fromBg) K.tl.fromTo(el, { backgroundColor: o.fromBg }, { backgroundColor: o.bg || "#ffffff", duration: dur * 0.8, ease: "power1.in", immediateRender: false }, K.Q(t));
    K.tl.set(el, { opacity: 0 }, 0);
    K.tl.set(el, { opacity: 1 }, K.Q(t));
    return el;
  };

  Object.assign(box, BX);
  HF.box = box;
})(typeof window !== "undefined" ? window : globalThis);
