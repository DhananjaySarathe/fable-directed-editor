/*
 * kit/hf/footage.js: footage-native Reels (2026-10-10). The take itself is the world: graphics live IN the shot, not on
 * a designed stage. Built after the niche study in kit/refs/RESEARCH.md ("Viral Shorts in the AI agent applies to jobs
 * niche"): the viral ones show the real thing and cut fast; when there is no screen recording, the footage-native
 * devices below beat a card world. Use with HF.reel (it keeps the box: full frame, punches, zooms, takeovers).
 *
 *   const F = HF.footage(S, st, { cut: "cut", corner: "cut2" });          // after HF.reel, before S.box()
 *   F.behind("0", a, b, { x: 540, y: 520, size: 900, color: "#ff4757" })   // y = top of the line box; page: true = page px; parent: FRONT = over him   // giant type BEHIND the speaker (the person
 *                                              matte cut-out sits on top), in the footage's own pixels: it zooms and
 *                                              shakes with the shot. o.count: [from, to, at, dur] counts the number up
 *   F.pin(track, a, b, { label, circle })      // a label (and a hand-drawn ring) on a tracked point [[t, x, y], ...]
 *   const H = F.hud(x, y, w, { title, at, until })   // a dark glass agent panel: H.cmd(text, t), H.line(text, t, kind)
 *   F.alert(text, t, { color, dur })           // a full-frame alert: edge glow, a banner, a shake of the shot
 *   F.corner(a, b, { x, y, scale })            // his cut-out in a corner while a takeover fills the frame
 *   F.flash(t, color)                          // a hit-frame flash
 * Captions: S.captions({ base: "#fff", active: F.C.go, cls: "cap bold" }) with F's bold style (white, black edge).
 *
 * Rules: words behind him are his words or his numbers; pins sit on what he points at; every element is a pure
 * function of time (K.onFrame / the timeline), so any frame seeks exactly.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.reel) throw new Error("kit/hf/footage.js needs reel.js first");
  const CSS = `
    .cap.bold { font: 900 60px/1.12 Montserrat, Inter, sans-serif; letter-spacing: -0.01em; text-transform: none; }
    .cap.bold .plate { background: none; box-shadow: none; padding: 0; }
    .cap.bold span.w { color: #fff; padding: 2px 6px; text-shadow: 0 5px 0 rgba(0,0,0,.9), 0 0 22px rgba(0,0,0,.55);
      -webkit-text-stroke: 3px rgba(0,0,0,.92); paint-order: stroke fill; }
    .fx-glass { position: absolute; border-radius: 30px; background: rgba(10, 10, 16, 0.72); backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px); box-shadow: 0 30px 70px rgba(0,0,0,.45), inset 0 0 0 1.5px rgba(255,255,255,.10); overflow: hidden; }
    .fx-mono { font-family: "JBMono", monospace; }
    .fx-behind { position: absolute; white-space: nowrap; font-family: Anton, Inter, sans-serif; line-height: .86; letter-spacing: -0.01em; }`;

  HF.footage = function (S, st, o = {}) {
    const { K, tl, Q, E, el } = S;
    if (!document.getElementById("hf-footage-css")) { const s = document.createElement("style"); s.id = "hf-footage-css"; s.textContent = CSS; document.head.append(s); }
    const C = Object.assign({ go: "#3ddc84", stop: "#ff4757", warn: "#ffd166", ink: "#f4f4f6", dim: "rgba(244,244,246,.62)" }, o.colors || {});
    const SW = 1080, SH = 1920;
    // the layer behind him, then his cut-out (same frames as the A-roll, matte-cut) on top, both inside the shot
    const behindL = el(st.wrap, `left:0;top:0;width:${SW}px;height:${SH}px;pointer-events:none`);
    behindL.dataset.over = "1";
    if (o.cut) {
      const v = document.getElementById(o.cut);
      if (!v) throw new Error("HF.footage: no <video id=" + o.cut + ">");
      v.style.cssText = `position:absolute;left:0;top:0;width:${SW}px;height:${SH}px`;
      st.wrap.append(v);
    }

    // ---------------------------------------------------------------- giant type behind him (source pixels)
    function behind(text, a, b, x = {}) {
      // centred on x without transforms (a CSS translate plus GSAP's xPercent shifted some words by half their width):
      // a 3000 px box with centred text, its transform free for the slam's scale
      const size = x.size || 700, X = x.x != null ? x.x : 540, Y = x.y != null ? x.y : 300, HW = 1500;
      const e = el(x.parent || behindL, `left:${X - HW}px;top:${Y}px;width:${HW * 2}px;text-align:center;font-size:${size}px;color:${x.color || "#111"};` +
        `transform-origin:50% 50%;${x.style || ""}`, `<span class="fx-behind-t">${HF.esc(String(text))}</span>`, "fx-behind");
      const tx = e.firstChild;
      if (x.font) e.style.fontFamily = x.font;
      e.dataset.over = "1";
      K.show(e, a, b);
      const sp = HF.spring(HF.SPRING.snappy);
      if (x.anim !== "none" && a > 0) {
        tl.fromTo(e, { scale: x.from || 1.6, opacity: 0 }, { scale: 1, opacity: 1, duration: sp.duration, ease: sp.ease, immediateRender: false }, Q(a));
        if (x.sfx !== null) K.sfx(x.sfx || "impact/impact__short-bass-hit__mixkit-2299", a, x.db || -15, true);
      }
      if (x.count) {                                           // [from, to, at, dur]: the number runs up on its word
        const [f0, f1, at, dur] = x.count;
        K.onFrame((t) => { if (t < a - 0.05 || t > b + 0.05) return; const u = Math.max(0, Math.min(1, (t - at) / dur));
          tx.textContent = String(Math.round(f0 + (f1 - f0) * (1 - Math.pow(1 - u, 3)))) + (x.suffix || ""); });
      }
      if (x.out !== false && b != null) tl.to(e, { opacity: 0, scale: 0.94, duration: 0.14, immediateRender: false }, Q(b - 0.14));
      if (x.page && !x.parent) {                                 // x, y in page px: stays put while punches move the shot behind it
        K.onFrame((t) => { if (t < a - 0.05 || t > b + 0.05) return;
          const [ox, oy, s] = toPage(0, 0);
          e.style.left = (X - ox) / s - HW + "px"; e.style.top = (Y - oy) / s + "px";
          e.style.fontSize = size / s + "px"; }, { late: true });
      }
      return e;
    }

    // ---------------------------------------------------------------- the shot's transform (box): source px -> page px
    const toPage = (x, y) => {
      const m = /matrix\(([^)]+)\)/.exec(st.wrap.style.transform || "");
      const v = m ? m[1].split(",").map(Number) : [1, 0, 0, 1, 0, 0];
      const cx = parseFloat(st.cam.style.left || 0), cy = parseFloat(st.cam.style.top || 0);
      return [cx + v[4] + x * v[0], cy + v[5] + y * v[3], v[0]];
    };
    const trackAt = (tr, t) => { let p = tr[0]; for (const q of tr) { if (q[0] <= t + 1e-4) p = q; else break; } return p; };

    // ---------------------------------------------------------------- a label on a tracked point (page layer, follows)
    function pin(track, a, b, x = {}) {
      const L = el(S.FRONT, "left:0;top:0;width:1080px;height:1920px;pointer-events:none"); L.dataset.over = "1";
      K.show(L, a, b);
      const ring = x.circle !== false ? el(L, "left:0;top:0;width:0;height:0") : null;
      let path = null;
      if (ring) {
        const r = x.r || 150;
        ring.innerHTML = `<svg width="${r * 2 + 40}" height="${r * 2 + 40}" style="position:absolute;left:${-r - 20}px;top:${-r - 20}px;overflow:visible">
          <path d="M ${20 + r * 0.15} ${20 + r * 0.55} C ${20} ${20 - r * 0.1}, ${20 + r * 2.1} ${20 - r * 0.2}, ${20 + r * 2} ${20 + r}
          C ${20 + r * 1.9} ${20 + r * 2.3}, ${20 - r * 0.15} ${20 + r * 2.15}, ${20 + r * 0.05} ${20 + r * 0.95}" fill="none" stroke="${x.color || C.warn}"
          stroke-width="11" stroke-linecap="round"/></svg>`;
        path = ring.querySelector("path"); const len = 2000; path.style.strokeDasharray = len;
        tl.fromTo(path, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: 0.45, ease: E.in, immediateRender: true }, Q(a + 0.08));
      }
      const lab = x.label ? el(L, `left:0;top:0;padding:14px 24px;border-radius:18px;background:${x.color || C.warn};color:#111;font:900 44px/1 Montserrat,Inter;white-space:nowrap;box-shadow:0 14px 34px rgba(0,0,0,.45)`, x.label) : null;
      if (lab) { tl.fromTo(lab, { scale: 0.6, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: HF.spring(HF.SPRING.thrown).ease, immediateRender: true }, Q(a + 0.3)); }
      K.onFrame((t) => {          // late: after the box has set this frame's transform
        if (t < a - 0.05 || t > b + 0.05) return;
        const p = trackAt(track, t), [px, py] = toPage(p[1], p[2]);
        if (ring) ring.style.transform = `translate(${px.toFixed(1)}px,${py.toFixed(1)}px)`;
        if (lab) { const lx = Math.max(60, Math.min(1020 - lab.offsetWidth, px + (x.dx || -lab.offsetWidth / 2))), ly = Math.max(280, Math.min(1180, py + (x.dy || 210)));
          lab.style.left = lx.toFixed(1) + "px"; lab.style.top = ly.toFixed(1) + "px"; }
      }, { late: true });
      K.sfx("whoosh/whoosh__air-woosh__mixkit-1489", a - 0.03, -20);
      return L;
    }

    // ---------------------------------------------------------------- the agent's panel (dark glass, a live log)
    function hud(x0, y0, w, x = {}) {
      const P = el(S.FRONT, `left:${x0}px;top:${y0}px;width:${w}px;height:${x.h || 120}px`, "", "fx-glass");
      P.dataset.over = "1";
      const head = el(P, "left:26px;top:20px;display:flex;align-items:center;gap:14px;font:800 42px/1 Inter;color:#fff", `${S.orbI(34)}<span>${x.title || "Instinct"}</span>
        <span class="fx-mono" data-decor="1" style="margin-left:6px;font-size:32px;letter-spacing:.12em;color:${C.go}">● LIVE</span>`);
      const body = el(P, `left:26px;top:86px;width:${w - 52}px`);
      if (x.at != null) S.land(P, x.at, { from: { y: -30, scale: 0.92, blur: 10 }, spring: "snappy", sfx: "slide", db: -22 });
      if (x.until != null) S.leave(P, x.until);
      const rows = [];
      let h = 106;
      const max = x.max || 4;                                   // at most this many lines: older ones scroll off the top
      const grow = (t) => {
        if (rows.length > max) tl.set(rows[rows.length - max - 1], { display: "none" }, Q(t - 0.02));
        h = 106 + Math.min(rows.length, max) * 66; tl.to(P, { height: h, duration: 0.22, ease: E.in, immediateRender: false }, Q(t - 0.02)); };
      const api = { panel: P };
      api.line = (text, t, kind = "ok") => {
        const col = kind === "ok" ? C.go : kind === "err" ? C.stop : kind === "warn" ? C.warn : C.dim;
        const mark = kind === "ok" ? "✓" : kind === "err" ? "✕" : kind === "warn" ? "!" : "›";
        const r = el(body, `position:relative;height:60px;margin-top:6px;display:flex;align-items:center;gap:16px;font:600 44px/1 JBMono,monospace;color:${C.ink};white-space:nowrap`,
          `<b style="color:${col};width:30px;text-align:center">${mark}</b><span>${HF.esc(text)}</span>`, "");
        rows.push(r); grow(t);
        tl.fromTo(r, { opacity: 0, x: -16 }, { opacity: 1, x: 0, duration: 0.2, ease: E.in, immediateRender: true }, Q(t));
        if (kind === "ok") K.sfx("check", t, -24); else if (kind === "err") K.sfx("ui/ui__wrong-answer-fail-notification__mixkit-946", t, -19);
        return r;
      };
      api.cmd = (text, t, cps = 18) => {
        const r = el(body, `position:relative;height:64px;margin-top:6px;display:flex;align-items:center;gap:16px;font:700 46px/1 JBMono,monospace;color:#fff;white-space:nowrap`,
          `<b style="color:${C.go}">&gt;</b><span class="ty"></span>`, "");
        rows.push(r); grow(t - 0.1);
        tl.fromTo(r, { opacity: 0 }, { opacity: 1, duration: 0.1, immediateRender: true }, Q(t - 0.1));
        K.typeText(r.querySelector(".ty"), text, t, cps, true);
        K.sfx("typing/typing__electronic-typing__mixkit-1397", t, -24);
        return r;
      };
      api.clear = (t) => { rows.forEach((r) => tl.to(r, { opacity: 0, duration: 0.15, immediateRender: false }, Q(t))); rows.length = 0; grow(t + 0.15); };
      return api;
    }

    // ---------------------------------------------------------------- full-frame alert (edge glow, banner, the shot shakes)
    function alert(text, t, x = {}) {
      const col = x.color || C.stop, dur = x.dur || 0.9;
      const L = el(S.TOP, "left:0;top:0;width:1080px;height:1920px;pointer-events:none"); L.dataset.over = "1";
      K.show(L, t - 0.02, t + dur);
      const glow = el(L, `left:0;top:0;width:1080px;height:1920px;box-shadow:inset 0 0 160px 40px ${col};opacity:0`);
      tl.fromTo(glow, { opacity: 1 }, { opacity: 0.35, duration: dur, ease: "power1.out", immediateRender: false }, Q(t));
      if (text) { const bn = el(L, `left:0;top:${x.y || 560}px;width:1080px;text-align:center`, `<span style="display:inline-block;padding:18px 40px;border-radius:20px;background:${col};color:#fff;font:400 ${x.size || 110}px/1 Anton,Inter;letter-spacing:.02em;transform:rotate(-3deg);box-shadow:0 24px 60px rgba(0,0,0,.45)">${HF.esc(text)}</span>`);
        tl.fromTo(bn, { scale: 1.8, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.22, ease: HF.spring(HF.SPRING.snappy).ease, immediateRender: true }, Q(t)); }
      K.onFrame((tt) => { if (tt < t || tt > t + 0.35) return; const k = (1 - (tt - t) / 0.35) * 14; st.cam.style.translate = `${(k * Math.sin(tt * 90)).toFixed(1)}px ${(k * Math.cos(tt * 77)).toFixed(1)}px`; });
      K.onFrame((tt) => { if (tt > t + 0.35 && tt < t + 0.45) st.cam.style.translate = "0px 0px"; });
      K.sfx(x.sfx || "impact/impact__exciting-fast-hit__mixkit-2180", t, x.db || -14, true);
      return L;
    }

    // ---------------------------------------------------------------- his cut-out in a corner over a takeover
    function corner(a, b, x = {}) {
      const vid = x.video || o.corner;                         // one <video> per corner box (a later corner() would steal it)
      const v = document.getElementById(vid);
      if (!v) throw new Error("HF.footage.corner: no <video id=" + vid + ">");
      const s = x.scale || 0.5;
      const box = el(S.FRONT, `left:${x.x != null ? x.x : -60}px;top:${x.y != null ? x.y : 1920 - SH * s + 40}px;width:${SW * s}px;height:${SH * s}px;pointer-events:none`);
      v.style.cssText = `position:absolute;left:0;top:0;width:${SW * s}px;height:${SH * s}px`;
      box.append(v);
      // the source frame's edge cuts his shoulder/arm in a hard line: feather the box edges that sit inside the page
      const fr = [], W0 = SW * s, X0 = x.x != null ? x.x : -60;
      if (X0 + W0 < 1080 - 4) fr.push("linear-gradient(to left, transparent 0, #000 110px)");
      if (X0 > 4) fr.push("linear-gradient(to right, transparent 0, #000 110px)");
      if (fr.length) { box.style.webkitMaskImage = box.style.maskImage = fr.join(","); box.style.webkitMaskComposite = "source-in"; box.style.maskComposite = "intersect"; }
      K.show(box, a, b);
      tl.fromTo(box, { x: -260, opacity: 0 }, { x: 0, opacity: 1, duration: 0.35, ease: HF.spring(HF.SPRING.snappy).ease, immediateRender: false }, Q(a));
      tl.to(box, { x: -260, opacity: 0, duration: 0.2, ease: E.out, immediateRender: false }, Q(b - 0.2));
      return box;
    }
    const flash = (t, col = "#fff") => { const f = el(S.TOP, `left:0;top:0;width:1080px;height:1920px;background:${col};opacity:0;pointer-events:none`);
      tl.fromTo(f, { opacity: 0.6 }, { opacity: 0, duration: 0.25, immediateRender: false }, Q(t)); return f; };

    return { C, behind, pin, hud, alert, corner, flash, behindL, toPage };
  };
})(window);
