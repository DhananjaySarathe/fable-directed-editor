# preset_canvas_studio

> **Read first, every edit:** `kit/refs/OWNER_DEFAULTS.md`, the owner's standing taste. It holds in every preset; this
> file can be stricter, never plainer. **Before the template is written, the planning gate:** `kit/refs/SCENES.md` →
> `visual_plan.json` → `python3 kit/hf/plan_check.py visual_plan.json` (0 errors). Pick the components from
> `kit/hf/registry.json`, starting with `python3 kit/hf/tools/registry.py --unused`. After the build,
> `kit/qa/precheck.mjs` must show 0 HIGH, ambition section included (OWNER_DEFAULTS §8).

The owner approved this look on 2026-10-20 with "Yeah, it's a nice edit" (the 30 s HackerRank/Chakra sample,
`films/chakra-redline`, v4). It was **the default for his talking-head edits** from 2026-10-20 to 2026-10-22. Since
then the default is `preset_whitespace` (kit v11: the same engine and camera on a white page, from his asks "holistic,
not heavy" and "a white background"); this look stays available when he names it ("canvas studio", "like the
HackerRank sample") and renders exactly as before when a film chooses it.

**Since v11 (2026-10-22)** a canvas_studio film also gets, on the same engine:
- **the lens** on him (kit/hf/README "The lens"): it replaces the inline punch-in loops. A template that keeps its own
  "every other join ×1.12" shots still works (the lens carries across them as one hold, and the template's step shows
  whole), but the lens moves less inside that closer framing; drop the loop for the eased reframe;
- **takeovers** through `C.takeover(a, b, { kind: "type" | "diagram" | "evidence" | "list" })` (the hero below is now a
  `type` takeover) and transitions through a takeover's `in` / `out` and `HF.trans` (kit/hf/README "Takeovers and
  transitions"), with OWNER_DEFAULTS §1's budgets;
- **kit/film** as its pipeline (§4).

**The scaffold's open findings (pending his call).** `templates/template.html` is his approved choreography, so it was
not re-cut for the v11 gates: built on chakra-redline's data it still shows 5 HIGHs in precheck (his card beside the
content 47 % of the runtime, small text at the overview, his card upscaled ×1.40, whips at 50 %). Whether to
re-choreograph it is the owner's call; until then, a new canvas_studio film fixes these in its own template (or starts
from the whitespace scaffold's structure and keeps this look's tokens).

How it came about:
- **v1 was rejected.** It was a Redline page: text, plain animations, and his cut-out moved around. He called it "awesomely stupid. Go out and do online research on YouTube... how nice the animations, presentation, and transition all can be".
- **The references.** We studied frame by frame (`output/final/chakra-redline/reference_board.png`):
  - Enrico Tartarotti: a white seamless, macro UI, a gradient highlighter, glowing beams;
  - Ali Abdaal: speaker cards with a glow, 3D panels;
  - Ishan Sharma: giant condensed type, one card branching into three;
  - Think School: one canvas that builds.
- **The common thread is that nothing is a slide.** Everything sits on one lit stage, and a camera moves between the parts.
- **Two rounds of a fresh critic.** Scores went from 5/5/3.5/6 to 6.5/7/5.5/7 (motion / design / speaker / hook).
- **His own rule, added mid-way:** he is never cut out (§2.1).

The engine is `kit/hf/canvas.js` (`HF.canvas`; kit/hf/README "Canvas"). This file is the playbook: the rules, the scene recipes, the pipeline and what failed.

## 1. The look in one paragraph

A warm paper seamless (no grid, no texture) lit from the front. One accent gradient (violet → rose → amber). Ink-black
Schibsted Grotesk headlines and Atkinson labels. Cards and browser windows are white, with soft shadows and a slight 3D
turn. There is one dark or solid anchor card per scene.

His real room is always in a circle or a rounded card with a glow ring and a pastel block offset behind it. The shape
morphs between shots while the camera whips, pushes or pulls out between stations. The real evidence (their page,
their logos, dated facts) is shown big. There is one hero moment of giant condensed type with a strike, and a chart
that draws as he talks and lands on his last word. Sound: one calm bed (lo-fi, chill or soft piano; no EDM or rock) about 18 dB under him on long-form (12 on Reels), a whoosh under each
camera move, a pop on the landings, and the bed dips for the hero line. Since v11 (films made from 2026-10-22,
`kit/audio/mix.py`) the bed sits still under his voice and breathes only in real pauses, loops on its own phrases to
fill the whole film, and the whooshes and pops rotate 2-3 matched files within 4-8 small cues a minute. That is
kit/film's mix, which a new film runs on (§4). `templates/build.py` (chakra-redline's own pipeline, from before
kit/film) calls `kit.audio.mix` directly and keeps the v10 mix; a new film does not copy it.

## 2. The rules (hard)

1. **He is never cut out.** He is either full screen in his real take, or inside a closed shape: a circle (`r = w / 2`), a square or a rounded card, of any size.
   - The owner: "always put me either in a circle or in a square box... do not remove the person". No stage cut-out, no type behind his head.
   - His face is on screen from frame 1. A small circle in a corner over the hook is enough.
   - Shapes morph into each other under camera moves: circle → card → circle, never a pop.
   - The lens moves his picture inside the shape (v11, kit/hf/README "The lens"): pushes, pull-outs, arcs, eased
     punches on stressed words, and an eased reframe that hides each jump cut. It replaced the 1.12× punch-in shot
     (`s` on a `cut: true` shot); a kept one still plays, but the lens moves less there.
   - Keep the crop on the plain wall. No morph should start at full frame, or the room's clutter flashes up.
2. **Nothing is a slide.** One stage, one camera. Every scene is a station on the canvas: the camera travels to it, and the content builds there.
   - A held station keeps a slow camera push (`C.hold`, 3–12 %). It lets go on the next move. His picture moves by
     the lens on top of it.
3. **No two scene changes alike in a row** (`window.__trans` logs them: cuts may repeat, whips at most 40 %). The
   vocabulary:
   - a whip (0.55 s, `expo.inOut`, motion blur);
   - a push through a card into a hero (`C.takeover`'s `in: "zoom", from: card`, or `T.zoomThrough`);
   - a hard cut;
   - the overview: out until two stations sit side by side (z 0.48, 0.6 s), a 0.25 s beat, then into the next one;
   - a morph of his shape, or of his card into the graphic (`in: "card"`, `T.cardToGraphic`);
   - a match (`T.match`) and a chapter beat (`T.chapter`).
4. **Every claim card is a checked fact with a source line.**
   - Search before building, and date the source line: "pilot · May 2026", "live since Oct 5".
   - Nothing he didn't say and nothing unsourced. A quote is used only if it is verified word for word.
   - Drop what can't be sourced. In v3 a CEO quote and a Microsoft claim were dropped.
   - Claims are 6 words or fewer.
5. **Real evidence, big.** Use the real page (`kit/web/capture.mjs`, cropped of live counters), with a gradient highlighter on the line he means. Use real logos, trimmed of padding and set to an equal height (44 px). A named product gets its real logo (memory: real-product-references).
6. **One hero moment per thought.** Giant Archivo Condensed caps fill the width (96–1824 px). They enter with a 1.6→1 scale (0.5 s `expo.out`) and drift 40 px. The strike is a 28 px gradient bar in 0.4 s `power3.inOut` on the negating word ("may *not*"), and the type greys to #C9C9D2. A bass impact plays (−11 dB) and the bed dips (`HF.quiet`). He sits in a circle under the type.
7. **Never an empty plate.**
   - A chart draws in steps (`keys`): the flat "now" part as the card lands, creeping on through his hesitations. The change starts on the noun, and the end lands on his last word with a pop and a ring (`land`).
   - The card is locked, with no drift. Its push is a 4 % scale from its far edge, away from him.
   - Labels share one baseline.
8. **Beams connect to him.** On "connected", "linked" and the like, curved gradient beams with a travelling dot run from each card's edge into his shape and converge there.
9. **Palette.**
   - The warm seamless, one accent gradient, and one dark or solid anchor card per scene.
   - Pastel blocks only as a backing offset behind a card or his shape. Floating corner blocks read as sticky notes.
10. **Layout.**
    - A 96 px margin and gaps of at least 70 px.
    - Text at least 32 px.
    - Check it **after** 3D and the camera with `node kit/qa/measure.mjs <index.html> "<selector>" <times>`: turned cards grow toward the viewer.
11. **End with the take on the payoff.** The last landing (the chart's ring) is the last frame. No dead tail after he leaves, and no end card on a sample.
12. **Previews and samples render at 1080p.** 4K only for a final he asks for (memory: speaker-in-a-box).

## 3. Scene recipes (the scaffold: `templates/template.html`)

Times are tied to word ids (`W(i)`, `WE(i)`), never to seconds.

| Recipe | What it shows | How (chakra-redline) |
|---|---|---|
| **Hook macro** | their own page, his line highlighted | <ul><li>`C.window` with the real capture, turned rx 14 / ry −10, under a `C.dof` lens.</li><li>`C.highlight` at 0.55 s, then a 1.2 s pull back to z 1. The lens fades out.</li><li>A chip names the source.</li><li>He is a small circle bottom-right from frame 1, growing to a big circle on the pull back.</li></ul> |
| **Evidence wall** | the facts behind his claim | <ul><li>Three `C.card`s (640×230, ry 12, 70 px apart), each landing on a word.</li><li>The first card lands during the whip.</li><li>One card is dark.</li><li>Beams converge into his card on "connected".</li></ul> |
| **Hero** | the claim, as type | <ul><li>Push through the dark card, then a hard cut to the overlay: `C.big`-style caps, the strike and the grey-out.</li><li>He is a circle under the type, with a slow push inside it.</li><li>Since v11 the scaffold plays it as a takeover: `C.takeover(a, b, { kind: "type", in: "zoom", from: darkCard, text, mark: { word, t, kind: "strike" } })`, 4-12 s, with him off for it and his card back on the cut.</li></ul> |
| **Tree** | one idea into three | <ul><li>A gradient card (the anchor) with three curved branches. Each label lands on its word.</li><li>An underline lands on the key word of the last one.</li><li>He is the left card.</li></ul> |
| **Overview** | the canvas itself | <ul><li>Out to z 0.48 until the last scene and the next one sit side by side, a beat, then in.</li><li>He shrinks to a corner circle while it is out.</li><li>Its small text is allowed in precheck (`--allow=a-b`).</li></ul> |
| **Chart** | his bet / the trend | <ul><li>A locked card (logo pill, a 44 px title, "now" and "in 6 months" on one baseline) with a peach backing block.</li><li>`C.chart` keys, `land` on the last word, a chip up and left of the end dot.</li><li>He is a big circle right; the lens reframes the jump cut (chakra-redline had a ×1.12 punch-in shot there).</li></ul> |

Stations sit 1920 px apart on a 5760×3780 canvas: S1 [2880, 1620], S2 [4800, 1620], S4 [2880, 2700], S5 [4800, 2700].
`C.station(a, b, "mid", S)` is a flat frame there in screen px, visible only while the camera is near it. Plan one
station per thought and reuse the canvas, rather than one per sentence.

**The rest of the kit works on the canvas too (2026-10-20).** HF.canvas applies the canvas_studio look (`HF.look`), so the
shared components take its ink, Atkinson/Schibsted type and violet accent:
- `C.ui.*` (pr, checklist, note, chat, stamp, pointer…), `C.scoreboard`, `C.flow` and `C.focus` (via `C.parts`);
- `HF.code`, `HF.compare`, `HF.diagram`, `HF.sketch`, `HF.annotate` and the stickman.

Put them in a station: `const L = C.parts.layer(a, b, stn, { float: 0, push: 0 })`. The worked check is
`kit/hf/demos/looks` (kit/hf/README "Looks"). Use them where a passage needs them (a checklist, a scoreboard, a sketch),
so a canvas film isn't only cards, windows and beams.

## 4. The pipeline

**A new film runs on `kit/film`** (kit/film/README.md; the same steps as kit/presets/whitespace/README.md §4):
`films/<name>/film.py`, a schema-2 `visual_plan.json` and `src/template.html` copied from `templates/template.html`
here, its `<video id>` and `C.speaker` id named after `FACE_TRACK`. Then `uv run python -m kit.film films/<name>`
`prep`, `cut --plan`, `cut --voice`, `joins`, `cut`, `grade --sheet=8,30,120`, `grade`, `build`, `snap --at=...`,
`draft`. That gives it the lens, the tracks.json zoom budget, plan_check first and the v11 sound, which
`templates/build.py` has none of.

chakra-redline's own pipeline, from before kit/film (kept so that film rebuilds as it was; don't copy it for a new one):

```
# 0. ingest the take (word timings): uv run shorts probe "<take>" --job <job> --landscape && uv run shorts analyze <job>
# 1. the cut: copy templates/edl.py to films/<film>/, set JOB and KEEP (whole sentences; pauses trimmed in real quiet)
uv run python films/<film>/edl.py                      # -> work/edl.json, work/take.mov, work/vo_raw.wav
#    re-listen every join (audit-joins-before-render): edges sit in quiet, measured on the voice
# 2. the voice: WPE dereverb (~/.venvs/wpe) when the room echoes, then DeepFilterNet3 (~/.venvs/df/bin/deepFilter) -> work/vo.wav
# 3. his picture, graded, full frame (he is only ever in a shape):
#    a long film: python3 kit/look/grade.py work/take.mov work/room.mp4 --v2  (A/B at 100 % against the take: keep-source-quality)
#    a sample (what chakra-redline did): uv run python kit/look/cutout.py work/take.mov work/cutout.webm --plate=work/room.mp4
# 4. the page: copy templates/template.html to films/<film>/src/ and templates/build.py to films/<film>/; write the scenes
uv run python films/<film>/build.py --snap             # stills at SNAP times -> renders/snap; look at every one
node kit/qa/measure.mjs output/temp/films/<film>/hf/index.html ".cv-card, .cv-win, .cv-chip, .cv-t" <t1,t2,...>
# 5. render + gate: precheck (0 HIGH), cues, mix, 1080p render, mux, qa.py (~45 s for 30 s on this Mac)
uv run python films/<film>/build.py --all
# 6. the fresh critic (kit/qa/CRITIC.md) on the render, ledger in films/<film>/review/ledger.md; whitelist fixes only
```

Facts: research the claims (WebSearch) while planning the scenes, and write the source line on each card (§2.4).

## 5. What failed (do not repeat)

- **Plain text and animations on a page, his cut-out moved around.** Rejected ("awesomely stupid").
- **A cut-out of him anywhere.**
  - The matte breaks on fast hands: the railing leaks and the fingers ghost.
  - A card-to-cut-out switch pops.
  - He dislikes it as such (§2.1).
- **A cut-out on a lilac gradient inside a card.** It reads as a sticker, and a short frame left a white strip under him. Use his graded room, always covering the shape.
- **Hold pushes that never released.** They added up to 1.22× by the end and pushed cards off the frame. `canvas.js` now lets each one go on the next move.
- **Station frames with `preserve-3d`.** The layer's far-away perspective was added to theirs and threw cards off the frame's left edge. Station frames are flat now.
- **An empty chart plate for 3 s, and a card drifting under his head.**
- **Four identical whips.**
- **A 1.2 s dead tail after he slid out, and a buried impact (13 dB under the voice).**
- **An overview while the next station was empty, or while the last one was already hidden.** Land the next scene's card first, and keep the last station visible until the camera is back in.
- **Pastel corner blocks floating on the seamless.**
- **Unsourced claim cards.**

## 6. Files

| | |
|---|---|
| `kit/hf/canvas.js` | the engine: `HF.canvas` (camera, stations, windows, cards, highlight, beams, big type, the speaker in shapes, chart, chip, lens, blocks) |
| `kit/hf/motion.js`, `kit/hf/trans.js` | the lens on him (`HF.motion.lens`), the takeovers and transitions (`C.takeover`, `HF.trans`) |
| `kit/qa/measure.mjs` | where elements really land at given times (3D and camera included) |
| `kit/film/` | the pipeline of a new film (film.py, visual_plan.json, src/template.html; grade, mix, draft, render) |
| `kit/look/cutout.py --plate` / `kit/look/grade.py --v2` | his graded take for the shapes (chakra-redline's way; kit/film grades the cut itself) |
| `templates/template.html` | the scaffold of a new film's page (copy it to `films/<name>/src/`, then write the scenes) |
| `templates/edl.py`, `templates/build.py` | chakra-redline's pre-kit/film pipeline (no lens, no tracks.json, the v10 sound): not for a new film |
| `preset.json` | the tokens |
