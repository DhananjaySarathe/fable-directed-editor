---
name: paper-collage
description: Build a Reel/Short (or a 16:9 insert) in the paper-collage look the owner loves - photoreal cut-out objects on aged paper and newsprint, stamped Anton headlines with one red word, masking-tape labels, polaroids, torn price tags, a yellow ticket, a hand-drawn chart, red marker circles/arrows/handwriting (reference: the fliki reel instagram.com/p/Dcblnu1gyAP). Use it whenever he says collage, paper collage, mixed media, newspaper look, scrapbook, "like that fliki reel", hyper-realistic objects, photoreal props, or asks for a hook built from objects/prices/trends - alongside video-shorts (and the Reel rules (kit/refs/EDITING.md §3-4, kit/reel/README.md) for 9:16).
---

# Paper collage (preset_paper_collage)

Read `kit/presets/paper_collage/README.md` first. It has the look, when to use it, the parts (`kit/hf/paper.js`) and the rules.
The normal Reel pipeline (`kit/reel`, video-shorts skill) stays in charge of the cut, voice, grade, captions and QA.
This skill adds the collage beats.

## The run

1. **Plan the collage beats (you, the director).** In the hook plan, mark which phrases become collage. Usually it's
   the first 3–6 s, plus at most 1–2 later explainer beats. For each beat write:
   - the word ids it lands on;
   - the props, with their exact text, taken from his words;
   - the hero object or objects and where each comes from.
   Every number must be one he said. Write this as `films/<name>/collage_plan.json`:
   ```json
   { "beats": [ { "from": 3, "to": 18, "panel": "top", "props": [
       { "kind": "hero", "object": "toy", "at": "w4", "x": 520, "y": 260, "h": 760 },
       { "kind": "stamp", "text": "this toy is|*everywhere.", "times": ["w5", "w9"], "x": 60, "y": 110, "size": 120 },
       { "kind": "tape", "text": "labubu", "at": "w6", "x": 70, "y": 820 } ] } ],
     "objects": { "toy": { "source": "chatgpt", "prompt": "<the README §4 prompt with the exact object>" } } }
   ```
2. **Get the objects.** Prefer his own photos. Otherwise give him the ChatGPT prompts from README §4, in one message.
   He drops the images into `films/<name>/assets/objects/<object>.png`. Then run
   `uv run python -m kit.look.objects films/<name> --stage` (Apple Vision cut-outs, on-device). Never call a paid
   image generator without his explicit OK for that Reel.
3. **Build the beats.** Translate each beat into `HF.paper(S)` calls in the Reel's template, inside a `layer()` on its
   words. To save the main session's tokens, a builder subagent can do this step:
   - Use the Agent tool with `model: "sonnet"`.
   - Give it the plan JSON, `kit/presets/paper_collage/README.md` §3, and the template's existing scene code.
   - Tell it to use only `P.*`, `layer()`, `W(id)` and the plan's coordinates and text, and to write nothing new.
   Then you review its diff: text only from the plan, nothing invented, times on words.
   Don't hand the director's work (the plan, the judgment calls, the review) to a smaller model.
4. **Check.** `node kit/qa/precheck.mjs <hf>/index.html` must have 0 HIGH. Fix `small` (labels ≥ 36 px) and `read`
   (time to read).
   - Look at snapshots at the beat times (`npx hyperframes snapshot ... --at`) and at a 1080p draft. Check that each
     prop lands on its phrase, that his face isn't covered and that red is used once per beat.
   - Then continue with the normal Reel render and QA (`python -m kit.reel films/<name> render`).

## Guardrails

- The collage is a hook or an explainer beat, never the whole Reel. A real screen recording stays the evidence for a
  workflow.
- Objects are illustrations. No real people's faces from a generator, no logos unless he names the product, no fake
  documents or screenshots.
- Keep his footage's look v2 grade. The paper doesn't change his skin tone.
- If the cut-out fails, or he has no object image, fall back to a prop-only collage: stamps, tape, ticket, chart and
  ink on paper, with his cut-out face from the Reel's person matte (`F.corner`) as the hero.
