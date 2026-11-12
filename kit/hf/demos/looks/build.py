"""FIXTURE: the same kit components in every look (kit/refs/AUDIT_2026-10-20.md §6, phase 3: components that follow the look).

    uv run python kit/hf/demos/looks/build.py           # -> output/temp/demos/looks/<look>/index.html, one page per look
    node kit/hf/demos/looks/check.mjs                   # builds them, then measures contrast, errors and takes stills

Each page draws a pull request and a stamp (0-4 s), a checklist and a note (4-8 s), a scoreboard and a flow (8-12 s), a
code window and a before/after (12-16 s), a sketch, a stickman and a marker note (16-20 s), in one look: pastel_box,
canvas_studio, redline, night, paper_studio, paper_collage, whitespace (HF.canvas { look: "whitespace" }) and
whitespace:studio (the same look through HF.studio { look }, 2026-10-22). The camera is ffmpeg's test pattern (hidden: the
box is "graphic" throughout) and the content is made up. These are check pages, not edits.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
OUT = KIT.parent / "output/temp/demos/looks"                     # generated files stay out of kit/ (kit/paths.py)
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

TOTAL = 20.0
LOOKS = ["pastel_box", "canvas_studio", "redline", "night", "paper_studio", "paper_collage", "whitespace", "whitespace:studio"]


def build(look):
    # "look:frame" draws the look through another frame (whitespace:studio = HF.studio { look: "whitespace" }); its page
    # lives in <look>_<frame>/
    lk, frame = look.split(":") if ":" in look else (look, None)
    d = OUT / look.replace(":", "_")
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    take = d / "assets/take.mp4"
    if not take.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1920x1080:rate=30:duration={TOTAL}",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "32", str(take)], check=True)
    vendor.copy_assets(d)
    D = {"total": TOTAL, "look": lk, "frame": frame, "words": [], "pieces": [{"out_a": 0, "out_b": TOTAL, "face": [960, 420]}]}
    html = vendor.inline((HERE / "src/template.html").read_text()).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    (d / "index.html").write_text(html.replace("__TOTAL__", str(TOTAL)))
    print(f"{d}/index.html: {look}")


if __name__ == "__main__":
    for lk in (sys.argv[1:] or LOOKS):
        build(lk)
