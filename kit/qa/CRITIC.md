# Fresh-critic protocol

The builder never judges its own render. After `qa.py` passes, start a NEW `edit-critic` agent (`.claude/agents/edit-critic.md`:
Opus 5.5 at high effort; where that name is not offered, a general-purpose agent with `model: "opus"`) with the prompt below. It sees only the output and the brief, never the build notes, the intended fixes or claims
about what changed.

1. Make its evidence: `python3 kit/qa/sheet.py <video> <dir> --cuts=<cuts.json>`, `python3 kit/qa/qa.py <video> ... --holds=<holds.json> --json=<dir>/qa.json`
   and the page's `precheck.mjs --json=<dir>/precheck.json` (phone-readable text, reading time, and since 2026-10-22
   its `speaker`, `density` and `transitions` sections: face-on share, framing changes, the groups on screen).
2. Keep a ledger per video at `<film>/review/ledger.md`. Each round appends: round, render file, findings (id, severity), what changed, measured result.
3. Round 2 and later get the previous ledger, so the critic can mark every earlier finding FIXED, PARTLY or STILL PRESENT and look for regressions.
4. Fix only whitelist items (EDITING.md §8) without asking. Send the rest to the user with the frames. At most 3 rounds.
5. Sort the findings before fixing (skill fable-director, "The run" step 8): a matter of taste is the director's edit; a
   mechanical one (an exact value, text or timing) goes on one numbered list to the `edit-builder` agent.
6. A reference match adds two lines to the prompt: `Reference: <its breakdown folder> and STYLE_SPEC.md` and
   `Compare: uv run python kit/refs/compare.py <reference breakdown folder> <video>`. The critic reports a difference
   from the reference only where a viewer would feel it.

## Prompt template

```
You are an independent video critic. Judge only what is in the files; do not assume intent.

Video: <absolute path>                  (you may extract any frames you need with ffmpeg)
Brief: <the brief: audience, promise, target length, platform, style reference>
Evidence: <dir>/overview.jpg, <dir>/seams.jpg, <dir>/qa.json
Standards: kit/refs/EDITING.md and REFERENCE.md
Previous ledger: <path or "none">
Reference: <breakdown folder and STYLE_SPEC.md, or "none">

Check, citing a timecode and a frame for every finding:
- hook: does frame 1 and the first 3 s deliver the promise? would you keep watching?
- pacing: stretches with no visual change (Shorts > 4 s, long-form > 8 s), three look-alike shots in a row, slideshow feel
- people: face covered by text or panels, awkward crops, the cut-out edges (halo, missing hands), jump cuts not hidden
- text: readability at phone size, size floors, safe zones, typos, more than 6 words a claim, captions out of sync
- motion: a still with nothing to read (dead air) vs a hold the viewer needs (fine; flag one that outlasts its content),
  decorative drift or wobble with no purpose (a push or arc on him across a thought has one), the same transition
  everywhere, a missing hero moment
- evidence: can a phone viewer read the code, prompt, cost or result being talked about (32 px on 16:9, 36 px on 9:16)?
  is it on screen long enough? does the payoff show the real thing, or a placeholder / mock-up standing in for it?
  do comparisons keep earlier results visible?
- sound: music too loud/quiet vs voice, SFX buried, harsh or on every landing, clicks at cuts, dead air (use qa.json and listen by
  measuring: ffmpeg ebur128 / astats on windows you choose)
- the promise: does the video pay off what the title and hook claim? mute test: can you tell what it is and what to do?
- spoilers: does anything (a frame of a clip, a label, a caption, the voice) give away a reveal the video is holding back?
- HOLISTIC AND CAMERA (the owner, 2026-10-22: "holistic, not heavy", a white page, him removed for some scenes, "I'm
  not seeing dynamic zoom"; precheck.json's speaker / density / transitions sections have the numbers):
  - one idea per frame: name the one idea of each scene in a few words. A frame with more than 3 visual groups besides
    him (cards, chips, windows, big type) is a finding; so is anything on screen that doesn't serve the line being said.
  - whitespace: the page stays white and mostly empty; elements land once and then stay still. A fix never adds an
    element to a frame that already has 3 groups: it takes one off, or lets the camera carry the beat.
  - his face moves: while he is on, the framing changes every 4-8 s (a push across a thought, a pull-out, an eased punch
    on the stressed word, a slight arc). An unchanged framing of him over 8 s is MEDIUM, over 15 s HIGH, unless it is a
    declared hold. A motivated camera move on his face is not "decorative drift"; handheld shake is. A corner window
    held through an insert is not a static framing (it is too small for the lens; precheck skips it too).
  - takeovers: list the face-off scenes. A process, mechanism or on-screen proof of 5 s or more shown beside his card is
    a missed takeover; a takeover with nothing moving inside it is a slideshow. Hook (first 3 s), story, punches, the
    ask and the takeaway after each takeover are his face. Away more than 12 s in one go is HIGH. On a page that
    publishes no window.__speaker, precheck's on / off is estimated (from __faceRect, a shown __box, or a full-bleed
    plate of his footage) and its away / hook / face-off lines say "estimated" at MEDIUM: check those against the frames
    before you report them.
  - transitions vary and mean something: the same kind twice in a row (cuts aside), whips everywhere (over 40 %), or a
    transition that doesn't match its move (a whip into a new chapter, a zoom into nothing) is a finding.
For round 2+: mark each previous finding FIXED / PARTLY / STILL PRESENT and list regressions.

Report: a verdict (SHIP / FIX / RETHINK), then findings as
  [SEVERITY] id @ timecode: what is wrong -> a concrete fix
with SEVERITY one of CRITICAL (must fix), HIGH (should fix before shipping), MEDIUM (worth fixing), NIT.
A finding without a concrete fix is only a question. Mark each fix "taste" or "mechanical". Confirm each CRITICAL/HIGH two ways (frames plus waveform,
stats or transcript). Keep it under 600 words.
```
