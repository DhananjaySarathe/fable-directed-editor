# kit/hf — reusable scene components for HyperFrames films

The long-form building blocks behind `preset_paper_studio`, extracted from `films/how-i-edit` so that a new film is a
**plan plus scene calls**, not 700 lines of hand-written HTML. Everything is free, local, deterministic and seekable.

**Showcase** (every component in one 73 s film): `showcase/showcase.mp4`, with source in `showcase/src/template.html`.
**Previews**: `previews/*.jpg`. **Registry**: `registry.json`. **How to choose scenes**: `kit/refs/SCENES.md`.

| | |
|---|---|
| ![](previews/diagram_focus.jpg) living diagram | ![](previews/screen.jpg) annotated screen demo |
| ![](previews/code_diff.jpg) code walkthrough (diff) | ![](previews/terminal.jpg) terminal |
| ![](previews/compare.jpg) before / after | ![](previews/chat.jpg) chat explainer |

## What's in the kit

| File | What it gives you |
|---|---|
| `paper.css` | the paper-studio tokens and component styles (inlined into the page) |
| `core.js` | `HF.kit()`: frame-quantised motion (`enter`, `exit`, `fade`, `drift`, `words` + `rise`, `typeText`, `countUp`), icons, named SFX cues, `K.onFrame()` for time-pure state, `K.finish()` |
| `box.js` | **the speaker box**: the A-roll as an object on the stage (full → tilted card → small card → pill → gone), moved by measured moves (`grow`, `shrink`, `move`, `collapse` into a pill a graphic grows out of, `flip` from a card, `swing`, `slide`, `dissolve`, `tiles`), idle sway, and a director (`HF.box.direct`) that picks moves from beat notes. Rules: `kit/refs/MOTION.md`; demo: `demos/box/` |
| `explain.js` | `HF.tokens` (a real model's next-word probabilities, step by step, with a temperature beat), `HF.stack` (exploded isometric layers with labels, focus, collapse), `HF.race` (leaderboard race with physical rank swaps). Real data from `tools/nexttoken.py` and `tools/arena_race.py` |
| `polish.js` | `HF.tiltIn` (a screen swings flat toward the camera; `HF.screen(...).tilt(a, b)`), `HF.sweep` (glare / border beam / text glint), `HF.scramble` (characters decode into a word; seeded, frame-exact) |
| `scenes.js` | `HF.stage` (the layer stack), `HF.camera` (speaker framing: W/M/C/SR/SL/PIP/OFF, or `mode: "panel"` for 9:16), `side`, `insert`, `card`, `pill`, `win` + `scroll`, `phone`, `lowerThird`, `chapter`, `compare`, `chat`, `endCard` |
| `diagram.js` | **the living diagram**: `reveal`, `connect`, `focus` (camera zoom with the rest dimmed), `overview`, `flow` (dots travel an edge), `done`, `note`, `highlight`. Its state carries across `show()` windows, so it develops over the video and returns for the recap. Style `"flat"` (v11, the whitespace default): hairline boxes, right-angle connectors that never share a port, a loop's way back under the row; `HF.diagram.verify` is its geometry gate (see "Flat diagrams") |
| `screen.js` | **annotated screen demos** on a real recording or screenshot: `zoom`, `pan`, `reset`, `highlight` (spotlight + label), `arrow` (drawn on), `cursor` (eased path + click ripples), `callout`, `blur` (privacy). Coordinates are in the recording's own pixels |
| `code.js` | **code walkthroughs**: syntax colouring in the palette, `typeIn`, `highlight` (+ note), `focus`, `add` / `remove` (real diffs that move the lines below), `scrollTo`. Plus a **terminal**: `cmd`, `out`, `spinner` |
| `vendor.py` | puts the kit into a film: copies fonts and gsap, and inlines the CSS and JS at `<!--HF:KIT-->` |
| `plan_check.py` | validates `visual_plan.json` (types, techniques, fallbacks, ratios, timing, stickman budget, assets); `--key` prints a cache key |
| `registry.json` | every component (128): what it explains, the looks it has been used in, the films that used it, how precheck finds it, timing, ratios. **Generated:** `python3 tools/registry.py --write` from the module headers (document a new call in its header and add its META line); `--unused` lists what no film has tried; `--check` fails when it is stale |
| `render4k.py` | a long film at 4K in 30 s chunks joined by stream copy (`uv run python kit/hf/render4k.py films/<video>`; `--plan` lists the chunks) |
| `demos/audit/` | repro checks for the 2026-10-20 audit's bugs (`node kit/hf/demos/audit/check.mjs`): run it after changing studio.js, reel.js, box.js or precheck |
| `tools/locate.py` | **find on-screen text** in a recording ("Render", "Pull requests") → `[x, y, w, h]`, using Apple Vision on-device |
| `tools/grid.py` | a frame with a labelled pixel grid (`--ocr` boxes every text line) for picking coordinates |
| `tools/ocrboxes.swift` | the Vision text recogniser behind `locate.py`; build with `swiftc -O -o kit/bin/ocrboxes kit/hf/tools/ocrboxes.swift` |
| `examples/visual_plan.example.json` | a filled plan (labelled sample: "how an AI video editor reuses assets") |
| `showcase/` | the showcase film (16:9) plus `vertical/` (the 9:16 check) |

The stickman rig (`kit/stickman/stickman.js`) is inlined too. `K.finish()` drives it.

## A film in five steps

1. **Plan**: write `visual_plan.json` from the beat sheet (`kit/refs/SCENES.md`), then `python3 kit/hf/plan_check.py visual_plan.json`.
2. **Template**: start from `showcase/src/template.html`, with `<!--HF:KIT-->` in `<head>`, the A-roll `<video id="aroll" class="clip" …>` in the root, and these two literal lines (the HyperFrames linter looks for them):
   ```js
   const tl = gsap.timeline({ paused: true });
   window.__timelines = window.__timelines || {}; window.__timelines["<composition-id>"] = tl;
   ```
3. **Scenes**: one block per passage:
   ```js
   const K = HF.kit({ tl, id: "<composition-id>", width: 1920, height: 1080, words: D.words, pieces: D.pieces });
   const st = HF.stage(K, document.getElementById("root"), { aroll: "aroll" });
   HF.camera(K, st, { framing: { intro: "W", hook: "SR", demo: "PIP", ... } });
   HF.lowerThird(K, st.top, { name: "Your Name", line: "Building with Claude Code, every weekend", t: 0.3 });
   const I = HF.insert(K, st, a, b);
   const sd = HF.screen(K, I, { x: 110, y: 110, w: 1360, h: 860, src: "assets/rec.mp4", start: a, dur: b - a, srcW: 1920, srcH: 1080 }).show(a);
   sd.zoom(K.W(212), [1260, 190, 620, 250]).highlight(K.W(214), [1288, 236, 268, 60], { label: "What it is", until: K.W(230) });
   ...
   K.finish(D.total);
   ```
   Time everything to words with `K.W(i)` (word start) or `K.span(tag)`.
4. **Build**: in `build.py`, `F = Film(__file__)` (`kit/paths.py`), then `F.stage()`, `vendor.copy_assets(F.hf)`, `html = vendor.inline(html)` and write `F.hf / "index.html"`. The HyperFrames project lives in `output/temp/films/<name>/hf`, so `films/<name>/` keeps only the recipe. Then `npx hyperframes lint <F.hf>`.
5. **Render and gate**: `npx hyperframes render <F.hf> -o <F.renders>/raw.mp4 --quality delivery`, mux with `-aac_pns 0` (see gotchas) into `F.final`, then `kit/qa/qa.py`.

## Annotating a real screen recording

1. Record the screen separately (OBS / QuickTime, 1920x1080 or the native resolution). Hold still for a moment wherever you'll point at something.
2. Find targets: `python3 kit/hf/tools/locate.py rec.mp4 12.5 "Render"` → `{"box": [x, y, w, h]}`, or `grid.py rec.mp4 12.5 --ocr` and read them off the grid.
3. Annotate only while the screen is still (coordinates are per frame of the recording). Use `mediaStart` to choose the part of the recording to play.
4. Blur anything private with `sd.blur([[x, y, w, h], ...])`. The blur moves with zooms.

## Rules baked into the components

- **Still only when it's read**: inserts and diagram windows carry a slow push; a shot the viewer reads may hold still and is declared a hold (`S.hold` / `read: true`; qa.py `--holds`). Don't add motion just to pass the freeze check (EDITING.md §6).
- **Seek-exact**: camera moves, flowing dots, cursors, spinners and stickman poses are pure functions of time (`K.onFrame`). No `Math.random` anywhere (the linter checks).
- **Readable**: code ≥ 26 px, terminal ≥ 28 px; narrow windows (9:16) put code notes in a footer so they never cover code.
- **Real data only**: the terminal and code show real commands and output. Numbers come from real runs and pages.

## Gotchas (found while building this)

- **AAC spikes**: ffmpeg's native AAC encoder's noise substitution (PNS) can add +9 dB spikes on sparse noisy SFX (typing). Always mux with `-aac_pns 0`. It's set in every film, reel, the shorts renderer and normalisation.
- **Fonts**: never name a family after a CSS generic ("Serif", "Mono"). Use InstrumentSerif and JBMono.
- **Timelines**: register `window.__timelines[id]` literally in the page (the linter doesn't see `K.finish`).
- **Tweens after a set**: use `fromTo` with explicit start values (`immediateRender: false`); a plain `to` can capture stale values on seeks.
- **Puppeteer screencast**: `stop()` can hang after the file is complete; `showcase/make_screen.mjs` races it with a timeout.
- **Hide a video's container with opacity, not visibility** (HyperFrames 0.8.181, chakra-interview 2026-10-31): the renderer
  and `snapshot` swap every `<video data-start>` for an `<img class="__render_frame__">` sibling and set it
  `visibility: visible`, which beats a parent's `visibility: hidden`. A hidden full-frame viewport (a screen track that is
  black during the talking parts) then paints its frame over everything under it, with no warning. Hide such a container
  with `opacity: 0` (or `display: none`) as well; the DOM and precheck still look right, only a snapshot shows it.

## Status

v1.0.0 (2026-10-03, branch version_6). Verified:
- the 16:9 showcase renders and passes QA (−14.3 LUFS, TP −1.6, no freezes);
- the 9:16 check works: panel camera, card diagram, zoomed screen crop, 34 px code;
- the project tests pass (185).

Not built yet (add when a video needs them): animated timelines, network-flow presets, narrative charts, icon morphs, the rough.js sketch treatment (see the ranking in the session notes, and SCENES.md for fallbacks).

## Looks: one kit, many looks (`core.js` HF.look, `studio.js` HF.parts, 2026-10-20)

Each look is one token set in `HF.LOOKS`. The seven looks are pastel_box, canvas_studio, redline, night, paper_studio,
paper_collage and whitespace (2026-10-22, the white page: `kit/presets/whitespace`). A frame applies its look once:
- HF.studio and HF.reel apply pastel_box, or `o.look` (`HF.studio(K, ROOT, st, { end, look: "whitespace" })`);
- HF.canvas applies canvas_studio, or `o.look` (`HF.canvas(K, ROOT, { ..., look: "whitespace" })`);
- HF.redline, HF.night and HF.nightReel apply their own;
- `HF.paper(S, { look: true })` applies paper_collage;
- with no frame, paper_studio is the default.

The components read the tokens at call time: `HF.C` (colours), `HF.F` (fonts) and the CSS variables (`--card`, `--ink`,
`--f-body`, ...). A UI card, a scoreboard, a code window, a sketch or a stickman therefore takes the film's ink,
surfaces and type, in any look:
- dark glass in night;
- an ink hairline and the red pen in redline;
- Schibsted and Atkinson on the canvas.

- **Tokens:**
  - `C`:
    - paper, card, sunk, line;
    - ink, text, ink2, sub, mute;
    - acc / accTint, ok / okTint, bad / badTint;
    - warm, onFill (text on a filled chip), onVideo;
    - plate, shadow, shadowSoft, cardLine;
    - e1 / e2 / e3 (2026-10-22): elevation by level (a chip, a card, the scene's one hero object), also CSS `--e1..--e3`.
      A look without its own gets shadowSoft for e1 and shadow for e2 / e3, so asking for a level never changes an older look.
  - `F`: body, mono, code, display (+ weight, tracking), hand, stamp.
  - `HF.LOOK`: { name, dark, code, stage } (code is the default theme of HF.code; stage below).
  - `stage` (canvas_studio and whitespace): what HF.canvas paints itself, read back as `C.stage`. The seamless and the
    edge colour, the accent's three stops (`grad`; whitespace's are one colour, so `C.G` / `C.GRAD` are solid), decor
    block colours, the window / card / chip surfaces, the giant type, titles and labels (`.cv-*` classes read them as
    CSS variables `--cv-*`), the highlighter, the beam (glow, width cap, line colour, head), the chart (area, glow,
    halo, grid, base, tip), the ring / back block / fill around his shape, `driftMax` (a cap on the turn a landed
    card keeps making) and `blocks` (one colour for every decor block). canvas_studio's stage holds the literals
    canvas.js had through v10, so its pages render pixel-identically (frame diffs of chakra-redline, oss-editor and its
    Reels, kit-v10-sample, xchakra and its shorts, 2026-10-22).
- **Whitespace** (`kit/presets/whitespace/README.md`): true white, near-black Inter, one accent (#5646D6), white cards
  told apart by a hairline and e1-e3, no gradients, glows or pastel blocks. On it the canvas draws a beam as a 4 px ink
  line with an accent node, the highlighter as a solid tint marker, the chart as one accent stroke over a flat tint,
  his shape with an e3 shadow (no glow ring, `fo.back` ignored), and `C.blocks` in one neutral grey whatever colour
  is named. Cards and windows land once, then hold still (the stage's `driftMax: 0` caps any template's `drift`),
  and a film's `palette.acc` becomes the stage's accent too, so the page keeps one. HF.studio / HF.reel
  with `look: "whitespace"` paint a plain white world (no aurora, no grain) and take the look's ink, lines and accent
  for the chrome, chapter cards, fromPill and the end card (`HF.studioLook(name)`); S.sc scene pieces in a Reel keep
  their own content colours. Templates should use `HF.C` tokens rather than canvas_studio literals (the preset's
  README has the swap table).
- **A film's own palette** (`HF.studio(..., { palette })`, `HF.canvas(..., { palette })`) overrides the matching
  tokens (`HF.lookOver`). On a solid-accent stage (whitespace) the canvas's own accent (`C.G`, the beam's node, the
  chart, the marker) follows `palette.acc` too; canvas_studio's three-stop gradient stays its own, as before. Call
  `HF.look(name)` yourself only for a frame that doesn't set one.
- **`HF.parts(K, ROOT, { front })`** holds the frame-independent pieces: layer, land, card, chip, mono, icon, tick, pop,
  arrow, svgLayer, plus `.ui.*`, focus, scoreboard, flow, hold and quiet. HF.studio builds its helpers from it. HF.canvas
  exposes it as `C.parts`, `C.ui`, `C.scoreboard`, `C.flow` and `C.focus`, so a canvas film gets the UI cards and the
  evidence pieces. Put them in a flat station: `C.station(a, b, "mid", [x, y])`.
- **Writing a component:**
  - colours come from `HF.C` and type from `HF.F`, or from the CSS variables in classes;
  - white text on a fill uses `C.onFill`;
  - font tokens are single-quoted. They go inside `style="..."` attributes in innerHTML: a double-quoted
    `"Inter"` once ended the attribute early and every card lost its font size.
  - Content colours stay literal: avatars, a product's own UI, the orb.
- **The check:** `node kit/hf/demos/looks/check.mjs` draws the components in all seven looks (whitespace twice: through
  HF.canvas and, as `whitespace:studio`, through HF.studio). It measures every text's
  contrast against what it really sits on (≥ 3:1), finds broken markup, collects page errors, and writes
  `output/temp/demos/looks/sheet.png`.
- **Not converted yet:**
  - kinetic.js (it has its own type presets);
  - collage.js (it brings its own paper);
  - polish.js, explain.js and screen.js;
  - each look's own pieces (N.*, R.*, canvas.*, paper.*), which stay in their look.

## Pastel-box studio: a film's whole frame in one call (`studio.js`, `studio_ui.js`, 2026-10-10)

`HF.studio(K, ROOT, st, { end, talk, sections, chrome, palette, kicker })` sets up the frame of `preset_pastel_box`:
- the pastel aurora world (it orbits, so the frame is never still);
- the chrome (corner labels, section, timecode, progress; white only over a visible full-frame box);
- chapter cards (wipe, drift, auto-fit titles);
- the word-synced serif type (`say`, `line`, `strike`). `line()` accents like HF.kinetic: `"*word"` or `"*several words*"`, the
  closing `*` is never printed. `say()` returns `t0` (its first word's time). `strike(..., until)` gives the line an end;
  one drawn on FRONT without `until` stays up for the rest of the film (precheck flags it as `linger`);
- scene layers that float and push (`layer`), and `land`/`leave`, `card`, `chip`, `fromPill`;
- the speaker-box wiring (`beat()`, `S.box({ flips, jumps })`). Every picture cut in `K.pieces` (`HF.box.cutsOf`)
  reframes inside the shot it is in (`HF.box.jumpShots`): a full frame punches 1.12x or back out, and a card switches
  its footage zoom between 1.0 and 1.1. A cut near a beat or move is left alone. `jumps: [first word ids]` picks
  cuts and `jumps: false` turns it off. HF.reel does the same (`jumps: [times]`) and takes `src: [w, h]` for a 16:9
  camera (it defaults to a portrait take). With the lens on (`D.lens`, or `S.box({ lens })`; v11), the same cuts become
  the lens's eased 0.25 s reframes instead of hard 1.12x steps, on whatever shots the box gets (`box.shots` included).
  Where the sharp zoom budget can't pay one, the reframe spends the track's soft allowance, so no join plays bare.
  Every `say()` stress id becomes a punch candidate. The lens replaces the box's linear 3 % drift in the holds where it
  moves; a hold it leaves still keeps the drift (see "The lens");
- `S.endCard()`: the handles default to `HF.HANDLES` (kit/brand.json, injected by `vendor.inline`); `{ handles }` overrides.

### Paper collage (`paper.js`, 2026-10-11)

`HF.paper(S)`: `bg`, `hero` (a cut-out from `kit/look/objects.py`), `stamp`, `tape`, `polaroid`, `ticket`, `tag`, `chart`, `phone`,
`clipping`, `ink` (red HF.annotate). Rules and the image sourcing: `kit/presets/paper_collage/README.md`; skill `paper-collage`.
The objects are cut out on-device by `kit/bin/fgcut` (Apple Vision foreground mask; source `kit/hf/tools/fgcut.swift`).

### Evidence (`evidence.js`, 2026-10-10): S.focus, S.scoreboard, S.hold, S.quiet (HF.studio and HF.reel)

- `S.focus(L, target, { at, until, line, fill, side, click, dim })`: the layer's focus wrapper zooms so `target` fills
  ~78 % of the free frame (`side` leaves room for the box), `line` gets an accent-tint highlight, its siblings dim;
  `click: { from: [x, y], u, v }` glides a pointer in and clicks first. The held part is a declared hold.
- `S.scoreboard(par, x, y, w, { title, rows: [{ name, color, sub }], at, fmt, size })` -> `set(i, value, t)` (numbers
  count up; values are a pure function of time) and `win(i, t)`. Row text 40 px (16:9) / 48 px (9:16).
- `S.hold(a, b, why)`; `layer(a, b, par, { read: true })` holds still and declares the hold. `S.quiet(a, b, { depth })`.
- `cues.mjs` writes `<cues>.holds.json` and `<cues>.quiet.json`; `kit/audio/mix.py` applies the quiet moments;
  `kit/qa/precheck.mjs --holds-out` adds readable stills; `kit/qa/qa.py --holds` reads both.
- `S.flow(par, { states: [{ at, x, y, w, h, radius, bg, html, click: [u, v], sfx }], spring, cursor, until })`: one
  container through a process's states; it animates its geometry (never a scale: text stays sharp), the old content
  leaves before each move, the new enters after it settles; `click` brings a pointer that causes the change.
- `sd.walk([{ t, at: [x, y], click, zoom: [x, y, w, h] | null, why }], { lag, camDur, travel, until })` (screen.js): the
  pointer travels and clicks, the camera follows `lag` s later, gently; each settled zoom is a reading hold.
- Fixture checks: `kit/hf/demos/evidence/build.py` (`--reel`, `--flow`, `--walk`; builds into output/temp/demos/evidence;
  expected precheck findings in its docstring).

`S.ui.*` (studio_ui.js) holds the tested product-like UI cards: message, workspace, thread, pr, stamp, doc, checklist,
chat (user / think / rows), toggle (+ pointer click), column (grows with its items), hub, tiles, numbered, note,
lowerThird, thinking, pointer.

`kit/film/example/src/template.html` is a small model: scenes only. Check a built page with
`node kit/qa/precheck.mjs <hf>/index.html` before any render; see `kit/presets/pastel_box/README.md`.

## Night build: a dark developer desktop for AI-vs-AI films (`night.js`, 2026-10-17, films/ai-portfolio)

On top of `HF.studio` (pass `palette: HF.night.PALETTE`): `const N = HF.night(S, st, { cut, clock, sections, left })`.
- The world: a near-black grid, a monitor glow and a lamp; a HUD (REC + the story's clock from `clock: [[t, "04:00",
  "AM", "DAY 1"], ...]`, the section, the timecode, a progress bar). One colour per contender (`HF.night.TEAM`: GPT
  green, Claude coral, Argon blue-violet, "current" grey), the apps' own icons in `assets/icons/`.
- The room: `N.theme(t, "gpt")` crossfades the world's lights (themes night, gpt, claude, argon, verdict; `o.themes`
  adds more): each light is a colour wash plus the grid redrawn in its colour and masked to its reach, so the lines
  near it take the colour. Switch with the subject on screen; put the big switches under a chapter card or a skip.
- The corner (`HF.box`, 16:9): `beat(t, "corner", { side: "left" })` puts him in a straight card top right (`side`
  = where the screen is; `"right"` -> top left) while a recording fills the other side and the notes stack under him
  (x 1325-1882 from y ~540 for top right). Use it where a screen would otherwise hide him for more than ~8 s.
- Behind him (his cut-out on top): `N.light`, `N.word` (giant type), `N.dim` (the wall darker). With no cut-out they are
  hidden or drawn over him (layout work only).
- Evidence: `N.win` (a dark browser window playing a `kit/web/record.mjs` recording), `N.card`, `N.chip`, `N.lbl`,
  `N.stamp` (his words only), `N.bars` (sourced numbers).
- Structure: `N.skip(a, b, { from, to, ampm, note })` (the rolling-clock time skip), `N.chapter(t0, t1, "02", "the
  launch")` (both full frame, marked as cover so precheck lets their type sit where the face is), and
  `N.pip(a, b, { video, face: (t) => [cx, cy, head_w], at: [[t, cx, cy, d], ...] })`: a pickup camera as a face circle
  that moves and resizes between beats (a soft vignette inside sits a bright room into the dark world).

### The night build in 9:16 (`night_reel.js`, 2026-10-18, films/ai-portfolio/shorts)
On top of `HF.reel` (pass `palette: HF.nightReel.PALETTE`): `const N = HF.nightReel(S, st, { theme })`. You get the
same lit grid and themes, `N.win` / `N.card` / `N.chip` / `N.stamp` / `N.word` (sized for 9:16, text >= 36 px),
`N.pip`, and captions restyled on dark plates. The corner exists in 9:16 too: `beat(t, "corner", { side: "left" })`
puts the face top right (`cornerR`, y ~260-644) over a screen. kit/reel's build loads this module for every Reel.
Pass `faces: D.faces, src: [SQ, SQ]` to get the real face (`window.__faceRect(t)`: forehead `top`, chin `bottom`, and
`head` = the hair top, ~1.35 face widths above the nose point; precheck tests text against it) and `N.capY(t, y0, h, tEnd,
topLimit)` for captions: sampled over the page's whole time, at y0 when the face is clear, under the chin while it fits
the band, else above the hair, else over the hair (still off the face), never into the overlays above (topLimit). Give
`S.captions` `breaks:` at every layout change and punch (kit/reel sorts them). `N.word(..., { fast: true })` is the hero
slam (sharp and white by ~0.15 s; the default spring reads grey for ~0.5 s); `{ over: true }` marks a word meant to cross
the face. A punch inside a card: `S.box({ extra: [{ t, at: "cornerR" | "bottom" | ..., in: "cut", zoom: 1.12 }] })`.

## Redline: the editor's notebook (`redline.js`, 2026-10-19, kit/presets/redline)

`HF.redline(S, st, o)` re-skins the frame of `HF.studio` (16:9) or `HF.reel` (9:16):

- warm graph paper (60 px grid) that never moves;
- Schibsted Grotesk headlines;
- ONE red felt-tip pen (perfect-freehand, hand-speed warp, seeded noise) only on claim words;
- pencil icons and dashed links;
- real screens as numbered figures, marked on a tracing sheet that can frost all but one line;
- his real room in square framed windows (`R.face`, which publishes `window.__faceRect` for precheck);
- cards for titles, chapters, numbers, lists, comparisons, time skips and the end card;
- paper-label Reel captions.

Text geometry is measured on the first frame, after the fonts load. The rules and numbers are in `kit/presets/redline/README.md`. Demo:
`uv run python kit/hf/demos/redline/build.py --snap`. `screen.js` now exposes `sd.cam(t)`, `sd.map(t, x, y)` and `sd.onCam(fn)` for
overlays that map source px to view px.

## Canvas: one lit stage and a camera (`canvas.js`, 2026-10-20, films/chakra-redline)

The owner called a slide-style edit (text and plain animations on a page, his cut-out moved around) "awesomely stupid".
`HF.canvas(K, ROOT, { w, h, x, y, z })` came after studying premium talking-head edits frame by frame (Enrico
Tartarotti, Ali Abdaal, Ishan Sharma, Think School): nothing is a slide. Everything sits on one warm seamless stage,
and a camera moves between the parts:
- **The camera:** `C.cam` glides, pushes or whips between stations, with motion blur from its speed and a whoosh under the fast moves. `C.hold(a, b, dz)` adds a slow push while a frame holds; the push lets go during the next move.
- **Stations:** `C.station(a, b, "mid", [x, y])` is a flat 1920×1080 frame at a camera stop. Children use screen px there, and 3D turns are seen from its own centre.
- **Pieces:**
  - `C.window` (a browser window in 3D) and `C.card` (lands from depth with a turn);
  - `C.highlight` (a gradient highlighter) and `C.beam` (a glowing line; `curve`, `dot`);
  - `C.big` (giant condensed caps) and `C.chart` (a gradient line drawn in steps, `keys`, landing with a pop, `land`);
  - `C.chip`, `C.dof` (a macro lens) and `C.at` (positions on the parallax layers).
- **The speaker:** `C.speaker(id, shots, { back })` puts him in a closed shape. `mode: "card"` makes a rounded card, or a circle with `r: w / 2`; `s` sets his scale inside (a punch-in). The shape always covers, with a glow ring and an optional pastel `back` block. Shapes morph between shots.
  - The owner (2026-10-20): "always put me either in a circle or in a square box ... do not remove the person". Use his graded take (the `--plate` file of `kit/look/cutout.py`) as the video.
  - `mode: "stage"` (a cut-out on the seamless with a floor shadow) is kept only in case he ever asks for it.
  - `mode: "frame"` (2026-10-22, the seated frame): his take full bleed (`full: true`) or a large card (radius 28, centred on `x, y`; default 87.5 % of the page width, 16:9 on a landscape page = 1680×945 at 1920, 4:5 on a portrait one = 945×1181 at 1080). Its crop stays inside the take's clean rect (`clean: [x0, y0, x1, y1]` in the track's px, on the shot or for the whole speaker, or `{ <clip>: rect }` per take, following the piece playing), so no camera move shows the clutter beside the plain wall. `fx` / `fy` place his face (`at`) in the shape (default 0.5 / 0.42). Moving between full bleed and the card is the lift: 0.55 s in-out, the card shrinks while its shadow grows from nothing (the e3 shadow on whitespace). It is never a cut-out.
  - The lens (`fo.lens`, the next section) moves the camera on him inside every shape. It is on by default for the page's face track (`D.lens`), off for other speakers such as a screen recording, and `false` turns it off. `fo.ride: true` makes his shape ride the canvas camera: it follows `C.hold` pushes and slow zooms, and eases back to its screen place during whips and pans. `fo.primary: true` names the speaker `window.__speaker` reports (default: the page's face track, the speaker whose id is `D.lens.track`, else the last `C.speaker` call; `window.__faceRect` stays the last call's).

Checks: `node kit/qa/measure.mjs <index.html> "<selector>" <t1,t2>` prints where things really land (3D and the camera
included). Keep a 96 px margin and gaps of 70 px or more. The fresh critic's lessons from v2:
- His real room goes in the card. A cut-out on a gradient reads as a sticker.
- One dark anchor card per scene.
- Beams converge on him.
- Hero type fills the width behind his head, with his head over 2 letters at most.
- A chart is never an empty plate: the flat part draws as it lands.
- Floating pastel corner blocks read as sticky notes; a backing block behind a card works.

## Agent UI Reels: the product working, full screen or split (`agent.js`, 2026-10-10)

The owner's rule after two rejected cuts of the Instinct Reel: "where is the UI? show some kind of animation over there…
take the whole screen for that, or a split screen in some cases. Use a combination."
(top Shorts in this niche show the face full frame only ~20-35 % of the runtime). `const A = HF.agent(S)` after
`HF.reel`: dark-glass app chrome, generic (platform names as text on a letter tile, no logos), text >= 36 px:
`A.inbox` (+ `pre()` rows already there on frame 1), `A.chat` (`send` types into the bar then sends, `them`, `file`;
it scrolls itself), `A.connect`, `A.flood` (cards stamped APPLIED), `A.toast`, `A.limits`, `A.counter`, `A.week`, `A.title`.
Layouts are box rectangles: SPLIT `{ cx: .5, cy: .7745, w: .94, h: .42 }` (UI y 130-960, captions on the seam at 985),
CIRCLE `{ cx: .2, cy: .776, w: .3056, h: .1719, pill: 1 }` (330 px face circle, UI y 140-1190, captions 1225); move
into the circle with `in: "shrink"` (auto picked the pill collapse: a green slab).
Gotcha: `HF.E.in` is the entrance/move ease (decelerating), `HF.E.out` the exit ease (accelerating, starts slow).
**A named product is shown as itself** (the owner, 2026-10-11): look it up, then `node kit/web/capture.mjs <url>
films/<film>/assets/web --el=<logo selector>` (phone-width page.png for a scroll, el-N.png for the mark); put the page in
a phone-browser card that scrolls to its key line on the naming word, and pass the mark as `avatar` to `A.chat`/`A.panel`.

## Footage-native Reels: type behind him, tracked labels, the agent HUD (`footage.js`, 2026-10-10)

For a selfie Reel where the real room is the proof (the owner rejected a second pastel-box Reel as "the same as the
last one"). `const F = HF.footage(S, st, { cut: "cut", corner: "cut2" })` after `HF.reel`; the cut-out WebM
(`CUTOUTS = ["all"]` in reel.py) sits on top of a layer between it and the A-roll.
- `F.behind(text, a, b, { x, y, size, color, page, parent, count, style })`: giant Anton words BEHIND him. `y` is the
  top of the line box. `page: true` = page px, so punches don't push it off-screen (use it by default). Put the
  number in the wall band above his hair (bottom ≈ y 410 at zoom 1.0), side by side with its label; when his head
  fills the top (leaning in, a 1.12 punch), use `parent: S.FRONT` and put it on his dark shirt (y ≈ 1215).
- `F.pin(track, a, b, { label, r, dy })`: hand-drawn ring + label on a tracked point. Tracks: `kit/reel/track.py`
  `other_face(R, a, b, near=(x, y))` (YuNet, the second face) or `point()`. Always overlay the track on raw frames
  first: the speaker's head can hide the other person mid-shot, so crash zoom only while they are visible.
- `F.hud(x, y, w, { title, at, until })`: the agent's dark-glass panel: `.cmd(text, t)` types, `.line(text, t, ok|err|warn)`.
- `F.alert(text, t)`: red edge glow + banner + shake. `F.corner(a, b)`: his cut-out small in front of a takeover.
- `K.onFrame(fn, { late: true })` runs after every other frame fn: anything that reads the box's transform (pins,
  page-anchored type) must be late, or it lags a frame (and a snapshot shows the previous seek's framing).

## v8 motion: springs, motion tokens and kinetic type (`kinetic.js`, 2026-10-07)

Why: the research behind it (Remotion vs HyperFrames, what makes top motion reels look premium) found that designer
motion differs from programmatic motion in its curves, not its renderer: no stock eases, several properties animating
with offsets, springs that settle instead of tweens that stop, staggers with a capped total, exits designed like
entrances, and sound landing on the motion's landing frame. `kinetic.js` is that vocabulary. It is **opt-in**: `core.js`
keeps preset_paper_studio's calm defaults (no bounce), so approved looks don't change.

| API | What |
|---|---|
| `HF.E.in` / `.emph` / `.out` / `.move` | ease-out-expo `(0.16,1,0.3,1)` for entrances, Material 3 emphasized `(0.05,0.7,0.1,1)` for hero reveals, ease-in-expo `(0.7,0,0.84,0)` for exits, in-out `(0.65,0,0.35,1)` for moves. Never use GSAP's stock `power*`/`back`/`elastic` in new work |
| `HF.spring(HF.SPRING.ui)` | a closed-form damped spring as a GSAP ease → `{ ease, duration, land, overshoot }`. Presets (Apple's ratio + response): `ui` 1.0/0.4 s (no overshoot), `snappy` 0.82/0.32 s (~1 %), `thrown` 0.68/0.42 s (~5 %), `soft` 1.0/0.65 s. Bounce only for things with momentum. Remotion's default spring overshoots 16 %: that's the "generic AI video" look |
| `HF.stagger(n, per, cap)` | offsets 2 frames apart, the whole run capped at 0.5 s; the first item leads |
| `HF.land(K, el, t, { from, spring, sfx })` | entrance: opacity (fast), scale (spring), x/y/rotation (spring, one frame later), blur (expo). Returns the landing time; `sfx` fires one frame before it |
| `HF.leave(K, el, t, { to })` | exit: 0.26 s ease-in-expo with blur, shorter than the entrance |
| `HF.kinetic(K, parent, o)` | kinetic type. `text: "Most people spend *4 hours* editing"` (`*span*` = stressed, `|` = line break) at `at` with a capped stagger, or `from`/`to` word ids of the cut (+ `stress: [ids]`) so each word lands on its spoken time minus a frame. `style`: `slam` (Anton, scale 1.9 → 1 on the snappy spring, blur clears, the line takes a 7 px impact), `pop` (Montserrat 900, thrown spring), `rise` (serif in a mask, expo), `track` (Montserrat 800, tracking 0.32 em → 0 with blur). Stressed words share one accent box that draws after they land; `split: "char"` staggers letters. `sfx`: `"stress"` (default), `"each"`, `"first"` or `null`. `kt.out(t)` exits word by word |

Fonts: Anton and Montserrat 800/900 are declared in `paper.css` (so the render waits for them) and copied by `vendor.py`.
Exact: everything is a pure function of timeline time (no requestAnimationFrame, no randomness); tests in
`tests/test_kinetic.py`.

**Demo**: `uv run python kit/hf/demos/kinetic/build.py` renders the same 12 s beat sheet with the v7 vocabulary and with
`kinetic.js` → `output/final/kit-hf-demos-kinetic/kinetic_compare.mp4` (before, then after, with sound) and
`kinetic_side_by_side.mp4`.

## v7 styles: sketch, marker notes, scribble outline, paper collage

Four hand-made looks for explainers (16:9) and Reels/Shorts (9:16) about AI and coding tools, added in version 7.
Each is one module inlined by `vendor.py` like the rest of the kit, plus its library in the film's `vendor/`.

| File | What it gives you |
|---|---|
| `sketch.js` | `HF.sketch`: Excalidraw-look diagrams on rough.js that draw themselves (strokes on, fills fade, labels write) and boil while they hold |
| `annotate.js` | `HF.annotate`: marker strokes on perfect-freehand over screenshots, code and windows: circle, underline, highlight, scribble-out, strike, box, arrow, handwritten note |
| `scribble.js` + `tools/scribble.py` | a hand-drawn outline that follows the speaker: built offline from the person matte, picked per 12 fps step |
| `collage.js` | `HF.collage`: torn-paper screenshots, tape, shadows, halftone, paper grain, motion on twos, a 2.5D parallax camera |

All four share three helpers (defined by whichever module loads first): `HF.rng(seed)` (mulberry32, for build time),
`HF.handFont()` (the Excalifont / Caveat `@font-face`, and a `document.fonts.load` so the renderer's `fonts.ready`
waits for it) and `HF.drawOn(tl, path, t, dur)` (DrawSVG when vendored, a dash offset otherwise).

**Rules for all four**
- **One hand-made style per passage, two or three per video.** They are seasoning, like the stickman: the speaker,
  the real screen and the cards stay the meal. Never stack two of them on the same frame (marker notes on a collage
  piece is fine; a scribble outline plus a collage is not).
- **Ink, one orange, plus green for "done".** Hand strokes in `C.acc` (or `C.ink`), fills only as hachure or a pale
  tint; no extra colours, no clip-art icons, no emoji.
- **Exact or nothing**: geometry is built once from a seed; per frame you only select or slice it. No `Math.random`,
  no `requestAnimationFrame`, no real-time physics. Anything "boiling" steps at 12 fps (`floor(t * 12)`).
- **Never at time 0**: a layer that must show on the first frame gets no `tl.set` at 0 (GSAP's zero-time sets can
  render in reverse on the runtime's first seek; the demo's first beat came out blank until this was fixed).

### 1. Sketch diagrams (`sketch.js`)

**When to use (the rule)**: a flow, a loop or an architecture you *explain while it builds*: agent loops, "prompt
→ plan → edit → check", request paths, before/after pipelines. Three to six boxes. Use the living diagram
(`diagram.js`) instead when the same diagram must come back across the video with focus/zoom, and a card when it's
a list, not a flow.

```js
const sk = HF.sketch(K, layer, { x: 60, y: 440, w: 960, h: 1060, seed: 7 });   // view box in the layer; options: roughness, strokeWidth, dark
sk.node("read", { x: 480, y: 130, w: 300, h: 140, label: "Read", fill: "#f0a98d" });  // centre x/y in view px; shape: rect|ellipse|diamond; fillStyle
sk.arrow("a1", "read", "plan", { bend: -0.2 });          // node ids or [x, y]; bend < 0 bows outward on a clockwise loop; dashed, label
sk.text("mid", 480, 496, "loop until\nthe tests pass", { size: 42, color: C.ink2 });
sk.ring("ring", "check", { color: C.acc });               // an emphasis loop around a node
sk.line("l", [[x, y], ...]);                              // a free rough curve
const end = sk.draw(["read", "a1", "plan"], 0.1, { stagger: 0.4 });   // returns when the last label is written
sk.boil(3.9, 6.3);                                        // 12 fps line boil, only on items already drawn
sk.hide(Object.keys(sk.items), 6.0);  sk.show(a, b);
```

**How it stays exact**: each shape is generated by rough.js three times with fixed seeds (`seed`, `+1000`, `+2000`);
variant 0 is drawn on with DrawSVG tweens (an arrow's shaft, then its head); fills (hachure or solid) only fade;
labels write on with a clip wipe. During a boil window a `K.onFrame` shows variant `floor(t*12) % 3` and nudges the
labels by a fixed table. rough.js only calls `Math.random` when a seed is 0, which the module never passes.

**Cheap-look risks**: boil while something is still drawing (strobing); roughness above ~1.6 (looks broken, not
hand-made); more than one fill colour family; long labels (keep to one or two words, 52–64 px); arrows that touch
labels. Hand labels at 9:16 need ≥ 40 px.

### 2. Marker notes (`annotate.js`)

**When to use (the rule)**: to point at *one thing* on a real screenshot, code window or recording that the
narration names: a number, a line of code, a button. One to four marks per shot, each landing on its word.
`screen.js` (spotlight + label) stays the choice for a moving recording you zoom into; marker notes are for a still or
held frame. **Never on a face**: pass the face box as `avoid` and any mark that touches it throws at build time.

```js
const an = HF.annotate(K, group, { x, y, w, h, srcW: 1728, avoid: [faceBox] });   // over the image; boxes in its pixels (locate.py)
an.underline([419, 295, 92, 15], t);         // { double: true }
an.circle([815, 516, 72, 24], t, { pad: 14 });
an.highlight([x, y, w, h], t);               // highlighter sweep, multiply blend
an.scribble([x, y, w, h], t);                // scratch it out    an.strike(box, t)   an.box(box, t)
an.arrow([x0, y0], [x1, y1], t, { bend: 0.22 });
an.note(x, y, "split 2 ways", t, { size: 56, rotate: -3 });                    // Excalifont, written on
// every call: { dur, size, color, seed, until, sfx: false }; an.clear(t)
```
Put the annotated element and the `annotate` view in one parent and give neither a z-index or opacity of its own,
or the highlighter's multiply has nothing to multiply with (in the demo: `G1` holds the window and the marks).

**How it stays exact**: every mark is an authored point list (seeded wobble, a pressure curve: quick press, slight
swell, lift). At time t the visible part is `getStroke(points.slice(0, n(t)) + one interpolated point, { last: done })`,
a filled outline polygon (so no dash-offset), recomputed in `K.onFrame` only while it is drawing.

**Cheap-look risks**: perfect circles (use the default overshoot), marks wider than 12 px at 1080 wide, more than one
colour on one screenshot, notes longer than three words, highlighter on a dark theme (multiply vanishes: use an
underline), marks on text that is too small to read anyway (zoom first).

### 3. Scribble outline (`scribble.js` + `tools/scribble.py`)

**When to use (the rule)**: to make the speaker the subject of a beat for 2–4 s: the hook, a strong opinion, "this
is me", a reaction. One or two per video. Pick a clip with stable framing (1–3 s of one position is ideal); fast head
turns and hands near the face cost quality. Not over a busy screen recording, never with captions over the face.

```sh
python3 kit/hf/tools/scribble.py work/clip.mp4 work/outline.json --expand 14 --amp 5 --passes 2 --preview work/outline_sheet.jpg
```
Look at the preview sheet (every 4th step drawn on its frame) before using it: blobs at hair or hands show there.
`--open N` removes protrusions thinner than N px (fingers, hair wisps); `--temporal union` (default) keeps the line
outside the person through a whole 12 fps step, so a fast turn never puts it on the face. If the line still touches a
cheek on a fast turn (motion blur shrinks the matte), raise `--expand` (the demo uses 20).

```js
// build.py inlines the JSON: const S = {...}
HF.scribble(K, panel, S, { at: clipStart, box: [x, y, w, h], from: clipStart + 0.25, until: end, width: 8, draw: 0.75, erase: 0.3 });
// box = where the clip's full source frame sits in `panel` (the same box as the <video>); color "#fff" on dark footage
```

**How it stays exact**: everything is offline: personseg mattes at 12 fps (taken mid-step), union over neighbouring
steps, blur, largest blob, holes filled, a round expansion of 10–16 px, `findContours`, the runs along the frame
border removed (the line stays open where the body leaves the frame), resampled, smoothed, then a seeded jitter per
step (three low-frequency sines + a little grain) and slight overshoot at the ends. The page builds every step's
path once (Catmull-Rom → cubic) and a `K.onFrame` sets the path of `floor((t - at) * 12)` and the DrawSVG range
(draw on, hold, draw off), with the pen also on the 12 fps grid.

**Cheap-look risks**: an outline that hugs the matte (looks like a bad cut-out: keep `--expand` ≥ 10); a line
crossing the face on fast moves (`--temporal union`, or pick a calmer clip); a thick single line (two passes at
8 px + a thin second pass read as drawn); holding it longer than ~4 s (it stops being an accent).

### 4. Paper collage (`collage.js`)

**When to use (the rule)**: a comparison or a "here is the evidence" beat built from *real* screenshots: two app
screens side by side, a headline and its source, a before/after. One collage per video, 5–8 s, 3–7 pieces. Not for
a live demo (use `screen.js`) and not for code (unreadable when torn and tilted).

```js
const cg = HF.collage(K, layer, { w: 1080, h: 1920, seed: 23 });   // options: perspective, board, mottle, grain, grainOpacity
const A = cg.piece({ x, y, w, h, z: 20, rot: -5, img: "assets/low.jpg", torn: "tb", tape: ["top"], print: 0.22 });  // torn: t|r|b|l|all; tape sides top|bottom|tl|tr|bl|br
const s1 = cg.strip("Same prompt.", { x, y, size: 100, rot: -3, z: 120, w: 560, h: 146 });    // a torn strip with words; italic, color, font, bg
const d = cg.halftone({ x: 800, y: 760, r: 330, z: -120, color: C.acc });
cg.enter(A, t, { from: "drop" });            // drop | pop | left | right | up | down, on twos
cg.move(t, { x: 0, y: -14, z: 55, ry: -2.5, rx: 1.5, dur: 7, ease: "sine.inOut" });           // the camera
cg.show(a, b);  cg.exit(A, t);
```

**How it stays exact**: torn edges (an outer paper outline and an inner printed face, so a white fibre rim shows on
torn edges), tape ends and halftone dot sizes are generated once from the seed; the grain and board mottling are SVG
`feTurbulence` with fixed seeds (static). Piece entrances live on a child timeline that a `K.onFrame` drives with
`child.time(floor(t*12)/12)` (motion on twos); resting pieces get a sub-pixel nudge per step from a prebuilt table.
The camera rig is moved by `fromTo` tweens on the main timeline (smooth), so the pieces at different `z` parallax
against each other and the oversized board behind them.

**Cheap-look risks**: too many pieces or tapes (clutter); all pieces at the same angle; stock-looking textures (keep
grain under ~0.5 opacity and the board mottle subtle); upscaled small screenshots (keep scale ≤ 1.2, the `print` dots
hide a little softness); a camera push so deep the outer pieces leave the frame (the demo ends at `z: 55`).

### Libraries and licences

| What | Licence | Where |
|---|---|---|
| rough.js 4.6.6 | MIT | `npm i` at the repo root; `vendor/rough.js` (external file: it contains `Math.random`, unused with a seed) |
| perfect-freehand 1.2.3 | MIT | `npm i`; vendored as `vendor/perfect-freehand.js` (the CJS build wrapped to set `window.PerfectFreehand`) |
| GSAP DrawSVGPlugin 3.15 | GSAP standard licence (free, including plugins, since 2025) | `node_modules/gsap/dist`; `vendor/DrawSVGPlugin.min.js` |
| Excalifont (Latin subset) | SIL OFL 1.1 | `kit/fonts/Excalifont-Regular.woff2`, from excalidraw's GitHub; licence in `kit/fonts/licenses/Excalifont-OFL.txt` |
| Caveat 700 (fallback hand) | SIL OFL 1.1 | `kit/fonts/Caveat-700.ttf` (already in the kit) |
| diagram-design 2.6 (rules, and a port of its `verify-geometry.py` as `HF.diagram.verify`; nothing vendored) | MIT | notice in `kit/hf/lib/diagram-design.LICENSE`; the rules in `kit/refs/DIAGRAMS.md` |

Excalifont's Latin file covers U+20–7E and Latin-1 (no arrows or ✓: draw those as strokes). `vendor.py` copies the
libraries with `copy_libs()` and skips (with a warning) any that isn't installed.

## v7 camera: motion vocabulary, director, motion blur (`motion.js`, `HF.camera`, `kit/motion/camera.py`)

The speaker's camera used to put a new framing on every cut (1.0 / 1.08 A/B/A/B) with a constant drift. Version 7
replaces it with a small vocabulary of moves used the way top editors use them, and a **director** that picks them
from the edit. `HF.camera` keeps its call signature.

### The vocabulary (`HF.motion.RULES.long`; `reel` in brackets)

| Move | Scale | Timing | Easing | Blur | The director uses it |
|---|---|---|---|---|---|
| reframe (hard cut) | W 1.00 ↔ 1.15 (panel 1.00 ↔ 1.15) | 0 f, held ≥ 3 s (1.5 s) | none | none | at a new thought: a sentence start or a scene change; never mid-sentence; never on every cut |
| punch (hard cut) | 1.22-1.32 (1.28-1.40), and ≥ 1.1x every framing it cuts from or to | 2 f before the stressed word, held to the end of the line (0.8-3.2 s) | none | none | `punch`/`punchline` tags, then guesses (numbers, $/%, "never", "best", a word said three times); 1 per 16 s (6 s) |
| ease (eased punch) | x1.18 (x1.2) | 15 f (12 f) | power3.out | 180°, ≤ 8 samples | `ease` tags, and the second of two punches in a row |
| snap (crash zoom) | 1.4 (1.5) + 3% overshoot | 5 f (4 f), settles in 8 f | expo out (.16,1,.3,1) | 270°, ≤ 24 samples | `joke` tags (a reaction beat), with a swish; ≥ 25 s apart (10 s) |
| landing shake | 1% of the height (1.2%), ≤ 0.4° (0.5°) | 7 f, exponential decay | 9 / 11.3 / 7.4 Hz sines, zero phase | as the snap | on every snap's landing, clamped to the slack so no edge shows |
| push (slow push) | +5-10% (~1.2 %/s) | the thought, 4-14 s | sine in-out (.37,0,.63,1) | none | `story` tags, then the longest thoughts, ≥ 30 s apart (15 s); then a hard cut back out |
| zoomx (zoom transition) | 100 → 300% → 100% | 6 f out + 6 f in | expo in / expo out | 330°, ≤ 32 samples | `section` tags only (a chapter change), with a swish |
| drift | +0.6 %/s easing out at +3% | every held framing | exponential ease-out | none | always (a held shot is never a still) |

**Director rules**: framings change only at new thoughts and only after a hold; consecutive cuts inside a thought keep
the framing (a plain jump cut, face-locked); no hard cut between framings less than 1.1x apart (it reads as a glitch:
the punch goes further or the cut back picks the other framing); a punch that starts within 0.6 s of a cut moves onto
the cut, and one that would end within 0.6 s of the next cut ends on it (no double cuts); an ease or snap that opens a
thought starts from the framing before it (one move, not a cut plus a move); never the same move twice in a row
(punch ↔ ease, a second snap eases, a second push is dropped); moves stay 0.7 s clear of layout changes and 3 s clear
of zoom transitions; side layouts (SR/SL) get reframes, pushes and gentle punches (x1.12) only; PIP/OFF get none.
`P.log` (and `window.__camera` in the page) lists every decision with its reason.

**Composition**: the face anchor is the eyes (YuNet: 0.20 head widths above the box centre); the eyes sit on the upper
third unless that would crop the hair (top of the hair 1.1 head widths up, plus 3% headroom), at the layout's x (W/M/C
centre, SR right, SL left), clamped so the picture always covers the frame. Scale is interpolated in log space and
the eyes move in a straight line, so the face never swims during a zoom.

**Tags** (word ids, the film's own numbering): `{ punch: [...], punchline: [...], ease: [...], joke: [...],
story: [[first, last], ...], section: [...] }`. `auto: false` keeps only tagged moves. Sentence starts come from the
transcript's punctuation, so fix run-on transcripts (`.` per thought) before directing.

**9:16 panel Reels with several full-screen beats** (films/mutual-funds, 2026-10-09): in `mode: "panel"`, `framing`
maps piece tags to `"P"` (the face in the lower panel from `top`) or `"H"` (full screen); without it only `hook` is
full screen. `fullMoves: true` lets tagged moves play in the full-screen beats too (the hook alone stays still);
`hScale` sets the full-screen scale (default 1.08; 1.0 shows the whole take, for a close selfie whose face fills
the frame); `layoutPad` (default 0.7 s) is how far a move stays from a layout change (0: a crash zoom may hold up to
the cut into a panel).

### Motion blur: baked in Python (measured)

A fast move needs motion blur: the average of N sub-frame transforms of the same source frame (sample times
t + (k/(N-1) - 0.5) x shutter/360/fps, never across a cut; N = ceil(largest on-screen travel / 1.5 px), capped per move,
none under 1 px). Two ways were built and measured on the same 4 s test (a snap and an eased punch, 26 blur frames,
1080p, against an exact float reference):

| | luma PSNR | mean / p99.9 error | cost | |
|---|---|---|---|---|
| (a) in the page: N stacked copies of the A-roll, copy k at opacity 1/(k+1) | 45.5 dB | 1.00 / 6.0 | +40% capture time for the clip (~0.45 s extra per blur frame); one `<video>` per sample per window (65 for 2 windows) | 8-bit blending; DOM grows with N x windows |
| (b) **baked**: `kit/motion/camera.py`, cv2.warpAffine (bilinear, sub-pixel) + float32 sum | **47.1 dB** | **0.81 / 4.8** | ~11 ms CPU per sample (≈ 1.5 s for a snap); one small all-intra clip per film (6 MB for the demo's 37 frames) and one `<video>` per window | exact |
| no blur (for scale) | 32.7 dB | 4.29 / 50.6 | | |

(b) is the camera's path: as exact as the reference allows, cheap, and it keeps the page small. The page and the bake
run the same `motion.js` (Node runs it in a sandbox through `kit/motion/plan.cjs`), so the baked frames continue the
browser's frames exactly. Without a bake the moves still play, unblurred, and `HF.camera` warns in the console.

### Adopting it in a film

```python
# build.py
sys.path.insert(0, str(ROOT / "kit/motion")); import camera
P = camera.plan({"pieces": pieces, "words": words, "fps": 30, "view": [1920, 1080], "framing": framing,
                 "format": "long", "tags": {"punchline": [2512], "joke": [2427], "story": [[2471, 2502]], "section": [2593]}})
blur = camera.bake(HERE / "assets/aroll.mp4", P, HERE / "assets/aroll_motion")   # after the A-roll asset is final
D["camera"] = camera.for_page(P, blur)                                              # src paths are "assets/..."
print("\n".join(P["log"]))
```
```js
// template.html
HF.camera(K, st, { plan: D.camera, pipRadius: 158 });
// 9:16: camera.plan({..., mode: "panel", top: 880, width: 1080, height: 1920, format: "reel", hook: [0, hookEnd]})
```
- Pieces need `face` = [cx, cy, size] from a YuNet track (kit/look/faces.py); words need `i, text, t, e`.
- Don't tween `st.wrap` (or `cam` top/height in panel mode) in the template: the camera writes them every frame. To own
  the wrap for a while (a custom hook), pass `active: [a, b]`.
- Re-run the bake whenever the A-roll or the plan changes (the clip holds finished frames).

**Gotchas found here**: HyperFrames picks a clip frame as floor(time x fps), and `77/30` printed as `2.56667` is past
the frame, so a clip starting off a whole second repeats its 2nd frame (the camera gives windows a 0.1-frame lead).
A rawvideo pipe into ffmpeg must carry the output's colour tags on the input, or swscale converts the matrix (luma
-1.5 levels). The repo's `package.json` is `"type": "module"`, so Node helpers that load browser scripts are `.cjs`.

## The lens: the camera on him inside every shape (`motion.js` HF.motion.lens, 2026-10-22, v11)

The owner (2026-10-22): "I'm not seeing dynamic zoom". `HF.camera` above frames a full-frame A-roll. The lens is the
camera on his footage *inside* whatever shape shows it: a canvas circle or card, the seated `frame`, or an `HF.box`
full frame or card. The shape moves on the stage (canvas shots, box moves) and the lens moves the picture inside it, so
the two compose: use both. Only `HF.camera`'s layouts and `HF.box` on the same `<video>` still exclude each other,
because both write its transform. It is pure and seek-exact (no randomness); `tests/test_lens.py` runs it in node.

**What it does** (the decisions of 2026-10-22):
- **One move per thought.** It changes the framing every 4-8 s while he is on. A steady hold is cut into segments at
  sentence ends (and at the visual plan's passage starts), with one move each and never the same move twice in a row:
  - push +6-12 % across the thought (sine, scale in log space);
  - pull-out back to the base, from a framing at least 6 % in (a smaller pull reads as drift);
  - arc: truck ≤ 3 % of the shape, roll ≤ 0.6°, scale +4 % (a slider moving around a seated speaker);
  - settle: 1.04 → 1.0 in 1.2 s after a shape move, a whip or a takeover.

  "Never twice in a row" counts the thought moves only: a settle is not a break. Each thought takes the move the
  framing allows that played longest ago (push, arc, pull), so all three come round when his shape changes every
  5-8 s. A hold that opens on a pull-out lands on a closer framing (+9 %) and pulls out from it (review 2026-10-22:
  every hold used to go settle > push). A hold under 2.5 s keeps its framing. There is no handheld shake. While the
  canvas whips, the lens holds still (the whip is the move), then it settles.
- **Punches on stressed words.** ×1.15 over 13 frames (power3.out), landing on the word (the cut's own word times:
  TIME_FIX'd and respelled). It holds to the end of the sentence (0.8-3.2 s) and releases over 0.5 s. At most one
  every 12 s, never within 0.7 s of a shape move or a whip. Candidates come from:
  - `say()` stress ids (HF.studio / HF.reel);
  - `D.lens.stress` (film.py `STRESS`, plus the visual plan's `{ "at": id, "punch": true }` beats);
  - a plan passage's `"cam": "punch"` (its `"punch": <word id>`, else the passage's strongest word).

  A punch is a factor on the framing in force (the base lens times a jump reframe), and it is never smaller than
  ×1.12 on screen: the step from the frame before its ease-in to the word (the decision: ×1.12-1.18). A hold with a
  candidate keeps ×1.12 of its budget free for it: the base lens moves under `kmax / 1.12`, as long as that still
  leaves it a ×1.06 move. A join before the punch keeps that room too: its in-step stops where the punch still gets
  ×1.12, else it goes out or stays a bare cut (logged: "the punch on "critic" at 7.29 needs its x1.12 on top"). In a
  tighter budget the base keeps its room (the moves are the owner's ask), and a punch lands only where the framing is
  low enough. Otherwise it is skipped and logged ("punch "critic" skipped: the zoom budget pays x1.018 there"). The
  budget is sized before the 12 s gap, so a candidate that can't play never holds a slot, and a gap skip is logged
  too (review 2026-10-22: a logged ×1.15 showed ×1.02-1.05 after an in-step, and a dropped candidate hid a later one).
- **Jump cuts: the one kit reframe** (`HF.motion.jumps`). A picture join inside a hold becomes an eased 0.25 s
  reframe. Wide and close alternate: ×1.1 in when the budget has room, else ÷1.1 out from a base that is already
  zoomed in. A join under a punch that plays hides in it. There is none within 0.45 s of a move, none in shapes under
  240 px, and none under ×1.06 (smaller reads as a glitch). It replaces the films' inline "every other join ×1.12"
  loops: with the lens on, HF.studio and HF.reel stop adding `HF.box.jumpShots` hard steps. A canvas film rebuilt
  with its loop still in the template keeps working: a `cut: true` shot with the same mode and shape as the shot
  before it is one lens hold with it, so the lens carries across the join and the template's ×1.12 step shows whole
  (the lens adds no reframe there; logged "the template's own cut shot reframes it"). The hold's budget is the closer
  framing's, so the lens moves less there. Drop the loop for the eased reframe.
  - **No join plays bare for lack of budget.** When the sharp budget can't pay ×1.06, the in-step spends the track's
    soft allowance (tracks.json's soft rule; ×1.1, capped by it), and so does the step back. On a 4K render that is
    every full frame and every card on a 1080 track, where the pre-v11 kit stepped ×1.12 anyway. The log says so, and
    `window.__speaker` reports `soft: true` with `max_zoom` = that allowance while it holds.
    `LENS = dict(rules={"jump": {"soft": False}})` keeps the sharp cap; such a join then stays a bare cut (logged).
  - **HF.box keeps its drift where the lens is still.** The box's linear 3 % drift goes only from the holds the lens
    moves; a hold it leaves still (no budget, a short hold) keeps it, also counted against the soft allowance. So
    turning the lens on never takes away motion a box film had.
- **Eye-anchored, clamped, budgeted.**
  - The zoom keeps his eyes where the template put them. Eyes are the face track's median over the hold, 0.2 head
    widths above the YuNet centre; without a face track, the shot's `at`. The canvas reads the face track from
    `D.lens.faces`, in the face track's own px (`faces_px` its size, scaled to the speaker's `src`). It never reads
    `D.faces`: on a Reel those are in the film's page px, for HF.reel's box. Read as track px, a Reel's lens anchored
    ×1.78 off his face (review 2026-10-22).
  - The picture always covers its shape, and stays inside a clean rect when the shot has one. In a 16:9 rect a roll
    costs about 3 % zoom per degree, and the lens adds it; a circle rolls free.
  - It never zooms past the source's budget. `D.tracks[track]` (work/tracks.json) gives `sharp_px`, so each shape gets
    its own cap: `max(1, sharp_px / the footage's height at cover)`. A circle has more headroom than full frame. Without
    a tracks.json entry the cap is 1.2. A tight budget shrinks the moves; it never breaks the cap. Under ×1.03 of room
    the base lens holds still (logged).
- **Amplitude follows the shape.** Nothing under 240 px, 40 % at 240 px and 100 % from 540 px (a fast move in a small
  circle reads as jitter). Punches need 360 px. `calm` scales everything (0.6 is calmer).

**Defaults and options.** kit/film's build writes `D.lens = { on, track: FACE_TRACK, fps, stress, plan, faces,
faces_px, calm?, budget?, rules? }`. `LENS` in film.py wins when it is set: `False` is off, `True` or any dict is on
with those options (`{}` included), e.g. `LENS = dict(calm=0.6, budget="soft")`. Unset (`None`, the config default),
the lens follows the film's date like the v11 sound: on for a film (a Reel: its own template) made on or after
kit/film/mix.py `V11_FROM` (2026-10-22), off before, so rebuilding a delivered film adds no lens moves to it (build
prints `lens: on|off (LENS in film.py | made on <d>, v11 from 2026-10-22)`). It also writes `D.tracks` (each track's
file plus its tracks.json entry, `kinds` included). `D.faces` is unchanged: a Reel's edl faces in page px. The canvas
speaker on `D.lens.track` and the HF.box of HF.studio / HF.reel pick it up. Per call:
`C.speaker(id, shots, { lens: false | { calm, budget, track, stress, plan, faces, faces_px } })` and `S.box({ lens })`.

**The budget is per kind of footage** (`HF.motion.holdBudget`): each hold reads the tracks.json `kinds[kind]` entry of
the footage playing in it (`D.pieces[].kind` over the hold's span; the poorest kind inside that span), not the track's
top level (the poorest kind of the whole track). v11-sample's face track: the selfie (`cam`, sharp 1080 px) in the
1680 × 945 frame card gets ×1.143, while the bubble (`chrome`, 162 px) keeps ×1.0. Without `kinds` (or without
`D.pieces`) the track's top level is read, as before. `__speaker.max_zoom` publishes the cap in force.

`budget` is one of:
- `"auto"` (default; unset is the same): sharp in cards, circles and corners; at full bleed (a `{ mode: "frame",
  full: true }` shot, a card the size of the page, a full HF.box) the lens's own moves and punches spend the soft tier
  (`soft_zoom`: at most ×1.24 on a native 4K track, ×1.12 on a 1080 one). One constant, `HF.motion.LENS.full = "soft"`;
  set it to `"sharp"` to flip the kit back;
- `"sharp"`: tracks.json's `max_zoom` rule everywhere, sharp at the render size (`LENS = dict(budget="sharp")` per
  film). Only a jump-cut reframe it can't pay reaches into the soft allowance (above);
- `"soft"`: its `soft_zoom` rule, mild softness accepted, for every move in every shape;
- a number: a fixed cap, for everything (no soft fallback).

> **Full bleed spends the soft tier** (E-M2, 2026-10-23; owner sign-off pending, raised with the v11 delivery). Under
> strict sharp, every source has `max_zoom` 1.0 at full height on a 4K render, so push, pull, arc and punch held still
> at full bleed, the owner's "visible camera moves on him" ask. v11-sample (a fixed `budget=1.2`) shows how the soft
> tier looks. Cards and circles stay sharp; precheck measures against the cap the page publishes (`max_zoom`).

Off (an old page, or `LENS = False`), every page draws exactly what it drew before. Video transforms, boxes and
`__faceRect` are byte-identical on 9 built films, and the screenshots are pixel-identical up to the renderer's own ±1-3
noise (the evidence is in the v11 build notes).

```js
const L = HF.motion.lens({ holds: [{ t0, t1, w, h, kmax, enter: "start" | "move" | "cut" | "back", open }], words,
                           stress: [ids], plan: [{ a, b, cam, punch }], cuts: [t], whips: [[a, b]], fps, calm });
L.at(t, u)    // -> { k, dx, dy, rot, move, soft }; between two holds it blends their ends by u (the shape's own ease)
L.log         // every decision: "12.30 lens push x1.000->x1.091 until 18.00", "punch x1.15 landing on ...", skipped ones
L.holds       // with h.still on a hold the base lens leaves still (HF.box keeps its drift there)
HF.motion.lensFrame({ bw, bh, vs, vx, vy, circle }, L.at(t), { src, eye, rect, smax })   // -> { m (CSS matrix), s, rot, zoom }
HF.motion.lensBudget(D.tracks.face, heightAtCover, cover, vs, "sharp")                   // -> { zoom, kmax }
HF.motion.jumps(cuts, holds, { punches, whips, rules, log })   // the one jump-cut reframe, for a page without the lens
HF.box.speakerKind(S, W, H)          // -> { on, kind }: is his face on screen in a box state (the tint decides)
HF.canvas.frameBox(shot, W, H)       // the seated frame's shape; HF.canvas.cleanRect(clean, clip, full): the take's rect
window.__lens[id]   // the page's plans (canvas: by speaker id; HF.box: "box"), for checks and the precheck log
```

Holds take `ksoft` (the soft allowance as a cap on k) beside `kmax`. Only a soft jump reframe uses it.

**The seated frame on canvas** (`mode: "frame"`). The large card's default size follows the page: 87.5 % of its
width, 16:9 on a landscape page (1680 × 945 at 1920) and 4:5 on a portrait one (945 × 1181 at 1080). A per-take
clean rect (`clean: { <clip>: [x0, y0, x1, y1] }`) follows the piece playing: a cut into another take re-crops on
the cut, where the lens reframes anyway. While his shape moves into a shot, the clamp rect blends from the last
shot's to the new one with the move, so a new clean rect never snaps the old framing in one frame (review 2026-10-22:
a circle → clean frame card jumped his face 113 px on the move's first frame). A frame shot whose clean rect is too
small for its aspect frames past the zoom budget on its own; the page says so once (`console.warn` and
`window.__lens[id].log`: "frame shot 0: its clean rect frames x2.67 over cover, past the zoom budget x2.00: loosen
the rect or use a card").

### `window.__speaker` (the engine contract; kit/qa/speaker.mjs reads it)

Every frame engine publishes `window.__speaker = (t) => ({ on, kind, rect, face, zoom, lens, track, max_zoom, soft })`.
Today that is `canvas.js` and `box.js` (HF.studio / HF.reel), `redline.js` (`R.face`: full, card, or corner for its pip
and corner slots; `R.cutout`: full) and HF.camera pages (scenes.js, through a wrapper in `trans.js`: full, card, corner
for PIP, off for OFF; `lens` is "push" or "punch" during those moves and "" otherwise, since HF.camera declares no
holds and precheck should judge its framing). During a takeover (next section) every engine reports `kind: "off"`. On canvas the primary speaker reports: `fo.primary`,
else the page's face track (the speaker whose id is `D.lens.track`), else the last `C.speaker` call. A screen
recording added after his own speaker no longer takes it. The fields:
- `on`: his face is visible. In a box, that means shown and not under the accent wash (`tint` < 0.5). The tint
  decides, not the pill flag: HF.reel's face `CIRCLE { pill: 1 }` is him.
- `kind`: `"full" | "frame" | "card" | "circle" | "corner" | "off"`. On canvas: full bleed is `full`, the large seated
  card `frame`, a `card` with `r` = half its side `circle`, and a shape under 10 % of the frame `corner`. In a box: a
  square pill is `circle`.
- `rect`: his shape in page px.
- `face`: his head box in page px, as `__faceRect`'s, so through the lens.
- `zoom`: the footage's total scale over cover, lens included.
- `lens`: `"push" | "pull" | "punch" | "arc" | "settle" | "hold" | ""`.
- `track`: its tracks.json name.
- `max_zoom`: the cap in force at this shape, or null without tracks.json. That is the sharp budget, or the soft
  allowance while `soft` is true: a soft jump reframe, or a box hold's drift where the lens is still.
- `soft`: the soft allowance is in force (above).

`window.__faceRect` keeps working as before, and includes the lens when it is on. With the lens, its head centre is
kept inside his shape, so the rect is never inverted. While a box is hidden and another engine's `__faceRect` sees him
(a Reel that plays the A-roll itself), the box reports him on, as `full`.

## Takeovers and transitions (`trans.js`, 2026-10-22, v11)

The owner asked for "out-of-the-box full-screen animation scenes where he is removed completely", and for better cuts
and transitions. A **takeover** gives the whole frame to one scene while he is off: absent, never cut out, his voice
carrying on under it (no word moves). A **transition** moves from one scene to the next and means something. Both are
pure functions of time on the paused timeline: seeking forward, backward or straight to a frame gives the same page
(tests/test_takeover.py checks it).

**A takeover**

```js
const tk = C.takeover(a, b, { kind: "type", text: "Neat beats *busy.*", kicker: "the rule", mark: { word: 0, t, kind: "underline" } });   // HF.canvas
const tk = S.takeover(a, b, { kind: "list", title: "Three things", items: [["cuts on whole sentences", t1], ...], in: "card" });        // HF.studio / HF.reel
```

| kind | what it shows | options |
|---|---|---|
| `type` | a statement: big type, one accent mark (the copy-pasted HERO blocks of chakra-redline / oss-editor are this kind) | `text` (`\|` breaks a line, `*word` accents), `kicker`, `sub`, `mark: { word, t, kind: "underline" \| "strike" }`, `then: { text, at, size }` (a second line that cascades in, 0.55 of the statement's size and fitted to the frame's width like the statement: `HF.takeover.typeFit`), `size`, `align` |
| `diagram` | a system diagram that builds with HF.diagram: **flat** on whitespace (below, "Flat diagrams"), icon circles with v11's margin and fanned reverse ports elsewhere | `nodes: [{ id, label, icon, at }]` (flat also `sub`, `mono`, `tag`, `focal`, `kind`), `edges: [[from, to, t]]` or `{ from, to, t, route, label, accent }`, `focus: [[id, t]]` (`"*"` = the overview), `flows`, `title` (a kicker; flat: its eyebrow), `layout` (flat also `"hub"` with `hub`), `type`, `style` / `shape` |
| `evidence` | a close-up of a window or screenshot with one highlighter mark; the camera leans into the mark as far as the window and its source line stay in frame | `img` or `html` (a generic mock-up: no real logos), `url`, `mark: [x, y, w, h]` (the window body's px), `markAt`, `note` (the source line), `noteAt`, `w`, `h` |
| `list` | 3-4 points landing on their words, on one card; the point being said is ink, the ones before it step back to sub | `kicker`, `title`, `items: [[text, t], ...]` |
| `chapter` | T.chapter's white beat | `num`, `title` |

`{ mount: "name" }` puts a catalog piece (film.py MOUNTS) full frame in it; `{ build: (L, tk) => parts }` draws any
scene into `L` (a frame-sized layer in screen px under the takeover's own camera). Every kind has motion inside: the
takeover's camera pushes 3.5 % while it holds (`push`), and the evidence kind leans into its mark. Text follows the white
look's floor: body 32 px or more, the kicker 26-30 px mono caps in sub (class `mono`).

`tk = { a, b, root, plate, L, cam, parts, main }`: `tk.cam.cam(t, { x, y, z }, { dur, ease })` and `tk.cam.hold(a, b, dz)`
move the scene's camera (keyed in log space for zoom, with speed blur). `parts` are the kind's elements (`main`, `line`,
`words`, `card`, `rows`, `win`, `mark`, `note`, `dg`, `nodes`), so the transitions below can name them.

**In and out** (`in`, `out`; each is logged to `window.__trans` with its kind):

| | canvas (`C.takeover`) | HF.studio / HF.reel (`S.takeover`) |
|---|---|---|
| `in: "cut"` (default) | the scene is there on the cut | the box cuts off |
| `in: "fade"` | the scene fades in over 0.35 s while his shape fades out | the box dissolves |
| `in: "zoom"` (default with `from`) | the camera dives ~3x into `from` (an element of the canvas, or `"eyes"`: his face when his shape is 500 px or larger), expo.in 0.3 s, and cuts on the peak to the scene, which arrives from 3x (expo.out 0.45 s) | a hard cut, the scene arrives from 3x |
| `in: "card"` | his card morphs into the scene's first card (`card` or `parts.main`) over 0.55 s; a plate in that card's colour, made opaque, covers the whole shape as it lands, never a transparent edge | the box collapses into the pill and the scene's card grows out of it |
| `in: "match"` | `match: el` (an element of the canvas) flies as a clone onto the scene's first element (T.match); out of a full-bleed frame, name an element he does not cover (it would appear out of nowhere) | (not offered) |
| `out: "fade"` (default) | the scene fades over 0.4 s and leaves toward the viewer while his shape fades back in | the scene fades; the box fades his previous shape back in where it lands |
| `out: "cut"` | gone on the cut frame | the box cuts back |
| `out: "zoom"` | the scene's camera dives into `into` (a part's name, an element, or `(parts) => el`) and the canvas lands on `to` (`[x, y]`, `{ x, y, z }` or a station element) from 3x | the scene dives into `into`, the box cuts back |
| `out: "card"` | his card grows back out of the scene's last card (`cardOut`) | (not offered) |

**His shape.** On a canvas the takeover writes his shots for him, whichever is called first (`C.speaker` re-plans when a
takeover comes after it; declare takeovers first for exact sound, since a dropped shot's whoosh is already queued):
an off shot at `a` (after the morph for `in: "card"`), every template shot in `[a, b)` dropped, and at `b` the shape he
had before `a` (a template shot within 0.05 s of `b` is the return instead). A dropped shot is said once in the console,
in `window.__lens[id].log` and in `window.__takeovers[i].dropped` (`[{ speaker, t }]`); one within 0.35 s before `b` is
named as a likely mis-timed return. Every speaker on the canvas leaves for a takeover, but only the primary one (the one
`window.__speaker` reports: `fo.primary`, else the page's face track, else the last `C.speaker` call) morphs in
`in: "card"` / `out: "card"`; any other speaker (a screen recording beside him) fades off and back over the same time,
and a speaker that is already off at `a` stays off, with no morph and no return, until its own next shot.
`T.cardToGraphic` moves the primary speaker only (`HF.canvas.takeoverShots(shots, tks, { morph })` is the pure merge).
**Out of and back into a full-bleed frame.** When a shape covers the whole frame as the takeover starts (his seated
frame with `full: true`, or a card the size of the page) or as he comes back, the canvas under it was never on screen:
the plate is opaque from `a` (and until `b` + the out's time) and only his shape moves over the scene, so `in: "fade"`
/ `out: "fade"` are a true dissolve between his face and the scene, `in: "card"` is his frame shrinking into the card
on paper, `out: "card"` his frame growing back out of it, and nothing his frame hid shows through (review 2026-10-22:
station copy ghosted over his face for 0.3-0.55 s). The canvas asks each speaker (`C._covers(t)`) lazily, so the order
of the calls doesn't matter; the stage (a cut-out) never covers. **Takeovers may not overlap**: `C.takeover`,
`S.takeover` and `T.cardToGraphic` with `until` throw when their span overlaps another one's (the second would read him
as already off, and nothing would bring him back), and warn under 3 s of his face between two. `T.chapter`'s downbeat
snap never moves `t0` onto another takeover.
On HF.studio / HF.reel it is a box beat: `beat(a, "takeover", { until: b })` (`HF.box.takeoverBeats`: the beats inside
are dropped, his previous show comes back at `until`; a blended return is first put on its own slot, so it never grows
out of the pill a collapse left). Declare `S.takeover` before `S.box()`: the director reads the beats once there, so a
later call throws. `window.__speaker` reports `kind: "off"` while he is gone and `window.__faceRect` returns null; the
lens starts a new hold when he is back (`enter: "back"`).

Layers on a canvas: the takeover sits at z 3, over the canvas view (z 2, hidden while the plate covers it, from `a`
when a full-bleed shape hands over, so precheck reads only what can be seen; `view: false` leaves C.view to the
template) and under his shape (z 4), so his card can
morph into the scene above the plate. The plate is the look's paper (`C.PAPER.seamless`; `paper` overrides). On
HF.studio / HF.reel the scene sits on BACK under the box, on a plate of the frame's world (white on whitespace; none on
pastel_box, whose aurora stays alive; `plate: false` for none).

Budgets (kit/refs/SCENES.md §9; plan_check plans them, precheck measures them): long-form 15-30 % of the runtime in
takeovers of 4-12 s each (a takeover outside 4-12 s is named in the console), at least 3 s of his face between two, the
hook opens on his face, never away more than 12 s, and no layout over 35 % ("off (takeover)" is one layout).

**Transitions** (`const T = HF.trans(K, C)` on a canvas; `S.trans()` on HF.studio / HF.reel):
- `T.zoomThrough(t, el, to)`: the camera zooms ~3x into `el` (expo.in 0.3 s), hard-cuts on the peak at `t` to `to`
  (a canvas camera `[x, y]` / `{ x, y, z }` or a station element; inside a takeover, a point of its scene), which
  arrives from 3x (expo.out 0.45 s). Speed blur on both sides, capped at 10 px on the view so the element stays a shape
  into the cut; his shape zooms and blurs with the frame (a camera move: the decided "motion blur only from fast
  camera moves"). The zoom is a page-point zoom of the view and his shape together (`C._zoom`), and the lens and his
  shape's ride count it as a whip.
- `T.match(t, elA, elB, { cut })`: a box flies from `elA`'s rect onto `elB`'s (FLIP, 0.5 s power3.inOut) while the
  camera cuts underneath to `cut`. The box carries the two skins (background, border, shadow) cross-fading, its corner
  eased as a share of its shorter side (a pill becomes a card's corner on the way), and inside it each one's content
  at ONE scale, centred, cross-fading in the middle: type never stretches when the rects differ in aspect (review
  2026-10-22: a chip's label flew 2x taller than wide). Both elements are hidden while it flies (clip-path, the one
  property the kit never tweens). Rects are layout px through the camera at fixed times (`HF.trans.rectAt`): flat
  stations only (a card's own 3D turn is ignored).
- `T.chapter(t0, t1, { num, title, from, to })`: zoom through the outgoing anchor (`from`; his eyes when his shape is
  500 px or larger) into a white chapter beat holding `num` and 2-4 words for 1.2-2.2 s (warned outside), one soft
  whoosh (-19 dB) and a low hit (-18 dB); `t0` snaps to the nearest downbeat within 0.12 s when D.music exists (the
  graphics move, never the cut). Only `t0` moves: `t1` stays where the template put it, so the template's shot at `t1`
  is still his return, and the hold changes by the snap (warned outside 1.2-2.2 s). `to`: the camera it zooms out onto;
  without it, a cut.
- `T.cardToGraphic(t, el, { until, back })`: his card morphs into `el`'s frame (the covering plate again), then `el` is
  the graphic; at `until` his card grows back out of `back` (default `el`). Canvas only; on HF.studio / HF.reel the
  box's collapse + `S.fromPill` is the same move.
- `T.whip(t, to)` / `T.cut(t, to)`: a logged canvas whip or hard cut (a hard cut takes no blur from the jump).

**The budget.** Every transition is logged to `window.__trans` (a function: `HF.trans.list()`, `[{ t, kind, why }]`),
the canvas camera's own moves included, read from `C.cam`'s keys: a jump within a frame is a `cut`, a pan of a quarter
frame or more a `whip` (0.7 s or less) or a `glide`, else a zoom of 1.8x or more a `zoom`; pushes and small reframes
are moves inside a scene, and moves made under a takeover's plate (from `a` on a cut or zoom in, from the end of the
morph or fade otherwise) are not transitions. The rule: never the same kind twice
in a row (cuts may repeat: a hard cut is the absence of a transition), whips at most 40 % of the scene changes.
A **bracket** counts once: a takeover's own in and out, and `T.cardToGraphic`'s morph and its return, share a `pair`
id, and logged as one kind with nothing between them (in `"card"` / out `"card"`, the signature move; in `"zoom"` /
out `"zoom"`; a box takeover's dissolve and grow, both `"fade"`) they are folded into one entry
(`{ t, kind, why, pair, until }`, `HF.trans.fold`). `window.__trans` is published folded, so precheck's `transStats`
reads the same list with no change of its own. The same kind again after the bracket's return is still a repeat (named
from the return). `HF.trans.check(list)` is the rule (pure; the same as precheck's `transStats` and plan_check's), and
`T.pick(t, ["zoom", "match", "whip"])` returns the first kind that keeps it at `t` (inside a bracket both its ends are
neighbours). Kinds and what each means
(SCENES.md §10): `cut` keeps the thought going, `whip` moves to the next station, `glide` travels there slowly, `zoom`
dives into the detail, `match` carries a shape into the next scene, `card` turns his card into the graphic or back,
`chapter` opens a section, `fade` is the soft return of his shape after a takeover. No shaders (HyperShader stays out).

**Proof.** `uv run python kit/hf/demos/takeover/build.py [--room <take>] [--at x,y]` builds a 56 s canvas page in each
canvas look (four takeovers, one of each kind, a chapter beat, and every transition kind in a row the budget allows) and
an HF.studio and an HF.reel whitespace page with two S.takeover scenes each (on a Reel the scenes keep to the safe band,
y 270..1250); `node kit/hf/demos/takeover/shoot.mjs` takes five stills at every logged transition (0.3 s before, the
last frame before the cut, the cut, +0.2 s, +0.55 s), writes `<page>_sheet.png`, and fails if he is not "off" in the
middle of a takeover and "on" a second after it, or the budget breaks. `node kit/qa/precheck.mjs
output/temp/demos/takeover/<page>.html`: 0 HIGH on all four. Scaffolds that use all of it:
`kit/presets/whitespace/templates/template.html` (new films) and `kit/presets/canvas_studio/templates/template.html`
(its hero is now a `type` takeover).

## Flat diagrams (`diagram.js` style `"flat"`, 2026-10-22, v11)

The owner suggested two repos for v11 (2026-10-22). From cathrynlavery/diagram-design (MIT) the kit takes its
**rules**, re-drawn for video on the whitespace look; from shader-effects-inc/shaders **nothing** (it needs WebGPU,
which the default software render has none of, and on white its grounds went grey or vanished after encoding).
The rules, the routing table and the budgets for planners: `kit/refs/DIAGRAMS.md`.

```js
const dg = HF.diagram(K, layer, { style: "flat", title: "the loop", type: "loop",   // flat is the default on whitespace
  nodes: [{ id: "build", label: "Build", sub: "HTML + GSAP", mono: true }, { id: "draft", label: "Draft" },
          { id: "critic", label: "Critic", sub: "checks every frame", focal: true }],
  edges: [["build", "draft"], ["draft", "critic"], { from: "critic", to: "build", label: "fix what broke", accent: true }] });
dg.show(a, b).reveal("build", t1).reveal("draft", t2).reveal("critic", t3).connect("build", "draft", t2).connect("draft", "critic", t3);
dg.connect("critic", "build", t4, 0.9).flow([["build", "draft"], ["draft", "critic"], ["critic", "build"]], t5, { period: 3.2 });
```

- **What it draws.** One box size for all (from the longest name or sub line), a 4 px grid, 2 px hairlines, radius
  18; mono type tags ("01", ... in a row or column; `tag` names one, `steps: false` drops them); 3 type sizes
  (26 px mono kicker, 48 px name, 32 px sub; 9:16: 30 / 52 / 34, tags inline). Focal: the accent tint, stroke and
  name, lifted to e3. `kind: "input"` / `"external"` a sunk grey box, `"optional"` a dashed one. No icons.
- **Layouts.** `"row"` (16:9 default), `"column"` (9:16 default), `"hub"` (`hub: id`; fan-in puts the hub on the
  right), `"grid"`, or explicit centres (`x`, `y` on every node). The boxes are centred across inside 120 px margins
  (a lane's label may push them aside, never out), the block centred down (`cy`: a share of the height). Too wide: the
  sub lines wrap first, then the gaps give (to 64 px), then the boxes; each is said in the console.
- **Connectors.** Straight when the ports line up, else a right-angle `"z"` (or `"L"`), r 20 elbows. In a row the next
  node is straight, a way back runs `"under"` (dashed), a skip `"over"`; nested lanes 72 px apart, the longest
  outside. Ports fan along a side at L k / (n + 1) and keep 22 px off corners, so no two connectors share a point.
  Fanned connectors turn in order (the outermost first) so no leg crosses another. `label` (<= 14 characters) sits
  10 px off its longest run on a paper mask (`mask`: its colour, default the look's paper); `accent` draws the edge,
  its head and label in the accent.
- **Motion** (all tweens on the paused timeline; the token is a `K.onFrame` function of t): `reveal` is a 16 px rise
  over 0.48 s (stagger 0.24); `connect` draws the line, then the head, and lifts its label; `flow` moves the diagram's
  ONE token (a later call moves it) around an edge or a chain, one lap every `period` s (>= 3), until `until`;
  `highlight(id, t, until)` makes a node focal for a while (no ring); `done` swaps a tag for a check; `note` is the one
  chip, under the node and any lane beneath it; `focus` / `overview` move the diagram's camera. Budgets are said in the
  console (`HF.diagram (flat): ...`): over 5 nodes (4 on 9:16), 6 edges, 2 focal at once, a label over 14
  characters, more than 2 items entering in one step, more than 2 edges drawing at once, more than one note up.
- **Published.** `window.__diagrams`: one entry per diagram (every style) `{ id, style, type, gate, frame, nodes: [{ id,
  x, y, w, h }], edges: [{ from, to, route, dash, label, pts, lab }], show: [[a, b]] }` in its view's px; flat
  entries carry `gate: true` and the full connector polylines (port to port, on the box outlines).
- **Pure helpers** (node-testable): `HF.diagram.layout(o, w, h, { portrait, warn })` (the geometry, no DOM),
  `HF.diagram.verify(entry)` (the geometry gate: a port of diagram-design's `verify-geometry.py`, thresholds x2.75;
  stricter in counting an arriving and a leaving port as a pair, and in reporting lines behind boxes and labels on
  lines), `HF.diagram.styleOf(o)`, `HF.diagram.steps(times)`, `HF.diagram.textW(text, px, kind)`, `HF.diagram.FLAT`.

**Old pages.** A page that names no style and isn't on whitespace draws the circles exactly as before: films/expensewaale's
two diagram setups (a circle row with a way back, cards at explicit centres) plus focus, done and note are
pixel-identical with the kit before v11 at 13 timestamps. Two v11 fixes are opt-in on circle and card: `margin: 120`
(the boxes inside the margins; `pad` only placed centres, so cards sat 38 px from the edge) and `ports: "fan"` (an
edge and its reverse 32 px apart: a curve moves toward its bulge, its straight partner the other way). C.takeover's
diagram kind passes both.

**Check it.** `uv run python kit/hf/demos/diagram/build.py && node kit/hf/demos/diagram/shoot.mjs`: a loop, a process,
a hub and layers on whitespace, a 9:16 column, the old styles before and with the fixes, and the takeover kind in both
looks, as stills and sheets in `output/temp/demos/diagram/shots/`; it fails on a page error, a geometry finding or a
seek that isn't pure. `uv run pytest -q tests/test_diagram_flat.py`.

## Catalog pieces (2026-10-20)

Ten pieces from the HyperFrames catalog (Apache-2.0) are vendored in `kit/hf/catalog/` and registered as `catalog.<name>`:
screen-recording auto-zoom on your screenshot (`cursor-zoom-follow`), an AI agent's cursor (`agent-cursor`), a selected
phrase (`cursor-text-select`), `marker-highlight`, `headline-slam`, `push-in`, `notes-typing`, `decline-chart`,
`conic-progress-ring` and a phone `chat-thread` (best in Reels). A film mounts them in film.py:

    MOUNTS = [dict(name="cursor-zoom-follow", at="w212", box=(960, 120, 880, 495), radius=22,
                   vars=dict(image="assets/shots/dashboard.png", zoom=2.0, click1_x=40, click1_y=22))]

kit/film/build.py writes them into the page as static sub-compositions (a mount made from the page's script is never
rendered). They take the film's look through CSS variables HF.look sets (--bg, --fg, --surface, --accent, --font-display,
...), and a colour `accent` defaults to the look's. `headline-slam` and `agent-cursor` are laid out for the full frame
(scaled into their box). A mount sits over the camera in screen px; on a canvas page `C.adopt(C.station(a, b, "mid",
[x, y]), "marker-highlight")` moves it into a station so it rides the whips and pushes. A `dur` other than the piece's
own length retimes it (its hold stretches; mounts.py writes a retimed copy). precheck fills each mount the way
HyperFrames' compiler does (its CSS scoped to the mount, its script given its own root and variables, its timeline
seeked in its own time), so the type floor, overlaps and the face zone cover a piece's text too; findings start
`catalog <piece>:`, and a piece it can't fill is a MEDIUM `mount` finding. The check sheet:
`uv run python kit/hf/demos/catalog/build.py --sheet` (every piece in pastel_box, canvas_studio and night). More pieces:
`python3 kit/hf/tools/catalog.py add <name>` (browse hyperframes.heygen.com/catalog), then look at the sheet before using one.

## Motion additions (2026-10-20)

- `HF.kinetic(..., { style: "cascade" })`: letters flip up out of each word's mask, a frame apart. `style: "focus"`: each
  word pulls from a soft blur into focus as it is said. Both set in the look's display face (`face: "look"`, which any
  style can take), so kinetic type stops being Anton/Montserrat in every look.
- `HF.morph(K, parent, ["x", "check"], [t], { x, y, size, colors })`: one stroke icon becomes the next (GSAP MorphSVG), with
  a small pop and a click: a verdict, play into pause, a lock opening. Icons are HF.ICON names or path data.
- `HF.shake(K, el, t, { strength })`: a designed "no" (CustomWiggle) with the fail sound: a wrong answer, a failed run.
- Camera zooms (canvas `C.cam`, diagram and screen cameras) interpolate scale in log space: 1 -> 2 takes as long as
  2 -> 4, so a zoom moves at an even pace to the eye (`HF.canvas(..., { logZoom: false })` for the old feel).
- The plugins (MorphSVG, CustomEase, CustomWiggle) are vendored with the kit (vendor.py LIBS); all of GSAP's plugins are
  free under its standard license since 3.13. Check sheet: `uv run python kit/hf/demos/motion/build.py --sheet`.

## Backgrounds, emoji and icons (2026-10-20)

- `HF.shaderBg(K, parent, "grain" | "mesh" | "rays" | "warp", { a, b, colors, speed, params, opacity })`: a living
  background from Paper Shaders (kit/hf/lib/paper-shaders.js, Apache-2.0). Colours come from the look (HF.C), so it
  belongs to the film. grain: a premium stage or title card; mesh: a calm world behind cards; rays: the payoff, an
  "aha"; warp: an intro or transition world. Frame-exact (the page clock drives `setFrame`). Cheap: the 23 s check page
  renders in ~14 s on the GPU. One at a time, and not behind his face (OWNER_DEFAULTS: his room stays as shot).
- `HF.emoji(K, parent, "mind-blown", t, { x, y, size, until, from })`: one of 51 Noto animated emoji (kit/emoji/noto,
  CC BY 4.0) on a reaction that means something. vendor.py inlines only the ones a page names; kit/film's build writes
  the credit into output/final/<film>/credits.txt (with the music credits). HyperFrames' own Lottie adapter would pin
  an emoji to its last frame; emoji.js drives the player from the page clock and gives the adapter a no-op.
- `HF.icon(name)` now also knows 222 Lucide icons (kit/hf/lucide.js, ISC) on the same grid as HF.ICON, and
  `HF.drawIcon(K, parent, "rocket", t, { x, y, size, color })` draws one on stroke by stroke (DrawSVG) instead of
  fading it in. Names: lucide.dev/icons (the curated set is the map in lucide.js).
- Check sheet with all of these: `uv run python kit/hf/demos/motion/build.py --sheet`.
- `HF.parallax(K, parent, "assets/photo.jpg", a, b, { move: "push" | "pan" | "orbit" | "drift", x, y, w, h, radius })`:
  a 2.5D camera move through a still, displaced by its depth map (near things move more). Make the map once with
  `uv run --no-project --python 3.13 --with transformers --with torch --with pillow python -m kit.look.depth <photo>`
  (Depth Anything V2 Small, Apache-2.0, ~1 s a photo on the Apple GPU; writes photo.depth.png). For photos, products and
  places shown as evidence or b-roll, not his footage, and not flat UI screenshots (use a 3D card).
