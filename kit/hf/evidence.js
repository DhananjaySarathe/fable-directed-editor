/*
 * kit/hf/evidence.js: showing the evidence so a viewer can read it (2026-10-10, the reference study in
 * kit/refs/RESEARCH.md). HF.studio (16:9) and HF.reel (9:16) expose these as S.focus, S.scoreboard, S.hold, S.quiet.
 *
 *   S.focus(L, target, { at, until, line, fill, side, click })   the scene zooms to one card (or one line in it) and
 *                                         highlights the line being talked about, then hands back. Ali Abdaal's crop-in on
 *                                         a long AI answer; "a cursor action leads into a zoom".
 *   S.scoreboard(par, x, y, w, { title, rows: [{ name, color, sub }], at, fmt })  -> { set(i, value, t), win(i, t) }
 *                                         a comparison that stays on screen while results land in place (Mrwhosetheboss's
 *                                         running tally): every new result is read against the ones before it.
 *   S.flow(par, { states: [{ at, x, y, w, h, radius, bg, html, click: [u, v] }], until })   one container carries a
 *                                         workflow (prompt -> running -> result); content leaves before each move and enters
 *                                         after it settles; a pointer click can cause the change.
 *   S.hold(a, b, why)                     an intentional still: the viewer is reading or looking. qa.py --holds treats a
 *                                         freeze inside it as a hold, not a fault. Never add drift just to pass a check.
 *   S.quiet(a, b, { depth })              the music steps back (default: out) so a price, a failure or a reaction lands on
 *                                         the voice alone. kit/audio/mix.py reads it (cues.mjs writes quiet.json).
 *
 * Rules (kit/refs/EDITING.md §11):
 *   - focus only on real content: a real screenshot, the card's actual words, the number he said. Never a skeleton line.
 *   - the scoreboard's values are the ones he said or showed; it never invents a score.
 *   - a layer from S.layer() has a focus wrapper (L._F); focus moves the wrapper, the layer's own float/push stays.
 */
(function (root) {
  const HF = root.HF;
  window.__holds = window.__holds || [];
  window.__QUIET = window.__QUIET || [];

  HF.hold = (a, b, why = "") => { if (b - a > 0.05) window.__holds.push({ a: +a.toFixed(3), b: +b.toFixed(3), why: String(why).slice(0, 80) }); };
  HF.quiet = (a, b, o = {}) => { if (b - a > 0.05) window.__QUIET.push({ a: +a.toFixed(3), b: +b.toFixed(3), depth: o.depth != null ? o.depth : -60, ramp: o.ramp || 0.35 }); };

  // layout position of e inside anc (offsets only: transforms from entrances in flight don't count)
  const offsetIn = (e, anc) => {
    let x = 0, y = 0, p = e;
    while (p && p !== anc) { x += p.offsetLeft; y += p.offsetTop; p = p.offsetParent; }
    if (p !== anc) throw new Error("HF.focus: the target is not inside the layer");
    return { x, y, w: e.offsetWidth, h: e.offsetHeight };
  };

  // o: at, until (back out; omit to stay), line (a child to highlight), fill (share of the frame the target takes,
  // 0.78), max (largest zoom, 2.6), side ("left"|"right"|"top"|"bottom": leave the other side free for the speaker box),
  // dim (other rows fade while a line is highlighted), click ({ from: [x, y] } a pointer glides in and clicks first),
  // sfx (the click / settle sound; null for none)
  HF.focus = function (K, L, target, o = {}) {
    const tl = K.tl, Q = K.Q, E = HF.E, FW = K.width, FH = K.height;
    const F = L._F || L.parentElement;
    if (!F) throw new Error("HF.focus: pass a layer made by S.layer()");
    const r = offsetIn(target, L);
    const fill = o.fill || 0.78, max = o.max || 2.6;
    // the free part of the frame (the speaker box takes the other side)
    const area = { x: 0, y: 0, w: FW, h: FH };
    if (o.side === "left") area.w = FW * 0.6; else if (o.side === "right") { area.x = FW * 0.4; area.w = FW * 0.6; }
    else if (o.side === "top") area.h = FH * 0.6; else if (o.side === "bottom") { area.y = FH * 0.4; area.h = FH * 0.6; }
    const s = Math.max(1, Math.min(max, (fill * area.w) / r.w, (fill * area.h) / r.h));
    const cx = area.x + area.w / 2, cy = area.y + area.h / 2;
    const tx = cx - s * (r.x + r.w / 2), ty = cy - s * (r.y + r.h / 2);
    F.style.transformOrigin = "0 0";
    let at = o.at;
    if (o.click) {                                                          // the pointer leads into the zoom
      const [fx, fy] = o.click.from || [r.x + r.w + 220, r.y + r.h + 160];
      const px = r.x + r.w * (o.click.u != null ? o.click.u : 0.5), py = r.y + r.h * (o.click.v != null ? o.click.v : 0.5);
      const cur = K.el(L, "left:0;top:0;width:46px;height:46px;opacity:0;z-index:5;transform-origin:9px 5px",
        `<svg width="46" height="46" viewBox="0 0 24 24"><path d="M5 3l14 8-6.2 1.6L10 19z" fill="#17161f" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>`);
      const t0 = at - 0.75;
      tl.fromTo(cur, { x: fx - 9, y: fy - 5 }, { x: px - 9, y: py - 5, duration: 0.6, ease: E.move, immediateRender: true }, Q(t0));
      tl.to(cur, { opacity: 1, duration: 0.15, immediateRender: false }, Q(t0));
      tl.to(cur, { scale: 0.82, duration: 0.07, yoyo: true, repeat: 1, immediateRender: false }, Q(at - 0.12));
      tl.to(cur, { opacity: 0, duration: 0.2, immediateRender: false }, Q(at + 0.25));
      if (o.sfx !== null) K.sfx(o.sfx || "click", at - 0.12, -22, true);
    }
    tl.fromTo(F, { x: 0, y: 0, scale: 1 }, { x: tx, y: ty, scale: s, duration: 0.6, ease: E.move, immediateRender: false }, Q(at));
    const settled = at + 0.6;
    if (o.line) {
      const ln = o.line, acc = HF.C.accTint || "#ece9ff";
      ln.style.backgroundImage = `linear-gradient(${acc}, ${acc})`; ln.style.backgroundRepeat = "no-repeat";
      ln.style.backgroundSize = "0% 100%"; ln.style.borderRadius = ln.style.borderRadius || "8px";
      tl.fromTo(ln, { backgroundSize: "0% 100%" }, { backgroundSize: "100% 100%", duration: 0.4, ease: E.in, immediateRender: false }, Q(settled - 0.1));
      if (o.dim !== false && ln.parentElement) {
        const others = [...ln.parentElement.children].filter((c) => c !== ln);
        if (others.length) tl.to(others, { opacity: 0.38, duration: 0.3, immediateRender: false }, Q(settled - 0.1));
        if (o.until != null && others.length) tl.to(others, { opacity: 1, duration: 0.3, immediateRender: false }, Q(o.until));
      }
      if (o.until != null) tl.to(ln, { backgroundSize: "0% 100%", duration: 0.3, immediateRender: false }, Q(o.until));
    }
    if (o.until != null) tl.to(F, { x: 0, y: 0, scale: 1, duration: 0.5, ease: E.move, immediateRender: false }, Q(o.until));
    // a focus is read, not watched: the held part is an intentional still
    HF.hold(settled, o.until != null ? o.until : settled + (o.hold || 3), "focus: " + ((o.line || target).textContent || "").replace(/\s+/g, " ").trim().slice(0, 60));
    return { scale: s, settled };
  };

  // one container through a workflow's states (prompt -> running -> result): the same object changes shape, so the
  // viewer never loses it (reference: twoclipping-402193's UI morph, kit/refs/RESEARCH.md "Opus 5.5 collection").
  // Container and content have separate timing: the old content leaves before the container moves, the new content
  // enters once it has nearly settled, so text never overlaps or squeezes. The container animates its geometry (left/
  // top/width/height/radius/colour), never a scale, so text stays sharp. A pointer click can cause each change.
  // states: [{ at, x, y, w, h, radius, bg, html, click: [u, v] (0..1 in the old state, the pointer clicks there just
  //            before the change), sfx }]; o: spring ("snappy": ~1 % overshoot), cursor (start [x, y] page px),
  //            until (the flow leaves), hold (register readable holds, default true).
  // Every tween sits on the timeline with absolute times, so any frame seeks the same in any order.
  HF.flow = function (S, par, o = {}) {
    const { K, tl, Q, E, el, land } = S;
    const st = o.states || [];
    if (!st.length) throw new Error("HF.flow: pass states");
    const sp = HF.spring(HF.SPRING[o.spring || "snappy"]);
    const geo = (s) => ({ left: s.x, top: s.y, width: s.w, height: s.h, borderRadius: s.radius != null ? s.radius : 28, backgroundColor: s.bg || HF.C.card });   // the look's surface (HF.look)
    const s0 = st[0];
    const box = el(par, `left:${s0.x}px;top:${s0.y}px;width:${s0.w}px;height:${s0.h}px;border-radius:${geo(s0).borderRadius}px;background:${geo(s0).backgroundColor};` +
      `overflow:hidden;box-shadow:${HF.C.shadow}`, "", "hf-abs ui");
    const IN = 0.22, OUT = 0.14;
    const content = st.map((s, i) => {
      const c = el(box, `left:0;top:0;width:${s.w}px;height:${s.h}px`, s.html || "", "hf-abs");
      if (i) tl.set(c, { opacity: 0 }, 0);
      return c;
    });
    land(box, s0.at, { from: { y: 30, scale: 0.96, blur: 8 }, sfx: s0.sfx === undefined ? "slide" : s0.sfx, db: -24 });
    let cur = null, lastClick = null, cx = o.cursor ? o.cursor[0] : null, cy = o.cursor ? o.cursor[1] : null;
    for (let i = 1; i < st.length; i++) {
      const a = st[i - 1], b = st[i], T = b.at;
      if (b.click) {                                                          // the click causes the change
        const px = a.x + a.w * b.click[0], py = a.y + a.h * b.click[1];
        if (!cur) {
          cur = el(par, "left:0;top:0;width:46px;height:46px;opacity:0;z-index:5;transform-origin:9px 5px",
            `<svg width="46" height="46" viewBox="0 0 24 24"><path d="M5 3l14 8-6.2 1.6L10 19z" fill="#17161f" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>`);
          if (cx == null) { cx = px + 260; cy = py + 180; }
          tl.set(cur, { x: cx - 9, y: cy - 5 }, 0);
          tl.to(cur, { opacity: 1, duration: 0.15, immediateRender: false }, Q(T - 0.75));
        }
        tl.fromTo(cur, { x: cx - 9, y: cy - 5 }, { x: px - 9, y: py - 5, duration: 0.55, ease: E.move, immediateRender: false }, Q(T - 0.7));
        tl.to(cur, { scale: 0.82, duration: 0.07, yoyo: true, repeat: 1, immediateRender: false }, Q(T - 0.1));
        K.sfx("click", T - 0.1, -22, true);
        cx = px; cy = py; lastClick = T;
      }
      tl.to(content[i - 1], { opacity: 0, y: -8, filter: "blur(6px)", duration: OUT, ease: E.out, immediateRender: false }, Q(T - OUT * 0.6));
      tl.fromTo(box, geo(a), Object.assign(geo(b), { duration: sp.duration, ease: sp.ease, immediateRender: false }), Q(T));
      const enter = T + Math.max(0.12, sp.land * 0.85);
      tl.fromTo(content[i], { opacity: 0, y: 10, filter: "blur(6px)" }, { opacity: 1, y: 0, filter: "blur(0px)", duration: IN, ease: E.in, immediateRender: false }, Q(enter));
      if (b.sfx) K.sfx(b.sfx, enter, -22, true);
      if (o.hold !== false) {
        const end = i + 1 < st.length ? st[i + 1].at : (o.until != null ? o.until : enter + 2.5);
        HF.hold(enter + IN, end, "flow: " + (content[i].textContent || "").replace(/\s+/g, " ").trim().slice(0, 50));
      }
    }
    if (cur) tl.to(cur, { opacity: 0, duration: 0.2, immediateRender: false }, Q(Math.min(lastClick + 0.6, o.until != null ? o.until - 0.2 : 1e9)));   // gone once its work is done
    if (o.until != null) S.leave ? S.leave(box, o.until) : tl.to(box, { opacity: 0, duration: 0.25, immediateRender: false }, Q(o.until));
    return { box, content, cursor: cur, spring: sp };
  };

  // a running comparison: rows stay, values land in place, the winner is marked at the end.
  // o: title, rows [{ name, color, sub }], at, size (row text px: 40 on 16:9, 48 on 9:16), fmt (v -> text, e.g. "$" + v)
  // set(i, value, t, { fmt }) counts a number up (or writes text), win(i, t) lifts the winner and dims the rest
  HF.scoreboard = function (S, par, x, y, w, o = {}) {
    const { K, tl, Q, E, el, land } = S;
    const C = HF.C, F = HF.F;                                         // the look's tokens: a night film gets a dark card with light ink
    const sz = o.size || (K.height > K.width ? 48 : 40), rowH = Math.round(sz * 2.1), pad = Math.round(sz * 0.8);
    const rows = o.rows || [];
    const headH = o.title ? Math.round(sz * 1.6) : 0;
    const ink = o.ink || C.ink, mute = o.mute || C.mute;              // o.ink / o.mute / o.bg override the look
    const box = el(par, `left:${x}px;top:${y}px;width:${w}px;height:${headH + rows.length * rowH + pad}px;border-radius:${Math.round(sz * 0.8)}px;background:${o.bg || C.card};` +
      `box-shadow:${C.shadow};overflow:hidden`, "", "hf-abs ui");
    if (o.title) el(box, `left:${pad}px;top:${Math.round(sz * 0.55)}px;font:600 ${Math.round(sz * 0.5)}px/1 ${F.mono};letter-spacing:.16em;text-transform:uppercase;color:${mute}`, HF.esc(o.title)).dataset.decor = "1";
    const R = rows.map((r, i) => {
      const row = el(box, `left:${Math.round(pad / 2)}px;right:${Math.round(pad / 2)}px;top:${headH + Math.round(pad / 2) + i * rowH}px;height:${rowH - 8}px;border-radius:${Math.round(sz * 0.5)}px;` +
        "display:flex;align-items:center;gap:" + Math.round(sz * 0.45) + "px;padding:0 " + Math.round(pad / 2) + "px");
      row.innerHTML = `<span style="width:${Math.round(sz * 0.55)}px;height:${Math.round(sz * 0.55)}px;border-radius:50%;background:${r.color || C.acc};flex:none"></span>` +
        `<span style="font:700 ${sz}px/1 ${F.body};color:${ink};white-space:nowrap">${HF.esc(r.name)}</span>` +
        (r.sub ? `<span style="font:500 ${Math.round(sz * 0.82)}px/1 ${F.body};color:${mute};white-space:nowrap">${HF.esc(r.sub)}</span>` : "") +
        `<span class="sb-v" style="margin-left:auto;font:800 ${Math.round(sz * 1.12)}px/1 ${F.body};color:${ink};font-variant-numeric:tabular-nums;white-space:nowrap;opacity:.28">–</span>`;
      return { row, v: row.querySelector(".sb-v") };
    });
    if (o.at != null) land(box, o.at, { from: { y: 40, scale: 0.95, blur: 10 }, sfx: "slide", db: -24 });
    // values are a pure function of time (the renderer and precheck seek; a tween's onUpdate isn't reliable there)
    const ease = (u) => 1 - Math.pow(1 - u, 3);
    R.forEach((r) => { r.ev = []; });
    K.onFrame((now) => R.forEach((r) => {
      const ev = r.ev.filter((e) => e.t <= now + 1e-6).pop();
      if (!ev) { r.v.textContent = "–"; r.v.style.opacity = 0.28; return; }
      r.v.style.opacity = 1;
      const u = ev.num ? Math.min(1, (now - ev.t) / ev.dur) : 1;
      r.v.textContent = ev.num ? ev.fmt(u >= 1 ? ev.value : ev.value * ease(u)) : String(ev.value);
    }));
    const api = {
      box, rows: R,
      set(i, value, t, so = {}) {
        const r = R[i], fmt = so.fmt || o.fmt || ((v) => String(Math.round(v)));
        r.ev.push({ t: Q(t), value, num: typeof value === "number", dur: so.dur || 0.7, fmt });
        r.ev.sort((a, b) => a.t - b.t);
        tl.fromTo(r.row, { backgroundColor: "rgba(79,59,224,0)" }, { backgroundColor: C.accTint, duration: 0.18, yoyo: true, repeat: 1, immediateRender: false }, Q(t));
        if (so.sfx !== null) K.sfx(so.sfx || "tone", t, -22, true);
        return t;
      },
      win(i, t) {
        R.forEach((r, j) => { if (j !== i) tl.to(r.row, { opacity: 0.42, duration: 0.3, immediateRender: false }, Q(t)); });
        tl.to(R[i].row, { backgroundColor: C.accTint, duration: 0.3, immediateRender: false }, Q(t));
        tl.fromTo(R[i].row, { scale: 1 }, { scale: 1.035, duration: 0.14, yoyo: true, repeat: 1, ease: "power1.out", immediateRender: false }, Q(t));
        tl.set(R[i].v, { color: C.acc }, Q(t));
        K.sfx("check", t, -20, true);
        return t;
      },
    };
    return api;
  };
})(window);
