/* kit/hf/diagram.js — the living diagram: one diagram that develops across passages (needs core.js).
 *
 *   const dg = HF.diagram(K, layer, { title: "My whole workflow", layout: "row",
 *     nodes: [{ id: "rec", label: "Record", sub: "one take", icon: "cam" }, ...], edges: [["rec", "clean"], ...] });
 *   dg.show(a1, b1); dg.show(a2, b2);             // visible windows; its state carries over between them
 *   dg.reveal("rec", t)  dg.connect("rec", "clean", t)  dg.focus("clean", t)  dg.overview(t)
 *   dg.flow("rec", "clean", t, { dur: 1.2, dots: 3 })  dg.done("rec", t)  dg.note("clean", t, "skill file", until)
 *
 * Nodes are placed in a world (layout "row" | "column" | "grid", or explicit x/y); the camera (focus/overview) and the
 * flowing dots are pure functions of time (K.onFrame), node and edge reveals are timeline tweens. Works in 16:9 and
 * 9:16 (use layout "column" for vertical).
 *
 * Styles (o.style; o.shape is the old name and still wins when given): "circle" (an icon disc, the default) | "card" |
 * "flat" (2026-10-22, kit v11; the default on the whitespace look, kit/refs/DIAGRAMS.md). Flat is diagram-design's
 * rules (cathrynlavery/diagram-design 2.6, MIT: kit/hf/lib/diagram-design.LICENSE) at video scale: hairline boxes on a
 * 4 px grid, mono type tags, one focal node in the accent, straight or right-angle connectors that never share a port,
 * a loop's way back dashed under the row with its meaning written on it:
 *   const dg = HF.diagram(K, layer, { style: "flat", title: "the loop", type: "loop",
 *     nodes: [{ id: "build", label: "Build", sub: "HTML + GSAP", mono: true }, { id: "draft", label: "Draft" },
 *             { id: "critic", label: "Critic", sub: "checks every frame", focal: true }],
 *     edges: [["build", "draft"], ["draft", "critic"], { from: "critic", to: "build", label: "fix what broke", accent: true }] });
 *   node fields: { id, label, sub, mono (sub in mono), tag ("01".. by default in a row or column; steps: false for none),
 *     focal (the accent; at most 2), kind: "input" | "external" (a sunk grey box) | "optional" (a dashed hairline) }
 *   edges: [from, to] or { from, to, route: "straight" | "z" | "L" | "under" | "over", dash, label (<= 14 characters,
 *     mono caps on a paper mask), accent }; in a row the next node is straight, a way back runs under, a skip over
 *   layout: "row" | "column" (9:16) | "hub" (o.hub: the node the others fan out of / into) | "grid" | explicit x/y
 *   dg.flow keeps ONE token per diagram, cycling its edge (or a chain: dg.flow([[a, b], [b, c], [c, a]], t)) every 3 s+;
 *   dg.highlight makes a node focal for a while (no ring); dg.done swaps its tag for a check; budgets warn in the console.
 * Old pages are untouched: circle and card draw exactly as before unless a page opts in to the two v11 fixes:
 *   margin: px (the boxes stay inside it; `pad` placed only their centres) and ports: "fan" (an edge and its reverse
 *   leave 16 px apart instead of from one point). C.takeover's diagram kind opts in. Every diagram publishes its geometry
 *   to window.__diagrams ([{ style, gate, nodes: [{ id, x, y, w, h }], edges: [{ from, to, pts, lab }], show }], the
 *   view's px); HF.diagram.verify(entry) is the geometry gate (ported from diagram-design's verify-geometry.py, MIT,
 *   thresholds x2.75 for 1080p) and HF.diagram.layout(o, w, h) the flat layout, both pure.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/diagram.js needs core.js first");
  const C = HF.C, NS = "http://www.w3.org/2000/svg";

  HF.diagram = function (K, parent, o) {
    const style = HF.diagram.styleOf(o);
    if (style === "flat") return flat(K, parent, o);
    const tl = K.tl, Q = K.Q;
    const vx = o.x || 0, vy = o.y || 0, vw = o.w || K.width, vh = o.h || K.height;
    const view = K.el(parent, `left:${vx}px;top:${vy}px;width:${vw}px;height:${vh}px;overflow:hidden`);
    const world = K.el(view, `left:0;top:0;width:${vw}px;height:${vh}px;transform-origin:0 0`);
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("width", vw); svg.setAttribute("height", vh); svg.style.cssText = "position:absolute;left:0;top:0;overflow:visible";
    world.append(svg);
    const shape = style, R = shape === "circle" ? 60 : 0, CW = o.cardW || 300, CH = o.cardH || 120;
    // ---- layout (world coordinates = viewport pixels at zoom 1)
    // o.margin (v11, opt-in): `pad` places the node CENTRES, so a card row sat 38 px from the frame edge (the research
    // still, 2026-10-22); with a margin the boxes themselves stay inside it (a circle's box is its 260 px label column)
    const N = o.nodes.length, pad = o.pad != null ? o.pad : 0.12, MG = o.margin;
    const hw = shape === "circle" ? 130 : CW / 2, hTop = shape === "circle" ? 60 : CH / 2, hBot = shape === "circle" ? 200 : CH / 2;
    const along = (L, lo, hi, k, n) => lo + (L - lo - hi) * (n === 1 ? 0.5 : k / (n - 1));
    o.nodes.forEach((n, i) => {
      if (n.x != null && n.y != null) return;
      if ((o.layout || "row") === "row") { n.x = MG != null ? along(vw, MG + hw, MG + hw, i, N) : vw * pad + (vw * (1 - 2 * pad) * (N === 1 ? 0.5 : i / (N - 1))); n.y = vh * (o.rowY || 0.47); }
      else if (o.layout === "column") { n.x = vw / 2; n.y = MG != null ? along(vh, MG + hTop, MG + hBot, i, N) : vh * pad + (vh * (1 - 2 * pad) * (N === 1 ? 0.5 : i / (N - 1))); }
      else { const cols = o.cols || Math.ceil(Math.sqrt(N)), r = Math.floor(i / cols), c = i % cols, rows = Math.ceil(N / cols);
        n.x = MG != null ? along(vw, MG + hw, MG + hw, c, cols) : vw * pad + (vw * (1 - 2 * pad)) * (cols === 1 ? 0.5 : c / (cols - 1)); n.y = vh * 0.25 + (vh * 0.55) * (rows === 1 ? 0.5 : r / (rows - 1)); }
    });
    const byId = {};
    const kick = (n, i) => (n.kicker != null ? n.kicker : o.steps === false ? "" : "Step " + (i + 1));   // the small label above a node
    o.nodes.forEach((n, i) => {
      byId[n.id] = n;
      const box = K.el(world, `left:${n.x - (shape === "circle" ? 130 : CW / 2)}px;top:${n.y - (shape === "circle" ? 60 : CH / 2)}px;width:${shape === "circle" ? 260 : CW}px;text-align:center;opacity:0`);
      if (shape === "circle") {
        box.innerHTML = `<div class="ic" style="position:relative;margin:0 auto;width:120px;height:120px;border-radius:50%;background:${C.card};box-shadow:${C.shadowSoft};display:flex;align-items:center;justify-content:center">` +
          `<span class="i1" style="display:flex">${HF.icon(n.icon || "spark", 50, C.acc, 2.2)}</span><span class="i2" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;border-radius:50%;background:${C.okTint}">${HF.icon("check", 52, C.ok, 2.6)}</span>` +
          `<span class="ring" style="position:absolute;inset:-10px;border-radius:50%;border:4px solid ${C.acc};opacity:0"></span></div>` +
          (kick(n, i) ? `<div class="hf-lbl" style="margin-top:24px;font-size:16px;color:${C.mute}">${HF.esc(kick(n, i))}</div>` : "") +
          `<div class="hf-serif" style="margin-top:8px;font-size:${o.labelSize || 54}px">${HF.esc(n.label)}</div>` +
          (n.sub ? `<div style="margin-top:8px;font:500 21px ${HF.F.body};color:${C.ink2};white-space:nowrap">${HF.esc(n.sub)}</div>` : "");
      } else {
        box.className = "hf-abs hf-card"; box.style.height = CH + "px"; box.style.textAlign = "left";
        box.innerHTML = `<div style="display:flex;align-items:center;gap:20px;height:100%;padding:0 26px"><div class="ic" style="position:relative;width:64px;height:64px;border-radius:18px;background:${C.accTint};display:flex;align-items:center;justify-content:center;flex:none">` +
          `<span class="i1" style="display:flex">${HF.icon(n.icon || "spark", 36, C.acc, 2.2)}</span><span class="i2" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;border-radius:18px;background:${C.okTint}">${HF.icon("check", 36, C.ok, 2.6)}</span></div>` +
          `<div><div class="hf-serif" style="font-size:42px">${HF.esc(n.label)}</div>${n.sub ? `<div style="margin-top:4px;font:500 20px ${HF.F.body};color:${C.ink2}">${HF.esc(n.sub)}</div>` : ""}</div></div>` +
          `<span class="ring" style="position:absolute;inset:-8px;border-radius:32px;border:4px solid ${C.acc};opacity:0"></span>`;
      }
      n.el = box;
    });
    // ---- edges
    const edges = {};
    const anchor = (a, b) => {
      const dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
      if (shape === "circle") return [a.x + (dx / d) * (R + 22), a.y + (dy / d) * (R + 22)];
      return Math.abs(dx) * CH > Math.abs(dy) * CW ? [a.x + Math.sign(dx) * (CW / 2 + 16), a.y] : [a.x, a.y + Math.sign(dy) * (CH / 2 + 16)];
    };
    // o.ports "fan" (v11, opt-in): an edge and its reverse (check -> edit -> check) both anchored on the line between
    // the two centres, so the way back started on the way there's start point (the research still dd_01, 2026-10-22).
    // Fanned, the pair splits 32 px apart: a curved one moves 16 px toward its own bulge and its straight partner the
    // other way (moved to their own left instead, the curve started under the line and arced across it: the fixture,
    // 2026-10-22); two straight ones (or two curves) each move to their own right, which is opposite sides
    const keyOf = (e) => (Array.isArray(e) ? e[0] + ">" + e[1] : e.from + ">" + e.to), keys = new Set((o.edges || []).map(keyOf));
    const bendOf = {};
    (o.edges || []).forEach((e) => { bendOf[keyOf(e)] = (Array.isArray(e) ? e[2] : e.curve) || 0; });
    const pub = { style: shape, gate: false, nodes: o.nodes.map((n) => ({ id: n.id, x: n.x - hw, y: n.y - hTop, w: 2 * hw, h: hTop + hBot })), edges: [], show: [] };
    (o.edges || []).forEach((e) => {
      const [f, t] = Array.isArray(e) ? e : [e.from, e.to], A = byId[f], B = byId[t];
      if (!A || !B) throw new Error("HF.diagram: edge " + f + " -> " + t + " has an unknown node");
      let p0 = anchor(A, B), p1 = anchor(B, A);
      const bend = (Array.isArray(e) ? e[2] : e.curve) || 0;
      if (o.ports === "fan" && keys.has(t + ">" + f)) {
        // n: the side a positive bend bulges to (the quadratic's control point moves along (-dy, dx) for this direction)
        const back = bendOf[t + ">" + f], s = Math.sign(bend || back || 1), dx = B.x - A.x, dy = B.y - A.y, d = Math.hypot(dx, dy) || 1;
        const ox = (-dy / d) * 16 * s, oy = (dx / d) * 16 * s;
        p0 = [p0[0] + ox, p0[1] + oy]; p1 = [p1[0] + ox, p1[1] + oy];
      }
      pub.edges.push({ from: f, to: t, pts: [p0, p1], curve: bend });
      const mx = (p0[0] + p1[0]) / 2 - (p1[1] - p0[1]) * bend, my = (p0[1] + p1[1]) / 2 + (p1[0] - p0[0]) * bend;
      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", `M${p0[0]} ${p0[1]} Q${mx} ${my} ${p1[0]} ${p1[1]}`);
      path.setAttribute("fill", "none"); path.setAttribute("stroke", C.ink); path.setAttribute("stroke-opacity", "0.28");
      path.setAttribute("stroke-width", "4"); path.setAttribute("stroke-linecap", "round");
      svg.append(path);
      const len = path.getTotalLength();
      path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
      const head = document.createElementNS(NS, "path");
      const ang = Math.atan2(p1[1] - my, p1[0] - mx), hx = p1[0], hy = p1[1], s = 14;
      head.setAttribute("d", `M${hx - s * Math.cos(ang - 0.5)} ${hy - s * Math.sin(ang - 0.5)} L${hx} ${hy} L${hx - s * Math.cos(ang + 0.5)} ${hy - s * Math.sin(ang + 0.5)}`);
      head.setAttribute("fill", "none"); head.setAttribute("stroke", C.ink); head.setAttribute("stroke-opacity", "0.28"); head.setAttribute("stroke-width", "4");
      head.setAttribute("stroke-linecap", "round"); head.setAttribute("stroke-linejoin", "round"); head.style.opacity = 0;
      svg.append(head);
      edges[f + ">" + t] = { path, head, len };
    });
    const title = o.title ? K.el(view, `left:0;width:${vw}px;top:${o.titleY || vh * 0.17}px;text-align:center;opacity:0`, HF.esc(o.title), "hf-lbl hf-abs") : null;
    // ---- camera (pure function of time)
    const cams = [];
    const cam = { cx: vw / 2, cy: vh / 2, z: 1 };
    let camAt = null;
    K.onFrame((t) => {
      if (!camAt) camAt = HF.keyed(cams, cam, { log: ["z", "scale", "s"] });
      const c = camAt(t);
      world.style.transform = `translate(${(vw / 2 - c.cx * c.z).toFixed(2)}px, ${(vh / 2 - c.cy * c.z).toFixed(2)}px) scale(${c.z.toFixed(4)})`;
    });
    const flows = [];
    K.onFrame((t) => {
      for (const f of flows) {
        f.dots.forEach((d, k) => {
          const p = (t - f.t) / f.dur - k * f.gap;
          const on = p > 0 && p < 1;
          d.setAttribute("opacity", on ? Math.min(1, Math.min(p, 1 - p) * 8).toFixed(3) : "0");
          if (on) { const q = f.path.getPointAtLength(p * f.len); d.setAttribute("cx", q.x.toFixed(2)); d.setAttribute("cy", q.y.toFixed(2)); }
        });
      }
    });
    const ids = (x) => (Array.isArray(x) ? x : [x]);
    const dg = { nodes: byId, view, world };
    // show() may be called several times: later windows must not re-hide at 0
    let shown = false;
    view.style.transformOrigin = "50% 50%";
    dg.show = (a, b) => {
      if (!shown) { tl.set(view, { autoAlpha: 0 }, 0); shown = true; }
      tl.set(view, { autoAlpha: 1 }, Q(a)); if (b != null) tl.set(view, { autoAlpha: 0 }, Q(b));
      if (title) K.fade(title, a, 0.3);
      if (b != null && o.drift !== false) K.drift(view, a, b, 1.03);         // a slow push while it's up: never a still
      pub.show.push([a, b == null ? null : b]);
      return dg;
    };
    publish(pub, vx, vy, vw, vh, o);
    dg.reveal = (x, t, stagger = 0.14) => { ids(x).forEach((id, k) => { K.enter(byId[id].el, t + k * stagger, { y: 30 }); }); K.sfx("click", t); return dg; };
    dg.connect = (f, to, t, dur = 0.5) => {
      const e = edges[f + ">" + to]; if (!e) throw new Error("HF.diagram: no edge " + f + " -> " + to);
      tl.fromTo(e.path, { strokeDashoffset: e.len }, { strokeDashoffset: 0, duration: dur, ease: "power2.inOut" }, Q(t));
      tl.to(e.head, { opacity: 1, duration: 0.15 }, Q(t + dur - 0.1));
      return dg;
    };
    dg.connectAll = (t, dur = 0.5, stagger = 0.15) => { Object.keys(edges).forEach((k, i) => { const [f, to] = k.split(">"); dg.connect(f, to, t + i * stagger, dur); }); return dg; };
    dg.focus = (x, t, opt = {}) => {
      const ns = ids(x).map((id) => byId[id]);
      const bw = shape === "circle" ? 300 : CW + 60, bh = shape === "circle" ? 360 : CH + 80;
      const x0 = Math.min(...ns.map((n) => n.x)) - bw / 2, x1 = Math.max(...ns.map((n) => n.x)) + bw / 2;
      const y0 = Math.min(...ns.map((n) => n.y)) - bh / 3, y1 = Math.max(...ns.map((n) => n.y)) + (bh * 2) / 3;
      const z = Math.min(opt.zoom || 1.7, vw / (x1 - x0), vh / (y1 - y0));
      cams.push({ t, dur: opt.dur || 0.8, ease: opt.ease || "power3.inOut", v: { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, z } }); camAt = null;
      o.nodes.forEach((n) => tl.to(n.el, { opacity: ns.includes(n) ? 1 : (opt.dim != null ? opt.dim : 0.3), duration: 0.4 }, Q(t)));
      if (title) tl.to(title, { opacity: 0, duration: 0.3 }, Q(t));
      return dg;
    };
    dg.overview = (t, opt = {}) => {
      cams.push({ t, dur: opt.dur || 0.8, ease: opt.ease || "power3.inOut", v: { cx: vw / 2, cy: vh / 2, z: 1 } }); camAt = null;
      o.nodes.forEach((n) => tl.to(n.el, { opacity: 1, duration: 0.4 }, Q(t)));
      if (title) tl.to(title, { opacity: 1, duration: 0.3 }, Q(t + 0.3));
      return dg;
    };
    dg.done = (x, t, stagger = 0.12) => { ids(x).forEach((id, k) => { const e = byId[id].el; tl.to(e.querySelector(".i2"), { opacity: 1, duration: 0.3 }, Q(t + k * stagger)); tl.fromTo(e.querySelector(".ic"), { scale: 1 }, { scale: 1.08, duration: 0.15, yoyo: true, repeat: 1 }, Q(t + k * stagger)); }); K.sfx("check", t); return dg; };
    dg.highlight = (id, t, until) => { const r = byId[id].el.querySelector(".ring"); tl.fromTo(r, { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 0.3, ease: "power3.out" }, Q(t)); if (until != null) tl.to(r, { opacity: 0, duration: 0.3 }, Q(until)); return dg; };
    dg.note = (id, t, text, until) => {
      const n = byId[id], nt = K.el(world, `left:${n.x - 200}px;top:${n.y + (shape === "circle" ? 220 : CH / 2 + 24)}px;width:400px;display:flex;justify-content:center;opacity:0`,
        `<span class="hf-pill" style="position:relative;font-size:22px;padding:10px 18px;background:${C.ink};color:${C.paper}">${HF.esc(text)}</span>`);
      K.enter(nt, t, { y: 12 }); if (until != null) K.exit(nt, until);
      return dg;
    };
    dg.flow = (f, to, t, opt = {}) => {
      const e = edges[f + ">" + to]; if (!e) throw new Error("HF.diagram: no edge " + f + " -> " + to);
      const n = opt.dots || 3, dots = [];
      for (let k = 0; k < n; k++) { const d = document.createElementNS(NS, "circle"); d.setAttribute("r", opt.r || 9); d.setAttribute("fill", opt.color || C.acc); d.setAttribute("opacity", "0"); svg.append(d); dots.push(d); }
      flows.push({ path: e.path, len: e.len, t, dur: opt.dur || 1.0, gap: opt.gap || 0.18, dots });
      return dg;
    };
    return dg;
  };
  // the style a call draws: its own style or shape, else flat on the whitespace look (the white page's diagram) and the
  // icon circles everywhere else, so a page built before v11 (no style, never whitespace) draws what it drew
  HF.diagram.styleOf = (o = {}) => o.style || o.shape || (HF.LOOK && HF.LOOK.name === "whitespace" ? "flat" : "circle");

  // ================================================================== shared: what a page publishes, budgets over time
  // window.__diagrams: each diagram's geometry in its view's px (frame: where the view sits in its parent), for QA's
  // geometry gate (HF.diagram.verify). gate: true on flat, whose connectors are straight or right-angled by rule;
  // circle and card draw curves by design, so their entries carry only each edge's two end points.
  let SEQ = 0;
  const publish = (pub, x, y, w, h, o) => {
    Object.assign(pub, { id: o.id || "dg" + SEQ++, type: o.type || null, frame: { x, y, w, h } });
    (root.__diagrams = root.__diagrams || []).push(pub);
    return pub;
  };
  // the most spans [a, b) open at one moment (b null: to the end): items entering in one step, edges drawing at once,
  // focal nodes, notes on screen
  const most = (spans) => {
    const ev = [];
    spans.forEach(([a, b]) => { ev.push([a, 1]); if (b != null) ev.push([b, -1]); });
    ev.sort((p, q) => p[0] - q[0] || p[1] - q[1]);
    let n = 0, m = 0;
    ev.forEach(([, d]) => { n += d; m = Math.max(m, n); });
    return m;
  };
  // how many items enter within one step (diagram-design's motion step, 0.48 s): at most 2 read as one beat
  HF.diagram.steps = (times, step = 0.48) => most(times.map((t) => [t, t + step - 1e-6]));

  // ================================================================== the flat style: geometry (pure, no DOM)
  // diagram-design's rules (cathrynlavery/diagram-design 2.6, MIT) re-drawn for a 1080p frame on the whitespace look:
  // the research prototype (2026-10-22) scaled its presentation ramp x2.75 and the whitespace type limits (3 sizes, body
  // >= 32 px, the mono kicker 26-28 px) set the rest. 4 px grid; boxes >= 176 tall, >= 112 apart, radius 18, a 2 px
  // hairline; connectors leave and enter perpendicular, >= 22 px from a corner, never two on one point (L k / (n + 1)
  // along a side), never through a box that isn't one of their ends; elbows r 20; labels <= 14 characters, 10 px off
  // their stroke on a paper mask. Budgets: 5 nodes on 16:9 (4 on 9:16), 6 edges, 2 focal nodes.
  const FLAT = { margin: 120, marginY: 96, gap: 112, minGap: 64, minH: 176, r: 18, elbow: 20, so: 12, head: 14, lane: 96, laneStep: 72,
    corner: 22, port: 32, labelOff: 10, labelMax: 14, nodes: 5, nodesP: 4, edges: 6, focal: 2, step: 0.48, period: 3 };
  HF.diagram.FLAT = FLAT;
  // text widths before the fonts load (no layout is measured before the fonts load: the page must lay out the same on
  // every render). Inter 600 by character class, measured in Chrome on 2026-10-22 ("Main agent" 249 px at 48 px, this
  // says 260); JetBrains Mono advances 0.6 em, plus its tracking
  const EMW = (ch) => (/[ijlI.,:;'!|()[\] ]/.test(ch) ? 0.3 : /[frt/-]/.test(ch) ? 0.38 : /[mwMW]/.test(ch) ? 0.86 : /[A-Z]/.test(ch) ? 0.68 : /[0-9]/.test(ch) ? 0.6 : 0.54);
  const textW = (s, px, kind) => {
    s = String(s == null ? "" : s);
    if (kind === "mono") return s.length * px * 0.62;
    if (kind === "kick") return s.length * px * 0.74;
    let w = 0;
    for (const ch of s) w += EMW(ch);
    return w * px * 1.06;
  };
  HF.diagram.textW = textW;
  const c4 = (v) => Math.ceil(v / 4) * 4, r4 = (v) => Math.round(v / 4) * 4;
  // the layout: node boxes, each connector as a polyline between its two ports ON the box outlines (the drawing adds the
  // stand-off and the head), label boxes and the eyebrow, in the view's px. x.portrait (default: taller than wide) picks
  // the 9:16 sizes; x.warn(msg) hears the budget notes.
  const layout = (o, vw, vh, x = {}) => {
    if (!o.nodes || !o.nodes.length) throw new Error("HF.diagram: a diagram needs nodes");
    const P = x.portrait != null ? !!x.portrait : vh > vw, warn = x.warn || (() => {}), F = FLAT;
    // 9:16: four boxes and three 112 px gaps don't fit a Reel's 980 px safe band, so a portrait box carries its tag
    // inline (left of the name) and is >= 128 tall, 88 px apart (measured on the column fixture, 2026-10-22)
    const M = o.margin != null ? o.margin : F.margin, MY = o.marginY != null ? o.marginY : P ? 40 : F.marginY, GAP = o.gap != null ? o.gap : P ? 88 : F.gap;
    const inline = o.inlineTags != null ? !!o.inlineTags : P, minGap = P ? 56 : F.minGap;
    const KS = o.kickSize || (P ? 30 : 26), NZ = o.nameSize || (P ? 52 : 48), SZ = o.subSize || (P ? 34 : 32);
    const free = o.nodes.length > 0 && o.nodes.every((n) => n.x != null && n.y != null);
    const mode = free ? "free" : o.layout || (P ? "column" : "row");
    if (!["free", "row", "column", "hub", "grid"].includes(mode)) throw new Error("HF.diagram: unknown layout " + mode + " (row, column, hub, grid or x/y)");
    const chain = mode === "row" || mode === "column", numbered = o.steps !== false && chain;
    const nodes = o.nodes.map((n, i) => ({ id: n.id, i, label: n.label == null ? "" : String(n.label), sub: n.sub == null ? "" : String(n.sub), mono: !!n.mono,
      focal: !!n.focal, kind: n.kind || "", tag: n.tag != null && n.tag !== false ? String(n.tag) : numbered && n.tag !== false ? String(i + 1).padStart(2, "0") : "",
      cx0: n.x, cy0: n.y, w0: n.w, h0: n.h }));
    const byId = {};
    nodes.forEach((n) => { if (byId[n.id]) throw new Error("HF.diagram: two nodes are called " + n.id); byId[n.id] = n; });
    const seen = new Set();
    const edges = (o.edges || []).map((e, k) => {
      const d = Array.isArray(e) ? { from: e[0], to: e[1] } : e, A = byId[d.from], B = byId[d.to];
      if (!A || !B) throw new Error("HF.diagram: edge " + d.from + " -> " + d.to + " has an unknown node");
      if (A === B) throw new Error("HF.diagram: edge " + d.from + " -> " + d.to + " loops on itself (draw a loop as a row and its way back)");
      const key = d.from + ">" + d.to;
      if (seen.has(key)) throw new Error("HF.diagram: edge " + key + " is given twice");
      seen.add(key);
      return { k, key, from: d.from, to: d.to, A, B, route: d.route || "", dash: d.dash, optional: !!d.optional, label: d.label ? String(d.label) : "", accent: !!d.accent };
    });
    // ---- budgets (kit/refs/DIAGRAMS.md): what a viewer takes in during a 4-12 s takeover; over it, split into an overview
    // station and a detail station and let the camera move between them
    const maxN = P ? F.nodesP : F.nodes, nf = nodes.filter((n) => n.focal).length;
    if (nodes.length > maxN) warn(`${nodes.length} nodes (at most ${maxN} on ${P ? "9:16" : "16:9"}): split it into an overview station and a detail station`);
    if (edges.length > F.edges) warn(`${edges.length} edges (at most ${F.edges}): run the deletion test (can an arrow or a label go?)`);
    if (nf > F.focal) warn(`${nf} focal nodes (at most ${F.focal}; normally 1, the part he names)`);
    edges.forEach((e) => { if (e.label.length > F.labelMax) warn(`the edge label "${e.label}" has ${e.label.length} characters (at most ${F.labelMax})`); });
    // ---- the boxes: one size for all (an aligned grid), from the longest name or sub line. Stacked (16:9): the tag on
    // its own row at the top left, name and sub centred under it. Inline (9:16): tag, then name and sub left-aligned.
    // A sub line that doesn't fit a narrowed box wraps to two lines (the box grows); a name never wraps (said instead).
    const hasTag = nodes.some((n) => n.tag), hasSub = nodes.some((n) => n.sub), PAD = inline ? 28 : 40;
    const tagW = Math.max(0, ...nodes.map((n) => (n.tag ? c4(textW(n.tag, KS, "kick") + 22) : 0))), lead = inline ? (hasTag ? 24 + tagW + 20 : 32) : 0;
    const textMax = Math.max(0, ...nodes.map((n) => Math.max(textW(n.label, NZ), n.sub ? textW(n.sub, SZ, n.mono ? "mono" : "") : 0)));
    const need = inline ? lead + textMax + 32 : Math.max(textMax + 80, tagW + 80);
    let NW = o.nodeW || Math.max(P ? 440 : 280, c4(need)), NH = 0, nameTop = 0, subTop = 0, subLines = 1;
    const sizeH = () => {
      const area = inline ? NW - lead - 32 : NW - 48, longest = Math.max(0, ...nodes.map((n) => (n.sub ? textW(n.sub, SZ, n.mono ? "mono" : "") : 0)));
      subLines = longest > area ? 2 : 1;
      if (longest > 1.9 * area) warn(`a sub line needs ${Math.round(longest)} px in a ${NW} px box (two lines fit ${Math.round(1.9 * area)}): shorten it`);
      const content = NZ + (hasSub ? 18 + (subLines > 1 ? Math.round(SZ * 2.3) : SZ) : 0);
      NH = o.nodeH || Math.max(inline ? 128 : F.minH, c4((!inline && hasTag ? KS + 50 : PAD) + content + PAD));
      nameTop = !inline && hasTag ? KS + 50 : Math.round((NH - content) / 2);
      subTop = nameTop + NZ + 18;
    };
    sizeH();
    const lab = (e) => (e.label ? c4(textW(e.label, KS, "kick") + 20) : 0);
    // routes in a row or column: the next node straight, a way back under (a loop's return, dashed), a skip over
    if (chain) edges.forEach((e) => { if (!e.route) e.route = e.B.i === e.A.i + 1 ? "straight" : e.B.i < e.A.i ? "under" : "over"; });
    edges.forEach((e) => { if (e.dash == null) e.dash = e.optional || (chain && e.B.i < e.A.i); });
    // the gaps give first (down to 64 px), then the boxes; either is said, since names may then not fit
    const squeeze = (gaps, avail, size, what) => {
      const sum = () => gaps.reduce((s, g) => s + g, 0), N = nodes.length;
      if (N * size + sum() <= avail) return size;
      const before = sum(), room = gaps.reduce((s, g) => s + Math.max(0, g - minGap), 0), k = Math.min(1, (N * size + sum() - avail) / (room || 1));
      gaps.forEach((g, i) => { gaps[i] = Math.max(minGap, Math.floor((g - Math.max(0, g - minGap) * k) / 4) * 4); });
      warn(`${N} nodes need ${Math.round(N * size + before)} px ${what} (${Math.round(avail)} fit): the gaps narrow to ${Math.min(...gaps)} px (fewer nodes, shorter names or no sub lines keep the rule)`);
      if (N * size + sum() <= avail) return size;
      return Math.max(160, Math.floor((avail - sum()) / N / 4) * 4);
    };
    if (mode === "row") {
      const gaps = nodes.slice(1).map((_, i) => Math.max(GAP, ...edges.filter((e) => e.route === "straight" && Math.min(e.A.i, e.B.i) === i && Math.max(e.A.i, e.B.i) === i + 1).map((e) => c4(lab(e) + 48))));
      // too wide: first the sub lines wrap (the boxes narrow toward their longest name), then the gaps give, then the boxes
      const sumG = gaps.reduce((s, g) => s + g, 0);
      if (!o.nodeW && nodes.length * NW + sumG > vw - 2 * M) {
        const floorW = Math.max(240, c4(Math.max(...nodes.map((n) => textW(n.label, NZ))) + 64), tagW + 80);
        NW = Math.max(floorW, Math.floor((vw - 2 * M - sumG) / nodes.length / 4) * 4); sizeH();
      }
      const nw = squeeze(gaps, vw - 2 * M, NW, "across");
      if (nw < NW) {
        const wide = nodes.reduce((a, n) => (textW(n.label, NZ) > textW(a.label, NZ) ? n : a));
        if (textW(wide.label, NZ) > nw - 32) warn(`the boxes narrow to ${nw} px: "${wide.label}" needs ${c4(textW(wide.label, NZ) + 32)}`);
        NW = nw; sizeH();
      }
      let x0 = 0;
      nodes.forEach((n, i) => { Object.assign(n, { x: x0, y: 0, w: NW, h: NH }); x0 += NW + (gaps[i] || 0); });
    } else if (mode === "column") {
      const side = (r) => (edges.some((e) => e.route === r) ? F.lane + 8 + Math.max(0, ...edges.filter((e) => e.route === r && e.label).map((e) => lab(e) + F.labelOff)) : 0);
      const cap = Math.floor((vw - 2 * M - side("under") - side("over")) / 4) * 4;
      if (NW > cap) { warn(`the boxes narrow to ${cap} px to fit the column and its lanes (the names need ${NW})`); NW = cap; sizeH(); }
      const gaps = nodes.slice(1).map(() => GAP);
      squeeze(gaps, vh - 2 * MY - (o.title ? KS + 40 : 0), NH, "down");                 // the eyebrow sits over the column
      let y0 = 0;
      nodes.forEach((n, i) => { Object.assign(n, { x: 0, y: y0, w: NW, h: NH }); y0 += NH + (gaps[i] || 0); });
    } else if (mode === "hub") {
      // fan-out (the hub on the left) or fan-in (on the right): the spokes in a column, the connectors turning in the gap
      const hub = byId[o.hub] || nodes.find((n) => n.focal) || nodes[0], spokes = nodes.filter((n) => n !== hub);
      const into = edges.filter((e) => e.B === hub).length > edges.filter((e) => e.A === hub).length;
      const SG = o.spokeGap != null ? o.spokeGap : 48, HG = o.gap != null ? o.gap : Math.max(240, 96 + 40 * Math.ceil(spokes.length / 2) + 96);
      const cap = Math.floor((vw - 2 * M - HG) / 2 / 4) * 4;
      if (NW > cap) { warn(`the boxes narrow to ${cap} px to fit the hub and its spokes (the names need ${NW})`); NW = cap; sizeH(); }
      const colH = spokes.length * NH + (spokes.length - 1) * SG;
      if (colH > vh - 2 * MY) warn(`${spokes.length} spokes need ${colH} px down (${vh - 2 * MY} fit): fewer spokes or no sub lines`);
      Object.assign(hub, { x: into ? NW + HG : 0, y: r4((colH - NH) / 2), w: NW, h: NH });
      spokes.forEach((n, k) => Object.assign(n, { x: into ? 0 : NW + HG, y: k * (NH + SG), w: NW, h: NH }));
    } else if (mode === "grid") {
      const cols = o.cols || Math.ceil(Math.sqrt(nodes.length));
      nodes.forEach((n, i) => Object.assign(n, { x: (i % cols) * (NW + GAP), y: Math.floor(i / cols) * (NH + GAP), w: NW, h: NH }));
    } else {
      nodes.forEach((n) => { n.w = n.w0 || NW; n.h = n.h0 || NH; n.x = Math.round(n.cx0 - n.w / 2); n.y = Math.round(n.cy0 - n.h / 2); });
    }
    // ---- sides: a lane runs around the row (under: below a row, right of a column); the rest face each other
    const cx = (n) => n.x + n.w / 2, cy = (n) => n.y + n.h / 2, colm = mode === "column", LANE = colm ? { under: "r", over: "l" } : { under: "b", over: "t" };
    edges.forEach((e) => {
      const A = e.A, B = e.B;
      if (e.route === "under" || e.route === "over") { e.sides = [LANE[e.route], LANE[e.route]]; e.lane = true; return; }
      const gx = Math.max(B.x - (A.x + A.w), A.x - (B.x + B.w)), gy = Math.max(B.y - (A.y + A.h), A.y - (B.y + B.h));
      if (gx <= 0 && gy <= 0) throw new Error(`HF.diagram: the boxes of ${e.from} and ${e.to} overlap`);
      if (e.route === "L" && gx > 0 && gy > 0) { e.sides = [cx(B) > cx(A) ? "r" : "l", cy(B) > cy(A) ? "t" : "b"]; return; }
      if (e.route === "L") e.route = "";
      e.sides = gx >= gy ? (cx(B) > cx(A) ? ["r", "l"] : ["l", "r"]) : (cy(B) > cy(A) ? ["b", "t"] : ["t", "b"]);
    });
    // ---- ports: each side's connectors fanned at L k / (n + 1), ordered so that none crosses another
    const slots = new Map();
    edges.forEach((e) => e.sides.forEach((s, j) => { const n = j ? e.B : e.A, key = n.id + ":" + s; if (!slots.has(key)) slots.set(key, []); slots.get(key).push({ e, j, n, s }); }));
    slots.forEach((list) => {
      const { n, s } = list[0], hor = s === "t" || s === "b", L = hor ? n.w : n.h, oth = (a) => (a.j ? a.e.A : a.e.B), c = (m) => (hor ? cx(m) : cy(m));
      // lanes nest without crossing: first the ones that leave toward lower coordinates, the nearest first, then the ones
      // toward higher coordinates, the farthest first (an outer lane's leg stays outside an inner lane's run); facing
      // connectors in the order of their other ends
      const lk = (a) => [c(oth(a)) > c(n) ? 1 : 0, -c(oth(a))];
      list.sort((p, q) => {
        if (p.e.lane || q.e.lane) { const a = lk(p), b = lk(q); return a[0] - b[0] || a[1] - b[1] || p.e.k - q.e.k; }
        return c(oth(p)) - c(oth(q)) || p.e.k - q.e.k;
      });
      list.forEach((a, k) => Object.assign(a, { at: (L * (k + 1)) / (list.length + 1), of: list.length, L }));
      if (list.length > 1 && L / (list.length + 1) < F.port) warn(`${list.length} connectors on one side of "${n.label}" sit under ${F.port} px apart: spread them over two sides or drop one`);
      list.forEach((a) => { (a.e.ports = a.e.ports || [])[a.j] = a; });
    });
    // a side with one connector lines up with its other end when that end's port is on its straight part (straight
    // beats an elbow); otherwise it keeps its middle and the connector turns (sliding to a corner read as a mistake on
    // the hub fixture, 2026-10-22)
    const along = (a) => (a.s === "t" || a.s === "b" ? a.n.x : a.n.y), at = (a) => along(a) + a.at, put = (a, v) => { a.at = v - along(a); };
    const rng = (a) => [along(a) + F.corner, along(a) + a.L - F.corner], inR = (v, [lo, hi]) => v >= lo && v <= hi;
    edges.forEach((e) => {
      if (e.lane || e.route === "L") return;
      const [pa, pb] = e.ports;
      if (pa.of === 1 && pb.of === 1) {
        const ra = rng(pa), rb = rng(pb), lo = Math.max(ra[0], rb[0]), hi = Math.min(ra[1], rb[1]), mid = (at(pa) + at(pb)) / 2;
        if (lo <= hi) { const v = Math.max(lo, Math.min(hi, mid)); put(pa, v); put(pb, v); }
      } else if (pa.of === 1 && inR(at(pb), rng(pa))) put(pa, at(pb));
      else if (pb.of === 1 && inR(at(pa), rng(pb))) put(pb, at(pa));
    });
    const pt = (a) => { const n = a.n, v = Math.round(a.at); return a.s === "r" ? [n.x + n.w, n.y + v] : a.s === "l" ? [n.x, n.y + v] : a.s === "b" ? [n.x + v, n.y + n.h] : [n.x + v, n.y]; };
    // ---- lanes: a U past every box it spans, nested by length (the shortest innermost), 72 px apart
    const ax = colm ? 1 : 0;
    ["under", "over"].forEach((r) => {
      const ls = edges.filter((e) => e.lane && e.route === r).map((e) => { const p0 = pt(e.ports[0]), p1 = pt(e.ports[1]); return { e, p0, p1, lo: Math.min(p0[ax], p1[ax]), hi: Math.max(p0[ax], p1[ax]) }; });
      ls.sort((p, q) => p.hi - p.lo - (q.hi - q.lo) || p.e.k - q.e.k);
      const used = [];
      ls.forEach((l) => {
        let k = 0;
        while ((used[k] || []).some(([lo, hi]) => l.lo < hi + 24 && lo < l.hi + 24)) k++;
        (used[k] = used[k] || []).push([l.lo, l.hi]);
        const span = nodes.filter((n) => (colm ? n.y < l.hi && n.y + n.h > l.lo : n.x < l.hi && n.x + n.w > l.lo)), d = F.lane + F.laneStep * k;
        const c = colm ? (r === "under" ? Math.max(...span.map((n) => n.x + n.w)) + d : Math.min(...span.map((n) => n.x)) - d)
          : r === "under" ? Math.max(...span.map((n) => n.y + n.h)) + d : Math.min(...span.map((n) => n.y)) - d;
        l.e.pts = colm ? [l.p0, [c, l.p0[1]], [c, l.p1[1]], l.p1] : [l.p0, [l.p0[0], c], [l.p1[0], c], l.p1];
      });
    });
    // ---- the rest: straight when the ports line up, else an L (asked for) or a z that turns in the gap between the boxes
    const zs = [];
    edges.filter((e) => !e.lane).forEach((e) => {
      const p0 = pt(e.ports[0]), p1 = pt(e.ports[1]), h = e.sides[0] === "r" || e.sides[0] === "l";
      if (e.route === "L") { e.pts = [p0, [p1[0], p0[1]], p1]; return; }
      if (Math.abs(h ? p0[1] - p1[1] : p0[0] - p1[0]) < 1) { e.pts = h ? [p0, [p1[0], p0[1]]] : [p0, [p0[0], p1[1]]]; e.route = "straight"; return; }
      Object.assign(e, { route: "z", h, p0, p1 });
      zs.push(e);
    });
    // connectors fanning out of (or into) one side turn in order, the outermost first (nearest that side), 40 px apart
    // and centred in the gap, so no leg crosses another's run; a z alone turns half-way
    const groups = new Map();
    zs.forEach((e) => {
      e.sh = e.ports[0].of > 1 ? 0 : e.ports[1].of > 1 ? 1 : -1;
      if (e.sh < 0) return;
      const q = e.h ? 1 : 0, a = e.ports[e.sh], dir = Math.sign(e.sh ? e.p0[q] - e.p1[q] : e.p1[q] - e.p0[q]);
      e.gk = a.n.id + ":" + a.s + ":" + dir;
      if (!groups.has(e.gk)) groups.set(e.gk, []);
      groups.get(e.gk).push(e);
    });
    zs.forEach((e) => {
      const m0 = e.h ? 0 : 1, q = 1 - m0, a0 = e.p0[m0], a1 = e.p1[m0], gap = Math.abs(a1 - a0), dir = Math.sign(a1 - a0);
      let m = (a0 + a1) / 2;
      if (e.sh >= 0) {
        const g = groups.get(e.gk).slice().sort((p, r) => Math.abs(r.p1[q] - r.p0[q]) - Math.abs(p.p1[q] - p.p0[q]) || p.k - r.k);
        const off = gap / 2 - 20 * (g.length - 1) + 40 * g.indexOf(e);
        if (40 * (g.length - 1) <= gap - 80) m = (e.sh ? a1 : a0) + (e.sh ? -dir : dir) * off;
        else warn(`the connectors fanning from "${e.ports[e.sh].n.label}" need a ${40 * (g.length - 1) + 80} px gap (${Math.round(gap)} here)`);
      }
      m = Math.round(m);
      e.pts = e.h ? [e.p0, [m, e.p0[1]], [m, e.p1[1]], e.p1] : [e.p0, [e.p0[0], m], [e.p1[0], m], e.p1];
    });
    // ---- labels: on the connector's longest run, 10 px off the stroke, on the side toward the boxes for a lane
    edges.forEach((e) => {
      if (!e.label) return;
      const w = lab(e), h = KS + 12, S = e.pts.slice(1).map((p, i) => [e.pts[i], p]), len = ([a, b]) => Math.abs(b[0] - a[0]) + Math.abs(b[1] - a[1]);
      const hs = S.filter(([a, b]) => Math.abs(a[1] - b[1]) < 1).sort((p, q) => len(q) - len(p)), vs = S.filter(([a, b]) => Math.abs(a[0] - b[0]) < 1).sort((p, q) => len(q) - len(p));
      if (hs.length && !(colm && e.lane)) {
        const [a, b] = hs[0], y = a[1], below = e.lane && e.route === "over";
        e.lab = { x: Math.round((a[0] + b[0]) / 2 - w / 2), y: below ? y + F.labelOff : y - F.labelOff - h, w, h };
      } else if (vs.length) {
        const [a, b] = vs[0], left = e.lane && e.route === "over";
        e.lab = { x: left ? a[0] - F.labelOff - w : a[0] + F.labelOff, y: Math.round((a[1] + b[1]) / 2 - h / 2), w, h };
      }
    });
    // ---- the eyebrow (o.title): mono caps over the first box, its left edge on the grid's
    const title = o.title ? { text: String(o.title), w: c4(textW(o.title, KS, "kick")), h: KS } : null;
    const extent = () => {
      const xs = [], ys = [];
      nodes.forEach((n) => { xs.push(n.x, n.x + n.w); ys.push(n.y, n.y + n.h); });
      edges.forEach((e) => { e.pts.forEach((p) => { xs.push(p[0]); ys.push(p[1]); }); if (e.lab) { xs.push(e.lab.x, e.lab.x + e.lab.w); ys.push(e.lab.y, e.lab.y + e.lab.h); } });
      if (title && title.y != null) { xs.push(title.x, title.x + title.w); ys.push(title.y); }
      return { x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys) };
    };
    if (title) { const b = extent(); Object.assign(title, { x: Math.min(...nodes.map((n) => n.x)), y: b.y0 - 40 - KS }); }
    // ---- placed in the view on the 4 px grid: the boxes centred across (a lane and its label hang off to one side,
    // kept inside the margins; centring the whole block pushed a 9:16 column off-centre), the whole block centred down
    // (o.cy: where its middle sits, a share of the height)
    if (mode !== "free") {
      const b = extent(), nx0 = Math.min(...nodes.map((n) => n.x)), nx1 = Math.max(...nodes.map((n) => n.x + n.w));
      let ddx = vw / 2 - (nx0 + nx1) / 2;
      if (b.x1 + ddx > vw - M) ddx = vw - M - b.x1;
      if (b.x0 + ddx < M) ddx = M - b.x0;
      let dx = r4(ddx);
      if (b.x1 + dx > vw - M && b.x0 + dx - 4 >= M) dx -= 4;                     // the grid's rounding stays inside too
      else if (b.x0 + dx < M && b.x1 + dx + 4 <= vw - M) dx += 4;
      const dy = r4(vh * (o.cy != null ? o.cy : 0.5) - (b.y0 + b.y1) / 2);
      nodes.forEach((n) => { n.x += dx; n.y += dy; });
      edges.forEach((e) => { e.pts = e.pts.map((p) => [p[0] + dx, p[1] + dy]); if (e.lab) { e.lab.x += dx; e.lab.y += dy; } });
      if (title) { title.x += dx; title.y += dy; }
    }
    const b = extent();
    if (b.x0 < M - 0.5 || b.x1 > vw - M + 0.5) warn(`the diagram spans ${Math.round(b.x1 - b.x0)} px across, past the ${M} px margins (${vw - 2 * M} px fit)`);
    if (b.y0 < MY - 0.5 || b.y1 > vh - MY + 0.5) warn(`the diagram spans ${Math.round(b.y1 - b.y0)} px down, past the ${MY} px margins (${vh - 2 * MY} px fit)`);
    return { mode, portrait: P, size: { KS, NZ, SZ, NW, NH, nameTop, subTop, subLines, inline, lead }, title,
      nodes: nodes.map((n) => ({ id: n.id, i: n.i, x: n.x, y: n.y, w: n.w, h: n.h, label: n.label, sub: n.sub, mono: n.mono, tag: n.tag, focal: n.focal, kind: n.kind })),
      edges: edges.map((e) => ({ from: e.from, to: e.to, route: e.route, dash: !!e.dash, accent: e.accent, label: e.label, pts: e.pts.map((p) => [p[0], p[1]]), lab: e.lab || null, sides: e.sides })) };
  };
  HF.diagram.layout = (o, vw, vh, x) => layout(o, vw, vh, x);

  // ================================================================== the geometry gate (pure)
  // Ported from diagram-design's scripts/verify-geometry.py (cathrynlavery/diagram-design 2.6, MIT, (c) 2025 Cathryn
  // Lavery: kit/hf/lib/diagram-design.LICENSE), its thresholds x2.75 (its type ramp is a document's, ours a 1080p
  // frame): no diagonal segment; no run along a box's border; no endpoint within 22 px of a corner; no two ports on one
  // side under 32 px apart (22 on a side under 132 px); no two connectors within 3 px for more than 11 px. Stricter than
  // the original in three ways, for video: an arriving and a leaving port count as a pair too (a loop's way back that
  // lands on the way there's start point was HF.diagram's own bug, 2026-10-22); a connector through a box that isn't one
  // of its ends is reported; a label may not sit on a box, another label, or any line.
  // In: a window.__diagrams entry ({ nodes: [{ id, x, y, w, h }], edges: [{ from, to, pts, lab }] }). Out: one line a finding.
  const TOL = { axis: 0.5, border: 2.75, run: 11, port: 11, corner: 22, shared: 32, small: 22, smallSide: 132, stack: 2.75, step: 1 };
  HF.diagram.verify = (g, tol = {}) => {
    const T = Object.assign({}, TOL, tol), out = [], N = g.nodes || [], E = (g.edges || []).filter((e) => e.pts && e.pts.length > 1);
    const nm = (e) => `${e.from} -> ${e.to}`, nn = (n) => `"${n.id}"`;
    const segs = (e) => e.pts.slice(1).map((p, i) => [e.pts[i][0], e.pts[i][1], p[0], p[1]]);
    const attached = ([px, py], n) => Math.max(n.x - px, 0, px - n.x - n.w, n.y - py, py - n.y - n.h) <= T.port &&
      Math.min(px - n.x, n.x + n.w - px, py - n.y, n.y + n.h - py) <= T.port;
    const sideOf = ([px, py], n) => {
      const d = { t: Math.abs(py - n.y), b: Math.abs(py - n.y - n.h), l: Math.abs(px - n.x), r: Math.abs(px - n.x - n.w) };
      const s = ["t", "b", "l", "r"].reduce((a, b) => (d[b] < d[a] ? b : a));
      return [s, s === "t" || s === "b" ? px : py];
    };
    const ports = [];
    E.forEach((e, id) => {
      const S = segs(e);
      const dg = S.find(([x1, y1, x2, y2]) => Math.abs(x1 - x2) > T.axis && Math.abs(y1 - y2) > T.axis);
      if (dg) out.push(`${nm(e)}: a diagonal segment ${dg.map((v) => Math.round(v)).join(",")}: run it straight or with right-angle elbows`);
      let hit = null;
      for (const [x1, y1, x2, y2] of S) {
        for (const n of N) {
          const hz = Math.abs(y1 - y2) <= T.axis, vt = Math.abs(x1 - x2) <= T.axis;
          if (!hz && !vt) continue;
          const c = hz ? y1 : x1, lo = hz ? n.y : n.x, hi = hz ? n.y + n.h : n.x + n.w, r0 = hz ? n.x : n.y, r1 = hz ? n.x + n.w : n.y + n.h;
          const run = Math.min(Math.max(hz ? x1 : y1, hz ? x2 : y2), r1) - Math.max(Math.min(hz ? x1 : y1, hz ? x2 : y2), r0);
          if (run <= T.run) continue;
          if (Math.abs(c - lo) <= T.border || Math.abs(c - hi) <= T.border) { hit = `runs along the border of ${nn(n)}`; break; }
          if (n.id !== e.from && n.id !== e.to && c > lo && c < hi) { hit = `passes behind ${nn(n)}`; break; }
        }
        if (hit) break;
      }
      if (hit) out.push(`${nm(e)} ${hit}: route it around the box, each end perpendicular to its side`);
      const ends = [e.pts[0], e.pts[e.pts.length - 1]];
      let cornered = false;
      ends.forEach((p, j) => N.forEach((n, ni) => {
        if (!attached(p, n)) return;
        for (const kx of [n.x, n.x + n.w]) for (const ky of [n.y, n.y + n.h]) {
          const dd = Math.max(Math.abs(p[0] - kx), Math.abs(p[1] - ky));
          if (!cornered && dd < T.corner) { cornered = true; out.push(`${nm(e)} attaches ${Math.round(dd)} px from a corner of ${nn(n)} (at least ${T.corner}): move the port onto the straight part of the side`); }
        }
        ports.push({ ni, p, j, id, e });
      }));
    });
    for (let i = 0; i < ports.length; i++) for (let k = i + 1; k < ports.length; k++) {
      const a = ports[i], b = ports[k];
      if (a.ni !== b.ni || a.id === b.id) continue;
      const n = N[a.ni], [sa, va] = sideOf(a.p, n), [sb, vb] = sideOf(b.p, n);
      if (sa !== sb) continue;
      const min = (sa === "t" || sa === "b" ? n.w : n.h) < T.smallSide ? T.small : T.shared, gap = Math.abs(va - vb);
      if (gap < min) out.push(`${nm(b.e)} ${b.j ? "arrives" : "leaves"} ${Math.round(gap)} px from where ${nm(a.e)} ${a.j ? "arrives" : "leaves"} on one side of ${nn(n)} (at least ${min}): fan the ports`);
    }
    const near = (px, py, S2) => S2.some(([x1, y1, x2, y2]) => {
      const dx = x2 - x1, dy = y2 - y1, l2 = dx * dx + dy * dy, t = l2 ? Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / l2)) : 0;
      return Math.hypot(px - x1 - t * dx, py - y1 - t * dy) <= T.stack;
    });
    const shared = (A, B) => {                               // the longest continuous stretch of A drawn within 3 px of B
      const SB = segs(B), joints = [[A.pts[A.pts.length - 1], B.pts[0]], [A.pts[0], B.pts[B.pts.length - 1]]]
        .filter(([p, q]) => Math.hypot(p[0] - q[0], p[1] - q[1]) <= T.stack).map(([p]) => p);
      let best = 0, cur = 0;
      for (const [x1, y1, x2, y2] of segs(A)) {
        const n = Math.max(1, Math.ceil(Math.hypot(x2 - x1, y2 - y1) / T.step));
        for (let i = 0; i < n; i++) {
          const px = x1 + ((x2 - x1) * i) / n, py = y1 + ((y2 - y1) * i) / n;
          if (!joints.some((q) => Math.hypot(px - q[0], py - q[1]) < T.corner) && near(px, py, SB)) { cur++; best = Math.max(best, cur); } else cur = 0;
        }
      }
      return best * T.step;
    };
    for (let i = 0; i < E.length; i++) for (let k = i + 1; k < E.length; k++) {
      const s = Math.max(shared(E[i], E[k]), shared(E[k], E[i]));
      if (s > T.run) out.push(`${nm(E[k])} runs on top of ${nm(E[i])} for about ${Math.round(s)} px: move one route so each arrow stays traceable`);
    }
    const ov = (a, b) => Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x) > 1 && Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y) > 1;
    const crosses = ([x1, y1, x2, y2], r) => (Math.abs(y1 - y2) <= T.axis ? y1 > r.y && y1 < r.y + r.h && Math.min(Math.max(x1, x2), r.x + r.w) - Math.max(Math.min(x1, x2), r.x) > 1
      : Math.abs(x1 - x2) <= T.axis ? x1 > r.x && x1 < r.x + r.w && Math.min(Math.max(y1, y2), r.y + r.h) - Math.max(Math.min(y1, y2), r.y) > 1 : false);
    const L = E.filter((e) => e.lab);
    L.forEach((e, i) => {
      const n = N.find((m) => ov(e.lab, m));
      if (n) out.push(`the label of ${nm(e)} sits on ${nn(n)}: move it onto a free run of its connector`);
      L.slice(i + 1).forEach((f) => { if (ov(e.lab, f.lab)) out.push(`the labels of ${nm(e)} and ${nm(f)} overlap`); });
      E.forEach((f) => { if (segs(f).some((s) => crosses(s, e.lab))) out.push(`the label of ${nm(e)} covers the line of ${nm(f)}`); });
    });
    return out;
  };

  // ================================================================== the flat style: the page
  const rgba = (c, a) => { const m = /^#([0-9a-f]{6})$/i.exec(String(c).trim()); if (!m) return c; const v = parseInt(m[1], 16); return `rgba(${v >> 16},${(v >> 8) & 255},${v & 255},${a})`; };
  const svgEl = (tag, at) => { const e = document.createElementNS(NS, tag); Object.keys(at).forEach((k) => e.setAttribute(k, at[k])); return e; };
  const f1 = (v) => Math.round(v * 10) / 10;
  // a polyline as a path: its first segment starts a (the stand-off from the box), its last stops b short (room for the
  // head), each elbow rounded to r (or half the shorter neighbour)
  const pathD = (pts, a, b, r) => {
    const P = pts.map((p) => p.slice()), n = P.length - 1;
    const dir = (p, q) => { const dx = q[0] - p[0], dy = q[1] - p[1], d = Math.hypot(dx, dy) || 1; return [dx / d, dy / d]; };
    const d0 = dir(P[0], P[1]), d1 = dir(P[n - 1], P[n]);
    P[0] = [P[0][0] + d0[0] * a, P[0][1] + d0[1] * a]; P[n] = [P[n][0] - d1[0] * b, P[n][1] - d1[1] * b];
    let s = `M${f1(P[0][0])} ${f1(P[0][1])}`;
    for (let i = 1; i < n; i++) {
      const u = dir(P[i - 1], P[i]), v = dir(P[i], P[i + 1]);
      const k = Math.min(r, Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]) / 2, Math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]) / 2);
      s += ` L${f1(P[i][0] - u[0] * k)} ${f1(P[i][1] - u[1] * k)} Q${f1(P[i][0])} ${f1(P[i][1])} ${f1(P[i][0] + v[0] * k)} ${f1(P[i][1] + v[1] * k)}`;
    }
    return s + ` L${f1(P[n][0])} ${f1(P[n][1])}`;
  };
  HF.diagram.pathD = pathD;
  let MASKS = 0;
  const flat = (K, parent, o) => {
    const tl = K.tl, Q = K.Q, F = FLAT;
    const vx = o.x || 0, vy = o.y || 0, vw = o.w || K.width, vh = o.h || K.height;
    const said = new Set(), warn = (m) => { if (!said.has(m)) { said.add(m); console.warn("HF.diagram (flat): " + m); } };
    const g = layout(o, vw, vh, { portrait: o.portrait != null ? o.portrait : K.height > K.width, warn });
    HF.diagram.verify(g).forEach((m) => warn("geometry: " + m));          // said while building, not only at QA
    const { KS, NZ, SZ, nameTop, subTop, subLines, inline, lead } = g.size;
    const view = K.el(parent, `left:${vx}px;top:${vy}px;width:${vw}px;height:${vh}px;overflow:hidden`);
    const world = K.el(view, `left:0;top:0;width:${vw}px;height:${vh}px;transform-origin:0 0`);
    const svg = svgEl("svg", { width: vw, height: vh });
    svg.style.cssText = "position:absolute;left:0;top:0;overflow:visible";
    world.append(svg);
    const HAIR = rgba(C.ink, 0.16), TAG = rgba(C.ink, 0.22), MASK = o.mask || C.paper, mono = HF.F.mono, body = HF.F.body;
    // ---- connectors first, then their labels, then the boxes (diagram-design's paint order: a box never has a line on
    // its face; a label that strays under a box is what verify() reports)
    const edges = {};
    g.edges.forEach((e) => {
      const col = e.accent ? C.acc : C.ink, path = svgEl("path", { d: pathD(e.pts, F.so, F.so + F.head - 2, F.elbow), fill: "none", stroke: col,
        "stroke-opacity": e.accent ? 1 : 0.45, "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round" });
      svg.append(path);
      const len = path.getTotalLength();
      let draw = path;
      if (e.dash) {
        // a dashed line draws on through a mask (its own dash array is the dashes): a solid white copy that grows along it
        // (user-space units: a straight dashed line has a zero-height box, and a box-relative mask would hide it all)
        path.setAttribute("stroke-dasharray", "12 10");
        const id = "dgm" + MASKS++, m = svgEl("mask", { id, maskUnits: "userSpaceOnUse", x: -vw, y: -vh, width: 3 * vw, height: 3 * vh });
        draw = svgEl("path", { d: path.getAttribute("d"), fill: "none", stroke: "#fff", "stroke-width": 9, "stroke-linecap": "round", "stroke-linejoin": "round" });
        m.append(draw); svg.prepend(m); path.setAttribute("mask", `url(#${id})`);
      }
      draw.style.strokeDasharray = `${len} ${len}`; draw.style.strokeDashoffset = len;
      const P = e.pts, n = P.length - 1, dx = P[n][0] - P[n - 1][0], dy = P[n][1] - P[n - 1][1], d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
      const tx = P[n][0] - ux * F.so, ty = P[n][1] - uy * F.so, bx = tx - ux * F.head, by = ty - uy * F.head, hw = F.head * 0.7;
      const head = svgEl("path", { d: `M${f1(bx - uy * hw)} ${f1(by + ux * hw)} L${f1(tx)} ${f1(ty)} L${f1(bx + uy * hw)} ${f1(by - ux * hw)} Z`, fill: col, "fill-opacity": e.accent ? 1 : 0.6 });
      head.style.opacity = 0;
      svg.append(head);
      const lab = e.lab ? K.el(world, `left:${e.lab.x}px;top:${e.lab.y}px;width:${e.lab.w}px;height:${e.lab.h}px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;` +
        `border-radius:4px;background:${MASK};font:500 ${KS}px/1 ${mono};letter-spacing:.14em;text-transform:uppercase;color:${e.accent ? C.acc : C.sub};white-space:nowrap;opacity:0`,
        HF.esc(e.label), "hf-abs mono") : null;                               // .mono: the kicker type (precheck reads it as one)
      edges[e.from + ">" + e.to] = { path, draw, head, lab, len, e };
    });
    // ---- the boxes: white with a hairline; sunk grey for an input or an outside system; dashed when optional; the focal
    // one in the accent, lifted to e3 (whitespace README §3: "the part he means in the accent and raised to e3"); no
    // other shadow, glow or ring on a box
    const byId = {}, all = [];
    // stacked (16:9): the tag at the top left, the text centred under it; inline (9:16): the tag left of the text
    const tagTop = inline ? Math.round((g.size.NH - (KS + 16)) / 2) : 18, tagLeft = inline ? 24 : 20;
    const txt = inline ? `left:${lead}px;right:24px;text-align:left` : "left:24px;right:24px;text-align:center";
    g.nodes.forEach((n) => {
      const sunk = n.kind === "input" || n.kind === "external", bg = sunk ? C.sunk : C.card;
      const box = K.el(world, `left:${n.x}px;top:${n.y}px;width:${n.w}px;height:${n.h}px;box-sizing:border-box;border-radius:${F.r}px;` +
        `background:${n.focal ? C.accTint : bg};border:2px ${n.kind === "optional" ? "dashed" : "solid"} ${n.focal ? C.acc : HAIR};opacity:0`,
        `<div class="dg-lift" style="position:absolute;inset:-2px;border-radius:${F.r}px;box-shadow:${C.e3};opacity:${n.focal ? 1 : 0}"></div>` +
        (n.tag ? `<div class="dg-tag mono" style="position:absolute;left:${tagLeft}px;top:${tagTop}px;box-sizing:border-box;height:${KS + 16}px;padding:0 8px 0 10px;display:flex;align-items:center;` +
          `border:2px solid ${n.focal ? C.acc : TAG};border-radius:6px;font:500 ${KS}px/1 ${mono};letter-spacing:.14em;color:${n.focal ? C.acc : C.sub};white-space:nowrap">${HF.esc(n.tag)}</div>` : "") +
        `<div class="i2" style="position:absolute;left:${tagLeft}px;top:${tagTop}px;height:${KS + 16}px;display:flex;align-items:center;opacity:0">${HF.icon("check", KS + 10, C.ok, 2.6)}</div>` +
        `<div class="dg-name" style="position:absolute;${txt};top:${nameTop}px;font:600 ${NZ}px/1 ${body};letter-spacing:-0.02em;color:${n.focal ? C.acc : C.ink};white-space:nowrap">${HF.esc(n.label)}</div>` +
        (n.sub ? `<div class="dg-sub" style="position:absolute;${txt};top:${subTop}px;font:500 ${SZ}px/${subLines > 1 ? 1.15 : 1} ${n.mono ? mono : body};` +
          `letter-spacing:${n.mono ? ".02em" : "0"};color:${C.sub};white-space:${subLines > 1 ? "normal" : "nowrap"}">${HF.esc(n.sub)}</div>` : ""));
      box.dataset.node = n.id;
      const N = { id: n.id, x: n.x + n.w / 2, y: n.y + n.h / 2, w: n.w, h: n.h, el: box, g: n, bg, bd: n.focal ? C.acc : HAIR, ink: n.focal ? C.acc : C.ink };
      byId[n.id] = N; all.push(N);
    });
    const node = (id) => { const n = byId[id]; if (!n) throw new Error("HF.diagram: no node " + id); return n; };
    const eyebrow = g.title ? K.el(world, `left:${g.title.x}px;top:${g.title.y}px;font:500 ${KS}px/1 ${mono};letter-spacing:.14em;text-transform:uppercase;color:${C.sub};white-space:nowrap;opacity:0`,
      HF.esc(g.title.text), "hf-abs mono") : null;
    // ---- the camera (focus / overview: the energy is the camera's; boxes never zoom, bounce or blur)
    const cams = [], cam = { cx: vw / 2, cy: vh / 2, z: 1 };
    let camAt = null;
    K.onFrame((t) => {
      if (!camAt) camAt = HF.keyed(cams, cam, { log: ["z", "scale", "s"] });
      const c = camAt(t);
      world.style.transform = `translate(${(vw / 2 - c.cx * c.z).toFixed(2)}px, ${(vh / 2 - c.cy * c.z).toFixed(2)}px) scale(${c.z.toFixed(4)})`;
    });
    // ---- the one flow token: a pure function of time, on the latest dg.flow's path until its `until`
    const tok = svgEl("circle", { r: 9, fill: C.acc, opacity: 0 }), runs = [];
    svg.append(tok);
    K.onFrame((t) => {
      let r = null;
      for (const x of runs) if (x.t <= t && (x.until == null || t < x.until)) r = x;
      if (!r) { tok.setAttribute("opacity", "0"); return; }
      const Ls = r.es.map((e) => e.len), tot = Ls.reduce((a, b) => a + b, 0);
      let d = (((t - r.t) % r.period) / r.period) * tot, k = 0;
      while (k < Ls.length - 1 && d > Ls[k]) { d -= Ls[k]; k++; }
      const q = r.es[k].path.getPointAtLength(Math.min(d, Ls[k]));
      tok.setAttribute("cx", q.x.toFixed(2)); tok.setAttribute("cy", q.y.toFixed(2)); tok.setAttribute("opacity", Math.min(1, (t - r.t) / 0.15).toFixed(3));
    });
    const ids = (x) => (Array.isArray(x) ? x : [x]);
    // a step: a rise of 16 px with opacity over 0.48 s (diagram-design's motion step); no zoom, bounce or blur
    const rise = (e, t) => { tl.fromTo(e, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: F.step, ease: "power2.out", immediateRender: false }, Q(t)); };
    const enters = [], draws = [], focal = g.nodes.filter((n) => n.focal).map(() => [-1e9, null]), notes = [];
    const pub = { style: "flat", gate: true, title: g.title ? g.title.text : null, show: [],
      nodes: g.nodes.map(({ id, x, y, w, h, focal: fo, kind }) => ({ id, x, y, w, h, focal: fo, kind })),
      edges: g.edges.map(({ from, to, route, dash, accent, label, pts, lab }) => ({ from, to, route, dash, accent, label, pts, lab })) };
    const dg = { nodes: byId, view, world, geom: g, pub };
    let shown = false;
    view.style.transformOrigin = "50% 50%";
    dg.show = (a, b) => {
      if (!shown) { tl.set(view, { autoAlpha: 0 }, 0); shown = true; }
      tl.set(view, { autoAlpha: 1 }, Q(a)); if (b != null) tl.set(view, { autoAlpha: 0 }, Q(b));
      if (eyebrow) rise(eyebrow, a);
      if (b != null && o.drift !== false) K.drift(view, a, b, 1.03);         // a slow push while it's up: the camera's motion
      pub.show.push([a, b == null ? null : b]);
      return dg;
    };
    const entered = (t) => { enters.push(t); if (HF.diagram.steps(enters, F.step) > 2) warn(`more than 2 items enter within ${F.step} s (by ${t.toFixed(2)} s): give each its own word`); };
    dg.reveal = (x, t, stagger = 0.24) => { ids(x).forEach((id, k) => { rise(node(id).el, t + k * stagger); entered(t + k * stagger); }); K.sfx("click", t); return dg; };
    dg.connect = (f, to, t, dur = 0.5) => {
      const e = edges[f + ">" + to]; if (!e) throw new Error("HF.diagram: no edge " + f + " -> " + to);
      tl.fromTo(e.draw, { strokeDashoffset: e.len }, { strokeDashoffset: 0, duration: dur, ease: "power2.inOut", immediateRender: false }, Q(t));
      tl.to(e.head, { opacity: 1, duration: 0.12 }, Q(t + dur - 0.1));
      if (e.lab) { rise(e.lab, t + dur * 0.5); entered(t + dur * 0.5); }
      draws.push([t, t + dur]);
      if (most(draws) > 2) warn(`more than 2 edges draw at once (by ${t.toFixed(2)} s)`);
      return dg;
    };
    dg.connectAll = (t, dur = 0.5, stagger) => {
      const s = stagger != null ? stagger : dur * 0.6;
      Object.keys(edges).forEach((k, i) => { const [f, to] = k.split(">"); dg.connect(f, to, t + i * s, dur); });
      return dg;
    };
    dg.focus = (x, t, opt = {}) => {
      const ns = ids(x).map(node);
      const x0 = Math.min(...ns.map((n) => n.x - n.w / 2)) - 60, x1 = Math.max(...ns.map((n) => n.x + n.w / 2)) + 60;
      const y0 = Math.min(...ns.map((n) => n.y - n.h / 2)) - 80, y1 = Math.max(...ns.map((n) => n.y + n.h / 2)) + 80;
      const z = Math.min(opt.zoom || 1.6, vw / (x1 - x0), vh / (y1 - y0));
      cams.push({ t, dur: opt.dur || 0.8, ease: opt.ease || "power3.inOut", v: { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, z } }); camAt = null;
      all.forEach((n) => tl.to(n.el, { opacity: ns.includes(n) ? 1 : opt.dim != null ? opt.dim : 0.3, duration: 0.4 }, Q(t)));
      if (eyebrow) tl.to(eyebrow, { opacity: 0, duration: 0.3 }, Q(t));
      return dg;
    };
    dg.overview = (t, opt = {}) => {
      cams.push({ t, dur: opt.dur || 0.8, ease: opt.ease || "power3.inOut", v: { cx: vw / 2, cy: vh / 2, z: 1 } }); camAt = null;
      all.forEach((n) => tl.to(n.el, { opacity: 1, duration: 0.4 }, Q(t)));
      if (eyebrow) tl.to(eyebrow, { opacity: 1, duration: 0.3 }, Q(t + 0.3));
      return dg;
    };
    // done: the tag gives way to a check (no pulse: boxes stay still)
    dg.done = (x, t, stagger = 0.24) => {
      ids(x).forEach((id, k) => { const e = node(id).el, tg = e.querySelector(".dg-tag"); if (tg) tl.to(tg, { opacity: 0, duration: 0.2 }, Q(t + k * stagger)); tl.to(e.querySelector(".i2"), { opacity: 1, duration: 0.3 }, Q(t + k * stagger)); });
      K.sfx("check", t); return dg;
    };
    // highlight: the node is focal from t (accent, lifted to e3) until `until`; at most 2 focal at once
    dg.highlight = (id, t, until) => {
      const n = node(id), e = n.el, lift = e.querySelector(".dg-lift"), nmEl = e.querySelector(".dg-name"), tg = e.querySelector(".dg-tag");
      const set = (on, at) => {
        tl.to(e, { backgroundColor: on ? C.accTint : n.g.focal ? C.accTint : n.bg, borderColor: on ? C.acc : n.bd, duration: 0.3 }, Q(at));
        tl.to(lift, { opacity: on || n.g.focal ? 1 : 0, duration: 0.3 }, Q(at));
        tl.to(nmEl, { color: on ? C.acc : n.ink, duration: 0.3 }, Q(at));
        if (tg) tl.to(tg, { color: on || n.g.focal ? C.acc : C.sub, borderColor: on || n.g.focal ? C.acc : TAG, duration: 0.3 }, Q(at));
      };
      set(true, t); if (until != null) set(false, until);
      if (!n.g.focal) focal.push([t, until == null ? null : until]);
      if (most(focal) > F.focal) warn(`more than ${F.focal} focal nodes at once (by ${t.toFixed(2)} s): one is the part he names`);
      return dg;
    };
    // note: the one annotation chip, under the node and under any lane that runs beneath it
    dg.note = (id, t, text, until) => {
      const n = node(id).g;
      let yb = n.y + n.h;
      g.edges.forEach((e) => {
        e.pts.slice(1).forEach((p, i) => { const q = e.pts[i]; if (Math.max(p[0], q[0]) >= n.x && Math.min(p[0], q[0]) <= n.x + n.w && Math.min(p[1], q[1]) >= n.y + n.h) yb = Math.max(yb, p[1], q[1]); });
        if (e.lab && e.lab.x < n.x + n.w && e.lab.x + e.lab.w > n.x && e.lab.y >= n.y + n.h) yb = Math.max(yb, e.lab.y + e.lab.h);
      });
      const nt = K.el(world, `left:${n.x + n.w / 2 - 400}px;top:${yb + 28}px;width:800px;display:flex;justify-content:center;opacity:0`,
        `<span style="display:inline-block;padding:10px 18px;border-radius:12px;background:${C.card};border:2px solid ${HAIR};font:500 ${SZ}px/1.1 ${body};color:${C.ink2};white-space:nowrap">${HF.esc(text)}</span>`);
      rise(nt, t); if (until != null) tl.to(nt, { opacity: 0, duration: 0.3 }, Q(until));
      notes.push([t, until == null ? null : until]);
      if (most(notes) > 1) warn("more than 1 annotation chip on screen at once (at most 1)");
      return dg;
    };
    // flow: the diagram's one token on an edge, or a chain of them (a loop: [[a, b], [b, c], [c, a]]), one lap every
    // `period` s (>= 3); a later call moves the same token
    dg.flow = (f, to, t, opt = {}) => {
      const [chain, at, op] = Array.isArray(f) ? [f, to, t || {}] : [[[f, to]], t, opt];
      const es = chain.map(([a, b]) => { const e = edges[a + ">" + b]; if (!e) throw new Error("HF.diagram: no edge " + a + " -> " + b); return e; });
      runs.push({ t: at, es, period: Math.max(F.period, op.period || op.dur || 3.2), until: op.until != null ? op.until : null });
      runs.sort((p, q) => p.t - q.t);
      return dg;
    };
    publish(pub, vx, vy, vw, vh, o);
    return dg;
  };
})(typeof window !== "undefined" ? window : globalThis);
