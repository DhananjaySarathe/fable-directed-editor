"""FIXTURE: the whitespace still sheet (kit/presets/whitespace/README.md §6). One canvas page with the pieces a film
uses: his card (the hook), a statement takeover, a system diagram (cards + beams), an evidence close-up (a window, a
highlighter, a source chip), a chart card that lands, and the overview. The same page builds in any canvas look, so
whitespace sits next to canvas_studio scene for scene. Made-up copy, no numbers, a generic mock UI. A check page, not an edit.

    uv run python kit/presets/whitespace/sheet/build.py [--room <take.mp4>] [look ...]
    node kit/presets/whitespace/sheet/shoot.mjs [look ...]          # builds, then stills + <look>_sheet.png

Pages go to output/temp/demos/whitespace_sheet/<look>.html (default looks: whitespace canvas_studio). His card shows
ffmpeg's test pattern unless --room names a real take (its first 24 s at 1080p): the sheet in the README was looked at
with an oss-editor take, which stays local (his face is never committed; kit/refs/me).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
OUT = KIT.parent / "output/temp/demos/whitespace_sheet"            # generated files stay out of kit/ (kit/paths.py)
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

TOTAL = 24.0


def room(src):
    # his card's footage: a real take (scaled to 1080p, the first 24 s) or the test pattern; rebuilt only when asked
    take = OUT / "assets/room.mp4"
    take.parent.mkdir(parents=True, exist_ok=True)
    if src:
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-t", str(TOTAL), "-vf", "scale=1920:1080", "-an",
               "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "24", str(take)]
    elif not take.exists():
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1920x1080:rate=30:duration={TOTAL}",
               "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "32", str(take)]
    else:
        return
    subprocess.run(cmd, check=True)


def build(look):
    D = {"total": TOTAL, "look": look}
    html = vendor.inline((HERE / "template.html").read_text()).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    (OUT / f"{look}.html").write_text(html.replace("__TOTAL__", str(int(TOTAL))))
    print(OUT / f"{look}.html")


if __name__ == "__main__":
    args = sys.argv[1:]
    src = None
    if "--room" in args:
        i = args.index("--room")
        src = Path(args[i + 1]).expanduser().resolve()
        del args[i:i + 2]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    vendor.copy_assets(OUT)
    room(src)
    for lk in args or ["whitespace", "canvas_studio"]:
        build(lk)
