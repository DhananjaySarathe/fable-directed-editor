/*
 * kit/hf/paper.js: the paper-collage explainer look (kit/presets/paper_collage), studied 2026-10-11 on a fliki reel
 * (instagram.com/p/Dcblnu1gyAP): photoreal objects cut out on aged paper and newsprint, stamped headlines, masking-tape
 * labels, red marker strokes drawn on, polaroids, torn price tags, a hand-drawn chart, a phone. Works inside HF.reel or
 * HF.studio (pass S); every element is a pure function of timeline time, so any frame seeks the same.
 *
 *   const P = HF.paper(S);                                 // after HF.reel / HF.studio (needs annotate.js for ink)
 *   P.bg(par, { x, y, w, h, news: ["his words", ...] })    aged paper + faint newsprint columns + grain + stains
 *   P.hero(par, src, { x, y, h, at, from: "drop"|"rise"|"pop", bob, shadow })   a cut-out object (kit/look/objects.py)
 *   P.stamp(par, "THIS TOY IS|EVERYWHERE.", { x, y, size, at, per, color, words })  bold caps slammed in, line by line
 *   P.tape(par, "LABUBU", { x, y, rot, at, size })          a masking-tape label, typewriter text
 *   P.polaroid(par, src, { x, y, w, rot, at, caption })     a photo in a white frame, thrown in
 *   P.ticket(par, { title, value, sub, x, y, w, rot, at })  a torn yellow ticket with one big number
 *   P.tag(par, text, { x, y, rot, at, color })              a torn red price tag
 *   P.chart(par, { x, y, w, h, values, labels, at, dur, title })  graph paper, axes and a line that draws itself
 *   P.phone(par, src, { x, y, h, at, rot })                 a phone with an image (or HTML) on its screen
 *   P.ink(par, box)                                         red marker: HF.annotate in the preset's red (circle, arrow, note)
 *   P.clipping(par, { title, body, x, y, w, rot, at })      a newspaper clipping with a headline
 *
 * Honesty rules (README): objects are illustrations, labelled as such where it matters; every number is one he said or
 * showed; no real logos unless he names the product; generated people are never presented as real people.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/paper.js needs core.js first");
  const CSS = `
    .pp-paper { position: absolute; overflow: hidden; background: #eee4cf; }
    .pp-news { position: absolute; font: 400 15px/1.32 Georgia, "Times New Roman", serif; color: rgba(40,32,20,.34); text-align: justify; overflow: hidden; }
    .pp-news b { display: block; font: 700 30px/1 Georgia, serif; color: rgba(40,32,20,.3); margin-bottom: 8px; letter-spacing: -.01em; }
    .pp-stamp { position: absolute; font: 400 120px/0.92 Anton, "Oswald", sans-serif; text-transform: uppercase; color: #121212; letter-spacing: .005em; white-space: nowrap; }
    .pp-tape { position: absolute; padding: 14px 26px 12px; background: rgba(226,208,164,.94); font: 700 38px/1 "JBMono", monospace; letter-spacing: .06em;
      color: #1d1a14; text-transform: uppercase; white-space: nowrap; box-shadow: 0 4px 10px rgba(0,0,0,.18);
      clip-path: polygon(0 6%, 3% 0, 97% 4%, 100% 0, 98% 50%, 100% 100%, 96% 94%, 4% 100%, 0 96%, 2% 50%); }
    .pp-pol { position: absolute; background: #fbfaf6; padding: 14px 14px 52px; box-shadow: 0 18px 34px rgba(30,20,10,.35); }
    .pp-pol img, .pp-pol .pp-img { display: block; width: 100%; object-fit: cover; }
    .pp-pol { padding-bottom: 64px; } .pp-pol i { position: absolute; left: 0; right: 0; bottom: 14px; text-align: center; font: 400 42px/1 Caveat, cursive; color: #2a2620; font-style: normal; }
    .pp-ticket { position: absolute; background: #f2c84b; color: #141210; padding: 26px 30px 30px; box-shadow: 0 16px 30px rgba(40,28,6,.32);
      clip-path: polygon(0 3%, 6% 0, 12% 3%, 20% 0, 30% 3%, 40% 0, 52% 3%, 64% 0, 76% 3%, 88% 0, 100% 2%, 100% 100%, 0 100%); }
    .pp-ticket b { display: block; font: 400 40px/1 Anton, sans-serif; text-transform: uppercase; }
    .pp-ticket strong { display: block; font: 400 110px/1 Anton, sans-serif; margin-top: 10px; letter-spacing: -.01em; }
    .pp-ticket span { display: block; font: 700 22px/1.2 "JBMono", monospace; margin-top: 10px; letter-spacing: .08em; text-transform: uppercase; }
    .pp-tag { position: absolute; padding: 12px 22px 12px 34px; background: #d6452f; color: #fff7ee; font: 400 44px/1 Anton, sans-serif; white-space: nowrap;
      box-shadow: 0 10px 20px rgba(80,20,10,.3); clip-path: polygon(14px 0, 100% 0, 98% 50%, 100% 100%, 14px 100%, 0 50%); }
    .pp-clip { position: absolute; background: #f3ecdc; padding: 22px 26px; box-shadow: 0 12px 26px rgba(30,20,10,.25); font: 400 19px/1.35 Georgia, serif; color: #2b241a; text-align: justify;
      clip-path: polygon(0 2%, 4% 0, 9% 2%, 15% 0, 22% 2%, 30% 0, 38% 2%, 47% 0, 56% 2%, 65% 0, 74% 2%, 83% 0, 92% 2%, 100% 0, 100% 98%, 95% 100%, 88% 98%, 80% 100%, 71% 98%, 62% 100%, 53% 98%, 44% 100%, 35% 98%, 26% 100%, 17% 98%, 8% 100%, 0 98%); }
    .pp-clip b { display: block; font: 700 40px/1.05 Georgia, serif; margin-bottom: 12px; letter-spacing: -.01em; text-align: left; }
    .pp-phone { position: absolute; border-radius: 54px; background: #111; padding: 16px; box-shadow: 0 26px 50px rgba(20,14,8,.45), inset 0 0 0 3px #2b2b2b; }
    .pp-phone .scr { position: relative; width: 100%; height: 100%; border-radius: 40px; overflow: hidden; background: #f4efe4; }
  `;
  const RED = "#d6452f";

  HF.paper = function (S, o = {}) {
    const K = S.K, tl = K.tl, Q = K.Q, E = HF.E, el = K.el;
    if (!document.getElementById("hf-paper-css")) { const s = document.createElement("style"); s.id = "hf-paper-css"; s.textContent = CSS; document.head.append(s); }
    if (HF.handFont) HF.handFont();
    // o.look: the film IS a paper collage (its UI cards, code, sketches take paper and ink). Off by default: a paper beat
    // usually sits inside another look's Reel (kit/presets/paper_collage)
    if (o.look) HF.look("paper_collage", HF.lookOver(o.palette));
    const rng = HF.rng ? HF.rng(o.seed || 7) : Math.random;
    const P = { RED };

    // a thrown-in entrance: lands with a small rotation settle and a short shadow pop (no bounce past ~2 %)
    const throwIn = (e, t, from = "drop", rot = 0, x = {}) => {
      if (t == null) return;
      const d = { drop: { y: -140, rotation: rot - 9, scale: 1.08 }, rise: { y: 120, rotation: rot + 5, scale: 0.96 }, pop: { y: 0, rotation: rot, scale: 0.6 },
        left: { x: -260, rotation: rot - 12, scale: 1 }, right: { x: 260, rotation: rot + 12, scale: 1 } }[from] || {};
      const sp = HF.spring(HF.SPRING[x.spring || "snappy"]);
      e.style.opacity = 0;                                                  // hidden until it is thrown (also on frame 1)
      tl.fromTo(e, { opacity: 0 }, { opacity: 1, duration: 0.12, immediateRender: false }, Q(t));
      tl.fromTo(e, { x: d.x || 0, y: d.y || 0, rotation: d.rotation != null ? d.rotation : rot, scale: d.scale || 1 },
        { x: 0, y: 0, rotation: rot, scale: 1, duration: sp.duration, ease: sp.ease, immediateRender: false }, Q(t));
      if (x.sfx !== null) K.sfx(x.sfx || "ui/ui__select-click__mixkit-1109", t + sp.land, x.db != null ? x.db : -24);
    };
    P.throwIn = throwIn;

    // aged paper: cream base, soft stains, faint newsprint columns of HIS words (texture only, low contrast), grain
    P.bg = (par, x = {}) => {
      const X = x.x || 0, Y = x.y || 0, W = x.w || K.width, H = x.h || K.height;
      const pp = el(par, `left:${X}px;top:${Y}px;width:${W}px;height:${H}px`, "", "pp-paper");
      el(pp, `left:0;top:0;width:${W}px;height:${H}px;background:radial-gradient(ellipse at 30% 20%, rgba(255,250,236,.7), rgba(255,250,236,0) 60%),` +
        `radial-gradient(ellipse at 80% 85%, rgba(150,110,60,.16), rgba(150,110,60,0) 55%),radial-gradient(ellipse at 10% 90%, rgba(120,90,50,.12), rgba(120,90,50,0) 50%)`);
      const words = (x.news && x.news.length ? x.news : ["", ""]).join(" ").trim();
      const cols = x.cols != null ? x.cols : Math.max(2, Math.round(W / 300));
      if (x.news !== false) for (let c = 0; c < cols; c++) {
        if (rng() < 0.35) continue;                                       // gaps: a collage, not a page
        const cw = W / cols - 26, nx = c * (W / cols) + 13, ny = 10 + rng() * H * 0.5, nh = H * (0.25 + rng() * 0.4);
        const body = (words || "the edit is code and every frame is a function of time").repeat(Math.ceil(1600 / Math.max(20, words.length)));
        el(pp, `left:${nx}px;top:${ny}px;width:${cw}px;height:${nh}px;transform:rotate(${(rng() - 0.5) * 2.4}deg)`,
          `${rng() < 0.5 ? `<b>${HF.esc((words.split(" ").slice(0, 3).join(" ") || "notes").toUpperCase())}</b>` : ""}${HF.esc(body.slice(0, 1500))}`, "pp-news");
      }
      el(pp, `left:0;top:0;width:${W}px;height:${H}px;opacity:.5;mix-blend-mode:multiply;` +
        `background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' seed='4'/><feColorMatrix values='0 0 0 0 .55 0 0 0 0 .47 0 0 0 0 .35 0 0 0 .45 0'/></filter><rect width='240' height='240' filter='url(%23n)'/></svg>")`);
      el(pp, `left:0;top:0;width:${W}px;height:${H}px;box-shadow:inset 0 0 ${Math.round(W / 6)}px rgba(90,60,25,.28)`);
      pp.dataset.decor = "1";                                               // texture, not evidence (precheck skips it)
      return pp;
    };

    // a cut-out object (transparent PNG) with a contact shadow and a slow, small bob; x, y = the object's top-left
    P.hero = (par, src, x = {}) => {
      const h = x.h || 700, w = x.w || null;
      const g = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;height:${h}px;${w ? `width:${w}px;` : ""}`);
      const sh = el(g, `left:12%;right:12%;bottom:-${Math.round(h * 0.03)}px;height:${Math.round(h * 0.06)}px;border-radius:50%;background:radial-gradient(ellipse, rgba(40,26,10,.45), rgba(40,26,10,0) 70%);filter:blur(4px)`);
      const im = document.createElement("img"); im.src = src; im.alt = "";
      im.style.cssText = `position:relative;display:block;height:${h}px;${w ? `width:${w}px;object-fit:contain;` : ""}filter:drop-shadow(0 ${Math.round(h * 0.03)}px ${Math.round(h * 0.03)}px rgba(40,26,10,.35))`;
      g.append(im);
      throwIn(g, x.at, x.from || "drop", x.rot || 0, x);
      const bob = x.bob != null ? x.bob : 6, ph = (x.at || 0) * 1.3;
      if (bob) K.onFrame((t) => { if (x.at == null || t >= x.at + 0.6) { im.style.transform = `translateY(${(bob * Math.sin(t * 1.4 + ph)).toFixed(2)}px) rotate(${(0.6 * Math.sin(t * 0.9 + ph)).toFixed(3)}deg)`;
        sh.style.transform = `scaleX(${(1 - 0.03 * Math.sin(t * 1.4 + ph)).toFixed(4)})`; } });
      return g;
    };

    // stamped caps: each line slams in (scale 1.25 -> 1, a hair of rotation), one line per `per` s or on given times
    P.stamp = (par, text, x = {}) => {
      const lines = text.split("|"), size = x.size || 120;
      const box = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;transform:rotate(${x.rot || 0}deg);transform-origin:0 0`);
      box.dataset.block = "1";                                              // its lines are one headline (precheck)
      lines.forEach((ln, i) => {
        const d = el(box, `left:0;top:${i * size * 1.02}px;font-size:${size}px;${x.color ? `color:${x.color};` : ""}`, "", "pp-stamp");
        ln.trim().split(/\s+/).forEach((w, j) => { const s = document.createElement("span"); s.textContent = w.replace(/^\*/, "") + " ";
          if (w[0] === "*") s.style.color = x.accent || RED; d.append(s); });
        const t = x.times ? x.times[i] : x.at != null ? x.at + i * (x.per || 0.35) : null;
        if (t != null) {
          d.style.opacity = 0;
          tl.fromTo(d, { opacity: 0, scale: 1.25, rotation: -2 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.16, ease: "power3.out", immediateRender: false }, Q(t));
          d.style.transformOrigin = "0 60%";
          K.sfx("impact/impact__short-bass-hit__mixkit-2299", t + 0.12, x.db != null ? x.db : -22);
        }
      });
      return box;
    };

    P.tape = (par, text, x = {}) => {
      const e = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;${x.size ? `font-size:${x.size}px;` : ""}`, HF.esc(text), "pp-tape");
      throwIn(e, x.at, x.from || "pop", x.rot != null ? x.rot : -4, { sfx: x.sfx, spring: "snappy" });
      return e;
    };

    P.polaroid = (par, src, x = {}) => {
      const w = x.w || 320;
      const e = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;width:${w}px`, "", "pp-pol");
      if (/^</.test(src)) el(e, `position:relative;height:${Math.round(w * 0.92)}px`, src, "pp-img"); else { const im = document.createElement("img"); im.src = src; im.style.height = Math.round(w * 0.92) + "px"; e.append(im); }
      if (x.caption) { const c = document.createElement("i"); c.textContent = x.caption; e.append(c); }
      throwIn(e, x.at, x.from || "right", x.rot != null ? x.rot : 5, x);
      return e;
    };

    P.ticket = (par, x = {}) => {
      const e = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;width:${x.w || 300}px`,
        `<b>${HF.esc(x.title || "")}</b><strong>${HF.esc(x.value || "")}</strong>${x.sub ? `<span>${HF.esc(x.sub)}</span>` : ""}`, "pp-ticket");
      throwIn(e, x.at, x.from || "drop", x.rot != null ? x.rot : 4, x);
      return e;
    };

    P.tag = (par, text, x = {}) => {
      const e = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;${x.color ? `background:${x.color};` : ""}${x.size ? `font-size:${x.size}px;` : ""}`, HF.esc(text), "pp-tag");
      throwIn(e, x.at, x.from || "pop", x.rot != null ? x.rot : -6, x);
      return e;
    };

    P.clipping = (par, x = {}) => {
      const e = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;width:${x.w || 420}px`, `<b>${HF.esc(x.title || "")}</b>${HF.esc(x.body || "")}`, "pp-clip");
      throwIn(e, x.at, x.from || "left", x.rot != null ? x.rot : -3, x);
      return e;
    };

    // graph paper + hand-drawn axes + a line that draws itself; points get dots; values are only what he said or showed
    P.chart = (par, x = {}) => {
      const W = x.w || 640, H = x.h || 440, vals = x.values || [], n = vals.length;
      const e = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;width:${W}px;height:${H}px;background:#f6f1e4;box-shadow:0 14px 28px rgba(30,20,10,.25);` +
        "background-image:linear-gradient(rgba(70,120,160,.18) 1px, transparent 1px),linear-gradient(90deg, rgba(70,120,160,.18) 1px, transparent 1px);background-size:32px 32px");
      const NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
      svg.setAttribute("width", W); svg.setAttribute("height", H); svg.style.cssText = "position:absolute;left:0;top:0;overflow:visible";
      e.append(svg);
      const pad = { l: 70, r: 40, t: x.title ? 90 : 40, b: 60 };
      const lo = Math.min(...vals, x.min != null ? x.min : Infinity), hi = Math.max(...vals);
      const px = (i) => pad.l + (n > 1 ? (i / (n - 1)) * (W - pad.l - pad.r) : 0), py = (v) => H - pad.b - ((v - lo) / Math.max(1e-9, hi - lo)) * (H - pad.t - pad.b);
      const path = (d, sw, col) => { const p = document.createElementNS(NS, "path"); p.setAttribute("d", d); p.setAttribute("fill", "none"); p.setAttribute("stroke", col); p.setAttribute("stroke-width", sw); p.setAttribute("stroke-linecap", "round"); p.setAttribute("stroke-linejoin", "round"); svg.append(p); return p; };
      const axes = path(`M${pad.l} ${pad.t - 10} L${pad.l - 2} ${H - pad.b + 2} L${W - pad.r + 10} ${H - pad.b - 1}`, 4, "#2a2620");
      const line = path(vals.map((v, i) => `${i ? "L" : "M"}${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(" "), 6, x.color || RED);
      if (x.title) el(e, `left:${pad.l - 10}px;top:22px`, HF.esc(x.title), "pp-tag").style.cssText += ";font-size:34px;transform:rotate(-2deg)";
      (x.labels || []).forEach((lb, i) => { if (lb) el(e, `left:${px(i) - 60}px;top:${H - pad.b + 12}px;width:120px;text-align:center;font:400 30px/1 Caveat,cursive;color:#2a2620`, HF.esc(lb)); });
      const at = x.at, dur = x.dur || 1.2;
      if (at != null) {
        throwIn(e, at, x.from || "rise", x.rot || 0, { sfx: null });
        [axes, line].forEach((p, k) => { const L = p.getTotalLength ? p.getTotalLength() : 2000; p.style.strokeDasharray = L;
          tl.fromTo(p, { strokeDashoffset: L }, { strokeDashoffset: 0, duration: k ? dur : 0.4, ease: k ? "power1.inOut" : "power2.out", immediateRender: true }, Q(at + 0.25 + (k ? 0.35 : 0))); });
        vals.forEach((v, i) => { const c = el(e, `left:${px(i) - 9}px;top:${py(v) - 9}px;width:18px;height:18px;border-radius:50%;background:${x.color || RED};border:3px solid #f6f1e4`);
          tl.fromTo(c, { scale: 0 }, { scale: 1, duration: 0.2, ease: "back.out(2)", immediateRender: true }, Q(at + 0.6 + (n > 1 ? (i / (n - 1)) * dur : 0))); });
        K.sfx("whoosh/whoosh__technology-transition-slide__mixkit-3120", at + 0.6 + dur * 0.5, -26);
      }
      e.point = (i) => ({ x: (x.x || 0) + px(i), y: (x.y || 0) + py(vals[i]) });
      return e;
    };

    P.phone = (par, src, x = {}) => {
      const h = x.h || 640, w = Math.round(h * 0.49);
      const e = el(par, `left:${x.x || 0}px;top:${x.y || 0}px;width:${w}px;height:${h}px`, `<div class="scr">${/^</.test(src) ? src : `<img src="${src}" style="width:100%;height:100%;object-fit:cover">`}</div>`, "pp-phone");
      throwIn(e, x.at, x.from || "rise", x.rot != null ? x.rot : -3, x);
      return e;
    };

    // red marker strokes (circle, underline, arrow, handwritten note) on HF.annotate
    P.ink = (par, box = {}) => {
      if (!HF.annotate) throw new Error("P.ink needs kit/hf/annotate.js");
      return HF.annotate(K, par, Object.assign({ x: 0, y: 0, w: K.width, h: K.height, color: RED }, box));
    };
    return P;
  };
})(window);
