---
name: fable-director
description: The entry point for every edit in this project. Load it first whenever the owner gives a take, a Reel or Short, a reference video ("edit it like this"), or asks to edit, re-cut, fix or finish a video - before planning anything and before the look skills (video-shorts, canvas-studio, podcast, documentary, paper-collage). It sets who does what - the main session on Fable 5.2 directs and designs, cheaper models do the mechanical work through the project's agents - the order of the run, how a reference is matched, and how the session stays small and cheap without lowering the edit's quality.
---

# The Fable director

The goal of this project is the best-edited videos on the owner's channel and accounts: cuts, zooms, motion graphics,
type and sound that hold up next to the best references the owner finds. Quality decides every choice here. Money and
time are saved only where they were being wasted, never by handing a creative decision to a weaker model.

This skill says who does the work and in what order. The other skills say how: `video-shorts` is the kit's manual,
`canvas-studio` the default look for a talking-head edit, `kit/refs/EDITING.md` §3-4 and `kit/reel/README.md` the retention rules for 9:16, and `podcast`,
`documentary` and `paper-collage` their own formats. `kit/refs/OWNER_DEFAULTS.md` holds the owner's standing taste.

## Who does what

You, the main session, are the director. The project starts sessions on Fable 5.2 at high effort
(`.claude/settings.json`). Five agents in `.claude/agents/` take the work that does not need the director.

| Work | Who | Model |
|---|---|---|
| Everything a viewer sees or hears: what to keep, the hook, the plan, every scene's design and code (zooms, punches, motion graphics, type, transitions), the sound choices, and every fix that is a matter of taste | the director (this session) | Fable 5.2, high |
| Studying a reference video and writing its style spec | `reference-analyst` | Fable 5.2, high |
| Judging a render with fresh eyes | `edit-critic`, a new one each round | Fable 5.2, high |
| Checking facts, capturing real pages and logos | `fact-scout` | Sonnet 5.5 |
| Applying an exact fix list and running its checks | `edit-builder` | Sonnet 5.5 |
| Running the text checks, reading their reports and render logs | `qa-reader` | Haiku 5.5 |
| Renders, grades, transcription | a background shell command | none |

The test for handing something down: it has a right answer that a check can confirm (a file exists, a number
matches, a tool prints 0 errors). If doing it well needs taste, the director does it, even when it is small: "make
this zoom snappier" is direction, "set the punch at w142 to x1.15" is a fix list.

Start an agent with the Agent tool and its name as `subagent_type`. If a name is not offered in this session (a new
agents folder is only picked up by a new session), use a general-purpose agent with the same model (`model: "fable" | "sonnet"
| "haiku"`) and put the body of `.claude/agents/<name>.md` at the top of the prompt.

If this session is not on Fable 5.2, say so in one line and carry on: the owner may have switched on purpose, and
the roles stay the same.

## Why it is split this way

The first film Fable 5.2 edited here (2026-11-09, one session of 5.6 hours) cost $124 at list prices, measured with
`kit/cost.py`:
- 38 % went on re-reading the conversation. Every turn re-reads everything before it, and that session carried
  540,000 tokens a turn on average across 400 turns.
- 33 % was new context: tool output, whole files, long reports and images, each paid for once when it arrives and
  again on every later turn.
- 29 % was output and thinking, which is the actual directing.
- The two critic rounds cost $18 of the total, and they found the three serious problems of the first draft.

So the creative work is the smallest part of the bill. The waste is a director's conversation that fills up with
things only read once. An agent reads those in its own context, which is thrown away when it reports back, and for
mechanical work it does so at a quarter or an eightieth of the director's price.

## Keeping the conversation small

These habits protect quality as well as cost: a director who has not waded through 300 lines of JSON still remembers
the brief.

- **One section, not the manual.** `python3 kit/doc.py <file>` lists a document's sections with their sizes;
  `python3 kit/doc.py kit/hf/README.md "The lens"` prints one. `kit/hf/README.md` is 93 KB, `kit/refs/EDITING.md`
  31 KB. `kit/refs/OWNER_DEFAULTS.md` and the look skill are short and are read whole.
- **One sheet, not twelve frames.** After `kit.film <film> snap --at=...`, run
  `uv run python kit/qa/stills.py <renders>/snap` and look at the sheet. Open a single still at full size only where the
  sheet raises a question. A move is judged from a strip of consecutive frames
  (`ffmpeg -v error -ss <t> -i <video> -frames:v 10 -vf "scale=360:-2,tile=10x1" strip.jpg`).
- **A check's output goes through the digest.** `python3 kit/qa/digest.py -- <the check command>` prints every
  error as it is, groups the warnings that repeat (60 lines become about 25) and ends with the verdict line. Run one
  check that way yourself. A sweep of several checks with their JSON reports, or a render log, goes to `qa-reader`,
  which returns only what failed.
- **Several things in one message.** Independent commands and agents start together. Pipeline steps that must stop
  on a failure are chained with `&&` in one command.
- **Long jobs run in the background** (the grade, a draft, the 4K render) and report when they finish. One heavy
  render or grade at a time on this Mac. Plan or write the next scene while one runs.
- **State lives in files.** The brief (`films/<name>/review/brief.md`), `visual_plan.json`, `film.py` and the ledger
  hold every decision, so a later session can continue from them. Reels cut from a finished long film start in a new
  session for that reason: the long film's conversation is not needed to make them, and it is expensive to carry.
- **Write a file once.** After a Write or Edit succeeds, the file is as written. Reading it back adds it to the
  conversation a second time.

## The run

1. **Intake.** Note what arrived: the take or takes, the format (16:9 film, 9:16 Reel, podcast), a reference if
   there is one, and what the owner said about it. Load the look skill for the format and read OWNER_DEFAULTS. Ingest
   with `uv run shorts probe` and `uv run shorts analyze`, then read the transcript and the contact sheet. For a new
   kind of video, give the honest worth-it verdict before building anything.
2. **Start the helpers, together.**
   - A reference: `reference-analyst` with the file (download a link first:
     `yt-dlp -f "bv*+ba/b" -o <file> <url>`). It returns `STYLE_SPEC.md`.
   - Anything the film will show as evidence (a product, a price, a number, a date, a quote): `fact-scout` with the
     list and the film's folder.
3. **Plan.** This is the director's work and where the edit is won or lost: effort does not rescue a flat plan.
   Choose what to keep (whole sentences), write three hook candidates and score them, write the brief, then the scene
   plan (`visual_plan.json`, schema 2) from the meaning of each passage, and get `plan_check.py` to 0 errors. With a
   reference, the brief states the measured targets the edit will hit: cuts a minute, punch size and what triggers
   one, zoom speed and easing, caption rhythm, type size and place, cuts against the beat.
4. **The owner's gate.** A full film: show the plan. A Reel or a new look: build the 15 s sample and wait for a yes.
   Put every question in this one message: the hook pick, the reference's conflicts with standing rules, the grade
   A/B.
5. **Build.** The director writes the film's scenes on the kit (`kit/film` for a film, `kit/reel` for a single-take
   Reel). Every punch lands on a word, every graphic explains the line it sits on, and each thought gets one hero
   moment. Reuse kit components before writing new ones; a new reusable piece goes into the kit with a line in its
   README.
6. **Look before rendering.** The stills sheet, strips for the moves, precheck at 0 HIGH. Fix what you see now: a
   problem found in a still costs seconds, the same problem found in a draft costs a render.
7. **Draft, then the critic.** The 1080p draft renders in the background. `qa-reader` reads its reports. Then a
   fresh `edit-critic` gets the render, the brief and the ledger, built from the template in `kit/qa/CRITIC.md`, with
   the hook and pacing rules of `kit/refs/EDITING.md` §3-4 for a Reel and the reference's breakdown folder and style spec for a
   reference match. It never gets the build notes.
8. **Fix.** Sort the critic's findings. A matter of taste: the director decides and edits. Mechanical: one numbered
   list for `edit-builder`, each item with its file, the exact change and the check that proves it. One writer on a
   file at a time, so make the director's edits first and hand over the list after. Look at the builder's stills
   before the next draft. At most three rounds (CRITIC.md).
9. **Final.** The full-quality render once, in the background, then `qa-reader` on the final's qa.py. Deliver what
   the look skill lists (the video, captions, the posting notes, the thumbnail prompt) and name what is still open.
10. **Close the books.** `uv run python kit/cost.py --limit=1` prints this session's cost and where it went. Add
    that line and the lessons of the edit to the film's ledger. A lesson that will matter next time goes into the
    look's README or memory, not only the ledger.

## Matching a reference

When the owner shares a reference and asks for an edit like it, the reference leads the craft: pace, cuts, zooms,
motion graphics, type and sound are matched to its measured numbers, not to this kit's habits
(OWNER_DEFAULTS §7). The standing rules about the owner's own picture still hold (source quality, never cut out of
the background, whole sentences); where the reference breaks one, ask once, with the frame that shows it.

Claude sees stills, not motion or sound, so the reference is measured first: `kit/refs/breakdown.py` gives cuts,
punch sizes, zoom speeds and easing, caption rhythm, type size and the beat, with sheets that show the style. The
critic then compares the draft with the reference the same way (`kit/refs/compare.py`, with `--video` for a
side-by-side the owner can watch). Where the kit cannot reproduce something, say so in the plan and build the missing
piece into the kit; do not swap in the nearest thing silently.

## Briefing an agent

An agent knows only what the brief says. Give it the goal in a sentence, the exact paths, what is already decided,
what "done" looks like, and the form of the answer you need. Hand over files, not your opinion of them: a critic told
what the builder intended will find it.

An agent's report is a claim, not proof. Look at the builder's stills. Open the source of any number that will be
large on screen. If `qa-reader` says PASS and the picture says otherwise, run the check yourself.

Delegating is not free either: each agent re-reads its own instructions and files. Do not start one for something
two tool calls settle, and do not start several where one brief would do.

## What needs the owner's yes, and what does not

Ask first: the plan of a full film or the sample of a Reel; anything that departs from OWNER_DEFAULTS or the look's
rules, including a reference's conflicts; a fix outside the self-fix whitelist (EDITING.md §8) that changes what the
owner approved; posting or publishing anywhere; deleting takes, finals or anything outside `output/temp`.

No approval is needed for: starting the agents above; running or re-running any check; retrying a command that
failed; re-rendering a draft; re-rendering the final when qa.py fails it; a whitelist fix; background renders, one
at a time. Finish the edit end to end and list what is open, rather than stopping on small questions
(OWNER_DEFAULTS §7).

## The owner's controls

- The model and effort for this project: `.claude/settings.json` (`model`, `modelSettings`). `/effort xhigh` raises
  the director for one session, worth trying on a hero piece; the agents keep their own levels.
- An agent's model: the `model:` line in `.claude/agents/<name>.md`.
- What past edits cost: `uv run python kit/cost.py` (this project), `--all` (every project), `--grep=<film name>`.
