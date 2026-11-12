---
name: video-shorts
description: Edit talking-head footage into posting-quality video, either a 9:16 short/reel or a 16:9 YouTube long-form with motion graphics, using the local toolkit (whisper.cpp, the look v2 grade, HyperFrames compositions, an HTML graphics library, ffmpeg, severity-graded QA plus a fresh critic). Use when the user gives a video file and asks for a short, a reel, a long-form edit, a clean cut, captions, graphics, or removing fillers and pauses.
---

**Who runs the edit:** the `fable-director` skill (load it first). It sets the roles (the main session on Fable 5.2 directs
and designs; the agents in `.claude/agents/` check facts, read reports, apply fix lists and review), the order of the run and
how a reference video is matched. This skill is the kit's manual. Read the long manuals by section, not whole:
`python3 kit/doc.py kit/hf/README.md` lists the sections, `python3 kit/doc.py kit/hf/README.md "The lens"` prints one.

## Read first, every edit

- **`kit/refs/OWNER_DEFAULTS.md`, before anything else.** It holds the owner's standing taste, so he never has to say
  it again: a hook of 10 s or less that opens on his face, fast, the white page by default (`preset_whitespace`), one
  idea per frame, takeovers (he is off screen 15-30 % of a long film, 4-12 s at a time, never away over 12 s), the
  camera on him (the lens: a visible, smooth framing change every 4-8 s, eased punches, no shake), transitions that
  vary, animations that explain, the whole kit, him never cut out and his room as shot (the clean grade as an A/B),
  music ~12 dB under on Reels and a calm bed ~18 dB under on long-form that ducks on his voice (no EDM/rock, no drops),
  whole sentences, standalone Reels with no end screen. A brief can be stricter, never plainer.
- **The planning gate, every edit (long-form and Reels), before the template is written** (OWNER_DEFAULTS §8):
  1. Write `kit/refs/SCENES.md` → `visual_plan.json`, schema 2 (`"schema": 2`): one passage per idea with its type,
     technique from `kit/hf/registry.json`, `face` (on | off | corner | full | frame), `cam` (the lens move),
     `groups` and `transition`.
  2. Run `python3 kit/hf/plan_check.py visual_plan.json` and get 0 errors, with every warning fixed or answered in the
     brief. It also flags a technique outside the look, too few distinct techniques, a layout over 35 % (left and
     right merged) and the schema-2 budgets: away over 12 s and a long-form hook off his face are errors; takeover
     lengths and share, seated full frame over 30 %, punch spacing, a repeated transition, whips over 40 % and more
     than 3 groups are warnings. kit/film runs it first, before every draft and render: an error stops the build.
  3. `python3 kit/hf/tools/registry.py --unused` lists the components no film has tried. Look there first.
  4. After the build, precheck's ambition, speaker and density sections are gated like its defects: components per
     minute, layout share, the longest stretch with nothing new, parts left on screen with no end, his framing (a
     change every 4-8 s; a corner is not judged), time away, the zoom budget and groups on screen. Its last line is
     the verdict with every HIGH by kind and time: read that line first.
- **A new long film runs on `kit/film`** (`kit/film/README.md`, 2026-10-20). Don't copy a past film's
  `edl.py` / `build.py` / `audio.py`, nor a preset's `templates/edl.py` / `build.py` (they write no lens, no
  tracks.json budget and the v10 sound). The film is `films/<name>/film.py` (SOURCES, KEEP, JUDGED, fixes, spellings,
  MUSIC, REELS), `visual_plan.json` and `src/template.html` (on the default look, start from
  `kit/presets/whitespace/templates/template.html`; `kit/film/example` is a worked film that runs with no footage). Every step is
  `uv run python -m kit.film films/<name> prep|cut|joins|grade|build|mix|draft|render|mux|reels`, and a Reel cut from the
  film is `kit.film films/<name>/reels/<r> build|draft|render`. It carries the voice prep (DeepFilterNet3, WPE only when the mics differ, a measured EQ, room tone), the look v2
  grade of the cut (his room as shot: no vignette or matte), the frame-grid cut (Framecast's 0.02 s offset), the join re-listen, respelled captions placed on their sound, the mix, chunked 4K and Reels by whole
  sentences. The worked example is `kit/film/example` (a test pattern and a synthetic voice, end to end). A Reel from
  its own single take stays on `kit/reel`.
- **Version 10 tools (2026-10-20), plan with them every edit** (kit/hf/README "Catalog pieces", "Motion additions",
  "Backgrounds, emoji and icons"; kit/film/README "mix"):
  - **Music on the story:** set `"music": "drop" | "stop" | "riser" | "turn"` on 2-4 passages; on a Reel, in film.py
    MUSIC use `drop="auto", at="w<id>"` (the track's biggest rise lands on that word, from kit/music/beats.json) instead
    of measuring drops. On long-form only "stop" and "turn" (a calm bed ~18 dB under, no drops or risers:
    OWNER_DEFAULTS §4, 2026-10-21); every bed snaps to a downbeat; `end_on="track_end"` ends a film on the track's own ending.
    qa.py reports mid-bar entries and music turns with nothing on screen. A new track: `kit/audio/beats.py --all`.
  - **Arcs:** name each feature/demo/payoff passage's blueprint (kit/refs/SCENES.md §8: prompt-type-submit-generate,
    agent-progress-theater, cursor-ui-demo, dataviz-countup, titlecard-reveal for the breather...).
  - **Catalog pieces** (film.py MOUNTS, kit/hf/mounts.py): `cursor-zoom-follow` on his real screenshot for any screen
    demo, `cursor-text-select` for the line that matters, `agent-cursor`, `marker-highlight`, `headline-slam`,
    `push-in`, `notes-typing`, `decline-chart` / `conic-progress-ring` (real numbers only), `chat-thread` (Reels).
  - **Motion:** kinetic `cascade` and `focus` (face: "look"), `HF.morph` for a state change (x -> check on a verdict),
    `HF.shake` for a fail, `HF.drawIcon` (222 Lucide icons) for steps, camera zooms are even-paced by themselves.
  - **Living backgrounds and reactions:** `HF.shaderBg` (grain, mesh, rays, warp) for a title card, a payoff or an
    intro world, never behind his face and never on the white page (whitespace README §2.1); `HF.emoji` (51 Noto animated) for one reaction beat; `HF.parallax` for a still
    photo (depth from `kit/look/depth.py`). kit/film's build writes `output/final/<film>/credits.txt` (music that needs
    credit + Noto): put it in the posting notes.
  - Check sheets: `kit/hf/demos/motion/build.py --sheet`, `kit/hf/demos/catalog/build.py --sheet`.
- **Version 11 (2026-10-22), every new edit uses these without being asked** (OWNER_DEFAULTS §1, §4, §8):
  - **The white page:** `{ look: "whitespace" }` on HF.canvas / HF.studio / HF.reel (kit/presets/whitespace/README.md).
  - **Takeovers:** `C.takeover(a, b, { kind: "type" | "diagram" | "evidence" | "list" })` on canvas,
    `S.takeover(...)` on HF.studio / HF.reel (declared before `S.box()`); they may not overlap. Diagrams follow
    `kit/refs/DIAGRAMS.md` (flat: at most 5 boxes, 1-2 word names, the loop's way back `accent: true`).
  - **Transitions:** a takeover's `in` / `out` and `HF.trans` (`T.zoomThrough`, `T.match`, `T.chapter`,
    `T.cardToGraphic`, `T.whip`, `T.cut`), logged to `window.__trans`: never the same kind twice in a row, whips at
    most 40 % (kit/hf/README "Takeovers and transitions").
  - **The lens:** on for every kit/film page made from 2026-10-22; `STRESS` word ids and the plan's `cam` steer it
    (kit/hf/README "The lens"). Its budget comes from work/tracks.json (`TRACK_SIZE = {"<track>": "native"}` keeps a
    4K take's headroom); don't add inline punch-in loops.
  - **The sound:** kit/film/mix.py's v11 mix (voice-keyed duck, a looped calm bed whose seam times it prints: listen
    to each, downbeat crossfades, SFX families within 8 small cues a minute on films and 12 on Reels). Sticky per film
    (music.json `"sound"`); `SOUND` in film.py wins.
  - **The grade:** `kit.film <film> grade --sheet=8,30,120` puts the "clean" grade beside the film's look on white:
    offer it as an A/B, then set `GRADE`.
- `kit/refs/REFERENCE.md`: what top channels measurably do (look, captions, layouts) and the current standard: HyperFrames builds and renders, our kit does the footage.
- `kit/refs/EDITING.md`: the playbook, with stage gates, cutting rules, pacing, hooks, captions and safe zones, motion rules, sound levels, QA, the critic and the fix loop. Follow it; its numbers are the defaults.

## Speed and cost (2026-10-10): every new edit

The owner's rule: faster and cheaper, with no loss of quality. The ai-workflows film took 6-7 h. Most of it went into
hand-written scene code and 4K re-renders that found bugs, not into the 4K render itself. So:
1. **Reuse, don't rewrite.**
   - Build on `kit/hf/studio.js` + `studio_ui.js` (`HF.studio`: world, chrome, chapter cards, word-synced type, scene layers, box wiring; `S.ui.*`: tested UI cards) and `kit/audio/mix.py` (beds, cues, master).
   - A film's template is its scenes only (`kit/film/example/src/template.html` is a small model).
   - When a film needs something reusable, add it to the kit with a line in its README, not to the film.
2. **The voice first.** Run `python -m kit.film films/<name> cut --voice` (old films: `edl.py --voice`), then `joins`: measure every join on the voice envelope before any picture work. Edges sit in real quiet (onset/offset), never inside a breath or a word. In the first minute there are no in-sentence repairs.
3. **Prechecks before any render.** `node kit/qa/precheck.mjs $HF/index.html` takes ~5 s and must show 0 HIGH: offscreen text, text over the face, overlaps, blank world, page errors, parts that linger with no end, and the ambition section (distinct components, layout share ≤ 35 %, the longest stretch with nothing new, the box pace), and the speaker and density sections (his framing, time away, the zoom budget, groups on screen). Read its last line first: the verdict with every HIGH. kit/film turns the ambition gate off by itself for a film made before 2026-10-22 (`AMBITION` in film.py wins; `--no-ambition` / `--ambition` force it); by hand, `--no-ambition` is only for such a film. Also read the mixer's WARNING and dropout lines.
4. **Draft first.** `--resolution 1080p --quality draft` takes ~3.5 min for 5 min. `qa.py` and the fresh critic run on the draft. Render 4K **once**, at the end (~18 min).
5. **Grade faster.** Use `GRADE_WORKERS=12` (`kit/look/grade.py`) at 1080p; at 4K use 6 on this 24 GB Mac (12 workers at ~1 GB each swapped: 1.2 fps against 3.5 fps with 6, chakra-interview 2026-10-31). A face track's black stretches (where only the screen shows) pass through with `kinds={None: None}` in GRADE. Run only one 4K grade or render at a time on this Mac, and tell other sessions (SendMessage) before and after.

## Presets (named, approved styles)

When the user names a preset ("preset_paper_studio", "paper studio", "the how-i-edit style"), read `kit/presets/<name>/README.md` first and follow it end to end. It has the pipeline commands, the look, the design tokens (`preset.json`), the templates (`templates/`) and a worked example (`example/`). The index is `kit/presets/README.md`. For a new talking-head edit (16:9 long-form, a sample or a Reel) with no preset named, use **`preset_whitespace`** (the default since 2026-10-22, from his asks "holistic, not heavy" and "a white background"; invoke the `canvas-studio` skill and read `kit/presets/whitespace/README.md`): canvas_studio's stage and camera on a true white page with restraint, one idea per frame, takeovers where a passage shows a thing, the lens on him, him ONLY full frame or in a circle or a card (never cut out). Show a sample before a whole film until the owner has approved the look once. **`preset_canvas_studio`** (his approved look, "Yeah, it's a nice edit", the default 2026-10-20 to 10-22), `preset_pastel_box` (the reference look, the default 2026-10-10 to 10-20) and `preset_paper_studio` (calm) are the alternatives when he names them. **`preset_redline`** (2026-10-19, built from his `github/reverse-engineer` thumbnail; not yet used on a real take) is the minimal one: graph paper, black grotesk, one red pen only on claim words, pencil sketches, real screens as numbered figures marked on a tracing sheet, his real room in square framed windows, hard cuts (`kit/hf/redline.js`, `kit/presets/redline/README.md`). Use it when he asks for minimal, clean, notebook, redline or "like the thumbnail".

**Scene components and planning** (`kit/hf/`, README there): for every edit, plan scenes from meaning with `kit/refs/SCENES.md`, then write `visual_plan.json` and check it with `python3 kit/hf/plan_check.py` (the gate above). The catalogue is `kit/hf/registry.json`: 154 components (10 of them HyperFrames catalog pieces, `catalog.*`; 9 of them v11 takeovers and transitions, `takeover.*`, `trans.*`, `canvas.takeover`), each with what it explains, the looks it has been used in and the films that used it (`python3 kit/hf/tools/registry.py` regenerates it from the module headers). Then build the composition from kit components:
- the speaker camera, side cards, inserts and windows;
- the living diagram;
- annotated screen demos on real recordings (find coordinates with `kit/hf/tools/locate.py`);
- code and terminal walkthroughs, compare, chat, lower third, chapters and the end card.

`showcase/` is the worked example. Inline the kit with `kit/hf/vendor.py` (it includes the Reel kit: reel.js, footage.js, agent.js, night_reel.js), and mux audio with `-aac_pns 0`. Re-listen to a film's joins with `uv run python -m kit.cut.relisten <edl.json> <vo.wav>`. Render anything over ~2 min at 4K with `uv run python kit/hf/render4k.py films/<video>` (30 s chunks).

**Stickman moments** (`kit/stickman/`, README there): an ink stick-figure rig for 2 to 4 short moments per video (a metaphor, an emotional beat, a process acted out, a role), never a whole video. Pick the moments in the beat sheet and say which lines they illustrate.

## Version 7 defaults (2026-10-05): every new edit uses these

The owner's rules behind them:
- never cut a sentence midway or splice half-sentences;
- the grade, camera motion and animation must look premium;
- old videos are not re-edited.

Read `kit/refs/EDITING.md` §9 for the details.
1. **Cuts are sentence-safe by construction.**
   - Build the boundary map after the transcript: `uv run python -m kit.cut.sentmap <job>`.
   - Pick keep ranges with `kit/cut/boundaries.py` (`snap`; `restart_cut` on a retake).
   - Gate the edit list with `uv run python -m kit.cut.cutcheck <edl.json> --sources=...`:
     - exit 3 means a chopped or spliced sentence, so fix it;
     - REVIEW items are judged by you, with the text either side;
     - re-run with `--media=<final.mp4>` next to qa.py.
2. **Grade with look v2:** `kit/look/grade.py --v2`.
   - Make the face track with `kit/look/faces.py`, not the mask track.
   - Check with `kit/look/scopes.py qa`.
   - Use `--reel` for 9:16.
   - Face brightness is set halfway between the colourist target and the old engine; that's the owner's choice.
3. **Camera from the director** (`kit/hf/motion.js` + `kit/motion/camera.py`), for `HF.camera` films only (a full-frame A-roll with no box and no canvas shape; `kit/hf/showcase` is one):
   - `camera.plan(...)` with a per-frame face track and tags (`punch`, `joke`, `story`, `section`);
   - `camera.bake(...)` for the motion-blurred moves;
   - in the template, `HF.camera(K, st, {plan: D.camera})`.
   - Reframes come only at new thoughts and are held for the whole thought. In these films, never use A/B framing on every cut. Budgets are in kit/hf/README "v7 camera".
   - **Box and canvas films (every new edit since 2026-10-22) use the lens instead** (`HF.motion.lens`, kit/hf/README "The lens"): one move per thought every 4-8 s, eased punches on stressed words, and an eased reframe on every join by design (it replaces the old hard ×1.12 jump steps).
4. **Hand-made styles** (kit/hf/README "v7 styles"): `HF.sketch` (diagrams), `HF.annotate` (marker notes on screenshots/code), `HF.scribble` (outline around the speaker; build it with `kit/hf/tools/scribble.py`), `HF.collage` (paper cut-out).
   - Use 2–3 of these per video, one per passage, never two on the same frame. They come on top of the stickman's 2–4 moments.
5. **Every Reel gets a hook designed for it** (EDITING.md §4). There is no fixed template.
   - In the brief, write 3 candidate openings and score them. Show the user the pick and the reason.
   - Voice and face from frame 0; the number or proof on screen by ~3 s; one text line of 5 words or fewer, inside y 270–1250.
   - Then a purpose beat of at most ~2.5 s that adds the proof or the map of what's compared, never a repeat of the hook. End on the verdict line.
   - Before a shoot, suggest 2–3 hook lines for the user to say to camera with the number in them.

## Version 8 motion (2026-10-07): new reels and films

For new edits (not old videos, and not inside preset_paper_studio's calm look unless the user asks), animate with
`kit/hf/kinetic.js` (kit/hf/README "v8 motion"):
- motion tokens `HF.E.*` instead of stock eases, and springs from `HF.SPRING` (bounce only for things with momentum);
- `HF.land` / `HF.leave` for cards and panels (several properties with offsets, exits shorter than entrances);
- `HF.kinetic` for on-screen text, timed to the spoken words (`from`/`to` word ids), the stressed words boxed;
- a sound where a landing means something (a result, a click that causes the next shot, a section change), one frame
  early, never late; not on every landing or every word (EDITING.md §7: mix.py thins small cues to 6–12 a minute).

## Evidence and readability (2026-10-10): every new film and Reel

From the reference study (`kit/refs/RESEARCH.md`): the references show the real thing big enough to read and keep
earlier results on screen; ours showed small mock cards and placeholder payoffs. Rules in EDITING.md §11; the parts:
- plan each beat's **purpose** first (premise, proof, action, comparison, explanation, friction, reaction, cost,
  limitation, payoff), then pick the treatment: diagram for relationships, comparison for differences, the real
  footage or screenshot for an operation, a hold for a result, the face (maybe `S.quiet`) for a feeling;
- `S.focus(L, card, { at, until, line, click })` zooms to what is being read; `S.scoreboard(...)` keeps results on
  screen as they land; `S.quiet(a, b)` takes the music out for a price, failure or reaction (kit/hf/evidence.js);
- `S.layer(a, b, par, { read: true })` or `S.hold(a, b, why)` for a still the viewer reads. Never add float or drift to
  pass the freeze check: `precheck.mjs --holds-out` + `qa.py --holds` accept readable stills;
- precheck's `small` (under 32 px on 16:9, 36 px on 9:16) and `read` (gone before it can be read) are fixed before
  the draft render; a payoff never shows placeholder lines: real content, or ask the owner for the screenshot;
- when he films, give him `kit/refs/FILMING.md` (screen recordings, the result on screen, light) once per new setup.
- one process through its states (prompt → running → result): `S.flow(par, { states })`, one container that changes
  shape; on a real screen recording, `sd.walk(steps)` (the cursor leads, the camera follows) — EDITING.md §11;
- sound cues are given at the moment they should be heard; mix.py aligns each file's attack or peak (EDITING.md §7);
- conversations/podcasts: EDITING.md §12 (graphics inside one speaker's uncut audio, faces between, faithful copy).
- **podcasts / conversations (one camera)**: invoke the `podcast` skill (kit/podcast/README.md): speakers from mouth motion,
  trims for review, a virtual-multicam camera, gentle sound, a light grade, and a plan the owner approves before rendering.
- **paper-collage look** (photoreal cut-out objects on aged paper, stamps, tape, marker ink; the owner's 2026-10-11 favourite):
  for a Reel hook or explainer beat about a thing/price/trend, invoke the `paper-collage` skill (kit/presets/paper_collage).

## Premium edits and long-form (the current standard)

For long-form 16:9, for reels built from several takes, and whenever the user wants top-creator quality:
1. Ingest and glossary-fix the transcript (`shorts probe --landscape` and `shorts analyze` for the word timings), then write the brief and beat sheet, show them to the user, and score the scene plan's slideshow risk (EDITING.md §1, §8).
2. Cut-outs (legacy, before 2026-10-19: he is never cut out now, OWNER_DEFAULTS §2; a scene that needs the whole frame is a takeover): `python3 kit/look/cutout.py <clip> <out.webm> [--from= --to=]` produces one transparent graded WebM (about 70–85 MB/min); its temporary files are deleted automatically. Use it today only for its `--plate=` output (his graded room, uncut) on a short sample; a film grades with `kit.film <film> grade`.
3. Build a HyperFrames composition. A new film is built on `kit/film` with the default look (above). `kit/film/example` and `kit/hf/showcase/src/template.html` are the worked examples.
   - Run `npx hyperframes lint`, then `npx hyperframes snapshot` and look at the frames.
   - Render with `npx hyperframes render --quality delivery`, then master to −14 LUFS (`build.py --master` shows how).
4. QA: `node kit/qa/precheck.mjs <hf>/index.html --holds-out=<holds.json>` first (layout, phone-readable text, reading time; ~5 s), then a 1080p draft render, then `python3 kit/qa/qa.py <video> --cuts=<cuts.json> --expect-duration=<s> --expect-size=WxH --holds=<holds.json>,<cues.holds.json>` on the draft (a readable still is a hold, not a freeze). Exit 3 is FAIL, so fix and re-render the draft; never deliver it. The final 4K render gets `qa.py` again. `python3 kit/qa/sheet.py <video> <dir> --cuts=...` makes the review sheets.
5. Critic: follow `kit/qa/CRITIC.md`. A fresh `edit-critic` agent judges only the (draft) render and the brief, and the findings go into `review/ledger.md`. Only whitelist fixes may be made without asking, with at most 3 rounds.
6. Deliver the video, `captions.srt` (long-form keeps captions off the picture) and the posting notes, and list any open items.
7. Thumbnails, when the user asks (the edit desk's "Thumbnail kit" button): follow `kit/thumbs/THUMBNAILS.md`. It writes a ChatGPT prompt for three thumbnails (or one reel cover) and pulls face frames to attach to it.

# Take ingest (`shorts` CLI)

Every edit (Reel, long-form, podcast) starts with the `shorts` CLI, run from the repository root as `uv run shorts …`.
It only ingests: the editing itself is the kit (`kit/reel/README.md` for Reels, the presets and `kit/hf/README.md` for
long-form, the `podcast` skill for conversations).
- **Output:** every command prints one JSON object. Read it before the next step.
- **Errors:** they arrive as `{"error": {"code", "message", "fix"}}`. Follow the `fix`.
- **Status:** `uv run shorts status <job>` shows whether probe and analyze have run.

1. **Probe:** `uv run shorts probe "<video path>" --job <name>` (`--landscape` for 16:9).
   - Job names use lowercase letters, digits, `-` and `_`.
   - Silent clips, and landscape clips without `--landscape`, are refused. HDR, VFR, rotated and odd-sized clips are normalised automatically.
2. **Analyze:** `uv run shorts analyze <name>`.
   - It prints the sentences with ids and times, the fillers heard, loudness, face presence and warnings.
   - Read `output/temp/jobs/<name>/contact.png` (20 timecoded frames) to see the video.
   - Hindi speech is transcribed as romanized Hinglish automatically (`language: "hinglish"`); its spellings are rough,
     so fix them in the film's transcript fixes (`TRANSCRIPT` in a Reel's `reel.py`).
   - Fonts in `kit/fonts`: Montserrat 800/900, Poppins 600/700/800, Anton, Oswald 500/600/700, Inter 400–800, Bebas Neue, DM Sans 700, JetBrains Mono, Caveat.

## Where files go (2026-10-07: the user asked for zero clean-up between videos)

- Everything generated goes under `output/` (`kit/paths.py`, `shorts/config.py`). Nothing generated is written into `films/`, `kit/` or the repo root.
  - `output/final/<video>/`: what the user uploads (video, reel, `captions.srt`, posting notes, contact sheet).
  - `output/jobs/<take>/`: the footage copy (`source.mp4`), `probe.json` and `analysis.json`.
  - `output/music_usage.json`: the music history.
  - `output/temp/`: everything else, deletable any time: `jobs/<take>/` (audio, whisper, face tracks, `contact.png`, `sentmap.json`, logs), `films/<video>/` (`work/`, `hf/` = the HyperFrames project, `renders/`, `scratch/`), `cache/`.
- A film's scripts start with `F = Film(__file__)` (`kit/paths.py`) and write to `F.work`, `F.hf`, `F.renders`, `F.final`; `F.stage()` copies the film's own `assets/` and `hyperframes.json` into `F.hf`. Run HyperFrames on that folder: `npx hyperframes lint|snapshot|render <F.hf> ...`. Run film scripts with `uv run python`.
- `films/<video>/` holds only the recipe: for a new film `film.py`, `src/template.html`, `visual_plan.json`, `reels/<r>/template.html` and source screenshots in `assets/` (kit/film writes `edl.json`/`cuts.json` to the work folder); films made before 2026-10-20 have their own `edl.py`, `build.py`, `edl.json`/`cuts.json`. One-off fix or experiment scripts go in `F.scratch`, never in `films/`. Private raw screenshots go in `F.work`; only blurred copies go in `assets/`.
- `uv run shorts clean` empties `output/temp` (`--dry-run` lists it, a take or film name limits it). Never delete `output/final` or `output/jobs` without the user asking.

## Rules

- Never print, echo or commit `.env` (it may hold API keys).
- **Handles:** every end card, closing card, clip card and posting note takes the channel's handles from `kit/brand.json` (`HF.HANDLES` in a composition after `vendor.inline`, `end_card` in Python). Never type a handle into a template or notes by hand. YouTube and Instagram both go on every end card. The X handle in that file is for X posts only.
- **Captions:** they show only the speaker's words (with overrides).
- **Graphics text is on-screen copy.**
  - Keep it human and specific, not generic filler.
  - Never invent numbers or results the speaker didn't say (views, money, time saved).
  - No real brand names or logos in mockups unless the speaker names them; use generic app names.
  - Mockups use generic app names, no real logos.
- **Speed matters:**
  - `analyze` ≈ 10 s for a one-minute take; `output/jobs/<name>/timings.json` shows where time went;
  - don't re-run steps whose inputs did not change.
