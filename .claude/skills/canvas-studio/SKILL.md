---
name: canvas-studio
description: Edit the owner's talking-head video on the canvas engine (kit/hf/canvas.js), by default in the white look (preset_whitespace, kit v11, 2026-10-22, from his asks "holistic, not heavy" and "a white background"), or in his approved warm canvas_studio look when he names it ("Yeah, it's a nice edit", 2026-10-20). One stage with a camera that whips, pushes and pulls out between stations; real evidence (their page, logos, dated facts) on 3D cards; one idea per frame; takeovers where a passage shows a thing (he is off screen, never cut out); the lens moving on him while he sits; a chart that lands on his last word; and him ONLY full frame, in a circle or in a card. This is the default for any new talking-head edit or sample (16:9 long-form, "edit my next video", "clean edit", "white", "like the HackerRank sample", "minimal but premium", "camera moves", "canvas") unless he names another preset. Use it alongside video-shorts (and the Reel rules (kit/refs/EDITING.md §3-4, kit/reel/README.md) for 9:16).
---

# Canvas studio: the canvas engine, in the whitespace look (default) or canvas_studio

Read `kit/refs/OWNER_DEFAULTS.md`, then the look's README: `kit/presets/whitespace/README.md` (the default since
2026-10-22: the restraint rules, the takeover recipes, what to avoid) or `kit/presets/canvas_studio/README.md` (when he
names it: the rules, the scene recipes and what failed). The engine is `kit/hf/canvas.js` (kit/hf/README "Canvas",
"The lens", "Takeovers and transitions"). Worked examples: `kit/presets/whitespace/templates/template.html` (whitespace), `kit/presets/canvas_studio/templates/template.html` (canvas_studio), `kit/hf/demos/takeover/` (takeovers) and `kit/film/example` (the whole pipeline, no footage needed).

## Never break these (his words and the critic's)

1. **Him:** full screen (seated full frame, at most about 30 % of the runtime), or inside a closed shape (a circle, a square, a rounded card or the seated frame card) showing his real graded room. He is never cut out and never stands on the backdrop. His face is on screen from frame 1. Shapes morph under camera moves. **The lens moves the picture inside his shape** (kit/hf/README "The lens"): a framing change every 4-8 s (pushes of +6-12 %, pull-outs, slight arcs), eased punches of ×1.12-1.18 on stressed words, an eased reframe on every join, no shake. Don't write the old inline "every other join ×1.12" punch-in loop: the lens does it smoother.
2. **Nothing is a slide:** one stage, one camera, one station per thought, one idea per frame (at most 3 groups beside him). A held station keeps a slow camera push (`C.hold`); his picture moves by the lens.
3. **Takeovers where a passage shows a thing:** `C.takeover(a, b, { kind: "type" | "diagram" | "evidence" | "list" })` gives the whole frame to the scene while his voice carries on (kit/refs/SCENES.md §9). On long-form 15-30 % of the runtime, 4-12 s each, at least 3 s of his face between two, never away over 12 s; they may not overlap. A takeover diagram follows `kit/refs/DIAGRAMS.md` (flat).
4. **No two scene changes alike in a row:** a whip, a zoom through (`T.zoomThrough`, or a takeover's `in: "zoom"`), a match (`T.match`), his card morphing into the graphic (`in: "card"`, `T.cardToGraphic`), a chapter beat (`T.chapter`), a hard cut, an overview of the canvas. Use a takeover's `in` / `out` and `const T = HF.trans(K, C)`; every one is logged to `window.__trans` (cuts may repeat, whips at most 40 %; `T.pick` picks a kind that keeps the rule). No shader transitions.
5. **Facts:**
   - Every claim card is a checked fact with a dated source line, 6 words or fewer.
   - Search before building. Drop anything you can't source.
   - Nothing he didn't say is shown as his.
6. **Evidence:** the real page (`kit/web/capture.mjs`) with a highlighter on his line, and real logos at an equal height (a mock-up stays generic: no real logos).
7. **One hero moment per thought:** a `type` takeover (whitespace: Inter 700 in sentence case with one accent mark; canvas_studio: giant condensed caps with a strike and a grey-out on the negating word). The bed dips under it.
8. **Never an empty plate:** a chart draws in steps, creeps through his pauses and lands on his last word. The video ends on that landing.
9. **Layout, by look.** Whitespace: a true white page, one accent and no second hue, white cards with hairlines and soft shadows, no gradients, glows, pastel blocks, `HF.shaderBg` or grain, 120 px margins, at most 3 type sizes. canvas_studio: a warm seamless, one accent gradient, one dark anchor card per scene, pastel blocks only behind a card, a 96 px margin. Both: gaps of 70 px or more, text 32 px or more (a mono kicker 26-28 px), measured after 3D with `kit/qa/measure.mjs`.
10. **Render size:** previews and samples at 1080p, 4K only for a final he asks for.

## The run

1. **Ingest** the take (`uv run shorts probe ... --landscape`, `uv run shorts analyze`), read the transcript and pick the stretch. Whole sentences only; trim pauses in real quiet.
2. **Plan the beats before any code** in `films/<name>/visual_plan.json`, schema 2 (kit/refs/SCENES.md, OWNER_DEFAULTS §8). For each thought, write:
   - the station and the recipe (whitespace README §3: statement, system diagram, evidence close-up, list; canvas_studio README §3: hook macro, evidence wall, hero, tree, overview, chart; or a new one in the same grammar);
   - the word ids each element lands on;
   - his `face` (on, off for a takeover, corner, full, frame) and the lens's `cam` (push, pull, punch, arc, hold);
   - the `transition` into it, and `groups` (at most 3);
   - where the music turns (`"music"`). On long-form the bed is calm (lo-fi, chill, soft piano; no EDM or rock),
     sits ~18 dB under him and ducks on his voice, and it only steps back or stops, never drops (OWNER_DEFAULTS §4).
     On a Reel the hero may land on the track's drop with film.py MUSIC `drop="auto", at="w<id>"`
     (kit/music/beats.json). Chapter beats land on the downbeat by themselves.

   Then `python3 kit/hf/plan_check.py films/<name>/visual_plan.json`: 0 errors. Research the facts and capture the real
   pages and logos. Show him the plan when it is a full video. For a sample, go.
   Version 10 parts that fit this style (kit/hf/README): `catalog.cursor-zoom-follow` on his real screenshot for a screen
   beat, `HF.morph` (x -> check) on a verdict, kinetic `cascade` for a claim, one `HF.emoji` on a reaction, `HF.drawIcon`
   for a list's items. On canvas_studio a `HF.shaderBg` belongs on a title or hero station only, never as the stage
   itself; on whitespace never. A catalog
   piece stays put while the camera moves unless it is adopted: `C.adopt(C.station(a, b, "mid", [x, y]), "<piece>")`.
   `HF.kinetic` styles other than cascade and focus fall back to the paper serif: pass `face: "look"`, and keep the stress
   stars around the punctuation (`*MNCs.*`, never `*MNCs*.`, which prints the star).
3. **The film on `kit/film`** (kit/film/README.md; no copied `edl.py` / `build.py`: the preset templates' build.py
   writes no lens, no tracks.json budget and the v10 sound):
   - `films/<name>/film.py`: SOURCES, KEEP (whole sentences), JUDGED, fixes, spellings, MUSIC, `FACE_TRACK`, `STRESS`
     (punch words), `TRACK_SIZE = {"<face track>": "native"}` for a 4K take (the lens's headroom), `GRADE`.
   - `films/<name>/src/template.html`: copy `kit/presets/whitespace/templates/template.html` (the default) or
     `kit/presets/canvas_studio/templates/template.html` and write the scenes with
     `HF.canvas(K, ROOT, { ..., look: "whitespace" })`. Name his `<video id>` after `FACE_TRACK` (`<video id="face"
     src="assets/face.mp4">` with `FACE_TRACK = "face"`) and call `C.speaker("<FACE_TRACK>", shots)`, so the lens,
     `window.__speaker` and his face track all find him.
   - `uv run python -m kit.film films/<name> prep`, `cut --plan`, `cut --voice`, `joins` (re-listen to every join),
     `cut`, `grade --sheet=8,30,120` (the "clean" A/B on white: he picks), `grade`, `build`.
   `kit/film/example` is a worked film (film.py, visual_plan.json, src/template.html, on HF.studio); `kit/presets/whitespace/templates/template.html` is the whitespace page to start from.
4. **Check the stills:** `uv run python -m kit.film films/<name> snap --at=3,12.5,...` and look at every frame, plus `measure.mjs` at the busy moments. Fix margins, overlaps, density and empty plates before rendering.
5. **Render and gate:** `uv run python -m kit.film films/<name> draft` runs plan_check (an error stops it), the build, lint, cues, precheck (0 HIGH; read its last line), the mix, the 1080p render, mux and `qa.py`. Then pull real frames from the render at every transition: snapshots miss motion-blur and lens issues.
6. **The fresh critic** (`kit/qa/CRITIC.md`, the `edit-critic` agent), with the ledger in `films/<name>/review/ledger.md`. Fix and re-render up to 3 rounds, then deliver the video, a beat sheet and any open items.

When he gives new feedback on a look, add it to that look's README (whitespace §2 / §5, canvas_studio §2 / §5). Update this skill only if the change is a new hard rule.
