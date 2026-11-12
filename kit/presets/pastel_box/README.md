# preset_pastel_box

> **Read first, every edit:** `kit/refs/OWNER_DEFAULTS.md`, the owner's standing taste. It holds in every preset; this
> file can be stricter, never plainer. **Before the template is written, the planning gate:** `kit/refs/SCENES.md` →
> `visual_plan.json` → `python3 kit/hf/plan_check.py visual_plan.json` (0 errors). Pick the components from
> `kit/hf/registry.json`, starting with `python3 kit/hf/tools/registry.py --unused`. After the build,
> `kit/qa/precheck.mjs` must show 0 HIGH, ambition section included (OWNER_DEFAULTS §8).

The look and the fast workflow of **"3 AI workflows (+1 bonus) I use as a developer"** (`films/ai-workflows`,
2026-10-10). The owner: "Video is really, really good". It follows his reference edit (kit/refs/MOTION.md, memory
"reference-hook-grammar"): one pastel aurora world, the speaker as a moving box, serif type rising on the spoken word,
product-like UI cards, a chapter card per part.

Use it when the owner names it or asks for the reference look. Since 2026-10-20 the default for a talking-head edit
is `preset_canvas_studio` (kit/presets/canvas_studio); `preset_paper_studio` stays the calm alternative. His rule from
2026-10-20 holds here too: he is never cut out, only full screen or in a closed shape (circle, square, card).

The point of this preset is speed and cost with no loss of quality (the owner, 2026-10-10). The ai-workflows film took
6-7 h. Most of that was hand-writing ~940 lines of scene code, plus two extra 4K renders spent finding bugs. Here the
frame and the components are written once and tested, so a film is its cut plus a short scene list. Every check runs
before the one 4K render.

## 1. Files

| | |
|---|---|
| `kit/hf/studio.js` | `HF.studio(K, ROOT, st, opts)`: the frame (world, chrome, chapter cards, type, scene layers, the box wiring, end card) |
| `kit/hf/studio_ui.js` | `S.ui.*`: product-like UI cards (message, workspace, thread, PR, stamp, doc, checklist, chat, toggle + pointer, column, hub, tiles, numbered board, note, lower third, thinking dots, pointer) |
| `kit/audio/mix.py` | `mix(work, edl, beds, total)`: beds per chapter (voice-relative, crossfaded, gap-scanned), cues, master, dropout guard |
| `kit/qa/precheck.mjs` | the page checker: offscreen text, text over the face, overlaps, text on a foreign card, blank world, page errors (5 s for a 5-min film) |
| `kit/qa/qa.py`, `kit/qa/sheet.py`, `kit/qa/CRITIC.md` | the render gate, the review sheets, the fresh critic |
| `preset.json` | the tokens (palette, type, motion, chrome, audio, qa thresholds) |
| `kit/film/example/` | a small worked film on HF.studio: `film.py`, `visual_plan.json`, `src/template.html` |

## 2. The workflow (draft first, one 4K render)

Times measured on this Mac (M-series, 24 GB, 15 cores) for the 5-minute ai-workflows film.

```
# 0. ingest each take (word timings): uv run shorts probe "<take>" --job <take> --landscape && uv run shorts analyze <take>
# 1. prep (per take: CFR 4K intermediate, 1080 proxy, YuNet face track, voice: [WPE dereverb if the room echoes] + DeepFilterNet3)
uv run python prep.py
# 2. the cut: KEEP word ranges (whole sentences), FIX spellings -> edl.json, cuts.json, vo.wav, the ungraded 4K A-roll
uv run python edl.py --voice        # first: the voice only (seconds) -- check every join before any picture work
uv run python edl.py                # then the picture (~6 min)
# 3. grade only the cut (look v2): matte ~6 min + grade. At 4K the x264 encoder was the bottleneck (12 workers idled
#    behind -preset slow): GRADE_PRESET=veryfast for this intermediate
GRADE_WORKERS=12 GRADE_PRESET=veryfast uv run python grade_cut.py --only=matte,grade
# a later cut tweak (edges moved, a sentence restored from frames already in the cut): no rebuild, no re-matte
#   uv run python edl.py --map   # the new frame map only (save the old aroll.map.json first)
#   uv run python -m kit.cut.recut --old-map=<old map> --old=$W/aroll_ungraded.mp4 --new-map=$W/aroll.map.json \
#       --out=<new>.mp4 --matte-old=$W/matte --matte-new=<dir>      (or re-cut the graded aroll.mp4 and skip the grade)
# 4. the page, captions, cues, mix
uv run python build.py && uv run python build.py --cues && uv run python audio.py
npx hyperframes lint $HF
node ../../kit/qa/precheck.mjs $HF/index.html --fps=5 --holds-out=$W/holds.json   # ~5 s: fix every HIGH (and the
#    `small` / `read` findings: zoom with S.focus or build it bigger) before rendering anything
# 5. the draft: 1080p, 3.5 min -> qa.py + the fresh critic on the draft (never on a 4K render)
npx hyperframes render $HF -o $R/draft.mp4 --resolution 1080p --quality draft --workers 4
#    (mux it with the mix: ffmpeg -i $R/draft.mp4 -i $W/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest $R/draft_av.mp4)
uv run python ../../kit/qa/qa.py $R/draft_av.mp4 --cuts=cuts.json --expect-duration=<s> --expect-size=1920x1080 --holds=$W/holds.json,$W/cues.holds.json
# 6. one 4K render (~18 min: capture 8 + encode 10), mux, gate
NODE_OPTIONS=--max-old-space-size=16384 npx hyperframes render $HF -o $R/raw.mp4 --resolution 4k --fps 30 --quality delivery --workers 3
uv run python build.py --mux && uv run python ../../kit/qa/qa.py <final>.mp4 --cuts=cuts.json --expect-duration=<s> --expect-size=3840x2160 --holds=$W/holds.json,$W/cues.holds.json
uv run python -m kit.cut.cutcheck edl.json --sources=<take>=0,<take>=2000,... --media=<final>.mp4
```

Always `HYPERFRAMES_NO_UPDATE_CHECK=1`. A 4K HyperFrames render needs `NODE_OPTIONS=--max-old-space-size=16384` and
`--workers 3` (it crashed without). Only one 4K render or grade at a time on this Mac. Tell other sessions before you start one.

## 3. Writing a film's template

`kit/film/example/src/template.html` is a small model. The frame is one call:

```js
const K = HF.kit({ tl, id: "film", width: 1920, height: 1080, words: D.words, pieces: D.pieces });
const st = HF.stage(K, ROOT, { aroll: "aroll" });
const S = HF.studio(K, ROOT, st, { end: D.total, talk: D.talk, kicker: "workflow",
  palette: { gpt: "#10a37f" },                                     // extra brand colours for this film
  chrome: { left: "yourchannel · my video '26" },
  sections: [[0, "00 — the hook"], [K.W(110) - 0.1, "01 / ..."]] });
const { C, Q, W, E, el, layer, land, leave, card, chip, mono, say, line, strike, fromPill, chapter, beat, FLIPS, ui } = S;
// scenes ...
S.endCard();   // the handles come from kit/brand.json (HF.HANDLES); never type them into a template
S.box({ jumps: [<first word id of each pause-trim piece inside a held full frame>] });
K.finish(D.total);
```

A scene is a **beat** for the speaker box plus a **layer** for its graphics:

```js
beat(W(116) - 0.15, "beside", { side: "left", tag: "w1_dot" });    // hero | face | punch | beside | aside | graphic (+ card, section)
{ const L = layer(W(116) - 0.2, W(177) - 0.05);                     // floats and pushes: never a frozen hold
  say(L, 120, 122, { x: 120, y: 760, w: 760, size: 120, stress: [122] });   // the spoken words, on their times
  ui.pr(L, 1040, 330, 760, 330, { title: "Fix 3 bugs from the sheet", branch: "agent/sheet-fixes", base: "dev", at: W(242) - 0.1 }); }
```

Rules (each one cost a render on ai-workflows):
- **Type over video** (white, `shadow: true`) sits low (y 700-860) and leaves with `.out(t)` before the next line rises in the same spot. Lines spoken under 0.3 s apart go in **one** `say` with `br`.
- **The first element of a scene lands when the box leaves**, on the first word of the scene. No empty world, not even after a chapter card; the next scene starts on its exit.
- **No big empty card.** Grow it with its content (`ui.column`), or land it when its first item lands.
- Chapter titles auto-fit the 1180 px beside the numeral. Keep text inside x 24-1896, y 20-1060 (precheck).
- A card leaving with the box: `leave()` it about 0.2 s before the box moves. A card is never cut off in one frame.
- Generic content only: made-up names, no real logos or workspaces, no numbers he didn't say.
- `S.box({ jumps })`: a hard 1.12x punch hides a pause trim inside one held full frame. Skip a cut where a scribble
  outline is traced at full frame.

## 3b. Evidence (2026-10-10, EDITING.md §11)

- `layer()` sways ±6 px and pushes 0.4 %/s (the reference); `layer(a, b, BACK, { read: true })` holds still and is a
  declared reading hold. Don't add motion to pass qa.py.
- `S.focus(L, card, { at, until, line, click: { from: [x, y] } })`: zoom to the card (or one line of it), highlight the
  line, dim the rest; the studio's UI cards (`.txt` 25 px) need it before the viewer reads them on a phone.
- `S.scoreboard(L, x, y, w, { title, rows: [{ name, color }], at, fmt })` -> `set(i, value, t)`, `win(i, t)`.
- `S.quiet(a, b)`: the music out under a price, a failure or a reaction (audio: kit/audio/mix.py reads cues.quiet.json).
- `S.flow(L, { states })`: prompt → running → result as one container (EDITING.md §11); `sd.walk(steps)` on a real
  screen recording: the cursor leads, the camera follows.
- Sound cue times are heard times: give the event's moment; mix.py lines up each file's attack or peak.
- Worked check: `kit/hf/demos/evidence/` (a fixture page: native-size card vs focus, a scoreboard, a quiet moment).

## 4. Sound

`audio.py` lists the beds: one per chapter, starting on its chapter card, and a bookend for the hook and the verdict.
`kit/audio/mix.py` does the rest (music about 12 dB under the voice, crossfades, cue thinning, -14 LUFS / -1.5 dBTP).
**Read its WARNING lines**: a bed whose used range has silent gaps (a breakdown) must start elsewhere. On ai-workflows,
Beave - Talk's breakdown at 57.7 s dropped the mix to digital silence.

## 5. The cut (whole sentences, edges in real quiet)

- Whole sentences only. In the **first minute**, no repair inside a sentence: a filler cut mid-flow ("techniques of
  three, you can say,") restarts mid-sound and the owner hears it. Later, a repair needs a real pause on both sides.
- Every edge sits in quiet, measured on the voice envelope, not on the aligner's word times (they run late); `kit/cut/edges.py` has the functions (onset, offset, joint, audit):
  - `onset()` starts before the breath or attack;
  - `offset()` ends once the word stops sounding (not the room tail; waiting for it added 11 s of air);
  - two kept ranges on consecutive words only cut out the quiet between them, or stay continuous with no gap
    (films/ai-workflows/edl.py).
- `edl.py --voice` first, then measure each join before any picture work.

## 6. QA order (never find a bug with a 4K render)

1. `precheck.mjs` on the page: 0 HIGH, and every `small` / `read` finding fixed or judged. 2. the draft (1080p) +
`qa.py --holds`: no HIGH freeze (a still with nothing readable), flash, black or dropout; a reading hold is fine.
3. The fresh critic (CRITIC.md) on the **draft**. Whitelist fixes; re-render the draft only.
4. One 4K render, then `qa.py` + `cutcheck --media`. 5. Deliver the video, captions.srt and posting notes, with the open items listed.

## 7. Social cuts (X, LinkedIn): from the finished film, no re-grade

- `build.py --x` builds the page with burned captions (`S.captions`):
  - a phrase shows only while under a third of its words are on screen as type;
  - `data-nocap` elements, such as a hand-written CTA, hide it;
  - the 2.5 s end card shows handles only, with no YouTube slots.
  Render it at 1080p in about 6 min, then `build.py --x --mux` writes `final/<film>/x/`.
- `uv run python -m kit.cut.clip <edl.json> <x_full.mp4> <clip.mp4> --ranges=a-b,... --card="Full *breakdown*|in the reply ↓"` (the card's handles default to kit/brand.json)
  - It cuts whole-sentence word ranges in the pauses with 40 ms audio fades, and adds a pastel end card with a slow push.
  - It refuses a range that doesn't end a sentence.
  - Re-listen to the clip (whisper-cli) and look at a frame per join.
- Posting on X (the owner's account is small): the clip is the main post, the full video goes in the first reply, and the YouTube link in a later reply. Post text follows the x-post-voice skill.
