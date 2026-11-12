"""FIXTURE check of kit/hf/evidence.js (focus, scoreboard, reading holds, quiet moments) on the pastel-box frame.

    uv run python kit/hf/demos/evidence/build.py            # -> output/temp/demos/evidence/hf (16:9, kit inlined)
    uv run python kit/hf/demos/evidence/build.py --reel     # -> output/temp/demos/evidence/reel (9:16 on HF.reel)
    uv run python kit/hf/demos/evidence/build.py --flow     # -> flow_cards / flow_flow: three cards vs one S.flow container
    uv run python kit/hf/demos/evidence/build.py --walk     # -> walk_together / walk_walk: screen camera + cursor, two ways
    node kit/qa/precheck.mjs output/temp/demos/evidence/hf/index.html --holds-out=output/temp/demos/evidence/holds.json

Expected: precheck flags the native-size Slack card in part a as `small` and the twelve-word line as `read`; part b
(the focus zoom) reads at phone size and is a declared hold; part c's scoreboard is big enough. Nothing here is an edit:
the camera is ffmpeg's test pattern and the words are made up.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
OUT = KIT.parent / "output/temp/demos/evidence"                  # generated files stay out of kit/ (kit/paths.py)
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

TOTAL = 22.0
REEL_TOTAL = 14.0
FLOW_TOTAL = 10.0
WALK_TOTAL = 10.0


def take(d, size):
    t = d / "assets/take.mp4"
    if not t.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30:duration={TOTAL}",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "28", str(t)], check=True)


def build():
    d = OUT / "hf"
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    take(d, "1920x1080")
    vendor.copy_assets(d)
    D = {"total": TOTAL, "words": [], "pieces": [{"out_a": 0, "out_b": TOTAL, "face": [960, 400]}]}
    html = vendor.inline((HERE / "src/template.html").read_text(), stickman=False).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    (d / "index.html").write_text(html.replace("__TOTAL__", str(TOTAL)))
    print(f"{d}/index.html: {TOTAL} s (fixture)")


def build_reel():
    d = OUT / "reel"
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    take(d, "1080x1920")
    vendor.copy_assets(d)
    D = {"total": REEL_TOTAL, "words": [], "pieces": [{"out_a": 0, "out_b": REEL_TOTAL, "face": [540, 700]}]}
    mods = vendor.MODULES
    vendor.MODULES = mods + ["reel.js"]                       # as kit/reel/build.py does
    try:
        html = vendor.inline((HERE / "src/reel.html").read_text(), stickman=False).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    finally:
        vendor.MODULES = mods
    (d / "index.html").write_text(html.replace("__TOTAL__", str(REEL_TOTAL)))
    print(f"{d}/index.html: {REEL_TOTAL} s (fixture)")


def build_flow():
    """The flow check: the same prompt -> run -> result as three cards (today) and as one S.flow container."""
    for variant in ("cards", "flow"):
        d = OUT / f"flow_{variant}"
        (d / "assets").mkdir(parents=True, exist_ok=True)
        (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
        take(d, "1920x1080")
        vendor.copy_assets(d)
        D = {"total": FLOW_TOTAL, "variant": variant, "pieces": [{"out_a": 0, "out_b": FLOW_TOTAL, "face": [960, 400]}]}
        html = vendor.inline((HERE / "src/flow.html").read_text(), stickman=False).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
        (d / "index.html").write_text(html.replace("__TOTAL__", str(FLOW_TOTAL)))
        print(f"{d}/index.html: {FLOW_TOTAL} s ({variant}, fixture)")


def build_walk():
    """The screen check: our own precheck output as a terminal screenshot, walked with zoom + cursor keyed together
    (today) and with sd.walk (the cursor leads, the camera follows)."""
    src = OUT / "walk_src/term.png"
    if not src.exists():
        raise SystemExit(f"{src} missing: render walk_src/term.html to it first (see RESEARCH.md, 2026-10-11)")
    for variant in ("together", "walk"):
        d = OUT / f"walk_{variant}"
        (d / "assets").mkdir(parents=True, exist_ok=True)
        (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
        take(d, "1920x1080")
        vendor.copy_assets(d)
        (d / "assets/term.png").write_bytes(src.read_bytes())
        D = {"total": WALK_TOTAL, "variant": variant, "pieces": [{"out_a": 0, "out_b": WALK_TOTAL, "face": [960, 400]}]}
        html = vendor.inline((HERE / "src/walk.html").read_text(), stickman=False).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
        (d / "index.html").write_text(html.replace("__TOTAL__", str(WALK_TOTAL)))
        print(f"{d}/index.html: {WALK_TOTAL} s ({variant}, fixture)")


if __name__ == "__main__":
    if "--walk" in sys.argv:
        build_walk(); sys.exit()
    build_flow() if "--flow" in sys.argv else build_reel() if "--reel" in sys.argv else build()
