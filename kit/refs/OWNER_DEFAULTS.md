# The owner's standing defaults (read first, every edit)

"The owner" is you: the person whose videos are edited here. This file holds the taste every edit follows without
being told again. It ships with the defaults this kit's author settled on over many edits. They are a starting point:
change a line here and every later edit follows it. The skills, the agents and the kit's READMEs cite this file by
section number, so keep the numbering when you edit it.

The rules apply to every film and Reel, with or without a preset. A preset README or the owner's brief can be
stricter; it is never a reason to come out plain. When a brief says "not so much text", cut words, not ambition.

Sources: kit/refs/AUDIT_2026-10-20.md (why edits used only a few of the kit's components), EDITING.md,
kit/refs/SCENES.md §9-10, DIAGRAMS.md and the preset READMEs. If one of these changes, change it here first.

## 0. Never lower the picture quality

Check all four before the first render:
- **Frame rate:** the source's own rate. A 60 fps take is cut, graded and rendered at 60, never converted to 30.
- **Resolution:** long-form renders at 4K (chunked) when the take is 4K. Reels render at 1080x1920 for Instagram, plus
  2160x3840 for YouTube Shorts.
- **Zoom:** at most x1.3 over the full frame. On a wide or night shot, move the camera within that cap instead of
  cropping tight, because cropping magnifies the phone's own smoothing.
- **HDR (HLG) to SDR:** the tested tone map, not a flat default. Keep high-quality intermediates and final encodes too.

## 1. The edit

- **Hook.** Long-form: a hook of 6-10 s (at most ~12 s) that makes them watch to the end, with the stakes on frame 1.
  Reels: frame 1 is a finished composition with the stakes, there is movement by 0.5 s and an open loop by 3 s
  (EDITING.md §4). Write 3 candidate openings and pick by score. The hook opens on the speaker's face (its first 3 s).
- **Fast.** Trim pauses and fillers hard and keep the momentum. Reels: a visible change every 1.5-3 s. Long-form:
  nothing new for 6 s is a warning and 10 s is a fail (precheck's "still").
- **The camera on the speaker: visible, but smooth.** While they are on screen the framing changes every 4-8 s, one
  move per thought: a push of +6-12 % across it, a pull-out, a slight arc (truck ≤ 3 %, roll ≤ 0.6°). A stressed word
  gets an eased punch of ×1.12-1.18 (at most one every 12 s), every join an eased reframe, every whip a settle. No
  handheld shake, and never past the footage's zoom budget (`max_zoom` in work/tracks.json). The lens does all of this
  by itself on every kit/film page (kit/hf/README "The lens"; film.py `LENS` and `STRESS`, the plan's `cam`), in the
  card, the circle, the seated frame or a box: don't write punch-in loops by hand.
- **Transitions that vary and mean something.** One at each chapter and on the way into and out of each takeover: a
  cut keeps the thought going, a whip moves to the next station, a zoom dives into the detail, a match carries a shape
  into the next scene, a card turns the speaker's card into the graphic (SCENES.md §10; `C.takeover` in / out,
  `HF.trans`). Never the same kind twice in a row (cuts may repeat), whips at most 40 %. The kit's own code, no shader
  transitions.
- **Animations that explain.** Wherever the speaker contrasts, counts, explains a process or shows proof, a component
  shows it (kit/refs/SCENES.md §2: type → technique). Text is not the problem; plain is.
- **One idea per frame.** At most 3 visual groups up at once beside the speaker: the hero and one or two supporting
  chips or lines (precheck's density gate; the speaker's shape, captions and chrome don't count). A second idea gets
  its own station or takeover. This outranks the variety minimum below: a fix never adds an element to a frame that
  already holds 3.
- **Use the whole kit.** Plan from the components in `kit/hf/registry.json`, not from the last film's template. That
  includes HyperFrames catalog pieces (a cursor auto-zooming a screenshot, a selected line), icon morphs and draw-ons,
  animated emoji, living shader backgrounds (never on the white page), depth parallax on photos, the music map, the
  takeovers, transitions and flat diagrams (kit/hf/README; video-shorts skill "Version 10 tools").
  Look at the ones no film has used first: `python3 kit/hf/tools/registry.py --unused`. The minimum number of distinct
  visual components is 4 for a Reel, and 1.2 a minute for long-form (6-10). Add 2-4 stickman moments and 2-3 hand-made
  styles (sketch, annotate, scribble, collage), one per passage. The look is no excuse: the UI cards, evidence,
  code, diagram, compare, sketch, annotate and the stickman follow whatever look the film is in (kit/hf/README "Looks";
  each registry entry lists its looks).
- **Take the speaker off screen where a scene shows a thing.** A takeover gives the whole frame to one scene (a
  statement, a flat diagram, the evidence, a list) while the voice carries on; the speaker is absent, never cut out. On
  long-form, 15-30 % of the runtime is takeovers of 4-12 s each, with at least 3 s of face between two; the speaker is
  never away for more than 12 s, and the hook opens on their face. A Reel keeps the hook and the 12 s rule. Which
  passages: SCENES.md §9 (process, mechanism, relationship, chronology, quantity, proof). A takeover diagram follows
  kit/refs/DIAGRAMS.md's flat rules: at most 5 boxes on 16:9 (4 on 9:16) with 1-2 word names, 6 edges, one focal box,
  labels of 14 characters or fewer.
- **Vary where the speaker sits.** They move between seated full frame, the seated frame card, a card or circle beside
  the graphic, a corner, a punch and a takeover. No single layout covers more than 35 % of the runtime (a card beside
  the graphic is one layout, left or right), none runs three beats in a row, and seated full frame stays at or under
  about 30 %.
- **Default look.** For a talking-head edit with no preset named, use `preset_whitespace`: `HF.canvas`, `HF.studio` or
  `HF.reel` with `{ look: "whitespace" }` (kit/presets/whitespace/README.md, skill canvas-studio). Show a sample before
  a whole film until the owner has approved the look once. On request: `preset_canvas_studio` (warm), `preset_pastel_box`
  and `preset_paper_studio` (the calm one) (kit/presets/README.md).

## 2. The speaker on screen

- **Never cut out.** The speaker appears full frame or in a closed shape: a card, a circle, a square or a corner.
  When a scene needs the whole frame, they leave it (a takeover, §1).
- **The room stays as shot.** Grade only: no blur, dimming, vignette or background replacement, and no whitening of the
  wall to match a white page. The only blur on the speaker is motion blur from a fast camera move (a whip, a
  zoom-through). "bg" in a brief means background music; ask before touching the picture's background.
- **Text room on a close selfie:** zoom in from the top edge (zoom ≥ 1). Don't shrink or frame the video.
- **Captions never sit on the mouth.** Move them to the top band while the face fills the frame.

## 3. Words

- **Whole sentences only.** Never crop a sentence or splice half of one onto another (cutcheck). Re-listen to every
  join: `uv run python -m kit.cut.relisten <edl.json> <vo.wav>`. Word times drift by up to 1 s on Hinglish.
- **Captions say what was said.** Respell Hinglish properly and keep the speaker's words.
- **No invented numbers.** Illustrative shapes (bars, meters) carry no figures, or are labelled as illustrations.

## 4. Sound

- **Long-form (16:9 films): a calm bed about 18 dB under the voice** while the speaker talks. Pick a bed that sets the
  video's mood and stays out of the way: lo-fi, chill, soft piano or ambient (kit/music chill/, the soft emotional/ and
  cinematic/ tracks), a steady energy (library.json dynamic_db under ~12), no vocals, no EDM, rock or heavy synth beds,
  no drops or risers. One or two beds for a whole film, not one per chapter. Story turns are gentle: the bed steps
  back or stops for a line, it never hits a drop. The beds that pass this test carry `"longform": true` in
  kit/music/library.json. The test: dynamic_db 12 or less, no build-up intro, not beat- or bass-driven (pulse clarity
  0.65 or less and under 60 % of the energy below 150 Hz).
- **The bed follows the voice (the v11 sound, kit/film/mix.py).** It ducks on the voice: it sits still under the talk
  and lifts only in pauses of 0.8 s or more (0.4 s on a Reel), so it never pumps. One calm track loops on its own
  phrases to fill the film (the mix prints each seam's time: listen to every one). A bed change crosses on the outgoing
  bed's downbeat (1.5 s on a film). The whooshes and pops rotate 2-3 matched files a family, within a budget: at most
  8 small cues a minute on a film, 12 on a Reel, no file over 25 % of the cues. `SOUND = "v10" | "v11"` in film.py
  wins.
- **Reels: music about 12 dB under the voice** (a drop on the reveal is fine there). Music is lifted in gaps and ducked
  18-20 dB under clips with their own audio. Master to −14 LUFS, true peak −1.5 dBTP (EDITING.md §7).
- **Music changes with the story:** on Reels a drop on the reveal, a stop on the punchline, a riser before the payoff;
  on long-form only the gentle turns above. A sound goes on landings that mean something, not on every card. The music
  map does the measuring (kit/music/beats.json): plan the moments in visual_plan.json (`"music"`), land drops with
  `drop="auto", at="w<id>"`, and every bed starts on a downbeat (kit/film/README "mix").

## 5. Reels

- **Each Reel is a complete story on its own**, postable with no context. It is not a teaser.
- **No end screen** on a Reel, unless a long video goes out with it. The last frame flows back into frame 1.
- **When a long video and Reels are asked for together,** the Reels start only after the long video is fully rendered.
- **The 15 s sample gate:** send a sample and wait for the owner's yes. Skip it only when they have said to.

## 6. Mock-ups, sources and people

- **Mock-ups are generic:** no real logos or brand marks in mock UIs. A real post or screen is shown as itself and
  credited in the caption.
- **Private details are blurred:** figures, emails and other people's data.
- **A guest on camera needs their consent.** Confirm it with the owner before posting.

## 7. How to work with the owner

- **References.** A reference shared with a take, or with "edit it like this", leads the craft: match its pace, cuts,
  zooms, motion graphics, type and sound to its measured numbers (`kit/refs/breakdown.py`, the `reference-analyst`
  agent, then `kit/refs/compare.py` on the draft; skill fable-director "Matching a reference"). §0, §2 and §3 still
  hold: where the reference breaks one of them, ask once, with the frame. When a reference is shared for one named
  idea only (a placement, a background), take that idea and keep the kit's animation system.
- **Old videos are not re-edited** unless the owner asks.
- **Finish end to end** and list what is still open, rather than stopping to ask small questions.
- **One heavy render at a time** on one Mac.

## 8. The gate (every edit, before the template is written)

1. **Read** this file, then the preset README (or `kit/presets/README.md` to choose one).
2. **Plan scenes from meaning:** kit/refs/SCENES.md → `visual_plan.json`, schema 2 (`"schema": 2`): one passage per
   idea with its type and technique, plus `face` (on | off | corner | full | frame), `cam` (push | pull | punch | arc |
   drift | hold), `groups`, `bg` and `transition`. Then check it with `python3 kit/hf/plan_check.py visual_plan.json`.
   It must have 0 errors, and every warning is either fixed or answered in the brief. It flags:
   - a technique that doesn't fit its passage or the look;
   - too few distinct techniques;
   - one layout over 35 % (left and right merged);
   - too many words-only passages;
   - on schema 2, the §1 budgets: away over 12 s and (on long-form) a hook off the face are errors; takeovers outside
     4-12 s or 15-30 %, under 3 s of face between two, seated full frame over 30 %, a held frame on the speaker over
     8 s, punches under 12 s apart, the same transition twice in a row, whips over 40 % and more than 3 groups are
     warnings.

   kit/film runs it first, before every draft and render: an error stops the build (`--force` goes on).
3. **Build from the plan.** Then run `node kit/qa/precheck.mjs <hf>/index.html` and get 0 HIGH. Its ambition, speaker
   and density sections (component count, layout share, the longest still stretch, lingering parts, the framing, time
   away, the zoom budget, groups on screen) are gated like the defects. Read its last line: it repeats the verdict
   with every HIGH by kind and time ("precheck FAIL: 3 HIGH [framing 06:07.6 07:12.0, density 01:10.6], 9 MEDIUM").
   Time in a corner is not judged for framing (too small for the lens to move on). `AMBITION` in film.py switches the
   ambition gate (`--no-ambition` / `--ambition` force it).
4. **The grade as an A/B.** Offer the "clean" grade (bright, neutral whites, protected skin: the white page's) beside
   the film's look: `uv run python -m kit.film films/<name> grade --sheet=8,30,120` grades the same frames both ways,
   drawn on white with the scopes under each. The owner chooses; the chosen look goes in `GRADE` (screen recordings
   pass through ungraded: their view kind is `None` in GRADE's `kinds`). The room is never whitened or masked to match.
5. **Draft render, qa.py and the fresh critic** (kit/qa/CRITIC.md; for a Reel its brief also carries the hook and
   pacing rules of EDITING.md §3-4 and the layout shares of §1 above). Then the one 4K render
   (`uv run python kit/hf/render4k.py films/<video>` for anything over ~2 min).

**A new film runs on `kit/film` (kit/film/README.md):** no copied `edl.py` / `build.py` / `audio.py`, and no preset's
`templates/build.py` either (they write no lens, no tracks.json budget and the older sound). The film is
`films/<name>/film.py` (sources, KEEP, judged joins, fixes, spellings, music, Reels), `visual_plan.json` and
`src/template.html`, and the gate above is its commands: `uv run python -m kit.film films/<name> prep` (words, the
cleaned voice, its EQ), `cut --plan`, `cut --voice`, `joins` (whisper on every join), `cut`, `grade --sheet` then
`grade` (look v2, the room as shot), `build`, `draft` (plan_check, lint, cues, precheck, mix, 1080p, qa.py),
`render` (4K in chunks), `reels`. The worked example is `kit/film/example`: the whole pipeline on a generated take, so
it runs with no footage. For the whitespace look start from `kit/presets/whitespace/templates/template.html`. A Reel
from its own single take stays on `kit/reel`.
