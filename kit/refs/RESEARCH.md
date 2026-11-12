# Reference study: what we take, how it is built here (2026-10-10)

The owner's research brief (16 references, a vidIQ walkthrough of each, saved outside the repo at
`<research folder>/reference-library.json`) plus our
own look at the scenes. Read this before planning a film's visuals; the rules it produced live in
`kit/refs/EDITING.md` §6, §7 and §11, so they are not repeated here.

## How the scenes were inspected (and what that can't tell)

- **Seen:** YouTube pages in the built-in browser; the video element paused and stepped to chosen times, frames drawn
  into a contact sheet (1080p stream where offered). That gives composition, layout, text size and the order of events.
- **Not heard:** no audio was listened to in this pass. Music, SFX and mix notes below come from the saved vidIQ
  analysis and are marked *reported*. Sound decisions in our work were checked by measurement (loudness, cue density),
  not by ear.
- **Not seen:** the owner's Instagram reel is behind Instagram's login; its notes are *reported* only.
  MOTION.md §1 has a measured reference of the same "Opus 5.5" family that the box grammar already follows.
- Frames are seconds apart, so motion timing is inferred, not measured, except where `kit/refs/motion_ref.py` was run.
- Software, lenses and lights can't be identified from a finished edit; nothing here claims to.

## Mechanisms

Each: what the viewer gets → how it is built → what it needs → what we do with it. *Observed* = seen in the frames;
*reported* = from the saved analysis only.

### 1. Ali Abdaal, "How I use AI to save 10+ hours per week" (long) [Qc6pdR8BhFA](https://www.youtube.com/watch?v=Qc6pdR8BhFA)
Inspected 1:23–1:38, 1:41–3:50, 5:07–6:10, 12:23–13:42.
- *Observed:* the workflow chart is built node by node on a plain canvas (VoicePal → ChatGPT / Claude → Notion), each
  node arriving as it is named, dashed arrows in causal order. Then the real phone screen stands beside him at full
  frame height, its text readable. On desktop sections the screen recording is cropped in to one column (text
  roughly 2x), the presenter is a small rounded window, and the line being discussed is selected/highlighted.
- *Needs:* clean screen recordings, the real output.
- **Ours:** `S.focus` (zoom to the card or line, highlight it, dim the rest); EDITING §11 "readable on a phone";
  the diagram components already reveal in order (`diagram.js`). Status: **built** (focus), rule in place.

### 2. Mrwhosetheboss, "Which AI is smartest?" (Short) [1xI_lsZ4sxI](https://www.youtube.com/shorts/1xI_lsZ4sxI)
Inspected 0:00–0:13, 0:40–0:55.
- *Observed:* the premise is an action (pouring sweets into a jar) with the question as the first caption; a frozen
  photo of the jar in a rounded card is "the input"; each AI's answer is the real phone screen with the model's badge
  and the number large; a compact scoreboard of all guesses stays docked at the bottom while he counts, so every new
  result is read against the earlier ones.
- *Needs:* a real test and real results.
- **Ours:** `S.scoreboard` (rows stay, values land on their word, winner marked). Values only from what he said or
  showed. Status: **built**. Fits: model/cost comparisons (Haiku vs Opus), "which tool" tests.

### 3. Cleo Abram, "What Quantum Computers REALLY Do" (Short) [_utuiCPnurg](https://www.youtube.com/shorts/_utuiCPnurg)
Inspected 0:16–0:23, 0:34–0:51.
- *Observed:* one illustrated world (an island) persists; a menu card offers a car, the car is struck through, a boat is
  chosen with a pointer, and the boat leaves the card and sails in the same world. The object chosen in the UI becomes
  the actor. She returns to camera for the takeaway. Captions are small, one line, low in the frame.
- *Needs:* custom 3D in the original; the mechanism (one metaphor that develops, object continuity) works in 2D.
- **Ours:** the box grammar's hand-offs (pill → card, flip) are object continuity for the speaker; for the metaphor,
  plan one recurring scene per film that returns and develops (SCENES.md §3). Status: **guidance**;
  a reusable "world that develops" component is in the backlog.

### 4. Varun Mayya, "How to Master AI Agents in 2025" (long) [ToTyofKeE7s](https://www.youtube.com/watch?v=ToTyofKeE7s)
Inspected 1:10–2:25, 8:05–8:25, 12:45–13:05.
- *Observed:* real screen recordings with a small presenter window at the right edge; the camera between screen
  passages; friction left in (a terminal deprecation warning on screen with its caption).
- **Ours:** keep failures and retries that teach (EDITING §11 "friction" purpose); needs screen recordings
  (FILMING.md). Status: **guidance**.

### 5. HillierSmith, "The Editing That Makes Your Story 10x Deeper" (long) [mPhhBgTIG2Y](https://www.youtube.com/watch?v=mPhhBgTIG2Y)
Inspected 2:04–3:00, 8:38–8:53, 11:36–11:53 (frames only).
- *Observed:* playback of the attempt with a running timer overlay (stakes), intercut with the people watching it; his
  V2 timeline literally labels an inserted "Awkward Beat", a held reaction. *Reported:* the same footage under different
  music changes the tone.
- **Ours:** `S.quiet` lets a reaction or failure land without the bed; "reaction" is a beat purpose; a held reaction is
  a declared hold, not dead air. Status: **built** (quiet, holds); conversation grammar in the backlog.

### 6. Daniel Schiffer, "B ROLL 101" (long) [3mZuJAWH1Ow](https://www.youtube.com/watch?v=3mZuJAWH1Ow)
Inspected 4:16–4:45, 6:05–7:10, 9:18–10:05.
- *Observed:* the transitions are filmed: matched camera moves, hands and objects passing the lens as wipes, real
  product inserts. *Reported:* sound effects give the moves weight.
- **Ours:** mostly a capture lesson (FILMING.md: a few matched-move inserts per build video). Our digital equivalent is
  MOTION.md rule 4 (an element leaves in the direction the next one enters). Status: **filming guidance**.

### 7. The owner's reel (*reported only*, login-gated)
- *Reported:* serif type behind the cut-out speaker with small UI tags pinned to him; a wall of takes → a scrolling
  filmstrip behind the cut-out; the speaker moves to a corner and hands the frame to a node diagram; then a full-frame
  schematic. Music continuous, small ticks on card reveals.
- **Ours:** the box grammar (MOTION.md) and `HF.scribble` / cut-outs already cover "speaker and graphics in one space";
  text behind the speaker needs the person matte per frame (available from `kit/look`, used by the scribble).
  Status: **existing**; "type behind the speaker" as a studio helper is in the backlog.

### Summary-supported only (not inspected in this pass)
Marques Brownlee (rU9aqBv0YdY): restraint, tactile detail, matched side-by-side. Cleo Abram long (MWHN6ojlVXI): concept
animation beside an interview, document highlights, real vs illustrative kept distinct. Mohak Mangal (DV9pVzqQPR0):
roadmap reveals, a large divided cost breakdown. Dhruv Rathee (vJefOB8kec8): sequential chart with one emphasised
result, before/after with focused callouts. TechBurner (YvsnO6pWxeA): laptop insert → real screen. Benny Productions
(0wxLZbnHgAY): a cinematic reveal for the finished work. fern (-Gnrp_caPvo): labelled comparison grids, an isolated
discrepancy. Fireship (PeMlggyqz0Y): code beside a concept, input → process → output. Colin and Samir (jz_qFyTrS8w):
wide → speaker → rig → monitor for visits. Their lessons are folded into EDITING §11's "choose by what the moment needs".

## Our published work, against the references (frames inspected 2026-10-10)

- **Why I don't touch code until the PR is ready** (long):
  strong opening and box motion; but the evidence is small: the 0:52 Slack card fills about a third of the frame with
  ~18–25 px text (unreadable on a phone), 1:35's meeting tiles are near-empty placeholders, cards float in a large
  pastel field. No real screen recordings (none were captured that night). Graphics moved constantly partly to keep
  qa.py's freeze check quiet.
- **Haiku vs Opus** (Short): a clear hook ("$0.90 edit vs $16
  edit" in the title), but the two costs are never kept side by side on screen; 0:30–0:49 has a mostly empty top panel
  with small labels.
- **Channel audit** (Short): the "#1 #2 #3" idea cards show
  grey placeholder lines; the unlock shows field labels, not the actual ideas, so the promised payoff isn't seen.
- Sound: not judged by ear here. Measured: the shared mixer allowed ~20 small cues a minute (EDITING says 6–12).

## What was built (and where it is wired)

| Change | Files | Reached by |
|---|---|---|
| Phone-readable text + reading-time checks, 16:9 and 9:16 | `kit/qa/precheck.mjs` | pastel_box workflow step 4; `kit.reel render` (new precheck step) |
| Readable stills are holds, not freezes | `kit/qa/qa.py --holds`, `precheck --holds-out`, `cues.mjs` sidecars | both workflows' QA lines |
| Calmer layer motion (reference numbers) + `read` layers | `kit/hf/studio.js`, `kit/hf/reel.js` | every `S.layer()` |
| Focus zoom with line highlight and pointer | `kit/hf/evidence.js` (`S.focus`) | HF.studio / HF.reel |
| Running scoreboard | `kit/hf/evidence.js` (`S.scoreboard`) | HF.studio / HF.reel |
| Quiet moments; SFX budget 6–12/min with `keep` | `kit/audio/mix.py`, `kit/hf/core.js` | every film/Reel mix |
| Rules | EDITING §2, §6, §7, §11; CRITIC.md; MOTION.md rule 2; SKILL.md; preset READMEs | the skill and preset docs |

## The Opus 5.5 collection (2026-10-11)

[yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) at commit 7562902: a README, 513
prompt files and a catalog. It contains no editor or renderer. Read from the owner's saved snapshot
(`<research folder>/opus-repo-snapshot/`): the
six primary prompts in full and eight more in part. The original twoclipping-402193 clip (`~/Downloads/original.mp4`,
1280x1280, 60 fps, 14.06 s) was decoded at 1 and 10 fps. Its frames are third-party and used for reference only.
Nothing was installed, no paid tool was called, and no audio was listened to.

| Reference | Inspected | We had | Decision |
|---|---|---|---|
| twoclipping-402193 (one shape through UI states) | prompt + the clip at 10 fps: the container moves first, the old content stays pinned, the new content enters after it settles, with a short blur; the tab indicator's edges move on different springs | `HF.box.morph` (one hand-off: pill to card); separate studio_ui cards | **built `S.flow`** (container/content timing, the click causes the change, pure time). Rejected: 120 BPM "every beat", loops, 60 fps with subframe blur, square format |
| verbove-268381 (real states, real data) | prompt | evidence rules | **rule**: real data in every state, no placeholders; recompose 9:16 separately. Its state list is that product's brief |
| jake11moran-414633 (one desktop camera) | prompt; saved frame spot-check | `screen.js` zoom/pan/cursor keyed separately | **built `sd.walk`** (the cursor leads, the camera follows, gentle). Opt-in. Rejected: "no audio", fake app recreations |
| howdevelop-733090 (features as actions) | prompt | `diagram.js` flow/branches | **direction only** (show branching, interrupt and resume as actions). Its product claims are rejected |
| gdgtify-929495 (type that builds space) | prompt | `say()`/`line()`, kinetic.js, `F.behind` | **keep existing, use rarely**: one strong distinction or payoff per video; phrase timing (we already time to words), a held stillness |
| stokebuilder-356793 (podcast inserts) | prompt | none | **rules only** (EDITING.md §12), not validated on real footage. Rejected: the 35–50 graphics quota, "fill every quiet face" |
| twoclipping-000267 (montage) | prompt | sounds placed by file start | **fixed sound timing** (mix.py aligns attack/peak). Rejected: tmix subframe blur (4–6x render cost, no defect shown in our renders) |
| daniel-haida, brainextends, parkerrex, astrothewizard, annacher, techhalla, arthurkatcher | prompts (arthurkatcher's is only a post) | scoreboard, chrome, restraint rules | lessons only: inspect the real product first, one persistent anchor, few strong moments, check the encoded result. Rejected: brand bumpers, "a sound on every move", hosted voices, the Remotion stack, a ban on screen recordings |
| Skillry helpers (title takeover, action checklist, velocity sting) | not installed | behind-type, checklist, focus | **rejected for now**: the gap is direction, not a component |

**What the fixtures showed** (`output/temp/demos/evidence/`, made by `kit/hf/demos/evidence/build.py`; test pages, not
edits):
- `flow_compare.mp4` (left: three cards, right: `S.flow`; the same states and times; the words are our own precheck
  output). At 3.1 s and 5.3 s the separate cards put the new text over the fading old text. `S.flow` changes shape with
  no overlap. Frames are pixel-identical when seeked in any order (2.95, 3.2, 5.35 and 7.0 s, max diff 0).
- `walk_compare.mp4` (left: zoom and cursor keyed together, right: `sd.walk`). At 2.4 s the left one zooms while the
  pointer is still travelling. The right one has the pointer clicked by 2.05 s on a still frame, then eases in; both
  settle on the same framing by ~4 s. This is only a plausible improvement until it is tried on a real recording.
- Sound timing, measured on the mixer's output (not by ear): the chapter whoosh's peak was +1082 ms late and is now
  −25 ms; the bass hit +64 ms → +4 ms; the check +103 ms → +3 ms; the pop +15 ms → 0 ms.

## The paper-collage reel (2026-10-11)

[instagram.com/p/Dcblnu1gyAP](https://www.instagram.com/p/Dcblnu1gyAP/) (fliki), 27 s, 720x1280. It was inspected in the
browser through the post's public embed, as frames at ~40 times; Instagram's video can't be copied to a canvas, so the
frames were shown as a wall of paused players. Nothing was downloaded and nothing was heard.
- **0–6 s:** a paper collage above the caption band, with the presenter below.
- **6–19 s:** the product's screen recording.
- **20–27 s:** the face full screen.

Built from it: `kit/hf/paper.js`, `kit/look/objects.py` + `kit/bin/fgcut` (Vision cut-outs), `kit/presets/paper_collage/`
and the skill `paper-collage`. What can't be made here: the photoreal images themselves (no local image model). They
come from his photos or his ChatGPT, and the README has the prompt style.

## Backlog (ordered)

1. **Validate on real footage**: the owner chose (2026-10-10) to judge the changes on his next real video instead of
   A/B previews of old ones. After it, record what he says here and tune focus `fill`, the reading-time constant and
   the SFX budget from his notes.
2. **Screen recordings in the next video** (FILMING.md): the biggest gap against Ali Abdaal / Varun Mayya is real UI,
   which no editing can make up.
3. **Type behind the speaker** (`S.behind`): serif type on a layer under the matte-cut speaker, for hooks.
4. **A metaphor world that develops** (Cleo Abram): a 2D scene component whose objects persist across beats.
5. **Conversation / podcast grammar**: J/L cuts, reaction holds, speaker-level matching, multi-camera sync check; needs
   real two-person footage before it is built.
6. **Grade comparisons**: a labelled original / corrected / finished triptych per room from `kit/look` (same frame,
   same viewing transform) so grade choices are shown, not asserted.
7. **Listening pass**: a by-ear review of the mixes at matched loudness (voice-only vs finished) on the next film.
8. **Text inside screenshots**: precheck reads the page structure, not pixels, so text inside an image (a screen
   recording, a screenshot) is never checked for size. Add the source text height to `HF.screen` (or OCR it with
   `kit/hf/tools/locate.py`) and check the zoomed size.
10. **The paper-collage look on a real Reel** (first use: check the pace, readability and the objects' realism; a world map
   needs a public-domain outline, downloaded with his OK).
9. **Judge `sd.walk` and `S.flow` on real footage** (the next video with a screen recording / an agent run), then decide
   whether either becomes the default.

## Viral Shorts in the "AI agent applies to jobs" niche (inspected 2026-10-10, for films/agent-reel)

YouTube search "ai agent applies to jobs for you" (Shorts filter), top results by views: Varun Mayya "This AI Agent Got
Him 12 Interviews Without Writing a Single Resume" (430k, [8YuGkHTWf3Q](https://www.youtube.com/shorts/8YuGkHTWf3Q)),
"This reddit user applied to 1000 jobs in 24 hours using AI" (257k, [F57l22yz4NE](https://www.youtube.com/shorts/F57l22yz4NE)),
an n8n agent build (211k), "I Built an AI Agent That Applies to Jobs FOR YOU" (126k). Frames sampled in the built-in
browser (video stepped, drawn to a sheet); audio not judged.
- *Observed (8YuGkHTWf3Q, 71 s):* frame 0 is the REAL thing (the agent running in a terminal) with a 3-word serif title
  ("Claude got him hired"); most of the runtime is real screen recordings (the agent's terminal, the job listings it
  found, a resume diff, LinkedIn changes); while he talks the frame is a plain split (screen top, him below) or his
  face; near the end it cuts to footage of the person who got hired at his desk. Captions: one word, small dark pill,
  low centre. No designed "world", no mock cards.
- *Observed (F57l22yz4NE, 55 s):* frame 0 is a split (a real laptop with the Reddit post on top, him below); a new shot
  every ~1.5-3 s, cutting between real screenshots, cinematic b-roll cutaways (movie/office clips for "and the fun
  part?"), famous faces, news-style clips; one-word centred captions; almost no designed graphics.
- **What wins here:** proof you can see (the real agent screen, the real result, the real person), a number in the
  title and on frame 0, and pace from cutting between real things rather than animating cards. Practitioner guides
  (teleprompter.com, blitzreels.com, sociolyzer.com) agree on a visual change every 1-3 s, captions that work muted, a
  result shown in the first second, loop-friendly endings; their numbers are vendor claims, not measurements.
- **For our takes:** ask for 10-30 s of screen recording of the tool doing the thing and a screenshot of the result
  (blurred) before editing; without them, footage-native devices (tracked labels on people in the shot, type behind
  the speaker, a live log of what the agent does) beat a pastel card world.
