"""FIXTURE: the flat diagram (kit/hf/diagram.js style "flat", kit/refs/DIAGRAMS.md; engine-adopt, 2026-10-22). Check
pages, not edits: made-up copy, no numbers, no logos, never his face (his shape is ffmpeg's test pattern).

    flat.html       16:9 whitespace, 28 s: a loop, a process, a hub, layers (one scene per routed type)
    portrait.html   9:16 whitespace, 8 s: a column of four in a Reel's safe band, tags inline, the way back on the right
    legacy_*.html   the old styles as old films call them (films/expensewaale's two diagrams), on paper_studio, before
                    (legacy_old.html) and with v11's opt-in fixes (legacy_fixed.html: margin 120, ports "fan")
    takeover_*.html C.takeover's diagram kind on a canvas: flat on whitespace, circles on canvas_studio

    uv run python kit/hf/demos/diagram/build.py
    node kit/hf/demos/diagram/shoot.mjs        # stills + sheets, the geometry gate, seek purity -> output/temp/demos/diagram/
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
OUT = KIT.parent / "output/temp/demos/diagram"                    # generated files stay out of kit/ (kit/paths.py)
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

PAGES = {"flat": ("flat.html", 28, {}), "portrait": ("portrait.html", 8, {}),
         "legacy_old": ("legacy.html", 10, {"look": "paper_studio", "fixed": False}),
         "legacy_fixed": ("legacy.html", 10, {"look": "paper_studio", "fixed": True}),
         "takeover_whitespace": ("takeover.html", 14, {"look": "whitespace"}),
         "takeover_canvas_studio": ("takeover.html", 14, {"look": "canvas_studio"})}


def room():
    """assets/room.jpg: ffmpeg's test pattern at 1920 x 1080 (never a real take: the fixture shows no face)."""
    j = OUT / "assets/room.jpg"
    j.parent.mkdir(parents=True, exist_ok=True)
    if not j.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=1", "-frames:v", "1", "-q:v", "4", str(j)], check=True)
    return [1920, 1080], [960, 500]


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    vendor.copy_assets(OUT)
    src, at = room()
    for name in sys.argv[1:] or PAGES:
        tpl, total, D = PAGES[name]
        D = dict(D, src=src, at=at, pieces=[{"out_a": 0, "out_b": total, "face": at}])
        html = vendor.inline((HERE / "src" / tpl).read_text()).replace("/*DATA*/", json.dumps(D)).replace("__TOTAL__", str(total))
        (OUT / f"{name}.html").write_text(html)
        print(OUT / f"{name}.html")
