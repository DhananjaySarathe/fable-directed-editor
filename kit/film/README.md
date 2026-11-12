# kit/film: the shared film pipeline

Built 2026-10-20 (kit/refs/AUDIT_2026-10-20.md, phase 4). Before it, every film copied its own `edl.py`, `build.py`
and `audio.py` (2,265 lines of `edl.py` alone), so each fix (the Framecast frame offset, aligner drift at joins,
chunked 4K) was re-learned film by film. Now a film is three things:

```
films/<name>/film.py              the settings: SOURCES, KEEP, JUDGED, fixes, spellings, MUSIC, REELS   (~40-120 lines)
films/<name>/visual_plan.json     the scene plan, schema 2 (kit/refs/SCENES.md -> python3 kit/hf/plan_check.py, 0 errors)
films/<name>/src/template.html    the scenes on the look's frame, timed to word ids (W(id)) and KEEP tags
                                  (a new film copies kit/presets/whitespace/templates/template.html, the default look)
films/<name>/assets/              screenshots (blurred copies only)
films/<name>/reels/<r>/template.html   each Reel's page (its sentences are in film.py REELS)
```

Read `kit/refs/OWNER_DEFAULTS.md` first; this is its §8 gate as commands. kit/reel stays the engine for a Reel made
from its own single take; a long film and the Reels cut from it use this.

## The run

```
uv run python -m kit.film films/<name> prep       # words (shorts probe + analyze), the 4K picture copy, the cleaned voice
                                                  # and its measured EQ, for each source that needs them
uv run python -m kit.film films/<name> cut --plan # cutcheck gate + the pieces, nothing written (fix KEEP / JUDGED here)
uv run python -m kit.film films/<name> cut --voice  # edl.json + vo.wav only: listen before any picture work
uv run python -m kit.film films/<name> joins      # each edge on the voice envelope, then whisper on every join (exit 2)
uv run python -m kit.film films/<name> cut        # + one picture track per track name, faces
uv run python -m kit.film films/<name> grade --sheet=8,30,120   # the A/B: the film's look beside "clean" on white
                                                  # (--sheet-looks=, --stage=); he picks, it goes in GRADE
uv run python -m kit.film films/<name> grade      # look v2 on the cut's camera track (only what the edit keeps); a
                                                  # changed GRADE re-grades without --force
uv run python -m kit.film films/<name> build      # the HyperFrames page (F.hf) + captions.srt; then `snap --at=...`
uv run python -m kit.film films/<name> draft      # plan_check (stops on an error), build, lint, cues, precheck (stops on
                                                  # HIGH), mix, 1080p draft, qa.py
                                                  # -> the fresh critic on renders/draft_av.mp4 (kit/qa/CRITIC.md)
uv run python -m kit.film films/<name> render     # the same checks, the 4K render in 30 s chunks, mux, qa.py
uv run python -m kit.film films/<name> reels      # each Reel from the finished film, by whole sentences
uv run python -m kit.film films/<name>/reels/a draft | render     # a Reel's own page, mix, render (1080x1920)
```
Also `mix`, `cues`, `precheck`, `mux [--draft]`, `snap --at=3,12.5`, `paths` (W, HF, R, FINAL, EDL). Everything it
writes is under output/ (kit/paths.py), edl.json and cuts.json included: `output/temp/films/<name>/work/`. One heavy
render at a time on this Mac.

**The gates, in order** (OWNER_DEFAULTS §8). `draft` and `render` run `kit/hf/plan_check.py` on the recipe's
`visual_plan.json` first, timed on the film's own cut (`--edl=work/edl.json`): an error (exit 3) stops the build, a
warning prints, no plan is a note, and `--force` goes on anyway. Then precheck on the built page: a HIGH stops it
(`--force` goes on). Read precheck's last line: it repeats the verdict with every HIGH by kind and time ("precheck
FAIL: 3 HIGH [framing 06:07.6 07:12.0, density 01:10.6], 9 MEDIUM"); the full report is work/precheck.json.

**Defaults by the film's date (v11, 2026-10-22).** Three v11 defaults follow the day the film was made
(`kit.film.mix.made_on`: the day film.py was added to git, else the oldest of its file times and its work dir's
edl.json / vo.wav), so a rebuilt old film stays what it was (OWNER_DEFAULTS §7) and a new one gets v11 without anyone
asking. Each prints why:
- **the sound** (`SOUND`): "v11" from 2026-10-22, sticky (below, "mix");
- **the lens** (`LENS`): an explicit `LENS` in film.py wins (True, False or a dict); otherwise on for a film made from
  2026-10-22 and off before (a Reel follows its own date);
- **the ambition gate** (`AMBITION`): an explicit `AMBITION` in film.py wins; otherwise precheck's ambition, speaker and
  density findings stop the build for a film made from 2026-10-22, and print as MEDIUM before it. `--no-ambition`
  forces it off, `--ambition` on.

## What each step does (and the lesson it carries)

- **prep** (prep.py, from films/reverse-engineer prep.py + voice_eq.py, films/ai-workflows prep.py, kit/reel prep.py):
  - words: `shorts probe [--landscape]` + `shorts analyze` for a source with a `file` and no words yet;
  - picture (`picture=True`): a CFR SDR copy of the original at the film's FPS, HLG tone-mapped. shorts probe keeps a
    16:9 take at 1080p, so a 4K film cuts from this;
    `TONEMAP` picks the HLG -> SDR (kit/film/tonemap.py): "mobius" (the default, v11), "hable", "bt2390" (BT.2390's
    roll-off as a 3D LUT, dithered to 8 bit: who-gonna-hire, 2026-10-23) or "bt2390c"; `PICTURE_CRF` its x264 CRF (12);
  - voice (`clean=True` or `dict(mic, declip, dereverb, eq)`): optional de-clipping, two-mic WPE, then DeepFilterNet3.
    WPE runs only when the channels really differ: on identical channels it cancelled a take to −61 LUFS, and the
    example's identical channels are skipped with a note;
  - eq: each cleaned voice measured against one speech target (a smooth correction capped at −8 / +6 dB, a gain to
    −21 LUFS). The cut's chain becomes that EQ, an expander, a de-esser, compression and −19 LUFS, so different mics sit
    together.
- **cut** (cut.py, from films/ai-workflows, reverse-engineer and xchakra edl.py):
  - the gate: kit.cut.cutcheck on KEEP before any media (FAIL or an unjudged REVIEW stops it, exit 3);
  - words with TIME_FIX / START_FIX / END_FIX (the aligner drifts up to 1 s; the example's "The" was stretched over a 1.2 s
    pause);
  - edges in real quiet on the cleaned voice (kit/cut/edges.py): consecutive words lose only the quiet between them or stay
    continuous; a pause over MAX_GAP inside a range becomes a SLIVER;
  - the frame grid: a piece starts on a frame and lasts whole output frames at its speed;
  - the picture per piece: `-ss` a quarter frame early, then `fps=FPS:round=down,trim=end_frame=n`. That handles
    Framecast's 0.02 s offset and the 4-decimal rounding that skipped a frame on every piece starting at frame 2 mod 3.
    The source plays on through the pause after a piece; black where a track has nothing. HOLD_GAP = {tags} (or True)
    holds a scene's last frame to the next scene and through the tail instead: a screen recording plays on into
    whatever was on his screen next (kit-v10-sample: the CEO video's next caption, the recorder's UI);
  - the voice cut once at the measured edges, half-sine fades, none inside a continuous run. `VOICE_MUTE = [(source,
    from, to)]` silences a span of a take's voice (5 ms ramps) before it is cut: a click or lip smack just before a word,
    with no edge moved (chakra-interview: a −3 dBFS click 0.09 s before his first "So");
  - ROOM_TONE (dB, 0.0 = as in the take): each source's quietest 0.8 s with no word, looped under its own stretches.
    DeepFilterNet leaves digital silence in the pauses (the example: 175 windows down to −118 dB); with it, the
    quietest window in vo.wav is −76 dB;
  - YuNet faces per piece. Every track is checked for its exact frame count.
  - **Track sizes and the zoom budget (v11).** `TRACK_SIZE = {track: (w, h) | "native"}`: "native" keeps the largest
    picture its sources' vf give (a 4K selfie stays 3840 x 2160: write the vf without a scale), so the lens has room on
    him. `TRACK_SHOW = {track: page px}` is the tallest the page shows that track (default the page height). The cut
    then writes **work/tracks.json**: per track `{w, h, src_w, src_h, render_scale, ref_px, sharp_px, max_zoom,
    soft_zoom, soft, kinds}`, where `sharp_px` is the page height up to which a source pixel still backs every render
    pixel, `max_zoom` = max(1, sharp_px / ref_px) (any shape S px tall: max(1, sharp_px / S)), `soft_zoom` the
    allowance with mild softness, and `kinds` the same per view kind with its share of the timeline (the track-level
    fields are its poorest kind). Each Reel writes its own for its 1080 x 1920 page.
- **grade** (grade.py, from films/ai-workflows/grade_cut.py): look v2 on `work/<track>.mp4` → `<track>_graded.mp4`
  (same frames, checked):
  - one shot per take and view kind, so each gets its own balance; the face track is the cut's own;
  - his room stays as shot by default (OWNER_DEFAULTS §2): vignette 0 through `GRADE_V2_SET` (kit/look/v2.py), and no
    matte. `matte=True`, a vignette or `set="bg_stops=-0.5"` are opt-ins;
  - **kinds and regions (v11):** `kinds={view kind: look | None}`: None passes a kind through as recorded (a screen
    recording stays crisp and neutral), a name grades it in its own look (`cam="clean"`); the key `None` is the
    track's black stretches (where it shows nothing: chakra-interview's face track is black for 59 % of the film,
    `kinds={"screen": None, None: None}` passes them through and the 4K grade took a third of the time); `regions={kind: [x, y, w,
    h]}` grades only that rectangle (a screen recorder's cam bubble), on each GRADE track whose frame holds it;
  - **the A/B (v11):** `grade --sheet=8,30,120` grades those frames in the film's look and in "clean" side by side,
    each drawn the way the white page shows him (a card and a circle on white), with the scopes under every tile;
    nothing is graded for the film. "clean" is offered, never imposed (OWNER_DEFAULTS §8);
  - **complete or absent (v11):** a grade writes `<track>_graded.mp4.part` and renames it only when every frame of the
    cut is in it, then writes `<track>_graded.mp4.ok` (what it was graded from and the settings it was asked for). Build
    and reels use a graded track only while that record matches the cut and GRADE as they are now (a NOTE otherwise:
    they use the cut), so a changed GRADE re-grades on the next `grade` with no `--force`. `render` refuses a missing,
    stale, short or differently-graded track while GRADE is set (`--force` to override). A grade from before settings
    were recorded is compared on its looks only, so an unchanged film is never re-graded for the upgrade
    (films/ai-video-editor shipped a frozen 7 s tail from a short grade before this rule).
- **joins**: the envelope audit (an edge inside a sound), then `kit.cut.relisten` on vo.wav (what was meant vs what
  whisper hears at each join). Fix with TIME_FIX / IN_AT / OUT_AT and cut again.
- **build** (build.py):
  - vendor.inline and the data: `D = { total, talk, pieces, words, caps, tracks, lens, music?, faces?, ...DATA }`, plus
    `__TOTAL__`, `__TALK__` and `__END-<s>__`;
  - `D.tracks[name]` is an object: `{ file: "assets/<name>.mp4", w, h, src_w, src_h, render_scale, ref_px, sharp_px,
    max_zoom, soft_zoom, soft, kinds }` (the file plus its work/tracks.json entry; just `{ file }` without one). The
    lens reads its zoom budget there, and precheck's upscale gate checks against it;
  - `D.lens = { on, track: FACE_TRACK, fps, stress, plan, faces, faces_px, calm?, budget?, rules? }`: the camera on him
    (kit/hf/README "The lens"). `LENS` sets it (`False` off, a dict on with those options: `calm`, `budget` "sharp" |
    "soft" | a number, `rules`; unset: by the film's date, above); `STRESS` word ids plus the plan's `"cam": "punch"`
    passages are its punch candidates. The canvas speaker whose id is `FACE_TRACK` (name the `<video id>` the same)
    and the HF.box of HF.studio / HF.reel pick it up;
  - the words as shown: RESPELL placed on its own sound (kit/cut/respell.py, never an even spread), then TEXT, then SPELL;
  - captions.srt (a sentence end, 42 characters, a 0.6 s pause or 3.2 s: CAPTIONS).
- **mix** (mix.py): MUSIC beds for kit/audio/mix.py. a / b / at can be seconds, `w<id>`, `tag:<tag>`, `end` or
  `end-<s>`. The music sits ~18 dB under the voice on a film (calm beds, no drops: OWNER_DEFAULTS §4) and ~12 dB on a Reel, and the page's cues and quiet moments come from `cues`. Read its
  WARNING and dropout lines.
  - **The music map** (2026-10-20): kit/music/beats.json (kit/audio/beats.py) holds every track's beats, downbeats
    and section starts with how much each one rises or falls. With it, a bed's `start` snaps to the nearest downbeat
    (no bed starts mid-bar; `snap=False` keeps it as typed); `drop="auto", at="w142"` lands the track's biggest rise on
    word 142 (`drop="section:2"` a given section), so nobody measures drops by hand; `end_on="track_end"` puts the
    track's own ending on the bed's end. Each bed prints how its start was chosen.
  - mix writes work/music.json: the beds' beats, downbeats and sections in film time, and its findings, which qa.py
    reports (MEDIUM): a bed entering off its downbeat, and a section change of 6 dB or more with no story sound near
    it (the music turns while nothing happens). build hands the same map to the page as D.music (HF.music).
  - A new track: `uv run --no-project --python 3.13 --with all-in-one-mlx==1.0.14 python -m kit.audio.beats --all`
    (~15 s a track, run it alone); `uv run python -m kit.audio.beats --check` lists what is missing.
  - **The v11 sound (2026-10-22; mix.py's docstring has the details).** Which sound a film mixes with: `SOUND = "v10"
    | "v11"` in film.py (or `sound=` in a REELS entry) wins; else the sound its last mix recorded in work/music.json
    (`"sound"`; a music.json without it is a v10 mix): **the gate is sticky**, so an edit or a copy of film.py never
    flips a film's sound between two mixes; else (never mixed) v11 for a film made from 2026-10-22 (above). On v11:
    - every bed ducks on his voice (`duck="voice"`): it sits at `under` (films −18, Reels −12) through the talk and
      lifts to `gap` (under + 6) only in pauses of 0.8 s or more (Reels 0.4 s); `carve=3` dips its 1.2-5 kHz band
      under speech (opt-in per bed);
    - a bed whose track runs out loops on its own phrases (kit/audio/loop.py; `loop=False` turns it off). The mix
      prints each seam's film time: **listen to every seam**. When no seam fits, a second long-form bed takes over
      with a 2 s crossfade;
    - a bed change on a film ends the outgoing bed on its own next downbeat with a 1.5 s equal-power crossfade
      (`xfade=` on the incoming bed overrides it); Reels keep a 0.2 s crossfade for their drops;
    - SFX families rotate within the budget: films at most 8 small cues a minute, Reels 12, no file over 25 % of the
      cues or 4 a minute; clips take the music down 19 dB;
    - the plan's music moments are played: "stop" becomes a quiet window over the passage's first sentence; on a Reel
      "riser" and "drop" are placed on the passage; long-form drops and risers are dropped (beds are calm).
    work/music.json then records `"sound"`, `"mix"` (the measured sound: under_db, lifts_per_min, up_db_s, down_db_s,
    sfx_per_min, small_per_min, top_file, top_share, variants, lra) and, per looped bed, its `segments` and `seams`.
    Its findings (qa.py `--music`, MEDIUM) add a long-form bed outside the library's `longform` list, one louder than
    −16 under the voice or more than 2 beds, a bed that runs out, music under speech more than 2 dB off the format's
    target and more than 3 lifts a minute.
- **draft / render / mux** (render.py): 1080p draft → qa.py; the 4K render through kit/hf/render4k.py (chunks, videos
  kept from streaming, a finished chunk skipped on a re-run; at 60 fps use `CHUNK = 15`, ~900 frames a chunk); `-aac_pns 0`.
  A Reel with `out_4k=` in its REELS entry renders again at 2x (2160x3840, render4k `--resolution=portrait-4k`) after its
  1080x1920 file. `ZOOM_CAP = 1.3` (film.py) caps every footage scale at x1.3 over the page's full-frame cover through
  tracks.json (sharp_px = cap x page height), accepting that upscale on a 4K render (who-gonna-hire's 4K60, 2026-10-23).
  At 60 fps a template that reads D.lens.faces (one per output frame) indexes it by D.lens.fps, never by 30.
- **reels** (reels.py, from films/xchakra/shorts/cut.py):
  - each Reel is the film's sentences by its word ids, lifted from the film's own voice, tracks and spelled words, and
    writes its own work/tracks.json for its 1080 x 1920 page;
  - edges at quiet points on the film's voice, on the frame grid;
  - split at the film's piece starts, so each sentence keeps the pause the film gave it;
  - audio placed by frame (1600 samples a frame at 30 fps), so the voice inside a Reel is the film's, sample for sample;
  - (2026-10-25, films/not-ai-made's Short) these REELS options:
    - `split=[id]` starts a new range at a word, so a held pause the film needed is cut down to its quiet points;
    - `hold={id: s}` adds a beat with no voice after a range, for a reveal the page covers;
    - `voice_fx=[(id0, id1, "af")]` runs an ffmpeg filter on one passage (a soft line in the take: a presence lift),
      crossfaded in and out over 40 ms.

## film.py (all defaults: config.py DEFAULTS)

```python
SOURCES = {1: dict(job="mytake-cam", file="~/Downloads/take1.mov", picture=True, clean=dict(dereverb=True), kind="cam"),
           2: dict(job="mytake-screen", base=2000, kind="screen", speed=1.0, tracks={"screen": ""},
                   views=[(0, 36.6, "screen"), (36.6, 41.0, "clip")])}                           # what the recording shows
SPEED = 1.06                       # his talk; a clip keeps its own timing (its source's speed=1.0)
GRADE = dict(look="natural", room="woodoffice")   # look v2 on the cut, the room as shot; or a light grade per track:
                                                  # tracks={"aroll": "eq=contrast=1.04:saturation=1.05"}
ROOM_TONE = 0.0
KEEP = [(2, 152, 155, "hook", 0.4, "copy"),     # a cold-open copy (ids + 10000)
        (1, 0, 93, "intro"), (1, 108, 119, "post"), ...]   # (src, first, last, tag[, gap s][, "copy"]); one source: (first, last, tag)
JUDGED = {(4027, 14387): "why the editor accepts this join, with the evidence"}
TIME_FIX = {(1, 100): (34.20, 34.35)}           # measured on the voice envelope; IN_AT / OUT_AT {edit id: source s} for hard edges
SPELL = {"Stryver": "Striver"}; TEXT = {855: "enter"}; RESPELL = {(1, 0, 27): "what he said, spelled right"}
MUSIC = [dict(file="tech/tech__max-brhon__ai.mp3", a=0, b="tag:part1", drop="auto", at="w12"),   # its drop on word 12
         dict(file="tech/tech__mixkit__brainiac.mp3", a="tag:part1", b="end", start=2.0, under=-12.5, gap=-6), ...]
REELS = {"a": dict(sentences=[(138, 155), (0, 17)], out="reel_a_<slug>.mp4", music=[...], end_at={254: 82.7})}
```

v11 settings (config.py has their comments): `TRACK_SIZE` / `TRACK_SHOW` (cut, above), `GRADE` with `kinds` / `regions`,
`LENS` and `STRESS` (the lens), `SOUND` and the beds' `duck`, `carve`, `loop`, `xfade` (mix), `AMBITION` (precheck).
A whitespace film's `film.py` carries: `TRACK_SIZE = {"face": "native"}`, `FACE_TRACK = "face"`,
`GRADE = dict(look="clean")` after the A/B, `STRESS`, `SOUND = "v11"` and one calm bed at `under=-18.0` with
`duck="voice"`.

The template reads `D.tracks[<track>].file` (`assets/<track>.mp4`: a static `<video id="aroll" src="assets/aroll.mp4"
data-start="0" data-duration="__TOTAL__" ...>`; name his `<video id>` after `FACE_TRACK`), `K.W(id)` for word times
and `K.span(tag)` for a KEEP tag's span. Each `D.tracks[name]` is an object, `{ file, w, h, src_w, src_h,
render_scale, ref_px, sharp_px, max_zoom, soft_zoom, soft, kinds }` (cut, above), not a path. A Reel's page uses
HF.reel with `src: [1920, 1080]` (the film's 16:9 track) and `faces: D.faces`.

## The example: kit/film/example

A check film, not an edit: ffmpeg's test pattern and a synthetic voice (macOS `say`) with a retake, an aside and a
pause for the cut to remove. It runs every step end to end in about 5 minutes (plus the 4K render):

```
uv run python kit/film/example/make_take.py && uv run python -m kit.film kit/film/example prep
uv run python -m kit.film kit/film/example cut && uv run python -m kit.film kit/film/example joins
uv run python -m kit.film kit/film/example draft                  # plan_check 0 errors, precheck 0 HIGH (exit 0), qa.py
uv run python -m kit.film kit/film/example grade
uv run python -m kit.film kit/film/example reels && uv run python -m kit.film kit/film/example/reels/a draft
uv run python -m kit.film kit/film/example render                 # the 4K film, mux, qa.py
```

Its film.py shows a cold-open copy, a retake left out, a TIME_FIX, a sliver, SPELL and RESPELL, a cleaned voice with
its measured EQ (and the WPE guard), room tone, a look v2 grade, one music bed and one Reel. `render` makes its 4K
film. Its template uses 8 registry components (sketch with its arrows, stickman, checklist, flow, code, numbered cards,
stamp) on HF.studio. Its scene plan is schema 2 (face, cam, groups, transition per passage) and passes plan_check,
and its film.py pins `LENS = {}`, `SOUND = "v11"` and `AMBITION = True`, so the smoke test runs the v11 lens, sound and
gates whatever day it is rebuilt (the example was made on 2026-10-20, before the v11 date gates). It is a pipeline
check on HF.studio, not a look: for the whitespace look start from `kit/presets/whitespace/templates/template.html`.
