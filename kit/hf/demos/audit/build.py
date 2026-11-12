"""FIXTURE: repro pages for the kit bugs in kit/refs/AUDIT_2026-10-20.md §3 (all hit on films/xchakra, 2026-10-20).

    uv run python kit/hf/demos/audit/build.py        # -> output/temp/demos/audit/{studio,reel,speaker*}/index.html
    node kit/hf/demos/audit/check.mjs                # builds them, then checks every bug (exit 1 if one is back)

studio (16:9, HF.studio, 26 s): say() / line() accents, a box jump cut inside a card, strike() with and without an end,
a chapter card over the full-frame face, HF.code's title bar. reel (9:16, HF.reel, 10 s): a 16:9 camera (src), say()
word times, line() accents, strike() with an end, a jump cut inside a card. The cameras are ffmpeg test patterns and the
words are made up: these are check pages, not edits.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
OUT = KIT.parent / "output/temp/demos/audit"                     # generated files stay out of kit/ (kit/paths.py)
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

PAGES = {
    # name: (template, total s, camera size, words [(text, t)], pieces [(out_a, out_b, src_a, first word, last word)])
    "studio": ("studio.html", 26.0, "1920x1080",
               [("we", 0.5), ("spent", 0.8), ("a", 1.1), ("decade", 1.4), ("on", 4.4), ("code", 4.7), ("tests", 5.0), ("today", 5.3)],
               [(0, 4, 0, 0, 3), (4, 26, 6, 4, 7)]),
    "reel": ("reel.html", 10.0, "1920x1080",
             [("that", 0.5), ("signal", 0.8), ("changed", 1.1), ("so", 4.4), ("practice", 4.7), ("this", 5.0)],
             [(0, 4, 0, 0, 2), (4, 10, 7, 3, 5)]),
}


def build(name):
    tpl, total, size, words, pieces = PAGES[name]
    d = OUT / name
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    take = d / "assets/take.mp4"
    if not take.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30:duration={total + 8}",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "30", str(take)], check=True)
    vendor.copy_assets(d)
    W = [{"i": i, "text": w, "t": t, "e": t + 0.25} for i, (w, t) in enumerate(words)]
    face = [960, 420]                                              # the test pattern's middle, in camera px
    P = [{"out_a": a, "out_b": b, "src_a": s, "src_b": s + b - a, "clip": 0, "w": [w0, w1], "face": face} for a, b, s, w0, w1 in pieces]
    D = {"total": total, "words": W, "pieces": P}
    html = vendor.inline((HERE / "src" / tpl).read_text(), stickman=False).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    (d / "index.html").write_text(html.replace("__TOTAL__", str(total)))
    print(f"{d}/index.html: {total} s (fixture)")


def speaker():
    """speaker / speaker_fallback / speaker_boxhidden / speaker_plate (2026-10-22, kit v11): src/speaker.html, a static
    60 s page with no engine, as is (window.__speaker, __trans, D.tracks), with MODE "fallback" (only window.__faceRect,
    as pages before v11), "boxhidden" (a hidden __box over a full-frame A-roll whose __faceRect gives his face) and
    "plate" (a room plate opens the hook with __faceRect null), for precheck's SPEAKER, DENSITY and transition sections."""
    html = (HERE / "src/speaker.html").read_text()
    for name, mode in (("speaker", "speaker"), ("speaker_fallback", "fallback"), ("speaker_boxhidden", "boxhidden"), ("speaker_plate", "plate")):
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(html.replace('const MODE = "speaker";', f'const MODE = "{mode}";'))
        print(f"{d}/index.html: 60 s (fixture, {mode})")


if __name__ == "__main__":
    for n in (sys.argv[1:] or [*PAGES, "speaker"]):
        speaker() if n == "speaker" else build(n)
