/*
 * kit/hf/redline.js: the Redline look (kit/presets/redline/README.md, 2026-10-19). An engineer's notebook page: warm
 * graph paper that never moves, black newsroom-grotesk headlines, ONE red felt-tip pen that marks only the words he is
 * claiming, light pencil sketches for structure, his real face in his real room, and his real screen recordings shown
 * as numbered figures. The pen marks screens on a tracing sheet that is laid over the recording and lifted off again.
 * It re-skins the frame of HF.studio (16:9) or HF.reel (9:16), so focus/scoreboard/holds/captions still work:
 *
 *   const S = HF.studio(K, ROOT, st, { end: D.total, talk: D.talk });          // or HF.reel(...) for a Reel
 *   const R = HF.redline(S, st, { sections: [[0, "01 / the idea"], ...] });
 *   R.face([{ t: 0, at: "full" }, { t: 12.4, at: "right" }, { t: 30, at: "pip", in: "slide" }])   the speaker
 *   const L = R.page(a, b);                                       a still layer (a page is read, never swayed)
 *   const h = R.head(L, "github/*reverse-engineer*", t, { x: 120, y: 160, size: 150 })   *words* get the pen
 *   R.say(L, from, to, { x, y, size, mark: [ids] })               his words landing on their spoken time
 *   R.sub(L, "Complete app · 6 hours", t, { x, y })  R.label(L, x, y, "FIG. 02")  R.note(L, x, y, "the bug", t)
 *   const pen = R.pen(L); pen.underline(el | [x, y, w, h], t); pen.circle(...); pen.strike(...); pen.arrow(p0, p1, t)
 *   const pc = R.pencil(L); pc.icon("mic", x, y, 140, t); pc.arrow([x0, y0], [x1, y1], t, { dashed: true })
 *   const f = R.fig(L, x, y, w, h, { img | src, srcW, srcH, caption: "Claude Code / terminal" })   a screen as a figure
 *   f.place(a, b); f.look(t, [x, y, w, h]); f.back(t); const sh = f.sheet(a, b, { window: [x, y, w, h] });
 *   f.mark("circle", [x, y, w, h], t)                              source px, drawn on the sheet (camera held)
 *   R.card(a, b, { kicker, title, sub, icons, peek })  R.stat  R.list  R.compare  R.print  R.skip  R.endCard  R.peek
 *   R.captions({ ... })                                           9:16 only: paper-label captions (S.captions)
 *
 * Rules (the README has the reasons and the sources):
 *   - red is the pen and nothing else: at most one mark per sentence and three on screen, only on claim words;
 *     underline = emphasis, circle = look here, strike (+ a handwritten fix) = wrong -> right, caret = an addition;
 *   - the pen goes down ~80 ms after the word is said; underline 0.32 s, circle 0.6 s, an arrow's head after a lift;
 *   - the paper, the grid and a landed headline never move; type lands whole on a cut or word by word on the voice
 *     (no blur-in, no scale-pop, no letter-by-letter typing); things leave on a cut, or are struck through;
 *   - pieces are placed in 0.28 s (power3.out, 24 px travel) and leave in 0.2 s or on a cut; no rotation except a
 *     taped print (+-1.5 deg); no shadows, no rounded corners, no glow; depth is overlap and a 2 px ink outline;
 *   - a screen the viewer must read is a figure (full bleed, or 66-75 % wide with a FIG. caption); zoom only to read
 *     (look(): ~1.8x, 1.1 s in, a held read), marks go on the tracing sheet while the camera holds;
 *   - everything is a pure function of time; geometry that needs laid-out text is measured lazily on the first frame.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.kit) throw new Error("kit/hf/redline.js needs core.js first");
  const NS = "http://www.w3.org/2000/svg";

  const PALETTE = { paper: "#FBFAF6", grid: "#E6E6E1", ink: "#151515", ink2: "#3D3B37", grey: "#6F6D68", pencil: "#8F8C85",
    red: "#D7261E", hi: "#FFE45C", sheet: "rgba(255,255,255,.06)", frost: "rgba(251,250,246,.90)" };
  const TIME = { place: 0.28, out: 0.2, travel: 24, penLag: 0.08, underline: 0.32, circle: 0.6, strike: 0.28, arrow: 0.45,
    zoomIn: 1.1, zoomOut: 0.9, sheetIn: 0.28, sheetOut: 0.2 };
  const GRID = 60;                                                           // 32 x 18 cells at 1920x1080, 18 x 32 at 9:16

  const CSS = `
    .rl { font-family: "Atkinson", sans-serif; color: #151515; }
    .rl-h { font-family: "Schibsted", sans-serif; font-weight: 900; letter-spacing: -0.03em; line-height: 0.95; white-space: nowrap; color: #151515; }
    .rl-h > span { display: inline-block; white-space: pre; }
    .rl-sub { font: 700 46px/1.15 "Atkinson", sans-serif; color: #6F6D68; white-space: nowrap; letter-spacing: -0.005em; }
    .rl-body { font: 500 36px/1.3 "Atkinson", sans-serif; color: #151515; }
    .rl-lbl, .rl-lbl.lbl { font: 500 21px/1 "Martian", monospace; letter-spacing: .01em; text-transform: none; color: #6F6D68; white-space: nowrap; }   /* .lbl only exempts it in precheck */
    .rl-hand { font: 400 72px/1 "NanumPen", cursive; color: #D7261E; white-space: pre; }
    .rl-say { font-family: "Schibsted", sans-serif; font-weight: 800; letter-spacing: -0.025em; line-height: 1.0; color: #151515; white-space: normal; }
    .rl-say > span { display: inline-block; }
    .rl-paper { background-color: #FBFAF6; }
    .rl-reel .rl-lbl, .rl-reel .rl-lbl.lbl { font-size: 26px; }                                    /* 9:16: a label still reads on a phone */
    .rl-cap { position: absolute; left: 60px; width: 960px; text-align: center; font: 700 50px/1.22 "Atkinson", sans-serif; color: #151515; white-space: normal; }
    .rl-cap span.w { display: inline-block; padding: 0; }
    .rl-cap .plate { display: inline; background: #FBFAF6; box-decoration-break: clone; -webkit-box-decoration-break: clone;
      padding: 4px 14px 6px; box-shadow: 0 0 0 2px #151515; }`;

  // ---------------------------------------------------------------- hand geometry (build time, seeded)
  // 1-D value noise with a cosine blend: the slow wave and the fine tremor of a hand (plain per-point jitter reads as fuzz)
  const noise1 = (seed) => { const r = HF.rng(seed), v = Array.from({ length: 256 }, () => r() * 2 - 1);
    return (x) => { const i = Math.floor(x), f = x - i, a = v[((i % 256) + 256) % 256], b = v[(((i + 1) % 256) + 256) % 256], u = (1 - Math.cos(f * Math.PI)) / 2; return a + (b - a) * u; }; };
  // a centreline [[x, y], ...] -> resampled every ~7 px, nudged along its normal by two noise layers, with a pressure
  const handLine = (pts, seed, o = {}) => {
    const out = [], n1 = noise1(seed), n2 = noise1(seed + 977);
    const L = [0]; for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const tot = L[L.length - 1] || 1, step = o.step || 7, N = Math.max(2, Math.ceil(tot / step));
    let k = 0;
    for (let j = 0; j <= N; j++) {
      const s = (j / N) * tot;
      while (k < L.length - 2 && L[k + 1] < s) k++;
      const u = (s - L[k]) / ((L[k + 1] - L[k]) || 1), A = pts[k], B = pts[k + 1] || A;
      const x = A[0] + (B[0] - A[0]) * u, y = A[1] + (B[1] - A[1]) * u, dx = B[0] - A[0], dy = B[1] - A[1], dl = Math.hypot(dx, dy) || 1;
      const off = (o.wave != null ? o.wave : 1.1) * n1(s / (o.waveLen || 220)) + (o.tremor != null ? o.tremor : 0.35) * n2(s / 28);
      const q = s / tot, p = o.press ? o.press(q) : 0.75 + 0.25 * Math.sin(Math.PI * Math.min(1, q * 1.1)) - 0.1 * q;   // press, swell, lift
      out.push([x - (dy / dl) * off, y + (dx / dl) * off, p]);
    }
    return out;
  };
  // time warp along a stroke: a hand slows on tight curves (two-thirds power law: v ~ R^(1/3)) and starts and stops
  // smoothly (minimum jerk), so the pen never moves like a progress bar
  const warp = (pts) => {
    const n = pts.length, dt = [0];
    for (let i = 1; i < n; i++) {
      const a = pts[Math.max(0, i - 2)], b = pts[i - 1], c = pts[Math.min(n - 1, i + 1)];
      const ab = Math.hypot(b[0] - a[0], b[1] - a[1]), bc = Math.hypot(c[0] - b[0], c[1] - b[1]), ac = Math.hypot(c[0] - a[0], c[1] - a[1]);
      const area = Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2;
      const R = area > 1e-6 ? (ab * bc * ac) / (4 * area) : 1e6, v = Math.pow(Math.min(1e4, Math.max(8, R)), 1 / 3);
      dt.push(dt[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) / v);
    }
    const T = dt[n - 1] || 1;
    return dt.map((x) => x / T);                                             // cumulative time share at each point
  };
  const minJerk = (p) => p * p * p * (10 - 15 * p + 6 * p * p);
  const outlinePath = (pts) => {                                             // perfect-freehand polygon -> a smooth closed path
    if (pts.length < 3) return "";
    let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)} Q`;
    for (let i = 0; i < pts.length; i++) { const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
      d += ` ${x0.toFixed(1)} ${y0.toFixed(1)} ${((x0 + x1) / 2).toFixed(1)} ${((y0 + y1) / 2).toFixed(1)}`; }
    return d + " Z";
  };
  // a box [x, y, w, h] of an element inside a container, from layout offsets (ignores transforms: the mark lives in
  // the same transformed parent), or a given box
  const boxIn = (target, cont) => {
    if (Array.isArray(target)) return target;
    let x = 0, y = 0, e = target;
    while (e && e !== cont) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    if (e !== cont) { const a = target.getBoundingClientRect(), b = cont.getBoundingClientRect(); return [a.left - b.left, a.top - b.top, a.width, a.height]; }
    return [x, y, target.offsetWidth, target.offsetHeight];
  };
  const fontsReady = () => !document.fonts || document.fonts.status === "loaded";

  // ---------------------------------------------------------------- pencil icons: centrelines in a 100 x 100 box
  // drawn the way a person sketches: a few strokes, corners overshooting a little, shapes left slightly open
  const arc = (cx, cy, rx, ry, a0, a1, n = 24) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + ((a1 - a0) * i) / n; return [cx + rx * Math.cos(a), cy + ry * Math.sin(a)]; });
  const rect = (x, y, w, h, o = 3) => [[x - o, y], [x + w + o, y], [x + w, y - o], [x + w, y + h + o], [x + w + o, y + h], [x - o, y + h], [x, y + h + o], [x, y - o * 0.5]];
  const rr = (x, y, w, h, r) => [...arc(x + w - r, y + r, r, r, -Math.PI / 2, 0, 6), ...arc(x + w - r, y + h - r, r, r, 0, Math.PI / 2, 6),
    ...arc(x + r, y + h - r, r, r, Math.PI / 2, Math.PI, 6), ...arc(x + r, y + r, r, r, Math.PI, Math.PI * 1.42, 5)];
  const P = Math.PI;
  const ICONS = {
    webcam: [arc(50, 40, 30, 26, -P * 0.42, P * 1.5), arc(50, 40, 11, 11, 0, P * 2.1, 16), [[38, 66], [32, 82], [68, 82], [62, 66]], [[26, 90], [74, 90]]],
    mic: [rr(38, 10, 24, 46, 12), arc(50, 44, 24, 24, P * 0.05, P * 0.95, 16), [[50, 68], [50, 84]], [[34, 86], [66, 86]], [[38, 26], [46, 26]], [[38, 36], [46, 36]]],
    window: [rect(8, 14, 84, 70), [[8, 28], [92, 28]], arc(16, 21, 2.2, 2.2, 0, P * 2, 8), arc(23, 21, 2.2, 2.2, 0, P * 2, 8), rect(15, 36, 32, 40, 1.5), rect(53, 36, 32, 40, 1.5),
      arc(31, 50, 6, 6, 0, P * 2, 12), arc(31, 74, 11, 9, P, P * 2, 10), arc(69, 50, 6, 6, 0, P * 2, 12), arc(69, 74, 11, 9, P, P * 2, 10)],
    monitor: [rect(8, 14, 84, 56), [[42, 70], [38, 84]], [[58, 70], [62, 84]], [[28, 86], [72, 86]]],
    phone: [rr(30, 6, 40, 88, 7), [[44, 14], [56, 14]], arc(50, 84, 3, 3, 0, P * 2, 8)],
    chat: [[...rr(10, 16, 80, 54, 10), [26, 70], [22, 86], [40, 70]], [[24, 34], [74, 34]], [[24, 46], [66, 46]], [[24, 58], [52, 58]]],
    terminal: [rect(8, 14, 84, 70), [[8, 28], [92, 28]], [[20, 44], [32, 52], [20, 60]], [[38, 62], [56, 62]]],
    cursor: [[[30, 12], [30, 76], [44, 62], [54, 86], [64, 81], [54, 58], [74, 58], [30, 12]]],
    file: [[[24, 8], [62, 8], [78, 24], [78, 92], [24, 92], [24, 6]], [[62, 8], [62, 24], [78, 24]], [[34, 42], [68, 42]], [[34, 54], [68, 54]], [[34, 66], [58, 66]]],
    globe: [arc(50, 50, 38, 38, -P * 0.5, P * 1.55, 30), arc(50, 50, 16, 38, -P * 0.5, P * 1.5, 20), [[13, 50], [88, 50]], [[18, 32], [82, 32]], [[18, 68], [82, 68]]],
    person: [arc(50, 34, 16, 18, -P * 0.4, P * 1.62, 20), arc(50, 92, 32, 28, P * 1.03, P * 1.97, 16)],
    signal: [arc(50, 50, 7, 7, 0, P * 2.05, 12), arc(50, 50, 20, 20, -P * 0.28, P * 0.28, 8), arc(50, 50, 20, 20, P * 0.72, P * 1.28, 8), arc(50, 50, 34, 34, -P * 0.3, P * 0.3, 10), arc(50, 50, 34, 34, P * 0.7, P * 1.3, 10)],
    clock: [arc(50, 50, 38, 38, -P * 0.45, P * 1.6, 30), [[50, 24], [50, 50], [68, 60]]],
    git: [arc(28, 20, 8, 8, 0, P * 2.1, 12), arc(28, 80, 8, 8, 0, P * 2.1, 12), arc(72, 34, 8, 8, 0, P * 2.1, 12), [[28, 28], [28, 72]], [[72, 42], [72, 50], [36, 70]]],
    db: [arc(50, 20, 32, 9, 0, P * 2.05, 20), [[18, 20], [18, 80]], [[82, 20], [82, 80]], arc(50, 80, 32, 9, 0, P, 14), arc(50, 50, 32, 9, 0, P, 14)],
    bolt: [[[56, 6], [24, 56], [48, 56], [40, 94], [76, 40], [52, 40], [58, 6]]],
    list: [rect(14, 16, 12, 12, 1), [[34, 22], [84, 22]], rect(14, 44, 12, 12, 1), [[34, 50], [78, 50]], rect(14, 72, 12, 12, 1), [[34, 78], [70, 78]]],
    spark: [[[50, 8], [56, 42], [90, 50], [56, 58], [50, 92], [44, 58], [10, 50], [44, 42], [50, 6]]],
  };

  HF.redline = function (S, st, o = {}) {
    const { K, tl, Q, el } = S;
    const PF = root.PerfectFreehand;
    if (!PF || !PF.getStroke) throw new Error("HF.redline needs vendor/perfect-freehand.js: `npm i` at the repo root, then vendor.copy_assets(film)");
    const C = Object.assign({}, PALETTE, o.palette || {});
    const WD = K.width, HT = K.height, REEL = HT > WD;
    if (!document.getElementById("hf-redline-css")) { const s = document.createElement("style"); s.id = "hf-redline-css"; s.textContent = CSS; document.head.append(s); }
    const ROOT = S.WORLD.parentElement;
    if (REEL) ROOT.classList.add("rl-reel");
    HF.look("redline", Object.assign(HF.lookOver(o.palette), o.palette && o.palette.red ? { acc: C.red } : {}));   // every kit component: ink, paper, the one red
    S.C.acc = C.red; S.C.ink = C.ink; S.C.paper = C.paper;

    // ---------------------------------------------------------------- the page: warm paper, a 60 px grid, still
    const gridCss = (col) => `background-image:linear-gradient(${col} 1px, transparent 1px),linear-gradient(90deg, ${col} 1px, transparent 1px);background-size:${GRID}px ${GRID}px;background-position:-1px -1px`;
    // o.grid === false: a plain white page (the owner, 2026-10-20: "a white, completely empty background")
    const paper = (par, z) => { const p = el(par, `left:0;top:0;width:${WD}px;height:${HT}px;background-color:${C.paper};${o.grid === false ? "" : gridCss(C.grid)}` + (z != null ? `;z-index:${z}` : ""));
      p.dataset.decor = "1"; return p; };
    S.WORLD.innerHTML = ""; S.WORLD.style.background = C.paper; ROOT.style.background = C.paper;
    paper(S.WORLD);
    [...ROOT.children].forEach((c) => { if (c.style && c.style.zIndex === "1" && !c.id) c.style.display = "none"; });   // the frame's dot grain
    if (S.CHROME) S.CHROME.style.display = "none";                         // the studio's corner labels and progress bar
    const snap = (v) => Math.round(v / GRID) * GRID;

    // ---------------------------------------------------------------- small pieces
    const page = (a, b, par = S.BACK, x = {}) => S.layer(a, b, par, Object.assign({ read: x.read !== false ? x.why || "page" : false, fade: 0, float: 0, push: 0 }, x));
    const place = (e, a, b, x = {}) => {                                       // in: 0.28 s, 24 px; out: a cut (or 0.2 s)
      K.show(e, a - 0.01, x.cut === false && b != null ? b + TIME.out : b);
      if (x.instant) return e;
      tl.fromTo(e, { opacity: 0, y: x.from != null ? x.from : TIME.travel }, { opacity: 1, y: 0, duration: TIME.place, ease: "power3.out", immediateRender: false }, Q(a));
      if (x.cut === false && b != null) tl.to(e, { opacity: 0, duration: TIME.out, ease: "power2.in", immediateRender: false }, Q(b));
      return e;
    };
    const label = (par, x, y, text, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, HF.esc(text), "hf-abs rl-lbl lbl");
    // a headline: lands whole at t (on a cut). "*a b*" spans get the pen (x.mark: "underline" | "circle" | "double"),
    // drawn at x.markAt (default t + 0.35, i.e. once the eye has the line)
    const head = (par, text, t, x = {}) => {
      const size = x.size || (REEL ? 116 : 150);
      const box = el(par, `left:${x.x != null ? x.x : 120}px;top:${x.y != null ? x.y : 120}px;font-size:${size}px;${x.align ? "text-align:" + x.align + ";width:" + (x.w || WD - 240) + "px;" : ""}${x.color ? "color:" + x.color + ";" : ""}`, "", "hf-abs rl-h");
      const marks = [];
      text.split("|").forEach((ln, li) => {
        if (li) box.append(document.createElement("br"));
        ln.split(/(\*[^*]+\*)/).filter(Boolean).forEach((seg) => {
          const s = document.createElement("span"); s.textContent = seg.replace(/^\*|\*$/g, "");
          box.append(s); if (seg[0] === "*") marks.push(s);
        });
      });
      K.show(box, t, x.until);
      const pen = marks.length && x.mark !== false ? penOn(par) : null;
      if (pen) marks.forEach((m, i) => { const at = (x.markAt != null ? x.markAt : t + 0.35) + i * 0.4, kind = x.mark || "underline";
        if (kind === "circle") pen.circle(m, at, { pad: size * 0.08 }); else pen.underline(m, at, { double: kind === "double", gap: size * 0.02, until: x.until, size: Math.max(12, Math.round(size * 0.1)) }); });
      return { box, marks, pen };
    };
    const sub = (par, text, t, x = {}) => { const s = el(par, `left:${x.x != null ? x.x : 120}px;top:${x.y != null ? x.y : 330}px;${x.size ? "font-size:" + x.size + "px;" : ""}${x.align ? "text-align:" + x.align + ";width:" + (x.w || WD - 240) + "px;" : ""}`, HF.esc(text), "hf-abs rl-sub");
      K.show(s, t, x.until); return s; };
    // his words on their spoken time: each word appears as it is said (no rise, no blur); x.mark: ids the pen underlines
    // as the last of them is said, x.circle: ids it circles
    const say = (par, from, to, x = {}) => {
      const ws = K.words_.filter((w) => w.i >= from && w.i <= to && w.text);
      const box = el(par, `left:${x.x != null ? x.x : 120}px;top:${x.y != null ? x.y : 160}px;width:${x.w || WD - 240}px;font-size:${x.size || (REEL ? 96 : 110)}px;${x.align ? "text-align:" + x.align + ";" : ""}`, "", "hf-abs rl-say");
      const spans = {}, brk = new Set(x.br || []);
      ws.forEach((w) => { if (brk.has(w.i)) box.append(document.createElement("br"));
        const s = document.createElement("span"); s.textContent = String(w.text).replace(/,$/, ""); s.dataset.w = w.i; box.append(s); box.append(document.createTextNode(" "));
        s.style.visibility = "hidden"; tl.set(s, { visibility: "visible" }, Q(Math.max(0.01, w.t - 1 / K.fps))); s._a = Q(w.t); spans[w.i] = s; });
      if (S.cover) S.cover(from, to);                                        // 9:16: captions skip these words
      const pen = (x.mark || x.circle) ? penOn(par) : null;
      const group = (ids) => { const ss = ids.map((i) => spans[i]).filter(Boolean); if (!ss.length) return null;
        return { ss, last: Math.max(...ids.map((i) => (K.words_.find((w) => w.i === i) || { e: 0 }).e)) }; };
      const markOn = (ids, kind) => { const g = group(ids); if (!g) return;
        pen[kind](g.ss[0], g.last + TIME.penLag, g.ss.length > 1 ? { lazy: () => spanBox(g.ss, par) } : {}); };
      if (x.mark) markOn(x.mark, "underline");
      if (x.circle) markOn(x.circle, "circle");
      return { box, spans, pen };
    };
    const spanBox = (ss, par) => { const bs = ss.map((s) => boxIn(s, par)); const x0 = Math.min(...bs.map((b) => b[0])), y0 = Math.min(...bs.map((b) => b[1]));
      return [x0, y0, Math.max(...bs.map((b) => b[0] + b[2])) - x0, Math.max(...bs.map((b) => b[1] + b[3])) - y0]; };

    // ---------------------------------------------------------------- the red pen (and the pencil): perfect-freehand
    // A pen draws into one svg per container. Every mark is generated once, lazily on the first frame its geometry is
    // needed (fonts loaded), then drawn by progress: at time t the outline of points[0..n(t)] with a warped speed.
    const pens = new Map();
    const penOn = (par, x = {}) => {
      const key = par, kind = x.kind || "pen";
      if (pens.has(key) && pens.get(key)[kind]) return pens.get(key)[kind];
      const svg = document.createElementNS(NS, "svg");
      svg.setAttribute("width", par.offsetWidth || WD); svg.setAttribute("height", par.offsetHeight || HT);
      svg.style.cssText = `position:absolute;left:0;top:0;overflow:visible;pointer-events:none;${kind === "pen" ? "mix-blend-mode:multiply;" : ""}`;
      svg.dataset.decor = "1";
      par.append(svg);
      const P0 = makePen(par, svg, kind, x);
      const rec = pens.get(key) || {}; rec[kind] = P0; pens.set(key, rec);
      return P0;
    };
    const STYLE = {
      pen: (size) => ({ size, thinning: 0.18, smoothing: 0.6, streamline: 0.45, simulatePressure: false, start: { taper: size * 0.6, cap: true }, end: { taper: size * 2.4, cap: true } }),
      pencil: (size) => ({ size, thinning: 0.55, smoothing: 0.55, streamline: 0.4, simulatePressure: false, start: { taper: size * 4, cap: true }, end: { taper: size * 6, cap: true } }),
    };
    function makePen(par, svg, kind, x0) {
      const color = x0.color || (kind === "pen" ? C.red : C.pencil), base = x0.size || (kind === "pen" ? (REEL ? 13 : 12) : 2.6);
      const opacity = kind === "pen" ? 0.92 : 0.9;
      let seedN = (x0.seed || 7) * 7919;
      const marks = [];
      // strokes(geom) -> [[x, y], ...][]; each stroke drawn in turn inside [t, t + dur] with a short lift between
      const mark = (geomFn, t, a = {}) => {
        const m = { geomFn, t: Q(t), dur: a.dur || 0.4, size: a.size || base, color: a.color || color, seed: a.seed || (seedN += 101), until: a.until,
          els: [], st: null, last: -1 };
        marks.push(m);
        if (o.sfx && o.sfx[kind] && a.sfx !== false) K.sfx(o.sfx[kind], t, a.db != null ? a.db : -24);
        return m.t + m.dur;
      };
      const build = (m) => {
        const raw = m.geomFn();
        if (!raw) return false;
        const strokes = raw.map((s, i) => handLine(s, m.seed + i * 31, { wave: kind === "pen" ? 1.1 : 0.7, tremor: kind === "pen" ? 0.35 : 0.25, step: kind === "pen" ? 7 : 5 }));
        const lens = strokes.map((s) => s.reduce((L, p, i) => L + (i ? Math.hypot(p[0] - s[i - 1][0], p[1] - s[i - 1][1]) : 0), 0));
        const tot = lens.reduce((a, b) => a + b, 0) || 1, lift = strokes.length > 1 ? 0.08 : 0, usable = Math.max(0.1, m.dur - lift * (strokes.length - 1));
        let acc = 0;
        m.st = strokes.map((s, i) => {
          const p = document.createElementNS(NS, "path"); p.setAttribute("fill", m.color); p.setAttribute("opacity", opacity); svg.append(p);
          const t0 = m.t + (acc / tot) * usable + i * lift; acc += lens[i];
          return { p, pts: s, w: warp(s), t0, d: Math.max(0.06, (lens[i] / tot) * usable), last: -1 };
        });
        return true;
      };
      const draw = (s, t, m) => {
        const pr = Math.max(0, Math.min(1, (t - s.t0) / s.d));
        const gone = m.until != null && t >= m.until;
        const key = gone ? -2 : pr;
        if (key === s.last) return;
        s.last = key;
        if (pr <= 0 || gone) { s.p.setAttribute("d", ""); return; }
        const u = minJerk(pr);
        let i = 0; while (i < s.w.length - 1 && s.w[i + 1] <= u) i++;
        const sl = s.pts.slice(0, i + 1);
        if (i + 1 < s.pts.length) { const f = (u - s.w[i]) / ((s.w[i + 1] - s.w[i]) || 1), A = s.pts[i], B = s.pts[i + 1];
          if (f > 1e-3) sl.push([A[0] + (B[0] - A[0]) * f, A[1] + (B[1] - A[1]) * f, A[2] + (B[2] - A[2]) * f]); }
        s.p.setAttribute("d", outlinePath(PF.getStroke(sl, Object.assign({}, STYLE[kind](m.size), { last: pr >= 1 }))));
      };
      K.onFrame((t) => {
        for (const m of marks) {
          if (t < m.t - 0.02 && !m.st) continue;
          if (!m.st) { if (!fontsReady()) continue; if (!build(m)) continue; }
          m.st.forEach((s) => draw(s, t, m));
        }
      });
      const B = (target, a) => () => (a && a.lazy ? a.lazy() : boxIn(target, par));
      const P1 = { svg, kind, marks };
      // ---- the marks (boxes in the container's px; an element is measured on the first frame)
      P1.underline = (target, t, a = {}) => mark(() => { const [x, y, w, h] = B(target, a)(); if (!w) return null;
        const gap = a.gap != null ? a.gap : 6, yb = y + h + gap, x0 = x - Math.min(w * 0.04, 22), x1 = x + w + Math.min(w * 0.06, 36), rise = Math.min(12, Math.tan((1.5 * Math.PI) / 180) * (x1 - x0));
        const r = HF.rng(a.seed || 11), bow = (0.6 + r() * 0.6) * 0.01 * (x1 - x0);
        const line = (dy, rev) => Array.from({ length: 24 }, (_, k) => { const u = k / 23, q = rev ? 1 - u : u;
          return [x0 + (x1 - x0) * q, yb + dy - rise * q + bow * Math.sin(Math.PI * q)]; });
        return a.double ? [line(0, false), line(a.size ? a.size * 0.9 : 11, true)] : [line(0, false)]; }, t, { dur: a.double ? 0.55 : TIME.underline, ...a });
      P1.circle = (target, t, a = {}) => mark(() => { let [x, y, w, h] = B(target, a)(); if (!w) return null;
        if (!Array.isArray(target) && !a.lazy && h > 40) { y += h * 0.14; h *= 0.72; }
        const pad = a.pad != null ? a.pad : 14, cx = x + w / 2, cy = y + h / 2, rx = w / 2 + pad + w * 0.04, ry = h / 2 + pad * 0.6 + h * 0.03;
        const a0 = -P / 3, sweep = 2 * P + (20 * P) / 180, n = 64;              // starts near 1 o'clock, runs ~20 deg past
        return [Array.from({ length: n }, (_, k) => { const u = k / (n - 1), th = a0 + sweep * u, g = 1 + 0.06 * u;
          return [cx + rx * g * Math.cos(th), cy + ry * g * Math.sin(th) * (1 - 0.03 * Math.sin(th * 2))]; })]; }, t, { dur: TIME.circle, ...a });
      P1.strike = (target, t, a = {}) => mark(() => { const [x, y, w, h] = B(target, a)(); if (!w) return null;
        const yc = y + h * (a.at != null ? a.at : 0.56);
        return [[[x - w * 0.03, yc + 3], [x + w * 0.5, yc - 1], [x + w * 1.03, yc - 5]]]; }, t, { dur: TIME.strike, ...a });
      const pt = (p) => (typeof p === "function" ? p() : p);
      P1.caret = (at, t, a = {}) => mark(() => { const [x, y] = pt(at), s = a.w || 34; return [[[x - s / 2, y + s * 0.6], [x, y - s * 0.2], [x + s / 2, y + s * 0.6]]]; }, t, { dur: 0.22, ...a });
      P1.tick = (at, t, a = {}) => mark(() => { const [x, y] = pt(at), s = a.w || 46; return [[[x - s * 0.5, y], [x - s * 0.12, y + s * 0.42], [x + s * 0.6, y - s * 0.6]]]; }, t, { dur: 0.28, ...a });
      P1.cross = (at, t, a = {}) => mark(() => { const [x, y] = pt(at), s = (a.w || 44) / 2; return [[[x - s, y - s], [x + s, y + s]], [[x + s, y - s * 1.05], [x - s, y + s * 0.95]]]; }, t, { dur: 0.36, ...a });
      P1.bracket = (target, t, a = {}) => mark(() => { const [x, y, w, h] = B(target, a)(); if (!w) return null; const bx = x - (a.gap || 28), d = 16;
        return [[[bx + d, y - 4], [bx, y + 6], [bx - 2, y + h / 2], [bx, y + h - 6], [bx + d, y + h + 4]]]; }, t, { dur: 0.35, ...a });
      P1.line = (pts, t, a = {}) => mark(() => [pts], t, { dur: a.dur || 0.4, ...a });
      P1.arrow = (p0, p1, t, a = {}) => mark(() => {
        const [x0, y0] = pt(p0), [x1, y1] = pt(p1), bend = a.bend != null ? a.bend : 0.18;
        const Ld = Math.hypot(x1 - x0, y1 - y0) || 1, mx = (x0 + x1) / 2 - ((y1 - y0) / Ld) * bend * Ld, my = (y0 + y1) / 2 + ((x1 - x0) / Ld) * bend * Ld;
        const q = (u) => [(1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u * u * x1, (1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u * u * y1];
        const end = a.dashed ? 0.97 : 1, shaft = Array.from({ length: 26 }, (_, k) => q((k / 25) * end));
        const b = q(0.86), ang = Math.atan2(y1 - b[1], x1 - b[0]), hl = a.head || (kind === "pen" ? 30 : 20), sp = 0.48;
        const head = [[x1 - hl * Math.cos(ang + sp), y1 - hl * Math.sin(ang + sp)], [x1, y1], [x1 - hl * Math.cos(ang - sp), y1 - hl * Math.sin(ang - sp)]];
        if (!a.dashed) return [shaft, head];
        // a dashed pencil line: dashes ~10 px with gaps of 7-11 px (each its own short stroke), then the head
        const r = HF.rng(a.seed || 5), out = [], pts = Array.from({ length: 160 }, (_, k) => q((k / 159) * end));
        let acc = 0, on = true, cur = [pts[0]], target = 10;
        for (let k = 1; k < pts.length; k++) { acc += Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]);
          if (on) cur.push(pts[k]);
          if (acc >= target) { if (on && cur.length > 1) out.push(cur); on = !on; cur = [pts[k]]; acc = 0; target = on ? 9 + r() * 3 : 7 + r() * 4; } }
        out.push(head);
        return out; }, t, { dur: a.dur || (a.dashed ? 0.7 : TIME.arrow), ...a });
      // a pencil icon (ICONS) in a box of `size` px whose top-left is (x, y)
      P1.icon = (name, x, y, size, t, a = {}) => { const g = ICONS[name]; if (!g) throw new Error("HF.redline.icon: no icon " + name + " (" + Object.keys(ICONS).join(", ") + ")");
        return mark(() => g.map((s) => s.map(([u, v]) => [x + (u / 100) * size, y + (v / 100) * size])), t, { dur: a.dur || 0.9, size: a.size || (kind === "pencil" ? 2.6 : base), ...a }); };
      P1.clear = (t) => { marks.forEach((m) => { if (m.until == null || m.until > t) m.until = Q(t); }); return P1; };
      return P1;
    }
    const pen = (par, x = {}) => penOn(par, Object.assign({ kind: "pen" }, x));
    const pencil = (par, x = {}) => penOn(par, Object.assign({ kind: "pencil" }, x));

    // a handwritten margin note in the red felt-tip, written on left to right (a slower start, a pause between words)
    const note = (par, x, y, text, t, a = {}) => {
      const size = a.size || (REEL ? 80 : 72);
      const d = el(par, `left:${x}px;top:${y}px;font-size:${size}px;color:${a.color || C.red};rotate:${a.rotate != null ? a.rotate : -2}deg;${a.align === "right" ? "transform:translateX(-100%);" : ""}`, HF.esc(text), "hf-abs rl-hand");
      d.dataset.block = "1";
      const dur = a.dur || Math.min(1.6, 0.2 + text.length * 0.05);
      d.style.clipPath = "inset(-30% 100% -30% -4%)"; d.style.visibility = "hidden";
      tl.set(d, { visibility: "visible" }, Q(t));
      tl.fromTo(d, { clipPath: "inset(-30% 100% -30% -4%)" }, { clipPath: "inset(-30% -4% -30% -4%)", duration: dur, ease: "power1.inOut", immediateRender: false }, Q(t));
      if (a.until != null) tl.set(d, { visibility: "hidden" }, Q(a.until));
      if (a.to) pen(par).arrow(() => { const b = boxIn(d, par), x0 = a.align === "right" ? b[0] - b[2] : b[0], up = a.to[1] < b[1];    // from the edge facing the target
        return a.from || [x0 + b[2] * 0.5, up ? b[1] - 4 : b[1] + b[3] + 6]; }, a.to, t + dur * 0.8, { bend: a.bend != null ? a.bend : 0.2, until: a.until });
      if (o.sfx && o.sfx.pen && a.sfx !== false) K.sfx(o.sfx.pen, t, -24);
      return d;
    };

    // ---------------------------------------------------------------- screens as figures (HF.screen underneath)
    let figN = o.figStart || 1;
    const OFF = (o.chromeOff || []).slice();                                   // times the section label hides
    const fig = (par, x, y, w, h, fo = {}) => {
      const sd = HF.screen(K, par, { x, y, w, h, chrome: "none", img: fo.img, src: fo.src, srcW: fo.srcW || 1920, srcH: fo.srcH || 1080,
        start: fo.start, dur: fo.dur, mediaStart: fo.media, track: fo.track, fit: fo.fit });
      const box = sd.box;
      Object.assign(box.style, { borderRadius: "0px", boxShadow: fo.bleed ? "none" : `0 0 0 2px ${C.ink}`, background: "#fff", opacity: "1" });
      const num = fo.num != null ? fo.num : figN++, cap = fo.caption != null && !fo.bleed ? label(par, x, y + h + 18, `Fig. ${num} — ${fo.caption}`) : null;
      if (fo.bleed && fo.caption) { const tab = el(par, `left:${x + (REEL ? 60 : 120)}px;top:${y + h - (REEL ? 430 : 72)}px;padding:10px 14px 9px;background:${C.paper}`,
        `<span class="rl-lbl lbl">Fig. ${num} — ${HF.esc(fo.caption)}</span>`); tab.dataset.decor = "1"; sd.tab = tab; }
      const f = sd;
      f.num = num; f.cap = cap;
      f.place = (a, b, x2 = {}) => { if (fo.bleed) OFF.push([a, b != null ? b : 1e9]); [box, cap, sd.tab].filter(Boolean).forEach((e, i) => place(e, a + i * 0.06, b, x2)); return f; };
      // zoom only to read: ~1.6-2.2x, 1.1 s expo out, then a declared reading hold (until the next move or `until`)
      f.look = (t, r, x2 = {}) => { sd.zoom(t, r, { dur: x2.dur || TIME.zoomIn, ease: x2.ease || "expo.out", pad: x2.pad != null ? x2.pad : 0.08, max: x2.max || 3.2, min: x2.min });
        if (x2.until != null) HF.hold(t + (x2.dur || TIME.zoomIn), x2.until, "figure: " + (x2.why || "reading the zoom"));
        if (o.sfx && o.sfx.zoom) K.sfx(o.sfx.zoom, t, -26); return f; };
      f.back = (t, x2 = {}) => { sd.reset(t, { dur: x2.dur || TIME.zoomOut, ease: x2.ease || "power2.inOut" }); return f; };
      // the tracing sheet: laid over the (held) figure, it carries the red marks, then lifts off. so.window: a source
      // rect left clear while the rest of the sheet is frosted to paper (the focus without dimming to black)
      f.sheet = (a, b, so = {}) => {
        const vw = sd.vw, vh = sd.vh;
        const sh = el(sd.over, `left:0;top:0;width:${vw}px;height:${vh}px;background:${so.window ? "transparent" : C.sheet};box-shadow:inset 0 0 0 1px rgba(21,21,21,.16)`);
        sh.dataset.over = "1";
        if (so.window) {
          const win = el(sh, `left:0;top:0;width:10px;height:10px;box-shadow:0 0 0 4000px ${so.frost || C.frost}`);
          win.dataset.decor = "1";
          let set = false;
          sd.onCam((t) => { if (set || t < a - 0.05) return; const [wx, wy] = sd.map(a, so.window[0], so.window[1]), c = sd.cam(a), pad = so.pad != null ? so.pad : 10;
            Object.assign(win.style, { left: (wx - pad).toFixed(1) + "px", top: (wy - pad).toFixed(1) + "px", width: (so.window[2] * c.s + 2 * pad).toFixed(1) + "px", height: (so.window[3] * c.s + 2 * pad).toFixed(1) + "px" }); set = true; });
        }
        [[18, 18], [vw - 18, 18], [18, vh - 18], [vw - 18, vh - 18]].forEach(([cx, cy]) =>       // registration crosses, pencil
          el(sh, `left:${cx - 9}px;top:${cy - 9}px;width:18px;height:18px;background:linear-gradient(${C.pencil},${C.pencil}) center/18px 1.5px no-repeat,linear-gradient(${C.pencil},${C.pencil}) center/1.5px 18px no-repeat;opacity:.8`).dataset.decor = "1");
        K.show(sh, a - 0.01, b + TIME.sheetOut);
        tl.fromTo(sh, { x: Math.round(vw * 0.04), opacity: 0 }, { x: 0, opacity: 1, duration: TIME.sheetIn, ease: "power3.out", immediateRender: false }, Q(a));
        tl.to(sh, { x: -Math.round(vw * 0.03), opacity: 0, duration: TIME.sheetOut, ease: "power2.in", immediateRender: false }, Q(b));
        if (o.sfx && o.sfx.sheet) K.sfx(o.sfx.sheet, a, -26);
        HF.hold(a + TIME.sheetIn, b, "figure: marked on the sheet");
        const P2 = pen(sh);
        // marks in SOURCE px, mapped through the camera at the mark's time (the camera holds while the sheet is down)
        const toView = (r, t) => { const [vx, vy] = sd.map(t, r[0], r[1]), c = sd.cam(t); return [vx, vy, r[2] * c.s, r[3] * c.s]; };
        sh.mark = (kind, r, t, x2 = {}) => {
          if (kind === "arrow") return P2.arrow(() => sd.map(t, r[0][0], r[0][1]), () => sd.map(t, r[1][0], r[1][1]), t, x2);
          if (kind === "tick" || kind === "cross" || kind === "caret") return P2[kind](() => sd.map(t, r[0], r[1]), t, x2);
          return P2[kind](r, t, Object.assign({ lazy: () => toView(r, t) }, x2));
        };
        sh.note = (r, text, t, x2 = {}) => { const [vx, vy] = sd.map(t, r[0], r[1]); return note(sh, vx, vy, text, t, x2); };
        sh.pen = P2;
        f._sheets.push([a, b, sh]);
        return sh;
      };
      f._sheets = [];
      // privacy: a solid bar in the UI's own colour over source rects, moving with the camera (pixelation and blur can
      // be reversed; a bar can't). ro.color defaults to the paper; pass the UI's background (e.g. "#1f1f1f" on dark)
      f.redact = (rects, ro = {}) => { rects.forEach((r) => { const b = el(sd.over, `left:0;top:0;background:${ro.color || C.paper}`); b.dataset.decor = "1";
        sd.onCam((t, c) => { const on = (ro.from == null || t >= ro.from) && (ro.until == null || t <= ro.until), x0 = c.tx + r[0] * c.s, y0 = c.ty + r[1] * c.s;
          b.style.display = on ? "" : "none"; b.style.transform = `translate(${x0.toFixed(1)}px,${y0.toFixed(1)}px)`;
          b.style.width = (r[2] * c.s).toFixed(1) + "px"; b.style.height = (r[3] * c.s).toFixed(1) + "px"; }); }); return f; };
      f.click = (t, pt, x2 = {}) => { const P3 = pen(sd.over, { kind: "pen" }), rad = x2.r || (REEL ? 34 : 28);
        P3.circle(null, t, { lazy: () => { const [cx, cy] = sd.map(t, pt[0], pt[1]); return [cx - rad, cy - rad, 2 * rad, 2 * rad]; }, pad: 0, dur: 0.26, size: REEL ? 8 : 7, until: t + (x2.hold || 0.8) });
        if (o.sfx && o.sfx.click) K.sfx(o.sfx.click, t, -24); return f; };
      // a scroll of a tall capture at a reading speed (whole pixels a frame read cleanly: ~150 px/s of the source)
      f.scroll = (t, cy, x2 = {}) => { const c0 = sd.cam(t), d = x2.dur || Math.max(0.8, Math.abs(cy - c0.cy) / (x2.speed || 150));
        sd.pan(t, x2.cx != null ? x2.cx : c0.cx, cy, { dur: d, ease: x2.ease || "sine.inOut" }); if (x2.until != null) HF.hold(t + d, x2.until, "figure: scrolled to read"); return f; };
      // a mark on whichever sheet is down at t
      f.mark = (kind, r, t, x2 = {}) => { const s = f._sheets.find(([a, b]) => t >= a && t <= b);
        if (!s) throw new Error("fig.mark: no sheet is down at " + t + ": f.sheet(a, b) first");
        return s[2].mark(kind, r, t, x2); };
      return f;
    };

    // a taped print: a still (a tweet, a doc, a paper) held by two strips of tape, the one thing allowed to sit crooked
    const print = (par, src, x, y, w, h, po = {}) => {
      const d = el(par, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;background:#fff url(${src}) center/cover no-repeat;box-shadow:0 0 0 2px ${C.ink};rotate:${po.rot != null ? po.rot : -1.2}deg`);
      if (po.tape !== false) [[w * 0.12, -16, -4], [w * 0.74, -14, 3]].forEach(([tx, ty, r]) =>
        el(d, `left:${tx}px;top:${ty}px;width:${Math.round(w * 0.16)}px;height:34px;background:rgba(232,226,207,.78);rotate:${r}deg;box-shadow:inset 0 0 0 1px rgba(150,140,110,.18)`).dataset.decor = "1");
      return d;
    };

    // ---------------------------------------------------------------- the speaker: his real room, framed on the grid
    // shots [{ t, at, in: "cut" | "slide", zoom, label }]; at: full | left | right | pip | corner | top | bottom | off |
    // { x, y, w, h } (frame px). A window has square corners and a 2 px ink outline; zoom > 1 punches in (a jump cut
    // inside one framing takes 1.10-1.14). fo.face(t) -> [x, y] in the take's px keeps his face in the window
    const SLOTS = REEL
      ? { full: [0, 0, 1080, 1920], top: [60, 240, 960, 640], bottom: [60, 900, 960, 660], pip: [60, 1140, 360, 420], corner: [660, 240, 360, 420] }
      : { full: [0, 0, 1920, 1080], right: [1020, 120, 780, 840], left: [120, 120, 780, 840], pip: [1500, 600, 360, 360], corner: [1440, 60, 420, 420] };
    let faceRef = null;
    const face = (shots, fo = {}) => {
      const SRC = fo.src || (REEL ? [1080, 1920] : [1920, 1080]), FY = fo.faceY != null ? fo.faceY : REEL ? 0.38 : 0.42;   // 9:16: eyes high, clear of the app's UI
      const cam = st.cam, wrap = st.wrap, v = wrap.querySelector("video");
      Object.assign(cam.style, { overflow: "hidden", filter: "none", borderRadius: "0px", zIndex: "4", transformOrigin: "0 0" });
      Object.assign(wrap.style, { width: SRC[0] + "px", height: SRC[1] + "px", transformOrigin: "0 0" });
      if (v) Object.assign(v.style, { width: SRC[0] + "px", height: SRC[1] + "px", objectFit: "cover" });
      const ss = shots.slice().sort((p, q) => p.t - q.t);
      const rectOf = (s) => s.at === "off" ? null : Array.isArray(s.at) ? s.at : typeof s.at === "object" ? [s.at.x, s.at.y, s.at.w, s.at.h] : SLOTS[s.at];
      ss.forEach((s) => { if (s.at !== "off" && !rectOf(s)) throw new Error("R.face: no slot " + s.at + " (" + Object.keys(SLOTS).join(", ") + ")"); });
      const ease = (u) => 1 - Math.pow(1 - u, 3);
      const at = (t) => {
        let k = 0; while (k + 1 < ss.length && ss[k + 1].t <= t + 1e-6) k++;
        const s = ss[k], r1 = rectOf(s);
        if (!r1) return { r: SLOTS.full, op: 0, s };
        const p = ss[k - 1], r0 = p ? rectOf(p) : null;
        if (s.in === "slide" && r0 && t < s.t + TIME.place) { const u = ease((t - s.t) / TIME.place); return { r: r0.map((v0, i) => v0 + (r1[i] - v0) * u), op: 1, s, z0: p.zoom || 1 }; }
        return { r: r1, op: 1, s };
      };
      const capL = el(ROOT, "left:0;top:0;z-index:5;opacity:0", "", "hf-abs rl-lbl lbl");
      K.onFrame((t) => {
        const { r, op, s } = at(t), [x, y, w, h] = r, full = w >= WD - 1 && h >= HT - 1;
        cam.style.left = x.toFixed(1) + "px"; cam.style.top = y.toFixed(1) + "px"; cam.style.width = w.toFixed(1) + "px"; cam.style.height = h.toFixed(1) + "px";
        cam.style.opacity = op.toFixed(3); cam.style.transform = "none";
        cam.style.boxShadow = full || !op ? "none" : `0 0 0 2px ${C.ink}`;
        const f = (fo.face && fo.face(t)) || fo.at || (REEL ? [540, 760] : [960, 430]), z = s.zoom || 1;
        const sc = Math.max(w / SRC[0], h / SRC[1]) * z;
        let tx = w / 2 - f[0] * sc, ty = h * FY - f[1] * sc;
        tx = Math.min(0, Math.max(w - SRC[0] * sc, tx)); ty = Math.min(0, Math.max(h - SRC[1] * sc, ty));
        wrap.style.transform = `matrix(${sc.toFixed(5)},0,0,${sc.toFixed(5)},${tx.toFixed(2)},${ty.toFixed(2)})`;
        if (s.label && op && !full) { capL.textContent = s.label; capL.style.opacity = "1"; capL.style.left = x + "px"; capL.style.top = (y + h + 16) + "px"; } else capL.style.opacity = "0";
      });
      // where his face really is in the frame (the same crop as the frame above): precheck keeps text off it
      const faceRect = (t) => {
        const { r, op, s } = at(t), [x, y, w, h] = r;
        if (!op) return null;
        const f = (fo.face && fo.face(t)) || fo.at || (REEL ? [540, 760] : [960, 430]), sc = Math.max(w / SRC[0], h / SRC[1]) * (s.zoom || 1);
        let tx = w / 2 - f[0] * sc, ty = h * FY - f[1] * sc;
        tx = Math.min(0, Math.max(w - SRC[0] * sc, tx)); ty = Math.min(0, Math.max(h - SRC[1] * sc, ty));
        const hw = ((fo.head || (REEL ? 0.42 : 0.2)) * SRC[0] * sc) / 2, cx = x + tx + f[0] * sc, cy = y + ty + f[1] * sc;
        return { left: Math.max(x, cx - hw), right: Math.min(x + w, cx + hw), top: Math.max(y, cy - hw * 1.25), bottom: Math.min(y + h, cy + hw * 1.25) };
      };
      faceRef = { rect: (t) => { const { r, op } = at(t); return { cx: r[0] + r[2] / 2, cy: r[1] + r[3] / 2, w: r[2], h: r[3], rot: 0, op }; }, face: faceRect, shots: ss };
      window.__box = faceRef;                                                 // precheck: what the window covers
      window.__faceRect = faceRect;                                           // ... and the real face inside it
      // the window.__speaker contract (2026-10-22, kit v11; kit/hf/README "window.__speaker"; kit/qa/speaker.mjs): his
      // window on the page and his face in it; full (the whole page), corner (pip / corner: under 10 % of it), else card.
      // The frame holds its crop (no lens here): zoom is the slot's own, lens "".
      window.__speaker = (t) => {
        const { r, op, s } = at(t), [x, y, w, h] = r;
        if (!op) return { on: false, kind: "off", rect: null, face: null, zoom: null, lens: "" };
        const fr = faceRect(t), face = fr && fr.right > fr.left + 1 && fr.bottom > fr.top + 1 ? { x: fr.left, y: fr.top, w: fr.right - fr.left, h: fr.bottom - fr.top } : null;
        const kind = w >= WD - 1 && h >= HT - 1 ? "full" : (w * h) / (WD * HT) < 0.1 ? "corner" : "card";
        return { on: true, kind, rect: { x, y, w, h }, face, zoom: s.zoom || 1, lens: "" };
      };
      return faceRef;
    };
    // his cut-out standing on the page (kit/look/cutout.py's transparent WebM: the whole take frame, his room removed).
    // shots [{ t, x, s, foot }]: his face's centre goes to page x, the take is scaled by s, and the take's bottom edge
    // sits on `foot` (default the page's bottom). A new shot is a hard cut (use it on a join: it hides the jump), or
    // { slide: true } eases there in 0.28 s. fo.id: the <video> id; fo.src: the take's px; fo.at: his face in the take
    // (fo.face(t) for a track); fo.head: the head's width in take px (precheck keeps text off it). z 5: over BACK, under FRONT.
    const cutout = (shots, fo = {}) => {
      const v = document.getElementById(fo.id || "cutout");
      if (!v) throw new Error("R.cutout: no <video id=" + (fo.id || "cutout") + ">");
      const SRC = fo.src || [WD, HT], at0 = fo.at || [SRC[0] / 2, SRC[1] * 0.45], ss = shots.slice().sort((p, q) => p.t - q.t);
      const holder = el(ROOT, `left:0;top:0;width:${WD}px;height:${HT}px;z-index:${fo.z || 5};overflow:hidden;pointer-events:none`);
      holder.append(v);
      Object.assign(v.style, { position: "absolute", left: "0px", top: "0px", width: SRC[0] + "px", height: SRC[1] + "px", transformOrigin: "0 0" });
      const ease = (u) => 1 - Math.pow(1 - u, 3);
      const state = (t) => {
        let k = 0; while (k + 1 < ss.length && ss[k + 1].t <= t + 1e-6) k++;
        const c = ss[k], p = ss[k - 1];
        const g = (q) => ({ x: q.x, s: q.s || 1, foot: q.foot != null ? q.foot : HT, op: q.off ? 0 : 1 });
        let r = g(c);
        if (c.slide && p && t < c.t + TIME.place) { const a = g(p), u = ease((t - c.t) / TIME.place); r = { x: a.x + (r.x - a.x) * u, s: a.s + (r.s - a.s) * u, foot: a.foot + (r.foot - a.foot) * u, op: r.op }; }
        return r;
      };
      const place = (t) => { const r = state(t), f = (fo.face && fo.face(t)) || at0;
        return { tx: r.x - f[0] * r.s, ty: r.foot - SRC[1] * r.s, s: r.s, op: r.op, f }; };
      K.onFrame((t) => { const q = place(t);
        v.style.transform = `matrix(${q.s.toFixed(5)},0,0,${q.s.toFixed(5)},${q.tx.toFixed(2)},${q.ty.toFixed(2)})`; v.style.opacity = String(q.op); });
      window.__faceRect = (t) => { const q = place(t); if (!q.op) return null; const hw = ((fo.head || SRC[0] * 0.2) * q.s) / 2, cx = q.tx + q.f[0] * q.s, cy = q.ty + q.f[1] * q.s;
        return { left: cx - hw, right: cx + hw, top: cy - hw * 1.35, bottom: cy + hw * 1.15 }; };
      // window.__speaker (2026-10-22, the engine contract): the cut-out stands on the whole page (kind "full", no rect of
      // its own); its face as __faceRect has it
      window.__speaker = (t) => { const q = place(t);
        if (!q.op) return { on: false, kind: "off", rect: null, face: null, zoom: null, lens: "" };
        const hw = ((fo.head || SRC[0] * 0.2) * q.s) / 2, cx = q.tx + q.f[0] * q.s, cy = q.ty + q.f[1] * q.s;
        return { on: true, kind: "full", rect: null, face: { x: cx - hw, y: cy - hw * 1.35, w: 2 * hw, h: hw * 2.5 }, zoom: q.s, lens: "" }; };
      return { holder, video: v, place };
    };

    // the peek: his cut-out rising from the bottom edge under a headline (the thumbnail's move). Opt-in: the owner
    // found background removal rough on video (claude-makes-claude), so it is for title cards and stills first
    const peek = (par, a, b, po = {}) => {
      const w = po.w || (REEL ? 900 : 860), x = po.x != null ? po.x : (WD - w) / 2, h = po.h || Math.round(w * (po.ratio || 0.75));
      const tag = po.video ? `<video id="${po.video}" class="clip" src="${po.src}" muted playsinline style="width:100%;height:100%;object-fit:cover;object-position:50% 0"></video>`
        : `<img src="${po.src}" alt="" style="width:100%;height:100%;object-fit:cover;object-position:50% 0">`;
      const base = po.bottom != null ? po.bottom : REEL ? HT - 360 : HT;
      const clip = el(par, `left:0;top:0;width:${WD}px;height:${base}px;overflow:hidden`);
      const d = el(clip, `left:${x}px;top:${base - h}px;width:${w}px;height:${h}px`, tag);
      d.dataset.over = "1";
      K.show(clip, a - 0.01, b);
      if (base < HT) { const rule = el(par, `left:60px;top:${base}px;width:${WD - 120}px;height:2px;background:${C.ink}`); rule.dataset.decor = "1"; K.show(rule, a - 0.01, b); }
      tl.fromTo(d, { y: po.rise != null ? po.rise : 90 }, { y: 0, duration: 0.55, ease: "power3.out", immediateRender: false }, Q(a));
      return d;
    };

    // ---------------------------------------------------------------- cards (full frame, over everything)
    const LAYER = S.CHAP || S.TOP || S.FRONT;
    const full = (a, b, why) => { OFF.push([a, b]); const L = el(LAYER, `left:0;top:0;width:${WD}px;height:${HT}px;overflow:hidden`); L.dataset.over = "1";
      paper(L); K.show(L, a - 0.01, b); L._win = [a - 0.01, b]; HF.hold(a + 0.5, b, why || "card"); return L; };
    // a keyword / chapter card. co: kicker ("CHAPTER 02 / 05"), title (with *marks*), sub, icons [[name, x, y, size]],
    // links [[[x0, y0], [x1, y1]]] (dashed pencil arrows), peek { src, w }, mark ("underline" | "circle" | "double")
    const card = (a, b, co = {}) => {
      const L = full(a, b, co.why || "card: " + (co.title || ""));
      const top = co.y != null ? co.y : REEL ? 360 : 150, size = co.size || (REEL ? 120 : 150);
      if (co.kicker) label(L, co.align === "center" ? 0 : 120, top - 60, co.kicker, co.align === "center" ? `width:${WD}px;text-align:center` : "");
      const H = head(L, co.title || "", a, { x: co.align === "center" ? 0 : 120, y: top, size, align: co.align, w: co.align === "center" ? WD : undefined, mark: co.mark, markAt: co.markAt });
      if (co.sub) sub(L, co.sub, a, { x: co.align === "center" ? 0 : 120, y: top + size * (co.lines || 1) * 1.02 + 40, align: co.align, w: co.align === "center" ? WD : undefined });
      const pc = (co.icons || co.links) ? pencil(L) : null;
      (co.icons || []).forEach(([n, x, y, s], i) => pc.icon(n, x, y, s, a + 0.5 + i * 0.25));
      (co.links || []).forEach(([p0, p1], i) => pc.arrow(p0, p1, a + 0.9 + i * 0.25, { dashed: true }));
      if (co.peek) peek(L, a, b, co.peek);
      return Object.assign(L, { head: H });
    };
    const chapter = (t0, t1, num, title, subText, co = {}) => card(t0, t1, Object.assign({ kicker: `chapter ${num}${co.of ? " / " + co.of : ""}`, title, sub: subText, why: "chapter " + num }, co));
    // a number that matters, with where it came from (only his number, or one on screen with its source)
    const stat = (par, x, y, value, text, t, so = {}) => {
      const size = so.size || (REEL ? 220 : 260), mid = so.align === "center", al = mid ? `width:${WD}px;text-align:center;` : "", x0 = mid ? 0 : x;
      const v = el(par, `left:${x0}px;top:${y}px;font-size:${size}px;${al}`, mid ? `<span>${HF.esc(value)}</span>` : HF.esc(value), "hf-abs rl-h"); K.show(v, t, so.until);
      const l = el(par, `left:${mid ? 0 : x + 8}px;top:${y + size * 1.1}px;${al}font:700 ${REEL ? 50 : 44}px/1.2 Atkinson;color:${C.ink};white-space:nowrap`, HF.esc(text)); K.show(l, t, so.until);
      if (so.src) { const s = label(par, mid ? 0 : x + 8, y + size * 1.1 + 76, "source: " + so.src, al); K.show(s, t, so.until); }
      if (so.mark !== false) pen(par)[so.mark || "circle"](mid ? v.firstChild : v, (so.markAt != null ? so.markAt : t + 0.35), { pad: size * 0.08, until: so.until });
      return { v, l };
    };
    // up to 4 points, each on its spoken time; done: "tick" | "cross" | "strike" (a red mark), or none. lo.boxes: false
    // drops the square bullets (a tick in a box read as a web form, critic 2026-10-20): a bare hand tick marks the point
    const list = (par, x, y, items, lo = {}) => {
      if (items.length > 4) throw new Error("R.list: at most 4 points on screen (one idea at a time)");
      const gap = lo.gap || (REEL ? 150 : 120), size = lo.size || (REEL ? 54 : 50), out = [];
      const P2 = pen(par);
      items.forEach((it, i) => {
        const row = el(par, `left:${x + 70}px;top:${y + i * gap}px;font:700 ${size}px/1.15 Atkinson;color:${C.ink};white-space:nowrap`, HF.esc(it.text));
        row.dataset.block = "1";
        if (lo.boxes !== false) { const dot = el(par, `left:${x}px;top:${y + i * gap + size * 0.38}px;width:22px;height:22px;box-shadow:0 0 0 2px ${C.ink}`); dot.dataset.decor = "1"; place(dot, it.at, lo.until, { from: 16 }); }
        place(row, it.at, lo.until, { from: 16 });
        const mt = it.markAt != null ? it.markAt : it.at + 0.5;
        if (it.done === "tick") P2.tick([x + 16, y + i * gap + size * 0.55], mt, { until: lo.until, w: lo.boxes === false ? Math.round(size * 0.95) : 46 });
        else if (it.done === "cross") P2.cross([x + 11, y + i * gap + size * 0.5], mt, { until: lo.until, w: 34 });
        else if (it.done === "strike") P2.strike(row, mt, { until: lo.until });
        out.push(row);
      });
      return out;
    };
    // two columns divided by a pencil rule; the winner gets the red circle (his verdict only)
    const compare = (par, x, y, w, h, left, right, co = {}) => {
      const col = (c, cx) => {
        const hd = el(par, `left:${cx}px;top:${y}px;font-size:${co.size || 84}px`, HF.esc(c.title), "hf-abs rl-h"); place(hd, c.at, co.until, { from: 16 });
        const ly = y + (co.size || 84) * 1.2;
        (c.lines || []).forEach((ln, i) => { const r = el(par, `left:${cx}px;top:${ly + i * 52}px;font:500 42px/1.2 Atkinson;color:${C.ink2};white-space:nowrap`, HF.esc(ln)); place(r, c.at + 0.12 + i * 0.12, co.until, { from: 12 }); });
        if (c.img) { const fw = c.w || 600, fh = c.h || Math.round(fw * 0.5625);
          const f = fig(par, cx, ly + (c.lines || []).length * 52 + 36, fw, fh, { img: c.img, srcW: c.srcW, srcH: c.srcH, caption: c.caption, fit: c.fit });
          f.place(c.at + 0.2, co.until); if (c.look) f.look(c.at + 0.2, c.look, { dur: 0.01 }); }
        return hd;
      };
      const l = col(left, x), r = col(right, x + w / 2 + 40);
      pencil(par).line([[x + w / 2, y - 10], [x + w / 2 + 2, y + h]], Math.min(left.at, right.at) + 0.1, { dur: 0.5 });
      if (co.winner) pen(par).circle(co.winner === "left" ? l : r, co.winnerAt, { pad: 18 });
      return { l, r };
    };
    // a time skip: the old time struck through in red, the new one handwritten next to it
    const skip = (a, b, so = {}) => {
      const L = full(a, b, "time skip");
      const size = REEL ? 170 : 220, y = REEL ? 640 : 330, x = 120;
      if (so.kicker) label(L, x, y - 70, so.kicker);
      const t0 = el(L, `left:${x}px;top:${y}px;font-size:${size}px`, HF.esc(so.from || "02:10"), "hf-abs rl-h");
      pen(L).strike(t0, a + 0.35);
      note(L, REEL ? x + 40 : x + size * 2.9, REEL ? y + size * 1.15 : y + size * 0.1, so.to || "08:40", a + 0.65, { size: Math.round(size * 1.05), rotate: -4 });
      if (so.note) sub(L, so.note, a + 0.2, { x, y: y + size * (REEL ? 2.25 : 1.3) });
      return L;
    };
    // the end card: the two end-screen slots in pencil, the handles from kit/brand.json (HF.HANDLES)
    const endCard = (a, b, eo = {}) => {
      const L = full(a, b, "end card");
      head(L, eo.title || "see you in the next one", a, { x: 0, y: REEL ? 360 : 110, size: REEL ? 104 : 120, align: "center", w: WD, mark: false });
      const pc = pencil(L), slots = REEL ? [] : [[300, 290, 620, 310], [1000, 290, 620, 310]];
      slots.forEach(([x, y, w, h], i) => [[[x - 6, y], [x + w + 4, y]], [[x + w, y - 5], [x + w, y + h + 6]], [[x + w + 5, y + h], [x - 4, y + h]], [[x, y + h + 4], [x, y - 6]]]
        .forEach((sg, k) => pc.line(sg, a + 0.3 + i * 0.25 + k * 0.12, { dur: 0.16 })));
      if (eo.peek) peek(L, a, b, eo.peek);
      const hs = eo.handles || HF.HANDLES || [];
      const hd = el(L, `left:0;top:${REEL ? 640 : 640}px;width:${WD}px;display:flex;justify-content:center;gap:28px;flex-wrap:wrap`,
        hs.map((h) => `<span style="font:700 ${REEL ? 46 : 38}px/1 Atkinson;color:${C.ink};padding:16px 24px;box-shadow:0 0 0 2px ${C.ink};background:${C.paper}">${HF.esc(h)}</span>`).join(""), "hf-abs");
      place(hd, a + 0.5, null);
      return L;
    };

    // ---------------------------------------------------------------- chrome (16:9): the section label, on paper only
    if (!REEL && o.sections && o.sections.length) {
      const SEC = o.sections.slice().sort((p, q) => p[0] - q[0]);
      const sec = el(ROOT, "left:60px;top:28px;z-index:14", "", "hf-abs rl-lbl lbl"); sec.dataset.decor = "1";
      K.onFrame((t) => { const s = SEC.filter((x) => x[0] <= t + 1e-6).pop(); sec.textContent = s ? "§ " + s[1] : "";
        const fresh = s && t - s[0] < (o.sectionHold || 8);
        const r = faceRef ? faceRef.rect(t) : null, onFace = r && r.op > 0.5 && r.w >= WD - 1;
        const off = OFF.some(([p, q]) => t >= p - 0.02 && t < q);
        sec.style.opacity = onFace || off || !fresh ? "0" : "1"; });
    }

    // ---------------------------------------------------------------- 9:16 captions: a paper label, no karaoke colour
    const captions = (x = {}) => { if (!S.captions) throw new Error("R.captions: 9:16 only (HF.reel)");
      return S.captions(Object.assign({ cls: "rl-cap", base: C.ink, active: C.ink, max: 5 }, x)); };

    // a paper slip over the footage: his note in the red felt-tip on a torn scrap, one strip of tape (one every ~20 s
    // of talking head at most; never on the face: put it in a corner of his room)
    const slip = (x, y, text, t, so = {}) => {
      const size = so.size || (REEL ? 76 : 66), w = so.w || Math.round(text.length * size * 0.36 + 70), h = so.h || Math.round(size * 1.5);
      const d = el(S.FRONT, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;background:${C.paper};rotate:${so.rot != null ? so.rot : -1.5}deg;` +
        `clip-path:polygon(0 3%,8% 0,22% 2%,40% 0,61% 3%,79% 0,100% 2%,99% 97%,84% 100%,63% 97%,41% 100%,20% 98%,0 100%)`);
      d.dataset.over = "1";
      const tape = el(S.FRONT, `left:${x + w * 0.38}px;top:${y - 14}px;width:${Math.round(w * 0.24)}px;height:30px;background:rgba(232,226,207,.8);rotate:${(so.rot || -1.5) + 3}deg`); tape.dataset.decor = "1";
      [d, tape].forEach((e) => place(e, t, so.until, { from: 12 }));
      const n = note(d, 30, Math.round(h * 0.2), text, t + 0.2, { size, rotate: 0, until: so.until });
      return { d, n };
    };

    const R = { C, TIME, GRID, ICONS, SLOTS, snap, paper, page, place, label, head, sub, say, note, slip, pen, pencil, fig, print, face, peek,
      card, chapter, stat, list, compare, skip, endCard, captions, cutout, boxIn };
    return R;
  };
  HF.redline.PALETTE = PALETTE;
  HF.redline.TIME = TIME;
  HF.redline.ICONS = ICONS;
})(window);
