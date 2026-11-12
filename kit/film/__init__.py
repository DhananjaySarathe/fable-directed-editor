"""kit/film: the shared film pipeline (2026-10-20, kit/refs/AUDIT_2026-10-20.md phase 4). A film is a recipe, not a copy
of the last film's edl.py / build.py / audio.py:

    films/<name>/film.py            the settings: SOURCES, KEEP (whole sentences), JUDGED, fixes, spellings, MUSIC, REELS
    films/<name>/visual_plan.json   the scene plan (kit/refs/SCENES.md; python3 kit/hf/plan_check.py)
    films/<name>/src/template.html  the scenes, timed to word ids and tags, on the look's frame
    films/<name>/assets/            screenshots (blurred copies only)
    films/<name>/reels/<r>/template.html   each Reel's page (its sentences are in film.py REELS)

and every step runs from here (README.md has the details):

    uv run python -m kit.film <film> prep      words (shorts probe + analyze), a 4K picture copy, the cleaned voice
                                               (WPE when the mics differ, DeepFilterNet3) and its measured EQ
    uv run python -m kit.film <film> cut       cutcheck gate -> work/edl.json, cuts.json, vo.wav (+ room tone), one
                                               track per name, faces
    uv run python -m kit.film <film> joins     every edge on the voice envelope, then whisper on every join (exit 2)
    uv run python -m kit.film <film> grade     look v2 on the cut's camera track (the room as shot by default)
    uv run python -m kit.film <film> build     the HyperFrames page (F.hf) + captions.srt
    uv run python -m kit.film <film> mix       vo.wav + beds + the page's cues -> mix.wav (-14 LUFS)
    uv run python -m kit.film <film> draft     build, lint, cues, precheck, mix, a 1080p draft, mux, qa.py
    uv run python -m kit.film <film> render    the same checks, the 4K render in chunks, mux, qa.py
    uv run python -m kit.film <film> mux       raw.mp4 + mix.wav -> output/final/<film>/<OUT>
    uv run python -m kit.film <film> reels     the Reels from the finished film, by whole sentences
    uv run python -m kit.film <film>/reels/<r> build | mix | draft | render | mux

Modules: config.py (film.py + defaults + folders), prep.py, cut.py, grade.py, build.py, mix.py, render.py, reels.py. They lean on
kit/cut (edges, cutcheck, relisten, respell), kit/audio/mix.py, kit/hf (vendor, render4k), kit/qa and kit/look/faces.py.
The worked example: kit/film/example (an ffmpeg test pattern and a synthetic voice, end to end).
"""
