# Fable-Directed Editor

**Drop in a talking-head recording, get back a video ready to post.** A local editor driven by
[Claude Code](https://claude.com/claude-code): it cuts the pauses and fillers without ever chopping a sentence, adds
word-by-word captions, motion graphics, music and a colour grade, then checks the result before you see it. It makes
9:16 shorts and reels, and 16:9 YouTube videos. Everything runs on your Mac: no cloud editor, no paid renderer.

## Quick start

On a Mac with Apple silicon:

```bash
xcode-select --install                                      # once, if you don't have the command line tools yet
git clone https://github.com/DhananjaySarathe/fable-directed-editor.git "fable-directed-editor"
cd "fable-directed-editor"
./setup.sh                                                  # about 20-30 min the first time: mostly downloads
echo 'export HYPERFRAMES_NO_UPDATE_CHECK=1' >> ~/.zshrc     # keeps the video renderer on its tested version
claude                                                      # opens Claude Code in this folder
```

Then ask Claude: *"Make a short from ~/Downloads/take.mp4"*. It shows you a plan and a sample, asks before the final
render, and puts the finished video in `output/final/<video>/`.

## What gets installed

**Install these yourself first** (`setup.sh` checks for them):

| What | Why it's needed | Where it goes | How to install | Size |
|---|---|---|---|---|
| Homebrew | installs the tools below | `/opt/homebrew` | the one-line command on [brew.sh](https://brew.sh) | varies |
| Xcode Command Line Tools | builds the two Apple Vision tools | `/Library/Developer/CommandLineTools` | `xcode-select --install` | 1.3 GB |
| Google Chrome | draws the graphics and renders the compositions | `/Applications` | [google.com/chrome](https://www.google.com/chrome/) | 720 MB |
| Claude Code | runs the editing | your user folder | [claude.com/claude-code](https://claude.com/claude-code) | |

**`./setup.sh` installs the rest** (safe to re-run; anything already there is skipped):

| What | Why it's needed | Where it goes | Command it runs | Size |
|---|---|---|---|---|
| ffmpeg | cutting, encoding, loudness, checks | `/opt/homebrew` | `brew install ffmpeg` | 770 MB with its libraries |
| whisper.cpp | speech to text | `/opt/homebrew` | `brew install whisper.cpp` | 6 MB (+150 MB shared libraries) |
| uv, node | run the Python and JavaScript parts | `/opt/homebrew` | `brew install uv node` | 120 MB |
| Python packages (OpenCV, ONNX Runtime, numpy...) | the editor itself | `.venv/` in this folder | `uv sync` | 540 MB |
| Node packages (Chrome driver, GSAP, rough.js) | graphics rendering | `node_modules/` in this folder | `npm install` | 60 MB |
| HyperFrames 0.8.134 | renders long-form compositions | the global npm folder | `npm install -g hyperframes@0.8.134` | 120 MB |
| Whisper large-v3-turbo (q5) | transcription | `kit/models/` | `uv run shorts setup` | 574 MB |
| SaT sentence model + tokenizer | finds sentence ends, so no cut lands mid-sentence | `kit/models/hf/` | `uv run shorts setup` | 421 MB |
| wav2vec2 aligner (int8) | word timings to about 30 ms | `kit/models/` | `uv run shorts setup` | 95 MB |
| Smart Turn, Silero VAD, YuNet | end of a thought, speech vs pause, face detection | `kit/models/` | `uv run shorts setup` | 11 MB |
| Apple Vision tools | person cut-outs, text on screen | `kit/bin/` | built by `uv run shorts setup` | under 1 MB |
| Music and sound effects | background tracks and hits | `kit/music/`, `kit/sfx/` | `uv run python kit/assets_src/fetch.py` | 240 MB |

In total: about **1.9 GB inside this folder**, plus up to about **3 GB of system tools** if you have none of them yet,
plus room for your footage and renders in `output/`. `uv run shorts doctor` checks that everything is in place. The
fonts (3.5 MB) come with the repo.

## What it does

- **Hear:** whisper.cpp transcribes, keeping fillers. A wav2vec2 aligner and the audio envelope give word times accurate to about 30 ms. Hindi is written as romanised Hinglish.
- **Look:** ffmpeg, OpenCV and Apple Vision find the face, blur and shot changes. Claude reads timecoded contact sheets.
- **Decide:** the editing questions (false starts, fillers, pauses, retakes, zoom-ins) are answered by Claude. Cuts land only in silence, and a checker refuses any edit that chops a sentence or splices two half-sentences.
- **Graphics:** a HyperFrames component kit (`kit/hf/`): a speaker camera with a director, diagrams, screen demos, code, kinetic type with springs, sketch and collage styles, a stick-figure rig, and the Reel scene library (`kit/hf/reel.js`). The older template library in `kit/graphics/` is kept as the fallback list `kit/hf/plan_check.py` checks against.
- **Look and sound:** a face-aware colour grade, the speaker cut out for words-behind-head shots, a music and sound-effect library, mastered to −14 LUFS.
- **Check:** the final file is checked for size, frame rate, duration, loudness, true peak, black or frozen picture and cropped sentences, then a fresh Claude critic reviews it.

Why `HYPERFRAMES_NO_UPDATE_CHECK=1`: HyperFrames otherwise upgrades itself in the background, even mid-render, which
crashes that render and breaks the tested version. Claude Code runs in this folder already get it from
`.claude/settings.json`. To move to a newer HyperFrames on purpose, change `HYPERFRAMES_VERSION` in `shorts/config.py`
and re-run `./setup.sh`.

## Claude Code cloud sessions (Linux)

`cloud-setup.sh` is the Linux counterpart of `setup.sh`. The `SessionStart` hook in `.claude/settings.json` runs it
automatically in cloud sessions (only when `CLAUDE_CODE_REMOTE=true`, so it never fires on a Mac). Leave the cloud
environment's own setup script empty. Its output goes to `/tmp/cloud-setup.log`.

A cloud session can edit code, run the tests and build graphics. Grading, person cut-outs, OCR boxes and full renders
need macOS (Apple Vision, Chrome in `/Applications`), so they stay on the Mac. The speech and face models are skipped by
default. Run `CLOUD_MODELS=1 ./cloud-setup.sh` to download them (needs Full network access). Cloud sessions clone
from GitHub, so a push is all it takes to update them.

## The director and its helpers

Every edit runs the same way (the `fable-director` skill, `.claude/skills/fable-director/SKILL.md`):

- **One director session.** The Claude Code session you talk to plans the edit and designs everything a viewer sees
  or hears: what to keep, the hook, each scene, the zooms, the type and the sound. `.claude/settings.json` starts it on
  Fable 5.2 at high effort.
- **Five helper agents** (`.claude/agents/`). The director starts them for the work that does not need it:

| Agent | What it does | Model |
|---|---|---|
| `reference-analyst` | studies a reference video you share and writes its style spec | Fable 5.2 |
| `edit-critic` | reviews a rendered draft with fresh eyes, a new one each round | Fable 5.2 |
| `fact-scout` | checks the facts and captures the real pages and logos an edit shows | Sonnet 5.5 |
| `edit-builder` | applies an exact fix list and runs its checks | Sonnet 5.5 |
| `qa-reader` | runs the text checks and reads their reports and render logs | Haiku 5.5 |

Renders, grades and transcription are shell commands on your Mac and use no model.

**What you need:** Claude Code signed in with a Claude Pro or Max plan. A full edit is a long session with several
agents, and how many edits fit before a plan's usage limit depends on the plan. If your plan does not offer one of
these models, change `model` in `.claude/settings.json` and the `model:` line of that agent's file in
`.claude/agents/`; the roles stay the same.

**What an edit cost:**

```bash
uv run python kit/cost.py              # this project's sessions, newest first, per model
uv run python kit/cost.py --limit=1    # the latest session only
```

It reads Claude Code's own session logs and prices the tokens at Anthropic's API list prices, per model, with where
they went (re-reading the conversation, new context, output). On a plan you are not billed these dollars: they show
which model and which part of a session used the most.

**Matching a reference:** share a video and say "edit it like this". `kit/refs/breakdown.py` measures its cuts, zooms,
captions and beat from the frames and the audio, and `kit/refs/compare.py` puts your draft beside it. They are
measurements to steer the edit by; judge the result by eye.

## Use

Open this folder in Claude Code and ask, for example:

> Make a short from ~/Downloads/take.mp4

> Edit ~/Movies/talk.mov into a YouTube video with graphics, preset paper studio

The `fable-director` skill (`.claude/skills/fable-director/SKILL.md`) runs the edit, with the `video-shorts` skill as
the kit's manual: it shows you a plan and a sample, and asks before the final render. The finished files land in
`output/final/<video>/`.

Every edit starts by copying the take in and transcribing it:

```bash
uv run shorts probe ~/Downloads/take.mp4 --job take1    # output/jobs/take1/source.mp4 + probe.json
uv run shorts analyze take1                             # analysis.json: words, sentences, pauses, face, loudness
```

Then a Reel follows `kit/reel/README.md` (`uv run python -m kit.reel films/<name> prep|edl|joins|sample|render`), and a
long-form film follows `kit/film/README.md` (`uv run python -m kit.film films/<name> prep|cut|joins|grade|build|draft|render`)
with the look's README in `kit/presets/`.

## Where files go

Everything the pipeline generates lands in `output/` (git-ignored), never in `films/` or `kit/`:

| Folder | What | Keep? |
|---|---|---|
| `output/final/<video>/` | the video(s) to upload, `captions.srt`, posting notes, the final contact sheet | yes |
| `output/jobs/<take>/` | one recorded take: `source.mp4` (the footage copy), `probe.json`, `analysis.json` (transcript) | while you might re-edit it |
| `output/music_usage.json` | which track each video used, so the next videos don't repeat it | yes |
| `output/temp/` | everything else: audio extracts, whisper output, face tracks, graphics frames, previews, cut A-roll, grades, mixes, raw renders, snapshots, one-off scripts, caches | **delete any time** |

```bash
uv run shorts clean --dry-run   # what would go, and how big it is
uv run shorts clean             # delete all of output/temp
uv run shorts clean take1       # only one take's (or film's) temp files
```

Deleting `output/temp` loses nothing you need: re-running a step rebuilds what it made. `films/<video>/` keeps only a
film's recipe (edl.py, build.py, the template, edl.json and its screenshots). Film scripts find every folder through
`kit/paths.py` (`F = Film(__file__)`); run them with `uv run python`.

## Make it yours

The repo ships its author's look and identity in a few places. Change these before your first long-form video:

- **Name and handle** in the long-form preset: the lower third and end card in `kit/presets/paper_studio/templates/longform.html` and `templates/reel.html`, and the showcase (`kit/hf/showcase/src/template.html`).
- **Design tokens** (palette, fonts, motion): `kit/presets/paper_studio/preset.json` and `kit/hf/paper.css`.
- **Your handles** for end cards: `kit/brand.json` (it ships with placeholders).
- **Your taste:** `kit/refs/OWNER_DEFAULTS.md` holds the standing rules every edit follows (pace, zooms, layouts,
  sound levels, what needs your yes). They are the author's defaults: edit the file, or tell Claude a preference and
  ask it to write it there.
- **Your films** go in `films/<video>/`, one folder per video. `kit/film/example/` is a complete small film on a
  generated take: run its commands once to see every step work before your first real edit.

Claude Code builds up its own memory of your preferences as you edit.

## Music and sound effects

The music and the downloaded sound effects are not in this repository: their licences (NCS, Mixkit and others) don't
allow passing them on. (The 13 basic sounds in `kit/sfx/` itself were synthesised by this project and are included.)
`./setup.sh` downloads each track from its source (`kit/assets_src/fetch.py`, listed in `kit/music/library.json` and
`kit/sfx/library.json`; about 10 minutes the first time); a few tracks have no public download and are simply skipped. Credits are in
`kit/music/CREDITS.md`: paste the block into your video description when a track asks for one. Add your own tracks to
`kit/music/<mood>/` and `kit/music/library.json`.

## Licences of what's bundled or downloaded

- **Fonts** (`kit/fonts/`, in the repo): all under the SIL Open Font License 1.1, which allows sharing them with their
  licence; each family's licence text is in `kit/fonts/licenses/`.
- **Models**: not in the repo. `uv run shorts setup` downloads them from their official sources, each under its own
  permissive licence (MIT, Apache-2.0 or BSD).
- **Music and sound effects**: not in the repo (see above). You download them from their sources yourself, and the
  track's own terms apply to your videos: credit NCS tracks as `kit/music/CREDITS.md` shows.
- **Python and npm packages**: installed from PyPI and npm under their own licences.

## Tests

```bash
uv run pytest            # unit and slow media tests
uv run pytest kit/cut    # the cut checker's unit tests
```
