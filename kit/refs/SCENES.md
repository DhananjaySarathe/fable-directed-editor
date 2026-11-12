# Choosing scenes from meaning

Read this after the beat sheet and before writing the composition. Every passage of the script gets a visual that **helps the viewer understand it**, not one that looks busy. Pick by what the passage *does*, not by the words in it.

The plan is written as `visual_plan.json` and checked with `python3 kit/hf/plan_check.py visual_plan.json` before anything is built. The format and a filled example are in §5.

## 1. Two separate choices

1. **The explanation type**: what the passage does for the viewer (the table below). This picks the technique.
2. **The treatment**: how it looks. This is fixed by the preset (`preset_paper_studio`: clean vector, ink on paper, one orange accent, plus stickman accents). Change it per video, never per scene. A scene in a different style breaks the film.

## 2. Explanation types → technique

| Type | You hear… | Best technique (registry id) | Alternative (trade-off) | Fallback | Don't |
|---|---|---|---|---|---|
| **process** | steps, "first… then…", a workflow | `diagram` (living: reveal → focus the current step → tick done) | `flow_steps` / checklist (simpler, less spatial) | side `words` | a new diagram for every step |
| **comparison** | X vs Y, before/after, old way/new way | `compare` (aligned rows, verdict) | `before_after`, `split_screen` (one image per side) | two `card`s | unaligned lists |
| **quantity** | a number, growth, share | big number (`countUp` in `words`) or `stat_chart` | `people_grid` pictogram (concrete, slower) | `pill` with the number | invented or rounded-up numbers |
| **relationship** | connected parts, "talks to", data moving | `diagram` (shape `card`, edges, `flow` dots) | `stickman` roles (warmer, less exact) | `diagram` row | more than ~7 nodes on screen |
| **mechanism** | how it works inside, "under the hood" | `diagram` focus + `flow`, or `code` focus | cutaway (special case, expensive) | `card` with 3 parts | decoration without the actual parts |
| **story** | a problem, a consequence, a feeling | `stickman` moment (2–5 s) | `speaker` + side `words` (keeps the face) | `words` | stickman for facts or numbers |
| **analogy** | "it's like a…", library, factory, queue | `stickman` + props, mapped part by part | `diagram` with labelled metaphor nodes | `words` naming both sides | an analogy that isn't mapped back to the real thing |
| **chronology** | days, versions, history | `diagram` row with dates (layout row) | `calendar_page` / `streak_days` | `chapter` tags | a timeline with one event |
| **instruction** | "click", "go to", "type", a product step | `screen` (real recording: zoom, highlight, cursor) | `win` screenshot + scroll (no motion inside) | `card` with the step | a mock UI when the real screen exists |
| **code** | a function, a config, a command | `code` (highlight, diff) / `terminal` (real output) | `card` with the line | `pill` with the file name | more than ~10 visible lines; fake output |
| **conversation** | "I asked it…", it replied | `chat` | `ai_chat` (shorts) | `card` with the prompt | brand logos in mock UIs |
| **definition** | "X is…", naming a term | side `words` (2–4 words, serif) | `card` with one line | `pill` | the whole sentence on screen |
| **emphasis** | the punchline, a strong claim | side `words` or `C` framing (close) | `title_behind` (shorts) | nothing: the face | more than one per ~20 s |
| **proof** | "here it is", "you can see" | `screen` / `win` / `phone` (the real thing) | `card` with a quote | `pill` | a claim with no real artefact |
| **structure** | intro, chapters, recap, transitions | `lowerThird`, `chapter`, `diagram` recap (`show()` again) | `section_card` (shorts) | — | a title card before the speaker |
| **ask** | subscribe, comment, link | comment card, `endCard` | `comment_reply` (shorts) | `pill` | asking before giving value |

**Added 2026-10-09** (kit/hf/explain.js, kit/hf/polish.js; demo in kit/hf/demos/explain):

| Technique | Use it when you hear… | Don't |
|---|---|---|
| `tokens` (mechanism) | "it just predicts the next word", temperature, why it hallucinates | type the numbers: run `kit/hf/tools/nexttoken.py` and name the model on screen |
| `stack` (structure, mechanism) | "what's inside", "built on top of", model → harness → tools → app | stack things that aren't layered (use `diagram` for a network) |
| `race` (quantity, chronology) | "went from #4 to #1", a ranking over weeks | race a ranking that never changes order; data from `kit/hf/tools/arena_race.py` or another real source |
| `tiltIn` (instruction, proof) | "let me show you", right before a screen demo (`HF.screen(...).tilt(a, b)`) | use it on every window: it is the demo's entrance |
| `sweep` (emphasis) | the moment a name, price or number lands | sweep every card; one per moment, a few per video |
| `scramble` (emphasis) | revealing a model name, a secret, a key | more than once or twice a video |

Rejected after review (2026-10-09): ASCII/dither on the speaker, particle dissolves, orbiting logo rings, split-flap
boards. They are effects rather than explanations, clash with the one-accent paper look, or need brand logos.

When in doubt: **process → diagram, comparison → compare, human problem → stickman, product step → real screen, number → accurate number, connected system → diagram with flow, term → restrained words.**

## 3. Rules

- **The visual adds what the narration can't**: structure, the real screen, the exact number, the relation between things. Words on screen are 2–4 key words, never the sentence being said.
- **One diagram per idea, developing across passages.** Reveal it, focus the step being discussed, tick steps done, and come back to it for the recap (`diagram.show()` again; its state carries over).
- **Vary scenes only when it serves the explanation.** The same technique 3 passages in a row is a warning, unless it's the same developing diagram.
- **The face is the anchor, and he leaves on purpose** (2026-10-22, replacing "at least a third of the talking time"):
  the hook's first 3 s are his face; on long-form 15-30 % of the runtime is takeovers (full-screen scenes with him
  removed completely, 4-12 s each, at least 3 s of face between two, never away more than 12 s); seated full frame up
  to 30 %. Which passages go face-off is §9. The corner window keeps the face during inserts that aren't takeovers.
- **Real data only**: numbers, star counts, render times and outputs come from real pages and real runs. No invented statistics.
- **Readable on a phone**: evidence text ≥ 32 px in 16:9 (≥ 36 px in 9:16) as drawn, after any zoom (precheck `small`; EDITING.md §11); kickers and chrome may be smaller. At most ~10 code lines; zoom to the lines being discussed.
- **Motion carries meaning**: a camera move goes *to* the thing being said. No decorative spins or bounces. A shot the viewer reads may hold still: declare it (`read: true` / `S.hold`) and qa.py treats it as a hold; a still with nothing to read gets cut sooner (EDITING.md §6).
- **Stickman moments**: 2–4 per video, 2–5 s each, never back to back (`kit/stickman/README.md`).
- **Screen demos**: annotate only while the screen is still. Get coordinates from `kit/hf/tools/locate.py` (text search) or `grid.py`. Blur anything private.
- **Every scene has a fallback**: if the asset isn't there or the ratio is wrong, the fallback keeps the film working.

- **One metaphor that develops (2026-10-10, RESEARCH.md §3).** When a film explains with a metaphor, build it once
  and let it return and change (an object chosen in one beat becomes the actor in the next) instead of a new
  picture every sentence. Use the face to state the takeaway after it.
- **Treatment follows purpose (EDITING.md §11).** Relationships → a diagram in causal order; differences → a
  comparison that keeps both sides (`S.scoreboard` for results that accumulate); an operation → the real
  footage or screenshot, focused (`S.focus`); a result → room to look (a hold); a feeling → the face.

## 4. Ratios

- **16:9**: side layouts (content beside the speaker), wide diagrams (layout row), compare, screen demos at fit-width.
- **9:16**: top panel graphics with the face panel below (`camera` mode `panel`), diagrams in layout column, screen demos as zoomed crops (zoom into the region; a full desktop is unreadable on a phone), compare as stacked cards.

## 5. The plan (`visual_plan.json`)

```json
{
  "film": "how-ai-editor-reuses-assets", "ratio": "16:9", "preset": "preset_whitespace", "edl": "edl.json", "schema": 2,
  "passages": [
    { "id": "p3", "words": [210, 248], "goal": "See that every video goes through the same five steps",
      "type": "process", "technique": "diagram", "why": "five ordered steps; the diagram returns as the recap",
      "beats": [ { "at": 212, "show": "five nodes reveal left to right" }, { "at": 231, "show": "focus 'Clean up', note 'skill file'" } ],
      "assets": [], "fallback": "flow_steps", "diagram": "workflow",
      "face": "off", "transition": "zoom", "groups": 2 },
    { "id": "p4", "words": [249, 270], "goal": "The takeaway, from him", "type": "emphasis", "technique": "kinetic",
      "why": "the line after a takeover is his", "beats": [ { "at": 262, "show": "two words land beside him" } ],
      "face": "full", "cam": "push", "transition": "cut", "groups": 1 }
  ]
}
```

- `words` are word indices in the cut (from `edl.json`). Use `"t": [a, b]` in seconds instead when there is no EDL yet.
- `beats[].at` is a word index (or a time). `diagram` names a diagram that several passages share (develops, not redrawn).
- Required fields: `id`, `words` or `t`, `goal`, `type`, `technique`, `beats`. `fallback` is required for `screen`, `code`, `terminal`, `diagram` and `stickman`.
- **Schema 2** (2026-10-22, `"schema": 2`): where he is, how the camera moves on him, how much is on screen, and how
  the passage is entered. Every field is optional with a default; set them where the passage needs a decision.
  - `face`: `on` (default: a card or circle beside the content), `off` (a takeover: he is removed completely and the
    scene has the whole frame; §9), `corner`, `full` (seated full frame, cropped to a clean rect of his plain wall,
    never a cut-out) or `frame` (the seated 'frame' card). With no `face`, the `box` beat implies one
    (`graphic` = off, `face`/`punch` = full, `corner` = corner, the rest = on).
  - `cam`: the lens on him across the passage: `push` (+6-12 % across the thought), `pull`, `punch` (x1.12-1.18 on
    the stressed word, one per 12 s at most), `arc` (truck <= 3 % and roll <= 0.6°), `drift`, or `hold` (a still
    frame, declared: keep it under 8 s). With no `cam` the lens picks one (§10).
  - `groups`: visual groups the scene puts up at once besides him (default 3: the hero and one or two supporting chips
    or lines; his shape, captions and chrome don't count, as in precheck's density gate). More than 3 warns "heavy";
    set `"dense": "<why>"` when the pile-up is the point (`overwhelm-surround`).
  - `bg`: the page behind it (default `white`, the whitespace look). It never means whitening his room.
  - `transition`: how the passage is entered: `cut`, `whip`, `zoom` (zoom-through), `match` (a shape carries over),
    `chapter` or `card`. The kit's own transitions (each logs itself to `window.__trans`), no shader transitions.
  - `form` (plan level): `long` or `reel`; by default 9:16 or under 2 minutes is a Reel.

A full example: `kit/hf/examples/visual_plan.example.json` (the labelled sample "how an AI video editor reuses assets").

`plan_check.py` checks:
- types and techniques exist, and the technique explains the type;
- the ratio is supported and fallbacks are valid;
- timing is within each component's limits;
- stickman count and length, and no repeated runs;
- assets exist, goals are written, and at most 40 % of passages are words-only;
- one box layout over 35 % of the time (left and right count as one layout);
- music: a Reel of 45 s or more with no music moment; on long-form, a `drop` or `riser` (long-form beds are calm:
  18 dB under the voice, they `turn` or `stop`, never drop or rise; OWNER_DEFAULTS §4);
- schema 2: the face-off share on long-form (15-30 %), each takeover 4-12 s, at least 3 s of face between two, never
  away more than 12 s (an error), the hook's first 3 s on his face (an error on long-form), seated full frame <= 30 %,
  a `hold` on him over 8 s (not in a `corner`, §10), punches under 12 s apart, the same transition in two
  neighbouring passages (cuts may repeat; a passage with no `transition` is entered on a cut), whips over 40 % of the
  planned transitions, and groups over 3. When the face-off share is under 15 % it lists the passages §9 would take
  him off for. A schema-1 plan gets a NOTE that these budgets were skipped (its exit code is unchanged).

`--key` prints a cache key covering the plan, the component versions, the kit files, the preset and the output settings.
`--edl=<edl.json>` times `words` spans when the plan names no EDL. `python -m kit.film <film> draft|render` runs
plan_check first: errors stop the build (`--force` goes on), warnings print.

## 6. Light and look by meaning

The grade is part of the explanation too. Each passage may carry a `look` (kit/look/looks.py). Light changes are motivated by the story, like a cinematographer's lighting cues:

| Look | Use it for | What it does |
|---|---|---|
| `natural` | the default: talking, explaining | the channel's look: cream wall, lit face, gentle contrast |
| `bright` | payoffs, results, good news | lifted, airy, open shadows |
| `cinematic` | hooks, big claims, launch films | film S-curve, darker cool room, warm face, halation, grain |
| `moody` | setbacks, consequences, confessions | the room falls into shadow, the face keeps a warm pool of light |
| `film` | flashbacks, "how it started" | faded blacks, warm highlights, green-cyan shadows, grain |
| `noir` | rare: one dramatic line or quote | black and white, red-filter mix, hard contrast |

**Rules:**
- Most of the video is `natural`. Use at most 2–3 other looks per video, each held for at least 3 s.
- Switch on a cut (a hard change), or as a motivated "lights dim / lights up" moment: a 0.8–1.2 s fade landing on the emotional word. In the plan, set `"look_at": <word index>` (and optionally `"look_fade"`).
- Never flicker between looks passage by passage.
- Verify with `python3 kit/look/scopes.py` or `grade.py --sheet` (numbers):
  - skin hue stays within about ±4° of the source's own skin hue;
  - skin saturation stays 0.09–0.14 (above 0.14 reads orange);
  - blacks are not pinned at 0 (moody ≥ 0.008) and whites are not clipped.

`python3 kit/look/looks.py switches visual_plan.json edl.json looks.json` turns the plan's looks into `grade.py --looks=looks.json`.

## 7. The speaker box (motion between the face and the graphics)

When a film moves the speaker as a box (full frame ⇄ tilted card ⇄ pill ⇄ gone), give each passage a `box` beat
(`{ "show": "beside", "side": "left" }`) and let `HF.box.direct` choose the moves. The grammar, the measured timings
and the budgets are in `kit/refs/MOTION.md`.

## 8. Scene blueprints for AI and dev explainers (2026-10-20)

Proven multi-beat shapes, summarised from the HyperFrames team's `hyperframes-animation` skill (22 blueprints measured on
real motion pieces; Apache-2.0, github.com/heygen-com/hyperframes, skills/hyperframes-animation/blueprints-index.md).
They name a passage's arc; the kit's techniques build them. Pick one per passage that carries a feature, a demo or the
payoff, and say which in visual_plan.json (`"blueprint"`), so a reviewer knows the arc you meant.

| blueprint | the arc | builds with |
|---|---|---|
| prompt-type-submit-generate | a prompt types into a real input, the machine visibly works, the answer/diff/artifact lands | `ui.message`, kit/graphics `ai_chat`, `catalog.notes-typing`; the real screenshot as proof after it |
| agent-progress-theater | one trigger hands the frame to the agent: status lines swap while it works, then the receipt cascades in | agent.js (`A.*`), `catalog.agent-cursor` over the screen, `ui.checklist` as the receipt |
| cursor-ui-demo | a cursor drives the app through clicks; the camera chases each one | `catalog.cursor-zoom-follow` on his own screenshot, screen.js |
| transcript-scroll-artifact-reveal | the camera travels down one long output (a transcript, a log, a doc) reading it as evidence, then one focal click | `focus` on a tall screenshot, code.js scroll, `catalog.cursor-text-select` for the line that matters |
| camera-journey / spatial-pan-stations | one continuous world; the camera dives in, something fires, it travels to the consequence | canvas.js `C.cam` + stations (canvas_studio) |
| zoom-out-workspace-reveal | open tight on one detail, one long decelerating pull-out reveals the whole workspace | `C.cam` z from 2.4 to 1 (ease out), or `focus` released |
| dataviz-countup | the number carries the argument: count-up, trend, then push through to one hero metric | `canvas.chart`, `scoreboard`, `catalog.decline-chart`, `catalog.conic-progress-ring` (real numbers only) |
| comparison-split | two equal items enter from opposite sides with mirrored tilts, a badge pops on each | `compare`, `scoreboard`, canvas 3D cards |
| kinetic-type-beats / ticker-takeover | the motion is the words changing; a cycling word is shoved aside by the answer | kinetic.js, `catalog.headline-slam` |
| fixed-anchor-cycle | one element stays pinned while everything around it cycles | a kept card + `ui.*` swaps, kinetic word swaps |
| typewriter-reveal | someone is typing this: a caret types, edits, then the payoff pops | code.js typing, `catalog.notes-typing` |
| overwhelm-surround | the pain by accumulation: surfaces pile in and close in from all sides | collage, `ui.notif` stacks |
| titlecard-reveal | the breather: one clean card, ONE restrained move, then a still hold | `chapter`, `S.hold`, a quiet moment (`S.quiet`) |

Rhythm: after two or three dense beats, give one titlecard-style breather; land the payoff on a music turn
(`"music": "turn"` on long-form, whose beds stay calm; a `"drop"` on a Reel; kit/film/README "mix"). Catalog pieces (`catalog.*`) are mounted from film.py MOUNTS
(kit/hf/mounts.py) and listed with `python3 kit/hf/tools/catalog.py --list`.

Since 2026-10-20 the kit also has (kit/hf/README "Motion additions", "Backgrounds, emoji and icons"): `morph` (a state
change: x -> check, play -> pause), `shake` (a fail), `drawIcon` (a step or item that draws itself on), `emoji` (a
reaction beat: one per beat, never decoration), `shaderBg` (a title card, a payoff, an intro world) and kinetic
`cascade` / `focus` styles. They count as distinct components for plan_check and precheck.

## 9. When to remove him (2026-10-22)

The owner asked for "out-of-the-box full-screen animation scenes where he is removed completely". A takeover is a
passage with `"face": "off"`: no circle, no corner, no card. The scene has the whole white frame and his voice carries
on underneath (it never trims or reorders a word). He is absent, never cut out.

**Face off** when the passage *shows a thing* for 5 s or more and carries no claim, feeling or ask:

| type | why the frame is better without him |
|---|---|
| process | the steps need the width, and the viewer follows the order, not his face |
| mechanism | the parts and the flow between them are the explanation |
| relationship | the edges between things are the point; a speaker shape is one more node |
| chronology | a row of dates reads left to right across the whole frame |
| quantity | one number, big, alone (a real number only) |
| proof (on-screen) | the real page, screen or output, focused, at a size a phone can read |

**Face on** for:
- the hook's first 3 s (frame 1 is his face, even when the hook's promise is a graphic: it lands beside him);
- story, feelings, confessions and consequences (the face carries them, §3 "a feeling → the face");
- the punches: the stressed claim, the punchline (`cam: "punch"`);
- the ask (subscribe, the link, the comment prompt);
- the takeaway line after each takeover: the scene shows it, he says what it means (at least 3 s of face before the
  next takeover).

Budgets (long-form; plan_check warns outside them, precheck measures them on the page): 15-30 % of the runtime in
takeovers, each 4-12 s (a longer process is split by a face beat on its takeaway), never away more than 12 s.
A Reel follows the same rules for its hook and the 12 s limit; its share is free. Shares count each second once:
passages that overlap are merged first. precheck measures them from the engine's `window.__speaker`; on a page from
before it, on / off is estimated (the page's own face, a shown box, a full-bleed plate of him) and those findings
say so, at MEDIUM.

Each takeover needs motion inside it (a build, the camera travelling between stations, a focus on the line), or it
becomes the slideshow the critic flags. Enter and leave it with a transition that means something (§10).

## 10. Holistic, not heavy: one idea per frame, a camera on him (2026-10-22)

- **One idea per frame.** At most 3 visual groups up at once besides him (a card, a chip, a window, a block of big
  type, a mount, a graphic; his shape, captions and chrome don't count): the hero and one or two supporting chips or
  source lines. A component can mark its own group with `data-group="<name>"`. precheck's density gate flags more than
  3 for over 2 s (MEDIUM) and more than 5 for over 2 s (HIGH), and it outranks the variety minimum: a calm film meets
  the bar with fewer components (long-form 1.2 a minute, 6-10), and a fix never adds an element to a frame already at 3.
- **Whitespace.** The page is white and mostly empty; elements land once, then stay still. The camera carries the
  energy, not more elements.
- **His face moves.** While he is on, the framing changes every 4-8 s: a push across a thought, a pull-out to
  reset, an eased punch on a stressed word (one per 12 s at most), a slight arc (truck <= 3 %, roll <= 0.6°), a settle
  after a whip. No handheld shake, and never past the footage's resolution budget (the lens reads work/tracks.json).
  precheck reports framing changes per minute and the longest unchanged framing (MEDIUM > 8 s, HIGH > 15 s, unless
  the lens declares a hold). A `corner` is not judged by either tool: it is too small for the lens to move on, and
  it only holds his face through an insert that is not a takeover (precheck prints its seconds as "in a corner:
  framing not judged"; going into or out of it counts as a framing change).
- **Vary where he sits.** No layout over 35 % of the runtime, and a card beside the content is one layout whichever
  side it is on (OWNER_DEFAULTS §1). precheck fails a page that publishes `window.__speaker` on the merged share; on a
  page from before v11 one side over 35 % still fails and the merged share is a MEDIUM, so an approved film does not
  stop on a rule it was never built for.
- **Transitions vary and mean something.** A `cut` keeps the thought going; a `whip` moves to the next station of the
  same world; a `zoom` dives into the detail being explained; a `match` carries a shape from one scene into the next;
  a `chapter` or a `card` opens a new section. Never the same kind twice in a row (cuts may repeat), whips at most
  40 % (plan_check plans it between neighbouring passages, precheck reads the page's `window.__trans`).

