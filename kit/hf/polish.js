/* kit/hf/polish.js — entrances and accents that finish a moment (needs core.js).
 *
 *   HF.tiltIn(K, el, t, { rot: 28, scale: 0.84, y: 90, dur: 0.9 })   a screen / window swings flat toward the camera
 *   HF.sweep(K, el, t, { mode: "glare" | "beam" | "text", dur, color, onDark })  a light sweep over a card, a beam round its edge,
 *                                                                     or a glint through a headline's letters
 *   HF.scramble(K, el, "Claude Opus 5.5", t, { dur: 0.8, from: "" })  characters cycle through symbols, then lock in
 *
 * Use them as accents: a sweep when a name, price or number lands (one per moment, not on every card); scramble
 * once or twice a video for a reveal; tiltIn right before a screen demo ("let me show you"). All are deterministic
 * (scramble uses a seeded hash, never Math.random), so any frame renders the same on every machine.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/polish.js needs core.js first");
  const C = HF.C;
  const clamp01 = (v) => Math.max(0, Math.min(1, v));

  // ---------------------------------------------------------------- tilt-to-flat reveal
  // The element starts tilted back (rotateX) and small, hinged near its bottom edge, and swings flat as it grows;
  // its shadow deepens as it lands. Pairs with the speaker box: the face shrinks aside in the same beat.
  HF.tiltIn = function (K, el, t, o = {}) {
    const rot = o.rot != null ? o.rot : 28, dur = o.dur || 0.9;
    const host = el.parentNode;
    if (host && !host.style.perspective) host.style.perspective = (o.persp || 1700) + "px";
    el.style.transformOrigin = o.origin || "50% 85%";
    K.tl.set(el, { opacity: 0 }, 0);
    K.tl.fromTo(el, { opacity: 0, rotationX: rot, scale: o.scale || 0.84, y: o.y != null ? o.y : 90, filter: "blur(2px)" },
      { opacity: 1, rotationX: 0, scale: 1, y: 0, filter: "blur(0px)", duration: dur, ease: o.ease || "power3.out", immediateRender: false }, K.Q(t));
    K.tl.set(el, { opacity: 1 }, K.Q(t + 0.12));                               // fully opaque early: the swing is the reveal
    K.sfx("swish", t, -22);
    return el;
  };
  // a screen demo with this entrance: HF.screen(...).tilt(a, b)  (kit/hf/screen.js)

  // ---------------------------------------------------------------- light sweep / border beam / text glint
  HF.sweep = function (K, el, t, o = {}) {
    const mode = o.mode || "glare", dur = o.dur || (mode === "beam" ? 1.6 : 0.85), Q = K.Q;
    if (mode === "text") {                                                    // the letters themselves catch the light
      const base = o.base || getComputedStyle(el).color || C.ink, hi = o.color || C.acc;
      el.style.backgroundImage = `linear-gradient(100deg, ${base} 0%, ${base} 40%, ${hi} 50%, ${base} 60%, ${base} 100%)`;
      el.style.backgroundSize = "250% 100%";
      el.style.webkitBackgroundClip = "text"; el.style.backgroundClip = "text"; el.style.color = "transparent";
      K.tl.fromTo(el, { backgroundPosition: "100% 0%" }, { backgroundPosition: "0% 0%", duration: dur, ease: "power2.inOut", immediateRender: true }, Q(t));
      return el;
    }
    const r = o.radius != null ? o.radius : getComputedStyle(el).borderRadius;
    const ov = K.el(el, `left:0;top:0;width:100%;height:100%;border-radius:${r};overflow:hidden;pointer-events:none;z-index:9`);
    if (mode === "glare") {
      // on a light card a white band is invisible: a warm sheen (accent tint, multiply) reads instead; onDark keeps a white glint
      const col = o.color || (o.onDark ? "rgba(255,255,255,.85)" : "rgba(242,170,140,.55)"), blend = o.blend || (o.onDark ? "screen" : "multiply");
      const band = K.el(ov, `left:0;top:-30%;width:30%;height:160%;background:linear-gradient(90deg, rgba(255,255,255,0) 0%, ${col} 50%, rgba(255,255,255,0) 100%);transform:skewX(-18deg);mix-blend-mode:${blend}`);
      K.tl.fromTo(band, { xPercent: -160 }, { xPercent: 460, duration: dur, ease: "power2.inOut", immediateRender: true }, Q(t));
      K.sfx("tone", t + dur * 0.4, -26);
      return ov;
    }
    // beam: a thin ring of light travels once round the edge (conic gradient masked to the border)
    const wpx = o.width || 3, col = o.color || C.acc;
    Object.assign(ov.style, { padding: wpx + "px", webkitMask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)", webkitMaskComposite: "xor",
      mask: "linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0)", opacity: "0" });
    const turns = o.turns || 1;
    K.onFrame((tt) => {
      const p = clamp01((tt - t) / dur);
      const a = 360 * turns * (1 - Math.pow(1 - p, 2.2));
      const fade = p <= 0 ? 0 : Math.min(1, p / 0.08, (1 - p) / 0.15 + 0.0001);
      ov.style.opacity = (tt < t || p >= 1 ? 0 : fade).toFixed(3);
      ov.style.background = `conic-gradient(from ${a.toFixed(1)}deg, transparent 0deg 250deg, ${col} 320deg, #fff 345deg, transparent 360deg)`;
    });
    return ov;
  };

  // ---------------------------------------------------------------- scramble / decode
  // Before t: `from` (default: blank). From t: every character shows a seeded symbol that changes every ~2 frames, and
  // characters lock in left to right over `dur` (spaces stay spaces). Pure function of time.
  const SYM = "!<>-_\\/[]{}=+*^?#%&@$~01";
  const hash = (a, b) => { const x = Math.sin(a * 91.17 + b * 47.53 + 13.1) * 43758.5453; return x - Math.floor(x); };
  HF.scrambleAt = function (text, p, frame, seed = 1, from = "") {
    if (p <= 0) return from;
    if (p >= 1) return text;
    const n = text.length;
    let s = "";
    for (let i = 0; i < n; i++) {
      const lock = (i / Math.max(1, n - 1)) * 0.82 + hash(i, seed) * 0.12;
      if (text[i] === " ") s += " ";
      else if (p >= lock + 0.06) s += text[i];
      else if (p < lock * 0.35 && i >= from.length) s += i < 1 + Math.floor(p * n * 3) ? SYM[Math.floor(hash(i + seed, Math.floor(frame / 2)) * SYM.length)] : "";
      else s += SYM[Math.floor(hash(i + seed, Math.floor(frame / 2)) * SYM.length)];
    }
    return s;
  };
  HF.scramble = function (K, el, text, t, o = {}) {
    const dur = o.dur || 0.8, seed = o.seed || text.length, from = o.from || "";
    if (o.mono !== false) el.style.fontVariantNumeric = "tabular-nums";
    K.onFrame((tt) => { el.textContent = HF.scrambleAt(text, (tt - t) / dur, Math.round(tt * K.fps), seed, from); });
    K.sfx("type", t, -26);
    return el;
  };
})(typeof window !== "undefined" ? window : globalThis);
