# kit/reel: the Reel engine (9:16, pastel-box grammar)

Built 2026-10-10 while editing films/youtube-audit and films/social-media-automation. Before it, every Reel copied ~700
lines of edl/prep/build code from the last film and hand-wrote a 300-900 line template. Now a Reel is:

```
films/<name>/reel.py            settings + TRANSCRIPT fixes + KEEP (whole sentences) + MUSIC + DATA  (~60-90 lines)
films/<name>/src/template.html  the scenes, timed to word ids, on HF.reel (kit/hf/reel.js)          (~250-330 lines)
films/<name>/assets/            screenshots (blurred / cropped copies only), stills
```

## The run

```
uv run shorts probe <take.mp4> --job <name> && uv run shorts analyze <name>      # words (check punctuation!)
uv run python -m kit.reel films/<name> prep          # CFR, face track, matte, WPE+DeepFilter voice, look v2 grade (~6 min)
uv run python -m kit.reel films/<name> transcript     # only when reel.py has TRANSCRIPT (punctuation, names, mishears)
uv run python -m kit.reel films/<name> edl            # cutcheck gate -> edl.json, vo.wav, aroll.mp4
uv run python -m kit.reel films/<name> joins          # voice-cut audit + whisper re-listen. Exit 3 = fix before picture
uv run python -m kit.reel films/<name> sample         # hf_sample/ (first SAMPLE s) ; then `render --sample`
uv run python -c "from kit.reel.config import Reel; from kit.reel import build; R=Reel('films/<name>'); build.build(R); build.cues(R); build.snap(R, [t1, t2, ...])"
uv run python -m kit.reel films/<name> render         # lint, cues, precheck (stops on HIGH; --force), mix, render, mux, qa --holds
```
`HF_WORKERS=2` before `render` caps the Chrome workers when a grade or another render shares the Mac.
A Reel cut from a finished long film (its voice, grade and words) instead of a take: `uv run python -m kit.film films/<name> reels` (kit/film/README.md).
Prep grades with GRADE_PRESET=veryfast (an intermediate). To re-cut an existing A-roll and its mattes to a new frame
map without re-grading, see kit/cut/recut.py. A 50-60 s Reel renders in ~2 min at 1080x1920 (delivery). The music alone: `build.mix(R); build.mux(R)` (no re-render).

## reel.py fields (kit/reel/config.py has all defaults)
TAKE, ROOM, SPEED (1.06 for chatty takes), TRANSCRIPT [((a, b), "words, caption|spoken")], TIME_FIX, KEEP
[(first id, last id, tag)], JUDGED {(left, right): why}, START_FIX / END_FIX {id: s} (from `joins`), GAP_AFTER
{last id: s}, VOICE_GAIN {tag: dB} (lifts a quieter voice, e.g. someone off camera; measure on vo.wav: the clean chain's compressor and
loudnorm already lift a quiet voice a lot), ROOM_TONE (dB vs natural: the take's room tone looped under
vo.wav; the cleaned voice leaves digital silence in every pause, which the mixer flags as dropout RUNS), CUTOUT_REFINE (the cut-out's edge
re-cut on the picture and recoloured from him: no white halo when a bright room goes onto a dark background), OPEN_HOLD (frames: hold the first
open-eyed frame over a blink on frame 1), BG_DULL (the CUTOUTS WebM keeps his own room, dulled and fading
to black at the frame's top and sides: he stays attached to his room instead of a pasted cut-out), SLIVER_AT {id: s}, NOTRIM {ids} (never trim the pause before these: a trim on a full face is a visible
jump), SAMPLE, OUT, MUSIC [dict(file, a, b, drop, at, gap, under)] with a/b/at as seconds, "w<id>", "end" or "end-<s>", DATA {...} -> D.

## Voice cuts: the owner's rule ("if you are saying something, make sure it's completely said")
`joins` measures every piece edge on the 10 ms voice envelope: CLIP-TAIL / CLIP-HEAD (the word's sound runs past the cut;
it prints the END_FIX/START_FIX to use), EXTRA-TAIL/HEAD (a neighbour's syllable leaks in), HOT-CUT (the cut sits on
loud voice). Where two words run together with no valley ("uh I", "say You-", "it's, it's"), keep the words: a small
filler beats a chopped word. The voice is cut at exact measured times (va/vb), the picture on frames.
Aligner word ends are often 50-100 ms early on the last syllable ("some-thing" ran 0.11 s past its end time).

**Hesitations (2026-10-10, the owner: "places where I am thinking and fluctuating, you have not even trimmed them"):**
`MAX_GAP 0.10` + `SLIVER 0.04` cut every quiet pause inside a sentence; a gap with sound in it (a hum, a drawl, a mumbled
fragment) is never "quiet", so list the next word in `TRIM` and measure the edges (END_FIX / START_FIX) on the voice
envelope at 10 ms, checked with a filler-aware whisper pass; sentence starts get `SLIVER_AT` ~0.10 so it doesn't feel
breathless. Re-print the word list after every edl run before planning times (a stale list put a whole plan 1.3 s off).

## Page kit: HF.reel (kit/hf/reel.js)
World (aurora, grain, progress bar), layers BACK/FRONT/CAPS/TOP, the speaker box (HF.box 9:16 slots; the small slot is
raised so his face clears Instagram's caption zone), `say` (his words, serif, on their spoken time), `line`, `strike`,
`fromPill` (a card grows out of the collapse), `beat(t, show, {side, card, section})`, `captions` (every word say() did
not show; fillers never; a page clears when the serif takes over), and scenes `S.sc`: ideaCards (lock/unlock), prompt,
connect, scanGrid, week, clock, notif (scale), shot, toolPair (light), bars, slam (full-frame hero hit). `S.ui` = the
studio_ui cards (checklist, chat, stamp, pointer, thinking...).

## What the critics taught (2026-10-10, three rounds on Reel A) - plan for these from the start
1. **Layout share**: "graphic on top + face card below" (bottom AND small slots) reads as ONE layout. Keep it <= 30 %.
   Mix in: full face with the graphic overlaid (tools flanking his head, white serif on top), the face on the TOP card
   with content below (`beside`, side "bottom"; captions then go at y ~800), the tilted centre card (hero), graphic-only.
2. **Hook**: the payoff on frame 1 (a notification / a result already on screen, big, with a buzz), his title in white
   serif on a dark plate over the card. No tiny labels.
3. **Hero moments must fill the frame**: `sc.slam` (flash + 300 px word, opaque bg for a takeover) on the payoff word.
   Card-sized reveals don't count.
4. **Holds**: any card held > 2 s needs a change on a word (locks rattle, reorder, meter fill, a punch to his face).
5. **Payoffs show content**: a result card must show one legible example (labelled "sample").
6. **Collisions**: outgoing text leaves 0.12-0.26 s before the next serif lands; fade a layer before the next card lands.
7. **Growing from "off" to full fades the face in (a ghost)**: come back from a graphic via tiles, a slam that covers
   the move, or a small card first.
8. **Captions** look ahead over their whole time on screen (`capY` = the highest safe spot across +0.15..+1.3 s).
9. Music: `under` -10 to -12.5 per track (measured result ~-12 dB under speech); `gap` -8.5 to -10.5 so post-drop
   gaps don't shout. Line drops up with the two hero words (MUSIC drop/at).
10. Privacy: crop screenshots to what's needed and blur suggestion lists too (they're personalised); check the crop
    by eye (a first crop exposed two suggestion titles).

## Evidence (2026-10-10, kit/refs/EDITING.md §11)

- `render` runs `kit/qa/precheck.mjs` on the page first: layout, text under 36 px (`small`), text gone before it can be
  read (`read`). It writes `work/holds.json` (readable stills) for `qa.py --holds`.
- `S.focus`, `S.scoreboard`, `S.flow`, `S.hold`, `S.quiet` and `layer(..., { read: true })` work here as in HF.studio.
- `sc.ideaCards`' grey lines are a tease only; the payoff `unlock`s real rows (his words, the real output). The
  published audit Reel unlocked labels with empty values: if the real ideas aren't in the take or a screenshot, ask
  for the screenshot instead of showing structure as the result.

## Handles
Never type a handle into a Reel. When a Reel needs a closing card (only when a long video goes with it), read the
handles from kit/brand.json: `HF.HANDLES` in the page (vendor.inline injects it), the "end_card" key in Python.
YouTube @yourchannel, Instagram @yourhandle; the X handle never goes on a video or in YouTube/Instagram notes.

## Clips timed from the end

A clip that closes a Reel (a meme, a reaction) needs a static `data-start`: the renderer reads media timing from the HTML
attributes and ignores a script that changes them (the clip renders black). In the template, `__END-<s>__` becomes "the
Reel's total minus s" at build time, e.g. `data-start="__END-7.25__" data-duration="7.25" data-media-start="0.95"`.
