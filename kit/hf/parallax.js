/* kit/hf/parallax.js — a 2.5D camera move through a still: the photo is displaced by its depth map, so near things
 * move more than far ones and the picture reads as a shot, not a slide.
 *
 *   HF.parallax(K, parent, "assets/photo.jpg", a, b, { depth, x, y, w, h, move, amount, radius })
 *     depth   the map from kit/look/depth.py (default: the photo's path with .depth.png); white = near
 *     move    "push" (a slow push in, near things growing faster), "pan" (left to right), "orbit" (a small circle),
 *             "drift" (up and in, the default); amount scales it (1 = the designed size, keep it at 1.5 or less)
 *   The layer fades in at a and out at b (0.4 s). Frame-exact: the camera is a function of page time (K.onFrame).
 *
 * For stills shown as evidence or b-roll (a photo, a product, a place). Not his footage: his room stays as shot
 * (OWNER_DEFAULTS §2). A UI screenshot is flat; put it on a 3D card instead. Without WebGL or the depth map the photo is
 * shown with a plain Ken Burns push, so a page never breaks.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/parallax.js needs core.js first");
  const VS = "attribute vec2 p; varying vec2 v; void main(){ v = p * 0.5 + 0.5; v.y = 1.0 - v.y; gl_Position = vec4(p, 0.0, 1.0); }";
  // find the source pixel whose displaced position lands here (a few fixed-point steps on the depth)
  const FS = `precision highp float; varying vec2 v; uniform sampler2D img, dep; uniform vec2 off, crop; uniform float zoom, dz, focus;
    vec2 cov(vec2 uv) { return (uv - 0.5) * crop + 0.5; }       // the photo covers the box (cropped, never stretched)
    void main(){
      vec2 c = (v - 0.5) / zoom + 0.5; vec2 uv = c;
      for (int i = 0; i < 8; i++) {
        float d = texture2D(dep, cov(clamp(uv, 0.0, 1.0))).r - focus;
        uv = (c - 0.5) / (1.0 + dz * d) + 0.5 - off * d;
      }
      gl_FragColor = texture2D(img, cov(clamp(uv, 0.001, 0.999)));
    }`;
  const MOVES = {                                   // progress p in 0..1 -> { off: [x, y] (uv), zoom, dz }
    push: (p, k) => ({ off: [0, 0], zoom: 1.04 + 0.1 * k * p, dz: 0.25 * k * p }),
    pan: (p, k) => ({ off: [0.035 * k * (p - 0.5) * 2, 0], zoom: 1.1, dz: 0 }),
    orbit: (p, k) => ({ off: [0.025 * k * Math.cos(p * Math.PI * 2), 0.015 * k * Math.sin(p * Math.PI * 2)], zoom: 1.1, dz: 0.05 }),
    drift: (p, k) => ({ off: [0, -0.02 * k * p], zoom: 1.05 + 0.06 * k * p, dz: 0.15 * k * p }),
  };

  HF.parallax = function (K, parent, src, a, b, o = {}) {
    const move = MOVES[o.move || "drift"];
    if (!move) throw new Error(`HF.parallax: unknown move ${o.move} (${Object.keys(MOVES).join(", ")})`);
    const w = o.w || K.width, h = o.h || K.height, k = o.amount != null ? o.amount : 1;
    const box = K.el(parent, `left:${o.x || 0}px;top:${o.y || 0}px;width:${w}px;height:${h}px;overflow:hidden;opacity:0;` +
      (o.radius ? `border-radius:${o.radius}px;` : "") + (o.shadow !== false ? `box-shadow:${HF.C.shadow};` : ""));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(w * (o.scale || 2)); canvas.height = Math.round(h * (o.scale || 2));
    canvas.style.cssText = "position:absolute;left:0;top:0;width:100%;height:100%";
    box.append(canvas);
    const load = (s) => { const im = new Image(); im.src = s; return im; };
    const img = load(src), dep = load(o.depth || src.replace(/\.[a-z0-9]+$/i, ".depth.png"));
    const gl = canvas.getContext("webgl", { preserveDrawingBuffer: true, premultipliedAlpha: false });
    let prog = null, ready = false, fallback = !gl;
    const tex = (im, unit) => {
      const t = gl.createTexture(); gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im);
    };
    const init = () => {
      const sh = (type, s) => { const x = gl.createShader(type); gl.shaderSource(x, s); gl.compileShader(x); return x; };
      prog = gl.createProgram();
      gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { fallback = true; return; }
      gl.useProgram(prog);
      const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
      const loc = gl.getAttribLocation(prog, "p"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
      tex(img, 0); tex(dep, 1);
      gl.uniform1i(gl.getUniformLocation(prog, "img"), 0); gl.uniform1i(gl.getUniformLocation(prog, "dep"), 1);
      gl.uniform1f(gl.getUniformLocation(prog, "focus"), o.focus != null ? o.focus : 0.5);
      const ia = img.naturalWidth / img.naturalHeight, ba = w / h;
      gl.uniform2f(gl.getUniformLocation(prog, "crop"), ia > ba ? ba / ia : 1, ia > ba ? 1 : ia / ba);
      gl.viewport(0, 0, canvas.width, canvas.height);
      ready = true;
    };
    const ease = gsap.parseEase(o.ease || "power1.inOut");
    K.onFrame((t) => {
      if (fallback) return;
      if (!ready) { if (img.complete && img.naturalWidth && dep.complete && dep.naturalWidth) init(); else { if (dep.complete && !dep.naturalWidth) fallback = true; return; } }
      if (!ready) return;
      const m = move(ease(Math.max(0, Math.min(1, (t - a) / Math.max(0.1, b - a)))), k);
      gl.uniform2f(gl.getUniformLocation(prog, "off"), m.off[0], m.off[1]);
      gl.uniform1f(gl.getUniformLocation(prog, "zoom"), m.zoom);
      gl.uniform1f(gl.getUniformLocation(prog, "dz"), m.dz);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    });
    // no WebGL or no depth map: the photo with a plain push (decided by the first frame; the canvas is hidden then)
    const kb = document.createElement("img");
    kb.src = src; kb.style.cssText = "position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;display:none";
    box.append(kb);
    K.onFrame((t) => { if (fallback) { kb.style.display = "block"; canvas.style.display = "none";
      kb.style.transform = `scale(${1.04 + 0.08 * Math.max(0, Math.min(1, (t - a) / Math.max(0.1, b - a)))})`; } });
    K.tl.fromTo(box, { opacity: 0 }, { opacity: 1, duration: 0.4, ease: "none", immediateRender: false }, K.Q(a));
    K.tl.to(box, { opacity: 0, duration: 0.4, ease: "none", immediateRender: false }, K.Q(b - 0.4));
    return { box, canvas };
  };
})(typeof window !== "undefined" ? window : globalThis);
