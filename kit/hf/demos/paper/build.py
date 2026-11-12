"""STYLE SAMPLE of the paper-collage look (kit/hf/paper.js, kit/presets/paper_collage): a 9 s 9:16 page, no voice.

    uv run python kit/hf/demos/paper/build.py <hero image> <screenshot png>     # -> output/temp/demos/paper/hf
    npx hyperframes render output/temp/demos/paper/hf -o output/temp/demos/paper/sample.mp4 --fps 30 --quality draft

The hero image is cut out with Apple Vision (kit/look/objects.py's fgcut). Only the owner's own images go in.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kit/hf"))
import vendor  # noqa: E402
from kit.look.objects import cut  # noqa: E402

OUT = ROOT / "output/temp/demos/paper/hf"
TOTAL = 9.0


def build(hero: Path, shot: Path):
    (OUT / "assets/cut").mkdir(parents=True, exist_ok=True)
    (OUT / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    info = cut(hero, OUT / "assets/cut/hero.png")
    if not info["ok"]:
        raise SystemExit(f"no object found in {hero}")
    shutil.copy2(shot, OUT / "assets/term.png")
    vendor.copy_assets(OUT)
    html = vendor.inline((HERE / "src/template.html").read_text(), stickman=False).replace("/*DATA*/", "const D = " + json.dumps({"total": TOTAL}) + ";")
    (OUT / "index.html").write_text(html.replace("__TOTAL__", str(TOTAL)))
    print(f"{OUT}/index.html ({TOTAL} s, style sample); hero cut {info.get('w')}x{info.get('h')}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    build(Path(sys.argv[1]), Path(sys.argv[2]))
