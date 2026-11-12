# Fable-Directed Editor: an editor for talking-head videos, run by Claude Code

A toolkit that turns raw talking-head takes into finished YouTube videos and Instagram Reels: Python and ffmpeg for
the footage, HyperFrames (HTML) compositions for the motion graphics, whisper for the words, automatic QA and a fresh
critic. Quality decides; cost is saved only where it was being wasted.

"The owner" in this file, the skills, the agents and the kit's docs is the person whose videos are edited here: the
user you are working with. The docs were written while editing their author's own videos, so they often say "he" and
quote his feedback; read those lines as the reason behind a default, and follow the current owner where they differ.

## When a video, a Reel or a reference arrives

Load the `fable-director` skill first, then the look skill it points to. It sets:
- **the roles:** the main session (Fable 5.2, high effort, set in `.claude/settings.json`) directs and designs
  everything a viewer sees or hears. The agents in `.claude/agents/` do the rest: `reference-analyst` and `edit-critic`
  on Fable 5.2, `fact-scout` and `edit-builder` on Sonnet 5.5, `qa-reader` on Haiku 5.5. Renders and grades are
  background shell commands;
- **the order of the run**, from intake to the delivered files and the cost line;
- **how a reference video is matched:** measured first (`kit/refs/breakdown.py`), then compared with the draft
  (`kit/refs/compare.py`).

The standing taste is `kit/refs/OWNER_DEFAULTS.md`: read it before any edit. It holds defaults the owner can change;
when the owner states a lasting preference, offer to write it there.

## Working in this repository

- Python runs through uv (`uv run python ...`, `uv run shorts ...`, `uv run pytest`); the page checks run on node.
- `kit/` is the toolkit, `films/<name>/` holds one film's recipe (never generated files), `output/` holds everything
  generated (`final/` is what gets uploaded, `temp/` can be deleted any time), `broll/` is the reusable footage.
- Long manuals are read by section: `python3 kit/doc.py kit/hf/README.md` lists the sections,
  `python3 kit/doc.py kit/hf/README.md "The lens"` prints one.
- What an edit cost, per model: `uv run python kit/cost.py`.
- Something a film needs that another film could reuse goes into `kit/` with a line in its README and a test, not
  into the film.
- One heavy render or grade at a time on one Mac. Long jobs run in the background.
- Commit or push only when the owner asks.

## What this copy does not include

- **The author's films.** Docs and code comments name them (`films/ai-workflows`, `films/chakra-redline`,
  `films/v11-sample` and others) as the place a rule was learned. Those folders are not here; never go looking for
  them. The examples that are here:

  | For | Where |
  |---|---|
  | the whole film pipeline, run end to end with no footage | `kit/film/example/` (its `film.py` lists the commands) |
  | a page in the default white look | `kit/presets/whitespace/templates/template.html`, `kit/presets/whitespace/sheet/` |
  | the warm canvas look | `kit/presets/canvas_studio/templates/template.html` |
  | a documentary | `kit/presets/documentary/example/` |
  | the paper-studio long-form and Reel | `kit/presets/paper_studio/templates/`, and `example/` beside it to read (its footage is not here, so it does not run) |
  | single components (takeovers, diagrams, evidence, kinetic type ...) | the templates in `kit/hf/demos/<name>/src/` and `kit/hf/showcase/src/` |
  | a podcast | `kit/podcast/podcast.example.py` |
  | a single-take Reel | `kit/reel/README.md` (`reel.py` fields: `kit/reel/config.py`) |

  Read the demo templates for how a component is called. Four of their build scripts (`showcase`, and the `catalog`,
  `explain` and `redline` demos) copy screenshots from the author's films and stop without them; `kit/cut/evaluate.py`
  and `calibrate.py` need the author's labelled takes for the same reason.

- **Most music and sound effects.** `./setup.sh` downloads them (`kit/assets_src/fetch.py`); a track with no public
  download is skipped, so check that a file exists before planning a bed around it. The 13 basic sounds in `kit/sfx/`
  itself (whoosh, pop, click, stamp ...) were synthesised by this project and are included.
- **Preview pictures** of the components and templates (`kit/hf/previews/`, `kit/graphics/_previews/`): they showed the
  author. Choose components from `kit/hf/registry.json` and the READMEs, and look at a still of your own build.
- **A Claude memory.** Where a doc says "memory", the rule it means is in `kit/refs/OWNER_DEFAULTS.md` or that
  folder's README.
- **Handles.** `kit/brand.json` holds placeholders (`@yourchannel`, `@yourhandle`). Before the first end card, ask the
  owner for their handles and write them there; never render a placeholder into a video.
