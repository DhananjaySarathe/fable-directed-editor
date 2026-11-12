---
name: podcast
description: Edit a podcast, interview or builder conversation recorded on ONE camera (and usually one mic) into a professional episode - remove what doesn't make sense, repetition, dead air and phone-reading moments; virtual multicam (crop to whoever is talking, reactions, wide shots); gentle noise reduction and level matching; a light grade; little or no music. Use it whenever the owner says podcast, conversation, interview, guest, episode, "zoom to the other person", or shares a two-person recording, alongside video-shorts.
---

# Podcast (one camera)

Read `kit/podcast/README.md` first: the research, the pipeline, the rules and the limits. The steps, in order:

1. `uv run shorts probe "<file>" --job <take> --landscape && uv run shorts analyze <take>`. Copy
   `kit/podcast/podcast.example.py` to `films/<name>/podcast.py` (TAKE, SOURCE = the original full-resolution file,
   PEOPLE left to right). Check the source: if it's under 4K, tight crops will be soft; the plan says so.
2. `python -m kit.podcast films/<name> marks`, then `speakers`. Read `work/speakers.txt` against the words. Every `?`
   stretch gets a look, and a wrong speaker gets SPEAKER_FIX.
3. `trims`: read `work/trims.md` with the full transcript. Judge each candidate, and look for what the tools can't see:
   - tangents and false starts;
   - "let me check" moments and him reading his phone;
   - repeated points.
   Write CUT ranges with a reason. The rules:
   - whole thoughts only;
   - keep a question with its answer;
   - keep laughter and real reactions;
   - when in doubt, keep it and list it.
4. `plan`: send the owner `work/plan.md`'s summary (length before/after, what was cut and why, the camera mix, sound,
   look, chapters, warnings). **Wait for his ok.** This is the step that stops a full render of a wrong direction.
5. Optional: `preview --at=<s>` (90 s, 720p) for a quick look at the camera and the sound.
6. `render`, then check it yourself before sending:
   - qa.py;
   - frames at every shot change: the right person, face not cut, no jump;
   - the speaker levels in the audio log;
   - a whisper re-listen of a few joins.
   Deliver the episode, captions.srt, chapters.txt and the open items.

Shorts from the episode come after. They use `kit/podcast/shorts.py` and `kit/podcast/short.html`; the recipe goes in
films/<name>/shorts.py. A Short uses the face, stack, card and
slam layouts, hand-fixed Hinglish captions, a designed hook and a "full podcast on YouTube" card, and keeps a question
together with its answer. Follow the Reel rules (kit/refs/EDITING.md §3-4, kit/reel/README.md) for them.

The episode flow the owner wants: a trailer (~10 s, music, the best lines, the drop on the title), then a designed intro
of each person (2x slow motion freezing into a sticker cut-out with the name and role), then the podcast. Two-take
episodes, rotated or HLG iPhone files, and graphics windows are covered in kit/podcast/README.md, "Learned on the first
real episode".
