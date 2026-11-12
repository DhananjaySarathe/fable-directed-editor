"""One labelled sheet from a folder of stills, so a check looks at one image instead of twelve.

    uv run python kit/qa/stills.py <folder | image ...> [--out=sheet.jpg] [--cols=4] [--width=480]

For the stills of `kit.film <film> snap --at=...` (written to <renders>/snap/): the sheet shows composition, density,
margins and empty plates at a glance. Open a single still at full size only where the sheet raises a question (small
text, an overlap). Each tile is labelled with its file name, which carries the time.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

EXT = {".png", ".jpg", ".jpeg", ".webp"}


def arg(name, default):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def main():
    paths = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        sys.exit(__doc__)
    files = sorted(f for p in paths for f in (p.iterdir() if p.is_dir() else [p]) if f.suffix.lower() in EXT and f.name != "sheet.jpg")
    if not files:
        sys.exit("no images found")
    cols, width = int(arg("cols", 4)), int(arg("width", 480))
    tiles = []
    for f in files:
        im = Image.open(f).convert("RGB")
        im = im.resize((width, round(width * im.size[1] / im.size[0])))
        t = Image.new("RGB", (width, im.size[1] + 20), "white")
        t.paste(im, (0, 20))
        ImageDraw.Draw(t).text((4, 4), f.stem[: width // 7], fill="black")
        tiles.append(t)
    h = max(t.size[1] for t in tiles)
    cols = min(cols, len(tiles))
    sheet = Image.new("RGB", (cols * (width + 6) + 6, -(-len(tiles) // cols) * (h + 6) + 6), (225, 225, 225))
    for k, t in enumerate(tiles):
        sheet.paste(t, (6 + (k % cols) * (width + 6), 6 + (k // cols) * (h + 6)))
    out = Path(arg("out", (paths[0] if paths[0].is_dir() else paths[0].parent) / "sheet.jpg"))
    sheet.save(out, quality=88)
    print(f"{len(tiles)} stills -> {out} ({sheet.size[0]}x{sheet.size[1]})")


if __name__ == "__main__":
    main()
