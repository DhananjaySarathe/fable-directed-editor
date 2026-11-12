"""kit/reel: the shared 9:16 Reel pipeline (2026-10-10). A Reel is a recipe, not a fork of the last film's scripts.

A film folder holds only what is particular to that Reel:

    films/<name>/reel.py            the settings: take, room, keep list (whole sentences), judged joins, fixes, beats
    films/<name>/src/template.html  the scenes (HF.reel world + kit scene calls), timed to word ids
    films/<name>/transcript.py      only when the take needs hand-corrected words (optional)
    films/<name>/assets/            screenshots (blurred copies only; raw private ones go in the film's work folder)

and everything else is run from here:

    uv run python -m kit.reel <film> prep      footage: CFR copy, face track, person matte, cleaned voice, look v2 grade
    uv run python -m kit.reel <film> edl       sentence-gated cut -> edl.json, cuts.json, vo.wav, aroll.mp4
    uv run python -m kit.reel <film> joins     audit every piece edge on the voice envelope (no clipped word, no extra
                                               syllable), then re-listen vo.wav with cutcheck --media. Exit 3 = fix first
    uv run python -m kit.reel <film> build     cut-outs + the HyperFrames project (index.html)
    uv run python -m kit.reel <film> sample    the same composition cut to the first SAMPLE seconds (hf_sample/)
    uv run python -m kit.reel <film> render [--sample]   cues -> mix -> render -> mux -> qa
    uv run python -m kit.reel <film> all       prep, edl, joins, build, render

Modules: prep.py (footage), edl.py (the cut, the voice, the picture), joins.py (the voice-cut audit), cutout.py,
build.py (HF project, cues, mix via kit/audio/mix.py, render, mux, qa). The page side is kit/hf/reel.js (HF.reel: the
pastel 9:16 world, the speaker box, word-synced type, captions, and the scene library).
"""
