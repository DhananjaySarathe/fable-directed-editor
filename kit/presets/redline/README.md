# preset_redline: the editor's notebook

> **Read first, every edit:** `kit/refs/OWNER_DEFAULTS.md`, the owner's standing taste. It holds in every preset; this
> file can be stricter, never plainer. **Before the template is written, the planning gate:** `kit/refs/SCENES.md` →
> `visual_plan.json` → `python3 kit/hf/plan_check.py visual_plan.json` (0 errors). Pick the components from
> `kit/hf/registry.json`, starting with `python3 kit/hf/tools/registry.py --unused`. After the build,
> `kit/qa/precheck.mjs` must show 0 HIGH, ambition section included (OWNER_DEFAULTS §8).

**One line:** an engineer's notebook page with **one red pen**. Warm graph paper that never moves, black newsroom-grotesk
headlines, light pencil sketches, his real face in his real room, and his real screen recordings shown as numbered
figures. The pen marks only the words he is claiming. On a screen, it marks a tracing sheet laid over the recording and then lifted off.

The idea it carries: **AI does the work, a human red-pens it.** That is what this channel is (Claude/GPT/Gemini build
things; he checks, fixes, judges), and almost nobody in AI/dev YouTube looks like it. The crowded looks are:

- Fireship-speed meme edits;
- the dark Linear/Vercel glow;
- Excalidraw doodles, which are rough.js at its defaults;
- Vox/Johnny Harris collage, which is sold as a Fiverr gig now.

It starts from his own thumbnail (2026-10-19, `github/reverse-engineer`): graph paper, a heavy black headline, one red
marker stroke, a grey sub-line, pencil icons with dashed arrows, his face peeking up from the bottom edge. The video should look like that
thumbnail come to life.

Built 2026-10-19 from four research passes (sources below). **Stills only so far**: `kit/hf/demos/redline` (no real take
yet). The module is `kit/hf/redline.js` (`HF.redline`) and the tokens are in `preset.json`.

## 1. Rules (the whole style in twelve lines)

1. **One idea on screen at a time.** At most one overlay; lists cap at 4 points, each on its spoken word.
2. **Red is the pen and nothing else.** One mark per sentence, three on screen at most, only on claim words.
   - underline = emphasis
   - circle = look here
   - strike + a handwritten fix = wrong → right
   - caret + note = an addition
   - tick/cross = a verdict
3. **The page never moves.** The paper, the grid, a landed headline and finished ink stay still. No sway, no push, no
   boil. A page someone reads is a declared reading hold (qa.py `--holds`), not something to wiggle past freezedetect.
4. **Type lands whole on a cut, or word by word on his voice** (`R.say`). Never blur-in, scale-pop or letter-by-letter typing.
5. **Things leave on a cut, or get struck through.** Fades are 0.2 s at most.
6. **No shadows, no rounded corners, no glow, no tilt.** Depth is overlap and a 2 px ink outline. Only a taped print may sit crooked (±1.5°).
7. **His real room.** No cut-out or background effect by default. The owner on claude-makes-claude: "bg removal is too
   bad", "do not blur or put any effect in background". The peek cut-out is opt-in, for title cards and hooks.
8. **Real screens, shown so they can be read.** Zoom only when the viewer must read. Text is at least 28 px at 1080p on
   long-form, 40 px on a Reel, after the zoom.
9. **Hard cuts by default.** A slide (0.28 s) only when the layout continues; nothing whooshes.
10. **Long-form has no burned captions.** Ship `captions.srt`, plus about one keyword card a minute. **Reels always caption**, on a
    paper label, at most 5 words, the spoken word never recoloured, no emoji.
11. **Sound only for physical events.** A real marker stroke, a sheet of paper. Never on a cut, never a canned crowd.
12. **Real evidence, real numbers.** Numbers only if he said them or they're on screen with a source label.
13. **Few labels, written like a person writes them.** `Fig. 2 — Gemini, day 1, 2:10 am`, mixed case. The section
    marker shows only for the first ~8 s of a section, on paper. No "CAM A — LIVE" or kicker on every frame: spaced
    uppercase mono everywhere is the critic's #1 "generated page" tell.
14. **Sketch only what the video uses.** 2-3 pencil objects, placed asymmetrically, never a stock set mirrored left and right.
    Reuse pencil arrows and brackets later in the film so the sketches aren't a one-off.
15. **No dead half-frames.** A text block centres on the frame's middle, or its last baseline meets the face window's bottom (y 960).
    Everything sits on the 120 px margin.

## 2. Tokens

| Token | Value | Why |
|---|---|---|
| paper | `#FBFAF6` | warm, never `#FFFFFF`, so the real whites inside screen recordings still read as *screen* |
| grid | `#E6E6E1`, 60 px, 1 px lines (32×18 cells at 16:9, 18×32 at 9:16) | his thumbnail's grey grid; 60 divides both frames exactly; 120 px margins = 2 cells |
| ink | `#151515` (ink2 `#3D3B37`) | near-black, never pure black on warm paper |
| red | `#D7261E` | a felt-tip red, ~4.8:1 on the paper; strokes ≥ 10 px so YouTube's 4:2:0 chroma doesn't turn them pink |
| grey | `#6F6D68` | sub-lines and labels (~4.9:1) |
| pencil | `#8F8C85` at 90 % | sketches and dashed arrows: structure, never emphasis |

**Type** (all OFL, in `kit/fonts`, declared in `kit/hf/paper.css`, copied by `kit/hf/vendor.py`):

| Role | Face | Use |
|---|---|---|
| display | **Schibsted Grotesk** 900 (800 for word-on-voice) | a newsroom grotesk (Bakken & Bæck); headlines 136-150 px (16:9), 116-128 px (9:16), tracking −0.03em |
| text | **Atkinson Hyperlegible Next** 500/700 | sub-lines, list points, captions: drawn for legibility |
| labels | **Martian Mono** 500, caps | `FIG. 04 — CLAUDE CODE / TERMINAL`, kickers, sources, `§ 02 — the build` |
| hand | **Nanum Pen Script** | the red margin notes: it looks like a real felt-tip, not a "handwriting font" |

**Avoid**, because they read as AI or template defaults in 2025-26:

- Inter as a display face; Space Grotesk; Instrument Serif;
- Caveat and Excalifont (Excalidraw);
- the Anton/Bebas stamp look.

Those faces stay in the kit for the other presets.

## 3. The pen and the pencil (`R.pen(layer)`, `R.pencil(layer)`)

Both draw with perfect-freehand. A mark is a centreline drawn the way a hand moves:

- it is resampled every 7 px;
- it is nudged by two smooth noise layers: a slow 1.1 px wave every ~220 px plus a 0.35 px tremor every ~28 px. Plain per-point jitter reads as electric fuzz;
- its pressure presses, swells, then lifts;
- its speed slows on tight curves (two-thirds power law, v ~ R^(1/3)), starts and stops on a minimum-jerk curve, and gets an 80 ms lift between strokes.

All of it is seeded, so every render is identical. Geometry that needs laid-out text is measured on the first frame, after the fonts load.

| Mark | Timing | Shape |
|---|---|---|
| `underline(el or box, t)` | 0.32 s, pen down ~80 ms after the word | lead-in min(4 %, 22 px), overshoot min(6 %, 36 px), rises 1.5° (max 12 px), bows once |
| `underline(..., { double: true })` | 0.55 s | a return stroke: the video's single biggest claim only |
| `circle(el or box, t)` | 0.6 s | starts at 1 o'clock, runs ~20° past, drifts outward so the ends don't meet |
| `strike(el or box, t)` | 0.28 s | then a `note()` above for the fix |
| `arrow(p0, p1, t)` | 0.45 s | shaft, a lift, then the head; `{ dashed: true }` for pencil links |
| `tick / cross / caret([x, y], t)` | 0.22-0.36 s | list verdicts, insertions |
| `R.note(layer, x, y, text, t, { to })` | ~0.05 s per letter | Nanum Pen, −2°, written on left to right; `to` draws a red arrow from the note to a point |

Pencil icons (`pc.icon(name, x, y, size, t)`) are sketched with a few strokes, with corners that overshoot and shapes left slightly open:
`webcam mic window monitor phone chat terminal cursor file globe person signal clock git db bolt list spark`.
Add an icon to `ICONS` in `redline.js` (a centreline set in a 100 × 100 box), never inline.

## 4. Screens: three tiers

1. **Evidence (the viewer must read it).** Full bleed (`R.fig(L, 0, 0, W, H, { bleed: true, caption })`), untouched:
   - the FIG. label sits on a small paper tab;
   - marks go on the **tracing sheet** (`f.sheet(a, b)`), which slides in over 0.28 s, takes the red marks and slides out in 0.2 s;
   - `f.sheet(a, b, { window: box })` frosts the rest of the screen to paper (80 %) and leaves the line he is reading clear. This is focus without dimming to black.
2. **Figure (he is showing, not reading).** 66-75 % of the width, square corners, a 2 px ink outline, a mono `FIG. NN — what / where / when`
   caption under it, snapped to the grid. His face in the `pip` or `corner` window.
3. **Taped print (a still: a tweet, a doc, a paper).** `R.print(...)`: two tape strips, ±1.5°. Never tape live video.

**Zoom** (`f.look(t, box, { until })`) only to read:

- 1.6-2.2× on long-form; on a Reel, crop to one panel so the text is at least 40 px;
- 1.1 s `expo.out` in, 0.9 s out (`f.back`);
- hold ≥ 2.5 s, at least 0.8 s + words ÷ 3 s;
- for two zooms less than 1.5 s apart, pan instead of zooming out and in;
- the sheet comes down only after the camera has settled.

**Privacy:** `f.redact(boxes, { color })` lays a solid bar in the UI's own colour. Pixelation and blur can be reversed. Crop first if you can.

**Cursor and clicks:**

- `f.click(t, [x, y])` draws a small red ring at the click, gone 0.8 s later, without zooming;
- `f.scroll(t, cy, { speed: 150 })` scrolls a tall capture at a reading speed;
- HF.screen's `cursor` and `walk` still work.

**Crop only through whitespace or container edges.** Never cut a word or a stat in half. On a Reel, a one-line strip
(`R.fig(L, 60, y, 960, 120)` zoomed to the line) beats a whole screen at 9 px.

## 5. The face (`R.face(shots, { face | at, faceY })`)

His graded take in his real room. Each shot is `{ t, at, in: "cut" | "slide", zoom, label }`:

| 16:9 slot | Rect | Use |
|---|---|---|
| `full` | 0 0 1920 1080 | the hook, opinions, reactions, the verdict |
| `left` / `right` | 120 120 780 840 / 1020 120 780 840 | his words or a number beside him |
| `pip` | 1500 600 360 360 | over a figure while he is *doing*; off while the viewer *reads* |
| `corner` | 1440 60 420 420 | over a full-width board |

9:16 slots: `full`, `top` 60 240 960 640, `bottom` 60 900 960 660, `pip` 60 1140 360 420, `corner`. Every face box ends by y 1560, because Instagram's caption, handle and audio row cover the frame below that. The eyes sit at y 1380-1480 at the lowest (default `faceY` 0.38 in 9:16).

- A window has square corners and a 2 px ink outline, with an optional mono label under it ("cam a — live").
- A jump cut inside one framing takes `zoom: 1.10-1.14`.
- `R.face` publishes `window.__faceRect`, so precheck keeps text off the real face.
- **The peek** (`co.peek` on a card, or `R.peek`): the cut-out rising from the bottom edge under a headline, like the thumbnail. It is opt-in.
  In 9:16 he rises over a 2 px ink rule at y 1560, not from the frame's edge, so the app's UI never covers his eyes.
- **Talking head with one note:** `R.slip(x, y, text, t)` is his note in the red pen on a torn paper scrap taped over the footage. Use at most one every ~20 s, in a corner of his room, never on the face.

**Cut out on a white page: rejected (2026-10-20).** He asked for "a white, completely empty background", and
`films/chakra-redline` v1 tried it: `HF.redline(S, st, { grid: false })` with `R.cutout(shots, ...)`, his transparent take
moved left and right with text and plain animations beside him. He called it "awesomely stupid". He then set the rule:
never cut out, only full screen or in a closed shape (circle, square, card). The rebuild he approved is
`preset_canvas_studio` (kit/presets/canvas_studio). `R.cutout` stays in redline.js only in case he asks for it again.

## 6. Pages and cards

| Call | What |
|---|---|
| `R.page(a, b)` | a still layer on the page (a declared reading hold) |
| `R.head(L, "github/*reverse-engineer*", t, { x, y, size })` | a headline; `*span*` gets the pen (`mark: "underline" / "circle" / "double"`) |
| `R.say(L, from, to, { mark: [ids], circle: [ids] })` | his words landing as he says them; the pen marks the claim as he finishes it |
| `R.sub`, `R.label` | grey sub-line, mono label |
| `R.card(a, b, { kicker, title, sub, icons, links, peek, align })` | full-frame keyword/title card (about one a minute) |
| `R.chapter(t0, t1, "02", "the wall", sub, { of: 5 })` | a chapter card on the same grammar |
| `R.stat(L, x, y, "6 h", "from an idea to a live app", t, { src })` | one number, circled, with its source |
| `R.list(L, x, y, [{ text, at, done: "tick" / "cross" / "strike" }])` | at most 4 points |
| `R.compare(L, x, y, w, h, left, right, { winner, winnerAt })` | two columns, a pencil rule, his pick circled; each column takes `img` (+ `look`) so the verdict shows its evidence; his face goes in the pip |
| `R.skip(a, b, { from: "02:10", to: "08:40", note })` | a time skip: the old time struck through, the new one handwritten |
| `R.endCard(a, b, { peek })` | end-screen slots in pencil (square corners), handles from `kit/brand.json`, no red (nothing is claimed), his face peeking |
| `R.captions({ y })` | 9:16: paper-label captions (S.captions underneath) |

The section label (`§ 02 — the build`, top-left, mono) shows only on paper. It hides over a full-frame face, a card or a full-bleed screen.

## 7. Layout mix and pacing

**Long-form:**

- 4-7 visual changes a minute, where a change is a cut, a zoom, a card or a layout swap; median shot 6-10 s;
- a layout swap every 20-40 s;
- the first 30 s at about 1.5× that rate;
- one verdict hold of 30-60 s at about 75 % of the runtime;
- face on screen ≥ 35 % and never away for more than 12 s (since 2026-10-22; plan_check stops a plan over it);
- no layout over ~35 %, about one card a minute.

A typical mix: face full 35-45 %, evidence screens 25-35 %, figure + pip 10-20 %, face window + words 10 %, cards ≤ 15 %.

**Reels:**

- a state change every 2-5 s, payoff text by 3 s;
- frame 1 is a finished page, not a blank;
- captions on;
- the layout-variety rules still apply (≥ 4 layouts in 30-60 s, no layout over ~35 %).

## 8. Sound

The edit is quiet:

- the music bed sits ≥ 10 LU under the voice (`kit/audio/mix.py` defaults), with 12-16 dB ducking;
- room tone under every cut, never digital silence;
- no whoosh on cuts, no risers into cards, no canned crowd;
- master at −14 LUFS, true peak ≤ −1 dB.

**Pen and paper foley:** `HF.redline(S, st, { sfx: { pen, sheet, zoom } })` takes cue names. The kit has no real marker
sound yet: record 5-6 real strokes of a felt-tip on paper and one sheet laid down (into `kit/sfx/pen/`). That is more
"hand-made" than any library sound. Until then the marks are silent, which is fine.

## 9. What reads as AI or template (never)

- word-pop karaoke captions, emoji captions, neon highlights;
- a whoosh on every cut;
- auto-zoom on every click;
- a screen recording floating on a gradient wallpaper with a tilt and a giant soft shadow;
- glow, glassmorphism, permanent dark mode with grey text;
- Inter everywhere, three icon cards in a row, every element scale-popping in;
- constant Ken Burns drift on stills;
- AI b-roll (glowing brains, robot hands);
- three marks on one moment (box + arrow + zoom).

## 10. Making a film in this style

1. `uv run shorts probe <take> --job <name>` and `uv run shorts analyze <name>`, then cut with `kit/reel` (Reels) or the long-form path.
   The cut rules don't change: whole sentences, edges in quiet, the join audit.
2. In the template: `HF.studio` (16:9) or `HF.reel` (9:16), then `const R = HF.redline(S, st, { sections })`, then `R.face(...)`,
   scenes, and `K.finish`.
3. `node kit/qa/precheck.mjs <hf>/index.html`, snapshots, a 1080p draft, `qa.py`, then the critic (`kit/qa/CRITIC.md`)
   with this README as the brief. The demo shows every component:
   - `uv run python kit/hf/demos/redline/build.py --snap` writes stills to `output/temp/demos/redline/stills/`;
   - with his photo in `kit/refs/me/peek.png` (local only) the stand-in uses his face.

## Sources (2026-10-19 research)

- **Pacing:**
  - frame studies: MKBHD at 7.4 cuts/min, Fireship at 13.3 ([writepanda](https://www.writepanda.ai/blog/mkbhd-editing-style-measured/), [Fireship](https://www.writepanda.ai/blog/fireship-editing-style-measured));
  - no burned captions in 0 of 502 long-form frames ([writepanda](https://www.writepanda.ai/blog/youtube-videos-dont-burn-captions-study));
  - one overlay at a time, 4-bullet panels ([Matt Pocock's glossary](https://raw.githubusercontent.com/mattpocock/course-video-manager/main/GLOSSARY.md));
  - accent used sparingly, no novelty back to back ([Rauno on Vercel](https://rauno.me/craft/vercel)).
- **Screen numbers:**
  - zoom levels and timings from the source of the open-source Screen Studio clones ([Cap](https://github.com/CapSoftware/Cap/blob/main/crates/project/src/configuration.rs), [OpenScreen](https://github.com/siddharthvaddem/openscreen/blob/main/src/components/video-editor/videoPlayback/constants.ts));
  - reading speed ([Brysbaert 2019](https://www.gwern.net/doc/psychology/linguistics/2019-brysbaert.pdf));
  - redaction can be reversed ([Unredacter](https://www.bleepingcomputer.com/news/security/researcher-reverses-redaction-extracts-words-from-pixelated-image)).
- **The look:**
  - the engineering computation pad, copy-editing's red/blue pencil, non-photo blue;
  - the Swiss grid in motion ([Yablonski](https://www.webdesignerdepot.com/2016/01/swiss-in-css-animating-the-international-typographic-style/));
  - the two-thirds power law for hand speed ([Frontiers](https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2013.00068/pdf));
  - perfect-freehand's [options](https://github.com/steveruizok/perfect-freehand).
- **Human, not curated:** The Browser Company's "people are tired of things being overly curated" ([Every](https://every.to/podcast/transcript-the-browser-company-is-building-a-brand-that-drives-viral-growth)).

## Open

- **Not used on a real take yet.** The next film is the test: the face windows on his real room, the pen's timing on real word times, and a 1080p draft through qa.py.
- His own handwriting for notes (strokes captured once with a pen tablet and replayed) would beat any font.
- **Scene types not built yet**, named by the critic:
  - Claude Code / terminal as a figure: the active line left clear, a red bracket and the line number in the margin, a pencil "×8" on sped-up stretches;
  - an AI chat scrolling inside a fixed window, with a pencil "me" bracket on his prompt and wrong reply lines struck through;
  - a website scroll with a pencil position ruler in the margin;
  - FIG 3a/3b side by side in sync, with a running tally in red handwriting;
  - a code diff: red strike-through on removed lines, a pencil caret on added ones.
  They are all compositions of `fig`, `sheet`, `pen` and `note`. Add each as a helper when a real film needs it.
- **Critic pass 1 (2026-10-19), fixed:**
  - Reel faces sat under the app's UI;
  - too many uppercase labels;
  - dead half-frames;
  - a verdict with no evidence;
  - circles cutting glyphs;
  - crops through words;
  - the frost read as grey;
  - the end card had red and rounded corners;
  - the sketches were generic.
- Real pen and paper foley (see §8).
- Code and terminal scenes: show the real recording as a figure (≥ 40 px code at 1080p after the zoom). A paper-themed `HF.code` skin is not built yet.
