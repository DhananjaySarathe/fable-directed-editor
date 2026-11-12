/*
 * kit/hf/night_reel.js: the night build for 9:16 (2026-10-18, films/ai-portfolio-shorts), the vertical sibling of
 * kit/hf/night.js. It re-skins an HF.reel frame (the box, layers, captions and safe zones stay) as the film's dark
 * developer desktop, so a film's promo Shorts look like the film:
 *
 *   const S = HF.reel(K, ROOT, st, { end, talk, palette: HF.nightReel.PALETTE, label: "" });
 *   const N = HF.nightReel(S, st, { theme: "night" });
 *   N.theme(t, "claude")                 the room's light from t (night, gpt, claude, argon, verdict), as night.js
 *   N.win(par, x, y, w, h, { src, start, dur, media, url, team, label, srcW, srcH })   a dark browser window
 *   N.card / N.chip / N.lbl / N.stamp / N.icon / N.badge / N.word   dark glass, his words only, big type
 *     (N.stamp(..., { db }) sets its hit's level; N.word(..., { over: true }) marks a hero word meant to cross the face;
 *     N.word(..., { fast: true }) is the hero slam: sharp and white by ~0.15 s, where the default spring blurs for ~0.5 s)
 *   N.pip(a, b, { at: [[t, cx, cy, d], ...], face: (t) => [cx, cy, head_w], video: "pip" })   a face circle
 *   S.captions({ base: "#eef0f5", active: N.C.acc })   captions on dark plates (the CSS here restyles .cap)
 *
 * Text >= 36 px inside x 60..1020, y 270..1250 (the Reel safe band); the team colours and the apps' own icons as in
 * night.js; everything a pure function of time.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.reel) throw new Error("kit/hf/night_reel.js needs reel.js first");
  const WD = 1080, HT = 1920;
  const PALETTE = { ink: "#eef0f5", ink2: "#a7afbd", mute: "#7a8394", acc: "#f5c451", accTint: "rgba(245,196,81,.16)",
    ok: "#3ddc84", okSoft: "rgba(61,220,132,.16)", bad: "#ff5d5d", warm: "#f5c451", onVideo: "#ffd98a", paper: "#07090d",
    orb: "#f5c451", aurora: ["rgba(0,0,0,0)", "rgba(0,0,0,0)", "rgba(0,0,0,0)", "rgba(0,0,0,0)"] };
  const TEAM = (HF.night && HF.night.TEAM) || {
    gpt: { name: "GPT-6 Astra", tool: "Codex", color: "#10a37f", icon: "assets/icons/chatgpt.png" },
    claude: { name: "Claude", tool: "Claude Code", color: "#d97757", icon: "assets/icons/claude.png" },
    argon: { name: "Gemini 4 Argon", tool: "Gemini app", color: "#8b7cf6", grad: "linear-gradient(92deg,#4c8df6 0%,#9b6cf2 100%)", icon: "assets/icons/gemini.png" },
    current: { name: "my current site", tool: "live", color: "#8a93a3", icon: null },
  };
  const CSS = `
    .nr { font-family: "Inter", sans-serif; color: #eef0f5; }
    .nr-mono { font-family: "JBMono", monospace; }
    .nr-card { position: absolute; border-radius: 30px; background: rgba(14,17,23,.94); overflow: hidden;
      box-shadow: 0 40px 110px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.09), inset 0 1px 0 rgba(255,255,255,.05); }
    .nr-chip { position: absolute; display: inline-flex; align-items: center; gap: 16px; padding: 18px 30px 18px 20px; border-radius: 999px;
      background: rgba(18,21,28,.94); box-shadow: 0 18px 44px rgba(0,0,0,.5), 0 0 0 1px rgba(255,255,255,.1); white-space: nowrap;
      font: 800 40px/1 "Inter"; color: #eef0f5; }
    .nr-icon { width: 1em; height: 1em; border-radius: 0.24em; display: inline-block; flex: none; background-size: cover; background-position: center; }
    .nr-lbl { font: 700 24px/1 "JBMono", monospace; letter-spacing: .16em; text-transform: uppercase; color: #7a8394; white-space: nowrap; }
    .hf-win.nrw { border-radius: 24px; background: #0b0e13; box-shadow: 0 50px 120px rgba(0,0,0,.65), 0 0 0 1px rgba(255,255,255,.1); }
    .hf-win.nrw .bar { background: #12151c; border-bottom: 1px solid rgba(255,255,255,.07); }
    .hf-win.nrw .url { background: #0b0e13; color: #9aa3b2; border: 1px solid rgba(255,255,255,.08); font: 500 22px/30px "JBMono", monospace; padding: 0 14px; }
    .nr-stamp { position: absolute; font: 900 84px/1 "Inter"; letter-spacing: .02em; text-transform: uppercase; white-space: nowrap;
      padding: 14px 30px 16px; border: 9px solid currentColor; border-radius: 22px; background: rgba(7,9,13,.86); }
    .nr-word { position: absolute; white-space: nowrap; font: 900 200px/0.92 "Inter"; letter-spacing: -0.04em; }
    .nr-grad { -webkit-background-clip: text; background-clip: text; color: transparent; }
    .cap { font: 800 50px/1.12 "Inter" !important; color: #eef0f5 !important; }
    .cap .plate { background: rgba(10,12,17,.9) !important; box-shadow: 0 14px 34px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.08) !important; }`;

  HF.nightReel = function (S, st, o = {}) {
    const { K, tl, Q, E, el, f1 } = S;
    const C = Object.assign({}, S.C, PALETTE, o.colors || {});
    if (!document.getElementById("hf-night-reel-css")) { const s = document.createElement("style"); s.id = "hf-night-reel-css"; s.textContent = CSS; document.head.append(s); }
    if (o.look !== false) HF.look("night", HF.lookOver(o.colors));             // the kit's components go dark glass too (S.ui, code, sketch...)
    const ROOT = S.WORLD.parentElement;
    const team = (id) => TEAM[id] || { name: id, color: C.acc };
    ROOT.style.background = C.paper;

    // ---------------------------------------------------------------- the world: the grid, lit by the story (as night.js)
    const W0 = S.WORLD;
    W0.innerHTML = "";
    W0.style.background = C.paper;
    const gridCss = (col) => `background-image:linear-gradient(${col} 1px, transparent 1px),linear-gradient(90deg, ${col} 1px, transparent 1px);background-size:60px 60px`;
    const mask = "radial-gradient(ellipse 80% 72% at 50% 44%, #000 30%, rgba(0,0,0,0) 100%)";
    const grid = el(W0, `left:-60px;top:-60px;width:${WD + 120}px;height:${HT + 120}px;${gridCss("rgba(255,255,255,0.06)")};-webkit-mask-image:${mask};mask-image:${mask}`);
    const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a.toFixed(3)})`; };
    const THEMES = Object.assign({
      night: [["#f5a623", 140, 1680, 760, 1], ["#4c7dff", 960, 260, 820, 1]],
      gpt: [["#f5a623", 140, 1680, 640, 0.55], ["#10a37f", 960, 280, 860, 1]],
      claude: [["#f5a623", 140, 1680, 640, 0.55], ["#e07a55", 960, 280, 860, 1]],
      argon: [["#9b6cf2", 140, 1660, 760, 0.85], ["#4c8df6", 960, 260, 860, 1]],
      verdict: [["#e07a55", 120, 900, 820, 1], ["#8b7cf6", 980, 900, 760, 0.75]],
    }, o.themes || {});
    const LIT = {};
    Object.entries(THEMES).forEach(([name, lights]) => {
      const g = el(W0, `left:0;top:0;width:${WD}px;height:${HT}px;display:none`);
      const parts = lights.map(([col, x, y, r, k], i) => {
        const wash = el(g, `left:${x - r}px;top:${y - r}px;width:${2 * r}px;height:${2 * r}px;border-radius:50%;background:radial-gradient(circle, ${rgba(col, 0.2 * k)} 0%, ${rgba(col, 0.07 * k)} 38%, ${rgba(col, 0)} 68%)`);
        const m = `radial-gradient(circle ${r}px at ${x}px ${y}px, #000 0%, rgba(0,0,0,.55) 45%, rgba(0,0,0,0) 100%)`;
        const reach = el(g, `left:0;top:0;width:${WD}px;height:${HT}px;overflow:hidden;-webkit-mask-image:${m};mask-image:${m}`);
        const lines = el(reach, `left:-60px;top:-60px;width:${WD + 120}px;height:${HT + 120}px;${gridCss(rgba(col, 0.34 * k))}`);
        return { wash, lines, ph: i * 1.7 + name.length };
      });
      LIT[name] = { g, parts };
    });
    const SCHED = [[-1e9, o.theme || "night"]], FADE = o.themeFade || 0.8;
    const theme = (t, name) => { if (!LIT[name]) throw new Error("HF.nightReel.theme: no theme " + name); SCHED.push([t, name]); SCHED.sort((a, b) => a[0] - b[0]); };
    el(W0, `left:0;top:0;width:${WD}px;height:${HT}px;background:radial-gradient(ellipse 90% 80% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,.6) 100%)`);
    K.onFrame((t) => {
      const gx = (-(t * 5) % 60).toFixed(2), gy = (-(t * 3) % 60).toFixed(2);
      grid.style.transform = `translate(${gx}px,${gy}px)`;
      let k = 0;
      while (k + 1 < SCHED.length && SCHED[k + 1][0] <= t) k++;
      const cur = SCHED[k][1], prev = k ? SCHED[k - 1][1] : cur, u = k ? Math.min(1, Math.max(0, (t - SCHED[k][0]) / FADE)) : 1;
      Object.entries(LIT).forEach(([name, L]) => {
        const op = name === cur ? (prev === cur ? 1 : u) : name === prev ? 1 - u : 0;
        L.g.style.display = op > 0.001 ? "block" : "none";
        if (op <= 0.001) return;
        L.g.style.opacity = op.toFixed(3);
        L.parts.forEach((p) => {
          p.lines.style.transform = `translate(${gx}px,${gy}px)`;
          p.wash.style.transform = `translate(${(60 * Math.sin(t * 0.1 + p.ph)).toFixed(1)}px,${(80 * Math.cos(t * 0.08 + p.ph)).toFixed(1)}px)`;
        });
      });
    });

    // ---------------------------------------------------------------- pieces
    const icon = (id, s = 44) => { const m = team(id); return m.icon ? `<span class="nr-icon" style="width:${s}px;height:${s}px;background-image:url(${m.icon})"></span>`
      : `<span style="width:${Math.round(s * 0.5)}px;height:${Math.round(s * 0.5)}px;border-radius:50%;display:inline-block;flex:none;background:${m.color}"></span>`; };
    const badge = (id, s = 44) => `${icon(id, s)}<span style="font:800 ${Math.round(s * 0.86)}px/1 Inter;color:#fff">${HF.esc(team(id).name)}</span>`;
    const chip = (par, x, y, html, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, html, "nr-chip");
    const card = (par, x, y, w, h, html = "", style = "") => el(par, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;${style}`, html, "nr-card nr");
    const lbl = (par, x, y, text, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, HF.esc(text), "hf-abs nr-lbl lbl");
    const win = (par, x, y, w, h, wo = {}) => {
      const sd = HF.screen(K, par, { x, y, w, h, src: wo.src, img: wo.img, start: wo.start || 0, dur: wo.dur || 10, mediaStart: wo.media || 0,
        srcW: wo.srcW || 3840, srcH: wo.srcH || 2160, url: wo.url || "", dark: true, track: wo.track, fit: wo.fit });
      sd.box.classList.add("nrw");
      sd.box.querySelector(".bar").dataset.decor = "1";
      if (wo.team) {
        const m = team(wo.team);
        const tag = el(sd.box.querySelector(".bar"), `right:14px;top:8px;display:flex;align-items:center;gap:10px;padding:5px 12px 5px 6px;border-radius:9px;` +
          `background:rgba(255,255,255,.06);font:700 22px/1 Inter;color:#fff;white-space:nowrap;z-index:3`, `${icon(wo.team, 28)}${HF.esc(wo.label || m.name)}`);
        tag.dataset.decor = "1";
        sd.box.style.boxShadow = `0 50px 120px rgba(0,0,0,.65), 0 0 0 1px rgba(255,255,255,.1), 0 0 0 ${wo.ring || 0}px ${m.color}`;
      }
      return sd;
    };
    const stamp = (par, text, x, y, t, so = {}) => {
      const s = el(par, `left:${x}px;top:${y}px;color:${so.color || C.acc};transform:rotate(${so.rot != null ? so.rot : -7}deg);font-size:${so.size || 84}px`, HF.esc(text), "nr-stamp");
      const sp = HF.spring(HF.SPRING.snappy);
      tl.fromTo(s, { opacity: 0 }, { opacity: 1, duration: 0.05, immediateRender: true }, Q(t));
      tl.fromTo(s, { scale: 2.0 }, { scale: 1, duration: sp.duration, ease: sp.ease, immediateRender: true }, Q(t));
      if (so.sfx !== null) K.sfx(so.sfx || "impact/impact__exciting-fast-hit__mixkit-2180", t + 0.05, so.db != null ? so.db : -15, true);
      if (so.until) tl.to(s, { opacity: 0, duration: 0.2, immediateRender: false }, Q(so.until - 0.2));
      return s;
    };
    // big type: a slam on the snappy spring; x/y is its top centre (align "left" / "right" for an edge)
    const word = (par, text, a, b, x = {}) => {
      const w = el(par, `left:${x.x != null ? x.x : WD / 2}px;top:${x.y != null ? x.y : 300}px;font-size:${x.size || 180}px;` +
        `${x.align === "left" ? "" : x.align === "right" ? "transform:translateX(-100%);" : "transform:translateX(-50%);"}`, "", "nr-word");
      const inner = document.createElement("span");
      inner.innerHTML = x.html || HF.esc(text);
      inner.style.display = "inline-block";
      inner.style.opacity = "0";   // hidden until its slam: a renderer seeking back past the tween showed it sharp for a frame
      if (x.grad) { inner.className = "nr-grad"; inner.style.backgroundImage = x.grad; } else inner.style.color = x.color || "#fff";
      if (x.over) w.dataset.over = "1";                              // a hero word meant to sit over the face (precheck: not a defect)
      if (x.font) w.style.fontFamily = x.font;
      if (x.weight) w.style.fontWeight = x.weight;
      if (x.italic) w.style.fontStyle = "italic";
      if (x.shadow !== false) inner.style.textShadow = "0 10px 40px rgba(0,0,0,.55)";
      w.append(inner);
      K.show(w, a - 0.02, b);
      const sp = HF.spring(HF.SPRING.snappy);
      tl.fromTo(inner, { opacity: 0 }, { opacity: 1, duration: 2 * f1, ease: "none", immediateRender: false }, Q(a));
      if (x.fast) {                                                  // a hero slam: crisp and white by ~0.15 s, settled by 0.3 s
        tl.fromTo(inner, { scale: x.from || 1.4 }, { scale: 1, duration: 0.3, ease: "expo.out", immediateRender: false }, Q(a));
        tl.fromTo(inner, { filter: "blur(10px)" }, { filter: "blur(0px)", duration: 0.14, ease: "power2.out", immediateRender: false }, Q(a));
      } else tl.fromTo(inner, { scale: x.from || 1.4, filter: "blur(14px)" }, { scale: 1, filter: "blur(0px)", duration: sp.duration, ease: sp.ease, immediateRender: false }, Q(a));
      if (x.sfx !== null) K.sfx(x.sfx || "impact/impact__short-bass-hit__mixkit-2299", a, x.db != null ? x.db : -15, true);
      if (b != null) tl.to(inner, { opacity: 0, scale: 0.96, duration: 0.16, ease: E.out, immediateRender: false }, Q(b - 0.16));
      return w;
    };
    // a face circle from a <video id=...> of the speaker (moves and resizes between beats, as night.js pip)
    const pip = (a, b, po = {}) => {
      const v = document.getElementById(po.video || "pip");
      if (!v) throw new Error("HF.nightReel.pip: no <video id=" + (po.video || "pip") + ">");
      const at = (po.at || [[a, 540, 1500, 360]]).slice().sort((p, q) => p[0] - q[0]);
      const ring = el(ROOT, `left:0;top:0;width:300px;height:300px;z-index:${po.z || 5};border-radius:50%;overflow:hidden;background:#0b0e13;` +
        `box-shadow:0 30px 80px rgba(0,0,0,.6),0 0 0 4px rgba(255,255,255,.18);opacity:0`);
      ring.dataset.face = "1";
      v.style.cssText = `position:absolute;left:0;top:0;width:${po.srcW || 1920}px;height:${po.srcH || 1080}px;transform-origin:0 0`;
      ring.append(v);
      const vig = el(ring, "left:0;top:0;width:100%;height:100%;border-radius:50%;background:radial-gradient(circle at 50% 44%, rgba(7,9,13,0) 52%, rgba(7,9,13,.5) 100%)");
      vig.dataset.decor = "1";
      const mv = po.move || 0.4, head = po.head || 0.5, ez = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
      const where = (t) => {
        let k = 0;
        while (k + 1 < at.length && at[k + 1][0] <= t) k++;
        const cur = at[k], prev = k ? at[k - 1] : cur, u = k ? Math.min(1, Math.max(0, (t - cur[0]) / mv)) : 1, e = ez(u);
        return [1, 2, 3].map((i) => prev[i] + (cur[i] - prev[i]) * e);
      };
      K.onFrame((t) => {
        const [cx, cy, d] = where(t), f = (po.face && po.face(t)) || [960, 560, 280], s = (head * d) / f[2];
        ring.style.width = ring.style.height = `${d.toFixed(1)}px`;
        ring.style.transform = `translate(${(cx - d / 2).toFixed(1)}px,${(cy - d / 2).toFixed(1)}px)`;
        v.style.transform = `translate(${(d / 2 - f[0] * s).toFixed(1)}px,${(d / 2 - f[1] * s).toFixed(1)}px) scale(${s.toFixed(4)})`;
        ring.style.opacity = (t < a || t > b + 0.25 ? 0 : Math.min(1, (t - a) / 0.2, (b + 0.25 - t) / 0.25)).toFixed(3);
      });
      return ring;
    };
    // the speaker's real face on the frame at time t (box state + cover crop + the face track): { left, right, top, bottom,
    // mouth } in page px, or null when the box is hidden. window.__faceRect lets precheck test text against the real face
    // instead of the generic 42 % zone; capY(t, y0) puts a caption page at y0 unless the face is there (then below the chin,
    // or above the head when the chin is too low for the band)
    const faceRect = (t) => {
      const P = window.__box && window.__box.plan, faces = o.faces;
      if (!P || !faces || !faces.length) return null;
      const B = HF.box.at(P, t);
      if (!B || (B.op != null && B.op < 0.5) || B.w * WD < 120) return null;
      const bw = B.w * WD, bh = B.h * HT, x0 = B.cx * WD - bw / 2, y0 = B.cy * HT - bh / 2;
      const f = faces[Math.max(0, Math.min(faces.length - 1, Math.floor(t * (K.fps || 30))))];
      const I = HF.box.inner(bw, bh, [f[0], f[1]], B.zoom, o.src || [WD, HT]);
      const cx = x0 + I.tx + f[0] * I.s, cy = y0 + I.ty + f[1] * I.s, fw = f[2] * I.s;
      // the track's point is about the nose and w the face box width: forehead ~0.8 w above it, chin ~0.7 w below; the hair
      // reaches ~1.35 w above it (measured: Short A 19.2 s, hair top 470 for a face box top of 671): head is for captions
      return { left: cx - 0.6 * fw, right: cx + 0.6 * fw, top: Math.max(y0, cy - 0.8 * fw), bottom: Math.min(y0 + bh, cy + 0.7 * fw), mouth: cy + 0.4 * fw,
        head: Math.max(y0, cy - 1.35 * fw) };
    };
    window.__faceRect = faceRect;
    // capY(t, y0, h, tEnd, topLimit): sampled over the page's whole time [t, tEnd]; topLimit = the lowest edge of the overlays
    // above (a caption above the head never climbs into them: it goes under the chin instead, up to y 1290)
    const capY = (t, y0 = 1176, h = 70, tEnd = null, topLimit = 300) => {
      let worst = null, hair = 1e9, brow = 1e9;
      const e = tEnd != null ? Math.max(t + 0.1, tEnd) : t + 0.8;
      for (let k = 0; k <= 6; k++) { const r = faceRect(t + ((e - t) * k) / 6); if (r) { if (!worst || r.bottom > worst.bottom) worst = r; hair = Math.min(hair, r.head); brow = Math.min(brow, r.top); } }
      if (!worst || worst.bottom < y0 - 6 || worst.top > y0 + h) return y0;          // clear of the face
      if (worst.bottom + 12 + h <= 1250) return Math.max(y0, worst.bottom + 12);     // under the chin, still in the band
      if (hair - h - 16 >= topLimit) return hair - h - 16;                           // above his hair
      if (brow - h - 16 >= topLimit) return brow - h - 16;                           // over the hair, still off the face
      return Math.min(1290 - h, worst.bottom + 12);                                  // no room above: under the chin, a little low
    };
    return { C, TEAM, team, theme, THEMES, icon, badge, chip, card, lbl, win, stamp, word, pip, faceRect, capY };
  };
  HF.nightReel.PALETTE = PALETTE;
})(window);
