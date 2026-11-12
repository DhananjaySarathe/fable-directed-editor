/*
 * kit/hf/night.js: the "night build" frame for 16:9 films (2026-10-17, films/ai-portfolio). A dark developer desktop at
 * 4 AM instead of the pastel world: a near-black grid canvas with a cool monitor glow and a warm lamp, a broadcast-style
 * HUD (REC dot + the story's clock, the round, the timecode), one colour per contender, the real websites in dark
 * browser windows, and light / giant type painted on the wall BEHIND the speaker (his matte cut-out sits on top).
 * Built from the niche study (AI-vs-AI build videos: results on screen by ~10 s, settings shown for every model,
 * clock check-ins, a persistent score overlay, a quiet verdict) on top of HF.studio, so the box, type, layers,
 * focus/scoreboard and end card all still work.
 *
 *   const S = HF.studio(K, ROOT, st, { end, talk, palette: HF.night.PALETTE, sections });     // the frame, then:
 *   const N = HF.night(S, st, { cut: "cutout", clock: [[0, "04:00", "AM", "day 1"], ...], left: "yourchannel · ..." });
 *   N.light(a, b, { x, y, r, color, op })          a soft light on the wall behind him (source px of the A-roll)
 *   N.word(text, a, b, { x, y, size, grad, color, align })   giant type on the wall behind him
 *   N.dim(a, b, op)                                 the wall darker still (night), him untouched
 *   N.badge(id, size)                               html: the contender's real app icon + its name
 *   N.win(par, x, y, w, h, { src, start, dur, media, url, team })   a dark browser window playing a real recording
 *   N.card(par, x, y, w, h, html)                   a dark glass card
 *   N.skip(a, b, { from: ["04","00"], to: ["05","13"], note })     the full-frame time skip (rolling clock)
 *   N.stamp(par, text, x, y, t, { color, rot })     a verdict stamp (his words only)
 *   N.bars(par, x, y, w, { title, src, rows: [{ name, v, color }], at, max })   a small sourced bar chart
 *   N.chip(par, x, y, html, style)                  a dark pill
 *   N.theme(t, "claude")                            the room's light from t (themes: night, gpt, claude, argon, verdict;
 *                                                   o.themes adds more): the grid near each light takes its colour
 *   N.chapter(t0, t1, "02", "the launch", sub)      a chapter card (dark grid, mono number, the contenders' dots)
 *   N.pip(a, b, { video: "pip", face: (t) => [cx, cy, head_w], at: [[t, cx, cy, d], ...] })   a pickup camera as a
 *                                                   face circle that moves and resizes (each change eases)
 *
 * Rules: contender colours mean that contender everywhere (GPT green, Claude coral, Argon blue-violet, his current site
 * grey); real logos are the apps' own icons (never redrawn); every number on screen is his or sourced on screen; the
 * HUD is decoration (data-decor) and stays out of the safe area's middle; everything is a pure function of time.
 */
(function (root) {
  const HF = root.HF;
  if (!HF || !HF.studio) throw new Error("kit/hf/night.js needs studio.js first");

  const PALETTE = { ink: "#eef0f5", ink2: "#a7afbd", mute: "#7a8394", acc: "#f5c451", accTint: "rgba(245,196,81,.16)",
    ok: "#3ddc84", okSoft: "rgba(61,220,132,.16)", bad: "#ff5d5d", warm: "#f5c451", onVideo: "#ffd98a", paper: "#07090d",
    orb: "#f5c451", aurora: ["rgba(0,0,0,0)", "rgba(0,0,0,0)", "rgba(0,0,0,0)", "rgba(0,0,0,0)"] };
  const TEAM = {
    gpt: { name: "GPT-6 Astra", tool: "Codex", color: "#10a37f", icon: "assets/icons/chatgpt.png" },
    claude: { name: "Claude", tool: "Claude Code", color: "#d97757", icon: "assets/icons/claude.png" },
    argon: { name: "Gemini 4 Argon", tool: "Gemini app", color: "#8b7cf6", grad: "linear-gradient(92deg,#4c8df6 0%,#9b6cf2 100%)",
      icon: "assets/icons/gemini.png" },
    current: { name: "my current site", tool: "live", color: "#8a93a3", icon: null },
  };
  const CSS = `
    .nb { font-family: "Inter", sans-serif; color: #eef0f5; }
    .nb-mono { font-family: "JBMono", monospace; }
    .nb-card { position: absolute; border-radius: 22px; background: rgba(14,17,23,.92); overflow: hidden;
      box-shadow: 0 40px 110px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.08), inset 0 1px 0 rgba(255,255,255,.05); }
    .nb-chip { position: absolute; display: inline-flex; align-items: center; gap: 12px; padding: 12px 20px 12px 14px; border-radius: 999px;
      background: rgba(18,21,28,.92); box-shadow: 0 16px 40px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.09); white-space: nowrap;
      font: 700 26px/1 "Inter"; color: #eef0f5; }
    .nb-icon { width: 1em; height: 1em; border-radius: 0.24em; display: inline-block; flex: none; background-size: cover; background-position: center; }
    .nb-dot { width: .5em; height: .5em; border-radius: 50%; display: inline-block; flex: none; }
    .nb-lbl { font: 700 16px/1 "JBMono", monospace; letter-spacing: .16em; text-transform: uppercase; color: #7a8394; white-space: nowrap; }
    .hf-win.nbw { border-radius: 16px; background: #0b0e13; box-shadow: 0 50px 120px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.09); }
    .hf-win.nbw .bar { background: #12151c; border-bottom: 1px solid rgba(255,255,255,.07); height: 46px; }
    .hf-win.nbw .url { background: #0b0e13; color: #9aa3b2; border: 1px solid rgba(255,255,255,.08); font: 500 17px/26px "JBMono", monospace;
      padding: 0 14px; letter-spacing: 0; }
    .nb-stamp { position: absolute; font: 800 64px/1 "Inter"; letter-spacing: .02em; text-transform: uppercase; white-space: nowrap;
      padding: 12px 26px 14px; border: 7px solid currentColor; border-radius: 18px; background: rgba(7,9,13,.82); }
    .nb-word { position: absolute; white-space: nowrap; font: 800 300px/0.9 "Inter"; letter-spacing: -0.045em; }
    .nb-grad { -webkit-background-clip: text; background-clip: text; color: transparent; }`;

  HF.night = function (S, st, o = {}) {
    const { K, tl, Q, E, el, f1 } = S;
    const C = Object.assign({}, S.C, { bg: "#07090d", grid: "rgba(255,255,255,0.06)", surface: "#0e1117", line: "rgba(255,255,255,.08)" }, o.colors || {});
    if (!document.getElementById("hf-night-css")) { const s = document.createElement("style"); s.id = "hf-night-css"; s.textContent = CSS; document.head.append(s); }
    if (o.look !== false) HF.look("night", HF.lookOver(o.colors));             // the kit's components go dark glass too (S.ui, code, sketch...)
    const ROOT = S.WORLD.parentElement;
    const team = (id) => TEAM[id] || { name: id, color: C.acc };

    // ---------------------------------------------------------------- the world: a dark grid desktop, lit by the story
    // A base grid, then lights: a colour wash plus the same grid drawn in that colour and masked to the light's reach, so
    // the lines near a light take its colour (the owner's reference, 2026-10-17: an amber lamp low left, a monitor's blue
    // high right, the grid visible around the cards). A theme is a set of lights; N.theme(t, name) crossfades to another
    // one, so the room follows the subject: GPT green, Claude coral, Argon violet, the verdict split.
    const W0 = S.WORLD;
    W0.innerHTML = "";
    W0.style.background = C.bg;
    ROOT.style.background = C.bg;
    const mask = "radial-gradient(ellipse 72% 68% at 50% 46%, #000 34%, rgba(0,0,0,0) 100%)";
    const gridCss = (col) => `background-image:linear-gradient(${col} 1px, transparent 1px),linear-gradient(90deg, ${col} 1px, transparent 1px);background-size:60px 60px`;
    const grid = el(W0, `left:-60px;top:-60px;width:2040px;height:1200px;${gridCss(C.grid)};-webkit-mask-image:${mask};mask-image:${mask}`);
    const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a.toFixed(3)})`; };
    // [colour, x, y, reach, strength] in frame px
    const THEMES = Object.assign({
      night: [["#f5a623", 240, 940, 820, 1], ["#4c7dff", 1690, 190, 900, 1]],
      gpt: [["#f5a623", 240, 940, 700, 0.55], ["#10a37f", 1690, 200, 940, 1]],
      claude: [["#f5a623", 240, 940, 700, 0.55], ["#e07a55", 1690, 200, 940, 1]],
      argon: [["#9b6cf2", 250, 930, 800, 0.85], ["#4c8df6", 1690, 190, 940, 1]],
      verdict: [["#e07a55", 280, 560, 900, 1], ["#8b7cf6", 1650, 560, 860, 0.75]],
    }, o.themes || {});
    const LIT = {};
    Object.entries(THEMES).forEach(([name, lights]) => {
      const g = el(W0, "left:0;top:0;width:1920px;height:1080px;display:none");
      const parts = lights.map(([col, x, y, r, k], i) => {
        const wash = el(g, `left:${x - r}px;top:${y - r}px;width:${2 * r}px;height:${2 * r}px;border-radius:50%;background:radial-gradient(circle, ${rgba(col, 0.17 * k)} 0%, ${rgba(col, 0.06 * k)} 38%, ${rgba(col, 0)} 68%)`);
        const m = `radial-gradient(circle ${r}px at ${x}px ${y}px, #000 0%, rgba(0,0,0,.55) 45%, rgba(0,0,0,0) 100%)`;
        const reach = el(g, `left:0;top:0;width:1920px;height:1080px;overflow:hidden;-webkit-mask-image:${m};mask-image:${m}`);
        const lines = el(reach, `left:-60px;top:-60px;width:2040px;height:1200px;${gridCss(rgba(col, 0.32 * k))}`);
        return { wash, lines, ph: i * 1.7 + name.length };
      });
      LIT[name] = { g, parts };
    });
    const SCHED = [[-1e9, o.theme || "night"]], FADE = o.themeFade || 0.9;
    const theme = (t, name) => { if (!LIT[name]) throw new Error("HF.night.theme: no theme " + name); SCHED.push([t, name]); SCHED.sort((a, b) => a[0] - b[0]); };
    el(W0, "left:0;top:0;width:1920px;height:1080px;background:radial-gradient(ellipse 85% 80% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,.55) 100%)");
    K.onFrame((t) => {                                            // slow drift: a lived-in screen, never a slideshow
      const gx = (-(t * 4) % 60).toFixed(2), gy = (-(t * 2.5) % 60).toFixed(2);
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
          p.lines.style.transform = `translate(${gx}px,${gy}px)`;                 // the tinted lines sit on the base grid
          p.wash.style.transform = `translate(${(50 * Math.sin(t * 0.09 + p.ph)).toFixed(1)}px,${(34 * Math.cos(t * 0.07 + p.ph)).toFixed(1)}px)`;
        });
      });
    });

    // ---------------------------------------------------------------- HUD: REC + the story's clock, round, timecode
    S.CHROME.style.display = "none";
    const HUD = el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:14;pointer-events:none");
    HUD.dataset.decor = "1";
    const hudCol = "rgba(238,240,245,.72)";
    const tlb = el(HUD, `left:42px;top:32px;display:flex;align-items:center;gap:12px;font:700 18px/1 JBMono,monospace;letter-spacing:.12em;color:${hudCol};white-space:nowrap`,
      `<span style="width:12px;height:12px;border-radius:50%;background:#ff4d4d;box-shadow:0 0 12px rgba(255,77,77,.8)"></span><span>REC</span>` +
      `<span style="width:1px;height:16px;background:rgba(255,255,255,.25)"></span><span class="nbc" style="color:#fff">04:00</span><span class="nba">AM</span>` +
      `<span class="nbd" style="color:${C.acc}">DAY 1</span>`);
    const rec = tlb.firstChild, cTxt = tlb.querySelector(".nbc"), aTxt = tlb.querySelector(".nba"), dTxt = tlb.querySelector(".nbd");
    const CLOCK = (o.clock && o.clock.length ? o.clock : [[0, "04:00", "AM", "DAY 1"]]).slice().sort((a, b) => a[0] - b[0]);
    const SECT = (o.sections || [[0, ""]]).slice().sort((a, b) => a[0] - b[0]);
    const trb = el(HUD, `left:1276px;top:33px;width:600px;text-align:right;font:700 16px/1 JBMono,monospace;letter-spacing:.16em;text-transform:uppercase;color:${hudCol};white-space:nowrap`);
    const blb = el(HUD, `left:42px;top:1034px;font:700 15px/1 JBMono,monospace;letter-spacing:.16em;text-transform:uppercase;color:rgba(238,240,245,.5);white-space:nowrap`, HF.esc(o.left || ""));
    const brb = el(HUD, `left:1276px;top:1034px;width:600px;text-align:right;font:700 15px/1 JBMono,monospace;letter-spacing:.16em;color:rgba(238,240,245,.5);white-space:nowrap`);
    const bar = el(HUD, `left:0;top:1077px;width:1920px;height:3px;background:${C.acc};transform-origin:0 50%;opacity:.7`);
    const tc = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
    const TOT = (o.total || S.END);
    K.onFrame((t) => {
      const ck = CLOCK.filter((c) => c[0] <= t + 1e-6).pop() || CLOCK[0];
      cTxt.textContent = ck[1]; aTxt.textContent = ck[2] || ""; dTxt.textContent = ck[3] || "";
      rec.style.opacity = Math.floor(t * 1.25) % 2 ? "0.25" : "1";
      trb.textContent = (SECT.filter((s) => s[0] <= t + 1e-6).pop() || SECT[0])[1];
      brb.textContent = `${tc(t)} / ${tc(TOT)} · ${o.badge || "4K"}`;
      bar.style.transform = `scaleX(${(t / TOT).toFixed(5)})`;
    });
    const hud = (a, b, op = 0) => { tl.to(HUD, { opacity: op, duration: 0.2, immediateRender: false }, Q(a)); if (b != null) tl.to(HUD, { opacity: 1, duration: 0.25, immediateRender: false }, Q(b)); };

    // ---------------------------------------------------------------- behind him: a layer in the shot, his cut-out on top
    // without a cut-out (layout work before the matte exists) the layer still sits in the shot, but over him
    const BEHIND = el(st.wrap, "left:0;top:0;width:1920px;height:1080px;pointer-events:none;overflow:hidden");
    BEHIND.dataset.over = "1";
    if (o.cut) {
      const v = document.getElementById(o.cut);
      if (!v) throw new Error("HF.night: no <video id=" + o.cut + ">");
      v.style.cssText = "position:absolute;left:0;top:0;width:1920px;height:1080px";
      st.wrap.append(v);
    } else console.warn("HF.night: no cut-out: light and type behind him are drawn over him (layout work only)");
    const needBehind = () => BEHIND;
    // the wall darker still (the 4 AM room), him untouched (the cut-out is above)
    const dim = (a, b, op = 0.45, x = {}) => {
      if (!o.cut) return el(needBehind(), "display:none");       // no cut-out: darkening the wall would darken him too
      const d = el(needBehind(), `left:0;top:0;width:1920px;height:1080px;background:${x.bg || "radial-gradient(ellipse 80% 90% at 50% 40%, rgba(5,7,12,.55) 0%, rgba(5,7,12,1) 100%)"};opacity:0`);
      if (Q(a) <= 0) d.style.opacity = String(op);                  // on frame 1 already (no tween at time 0: kit/hf README)
      else tl.fromTo(d, { opacity: 0 }, { opacity: op, duration: x.fin != null ? x.fin : 0.35, ease: "none", immediateRender: false }, Q(a));
      if (b != null) tl.fromTo(d, { opacity: op }, { opacity: 0, duration: x.fout != null ? x.fout : 0.35, ease: "none", immediateRender: false }, Q(b - (x.fout != null ? x.fout : 0.35)));
      return d;
    };
    // a soft light on the wall (screen blend): colour, centre x/y and radius in the A-roll's 1920x1080 px
    const light = (a, b, x = {}) => {
      if (!o.cut) return el(needBehind(), "display:none");       // no cut-out: the light would tint him
      const r = x.r || 700, col = x.color || C.acc;
      const l = el(needBehind(), `left:${(x.x != null ? x.x : 960) - r}px;top:${(x.y != null ? x.y : 400) - r}px;width:${2 * r}px;height:${2 * r}px;border-radius:50%;` +
        `background:radial-gradient(circle, ${col} 0%, rgba(0,0,0,0) 64%);mix-blend-mode:screen;opacity:0;transform-origin:50% 50%`);
      const op = x.op != null ? x.op : 0.55, fin = x.fin != null ? x.fin : 0.28;
      tl.fromTo(l, { opacity: 0, scale: 0.7, x: x.dx || 0 }, { opacity: op, scale: 1, x: 0, duration: fin, ease: E.in, immediateRender: false }, Q(a));
      if (x.pulse) K.onFrame((t) => { if (t > a + fin && (b == null || t < b)) l.style.filter = `brightness(${(1 + 0.08 * Math.sin((t - a) * 3.1)).toFixed(3)})`; });
      if (b != null) tl.to(l, { opacity: 0, duration: 0.3, ease: "none", immediateRender: false }, Q(b - 0.3));
      return l;
    };
    // giant type on the wall behind him: a slam on the snappy spring, out with a short fade
    const word = (text, a, b, x = {}) => {
      const size = x.size || 300;
      const w = el(x.parent || needBehind(), `left:${x.x != null ? x.x : 960}px;top:${x.y != null ? x.y : 120}px;font-size:${size}px;transform-origin:${x.origin || "50% 60%"};` +
        `${x.align === "right" ? "transform:translateX(-100%);" : x.align === "left" ? "" : "transform:translateX(-50%);"}`, "", "nb-word");
      const inner = document.createElement("span");
      inner.textContent = text;
      inner.style.display = "inline-block";
      if (x.grad) { inner.className = "nb-grad"; inner.style.backgroundImage = x.grad; } else inner.style.color = x.color || "#fff";
      if (x.font) w.style.fontFamily = x.font;
      if (x.weight) w.style.fontWeight = x.weight;
      if (x.italic) w.style.fontStyle = "italic";
      if (x.track != null) w.style.letterSpacing = x.track;
      w.append(inner);
      K.show(w, a - 0.02, b);
      const sp = HF.spring(HF.SPRING.snappy);
      tl.fromTo(inner, { opacity: 0 }, { opacity: x.op != null ? x.op : 1, duration: 2 * f1, ease: "none", immediateRender: false }, Q(a));
      tl.fromTo(inner, { scale: x.from || 1.35, filter: "blur(14px)" }, { scale: 1, filter: "blur(0px)", duration: sp.duration, ease: sp.ease, immediateRender: false }, Q(a));
      if (x.sfx !== null) K.sfx(x.sfx || "impact/impact__short-bass-hit__mixkit-2299", a, x.db != null ? x.db : -15, true);
      if (b != null) tl.to(inner, { opacity: 0, scale: 0.96, duration: 0.16, ease: E.out, immediateRender: false }, Q(b - 0.16));
      return w;
    };

    // ---------------------------------------------------------------- small pieces
    const icon = (id, s = 32) => { const m = team(id); return m.icon ? `<span class="nb-icon" style="width:${s}px;height:${s}px;background-image:url(${m.icon})"></span>`
      : `<span class="nb-dot" style="width:${Math.round(s * 0.5)}px;height:${Math.round(s * 0.5)}px;background:${m.color}"></span>`; };
    const badge = (id, s = 32, sub = true) => { const m = team(id);
      return `${icon(id, s)}<span style="display:inline-flex;flex-direction:column;gap:6px"><span style="font:800 ${Math.round(s * 0.8)}px/1 Inter;color:#fff">${HF.esc(m.name)}</span>` +
        (sub && m.tool ? `<span class="nb-mono" style="font:500 ${Math.round(s * 0.5)}px/1 JBMono;color:${m.color}">${HF.esc(m.tool)}</span>` : "") + `</span>`; };
    const chip = (par, x, y, html, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, html, "nb-chip");
    const card = (par, x, y, w, h, html = "", style = "") => el(par, `left:${x}px;top:${y}px;width:${w}px;height:${h}px;${style}`, html, "nb-card nb");
    const lbl = (par, x, y, text, style = "") => el(par, `left:${x}px;top:${y}px;${style}`, HF.esc(text), "hf-abs nb-lbl lbl");

    // a dark browser window playing a real recording (kit/web/record.mjs: 3840x2160 by default). o.team draws its label
    const win = (par, x, y, w, h, wo = {}) => {
      const sd = HF.screen(K, par, { x, y, w, h, src: wo.src, start: wo.start || 0, dur: wo.dur || 10, mediaStart: wo.media || 0,
        srcW: wo.srcW || 3840, srcH: wo.srcH || 2160, url: wo.url || "", dark: true, track: wo.track, fit: wo.fit });
      sd.box.classList.add("nbw");
      sd.box.querySelector(".bar").dataset.decor = "1";                   // the title bar: chrome, not evidence
      if (wo.team) {
        const m = team(wo.team);
        sd.box.style.boxShadow = `0 50px 120px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.09), 0 0 0 ${wo.ring || 0}px ${m.color}`;
        const tag = el(sd.box.querySelector(".bar"), `right:14px;top:8px;display:flex;align-items:center;gap:10px;padding:5px 12px 5px 6px;border-radius:9px;` +
          `background:rgba(255,255,255,.06);font:700 17px/1 Inter;color:#fff;white-space:nowrap;z-index:3`, `${icon(wo.team, 24)}${HF.esc(wo.label || m.name)}`);
        sd.tag = tag;
      }
      return sd;
    };

    // the full-frame time skip: a rolling clock (digits count through like an odometer), the note under it
    const skip = (a, b, so = {}) => {
      const L = el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:12;overflow:hidden;clip-path:inset(0 0 0 100%)");
      L.dataset.over = "1";                                                   // a full-frame card: it covers the face
      el(L, `background:${C.bg}`, "", "hf-fill");
      const g = el(L, `left:0;top:0;width:2040px;height:1200px;background-image:linear-gradient(${C.grid} 1px, transparent 1px),linear-gradient(90deg, ${C.grid} 1px, transparent 1px);background-size:60px 60px;-webkit-mask-image:${mask};mask-image:${mask}`);
      el(L, "left:460px;top:140px;width:1000px;height:1000px;border-radius:50%;background:radial-gradient(circle, rgba(245,196,81,.12) 0%, rgba(245,196,81,0) 62%)");
      const from = so.from || ["04", "00"], to = so.to || ["05", "13"];
      const digits = (from.join("") + to.join("")).length === 8 ? [0, 1, 2, 3] : [];
      const box = el(L, "left:0;top:330px;width:1920px;display:flex;justify-content:center;align-items:flex-end;gap:6px;font:800 260px/1 JBMono,monospace;color:#fff;letter-spacing:-.02em");
      const cols = [];
      const f2 = from.join(""), t2 = to.join("");
      [0, 1, ":", 2, 3].forEach((k) => {
        if (k === ":") { el(box, "position:relative;width:110px;text-align:center;color:" + C.acc, ":", ""); return; }
        const col = el(box, "position:relative;height:260px;width:158px;overflow:hidden", "", "");
        const d0 = +f2[k], d1 = +t2[k];
        // each column counts forward to its digit; the last one spins a full turn on the way (the time is passing),
        // a column whose digit doesn't change stays put
        const seq = [d0];
        if (d0 !== d1 || k === 3) for (let v = (d0 + 1) % 10, g = 0; g < 30; v = (v + 1) % 10, g++) { seq.push(v); if (v === d1 && (k !== 3 || seq.length > 10)) break; }
        const strip = el(col, "position:absolute;left:0;top:0;width:158px;text-align:center", seq.map((v) => `<div style="height:260px">${v}</div>`).join(""), "");
        cols.push({ strip, n: seq.length });
      });
      const ap = el(L, `left:0;top:610px;width:1920px;text-align:center;font:700 40px/1 JBMono,monospace;letter-spacing:.3em;color:${C.ink2}`, so.ampm || "AM");
      const note = el(L, `left:0;top:700px;width:1920px;text-align:center;font:800 64px/1 Inter;color:#fff;letter-spacing:-.02em`, HF.esc(so.note || ""));
      const sub = el(L, `left:0;top:792px;width:1920px;text-align:center;font:500 32px/1 JBMono,monospace;color:${C.mute}`, HF.esc(so.sub || ""));
      tl.to(L, { clipPath: "inset(0 0 0 0%)", duration: 0.3, ease: E.move, immediateRender: false }, Q(a));
      const r0 = a + 0.3, rd = Math.max(0.6, (b - a) - 1.1);
      cols.forEach((c, i) => tl.fromTo(c.strip, { y: 0 }, { y: -260 * (c.n - 1), duration: rd, ease: "power3.inOut", immediateRender: false }, Q(r0 + i * 0.04)));
      tl.fromTo([note, sub], { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.45, ease: E.in, stagger: 0.08, immediateRender: false }, Q(r0 + rd * 0.55));
      tl.fromTo([box, ap], { scale: 1 }, { scale: 1.04, duration: b - a, ease: "none", immediateRender: false }, Q(a));
      K.onFrame((t) => { if (t > a - 0.1 && t < b + 0.1) g.style.transform = `translate(${(-(t * 22) % 60).toFixed(2)}px,0)`; });
      tl.to(L, { clipPath: "inset(0 100% 0 0%)", duration: 0.28, ease: E.move, immediateRender: false }, Q(b));
      K.sfx("whoosh/whoosh__cinematic-whoosh-fast-transition__mixkit-1492", a + 0.15, -19);
      K.sfx("transition/transition__fast-tape-rewind-cinematic-transition__mixkit-1092", r0 + 0.05, -20, true);
      K.sfx("impact/impact__short-bass-hit__mixkit-2299", r0 + rd, -16, true);
      K.sfx("whoosh/whoosh__air-woosh__mixkit-1489", b + 0.14, -23);
      return L;
    };

    // a verdict stamp: his words, slammed on
    const stamp = (par, text, x, y, t, so = {}) => {
      const s = el(par, `left:${x}px;top:${y}px;color:${so.color || C.acc};transform:rotate(${so.rot != null ? so.rot : -7}deg);font-size:${so.size || 64}px`, HF.esc(text), "nb-stamp");
      const sp = HF.spring(HF.SPRING.snappy);
      tl.fromTo(s, { opacity: 0 }, { opacity: 1, duration: 0.05, immediateRender: true }, Q(t));
      tl.fromTo(s, { scale: 2.0 }, { scale: 1, duration: sp.duration, ease: sp.ease, immediateRender: true }, Q(t));
      K.sfx("impact/impact__exciting-fast-hit__mixkit-2180", t + 0.05, -15, true);
      if (so.until) tl.to(s, { opacity: 0, duration: 0.2, immediateRender: false }, Q(so.until - 0.2));
      return s;
    };

    // a small bar chart with its source on it (values grow from the baseline with the count, one ease)
    const bars = (par, x, y, w, bo = {}) => {
      const rows = bo.rows || [], max = bo.max || 100, rh = bo.rowH || 74;
      const c = card(par, x, y, w, 96 + rows.length * rh + 54, "");
      el(c, "left:30px;top:26px;font:800 34px/1 Inter;color:#fff", HF.esc(bo.title || ""));
      el(c, `left:30px;top:${96 + rows.length * rh + 14}px;font:500 18px/1 JBMono,monospace;color:${C.mute}`, HF.esc(bo.src || ""), "hf-abs lbl");
      const at = bo.at || 0, out = [];
      rows.forEach((r, i) => {
        const yy = 92 + i * rh;
        el(c, `left:30px;top:${yy + 4}px;width:250px;font:700 32px/1 Inter;color:${C.ink2};white-space:nowrap`, HF.esc(r.name));
        const tw = w - 30 - 330 - 130;
        el(c, `left:330px;top:${yy}px;width:${tw}px;height:40px;border-radius:10px;background:rgba(255,255,255,.05)`);
        const b = el(c, `left:330px;top:${yy}px;width:${tw * r.v / max}px;height:40px;border-radius:10px;background:${r.grad || r.color};transform-origin:0 50%`);
        const n = el(c, `left:${330 + tw + 20}px;top:${yy + 4}px;font:800 32px/1 JBMono,monospace;color:#fff`, "0");
        const t0 = at + 0.1 + i * 0.08;
        tl.fromTo(b, { scaleX: 0 }, { scaleX: 1, duration: 0.9, ease: "power3.out", immediateRender: true }, Q(t0));
        K.countUp(n, 0, r.v, t0, 0.9, (v) => v.toFixed(1));
        out.push({ bar: b, num: n });
      });
      return { card: c, rows: out };
    };

    // a chapter card in the night look: the dark grid, a big mono number, the title, a sub line, one dot per contender.
    // Wipes in and out like the time skip; land the next scene's first element as it leaves (t1)
    const chapter = (t0, t1, num, title, sub = "", co = {}) => {
      const L = el(ROOT, "left:0;top:0;width:1920px;height:1080px;z-index:12;overflow:hidden;clip-path:inset(0 0 0 100%)");
      L.dataset.over = "1";                                                   // a full-frame card: it covers the face
      el(L, `background:${C.bg}`, "", "hf-fill");
      const g = el(L, `left:0;top:0;width:2040px;height:1200px;background-image:linear-gradient(${C.grid} 1px, transparent 1px),linear-gradient(90deg, ${C.grid} 1px, transparent 1px);background-size:60px 60px;-webkit-mask-image:${mask};mask-image:${mask}`);
      const glow = el(L, `left:-200px;top:-260px;width:1400px;height:1400px;border-radius:50%;background:radial-gradient(circle, ${co.glow || "rgba(245,196,81,.13)"} 0%, rgba(0,0,0,0) 62%)`);
      if (co.kicker) el(L, `left:150px;top:318px;font:700 22px/1 JBMono,monospace;letter-spacing:.3em;color:${C.acc};white-space:nowrap`, HF.esc(co.kicker), "hf-abs lbl");
      const n = el(L, `left:136px;top:360px;font:800 300px/1 JBMono,monospace;letter-spacing:-.04em;color:${C.acc}`, HF.esc(num));
      const tsize = co.titleSize || Math.min(120, Math.floor(1060 / (0.52 * Math.max(1, title.length))));
      const ti = el(L, `left:720px;top:${430 + (120 - tsize) * 0.5}px;font:800 ${tsize}px/1 Inter;letter-spacing:-.03em;color:#fff;white-space:nowrap`, HF.esc(title));
      const su = el(L, `left:724px;top:582px;font:500 34px/1.25 JBMono,monospace;color:${C.ink2};white-space:nowrap`, HF.esc(sub));
      const dots = el(L, "left:150px;top:742px;display:flex;gap:22px", (co.teams || ["gpt", "claude", "argon"]).map((id) => co.names
        ? `<span style="display:inline-flex;align-items:center;gap:10px;font:700 34px/1 Inter;color:${C.ink2}">${icon(id, 40)}${HF.esc(team(id).name)}</span>` : icon(id, 52)).join(""));
      tl.to(L, { clipPath: "inset(0 0 0 0%)", duration: 0.3, ease: E.move, immediateRender: false }, Q(t0));
      tl.fromTo(n, { x: 80 }, { x: 0, duration: 0.85, ease: E.in, immediateRender: false }, Q(t0));
      tl.fromTo([ti, su, dots], { x: 140, opacity: 0 }, { x: 0, opacity: 1, duration: 0.8, ease: E.in, stagger: 0.05, immediateRender: false }, Q(t0 + 0.04));
      const hold = t1 - t0 + 0.3;                                             // it drifts while it holds (never a still)
      tl.fromTo(glow, { x: 0, y: 0 }, { x: 160, y: 80, duration: hold, ease: "none", immediateRender: false }, Q(t0));
      tl.fromTo([n, ti, su], { scale: 1 }, { scale: 1.035, duration: hold, ease: "none", immediateRender: false }, Q(t0));
      K.onFrame((t) => { if (t > t0 - 0.1 && t < t1 + 0.4) g.style.transform = `translate(${(-(t * 16) % 60).toFixed(2)}px,0)`; });
      tl.to(L, { clipPath: "inset(0 100% 0 0%)", duration: 0.28, ease: E.move, immediateRender: false }, Q(t1));
      K.sfx("whoosh/whoosh__cinematic-whoosh-fast-transition__mixkit-1492", t0 + 0.15, -19);
      K.sfx("impact/impact__short-bass-hit__mixkit-2299", t0 + 0.3, -17);
      K.sfx("whoosh/whoosh__air-woosh__mixkit-1489", t1 + 0.14, -23);
      return L;
    };

    // the pickup camera as a face circle: a <video> (id po.video) of a 1080p track, its face kept at the circle's centre.
    // po.face(t) -> [cx, cy, head_w] in the track's 1920x1080 px; po.at: [[t, cx, cy, d], ...] where the circle is (each
    // change eases over po.move s); po.head: the head's share of the diameter. Shown from a to b (fades 0.25 s)
    const pip = (a, b, po = {}) => {
      const v = document.getElementById(po.video || "pip");
      if (!v) throw new Error("HF.night.pip: no <video id=" + (po.video || "pip") + ">");
      const at = (po.at || [[a, 1710, 850, 300]]).slice().sort((p, q) => p[0] - q[0]);
      const ring = el(ROOT, `left:0;top:0;width:300px;height:300px;z-index:${po.z || 5};border-radius:50%;overflow:hidden;background:#0b0e13;` +
        `box-shadow:0 30px 80px rgba(0,0,0,.55),0 0 0 3px rgba(255,255,255,.16);opacity:0`);
      ring.dataset.face = "1";
      v.style.cssText = "position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0";
      ring.append(v);
      // a soft edge inside the circle: a bright room (take 3's white cupboards) sits down into the dark world
      const vig = el(ring, `left:0;top:0;width:100%;height:100%;border-radius:50%;background:radial-gradient(circle at 50% 44%, rgba(7,9,13,0) 50%, rgba(7,9,13,${po.vignette != null ? po.vignette : 0.5}) 100%)`);
      vig.dataset.decor = "1";
      const mv = po.move || 0.45, head = po.head || 0.5, ez = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
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
        const o = t < a || t > b + 0.25 ? 0 : Math.min(1, (t - a) / 0.25, (b + 0.25 - t) / 0.25);
        ring.style.opacity = o.toFixed(3);
      });
      return ring;
    };

    const N = { C, TEAM, team, HUD, BEHIND, hud, dim, light, word, icon, badge, chip, card, lbl, win, skip, stamp, bars, chapter, pip, theme, THEMES };
    return N;
  };
  HF.night.PALETTE = PALETTE;
  HF.night.TEAM = TEAM;
})(window);
