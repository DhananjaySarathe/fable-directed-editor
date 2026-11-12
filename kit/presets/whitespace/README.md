# preset_whitespace

> **Read first, every edit:** `kit/refs/OWNER_DEFAULTS.md`, the owner's standing taste. It holds in every preset; this
> file can be stricter, never plainer. **Before the template is written, the planning gate:** `kit/refs/SCENES.md` →
> `visual_plan.json` → `python3 kit/hf/plan_check.py visual_plan.json` (0 errors). After the build,
> `kit/qa/precheck.mjs` must show 0 HIGH, ambition section included (OWNER_DEFAULTS §8).

canvas_studio's camera and evidence on a **true white page**, with restraint. Built 2026-10-22 (kit v11) from the
owner's asks on the oss-editor film:
- (A) "holistic, not heavy": the purpose shown neatly;
- (B) neat means a **white background**;
- (C) full-screen scenes where he is off screen completely;
- (D) the camera moving on him while he sits.

**Status.** This is the default look for **new** talking-head edits (decision of 2026-10-22; OWNER_DEFAULTS §1,
`kit/presets/README.md`). `preset_canvas_studio` stays available and renders pixel-identically when a film chooses it
(proved by frame diffs of chakra-redline, oss-editor and its Reels). Show a sample before a whole film until the owner has approved the look once.

The engine is unchanged: `kit/hf/canvas.js` (`HF.canvas`) with `{ look: "whitespace" }`. Every colour, surface and
type the canvas draws comes from the look's tokens (`kit/hf/core.js` `HF.LOOKS.whitespace` and its `.stage`), so the
pieces need no new calls. This file is the playbook: the restraint rules, the recipes and what to avoid.

## 1. The look in one paragraph

A true white page (#FFFFFF) lit from the front: white over the middle, falling off by only about 3 % toward the
corners, so it reads as a lit cyclorama and not as a blank screen. Near-black ink (#0E0E12) in Inter: 700 with tight
tracking for titles and statements, 500 for labels. There is **one** accent, a blue-violet (#5646D6), and no second
hue. Cards and windows are white on white, separated only by a 1 px hairline and a soft cool shadow, like paper lifted
off a table. Depth comes from elevation (e1 a chip, e2 a card, e3 the scene's one hero object), hairlines and 3D
turns, never from colour. His real room sits in a circle or a rounded card with an e3 shadow (no glow ring, no pastel
block). The camera carries the energy: it whips, pushes and pulls out between stations while elements land once and
then stay still. Sound and music follow OWNER_DEFAULTS §4 (a calm bed about 18 dB under him on long-form, 12 dB on Reels).

## 2. The rules (hard)

canvas_studio's rules hold unchanged (`kit/presets/canvas_studio/README.md` §2): he is never cut out, nothing is a
slide, no two scene changes alike in a row, every claim card is a checked and dated fact, real evidence is shown big,
a chart never sits empty, 1080p for previews and samples. On top of them:

### 2.1 Restraint (the white page punishes clutter)

1. **One idea on screen:** one hero object, one supporting chip or source line, and him. A second idea gets its own station.
2. **One accent, and at most one mark per sentence.** A mark is the accent word, a highlighter sweep, an underline, a beam or a ring. Pick one; never two on one sentence.
3. **No gradients, glows, pastel blocks or colour shader washes.** (`C.blocks` draws every block in one neutral grey on this look, whatever colour a template names, a hex included; `fo.back` blocks behind his card are ignored.) **No `HF.shaderBg` ground and no grain** on this page: studied 2026-10-22 (the owner's shader-effects-inc/shaders suggestion and a WebGL port of its ideas), a white shader ground either turned the page grey or vanished after encoding while costing bitrate, and grain is invisible on white yet multiplied a still's h264 size by eight (`kit/refs/DIAGRAMS.md` §11). A lit field, a highlight sweep or a soft reveal, if ever wanted, is CSS and GSAP.
4. **120 px margins.** Content sits in about 55 % of the frame or less; the rest is white.
5. **Depth only from shadows, hairlines and 3D turns.** One e3 object per scene (the window, the hero card, him), the rest e2 / e1. No dark anchor card: the hero is the raised one.
6. **At most 3 type sizes per scene** (a kicker, a title, a label). Body text and labels at least 32 px. The one exception is the kicker: mono caps at 26-28 px, always in `HC.sub` (6:1 on white). `HC.mute` (3.8:1) is for type of 32 px or more only.
7. **The camera carries the energy.** Elements land once (`C.card`, `C.window` through `C.land3d`, `C.chip`, a highlighter) and then stay still: no idle bobbing, pulsing, turning or re-landing. The engine does this by itself on this look: the stage caps any card's drift at 0 (`driftMax`, like the beam's width cap), so canvas_studio code that passes `drift: 1.2` lands still here too. Leave drift out anyway; a deliberate turn is a camera move, not a card's. The motion is the camera's (whips, pushes, pull-outs) and his shape's.

### 2.2 Him

1. **His room as shot.** White applies to the page and to the face-off scenes, never to his room: no blur, no dim, no vignette, no whitening of his wall. Motion blur on his picture comes only from fast camera moves (whips, zoom-throughs).
2. **The hook opens on his face.** Then the face comes and goes: on long-form, 15-30 % of the runtime is takeovers (§3) of 4-12 s each, with at least 3 s of his face between two takeovers. He is never away for more than 12 s.
3. **Seated full frame** is allowed for up to about 30 % of the runtime (the 35 % cap on any one layout still applies), cropped to a clean rectangle of his plain wall. Never a cut-out.
4. **The camera on him is visible but smooth:** a framing change every 4-8 s while he is on screen. Pushes of +6-12 % across a thought, pull-outs, eased punches of ×1.12-1.18 on stressed words (at most one per 12 s), slight arcs (truck ≤ 3 %, roll ≤ 0.6°), a settle after each whip, an eased reframe on every join. No handheld shake. Never zoom past the source's resolution budget (`max_zoom` in the film's `tracks.json`). The lens does all of it (kit/hf/README "The lens"): kit/film turns it on for a film made from 2026-10-22, film.py `STRESS` and the plan's `cam` steer it, and `TRACK_SIZE = {"<face track>": "native"}` keeps a 4K take's headroom. Write no punch-in loops of your own.

### 2.3 Picture and sound

- Grade: the "clean" look (bright, neutral whites, protected skin) is offered as an A/B against the current look
  (`uv run python -m kit.film films/<name> grade --sheet=8,30,120`: both looks drawn on white, with the scopes under
  each); he picks, and it goes in `GRADE`. Screen recordings pass through ungraded (their view kind `None` in
  GRADE's `kinds`).
- Music: long-form beds 18 dB under the voice with a voice-keyed duck (no pumping); Reels about 12 dB. Calm: no drops or risers on long-form.
  This is kit/film/mix.py's v11 sound, on by itself for films made from 2026-10-22: the bed lifts only in pauses of
  0.8 s or more, one calm track loops on its own phrases to fill the film (each seam's time is printed: listen), bed
  changes cross on the outgoing bed's downbeat, and the whooshes and pops rotate 2-3 matched files within at most 8
  small cues a minute on a film, 12 on a Reel (OWNER_DEFAULTS §4).
- Transitions are our own code: a takeover's `in` / `out` and `HF.trans` (`T.zoomThrough`, `T.match`, `T.chapter`,
  `T.cardToGraphic`, `T.whip`, `T.cut`; kit/hf/README "Takeovers and transitions"), plus the camera's moves and his
  shape morphing. Each one means something (kit/refs/SCENES.md §10): never the same kind twice in a row (cuts may
  repeat), whips at most 40 % (`window.__trans`; `T.pick` picks a kind that keeps it). No shader transitions.

## 3. Takeover recipes (he is off screen)

A takeover is a full-screen scene with no face, on his continuing voice (the cut never moves a word). Use the kinds
`C.takeover` already has (kit/hf/README "Takeovers and transitions"): it takes his shape off at `a`, drops any shot of
his inside `[a, b)` and brings back the shape he had before `a` at `b`. `templates/template.html` here is the
scaffold: a takeover of each kind with the transitions in and out of them (copy it to `films/<name>/src/` and
rewrite the scenes; a new film runs on kit/film, §4). The rules for every takeover:
- **4-12 s each, at least 3 s of his face between two, never away more than 12 s**, and 15-30 % of a long film in
  all (plan them as `"face": "off"` passages: plan_check checks the budgets, precheck measures them on the page).
- **They may not overlap**: `C.takeover` throws when two spans overlap, and warns under 3 s of face between them.
- **Every reveal lands on his word** (`W(id)` / `WE(id)`), never on seconds.
- **Motion inside**: the takeover's camera pushes 3.5 % while it holds (`push`), the evidence kind leans into its mark,
  a diagram builds; a still takeover is the slideshow the critic flags.
- **`in: "match"` out of a full-bleed frame:** name an element he does not cover (`match: el`), or the flying shape
  appears out of nowhere.
- **No `HF.shaderBg` and no grain** behind any of it (§2.1 rule 3).

| Recipe | What it shows | How |
|---|---|---|
| **Statement** | the one line the passage is about | <ul><li>`C.takeover(a, b, { kind: "type", kicker: "the rule", text: "Neat beats *busy.*", sub, mark: { word: 0, t, kind: "underline" } })`: a kicker (mono caps, 26-28 px, `HC.sub`), then the line in Inter 700, sentence case, ink.</li><li>The one mark: the accent on one word (`*word`) **or** an underline drawn on the word as it is said, never both.</li><li>One line under it (`sub`, 32-36 px in `HC.sub`), or nothing; `then` cascades a second line in.</li><li>Arrive with a zoom through an element (`in: "zoom", from`) or a hard cut; leave with a fade or by diving into the next station (`out: "zoom"`).</li><li>On a station while he stays on: `C.big(L, text, 960, y, t, { size: 150-200, align: "center" })` with a slow `C.hold` push (0.03-0.05).</li></ul> |
| **System diagram** | how the parts fit | <ul><li>`C.takeover(a, b, { kind: "diagram", type, title, nodes, edges })`, or `HF.diagram(K, layer, { style: "flat", type, ... })` on a station: the **flat diagram** (`kit/refs/DIAGRAMS.md`; it is this look's default): 3-5 hairline boxes on a grid, mono tags ("01"), each landing on its word; the part he means `focal` (the accent, raised to e3).</li><li>Names of 1-2 words, edge labels of 14 characters or fewer; at most 5 nodes (4 on 9:16), 6 edges, 2 focal.</li><li>Connectors straight or at right angles (never curved `C.beam`s here), drawing as he names the link; a loop's way back dashed under the row with its meaning on it (`{ from, to, label: "fix what broke", accent: true }`).</li><li>At most one note chip (`dg.note`) and one flow token.</li><li>Pick the type from what the passage does (process, loop, hub, layers: DIAGRAMS.md §2); over 5 boxes, split it into an overview and a detail station.</li><li>Past 12 s it becomes two takeovers with a face beat on the takeaway between them (or he comes back as a small circle in a corner).</li></ul> |
| **Evidence close-up** | the proof, big | <ul><li>`C.takeover(a, b, { kind: "evidence", img, url, mark: [x, y, w, h], markAt, note, noteAt })`: the real capture (or a generic mock-up via `html`: no real logos in mock UIs) in a white window at e3, one highlighter mark on the line he reads, the dated source line as `note`; the camera leans into the mark.</li><li>On a station while he stays on: `C.window` turned ry 6-10, rx 2-4, `C.highlight` on the line, `C.chip` with the source line, a `C.hold` push (0.04) or `C.focus`; pull back out when he moves on.</li></ul> |
| **List** | 3-4 points he names in order | <ul><li>`C.takeover(a, b, { kind: "list", kicker, title, items: [[text, W(id)], ...] })`: one card; the point being said is ink, the ones before it step back to sub.</li><li>`in: "card"`: his card morphs into the list card; `out: "zoom", into: "<part>"`: leave by diving into the last point.</li></ul> |

A scene of your own still goes through `C.takeover`, so the budgets, `window.__speaker` and `window.__trans` see it:
`{ build: (L, tk) => parts }` draws into the takeover's frame-sized layer (films/v11-sample's four layers), and
`{ mount: "<piece>" }` puts a catalog piece full frame.

His card between takeovers: a rounded card (r 32) or a circle (`r = w / 2`), e3 shadow, his graded room covering
it, at the side of the station's content. The beside-content layout leaves the 120 px margins. Seated full frame
(`mode: "frame"`, the 1680 × 945 card, or `full: true` for full bleed) holds at most about 30 % of the runtime.

## 4. Building a whitespace film

```js
const C = HF.canvas(K, ROOT, { w: 5760, h: 3240, x, y, z: 1, look: "whitespace" });   // the canvas, white
const HC = HF.C;                                                                       // the look's tokens
// a pastel-box frame can be white too: HF.studio(K, ROOT, st, { end, look: "whitespace" }) / HF.reel(..., { look })
```

**The pipeline is `kit/film`** (kit/film/README.md), not canvas_studio's `templates/edl.py` / `build.py`: those write
no lens, no tracks.json budget and the v10 sound, and nothing warns you. A whitespace film is three files:
- `films/<name>/film.py`: SOURCES, KEEP (whole sentences), JUDGED, fixes, spellings, MUSIC, `FACE_TRACK`, `STRESS`,
  `TRACK_SIZE = {"<face track>": "native"}` for a 4K take, `GRADE` (after the clean A/B, §2.3);
- `films/<name>/visual_plan.json`: schema 2 (face, cam, groups, transition per passage; kit/refs/SCENES.md);
- `films/<name>/src/template.html`: a copy of `templates/template.html` here with the scenes rewritten, on
  `HF.canvas(K, ROOT, { ..., look: "whitespace" })`. Name his `<video id>` after `FACE_TRACK`
  (`<video id="face" src="assets/face.mp4" data-duration="__TOTAL__" ...>` with `FACE_TRACK = "face"`) and give
  `C.speaker` the same id, so the lens, `window.__speaker` and his face track find him.

Then `uv run python -m kit.film films/<name> prep`, `cut --plan`, `cut --voice`, `joins`, `cut`, `grade --sheet=8,30,120`,
`grade`, `build`, `snap --at=...`, `draft` (plan_check first, precheck 0 HIGH, the v11 mix, 1080p, qa.py). Start from `templates/template.html` here; `kit/film/example` shows a film's three files (film.py, visual_plan.json, src/template.html) and runs with no footage.

Scene code from canvas_studio (its `templates/template.html`) carries over once its
canvas_studio literals are swapped for tokens, so the same scene reads in either look; `sheet/template.html` here is a
worked whitespace page (every scene of §3, already swapped) to copy scene code from:

| canvas_studio literal | token |
|---|---|
| `#16161C` (titles, the base line) | `HC.ink` |
| `#5f5f6a`, `#6b6b75` (labels, source lines) | `HC.sub` |
| `#8a8a96` (faint labels) | `HC.mute` at 32 px and up; `HC.sub` below |
| `#6C5CE7`, `C.G.a` (the accent) | `HC.acc` |
| `#E7E1FF` (a tint behind a numeral) | `HC.accTint` |
| `C.GRAD` as a text fill or a card fill | `HC.acc` (solid), or no fill |
| a dark anchor card (`background:#16161C`) | a white card raised to `HC.e3` |
| a glow `box-shadow` on a landing card | `HC.e3` |
| `fo.back` pastel block behind his card | nothing (ignored on this look) |
| `drift: n` / `hold: n` on cards (`clue`, `co`, a `card` helper's `drift: 1`) | leave both out: cards land once, then stay still (the engine ignores them here) |
| a kicker at 22-24 px in `#8a8a96` | mono caps 26-28 px in `HC.sub` |
| `C.blocks` with a pastel name or hex | leave them out (they draw neutral grey here) |
| a `size` for `S.line` / `S.say` copied from a pastel_box film (Instrument Serif) | about 0.7x: Inter 700 averages 0.48 em a character, Instrument Serif 0.33 (measured in Chrome, 2026-10-22); check the line fits its `w` before placing what sits under it. canvas_studio's sizes carry over (Archivo Condensed caps 0.48, Schibsted 800 0.49) |

What the engine does by itself on this look (`C.stage` holds the tokens):
- the page is the white cyclorama (`C.PAPER.seamless`), the edge colour `#F5F5F6`;
- cards and windows land, then hold still: `C.land3d` (behind `C.card`, `C.chip` and a window's landing) makes no drift turn, whatever `drift` the template passes (`C.stage.driftMax` 0);
- `C.window`: a white window, e3 shadow, grey traffic lights, Inter in the URL bar;
- `C.card` (e2) and `C.chip` (e1): white on white with the hairline;
- `C.highlight`: a solid `#E4DFFF` marker, multiplied (the ink under it stays black);
- `C.beam`: a 4 px ink line (never wider than 5 px, whatever `w` a template passes), no glow, an accent node at its head;
- `C.big`: Inter 700, sentence case, -0.045 em;
- `C.chart`: one accent stroke over a flat 4.5 % tint, a hairline grid, a 2 px base, no glow or halo, a white tip in an accent ring;
- `C.speaker`: an e3 shadow around his shape instead of the glow ring; `fo.back` is ignored;
- `C.blocks`: one neutral grey (`#F3F3F5`) for every block;
- a film's palette (`HF.canvas(..., { look: "whitespace", palette: { acc } })`) is the page's one accent everywhere: the
  kit's components take it through `HF.C`, and the stage follows it (`C.G` / `C.GRAD`, the beam's node, the chart's
  stroke and tip, and the marker, which becomes 17 % of that accent on white);
- `C.parts` / `C.ui` / `HF.code` / `HF.compare` / sketches: the look's tokens (white cards, Inter, the one accent).

Content colours stay literal where they are content: a product's own UI in a real capture, an avatar.

## 5. What to avoid

- **"A competent keynote template."** The critic's verdict on chakra-redline v1, and the main risk of white plus restraint. The cure is what canvas_studio already has: real evidence shown big, 3D turns, a camera that travels, and his real room. A white page with flat cards and no camera is a slide deck.
- **A cool grey seamless.** It read as a template (the critic, 2026-10-20). The page is true white with only a slight neutral falloff.
- **White cards with no hairline.** On white they vanish; every surface keeps its e1-e3 shadow (the 1 px ring is part of it).
- **Two accents, gradients, glows and pastel blocks.** They are canvas_studio's language; here they read as noise.
- **Busy stations.** Three cards, two chips, a beam and a highlighter at once is canvas_studio density. Split it.
- **His room looking grey-beige next to pure white.** Grade his take with the "clean" A/B and let him choose; never whiten or mask his room to match.

## 6. Proof and files

- **The still sheet** (`sheet/` here, 2026-10-22): one canvas page with his card (the hook), a statement takeover, a
  system diagram, an evidence window, a chart card and the overview, built the way §4 says (tokens, a 26 px kicker),
  in whitespace and in canvas_studio for the same scenes. It also checks rule 7: a landed card or window that still
  moves on whitespace fails it (the diagram's cards keep canvas_studio's `drift: 1.2` on purpose, to prove the cap).
  ```sh
  uv run python kit/presets/whitespace/sheet/build.py --room <a take.mp4>   # his room in the card; without it, a test pattern
  node kit/presets/whitespace/sheet/shoot.mjs                                # -> output/temp/demos/whitespace_sheet/<look>_sheet.png
  ```
  The images stay out of the repo (they show his face; `kit/refs/me`). Looked at with an oss-editor take on 2026-10-22:
  it reads white, calm and premium, the cards set apart by their hairline and shadow alone, one violet mark per scene.
- `node kit/hf/demos/looks/check.mjs whitespace whitespace:studio`: the shared components in this look (through
  HF.canvas and HF.studio), contrast ≥ 3:1.
- The flat diagram (2026-10-22): `uv run python kit/hf/demos/diagram/build.py && node kit/hf/demos/diagram/shoot.mjs`
  (a loop, a process, a hub, layers, a 9:16 column and the takeover kind; the geometry gate and seek purity) and
  `tests/test_diagram_flat.py`. Looked at on 2026-10-22: one idea per diagram, a single violet focal box, the loop's
  meaning written on its own way back.
- `tests/test_looks_whitespace.py`: the tokens, canvas_studio's stage locked to its v10 literals, the drift and block
  rules, the palette accent, contrast.

| | |
|---|---|
| `kit/hf/core.js` | `HF.LOOKS.whitespace` (C, F) and `HF.LOOKS.whitespace.stage` (what the canvas paints) |
| `kit/hf/canvas.js` | the engine (`HF.canvas(..., { look: "whitespace" })`), reads the stage tokens |
| `kit/hf/studio.js`, `kit/hf/reel.js` | `HF.studio` / `HF.reel` `{ look }` (`HF.studioLook`) |
| `kit/hf/trans.js`, `kit/hf/motion.js` | the takeovers and transitions (`C.takeover`, `HF.trans`), the lens on him (`HF.motion.lens`) |
| `preset.json` | the tokens and the rules as numbers |
| `templates/template.html` | the scaffold of a new film: copy it to `films/<name>/src/` (§3, §4) |
| `sheet/` | the still sheet: `build.py`, `template.html` (a worked whitespace template), `shoot.mjs` |
| `kit/film/`, `kit/film/example/` | the pipeline every new film runs on, and a worked film that needs no footage |
| `kit/presets/canvas_studio/` | the camera grammar and the scene recipes this preset builds on |
