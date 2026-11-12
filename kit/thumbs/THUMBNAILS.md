# Thumbnail kit

What the edit desk's **Thumbnail kit ↗** button asks for, once a video's final file exists. The kit is a prompt the
user pastes into ChatGPT, plus the photos they attach to it; ChatGPT makes the images. The kit lives in
`output/final/<video>/thumbnail/`:

```
gpt_prompt.md      paste-ready, nothing else in it: the desk's "Copy GPT prompt" copies this file as it is
notes.md           for the user: the three concepts and why, what the research found (with links), which photos to attach
photos/            face_01.jpg ... (frames of the creator), ref_*.jpg (kit/refs/me/), sheet.jpg, frames.json
research/          the competing videos' thumbnails (i.ytimg.com), sheet.jpg, videos.json
```

ChatGPT cannot open a path on this Mac: everything it needs is either in the prompt's text or in a photo the user
attaches. Never put a local path in `gpt_prompt.md` as if GPT could read it.

## What to make

- **Long-form (16:9):** three thumbnails, 1280×720, for YouTube's Test & Compare (it takes up to three and keeps the
  one with the best watch-time share). Three different *reasons to click*, never three versions of one idea.
- **Reel / Short (9:16):** one cover, 1080×1920, for the Shorts and Instagram cover. Everything that matters inside
  y 270-1250 (the reel safe band: the platform UI covers the rest), the face in the upper half.

## Steps

1. **Know the video.** Read the final transcript (the film's `cues.json` / `edl.json`), the
   film's `review/brief.md` if there is one, and `output/final/<video>/upload_copy.txt` (its titles). Write down, in a
   line each: the promise (what the viewer gets), the payoff moment (the best 5 s), the one surprising fact or number,
   and the title it will most likely run with.
2. **Photos.** `uv run python kit/thumbs/frames.py <video>`. Open `photos/sheet.jpg` and look: delete any frame with
   the eyes lowered or closed, a blur, a half-word mouth shape that reads as a grimace, or a hand across the face.
   Keep 3-5. Renumber nothing: the prompt names the files that are left. If `kit/refs/me/` holds photos, they are
   copied in as `ref_*.jpg`; prefer them for likeness and the frames for expression.
3. **Research (real, per video, every time).** Find 8-12 videos on the same topic from the last 12 months that did
   well: WebSearch `site:youtube.com <topic>` and variants in English and Hinglish, plus the Indian tech/AI/finance
   creators this channel sits next to. For each, get its id and fetch
   `https://i.ytimg.com/vi/<id>/hqdefault.jpg` into `research/` (curl). Tile them into `research/sheet.jpg` (Pillow, 4
   across) and look at the sheet. Note what the feed already looks like (colours, layouts, faces, word counts) and
   what nobody is doing: the three concepts must stand out *in that feed*, not just look good alone. Save
   `research/videos.json` (title, channel, views if shown, url).
4. **Three concepts.** Each one: a name, the reason to click in one line (curiosity gap, result/proof, contrast or
   before/after, stakes, a number), and how it completes the title instead of repeating it. Check each against the
   rules below, then write `gpt_prompt.md` and `notes.md`.

## Rules every thumbnail follows

What the research says works, and what it says does not (sources in `notes.md` of each kit; the base set is below):

- **One focal point**, readable at phone size (about 160 px wide in the feed): squint-test it.
- **The face fills about a third of the frame**, eyes to the camera or to the thing the video is about; a real
  expression from the video (curious, amused, sceptical, pleased). Exaggerated shock faces are rare on breakout
  thumbnails (5-11% in the 2026 studies): use one only when the video truly has that moment.
- **Text: 2-4 words, never more than 5**, bold sans-serif with an outline or shadow, large; it adds what the title
  doesn't say. No full sentences, no all-caps shouting across the frame, no pointing fingers or red arrows by default.
- **Contrast** against both of YouTube's backgrounds (white and dark): a subject that separates from its background
  (rim light, a darker or blurred background, a colour the face isn't).
- **Nothing in the bottom-right corner** (the timestamp covers it).
- **True to the video.** Every number, object and claim on it appears in the video. Test & Compare scores watch time,
  so a thumbnail that over-promises loses even when it gets the click.
- The channel's look carries over (the colours and type of the video's own graphics, from its `src/template.html` or
  look), so the three read as one channel.

## gpt_prompt.md

Plain text, written to be pasted as it is; it addresses GPT directly and names only photos the user will attach.

```
I'm attaching <N> photos of me: <face_02.jpg, face_05.jpg, ref_01.jpg ...>. Use them only as the identity reference
for the person in the thumbnails: keep my face, face shape, hair, beard, skin tone and age exactly as in the photos.
No beautifying, no smoothing, no making me look like someone else.

The video: <two or three sentences: what it is, the payoff, who it's for>. Its title: "<title>".

Make <three YouTube thumbnails, 1280×720 (16:9) | one 9:16 cover, 1080×1920>. One image per reply: make number 1 now,
and I'll say "next" for the others.

For all of them: <the shared rules, short: one focal point, face about a third of the frame, the exact text in
quotes and nothing else written anywhere, bold sans-serif with a dark outline, nothing in the bottom-right corner,
high contrast, photographic not cartoon unless a concept says otherwise>.

Thumbnail 1: <concept name>
- Me: <which photo's expression, pose, where in the frame, where I look>
- Scene: <background, light, depth>
- Object or graphic: <the one prop or visual that carries the idea, drawn from the video>
- Text: "<EXACT WORDS>" <where, colour, size>
- Colours: <two or three>
Thumbnail 2: ...
Thumbnail 3: ...

If any text comes out misspelled, make it again with no text and leave that space empty.
```

## notes.md

For the user, short: the three concepts and the reason to click of each; which photos to attach (and the order);
what the research showed (the feed's look, what the three do differently) with the video links; then how to use it:
paste the prompt, attach the photos, "next" twice, check every face against the real one, upload all three to Test &
Compare.

## Base research (2026-10-09)

- Test & Compare: up to three thumbnails per video, winner by watch-time share. [toptal](https://www.toptal.com/creator/post/youtube-thumbnail-ab-testing),
  [Search Engine Journal](https://searchenginejournal.com/youtube-rolls-out-thumbnail-a-b-testing-to-all-channels/519281)
- 500 breakout thumbnails: 69% a face, 72% text, 56% high contrast, 5% exaggerated expressions; the top set: a face
  about a third of the frame, strong contrast, few words. [vidIQ research, July 2026](https://vidiq.com/research/youtube-thumbnail-study/)
- 1,043 channels: shocked faces on 11% of face covers; no single feature marks the winners. (Thumbnail Bench, via
  [velio](https://velio.co/?p=3078))
- Text 2-5 words, legible at small size; the thumbnail opens a gap the title closes. [vidIQ tips](https://vidiq.com/blog/post/youtube-thumbnail-tips/),
  [Thumbnail Test](https://thumbnailtest.com/guides/best-practices-youtube-thumbnail/)
- GPT likeness: upload first, name each photo's role, say what must not change, add text last if it misspells.
  [Kapwing](https://www.kapwing.com/resources/using-chatgpt-as-a-thumbnail-maker-for-youtube-and-more/),
  [youmind](https://youmind.com/prompts/correct-thumbnail-face-24193)
