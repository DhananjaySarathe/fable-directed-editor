"""FIXTURE: takeovers and transitions (kit/hf/trans.js; kit/hf/README.md "Takeovers and transitions"). A check page, not
an edit: made-up copy, no numbers, a generic mock UI.

canvas page (src/template.html, 56 s, any canvas look): his card on a canvas, four takeovers, one of each kind (type,
list, evidence, diagram), a chapter beat, and every transition kind in a row the budget allows:
    6.0 whip (C.cam) -> 9.5 zoom (into the type takeover, out of a card) -> 13.5 fade (his card back) -> 18.0 zoom
    (T.zoomThrough, station to station) -> 21.0 card (his card becomes the list card) -> 25.0 zoom (out of the list
    into the next station) -> 31.0 chapter (from his eyes) -> 32.8 zoom (out of it) -> 36.0 cut (into the evidence
    takeover) -> 40.0 card (his card grows back out of the window) -> 45.5 match (a chip flies into the diagram) ->
    49.5 fade. Face off 31 % (each takeover 4 s, 3 s or more of face between two; the hook opens on his face).
studio page (src/studio.html, 30 s): HF.studio { look: "whitespace" } with two S.takeover scenes (type in a cut, list in
a card out of the pill), the box beat "takeover" bringing back his previous shape; reel page (src/reel.html, 28 s, 9:16):
HF.reel { look: "whitespace" } with a statement and an evidence close-up sized for the portrait frame.

    uv run python kit/hf/demos/takeover/build.py [--room <image or take>] [--at x,y] [look ...]
    node kit/hf/demos/takeover/shoot.mjs [page ...]      # stills at every transition's start / peak / end + sheets

Pages go to output/temp/demos/takeover/<look>.html, studio_whitespace.html and reel_whitespace.html (default looks:
whitespace canvas_studio).
His shape shows a still (assets/room.jpg): ffmpeg's test pattern unless --room names a real image or take (a frame at
12 s), which stays local (his face is never committed; kit/refs/me). --at: his face in that still's px.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
OUT = KIT.parent / "output/temp/demos/takeover"                   # generated files stay out of kit/ (kit/paths.py)
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

TOTAL, STUDIO_TOTAL, REEL_TOTAL = 56.0, 30.0, 28.0


def size(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def room(src):
    """assets/room.jpg (his shape on the canvas) and assets/room169.jpg (the studio's 16:9 A-roll), from a real image or
    take, or the test pattern; rebuilt only when asked."""
    a = OUT / "assets"
    a.mkdir(parents=True, exist_ok=True)
    j, j169, j916 = a / "room.jpg", a / "room169.jpg", a / "room916.jpg"
    if src:
        pre = ["-ss", "12"] if src.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm") else []
        subprocess.run(["ffmpeg", "-v", "error", "-y", *pre, "-i", str(src), "-frames:v", "1", "-q:v", "3", str(j)], check=True)
    elif not j.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=1", "-frames:v", "1", "-q:v", "4", str(j)], check=True)
    w, h = size(j)
    ch = min(h, round(w * 9 / 16))                                # the studio's A-roll: 16:9 out of it, at 1920 x 1080
    y0 = max(0, min(h - ch, round(h * 0.42 - ch / 2)))
    if src or not j169.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(j), "-vf", f"crop={w}:{ch}:0:{y0},scale=1920:1080",
                        "-q:v", "3", str(j169)], check=True)
    cw = min(w, round(h * 9 / 16))                                # the Reel's A-roll: 9:16 out of it, at 1080 x 1920
    x0 = max(0, min(w - cw, round(w / 2 - cw / 2)))
    if src or not j916.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(j), "-vf", f"crop={cw}:{h}:{x0}:0,scale=1080:1920",
                        "-q:v", "3", str(j916)], check=True)
    return w, h, y0, ch, x0, cw


def build(name, template, D, total):
    html = vendor.inline((HERE / "src" / template).read_text()).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    (OUT / f"{name}.html").write_text(html.replace("__TOTAL__", str(int(total))))
    print(OUT / f"{name}.html")


if __name__ == "__main__":
    args = sys.argv[1:]
    src, at = None, None
    if "--room" in args:
        i = args.index("--room")
        src = Path(args[i + 1]).expanduser().resolve()
        del args[i:i + 2]
    if "--at" in args:
        i = args.index("--at")
        at = [float(v) for v in args[i + 1].split(",")]
        del args[i:i + 2]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    vendor.copy_assets(OUT)
    w, h, y0, ch, x0, cw = room(src)
    at = at or [w * 0.5, h * 0.48]
    pieces = [{"out_a": 0, "out_b": TOTAL, "face": [at[0], at[1]]}]
    for lk in args or ["whitespace", "canvas_studio"]:
        build(lk, "template.html", {"total": TOTAL, "look": lk, "src": [w, h], "at": at, "pieces": pieces}, TOTAL)
    # the studio page's A-roll is the 16:9 crop (1920 x 1080): his face where the crop put it
    k = 1920 / w
    build("studio_whitespace", "studio.html", {"total": STUDIO_TOTAL, "look": "whitespace",
          "pieces": [{"out_a": 0, "out_b": STUDIO_TOTAL, "face": [round(at[0] * k), round((at[1] - y0) * 1080 / ch)]}]}, STUDIO_TOTAL)
    # the Reel's A-roll is the 9:16 crop (1080 x 1920)
    build("reel_whitespace", "reel.html", {"total": REEL_TOTAL, "look": "whitespace",
          "pieces": [{"out_a": 0, "out_b": REEL_TOTAL, "face": [round((at[0] - x0) * 1080 / cw), round(at[1] * 1920 / h)]}]}, REEL_TOTAL)
