---
name: documentary
description: Edit a "Netflix-style" tech documentary on kit/film with the documentary preset (kit/presets/documentary, 2026-10-24): full-frame interviews to the side of the camera, cutaways (B-roll) with natural sound, J/L cuts, name lower-thirds, black chapter cards, time stamps, documentary subtitles, a results board and the `doc` grade. Use it ONLY when the owner explicitly asks for a Netflix-style / documentary / mockumentary film, names preset_documentary. Never for tutorials, explainers, reviews, single-take Reels, podcasts or any normal talking-head edit (those stay on canvas-studio / preset_whitespace or the preset he names); "cinematic", "dark" or "moody" alone are not a request for this: ask him.
---

# Documentary: the opt-in "Netflix-style" pipeline

The owner, 2026-10-24: "Whenever we are recording a normal tutorial kind of video, we're going to use what we have
currently. Whenever I say specifically something like a Netflix sort of video, then only we're going to use these
particular new changes." So this skill is opt-in only. If you aren't sure he asked for it, ask him first.

Read, in order:
1. `kit/refs/OWNER_DEFAULTS.md` (everything in it holds, except the rows the preset README's table changes).
2. `kit/presets/documentary/README.md` (what changes in a documentary and only there, film.py, the run).
3. `kit/presets/documentary/example/` (a film.py, its page and a cutaway maker) and `kit/refs/SHOOT_PLAYBOOK.md` for the shoot.
4. `kit/film/README.md` for the run (prep, cut --plan, cut --voice + listen, joins, cut, grade --sheet, grade, build,
   draft, critic, render, reels).

The switch is `PRESET = "documentary"` in the film's film.py. Copy `kit/presets/documentary/templates/template.html`
to `films/<name>/src/template.html` and put the film's own scenes after `DC.all()`. The smoke test is
`kit/presets/documentary/example` (generated cutaways on the kit/film example take).

Never:
- add `PRESET`, `DOC` or J/L dicts to a film he did not ask to be a documentary (kit/film refuses them anyway);
- copy documentary grammar (chapter cards, letterboxing, the doc grade, subtitles in place of captions) into a normal
  edit;
- change the defaults of the shared pipeline for a documentary's sake. A documentary-only behaviour goes behind
  `doc.on(Fm)` / `--doc` / `HF.doc(`, and `uv run pytest tests/test_documentary.py` has to keep passing.

Use it alongside video-shorts (and the Reel rules (kit/refs/EDITING.md §3-4, kit/reel/README.md) when a Reel is cut from the documentary).
