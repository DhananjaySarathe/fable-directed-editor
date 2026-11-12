# kit/podcast: one-camera podcasts and builder conversations (2026-10-12)

The owner records conversations on **one camera, one mic**. He asked:
- remove what doesn't make sense, repetition, blank stretches and the moments he reads his phone;
- zoom to whoever is talking, or out to both ("crop things so it looks professional");
- a little colour grading;
- noise reduction "a bit";
- little or no music.

## What professionals do (research, 2026-10-12)

- **Virtual multicam from one wide shot:** crop one high-resolution wide into a wide, a single on each person and a
  tighter close-up, then switch between them like cameras.
  Sources: [AutoCut single camera](https://autocut.com/help-center/autocut-podcast/single-camera),
  [B&H video podcast guide](https://www.bhphotovideo.com/explora/node/124651),
  [Choppity speaker tracking](https://help.choppity.com/articles/6316341-speaker-tracking-for-multi-person-podcasts-and-interviews).
  Shoot in 4K so a single crop is still sharp at 1080p.
- **When to cut** ([Finchley: when to cut and why](https://www.finchley.co.uk/finchley-learning/video-engineering-in-a-professional-podcast-post-production-cutting-when-to-cut-and-why)):
  - Show whoever is talking.
  - Cut slightly behind the audio (2–4 frames), never exactly on the new voice.
  - Minimum hold 2–4 s, so "yes" and "uh-huh" don't flash a cut. Maximum 15–30 s on one close-up.
  - Listener reactions run 2–3 s.
  - The wide is for the open, topic changes, crosstalk and resets, 5–10 s. It doesn't replace the singles in dialogue.
  - Standard interviews change shot about every 10–15 s; dense explanations hold longer.
  - A 15–20 % punch-in hides a jump cut from a trim.
- **Sound** ([Podnews LUFS FAQ](https://podnews.net/article/lufs-lkfs-for-podcasters),
  [IRPR: inconsistent loudness](https://sounddesign.irpr.agency/guides/why-is-my-podcast-loudness-inconsistent/)):
  - Level the speakers to each other first; a mismatch between hosts is the usual problem.
  - Clean gently: over-correcting does more harm.
  - Master to about -16 LUFS for audio podcasts (we use -14 for YouTube), true peak under -1 dBTP.

## The pipeline (`uv run python -m kit.podcast films/<name> <step>`)

| Step | What it does | Who checks |
|---|---|---|
| (before) | `uv run shorts probe "<file>" --job <take> --landscape && uv run shorts analyze <take>` (words) | |
| `marks` | `kit/bin/facemarks` (Apple Vision, on-device): every face at 10 fps with its mouth opening and eye openness | |
| `speakers` | the faces grouped into people left to right; each word goes to the person whose mouth moves (sentences vote); `work/speakers.txt` | Claude reads it; `?` lines get SPEAKER_FIX |
| `trims` | `work/trims.md`: phone reading (eyes down, little talk), repeated sentences, restarts, filler runs; long pauses are listed (shortened automatically) | Claude judges each with the transcript, writes CUT |
| `plan` | the edit list (edges in real quiet) + the shot list + **`work/plan.md`** (length before/after, cuts and why, camera mix, sound, look, chapters, warnings) | **the owner, before any render** |
| `preview` | 90 s at 720p from `--at=` on the edited timeline | the owner, optional |
| `render` | the sound (gentle DeepFilterNet, per-speaker levelling, compressor, de-esser, LUFS), the picture (each shot cropped + graded, rendered in parallel, joined), lower thirds, captions.srt, chapters.txt, qa.py | Claude: qa, frames at every shot change, a listen-by-measure; then the owner |

The recipe is `films/<name>/podcast.py`; `kit/podcast/podcast.example.py` lists every setting. Output goes to
`output/final/<name>/` (the episode, captions.srt, chapters.txt).

## The rules (each one a setting; EDITING.md §12 is the editorial side)

- **Cuts:**
  - Whole thoughts only.
  - Keep a question with its answer, and keep laughter and real reactions.
  - Repetition: keep the later, complete version.
  - Phone reading: cut the gap. If he reads something out, keep the reading and cut the silence around it.
  - When in doubt, keep it and list it in the plan.
- **Pauses:** over GAP_MAX (0.6 s), shortened to GAP_KEEP (0.35 s) of the room's own quiet, never digital silence.
- **Camera** (`camera.py`):
  - Open wide 5 s, close wide 3 s, a wide at each chapter.
  - Cut 3 frames after the speaker starts. Hold at least 2.5 s; an interjection under 1.5 s doesn't cut.
  - A single lasts at most 15 s. Then, at the biggest pause, a tight, a reaction or the wide, in turn.
  - Quick back-and-forth stays on the wide.
  - A trim inside a shot switches single and tight to hide the jump.
- **Crops:** single = face at ~26 % of the crop height, tight = ~36 %, eyes on the upper third, always inside the frame.
  An upscale over 1.5x is warned (a 1080p source can't make sharp tight shots: ask him for 4K).
- **Sound:** noise reduction gentle (14 dB maximum), no music under the conversation (an optional quiet bed on the
  intro and outro only), voices levelled ±9 dB maximum.
- **Look:** one measured grade for the episode. White balance and exposure move halfway to natural skin, with a soft
  curve. Never recolour skin to a palette.
- **Quality (the owner, 2026-10-12: "the quality of the video has been decreased" next to his original):**
  - No denoise, no sharpening and no vignette by default. hqdn3d waxed skin and beards, unsharp haloed glasses, and the
    vignette darkened the frame; they are LOOK options for a reason only.
  - Keep the take's frame rate (60 stays 60).
  - Render the picture once at about the original's bitrate (HEVC 100 Mbps for 4K). With graphics windows, splice from
    near-lossless intermediates and encode once at the end, not 2-3 times.
  - Zooming a crop costs detail (a 2x tight is 1080p-sharp). Say so in the plan and suggest a 4K60 take, good light and
    people sitting further apart for wider singles.

## Learned on the first real episode (films/guest-podcast, 2026-10-12)

- **Two takes, one episode:** join them without re-encoding (`ffmpeg -f concat ... -c copy`; check the offset by
  cross-correlating the audio) and merge the analyses. `SEQUENCE` plays a part recorded
  later in the middle; `SPLITS` gives each take its own crops (people shift between takes).
- **iPhone files can be stored upside down** (rotation -180): facemarks passes the orientation to Vision. Without it,
  left and right were mirrored and every speaker was swapped. Check the speaker sheet's first turns against who says
  "hi guys".
- **HDR (HLG) takes:** the render and the grade tone-map them (render.tonemap). ffprobe prints "arib-std-b67," with a
  trailing comma, which silently broke the check once.
- **Hinglish conversations:** `shorts analyze <take> --language hinglish`. The English pass looped one line 40 times
  and dropped whole minutes.
- **People sitting close:** `CROP` = {"single": 0.20, "tight": 0.24} for a 4K episode. A single slides, or tightens up to
  20 %, so the other face is never cut in half, and a tight is always a 16 % punch-in on the single. `WIDE_ZOOM` 1.12.
- **4K speed:** the grade runs at the crop's size, then lanczos up, then h264_videotoolbox. x264 ran at 0.16x real time;
  this runs at about 0.45x. An 18-minute body renders in 35 minutes.
- **Graphics inside the episode:** windows of the rendered body rebuilt in HyperFrames, with the body's own frames as
  the bottom layer (a board can shrink the speaker into a panel or a circle). They're spliced back frame-exact, and
  then the whole film is encoded once. Windows must share edges: a
  one-frame overlap shifts the sound for the rest of the film.
- **Shorts:** `kit/podcast/shorts.py` + `kit/podcast/short.html`.
  - Layouts: face (a 9:16 crop following the speaker), stack (both people), card (a proof with the speaker in a circle)
    and slam.
  - Phrase captions with hand-fixed Hinglish, a designed hook, a progress bar and the "full podcast on YouTube" card.
  - The recipe is films/<name>/shorts.py.
- **Captions:** HyperFrames' clip runtime sets `visibility` on videos, so switch layers with `opacity`.

## Limits (be honest in the plan)

- **Who's speaking:** it's a mouth-motion estimate. It is confused by laughter, a hand over the mouth, profile views
  and a face that leaves the frame. The sheet marks weak stretches, and Claude checks them against the words.
- **One camera:** there are no true reaction angles, so a reaction is a crop of the listener. Crops never fake a
  second camera position (no mirroring).
- **One mic:** levelling evens the two voices out, but the far voice keeps more room sound. A lav mic per person fixes
  that at the source (kit/refs/FILMING.md).
- **Validation:** tested on synthetic data so far (tests/test_podcast.py). The first real episode is the validation:
  watch the speaker sheet and the shot changes closely.
