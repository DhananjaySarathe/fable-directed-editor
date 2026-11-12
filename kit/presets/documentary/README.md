# preset_documentary: the "Netflix-style" tech documentary

Built 2026-10-24 for the author's pilot ("Can AI Build a Website That Doesn't Look AI-Made?"). The reference is Clueso's Series A film (youtu.be/cd1tAlb3wWM): interviews to the side of
the camera with name lower-thirds, cutaways, a dark grade, burned-in subtitles, chapter cards and a cold open with a
callback at the end.

## When to use it: only when he asks

The owner, 2026-10-24: "Whenever we are recording a normal tutorial kind of video, we're going to use what we have
currently. Whenever I say specifically something like a Netflix sort of video, then only we're going to use these
particular new changes."

- **Use it** when he says Netflix-style, documentary, doc, mockumentary, or names this preset.
- **Never use it** for tutorials, explainers, reviews, Reels from a single take, podcasts or anything else. Those stay on
  `preset_whitespace` (the default) or whichever preset he names. "Cinematic", "dark" or "moody" alone are not a request
  for this preset: ask him.
- **The switch** is one line in film.py: `PRESET = "documentary"`. Without it, kit/film refuses `DOC` and J/L cuts
  (`kit/film/doc.py guard`), the page never inlines `kit/hf/doc.js`, and precheck judges the page as before. A normal
  film's cut, page and mix are byte-identical to before this preset existed (tests/test_documentary.py checks it).

## What changes in a documentary (and only there)

| | Normal film (OWNER_DEFAULTS) | Documentary |
|---|---|---|
| **His shot** | full frame or a card/circle over graphics, the lens moving | full frame in his room, or off screen. One slow push or pull per shot (HF.doc). No cards, circles or designed stages |
| **Graphics** | canvas stations, takeovers, components ≥ 1.2 a minute | lower-thirds, chapter cards, time stamps, subtitles, a results board, screen work (HF.screen). Few and quiet |
| **Captions** | word-by-word captions | one line of documentary subtitles (`DOC subtitles=True`) |
| **Cutaways** | none (takeovers instead) | `DOC broll`: inserts, him working, the location, screens; graded with the doc LUT; natural sound optional |
| **Cuts** | hard cuts on whole sentences | the same, plus J/L cuts at scene and speaker changes (`{"j": s}` / `{"l": s}` on KEEP) |
| **Hook** | opens on his face | cold open; it may start on footage that is not his face, with his face by 5 s |
| **precheck** | still 6/10 s, away 12 s HIGH, layout 35 % HIGH | `--doc`: still 10/15 s, away HIGH past 30 s, layout MEDIUM |
| **Grade** | the film's look, room as shot | look `doc` (no vignette, room as shot); the darker room comes from lighting it that way |
| **Music** | one or two calm beds, ~18 dB under, lifted a little in pauses | a **score** (2026-10-25): a cue per act (up to `doc.SCORE_CUES` = 6), each placed by `drop=`/`at=` so its drop or section lands on a story moment; `DC.swell` brings it up 4-8 dB in the held beats; `HF.quiet` takes it out for a punchline. Still ~18 dB under the voices while they talk |
| **Sound** | small cues thinned to 8 a minute | every typed line has the typing sound, cut to the typing's length; hits on DID/MISSED; these are `keep` cues (`DC.cue`), never thinned |

Everything else in OWNER_DEFAULTS holds unchanged: whole sentences only, re-listening to every join, the picture quality
rules (§0), music about 18 dB under the voice while anyone talks, guests' consent, blurring private details, no invented
numbers, the end card with both handles, Reels as complete stories.

## The Netflix cut (v2-v3, 2026-10-25, films/not-ai-made)

The owner on the first draft: "the whole taste of documentary is missing" (no zooms while people talk, hard cuts between
speakers, back to a character after an animation for no reason, exhibits that look like a tutorial). Then: "The music
plays a really important role", and for each tool the film names, "tell user in Netflix styled animation what is it,
what are the features .. What all it fixed ... the user must be able to feel not just see it". What came of it:

- **The camera** (`DC.cam`): framings W 1.0 / M ~1.15 / C ~1.28 about the face, a visible move in every shot, punch-cuts
  on the words that land, a step per word on a list. Never past x1.3.
- **Between speakers**: J/L cuts, a board shot, or a reaction; never a bare hard cut. Once the picture leaves a speaker
  for a graphic, his line ends over it: the film goes on to the next speaker, never back for a tail.
- **Type**: condensed caps (Oswald, copied in by `doc.copy_fonts`) for names, titles and chapters; JetBrains Mono for
  notes; one red (#E50914), green for DID. Everything types on (`DC.typed`) with the typing sound.
- **Screens are filmed objects** (`DC.screen`): a tilted plane, focus falloff, grain, a slow dolly, a camera inside that
  scrolls, pauses and zooms; `sc.mark` draws viewfinder corners and a typed tag on the thing; `DC.dossier` types the
  DID / MISSED list beside it.
- **Depth of field never hides content** (the owner on the 2026-10-25 preview): a filmed screen's top/bottom blur is a thin band
  (13 % of the plane, 3 px). Marks and their tags ride above it and the sheen, and the band eases off while a mark is up.
  The board's thread shots keep their full macro blur. Two takes of one person cut together get a zoom-through (a fast
  push into the cut, a flash, a fast pull out), never a bare jump.
- **Before / after** (`DC.compare`): two captures of one place, the AFTER wiping across behind a red line, each side
  labelled, a typed note on what changed. This is how "what it fixed" is shown.
- **The explainer** (`DC.explainer`): when the film names a tool, the camera follows the red thread into a dark evidence
  wall. The name slams in on a hit (put the score's drop there), an optional definition beat says what the words mean,
  then each feature is a station: a print under a spotlight, the number, the name, the command, what it does, and what it
  did in this film (the real number from the logs). It ends pulled back on the whole thread with the one word it fixes.
  **Budget its time**: per station, the typing (label 30 cps, text 52, proof 46) + ~0.6 s to read + the 0.7 s move;
  the not-ai-made explainers came to 15.2 s and 17.8 s. Every claim on it must be in the run logs (no invented numbers;
  a detector count that fell because flags were *accepted*, not fixed, is not a fix).
- **Cards**: chapter cards (`DC.chapter`), typed field notes and verdicts (`DC.card`).
- **The score**: one cue per act in film.py `MUSIC`, each with `drop=<track s>` and `at=<moment>` so the music turns on
  the story (a reveal, a title slam, a chapter card, the final site); `DC.swell(a, b, db)` over every held beat (exhibits,
  explainers, chapter cards, the finale); `HF.quiet` for a stop ("What?" got a scratch and silence); `DC.cue(name, t, db,
  { align, dur })` for hits that must play. kit/film/mix.py judges a documentary's music by the voice level only (no
  "two calm beds" or "lifts a minute" findings: a score lifts on purpose).

## Files

- `kit/film/doc.py`: guard, J/L cuts (`pic_a`), cutaways (`work/broll/bNN.mp4`), natural sound (into `vo.wav`; the voice
  alone in `vo_voice.wav` for the re-listen) and `D.doc` for the page.
- `kit/hf/doc.js`: `HF.doc(K, ROOT, { aroll })`, the documentary look tokens, and `DC.all()` / `broll` / `thirds` /
  `chapters` / `stamps` / `letterbox` / `subtitles` / `results` / `third` / `chapter` / `stamp`; the Netflix cut's
  `cam` / `typed` / `screen` (+ `mark`) / `dossier` / `card` / `compare` / `explainer` / `swell` / `cue`. It publishes
  `window.__speaker`.
- `kit/audio/mix.py`: a quiet window with a positive depth is a swell (music up); a cue with `dur` is cut to length.
- `kit/look/looks.py` look `doc`.
- `kit/qa/precheck.mjs --doc` (kit/film passes it for a documentary).
- `templates/template.html`: the page to copy to `films/<name>/src/template.html`.
- `example/`: a smoke-test documentary on the kit/film example take, with generated cutaways (no real footage).

## film.py

```python
PRESET = "documentary"
FPS = 25
SOURCES = {
    "me":    dict(job="nam-interview", file="...", picture=True, clean=True, kind="interview",
                  speaker="Alex", role="Developer · @yourchannel", tracks={"aroll": ""}),
    "owner": dict(job="nam-owner", file="...", picture=True, clean=True, kind="guest", base=4000,
                  speaker="Priya", role="Owner, Café X", tracks={"aroll": ""}),
}
KEEP = [
    ("me", 0, 14, "cold"),
    ("owner", 3, 40, "client", {"l": 0.6}),      # her picture comes in 0.6 s before his line ends
    ("me", 101, 130, "attempt1", {"j": 0.8}),    # his voice starts 0.8 s before his picture
]
GRADE = dict(look="doc")
DOC = dict(
    broll=[dict(file="assets/broll/typing.mp4", at="w104", dur=3.5, src_in=1.2, audio="natural", gain=-10),
           dict(file="assets/screens/site_v1.mp4", at="w118-0.3", until="w130", grade=False)],
    chapters=[dict(at="tag:attempt1", title="Attempt one", sub="Day 1 · 23:10")],
    stamps=[dict(at="w104", text="DAY 1 · 23:10")],
    letterbox=[("tag:client", "tag:attempt1")],
    results=dict(at="w900", until="w940", title="Who spotted the AI site?", rows=[["Panel", "1 of 5", True], ["Designer", "yes", False]]),
)
MUSIC = [dict(file="calm/calm__mixkit__piano-reflections.mp3", a=0.0, b="end", under=-18.0, duck="voice", end_fade=2.0)]
```

The run is kit/film's (`kit/film/README.md`): prep, cut --plan, cut --voice (listen), joins, cut, grade --sheet, grade,
build, draft, critic, render, reels. `cut` also writes the cutaways and the natural sound; `build` links them into the
page and adds `D.doc`.

## Before the first real documentary

- He picks the grade on a sheet made from a test clip shot in the interview setup: `doc` beside `cinematic` and `moody`,
  all with vignette 0.
- Built after the shoot, on real footage: the footage logger (`kit/film/log.py`), second-angle sync, story-order cutting
  from the log.
