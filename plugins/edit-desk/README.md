# edit-desk

A Claude Code plugin for the Fable-Directed Editor repo: its standing rules enforced, long steps announced, each video's API cost
tracked, and a live desk above the prompt.

## Turn it on and off

The repo is its own plugin marketplace (`.claude-plugin/marketplace.json` at the root lists this folder). In a terminal:

```bash
claude plugin enable edit-desk@video-shorts
```

```bash
claude plugin disable edit-desk@video-shorts
```

It applies to sessions started after the change. On a new Mac, add and install it once first:

```bash
claude plugin marketplace add "<path to the repo>"
```

```bash
claude plugin install edit-desk@video-shorts
```

From GitHub instead, at the prompt of a terminal session: `/plugin install edit-desk --marketplace DhananjaySarathe/fable-directed-editor`.

Installing copies the plugin into Claude Code's plugin cache, so after editing it bump `version` in
`.claude-plugin/plugin.json`, run `claude plugin marketplace update video-shorts` and
`claude plugin update edit-desk@video-shorts`, then `/reload-plugins` (or start a new session).

## What it does

**The desk** (above the prompt, terminal and desktop)
- One line: `🎬 <video> $<cost>` · `ctx <context used>%` · `5h <5-hour limit used>%` · `⏳ <running step> <elapsed>` · the
  last alert.
- Buttons: 1 Track / switch video (a name field), 2 Costs, 3 QA, 4 Details (a pane), 5 Stop tracking, 6 Hide / Show.
- `/desk` brings it back; `/film start <name>`, `/film cost`, `/film end` do the same from the prompt.

**The details pane** (right side; Simple / Detailed at its top, and it reopens the way you left it)
- Simple: the summary (now, cost per video, QA verdicts, recent alerts).
- Detailed: one film or take, picked from a list (films and takes under `output/`, newest first):
  - Latest video: a thumbnail, size, length, age; Play, Reveal, Frames (the QA contact sheet), Upload copy.
  - Pipeline: each stage read off the file it writes (film: take → grade → A-roll → join audit → mix → render → final →
    QA → sent; take: analysis → brief → decisions → edit → visuals → render → check → sent). A stage is stale when an
    earlier one, or its inputs (`edl.json`, `build.py`, `src/template.html`), changed after it. The running step shows
    elapsed time against the median of its last five runs.
  - QA: the verdict and each finding with its timecode (`review/qa.json` or `check.json`, plus the join audit's
    non-PASS joins). Run QA ↗ and Fix findings ↗ send Claude a prompt.
  - Cost: the film's total split by stage (approximate: a turn's cost goes to the step it ran, else the film's last
    step), cost per finished minute, the average film.
  - Thumbnails: Thumbnail kit ↗ asks Claude for a ChatGPT thumbnail kit (`kit/thumbs/THUMBNAILS.md`): researched
    concepts (three 16:9 for Test & Compare, or one 9:16 reel cover), face frames of you from the video plus any photos
    in `kit/refs/me/`. Then Copy GPT prompt, Show photos (to attach), Notes, Redo kit ↗. A kit made before the latest
    final file is flagged.
  - Limits: context and the 5-hour limit as bars.
  - Controls: sound on/off, the QA gate on/off, track this film, stop tracking, refresh.
- Thumbnails are cached in `output/temp/edit-desk/` (ffmpeg and ffprobe from PATH or Homebrew).

**Guardrails**
- Every `hyperframes` command runs with `HYPERFRAMES_NO_UPDATE_CHECK=1` (the CLI otherwise updates itself mid-render).
- Nothing reads, prints, edits or commits a `.env` file (shell, Read, Edit, Write). `.env.example` and its kin are fine.
- A video whose last QA run failed (`kit/qa/qa.py` FAIL) is never sent to you. A video
  sent with no QA run, or changed since its last one, goes through with a toast saying so.

**Render alerts**
- While a long step runs (render, grade, prep, mix, cut, QA) the desk and status line show `⏳ <step>`.
- When it ends: a toast (`✅ render (haiku-vs-opus) done in 1m14s`, or `❌ … failed`) and a sound, for foreground steps
  over 30 s and for every background one. A background QA run that printed FAIL counts as failed.

**Cost per video**
- Tracking starts with the Track button or `/film start <name>`; a pipeline command on a film or take
  (`films/<name>/build.py`, `shorts analyze <job>`) starts it on its own when nothing is tracked.
- Totals carry across sessions. The cost is what Claude Code's own `/cost` totals: API list prices for the tokens used,
  not your subscription bill.

## Files
- `hooks/register.tsx`: the hooks, the desk and the pane. `hooks/lib.ts`: parsing, pure functions. `hooks/film.ts`: the
  detailed view's stages, reports and cost split, pure. `types/index.d.ts`: the state contract.
- `tests/`: `claude plugin test plugins/edit-desk`.
- `assets/done.wav`, `assets/fail.wav`: the alert sounds. They are not in this copy (Mixkit's licence): put two short sounds of your own under these names, or leave them out and the toast alone is shown.
