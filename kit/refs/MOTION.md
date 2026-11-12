# Motion language: the speaker as a moving box

Learned 2026-10-08 from a reference the user loved: a 46 s 16:9 talking-head edit built in HTML + GSAP, shown side by
side with its raw take. The user's words: "see how the animation to him changes, the square movement where inside
that his video plays, and the pace with transitions". This file is the **grammar**, not a template. Use it to decide
moves for any take. The graphics in that edit (pastel gradient, indigo cards) were deliberately **not** turned into a
preset: graphics are chosen per video.

Built from it: `kit/hf/box.js` (`HF.box`, `HF.box.direct`, `HF.box.morph`), the demo `kit/hf/demos/box/`, and the
measuring tool `kit/refs/motion_ref.py`.

## 1. What the reference does (measured frame by frame)

`python3 kit/refs/motion_ref.py ref.mp4 --crop=720:404:0:152 --box=dark --strips` on the top half, plus a hand-checked
per-frame track of the box (position, size, tilt):

| t (s) | Move | Length |
|---|---|---|
| 0.47 | centred card (60 % wide, −2.2°) **grows** to full frame; tilt and corner radius go to 0 as it lands | 270 ms, even speed |
| 1.83 | full frame **collapses**: an accent wash covers the video, the box shrinks to a small pill, the pill grows into the next title card | 250 ms |
| 3.93 | that title card **flips** on its vertical axis; its back is the video, landing as a card on the right | 130 ms |
| 5.93 | card **dissolves** while the next graphic grows out of it | 130 ms |
| 10.0 | accent **tiles** cover the frame, then fly apart onto the full-frame face | ~300 ms |
| 11.27 | full frame **shrinks** to a small tilted card on the left | 100 ms (3 frames) |
| 12.67 | card **slides** out to the left, tilting −2° → −5° | 100 ms |
| 16.70 | the collapse again (it is the edit's signature) | 70–250 ms |
| 33.17 | a card **swings** in like a door on its near edge while the old graphic is pushed out | 100 ms |
| 35.30 | card **shrinks** 44 % → 34 % wide at the moment new content needs room | 100 ms |
| 38.77 | card and its neighbour **slide** out together | 100 ms |
| 43.50 | the tiles again, onto the full-frame ending | 130 ms + fly-out |

Card places (fractions of the frame): centre 60 % × 60 % (16:9); right 47 % × 74 % (~1.13 : 1); left 44 % × 65 %; small
left 33 % × 56 % (~1.06 : 1). **The box changes aspect as it moves**: a hero card is 16:9, a card beside text is
nearly square.

Whole-edit pace (`motion_ref.py`): something moves ~76 times a minute; the median move is **0.2 s**; the median hold
is 0.7 s (p90 1.4 s); the picture is in motion 27 % of the time. The face is on screen 43 % of the time, full frame
only 14 %. The longest stretch without the face is ~16 s (a run of graphics in the middle).

## 2. The rules (what makes it feel good)

1. **Fast moves, long holds.** Box moves take 0.1–0.3 s, and most of the travel happens in the first 2–3 frames
   (expo out). Growing back to full frame is the slowest (0.27 s, even speed), because it is the payoff. Holds last
   1.2–5.5 s.
2. **A held card is never still.** It sways ±0.4° (period ~5 s) and floats ±0.6 % of the height (period ~4 s). A full
   frame drifts in instead (+0.6 %/s, capped at 3 %, as the camera already does; with the lens on, v11, the footage
   moves by the lens instead wherever the lens moves, §5, a hold it leaves still keeps the drift, and the card's sway
   and float stay). This is the reference's look, at its
   own size: S.layer() uses ±6 px / 0.4 %/s (16:9). It is not there to pass a freeze check (2026-10-10): a scene the
   viewer reads holds still (`layer(..., { read: true })`) and qa.py treats it as a hold (EDITING.md §6, §11).
3. **The box becomes the next thing.** It collapses into a pill that grows into the next card, a card flips over into
   the face, tiles break apart onto it. One object changing shape keeps continuity, so cuts feel like one motion.
4. **Every move is caused by the layout.** The card shrinks exactly when new content needs the space; it leaves off
   its own side, in the direction the next scene comes from. The next element enters in the same frames, so there is
   never an empty frame.
5. **The face comes in bursts.** Graphics carry explanations; the face returns for the emotional lines (claims,
   "the crazy part", "I'm sharing the process", the ending), and lands hard. Keep the face on screen ≥ 35 % of the
   time and never away for more than 12 s of talk (since 2026-10-22, was ~18 s: plan_check errors on a longer
   absence, precheck reads it as HIGH; kit/refs/SCENES.md §9).
6. **One look for the box.** Tilt about 2° (leaning toward the content), rounded corners (~28 px in 1080p), a soft
   shadow, slight 3D. Only full frame is perfectly straight.
7. **Budgets**, so the special moves stay special: tiles at most once per ~20 s and only when returning to the face at
   a section; flip at most once per ~25 s and only out of a card; collapse whenever full frame hands over to a graphic
   that starts as a card.

These rules refine kit/refs/REFERENCE.md's "subject integrated, never boxed". A *static* webcam rectangle on a slide
still reads as amateur. A box that moves, tilts, morphs and hands over to graphics is a designed object, and that is
what the user liked.

## 3. Using it in an edit

In the visual plan, give each passage a `box` beat: what the passage shows and where its content sits. Then let
`HF.box.direct` pick the moves; `plan_check.py` validates the field.

```json
{ "id": "p4", "words": [88, 112], "type": "comparison", "technique": "compare", "goal": "...", "beats": [...],
  "box": { "show": "beside", "side": "left" } }
```

| `show` | When | Box goes to |
|---|---|---|
| `face` | nothing else on screen; the face carries the line | full frame |
| `punch` | the emotional line, the payoff (`section: true` at a chapter change allows tiles) | full frame, hard |
| `beside` | content on one side (`side` = where the **content** is) | the card on the other side |
| `aside` | small content (a number, a word) | the small card on the other side |
| `hero` | the face under or over a title | the centred 16:9 card |
| `graphic` | a full-screen explanation (`card: true` when it starts as a card: the collapse hands over to it) | off |

`card: true` on a `beside`/`aside` beat after a graphic means the graphic's last card turns over into the face
(flip): pass that element as the shot's `from`.

```js
const plan = HF.box.direct({ beats });                       // + plan.log: every decision and why
plan.shots.forEach((s) => { if (s.in === "flip") s.from = promptCard; });
const B = HF.box(K, st, { shots: plan.shots, face: [945, 300] });
HF.box.morph(K, card, pillRect, cardRect, landAt);          // a card grows out of the collapsed pill
HF.box.pace(B.plan, total);                                  // face share, longest away, moves per minute
```

Two cameras, two jobs (2026-10-22, v11), and they compose:
- **The box moves the shape.** HF.box (and the canvas speaker's shots) move the speaker's shape: full frame, a card,
  the pill, gone.
- **The lens moves the picture inside it.** `HF.motion.lens` (§5) moves the footage inside every steady shape:
  pushes, pull-outs, arcs, settles, punches on stressed words, and the jump-cut reframe.
  - It is on by default for kit/film builds of films made from 2026-10-22 (`D.lens`); an explicit `LENS` in film.py
    wins, so a rebuilt older film keeps the moves it was delivered with.
  - It replaces the hard 1.12x jump steps (with eased reframes, on the soft allowance where the sharp budget has no
    room), and the box's old linear 3 % drift wherever it moves. A hold it leaves still keeps the drift.
  - So a film with the box gets its punch-ins from the lens.

What still excludes each other is `HF.camera`'s *layouts* and `HF.box` on the same `<video>`: both write its
transform. `HF.camera` (the director's full-frame A-roll camera with baked motion blur, films/expensewaale) is for
films that have no box and no canvas shape.

9:16 has its own slots (`top`, `bottom`, `bottomSmall`, `center`, `pip`, `pill`); `side` is then `top` or `bottom`.

## 4. Learning from the next reference

1. `python3 kit/refs/motion_ref.py ref.mp4 [--crop=...] --box=dark --strips --out=work/ref` gives the pace numbers and
   every box move, with a 10-frame strip per move. Check the strips by eye: a dark graphic can register as a box.
2. Write what is new into §1–2 here (numbers, not adjectives), and into `box.js` only if it is a move we don't have.
3. Compare our render with the same tool: the pace of our edit should land near the reference's (moves of 0.1–0.3 s,
   holds ≥ 1.2 s, face share and longest absence inside the rules).

## 5. The camera inside the shape: the lens (2026-10-22)

The owner: "I'm not seeing dynamic zoom". Two measured misses did not read: xchakra's drift (0.5 % a second) and Reel
A's move (5 % over 4 s). The lens therefore changes the framing visibly but smoothly, every 4-8 s while he is on.

**Its moves**, one per thought, never the same twice in a row (a settle doesn't count as a break):
- push +6-12 % across the thought;
- pull-out back to the base, from at least 6 % in;
- arc: truck ≤ 3 % of the shape, roll ≤ 0.6°, scale +4 %;
- settle: 1.04 → 1.0 in 1.2 s after a shape move, whip or takeover.

Each thought takes the move that played longest ago, so push, arc and pull all come round when his shape changes
every 5-8 s; a hold that opens on a pull-out lands a little closer (+9 %) and pulls out from there.

**Punches** on stressed words: ×1.15 (never under ×1.12 on screen) over 13 frames, landing on the word, held to the
sentence's end, released over 0.5 s. At most one every 12 s. A punch is a factor on the framing in force (a jump
reframe included), so its step is its own size. A hold with a candidate keeps ×1.12 free for it, and a join before it
keeps that room too; where the budget can't pay ×1.12 the punch is skipped and logged, never landed smaller.

**Jump cuts** become an eased 0.25 s wide/close reframe. A join under a punch hides in it. Where the sharp budget has
no room for one (every full frame on a 4K render), the reframe spends the track's soft allowance rather than leave a
bare jump cut. The pre-v11 kit stepped ×1.12 there anyway; `__speaker` reports it as `soft`. A canvas template that
still has its own "every other join ×1.12" loop keeps its hard steps: the lens reads those same-shape cut shots as one
hold and carries across them. Drop the loop to get the eased reframe.

**Limits:**
- No handheld shake.
- It holds still during whips.
- It stays eye-anchored and always covers the shape. In a seated `frame` it stays inside the take's clean rect.
- Its own moves stay inside the zoom budget of the footage playing in each hold (work/tracks.json, per view kind: a
  4K selfie and a 576 px screen-recorder bubble on one track each get their own cap). In cards, circles and corners
  that is the sharp budget. At full bleed, where a 4K render leaves no sharp headroom, the lens's moves and punches
  spend the soft allowance (at most ×1.24 on a native 4K track, ×1.12 on a 1080 track): the owner's call, pending his
  sign-off on the v11 sample; `LENS = dict(budget="sharp")` keeps every hold strictly sharp (full bleed then holds
  still). The jump reframes and an HF.box hold's drift may also reach into the soft allowance.
- Amplitude shrinks with the shape (none under 240 px).

API and options: `kit/hf/README.md` "The lens".
