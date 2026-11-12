/* kit/hf/shaders.js — living backgrounds from Paper Shaders (Apache-2.0, kit/hf/lib/paper-shaders.js, shaders.paper.design).
 *
 *   HF.shaderBg(K, parent, "grain", { a, b, colors, speed, params, opacity, x, y, w, h })   a moving background layer
 *     grain   soft colour fields with film grain (a premium stage, a title card)
 *     mesh    a slow liquid mesh gradient (a calm world behind cards)
 *     rays    light rays from above with a bloom (a reveal, a payoff, an "aha")
 *     warp    a slow swirling pattern (a transition world, an intro)
 *   colors default to the look's tokens (HF.C: paper, accTint, acc, card, warm), so a shader belongs to the film's look;
 *   params override any of the shader's own settings (Paper's names: softness, intensity, noise, distortion, swirl...);
 *   speed sets its pace (each kind has a calm default, measured on a draft: the frame-to-frame change stays small). a/b fade the layer in and out (0.6 s); without them it is always on.
 *
 * Frame-exact: the shader's clock is the page's time (K.onFrame -> ShaderMount.setFrame), never requestAnimationFrame,
 * so any frame seeks to the same picture. The shader is created on the first frame its noise texture has decoded; a
 * page without the library (an older vendor/ folder) gets a CSS gradient of the same colours. Use one at a time: a
 * full-frame shader costs a GPU pass per frame (measure with the draft render).
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/shaders.js needs core.js first");
  const SIZING = ["fit", "scale", "rotation", "offsetX", "offsetY", "originX", "originY", "worldWidth", "worldHeight"];
  const KINDS = {
    grain: { speed: 0.6, frag: "grainGradientFragmentShader", sizing: "defaultObjectSizing", noise: true, enums: { shape: "GrainGradientShapes" },
      params: (C) => ({ fit: "cover", colorBack: C.paper, colors: [C.accTint, C.acc, C.card, C.warm || C.acc], softness: 0.8, intensity: 0.2, noise: 0.3, shape: "corners" }) },
    mesh: { speed: 0.35, frag: "meshGradientFragmentShader", sizing: "defaultObjectSizing", noise: false, enums: {},
      params: (C) => ({ fit: "cover", colors: [C.paper, C.accTint, C.card, C.acc], distortion: 0.7, swirl: 0.15, grainMixer: 0, grainOverlay: 0.06 }) },
    rays: { speed: 0.8, frag: "godRaysFragmentShader", sizing: "defaultObjectSizing", noise: true, enums: {},
      params: (C) => ({ fit: "cover", offsetX: 0, offsetY: -0.6, colorBack: C.paper, colorBloom: C.acc, colors: [C.accTint, C.acc, C.card],
        density: 0.3, spotty: 0.3, midIntensity: 0.4, midSize: 0.2, intensity: 0.55, bloom: 0.35 }) },
    warp: { speed: 2.5, frag: "warpFragmentShader", sizing: "defaultPatternSizing", noise: true, enums: { shape: "WarpPatterns" },
      params: (C) => ({ colors: [C.paper, C.accTint, C.paper, C.card], proportion: 0.45, softness: 1, distortion: 0.2, swirl: 0.6,
        swirlIterations: 8, shapeScale: 0.12, shape: "checks" }) },
  };
  const U = (k) => "u_" + k;

  function uniforms(P, S, p, noise) {
    const u = {}, col = (v) => P.getShaderColorFromString(v);
    for (const [k, v] of Object.entries(p)) {
      if (SIZING.includes(k)) continue;
      if (k === "colors") { u.u_colors = v.map(col); u.u_colorsCount = v.length; }
      else if (S.enums[k]) u[U(k)] = P[S.enums[k]][v];
      else if (typeof v === "string" && /^color/.test(k)) u[U(k)] = col(v);
      else u[U(k)] = v;
    }
    u.u_fit = P.ShaderFitOptions[p.fit];
    for (const k of SIZING.slice(1)) u[U(k)] = p[k];
    if (noise) u.u_noiseTexture = noise;
    return u;
  }

  HF.shaderBg = function (K, parent, kind, o = {}) {
    const S = KINDS[kind];
    if (!S) throw new Error(`HF.shaderBg: unknown kind ${kind} (${Object.keys(KINDS).join(", ")})`);
    const C = HF.C, P0 = root.PaperShaders;
    const base = S.params(C);
    if (o.colors) base.colors = o.colors;
    const op = o.opacity != null ? o.opacity : 1, speed = o.speed != null ? o.speed : S.speed, t0 = o.a || 0;
    const box = K.el(parent, `left:${o.x || 0}px;top:${o.y || 0}px;width:${o.w || K.width}px;height:${o.h || K.height}px;` +
      `opacity:${o.a != null ? 0 : op};overflow:hidden;pointer-events:none;${o.radius ? `border-radius:${o.radius}px;` : ""}`);
    box.dataset.decor = "shader";                                 // decoration: precheck reads no text here
    const params = Object.assign({}, P0 ? P0[S.sizing] : {}, base, o.params || {});
    let mount = null, failed = !P0;
    if (failed) box.style.background = `linear-gradient(135deg, ${(params.colors || [C.paper, C.accTint]).join(", ")})`;
    const make = () => {
      const P = root.PaperShaders;
      const noise = S.noise ? P.getShaderNoiseTexture() : null;
      if (noise && !(noise.complete && noise.naturalWidth)) return;             // still decoding: try on the next frame
      try {
        mount = new P.ShaderMount(box, P[S.frag], uniforms(P, S, params, noise), { preserveDrawingBuffer: true }, 0, 0, o.pixelRatio || 1);
      } catch (e) {
        failed = true;
        box.style.background = `linear-gradient(135deg, ${(params.colors || [C.paper, C.accTint]).join(", ")})`;
        console.warn("HF.shaderBg:", e.message);
      }
    };
    K.onFrame((t) => {
      if (failed) return;
      if (!mount) make();
      if (mount) mount.setFrame(Math.max(0, t - t0) * 1000 * speed);
    });
    if (o.a != null) K.tl.fromTo(box, { opacity: 0 }, { opacity: op, duration: 0.6, ease: "none", immediateRender: false }, K.Q(o.a));
    if (o.b != null) K.tl.to(box, { opacity: 0, duration: 0.6, ease: "none", immediateRender: false }, K.Q(o.b - 0.6));
    return { box, get mount() { return mount; } };
  };
})(typeof window !== "undefined" ? window : globalThis);
