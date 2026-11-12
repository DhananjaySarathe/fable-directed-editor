"""FIXTURE: the 2026-10-20 motion additions in the kit's looks: kinetic "cascade" and "focus" (kit/hf/kinetic.js), an
icon morph (HF.morph, GSAP MorphSVG) and the "no" shake (HF.shake, CustomWiggle).

    uv run python kit/hf/demos/motion/build.py [look ...]          # -> output/temp/demos/motion/<look>/index.html
    uv run python kit/hf/demos/motion/build.py --sheet             # build, stills mid-motion and settled -> sheet.jpg

Check pages, not edits: the camera is ffmpeg's test pattern (hidden) and the lines are made up.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
OUT = KIT.parent / "output/temp/demos/motion"
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

LOOKS = ["pastel_box", "night", "redline"]
TOTAL = 23.0
AT = [0.75, 1.5, 2.2, 4.8, 6.5, 9.15, 10.45, 11.5, 13.2, 15.2, 17.2, 19.2, 21.0, 22.2]   # ..., grain/mesh/rays/warp, emoji


def build(look):
    d = OUT / look
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    take = d / "assets/take.mp4"
    if not take.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1920x1080:rate=30:duration={TOTAL}",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "32", str(take)], check=True)
    vendor.copy_assets(d)
    D = {"total": TOTAL, "look": look, "words": [], "pieces": [{"out_a": 0, "out_b": TOTAL, "face": [960, 420]}]}
    html = vendor.inline((HERE / "src/template.html").read_text()).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    (d / "index.html").write_text(html.replace("__TOTAL__", str(TOTAL)))
    print(f"{d}/index.html: {look}")
    return d


def sheet(looks):
    rows = []
    for look in looks:
        d = build(look)
        out = OUT / "shots" / look
        shutil.rmtree(out, ignore_errors=True)
        subprocess.run(["npx", "hyperframes", "snapshot", str(d), "--at", ",".join(str(t) for t in AT), "--no-end", "-o", str(out)],
                       check=True, stdin=subprocess.DEVNULL, capture_output=True)
        fr = sorted(out.glob("frame-*.png"))
        r = OUT / f"row_{look}.png"
        ins = sum([["-i", str(p)] for p in fr], [])
        f = "".join(f"[{i}:v]scale=480:270[v{i}];" for i in range(len(fr))) + "".join(f"[v{i}]" for i in range(len(fr))) + f"hstack=inputs={len(fr)}"
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", f, str(r)], check=True)
        rows.append(r)
    stack = ["-filter_complex", f"vstack=inputs={len(rows)}"] if len(rows) > 1 else []
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", str(r)] for r in rows], []) + stack + [str(OUT / "sheet.jpg")], check=True)
    print("->", OUT / "sheet.jpg", f"(rows: {', '.join(looks)}; columns at {AT} s)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")] or LOOKS
    sheet(args) if "--sheet" in sys.argv else [build(lk) for lk in args]
