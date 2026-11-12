"""STILLS of the Redline preset (kit/presets/redline): every component on one 16:9 page and one 9:16 page.

    uv run python kit/hf/demos/redline/build.py           # -> output/temp/demos/redline/{hf,reel}/index.html
    uv run python kit/hf/demos/redline/build.py --snap    # ... and snapshot the stills into output/temp/demos/redline/stills
    node kit/qa/precheck.mjs output/temp/demos/redline/hf/index.html

FIXTURE, not an edit: the words and times are made up, the camera is a still. With the owner's photo in
kit/refs/me/peek.png (local only, never in git) the stand-in camera and the peek use his face; without it a grey
silhouette stands in. The screens are real captures already published in his films (ExpenseWaale's site, Gemini's
usage limit).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
ROOT = KIT.parent
OUT = ROOT / "output/temp/demos/redline"                  # generated files stay out of kit/ (kit/paths.py)
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

TOTAL, REEL_TOTAL = 47.5, 20.0
PEEK = KIT / "refs/me/peek.png"
SHOTS = {"site.png": ROOT / "films/expensewaale/assets/web/live.png", "limit.png": ROOT / "films/ai-portfolio/assets/gemini_limit.png"}
# the 16:9 page's still frames (after each scene's marks are down) and the Reel's
SNAP = [3.2, 12.6, 18.6, 25.6, 30.4, 35.8, 39.1, 42.3, 46.0]
SNAP_REEL = [3.0, 8.6, 12.8, 18.4]


def words(script, t0, wps=2.9):
    """Made-up word timings for a line: [{i, text, t, e}], ~2.9 words a second with a beat after punctuation."""
    out, t = [], t0
    for i, w in enumerate(script.split(), start=len(words.acc)):
        d = 0.18 + 0.045 * len(w)
        out.append({"i": i, "text": w, "t": round(t, 3), "e": round(t + d, 3)})
        t += 1 / wps + (0.25 if w[-1] in ",.?!" else 0)
    words.acc.extend(out)
    return out


words.acc = []


def peek_png(d):
    """The cut-out that rises from the bottom edge (his photo if present, else a silhouette)."""
    dst = d / "assets/peek.png"
    if PEEK.exists():
        dst.write_bytes(PEEK.read_bytes())
        return
    im = Image.new("RGBA", (760, 470), (0, 0, 0, 0))
    g = ImageDraw.Draw(im)
    g.ellipse([150, 30, 610, 620], fill=(120, 116, 110, 255))
    im.save(dst)


def take(d, w, h, face_w):
    """The stand-in camera: the peek photo on a plain warm wall, as a still clip (a real take replaces it)."""
    t = d / "assets/take.mp4"
    peek = d / "assets/peek.png"
    im = Image.new("RGB", (w, h), (214, 208, 198))
    p = Image.open(peek).convert("RGBA")
    p = p.resize((face_w, round(p.height * face_w / p.width)))
    im.paste(p, ((w - p.width) // 2, h - p.height), p)
    png = d / "assets/take.png"
    im.save(png)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(png), "-t", str(TOTAL), "-r", "30", "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-tune", "stillimage", "-crf", "24", str(t)], check=True)


def stage(name, w, h, face_w, template, data, total, reel=False):
    d = OUT / name
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    for k, src in SHOTS.items():
        (d / "assets" / k).write_bytes(src.read_bytes())
    peek_png(d)
    take(d, w, h, face_w)
    vendor.copy_assets(d)
    mods = vendor.MODULES
    if reel:
        vendor.MODULES = mods + ["reel.js"]                       # as kit/reel/build.py does
    try:
        html = vendor.inline((HERE / "src" / template).read_text(), stickman=False)
    finally:
        vendor.MODULES = mods
    html = html.replace("/*DATA*/", "const D = " + json.dumps(data) + ";").replace("__TOTAL__", str(total))
    (d / "index.html").write_text(html)
    print(f"{d}/index.html: {total} s (fixture)")
    return d


def build():
    words.acc = []
    W = {
        "a": words("I rebuilt the whole app in six hours, and the model was not the hard part.", 6.3),
        "b": words("Look at the promise on this page.", 13.0),
        "c": words("Six hours in, I hit the wall.", 21.0),
        "d": words("Six hours, idea to a live app.", 27.4),
        "e": words("And honestly, the bug was mine.", 40.2),
    }
    D = {"total": TOTAL, "words": words.acc, "pieces": [{"out_a": 0, "out_b": TOTAL, "face": [960, 700]}], "w": {k: [v[0]["i"], v[-1]["i"]] for k, v in W.items()}}
    return stage("hf", 1920, 1080, 1180, "template.html", D, TOTAL)


def build_reel():
    words.acc = []
    W = {
        "a": words("Claude built it, I fixed it.", 0.4),
        "b": words("Six hours in, Gemini stopped me cold.", 4.6),
        "c": words("So I opened the code and read every line myself.", 10.2),
        "d": words("Six hours. One live app.", 15.4),
    }
    D = {"total": REEL_TOTAL, "words": words.acc, "pieces": [{"out_a": 0, "out_b": REEL_TOTAL, "face": [540, 1500]}], "w": {k: [v[0]["i"], v[-1]["i"]] for k, v in W.items()}}
    return stage("reel", 1080, 1920, 1040, "reel.html", D, REEL_TOTAL, reel=True)


def snap(d, times, out):
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1")
    subprocess.run(["npx", "hyperframes", "snapshot", str(d), "--at", ",".join(f"{t:g}" for t in times), "--no-end", "--describe", "false",
                    "-o", str(out)], check=True, env=env, cwd=ROOT)


if __name__ == "__main__":
    hf, reel = build(), build_reel()
    if "--snap" in sys.argv:
        snap(hf, SNAP, OUT / "stills/hf")
        snap(reel, SNAP_REEL, OUT / "stills/reel")
