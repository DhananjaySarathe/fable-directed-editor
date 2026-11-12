# Editing playbook: how an edit gets made here

Rules distilled on 2026-10-01 from about 30 repos in the awesome-claude-video-skills list (editing, Shorts, motion,
QA), on top of the 11-channel study in `REFERENCE.md`. Everything is rewritten in our own words; no code or text was
copied. OpenMontage is AGPL and video-editor-agent has no licence, so take ideas only. Where a source's numbers
clash with a measured preference of the owner, the owner wins (music ~12 dB under the voice on Reels; on long-form a calm bed ~18 dB under, OWNER_DEFAULTS §4).

## 1. Workflow and gates (⏸ = show the user before going on)

| # | Stage | Output | Gate |
|---|---|---|---|
| 0 | Ingest | probe + whisper words + contact sheet per clip | every file probed and looked at; never infer content from a file name |
| 1 | Glossary pass | caption/term fixes | fix every product/model name first (whisper hears "Grok" as "Clock"); ASR words under 0.7 confidence get a second look |
| 2 | Reference (if the user names a style) | style notes: cuts/min per section, shot sizes, caption spec, palette, audio levels | every metric filled or marked n/a |
| 3 | Brief + beat sheet ⏸ | promise, audience, target length, hook, beats mapped to word ids; for a Reel, the hook plan (3 scored candidates, the pick and why, §4) | every beat maps to real words; the hook sits in 0–3 s (Shorts) or the first 20 s (long-form) and passes §4's musts |
| 4 | Scene plan | per beat: its purpose (premise, proof, action, comparison, explanation, friction, reaction, cost, limitation, payoff), then the evidence, layout, shot size, graphic, sfx, music (§11) | slideshow risk (below) under 3; no layout on more than 60 % of beats; text-only cards on at most 40 % |
| 5 | Sample ⏸ (new format or new style only) | 10–15 s: the hook + one typical beat, with real audio | same QA as the final |
| 6 | Build + render | HyperFrames composition (cut-out from `kit/look/cutout.py`) | `kit.cut.cutcheck` on the edit list exits 0/2 (every REVIEW judged) before building; `npx hyperframes lint` clean, snapshots looked at |
| 7 | QA | `node kit/qa/precheck.mjs index.html --holds-out=holds.json` on the page, then `python3 kit/qa/qa.py final.mp4 --cuts=... --expect-duration=... --holds=holds.json,cues.holds.json`, `kit.cut.cutcheck --media=final.mp4`, `kit/look/scopes.py qa` | exit 0 (PASS) or 2 (WARN, listed for the user); never deliver an exit 3 |
| 8 | Fresh critic | `kit/qa/CRITIC.md` | every critic finding FIXED or listed |
| 9 | Fix loop | whitelist fixes only (§8) | at most 3 fix-and-render rounds, then ship with the open items listed |
| 10 | Deliver ⏸ | video + captions.srt + notes + the open-item list | — |

## 2. Cutting talking heads

- **Where an edge goes is measured, not padded (2026-10-10).** `kit/cut/edges.py` (and `kit.reel joins`) put each edge
  on the voice envelope: the in-point before the breath that starts the word, the out-point after the word's last
  sound has decayed, and a join that has no real quiet stays continuous. That supersedes the fixed paddings below,
  which are kept only as a sanity range for a reviewer. Never insert silence inside a breath.
- **Cut from word boundaries, not raw whisper times.** Whisper's word end times run 0.1–0.4 s late.
  - Confirm each edge with a 50 ms RMS envelope of the cleaned voice.
  - Snap cuts to the frame grid so a cut only ever shrinks: the cut start rounds up, the cut end rounds down.
  - Keep the cut end at least one frame before the next speech onset.
- **Padding by the word's last sound:**
  - vowel: +30 ms;
  - other consonant: +50 ms;
  - sibilant (s, sh, z): +120 ms;
  - before every word: 30–50 ms.
- **Pauses:**
  - Don't cut every pause to zero. Keep 0.10–0.15 s of each (Shorts: about 15 % of pause time kept, median kept gap about 0.3 s; long-form a little looser).
  - Count breathy lulls at −28 to −36 dB as pauses too; silencedetect misses them.
- **Never cut inside a phrase:**
  - not between a preposition and its noun;
  - not between a number and its unit.

  A pause under 0.3 s usually means the thought isn't finished.
- **Retakes and fillers:**
  - keep the later, complete take;
  - keep one-breath runs whole rather than stitching best words together;
  - one filler can stay; cut runs of 2 or more;
  - when a wrong name or number is corrected, cut the wrong one.
- **Splice hygiene:**
  - put a 25–30 ms fade on both sides of every audio splice, using the smooth `hsin` curve, not linear;
  - cut from the original source once, never from an already-cut file;
  - remap the transcript through the edit list instead of re-transcribing the cut, which invents words at jump cuts;
  - keep a keyframe every second on intermediates.
- **Hide a jump cut** with the next framing (from version 7 the camera director reframes 1.00 ↔ 1.15 only at a new thought and holds it; cuts inside a thought keep the framing) or a punch. A lighting change can't be hidden; use a graphic over it instead.
- **Whole thoughts only (version 7, the owner's rule).** Trim pauses, fillers, retakes and tangents freely, but every kept piece starts at a sentence start and ends at a completed thought.
  - Never splice the first half of one sentence onto the second half of another.
  - On a restart, cut back to the end of the previous complete sentence.
  - `kit/cut` enforces this (§9).

## 3. Pacing

- **Shorts:**
  - a visual change every 2–4 s, spaced unevenly on purpose;
  - talk beats 2–4 s, stat beats 1.5–2.5 s, screen reads at least 3 s, a payoff holds at least 1 s;
  - 50–70 s total works well.
- **Long-form:** one idea per beat, beats of 5–6 s, a visual change every 3–5 s, never a static frame over 8 s. Re-engage around the 3-minute mark (see REFERENCE.md).
- **Perceived pace** is about twice the hard-cut rate, because caption pops and punch-ins count. Three identical shots in a row read as a slideshow.
- **Pivot lines** ("but", "so here's the thing") start the next shot. Give a pivot 2.5–3.5 s of clean frame.

## 4. Hooks (Shorts and Reels)

The owner's rule (2026-10-05): every Reel needs an awesome hook, designed for that Reel during planning. There is no fixed hook template. The research below (2024–2026) is the standard each hook must meet.

- **How platforms judge the first 3 s:**
  - Instagram ranks Reels on skip rate, the share of viewers who leave within 3 s.
  - YouTube Shorts uses "stayed to watch": 70–90 % wins, under 60 % rarely takes off.
  - About half of viewers watch muted, so the picture and the text must carry the hook on their own.
- **Hook plan: a ⏸ gate in the brief for every Reel.** Write 3 candidate openings for this Reel, score them (below), pick one, and show the user the pick and the reason. Candidates come from:
  - the transcript: whole sentences only, no "this/it" that needs earlier context;
  - what can be built in post from the footage and the receipts: screenshots, numbers, a before/after, a contrast;
  - hook pickups, when the user can record them. Before a shoot, suggest 2–3 one-breath lines said straight to camera with the number in them (result first, contrarian, one in Hinglish). The owner rarely says amounts in normal takes.

  Formats to draw ideas from, never to copy as templates:
  - receipt first (face plus the proof screens);
  - contrarian verdict;
  - "you" warning;
  - ranked ladder with prices;
  - guess-which (the answer at the end loops back to the start);
  - cut-out over the evidence;
  - experiment montage;
  - myth bust;
  - confession.
- **Every hook must have:**
  - voice and face from frame 0 (speech in the first 3 s: +11.7 % 3-s retention; a face: +10 % 10-s retention);
  - the number or proof on screen by about 3 s;
  - a spoken line of 6–14 words that makes sense cold;
  - **one** text line of 5 words or fewer (text walls cost about 6 %), stating the stakes;
  - a payoff the Reel actually delivers. Misleading hooks hit a retention cliff, and YouTube penalises clickbait.

  Combining two hook types (e.g. result + contrarian) beats one.
- **Score each candidate out of 100, then subtract penalties:**

  | Criterion | Points |
  |---|---|
  | specific number, cost or count | 15 |
  | tension word (never, waste, vs, only one, overpaying) | 15 |
  | number or key noun in the first 5 words | 15 |
  | speech starts within 150 ms of the cut with energy, no filler | 15 |
  | 6–14 words, about 4.5 s or less | 10 |
  | open loop that isn't a yes/no question | 10 |
  | face frontal, eyes open at the in-point | 10 |
  | "you" or a decision the viewer faces | 5 |
  | reduces to stakes text of 5 words or fewer | 5 |
  | **penalty:** greeting ("hey guys"), cliché ("nobody is talking about this", "wait till the end", "game-changer"), brand or logo first, rhetorical question | −10 each |

  The weights are starting points. Log what each posted Reel used and recalibrate after about 20.
- **Purpose beat after the hook** (the owner's ask: viewers must know what they'll get):
  - at most about 2.5 s, over his voice, never silent;
  - it adds something new (the proof/receipts or the map of what's compared) and never repeats the hook's question;
  - the content starts by about 5–6 s.
- **Frame 1 is already a finished composition** showing the topic literally: the face plus the claim or the proof. No logo, no title card, no music-only open.
- **Hook text:**
  - 96–130 px at 1080 wide, line height 1.05–1.1;
  - one word in the accent colour;
  - between y 270 and y 1250 (Instagram's own UI covers the top 14 % and the bottom 35 %).
- **End on the verdict line**, so the loop back into the hook reads naturally. Replays count as views on both platforms.
- **Optional test:** export 2–3 openings (only the first ~6 s differ) as Instagram Trial Reels, which go to non-followers for 72 h.
  - Read skip rate at 24 h.
  - Keep the winner if it has 1,000+ views and a skip rate at least 5 points lower.
  - Share the winner to followers.

## 5. Captions

- **Shorts:** burned in. **Long-form:** keyword pops only, with the full captions uploaded as `.srt`. This is the REFERENCE.md rule.
- **Timing:**
  - a page shows from its first word − 0.04 s until the next page's start − 0.04 s, never longer (longer gives double captions);
  - the page pops from 0.92 to 1.0 over 0.12 s.
- **Words:** 4–7 per line (2-word caps for emphasis). Use discrete on/off states (`tl.set`) so seeking is always right.
- **Safe zone at 1080×1920:**
  - key text and captions between y 270 and y 1250, at least 65 px from each side, and clear of the right-hand action rail (Instagram covers the top 14 % and the bottom 35 % with its own UI);
  - only decoration may sit lower.
- **Never over the face:**
  - from the Vision mask/face track, compute `eye_floor` = lowest eye line − 24 px and `head_floor` = top of the head − 8 px over each caption's own window;
  - wide elements (70 % of the width or more) may sit below the eye floor;
  - narrow ones must clear the head so they don't read as a hat.
- **Burn captions in last**, above every overlay.

## 6. Motion graphics (anti-slideshow)

- **One persistent world plus a camera.**
  - Graphics live in one `.world` wrapper that keeps breathing (scale 1.00 → 1.04–1.06, about 0.5 %/s, running past each shot's end).
  - Real shot-size changes take 0.7–0.9 s with `power2.inOut`.
  - A persistent subject (the speaker or the hero object) is on screen for 60 % or more of the runtime.
- **A still with nothing to read is dead air; a still the viewer is reading is a hold (2026-10-10).** No more than 1 s
  of frozen time with nothing readable per 30 s (`qa.py`). Readable text on screen, a focus on real evidence or a
  declared hold (`S.hold`, `layer(..., { read: true })`) makes a still a hold: `precheck.mjs --holds-out` +
  `qa.py --holds` accept it as long as it doesn't outlast its content. Don't add float, drift or wobble to pass the
  check; that was the old rule ("nothing still for more than 0.6 s") and it pushed the edits toward decoration.
- **Easing:**
  - entrances 0.7–1.0 s `power4.out` (per character: scale 1.45 → 1, blur 30 → 0);
  - exits 0.35–0.5 s `power2.in`;
  - entrances run about 1.6× longer than exits;
  - no more than two tweens per scene share an ease;
  - on a hand-off, exit and entry speeds match within about 5 %.
- **Stagger:**
  - a whole stagger stays under 0.5 s; per character 0.01–0.024 s; tiles 0.15 s with `back.out(1.9)`;
  - the first move starts 0.1–0.3 s into the scene;
  - a scene builds over 0–30 %, breathes over 30–70 % and resolves over 70–100 %.
- **Readability:**
  - a key element stays readable for at least 0.3 s, the motif lands inside the first 0.5 s, and 3 s of text must be readable in 2 s;
  - a CTA stays readable for at least 1.5 s; end cards hold 1.5–2 s.
- **Text:**
  - one statement per shot, 6 words or fewer, at most two text levels on screen;
  - Shorts: nothing under 30 px at 1080 wide; headlines 90 px or more, body 32 px or more, labels 24 px or more.
  - 16:9: headlines 60 px or more, body 20 px or more (floors, so go bigger for phones).
  - hero text spans 60–80 % of the width; track display type −0.03 to −0.05 em;
  - one expressive face; heavy weight contrast;
  - titles clean with a soft shadow; glow goes on objects only.
- **Composition:**
  - text never covers the face, and panels sit on the side away from the speaker;
  - keep one quadrant empty and at most 3 groups on screen;
  - background luminance under light text is 25 % or less (use a dark pocket at 0.35 opacity or less).
- **Hero moments:**
  - spend the expensive effects (shader transitions, light leaks, 3D) on 1–2 moments per video, with 4–6 layers active there;
  - elsewhere, lean frames with just the camera breath;
  - write the rhythm before coding, e.g. "fast-fast-SLOW-fast-SHADER-hold", and name the peak.
- **Transitions:**
  - hard cut for lists, comedy and anything under 0.8 s;
  - CSS carries for connected beats;
  - shaders only for 1–2 reveals (a 5–7-beat piece uses 1–2);
  - at least two transition types, one with depth; at most two wipes;
  - never the same transition on every cut, and never a zoom without a reason.
- **Data:**
  - count-up and bar share the same start and ease (0.7–1.2 s, `power3.out`), with a 0.08 s stagger between bars;
  - bars grow from the baseline;
  - one accent hue for every stat, tabular numbers with a fixed width;
  - every action visibly causes a result.
- **Speech-synced emphasis** (keyword glow):
  - attack 0.1–0.25 s from the word's start, with no lead;
  - hold to the word's end, then release over 0.2–0.5 s;
  - 1–2 words lit at a time, scale boost of 0.08 or less.
- **Music-synced text:**
  - every phrase lands on one shared `BEATS[]` grid, 1.2–1.8 s apart (under 0.8 s feels frantic, over 2.5 s drags);
  - each phrase has its own entrance;
  - hold 0.7 s after the last one.
- **UI zooms:**
  - scale 1.4–2.2 over 0.6–0.9 s, starting 0.3–0.5 s before the click;
  - never zoom in and out within 1.5 s;
  - off-centre targets: scale the outer wrapper and counter-translate the inner one.

## 7. Sound

- **Voice:** cleaned, then the whole mix is mastered to −14 LUFS with true peak −1.5 dBTP.
- **Music:** on Reels about 12 dB under the voice while speaking; on long-form a calm, steady bed about 18 dB under (the owner's rules, OWNER_DEFAULTS §4), lifted in gaps, ducked 18–20 dB under clips that carry their own audio (the blind test).
- **The v11 sound (2026-10-22, films made from that day; `SOUND = "v10"` in film.py keeps the old mix, and every
  older film still mixes sample for sample as it did). The choice is sticky: each mix records it in work/music.json
  and the next mix reuses it, so editing or copying film.py never switches a film's sound halfway through:**
  - *The bed sits still under him.* It ducks on his voice itself (the 10 ms level of vo.wav or the words), with a
    60 ms look-ahead and a 40 ms attack, holds 0.4 s after he stops and comes back over 0.8 s (Reels 0.2 / 0.3 s), and
    only lifts in pauses of 0.8 s or more (Reels 0.4 s). The lift is 6 dB (gap = under + 6: films −18 / −12, Reels
    −12 / −6). The v10 mask pumped 7 dB in every word gap (oss-editor: 37 lifts, 5.6 a minute, 75 dB/s); a tight
    long-form cut now has none. `carve=3` on a bed also dips its 1.2–5 kHz band under speech, where his voice lives.
  - *One calm bed can fill the whole film.* A track shorter than its bed loops on its own phrases (kit/audio/loop.py):
    it jumps between phrase starts that match in harmony and loudness, on the downbeat, with an 80 ms equal-power seam,
    and ends on the track's real ending. `kit/film/mix.py` prints each seam's film time: listen to each one. The
    start you type is kept when the seams can land the ending from it; otherwise the last bed starts up to 8 bars
    later (printed; `snap=False` forbids it). When no seam matches, a second calm long-form bed takes over with a 2 s
    crossfade (and loops the same way if it runs out too).
  - *Bed changes wait for the phrase* (long-form). The outgoing bed ends on its own next downbeat (at most a bar after
    the change) and the two cross over 1.5 s with an equal-power fade, instead of a 0.2 s cut-crossfade mid-bar.
    Reels keep the quick 0.2 s crossfade: their beds change on a drop.
  - *Clips quiet the music by themselves* (−19 dB under every edl piece of kind "clip"), and the plan's music moments
    are played: a "stop" takes the music out over the passage's first sentence (unless the page's `S.quiet` already
    does); on Reels a "riser" peaks on the passage and a "drop" places the bed's drop there. Long-form plans with a
    drop or a riser are flagged: long-form beds stay calm.
  - *The mix reports what it did:* the music under speech, lifts a minute (3 at most), the steepest gain slope, cues a
    minute, the most-played file's share and the loudness range; music.json carries the v11 findings for qa.py.
    Near-silent runs inside a quiet window (a planned stop over a cleaned voice's breath) are listed apart as meant,
    not as holes to fix; `ROOM_TONE` gives them air if they sound dead.
- **Effect levels:** SFX are peak-normalised, then set against the voice's 95th-percentile peak:
  - UI / pop: −14 dB;
  - whoosh: −12 dB;
  - impact: −8 dB.

  A hit 3–5 dB over the local voice level reads as punchy; a hit level with a quiet stretch is buried.
- **Effect use:**
  - a sound where something happens that matters (a result lands, a click causes the next shot, a stamp, a section
    change), not on every landing or every word; `kit/audio/mix.py` thins small UI cues to this budget (none within
    0.8 s of another cue, at most 2 in any 10 s); a cue that carries meaning is sent with `keep` (`K.sfx(n, t, db, true)`);
  - 6–12 subtle SFX per minute, rotating 2–3 variants of each. Since v11 the mix does the rotating: a sound with a
    family in `kit/sfx/library.json` ("family": pop, check, swish, camera_whoosh, tone, shutter, sparkle) plays its
    family's files in turn, each matched to the asked file's loudness with ±1.5 dB of jitter, and the budget is per
    format: 4–8 small cues a minute on calm long-form, 6–12 on Reels, no single file over 25 % of the cues or 4 times a
    minute (story sounds and `keep` cues always play). oss-editor's 49 identical bubble pops become 11 + 11 over two
    pop files, 6.6 cues a minute in all. Add a family only for files that sound alike (same attack, decay and
    brightness): measure them first;
  - whooshes only at section cuts; each hit on its exact word;
  - a whoosh leads into an impact for a text slam; one big swell per video.
- **Sources:** no YouTube-ripped memes (Content ID). Use only the kit library, whose licences are in `kit/music/CREDITS.md`.
- **A cue's time is when it is heard (2026-10-11).** Pass the moment of the event (a card lands, a click, the middle
  of a wipe); `kit/audio/mix.py` shifts each file so its attack (UI sounds, impacts) or its peak (whooshes) lands
  there, measured from the file. Exception: a riser starts on its cue and builds to the moment after it. The
  paper-studio preset's own `audio.py` keeps the old file-start placement. Fallback: `align: "start"` on a cue, or
  `mix(..., align=False)`.
- **Music on the story (2026-10-20):** plan where the music turns: `"music": "drop" | "stop" | "riser" | "turn"` on
  2-4 passages of visual_plan.json (plan_check warns when a plan of 45 s or more has none). Place drops from the
  music map instead of measuring them (kit/film/mix.py: `drop="auto", at="w<id>"`); every bed starts on a downbeat.
  In the page, `HF.music.snap(t)` lands a card on the beat the eye still reads as in sync (≤100 ms early, ≤40 ms late),
  `HF.music.turns()` lists the turns to land reveals on; chapter cards and camera whips snap by themselves.
- **Quiet moments (2026-10-10):** a price, a failure, a reaction or a verdict can land on the voice alone. `S.quiet(a, b)`
  takes the music out (or `{ depth: -10 }` down) with 0.35 s ramps; at most 2–3 a video, never under the hook's first
  3 s. If the music needs to resolve, end the bed on that moment instead of cutting it mid-phrase.

## 8. QA, the critic and the fix loop

- **Automatic gate:** `kit/qa/qa.py` checks CRITICAL, HIGH and MEDIUM issues, gives each a stable ID, and exits 0/2/3.
- **Review sheets:** `kit/qa/sheet.py` makes the first and last 2 s, a frame every 3 s, and each cut at ±0.12 s.
- **Confirming a finding:**
  - confirm each one in two ways (frames, waveform, loudness stats, transcript) before acting;
  - for a borderline seam, re-transcribe only a 5.5 s window around it and ask whether the word is there, not how long it is.
- **Fresh critic** (`kit/qa/CRITIC.md`): run it on the 1080p draft render (about 3.5 min for 5 min), never on a 4K render: 4K is rendered once, after the draft passes. A new agent that gets only the render, the brief and the previous ledger, never my reasoning or my list of fixes. It marks earlier findings FIXED, PARTLY or STILL PRESENT and looks for regressions. On one reported project the builder's own checks missed 28 % frozen footage that critics then found.
- **Self-fix whitelist** (anything else goes to the user with frames and timecodes):
  - nudge a cut by up to 500 ms;
  - trim or extend a clip by up to 500 ms;
  - retime a caption to its word window;
  - change gain by up to ±3 dB, or re-master loudness;
  - add a 25–30 ms fade at a click;
  - remove an exact duplicate;
  - move a caption inside the safe zone.
- **Stopping:** at most 3 fix-and-render rounds. Stop early when what's left is sub-frame or cosmetic. Apply each fix across the whole video, not only where it was found, and never reopen a decision the user already made.
- **Scope:** notes arrive against named beats and timecodes. A lesson from one reported project: a version got "really disappointed" because it was 18 small tidy cards; the approved one had five full-bleed takeovers and more movement grounded in the footage. The problem was scope, not polish.

- **Lessons from the first critic run** (pilot reel, 2026-10-01), all missed by the automatic checks:
  - A teaser must never show the answer. Scrub every frame of a clip shown in a blind test.
  - Frame 1 was blank, and `qa.py` now fails that.
  - Captions in hero layouts fell in the platform UI zone. Keep one caption slot per video, clear of the head.
  - Jump cuts need a real scale change of 1.08–1.12.
  - A screenshot's text must reach the 32 px floor, so crop tight.
  - The end-card question has to still be open after what the voice said.

### Slideshow risk (score the scene plan before building)

Score each of 6 dimensions 0–5 and average them:
- repetition: one scene type over 70 %, under 60 % unique descriptions, or one shot size over 60 %;
- decorative visuals that carry no information;
- weak motion;
- weak shot intent;
- too much typography: text/stat cards score 4 when over 60 % of scenes, 2.5 at 40–60 %;
- cinematic claims the plan can't support.

Under 2 is strong, under 3 is acceptable, 3–4 means revise before building, and 4 or more fails.

## Scenes from meaning (2026-10-03)

- Before building a long-form, decide each passage's explanation type and technique with `kit/refs/SCENES.md`. Then write `visual_plan.json` and run `kit/hf/plan_check.py` (exit 3 = fix before building).
- One diagram per idea that develops across passages. The visual adds what the narration can't. Words on screen are 2–4 key words, never the sentence.
- Build with the `kit/hf` components (`kit/hf/README.md`). Annotate real screen recordings, and blur anything private.
- Mux AAC with `-aac_pns 0`: the native encoder's noise substitution can add +9 dB spikes on typing and other sparse SFX.

## 9. Version 7 defaults (2026-10-05)

The owner asked for four things:
- never cut a sentence midway ("it feels really bad, like I had a bad impression of someone");
- a better grade;
- better zooms;
- new hand-made animation styles.

Old videos are not re-edited. The researched numbers live in each module's README; this section is the checklist.

- **Cuts (`kit/cut/README.md`).**
  - Make a boundary map per take: `uv run python -m kit.cut.sentmap <job>`. It combines a text model (SaT), an audio end-of-turn model (Smart Turn v3), pauses (VAD), pitch fall, and connector words ("and / but / because / ki / ke / aur / kyunki").
  - Choose keep ranges with `boundaries.snap`; on a retake, use `restart_cut`.
  - Gate the edit with `cutcheck`. FAIL (exit 3) blocks the build. REVIEW items are judged by the editor with the text either side; they are not auto-passed.
  - After rendering, run `cutcheck --media` to re-listen to every join. It also catches squeezed or clipped words.
  - Pause trims inside a sentence keep at least 0.15–0.20 s.
- **Grade (`kit/look/README.md`, v2 section).**
  - Use `grade.py --v2` with a `faces.py` face track and a person matte.
  - What v2 does:
    - white balance from the skin hue;
    - a sigmoid tone curve with highlight roll-off;
    - subtractive saturation;
    - a skin hue pull and chroma knee;
    - background separation (shelf room −0.7 stop);
    - subtle halation, a vignette and grain.
  - Face Y′ sits at ~0.535 on the bookshelf frames, halfway between the colourist target and the old engine; the owner chose that.
  - `--reel` halves the grain and lifts the shadows.
  - Gate with `scopes.py qa`: skin hue ~123°, chroma 0.20–0.32, face minus background ≥ 0.08 except in the cream-wall room.
- **Camera (`kit/hf/README.md`, "v7 camera").**
  - The director chooses moves from the edit and tags.
  - Reframe 1.00 ↔ 1.15: only at a new thought, held for the whole thought, eyes on the upper third.
  - Punch 1.22–1.32: at most one per 16 s in long-form, one per 6 s in Reels.
  - Snap zoom 1.4–1.5: joke tags only, with baked motion blur and a landing shake.
  - Slow push +5–10%: story moments.
  - Zoom transition: section changes only.
  - Never the same move twice in a row; never A/B framing on every cut.
  - The shorts CLI punches 1.15 / 1.3 and sharpens with zoom.
- **Hand-made styles (`kit/hf/README.md`, "v7 styles").**
  - The styles: sketch diagrams (rough.js), marker notes (perfect-freehand), a scribble outline around the speaker (from the person matte) and paper cut-out collage.
  - Use 2–3 per video, one per passage, never two on the same frame, on top of the stickman's 2–4 moments.
  - The scribble outline gets 2–4 s on a hook or opinion line.
  - Marker notes: 1–4 marks, each landing on its spoken word, never on the face.
  - Collage: one comparison or evidence beat of 5–8 s.

## 11. Evidence the viewer can read (2026-10-10, kit/refs/RESEARCH.md)

What the reference study found (Ali Abdaal, Mrwhosetheboss, Cleo Abram, Varun Mayya) against our published work: they
show the real thing big enough to read and keep earlier results on screen; ours often showed small mock cards on a large
empty pastel field and, in Shorts, grey placeholder lines where the payoff should be. The rules:

- **Readable on a phone.** Evidence text (UI, code, prompts, numbers) is drawn at 32 px or more on 16:9 and 36 px or more
  on 9:16, measured after every scale (`precheck.mjs` "small"). A card built at UI size is fine while it lands; before
  the viewer must read it, zoom in (`S.focus`) or build it bigger. Exceptions: corner chrome, kickers (`.lbl`), window
  title bars and anything marked `data-decor`. Fallback when a screenshot can't be read even zoomed: crop to the one
  line that matters and say the rest.
- **Time to read.** A block of 4+ words that isn't spoken type stays up 0.6 s + 0.24 s a word (precheck "read"). Spoken
  type (`say()`) is exempt: the voice reads it.
- **Focus on the line being talked about.** `S.focus(L, card, { at, until, line, click })`: the scene zooms so the card
  fills ~78 % of the free part of the frame, the line gets a highlight, the other rows dim; `click` brings a pointer in
  first (the action causes the zoom). Use it on real screenshots, code and model output; pair it with a `graphic` or
  `aside` beat so the box isn't over the target.
- **Keep results on screen while they accumulate.** For tests and comparisons, `S.scoreboard(...)`: rows stay, each
  result lands in its row on the word that says it, the winner is marked at the end. Values are only what he said or
  showed.
- **No placeholder as payoff.** Grey skeleton lines may tease a result that is still coming; the payoff shows the real
  content (his words, a screenshot, the actual output). If the real output isn't available, ask for a screenshot or
  show the spoken words; never invent it.
- **Choose by what the moment needs:** relationships → a diagram built in causal order; differences → a comparison that
  keeps both sides; an operation → the footage or screenshot itself, focused; a result → room to look at it (a hold);
  feeling → the face, and maybe quiet.
- **Holds are allowed.** See §6: a readable still is a hold; nothing floats to pass a check.
- **One object through a workflow (2026-10-11, `S.flow`).** When the speech walks one action through its states
  (prompt → running → result, input → output), keep one container and let it change shape instead of swapping
  cards: the old content leaves before the container moves, the new content enters once it settles, so text never
  collides (separate cards crossfading put the new text over the old). Use it for 2–4 states of one process, with
  real content in every state. Exception: unrelated ideas are separate scenes, not one morphing box. Fallback: a
  single card whose content swaps in place (same container, no geometry change).
- **On a screen recording, the cursor leads and the camera follows (`sd.walk`).** The pointer travels and clicks
  first, the camera eases in ~0.15 s later and slower (1.4 s, sine in-out), so the viewer's eye goes where the pointer
  went; a zoom box covers whole lines, never cutting text mid-word. Opt-in until it is judged on real recordings;
  `sd.zoom` + `sd.cursor` remain for cases where the camera must arrive first (the pointer is too small to find).

## 12. Conversation and podcast inserts (2026-10-11; the pipeline is `kit/podcast/README.md`, 2026-10-12)

From the Opus 5.5 collection's podcast entry (stokebuilder-356793) with its quota rejected:
- a graphic sits inside one uncut stretch of one speaker's audio, and is synced to their words; never across a cut or a
  change of speaker;
- leave faces on screen between graphics (several seconds); a quiet talking-head moment is not a gap to fill;
- copy is verbatim or faithful to what was said; no invented facts, numbers or quotes;
- when a graphic goes full screen, keep whoever is talking in a corner picture-in-picture, and use only the real
  camera angles (no fake second angle from a crop or a mirror);
- one shared visual style for every insert of an episode; no music under the conversation unless it serves a moment.

