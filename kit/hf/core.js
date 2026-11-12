/* kit/hf/core.js — the shared motion vocabulary for paper-studio HyperFrames compositions.
 *
 *   const K = HF.kit({ tl, id: "myfilm", width: 1920, height: 1080, words: D.words, pieces: D.pieces });
 *   K.enter(el, t)  K.exit(el, t)  K.rise(K.words(parent, "Big *idea", style).ws, [t])  K.typeText(el, "...", t, 20)
 *   ... components (scenes.js, diagram.js, screen.js, code.js) take K as their first argument ...
 *   K.finish(totalSeconds);           // once, at the end: installs the per-frame driver and registers the timeline
 *
 * Rules baked in (preset_paper_studio): entrances 0.6 s power3.out with a short travel, exits 0.35 s power2.in, text
 * rises word by word in a mask, no bounces or glitches, every time quantised to the frame. Anything whose state is a
 * function of time (camera moves, flowing dots, cursors) registers K.onFrame(fn) and is redrawn from one linear
 * proxy tween, so seeking to any frame gives the same picture.
 */
(function (root) {
  const HF = root.HF || (root.HF = {});
  HF.version = "1.0.0";
  HF.C = { paper: "#f3eee6", card: "#ffffff", ink: "#1b1815", ink2: "#4a443d", mute: "#8a8178", acc: "#e2562b", accTint: "#fbe4dc",
    ok: "#2f8a5b", okTint: "#dcefe3", bad: "#c23b22", badTint: "#f7dcd5", line: "rgba(27,24,21,.1)" };
  // ---------------------------------------------------------------- looks (2026-10-20, kit/refs/AUDIT_2026-10-20.md §6)
  // One token set per look. A frame applies its look once (HF.studio / HF.reel: pastel_box, HF.canvas, HF.redline,
  // HF.night / HF.nightReel, HF.paper; none = paper_studio) and every component reads the tokens at call time:
  // HF.C (colours), HF.F (fonts) and the CSS variables (--paper, --card, --ink, --f-body, ...). So a stickman, a sketch,
  // a UI card or a code window drawn in a redline or night film takes that film's ink, surfaces and type instead of the
  // look it was born in. HF.C is updated in place (modules hold a reference to it).
  //   C: paper (the world), card (a surface), sunk (a row or bar inside a card), line (hairlines), ink (titles), text
  //      (body copy), ink2, sub, mute (secondary to faint), acc/accTint, ok/okTint, bad/badTint, warm, onFill (text or a
  //      tick on an acc/ok/bad fill: white, but dark on night's bright fills), onVideo (an
  //      accent over footage), plate (behind type over busy pictures), shadow (a card), shadowSoft (a chip), cardLine,
  //      e1 / e2 / e3 (elevation by level: a chip, a card, the scene's hero object; 2026-10-22, CSS --e1..--e3)
  //   F: body (UI text), mono (labels), code (code windows: a narrow mono in every look, or lines overflow), display + displayWeight + displayTrack (say/line type, headlines), hand
  //      (marker notes, sketches), stamp (stamps, slams)
  //   dark: light ink on a dark world; code: the default code-window theme
  //   stage: HF.canvas's own surfaces (canvas_studio, whitespace; below the table), read as HF.LOOK.stage
  // Seven looks: paper_studio, pastel_box, canvas_studio, redline, night, paper_collage, whitespace (2026-10-22, the
  // white page: kit/presets/whitespace; HF.canvas(K, ROOT, { look: "whitespace" }), HF.studio / HF.reel { look }).
  // Font names are single-quoted: components put the tokens inside style="..." attributes in innerHTML.
  const INTER = "'Inter', sans-serif", JB = "'JBMono', monospace", SERIF = "'InstrumentSerif', serif", HAND = "'Excalifont', 'Caveat', cursive";
  HF.LOOKS = {
    paper_studio: { dark: false, code: "light",
      C: { paper: "#f3eee6", card: "#ffffff", sunk: "#f6f3ee", line: "rgba(27,24,21,.1)", ink: "#1b1815", text: "#2d2823", ink2: "#4a443d", sub: "#6b635a",
        mute: "#8a8178", acc: "#e2562b", accTint: "#fbe4dc", ok: "#2f8a5b", okTint: "#dcefe3", bad: "#c23b22", badTint: "#f7dcd5", warm: "#e2562b",
        onFill: "#ffffff", onVideo: "#ffd9c7", plate: "rgba(255,255,255,.94)", shadow: "0 1px 0 rgba(27,24,21,.04), 0 22px 60px rgba(60,40,20,.14)",
        shadowSoft: "0 12px 34px rgba(60,40,20,.14)", cardLine: "rgba(27,24,21,.06)" },
      F: { code: JB, body: INTER, mono: JB, display: SERIF, displayWeight: 400, displayTrack: "-0.01em", hand: HAND, stamp: "'Anton', sans-serif" } },
    pastel_box: { dark: false, code: "light",
      C: { paper: "#f6f1ec", card: "#ffffff", sunk: "#f7f5f2", line: "rgba(40,24,90,.08)", ink: "#17161f", text: "#2a2935", ink2: "#4d4b5c", sub: "#6b6a78",
        mute: "#8e8ba0", acc: "#4f3be0", accTint: "#ece9ff", ok: "#16a34a", okTint: "#dcf5e5", bad: "#d6455d", badTint: "#fbe2e6", warm: "#e2562b",
        onFill: "#ffffff", onVideo: "#ffc9ad", plate: "rgba(255,255,255,.94)", shadow: "0 40px 90px rgba(40,24,90,.18), 0 10px 26px rgba(40,24,90,.10), 0 0 0 1px rgba(40,24,90,.06)",
        shadowSoft: "0 18px 40px rgba(40,24,90,.14), 0 0 0 1px rgba(40,24,90,.06)", cardLine: "rgba(40,24,90,.06)" },
      F: { code: JB, body: INTER, mono: JB, display: SERIF, displayWeight: 400, displayTrack: "-0.012em", hand: HAND, stamp: "'Anton', sans-serif" } },
    canvas_studio: { dark: false, code: "light",
      C: { paper: "#F6F3EE", card: "#ffffff", sunk: "#F4F4F7", line: "rgba(20,20,40,.08)", ink: "#16161C", text: "#2a2a33", ink2: "#4A4A55", sub: "#6b6b75",
        mute: "#8a8a96", acc: "#6C5CE7", accTint: "#E7E1FF", ok: "#16a34a", okTint: "#D9F2E6", bad: "#E0435A", badTint: "#FFE3E8", warm: "#FF4D6D",
        onFill: "#ffffff", onVideo: "#FFE3D6", plate: "rgba(255,255,255,.92)", shadow: "0 0 0 1px rgba(20,20,40,.07), 0 30px 70px rgba(30,30,60,.14), 0 6px 18px rgba(30,30,60,.07)",
        shadowSoft: "0 0 0 1px rgba(20,20,40,.08), 0 10px 30px rgba(30,30,60,.12)", cardLine: "rgba(20,20,40,.07)" },
      F: { code: JB, body: "'Atkinson', sans-serif", mono: JB, display: "'Schibsted', sans-serif", displayWeight: 800, displayTrack: "-0.02em",
        hand: "'Caveat', cursive", stamp: "'ArchivoCond', sans-serif" } },
    redline: { dark: false, code: "light",
      C: { paper: "#FBFAF6", card: "#ffffff", sunk: "#F4F3EE", line: "rgba(21,21,21,.12)", ink: "#151515", text: "#151515", ink2: "#3D3B37", sub: "#6F6D68",
        mute: "#8F8C85", acc: "#D7261E", accTint: "rgba(215,38,30,.12)", ok: "#2f7a4b", okTint: "#e3f1e7", bad: "#D7261E", badTint: "rgba(215,38,30,.12)",
        warm: "#D7261E", onFill: "#ffffff", onVideo: "#FFE45C", plate: "rgba(251,250,246,.94)", shadow: "0 0 0 2px rgba(21,21,21,.85)", shadowSoft: "0 0 0 2px rgba(21,21,21,.85)",
        cardLine: "rgba(21,21,21,.85)" },
      F: { code: JB, body: "'Atkinson', sans-serif", mono: "'Martian', monospace", display: "'Schibsted', sans-serif", displayWeight: 800, displayTrack: "-0.025em",
        hand: "'NanumPen', cursive", stamp: "'Schibsted', sans-serif" } },
    night: { dark: true, code: "dark",
      C: { paper: "#07090d", card: "rgba(14,17,23,.92)", sunk: "rgba(255,255,255,.05)", line: "rgba(255,255,255,.08)", ink: "#eef0f5", text: "#d9dee7",
        ink2: "#a7afbd", sub: "#8a93a3", mute: "#7a8394", acc: "#f5c451", accTint: "rgba(245,196,81,.16)", ok: "#3ddc84", okTint: "rgba(61,220,132,.16)",
        bad: "#ff5d5d", badTint: "rgba(255,93,93,.16)", warm: "#f5c451", onFill: "#07090d", onVideo: "#ffd98a", plate: "rgba(7,9,13,.82)",
        shadow: "0 40px 110px rgba(0,0,0,.55), 0 0 0 1px rgba(255,255,255,.08), inset 0 1px 0 rgba(255,255,255,.05)",
        shadowSoft: "0 16px 40px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.09)", cardLine: "rgba(255,255,255,.08)" },
      F: { code: JB, body: INTER, mono: JB, display: INTER, displayWeight: 800, displayTrack: "-0.03em", hand: "'Caveat', cursive", stamp: INTER } },
    paper_collage: { dark: false, code: "light",
      C: { paper: "#eee4cf", card: "#fbfaf6", sunk: "#f3ecdc", line: "rgba(30,20,10,.14)", ink: "#121212", text: "#2b241a", ink2: "#3a3226", sub: "#5f5446",
        mute: "#8a7d6a", acc: "#d6452f", accTint: "#f7dcd3", ok: "#2f8a5b", okTint: "#dcefe3", bad: "#d6452f", badTint: "#f7dcd3", warm: "#d6452f",
        onFill: "#ffffff", onVideo: "#f2c84b", plate: "rgba(251,250,246,.94)", shadow: "0 18px 34px rgba(30,20,10,.35)", shadowSoft: "0 12px 26px rgba(30,20,10,.25)",
        cardLine: "rgba(30,20,10,.12)" },
      F: { code: JB, body: INTER, mono: JB, display: "'Anton', sans-serif", displayWeight: 400, displayTrack: "0.005em", hand: "'Caveat', cursive", stamp: "'Anton', sans-serif" } },
    // whitespace (2026-10-22, kit/presets/whitespace): the owner's "neat = a white background". canvas_studio's camera and
    // evidence on a true white page. Everything that canvas_studio does with colour (a gradient, a glow ring, pastel
    // blocks) is done here with elevation: white cards on white, told apart by a 1 px hairline and shadows e1-e3 (chip,
    // card, hero), like paper lifted off a table. ONE accent (a blue-violet, the canvas family's hue, so a film can move
    // between the two looks) and no second hue: warm = acc. Ink is near-black, never pure black (pure black on pure white
    // vibrates on a phone). Type is Inter: 700 with tight tracking for display (lighter than Schibsted 800, which made
    // the canvas feel heavy), 500/600 for body; both ship in paper.css. The shadows are a cool neutral (16,18,28): a warm
    // brown shadow on white reads dirty. kit/hf/demos/looks checks every component in it at >= 3:1 (mute is 3.8:1 on
    // white and 3.4:1 on sunk; sub 6:1, acc 6.5:1).
    whitespace: { dark: false, code: "light",
      C: { paper: "#FFFFFF", card: "#FFFFFF", sunk: "#F5F5F7", line: "rgba(14,14,18,.10)", ink: "#0E0E12", text: "#2B2B31", ink2: "#45454D", sub: "#63636C",
        mute: "#83838C", acc: "#5646D6", accTint: "#EEEBFF", ok: "#1A7F4B", okTint: "#E3F4EA", bad: "#C8364B", badTint: "#FBE6E9", warm: "#5646D6",
        onFill: "#ffffff", onVideo: "#D9D3FF", plate: "rgba(255,255,255,.95)",
        shadow: "0 0 0 1px rgba(16,18,28,.07), 0 2px 4px rgba(16,18,28,.04), 0 14px 36px rgba(16,18,28,.09)",
        shadowSoft: "0 0 0 1px rgba(16,18,28,.08), 0 1px 2px rgba(16,18,28,.05), 0 6px 16px rgba(16,18,28,.06)", cardLine: "rgba(16,18,28,.08)",
        // elevation: e1 a chip or a row, e2 a card, e3 the one hero object of a scene (a window, his card). Every look
        // gets e1-e3 from HF.look (shadowSoft / shadow when it has none), so a component can ask for depth by level.
        e1: "0 0 0 1px rgba(16,18,28,.08), 0 1px 2px rgba(16,18,28,.05), 0 6px 16px rgba(16,18,28,.06)",
        e2: "0 0 0 1px rgba(16,18,28,.07), 0 2px 4px rgba(16,18,28,.04), 0 14px 36px rgba(16,18,28,.09)",
        e3: "0 0 0 1px rgba(16,18,28,.06), 0 4px 10px rgba(16,18,28,.05), 0 28px 72px rgba(16,18,28,.13)" },
      F: { code: JB, body: INTER, mono: JB, display: INTER, displayWeight: 700, displayTrack: "-0.035em", hand: "'Caveat', cursive", stamp: INTER } },
  };
  // ---------------------------------------------------------------- the stage (2026-10-22): what HF.canvas paints
  // HF.canvas's own surfaces (the seamless, windows, cards, chips, giant type, the highlighter, beams, the chart, the
  // ring and back block around his shape, decor blocks), per look. canvas_studio's values are the literals canvas.js
  // had through v10, unchanged, so a canvas_studio page renders pixel-identically (proved by a frame diff, 2026-10-22).
  // A look without a stage (a frame that applied its own look and passed HF.canvas { look: false }) gets canvas_studio's.
  //   seamless/edge: the world and the colour around it; grad: the accent's three stops (beam/highlight/chart/C.G);
  //   pastel: decor block colours by name; win/card/chip: surfaces; big/t/s: giant type, titles, labels;
  //   hl: the highlighter { bg (null: the grad), op, blend }; beam { glow (0: none), w, wMax, line (null: the grad),
  //   head, ring, dotR, dotW }; chart { area, areaEnd, glow, halo, grid, base, baseW, w, dot }; ring (a box-shadow around
  //   his shape), back (draw fo.back blocks), fill (behind a cut-out in a card); driftMax (the most a landed card or
  //   window may keep turning, whatever drift a template passes, like beam.wMax: 0 = it lands, then holds still);
  //   blocks (one colour for every C.blocks block, whatever the template names). Optional keys fall back to canvas.js's
  //   v10 literals (the template's drift or 2.2, blocks by name), so canvas_studio lists only what it had.
  const SANS_A = "'Atkinson', sans-serif";
  HF.LOOKS.canvas_studio.stage = {
    seamless: "radial-gradient(ellipse 70% 75% at 50% 40%, #FFFEFC 0%, #F6F3EE 45%, #E9E4DB 100%)", edge: "#EEEAE3",
    grad: ["#6C5CE7", "#FF4D6D", "#FFB86B"],
    pastel: { lilac: "#E7E1FF", peach: "#FFE3D6", mint: "#D9F2E6", butter: "#FFF1C2", sky: "#DCEBFF" },
    win: { bg: "#fff", shadow: "0 1px 0 rgba(255,255,255,.9) inset, 0 0 0 1px rgba(20,20,40,.08), 0 30px 80px rgba(30,30,60,.16), 0 8px 22px rgba(30,30,60,.08)",
      bar: "#F4F4F7", barLine: "#E7E7EC", url: "#fff", urlLine: "#E5E5EA", urlInk: "#6b6b75", dots: ["#FF5F57", "#FEBC2E", "#28C840"] },
    card: { bg: "rgba(255,255,255,.92)", shadow: "0 0 0 1px rgba(20,20,40,.07), 0 30px 70px rgba(30,30,60,.14), 0 6px 18px rgba(30,30,60,.07)" },
    chip: { bg: "#fff", shadow: "0 0 0 1px rgba(20,20,40,.08), 0 10px 30px rgba(30,30,60,.12)", ink: "#2a2a33" },
    big: { font: "'ArchivoCond', sans-serif", weight: 900, case: "uppercase", lh: ".86", track: "-0.01em", ink: "#16161C" },
    t: { font: "'Schibsted', sans-serif", weight: 800, ink: "#16161C", track: "-0.02em" },
    s: { font: SANS_A, weight: 700, ink: "#4A4A55" }, label: SANS_A,
    hl: { op: 0.42, blend: "multiply" },                                  // bg: the grad (null) or a colour
    beam: { glow: 0.55, w: 10, head: "#fff" },                            // head: the travelling dot's fill (its ring is grad[1])
    chart: { area: 0.22, glow: 0.45, halo: 0.3, grid: "#D9D9E1", base: "#16161C", w: 9 },
    ring: "0 0 0 2px rgba(255,255,255,.9), 0 0 0 4px rgba(108,92,231,.55), 0 0 42px 6px rgba(255,77,109,.28), 0 30px 70px rgba(30,30,60,.18)",
    back: true, fill: "linear-gradient(160deg,#F3F0FF 0%,#FFF4F0 60%,#FFFFFF 100%)",
  };
  // whitespace: a white cyclorama, only ~3.5 % darker in the far corners (true white over the middle 55 %, where the
  // content sits), so the page reads as lit, not as a flat #fff screen. One solid accent (grad = acc three times; a
  // film's o.palette acc replaces all three, canvas.js). Cards and windows land once, then hold still (driftMax 0: the
  // camera carries the energy; canvas_studio code passes drift: 1.2 on its clue cards, and a white page that kept them
  // turning broke the restraint rule, the review of 2026-10-22). Decor blocks are one neutral grey whatever colour a
  // template names, a hex included (blocks). No ring and no back block around him: an e3 shadow lifts his card off the
  // page like the other cards. The beam is an ink line with an accent node at its head,
  // and the highlighter a solid tint marker (multiply keeps the ink under it black). Looked at on a still sheet of
  // every piece (2026-10-22, the engine-looks build): the cards separate from the page by the hairline in e1-e3 alone.
  HF.LOOKS.whitespace.stage = {
    seamless: "radial-gradient(ellipse 75% 80% at 50% 45%, #FFFFFF 0%, #FFFFFF 55%, #F5F5F6 100%)", edge: "#F5F5F6",
    grad: ["#5646D6", "#5646D6", "#5646D6"],
    pastel: { lilac: "#F3F3F5", peach: "#F3F3F5", mint: "#F3F3F5", butter: "#F3F3F5", sky: "#F3F3F5" },
    win: { bg: "#FFFFFF", shadow: HF.LOOKS.whitespace.C.e3, bar: "#F7F7F8", barLine: "#ECECEF", url: "#FFFFFF", urlLine: "#E6E6EA", urlInk: "#63636C",
      dots: ["#DEDEE3", "#DEDEE3", "#DEDEE3"] },
    card: { bg: "#FFFFFF", shadow: HF.LOOKS.whitespace.C.e2 },
    chip: { bg: "#FFFFFF", shadow: HF.LOOKS.whitespace.C.e1, ink: "#2B2B31", weight: 600 },
    big: { font: INTER, weight: 700, case: "none", lh: ".92", track: "-0.045em", ink: "#0E0E12" },
    t: { font: INTER, weight: 700, ink: "#0E0E12", track: "-0.025em" },
    s: { font: INTER, weight: 500, ink: "#45454D" }, label: INTER,
    hl: { bg: "#E4DFFF", op: 1, blend: "multiply" },
    // line: a solid ink stroke instead of the grad; wMax: a template's w: 12 (canvas_studio's glowing beam) still draws a
    // fine line here; the head is a solid accent node with a white ring (r 8), visible at the end of a 4 px line
    beam: { glow: 0, w: 4, wMax: 5, line: "#0E0E12", head: "#5646D6", ring: "#FFFFFF", dotR: 8, dotW: 3 },
    // one accent stroke over a flat 4.5 % tint (areaEnd = area: no fade; at 6 % it read as a lavender block on the
    // sheet), no glow or halo, a hairline grid and a 2 px base; the tip stays a white node in an accent ring (dot)
    chart: { area: 0.045, areaEnd: 0.045, glow: 0, halo: 0, grid: "rgba(14,14,18,.10)", base: "rgba(14,14,18,.88)", baseW: 2, w: 6, dot: "#FFFFFF" },
    ring: HF.LOOKS.whitespace.C.e3, back: false, fill: "#FFFFFF",
    driftMax: 0, blocks: "#F3F3F5",
  };
  HF.F = Object.assign({}, HF.LOOKS.paper_studio.F);
  HF.LOOK = { name: "paper_studio", dark: false, code: "light", stage: null };
  // apply a look: HF.look("night") or HF.look("pastel_box", { acc: "#..." }) (colour overrides, e.g. a film's palette).
  // Returns the tokens. Call it once, in the frame, before any component is drawn.
  HF.look = function (name, over = {}) {
    const L = HF.LOOKS[name];
    if (!L) throw new Error("HF.look: unknown look " + name + " (one of " + Object.keys(HF.LOOKS).join(", ") + ")");
    Object.assign(HF.C, L.C, over);
    // e1-e3 (elevation by level, 2026-10-22): a look without its own takes shadowSoft for e1 and shadow for e2/e3, so
    // asking for depth by level never changes what an older look draws
    ["e1", "e2", "e3"].forEach((k, i) => { if (!(L.C[k])) HF.C[k] = i ? HF.C.shadow : HF.C.shadowSoft; });
    Object.assign(HF.F, L.F);
    Object.keys(HF.F).forEach((k) => { if (typeof HF.F[k] === "string") HF.F[k] = HF.F[k].replace(/"/g, "'"); });   // see "Font names" above
    // stage: HF.canvas's own surfaces for this look (null: the look has none, HF.canvas uses canvas_studio's)
    Object.assign(HF.LOOK, { name, dark: L.dark, code: L.code, stage: L.stage || null });
    HF.HAND = HF.F.hand;                                                     // sketch.js / annotate.js handwriting
    if (typeof document !== "undefined") {
      const v = { paper: HF.C.paper, card: HF.C.card, sunk: HF.C.sunk, line: HF.C.line, ink: HF.C.ink, text: HF.C.text, ink2: HF.C.ink2, sub: HF.C.sub,
        mute: HF.C.mute, acc: HF.C.acc, "acc-tint": HF.C.accTint, ok: HF.C.ok, "ok-tint": HF.C.okTint, bad: HF.C.bad, "bad-tint": HF.C.badTint,
        plate: HF.C.plate, shadow: HF.C.shadow, "shadow-soft": HF.C.shadowSoft, "card-line": HF.C.cardLine, e1: HF.C.e1, e2: HF.C.e2, e3: HF.C.e3,
        "f-body": HF.F.body, "f-mono": HF.F.mono, "f-code": HF.F.code, "f-display": HF.F.display, "w-display": HF.F.displayWeight, "t-display": HF.F.displayTrack,
        "f-hand": HF.F.hand, "f-stamp": HF.F.stamp,
        // the HyperFrames catalog's token names (kit/hf/mounts.py): a mounted piece takes the film's look through them
        bg: HF.C.paper, fg: HF.C.ink, surface: HF.C.card, border: HF.C.line, muted: HF.C.mute, accent: HF.C.acc, "accent-2": HF.C.accTint,
        brand: HF.C.acc, "font-display": HF.F.display, "font-body": HF.F.body, radius: "22px" };
      const st = document.documentElement.style;
      Object.entries(v).forEach(([k, x]) => st.setProperty("--" + k, String(x)));
      document.documentElement.dataset.look = name;
    }
    return { C: HF.C, F: HF.F, look: HF.LOOK };
  };
  // a frame's own palette (o.palette) as token overrides: only the keys a film passed, okSoft read as okTint
  HF.lookOver = (pal = {}) => { const o = {}; Object.keys(pal).forEach((k) => { const t = k === "okSoft" ? "okTint" : k; if (t in HF.LOOKS.paper_studio.C) o[t] = pal[k]; }); return o; };
  Object.assign(HF.C, HF.LOOKS.paper_studio.C);                              // the defaults carry every token (no CSS write here)
  Object.assign(HF.C, { e1: HF.C.shadowSoft, e2: HF.C.shadow, e3: HF.C.shadow });
  HF.ICON = {
    cam: '<rect x="3" y="6" width="13" height="12" rx="2.5"/><path d="M16 10l5-3v10l-5-3z"/>', broom: '<path d="M14 3l7 7M11 6l7 7-6 6H6v-6z"/><path d="M6 19l-3 2"/>',
    map: '<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>', search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    code: '<path d="M8 6l-6 6 6 6M16 6l6 6-6 6"/>', play: '<path d="M8 5.5v13l11-6.5z"/>', check: '<path d="M4.5 12.5l5 5 10-11"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>', bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>', music: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    box: '<path d="M3 7l9-4 9 4-9 4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/>', spark: '<path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6z"/>',
    star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>',
    film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>', layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>', file: '<path d="M6 3h8l5 5v13H6z"/><path d="M14 3v5h5"/>',
    cut: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.1 8.1L20 20M8.1 15.9L20 4"/>', sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    wave: '<path d="M3 12h2M7 8v8M11 5v14M15 8v8M19 10v4"/>', db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>', user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4.5-6 8-6s7 2 8 6"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>', terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M12 15h5"/>',
    gear: '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    cache: '<rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 17h.01"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>', clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  };
  // HF.icon(n): the kit's own icons first, then the Lucide set (kit/hf/lucide.js, 222 icons on the same 24-unit grid)
  HF.iconSvg = (n) => HF.ICON[n] || (HF.LUCIDE && HF.LUCIDE[n]) || null;
  HF.icon = (n, size = 32, stroke = "currentColor", width = 2.2, fill = "none") => {
    const inner = HF.iconSvg(n);
    if (!inner) throw new Error("HF.icon: no icon " + n + " (HF.ICON or kit/hf/lucide.js)");
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="${fill}" stroke="${stroke}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
  };
  // named sound cues (kit/sfx) at the preset's levels
  HF.S = { swish: ["whoosh/whoosh__air-woosh__mixkit-1489", -21], slide: ["whoosh/whoosh__technology-transition-slide__mixkit-3120", -22],
    click: ["ui/ui__clear-mouse-clicks__mixkit-2997", -22], pop: ["ui/ui__bubble-pop-up-alert-notification__mixkit-2357", -23],
    check: ["ui/ui__modern-click-box-check__mixkit-1120", -21], type: ["typing/typing__typing-on-a-laptop-keyboard__mixkit-2531", -23],
    hit: ["impact/impact__short-bass-hit__mixkit-2299", -15], riser: ["riser/riser__cinematic-synth-riser__mixkit-645", -17],
    tone: ["ui/ui__confirmation-tone__mixkit-2867", -20], error: ["ui/ui__wrong-answer-fail-notification__mixkit-946", -20] };

  // "*word", "*word*" and "*several words*" mark the accent (one syntax for line(), say() titles and HF.kinetic): a leading
  // "*" opens it, a trailing "*" (before any punctuation) closes it and is never printed; a lone "*word" accents that word
  HF.accentTokens = (line) => {
    const toks = String(line).trim().split(/\s+/).filter(Boolean), out = [];
    let open = false;
    toks.forEach((tok, k) => {
      const starts = tok[0] === "*", ends = tok.length > 1 && /\*[.,!?;:)"”]*$/.test(tok);
      const accent = open || starts;
      if (starts && !ends && toks.slice(k + 1).some((x) => /\*[.,!?;:)"”]*$/.test(x))) open = true;
      if (ends) open = false;
      out.push({ text: tok.replace(/^\*/, "").replace(/\*(?=[.,!?;:)"”]*$)/, ""), accent });
    });
    return out;
  };
  HF.esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  HF.kit = function (o) {
    const tl = o.tl, fps = o.fps || 30, W = o.width || 1920, H = o.height || 1080;
    const Wd = o.words || [], P = o.pieces || [];
    const frameFns = [];
    window.__CUES = window.__CUES || [];
    const K = { tl, fps, width: W, height: H, C: HF.C, icon: HF.icon, esc: HF.esc, words_: Wd, pieces: P };
    K.Q = (t) => Math.round(t * fps) / fps;
    K.W = (i) => { const w = Wd.find((x) => x.i === i); if (!w) throw new Error("HF: word " + i + " is not in the cut"); return w.t; };
    K.WE = (i) => { const w = Wd.find((x) => x.i === i); if (!w) throw new Error("HF: word " + i + " is not in the cut"); return w.e; };
    K.span = (tag) => { const ps = P.filter((p) => p.tag === tag); if (!ps.length) throw new Error("HF: no pieces tagged " + tag); return [ps[0].out_a, ps[ps.length - 1].out_b]; };
    // keep: the cue carries meaning (a result landing, a click that causes the next shot): kit/audio/mix.py never thins it
    K.sfx = (name, t, db, keep) => {
      const s = HF.S[name];
      window.__CUES.push(Object.assign({ name: s ? s[0] : name, at: Math.round(t * 1000) / 1000, gain_db: db != null ? db : s ? s[1] : -20 }, keep ? { keep: true } : {}));
    };
    K.el = (parent, style, html = "", cls = "hf-abs") => { const d = document.createElement("div"); d.className = cls; d.style.cssText = style; d.innerHTML = html; parent.append(d); return d; };
    K.$ = (id) => document.getElementById(id);
    // ---- motion vocabulary
    const Q = K.Q;
    K.show = (e, a, b) => {                                                  // visible from a (from frame 1 when a <= 0) until b
      if (Q(a) > 0) {                                                        // a hide + show both at 0 can capture hidden
        e.style.visibility = "hidden"; e.style.opacity = "0";                // hidden in the DOM too: a seek to 0 on a fresh
        tl.set(e, { autoAlpha: 0 }, 0); tl.set(e, { autoAlpha: 1 }, Q(a));    // timeline doesn't render the set at 0 (frame 0 showed every layer)
      }
      if (b != null) tl.set(e, { autoAlpha: 0 }, Q(b));
      return e;
    };
    K.enter = (e, t, from = {}, dur = 0.6) => tl.fromTo(e, { opacity: 0, y: 28, filter: "blur(8px)", ...from },
      { opacity: 1, x: 0, y: 0, scale: 1, rotation: 0, filter: "blur(0px)", duration: dur, ease: "power3.out" }, Q(t));
    K.exit = (e, t, to = {}) => tl.to(e, { opacity: 0, y: -16, filter: "blur(6px)", duration: 0.35, ease: "power2.in", ...to }, Q(t));
    K.fade = (e, t, dur = 0.4) => tl.fromTo(e, { opacity: 0 }, { opacity: 1, duration: dur, ease: "power1.out" }, Q(t));
    K.drift = (e, a, b, s1 = 1.035) => tl.fromTo(e, { scale: 1 }, { scale: s1, duration: Math.max(0.3, b - a), ease: "none", immediateRender: false }, Q(a));
    K.words = (parent, str, style) => {
      const box = K.el(parent, style, "", "hf-serif hf-abs"), ws = [];
      str.split("|").forEach((line, li) => {
        if (li) box.append(document.createElement("br"));
        line.trim().split(/\s+/).forEach((tok, i, arr) => {
          const m = document.createElement("span"); m.className = "hf-m";
          const w = document.createElement("span"); w.className = "hf-wi"; w.textContent = tok.replace(/^\*/, "");
          if (tok[0] === "*") { w.style.fontStyle = "italic"; w.style.color = HF.C.acc; }
          m.append(w); box.append(m); if (i < arr.length - 1) box.append(" ");
          ws.push(w);
        });
      });
      return { box, ws };
    };
    K.rise = (ws, ts, outAt) => ws.forEach((w, k) => {
      const t = ts[Math.min(k, ts.length - 1)] + (k >= ts.length ? (k - ts.length + 1) * 0.07 : 0);
      if (t <= 0) tl.set(w, { yPercent: 0 }, 0);                               // finished on frame 1
      else tl.fromTo(w, { yPercent: 115 }, { yPercent: 0, duration: 0.7, ease: "expo.out" }, Q(t));
      if (outAt != null) tl.to(w, { yPercent: -115, duration: 0.3, ease: "power2.in" }, Q(outAt + k * 0.025));
    });
    K.typeText = (e, text, t, cps, caret = true) => {
      const o = { n: 0 };
      tl.set(e, { textContent: caret ? "▍" : "" }, 0);
      tl.to(o, { n: text.length, duration: text.length / cps, ease: "none", onUpdate: () => { e.textContent = text.slice(0, Math.round(o.n)) + (caret && o.n < text.length ? "▍" : ""); } }, Q(t));
      return t + text.length / cps;
    };
    K.countUp = (e, a, b, t, dur, fmt = (v) => Math.round(v)) => {
      const o = { v: a };
      tl.set(e, { textContent: fmt(a) }, 0);
      tl.to(o, { v: b, duration: dur, ease: "power3.out", onUpdate: () => { e.textContent = fmt(o.v); } }, Q(t));
    };
    // ---- per-frame state (pure functions of time)
    const lateFns = [];                                      // late: after every other frame fn (reads what they set, e.g. the box)
    K.onFrame = (fn, o) => { (o && o.late ? lateFns : frameFns).push(fn); fn(0); };
    let vid = 0;
    K.vid = (prefix = "v") => `${prefix}${o.id || "hf"}${vid++}`;              // media need unique ids to be tracked
    K.finish = (total) => {
      const proxy = { t: 0 };
      if (frameFns.length || lateFns.length) tl.fromTo(proxy, { t: 0 }, { t: total, duration: total, ease: "none", onUpdate: () => { frameFns.forEach((f) => f(proxy.t)); lateFns.forEach((f) => f(proxy.t)); } }, 0);
      if (root.Stickman && root.Stickman.drive && o.stickman !== false) root.Stickman.drive(tl, total);
      window.__timelines = window.__timelines || {};
      window.__timelines[o.id] = tl;
    };
    return K;
  };

  // shared math for components with keyframed state: value of a list of {t, dur, ease, v} keys at time t
  // o.log: keys interpolated in log space (2026-10-20). A zoom is a ratio: 1 -> 2 should take as long as 2 -> 4, so a
  // camera's scale moves at an even pace to the eye instead of rushing the first half and crawling the second.
  HF.keyed = function (keys, initial, o = {}) {
    const ks = keys.slice().sort((a, b) => a.t - b.t);
    const lerp = (a, b, p) => HF.lerpObj(a, b, p, o.log);
    let cur = initial, prev = null;
    for (const k of ks) {
      if (prev) cur = lerp(prev.from, prev.to, prev.e(Math.max(0, Math.min(1, (k.t - prev.t) / prev.dur))));
      k.from = { ...cur }; k.to = { ...cur, ...k.v }; k.e = k.ease ? (typeof k.ease === "function" ? k.ease : gsap.parseEase(k.ease)) : gsap.parseEase("power2.inOut");
      prev = k;
    }
    return (t) => {
      for (let i = ks.length - 1; i >= 0; i--) {
        const k = ks[i];
        if (t >= k.t) return lerp(k.from, k.to, k.e(Math.max(0, Math.min(1, (t - k.t) / k.dur))));
      }
      return { ...initial };
    };
  };
  HF.lerpObj = (a, b, p, log) => { const o = {}; for (const k in b) o[k] = typeof b[k] === "number" && typeof a[k] === "number"
    ? (log && log.includes(k) && a[k] > 0 && b[k] > 0 ? a[k] * Math.pow(b[k] / a[k], p) : a[k] + (b[k] - a[k]) * p) : b[k]; return o; };
  // ---------------------------------------------------------------- the music map (2026-10-20, kit/audio/beats.py)
  // D.music (kit/film/build.py): the MUSIC beds' beats, downbeats and sections [{t, rise}] in film time. A landing that
  // should hit the music asks for the nearest event the eye still reads as in sync with the word: up to 100 ms before
  // it or 40 ms after (lip-sync tolerance; a card that lands late looks off sooner than one that lands early).
  //   HF.music.snap(t, { kind: "beat" | "downbeat" | "section", early: 0.10, late: 0.04 })  -> the event time, or t
  //   HF.music.near(t, kind, within)  -> the nearest event within `within` s, or null (planning: "is a turn near?")
  //   HF.music.turns(minDb = 6)       -> the section changes a viewer hears ([{t, rise}]): land reveals and cards on them
  // Without D.music (a page built before 2026-10-20, or no MUSIC) every call returns t / null / [], so nothing moves.
  HF.music = {
    map() { try { return (typeof D !== "undefined" && D && D.music) || root.__music || null; } catch (e) { return root.__music || null; } },
    list(kind) {
      const M = this.map();
      if (!M) return [];
      return kind === "section" ? M.sections.map((s) => s.t) : kind === "downbeat" ? M.downbeats : M.beats;
    },
    near(t, kind = "beat", within = 0.12) {
      let best = null;
      for (const x of this.list(kind)) if (Math.abs(x - t) <= within && (best === null || Math.abs(x - t) < Math.abs(best - t))) best = x;
      return best;
    },
    snap(t, o = {}) {
      const early = o.early != null ? o.early : 0.10, late = o.late != null ? o.late : 0.04;
      let best = null;
      for (const x of this.list(o.kind || "beat")) if (x >= t - early && x <= t + late && (best === null || Math.abs(x - t) < Math.abs(best - t))) best = x;
      return best === null ? t : best;
    },
    turns(minDb = 6) { const M = this.map(); return M ? M.sections.filter((s) => Math.abs(s.rise) >= minDb) : []; },
  };
})(typeof window !== "undefined" ? window : globalThis);
