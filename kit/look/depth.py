"""Depth maps for stills (photos, product shots, b-roll frames), for the 2.5D camera move (kit/hf/parallax.js).

    D=(uv run --no-project --python 3.13 --with transformers --with torch --with pillow)
    $D python -m kit.look.depth films/<video>/assets/photo.jpg [more.png ...]     # -> photo.depth.png next to each

Depth Anything V2 Small (depth-anything/Depth-Anything-V2-Small-hf, Apache-2.0, 99 MB, downloaded once into the
Hugging Face cache). The map is a grayscale PNG the size of the image: white = near, black = far, normalised per
image. It is made once per still, on the CPU or Apple GPU in about a second, and the page only reads the PNG.

Not for his footage: his room stays as shot (OWNER_DEFAULTS §2); this is for stills shown as evidence or b-roll.
A UI screenshot is flat (no depth to move through): put it on a 3D card instead.
"""
import sys
from pathlib import Path

MODEL = "depth-anything/Depth-Anything-V2-Small-hf"


def main():
    paths = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        raise SystemExit(__doc__)
    try:
        import numpy as np
        import torch
        from PIL import Image
        from transformers import pipeline
    except ImportError:
        raise SystemExit("needs transformers + torch: uv run --no-project --python 3.13 --with transformers --with torch "
                         "--with pillow python -m kit.look.depth <image>")
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    pipe = pipeline("depth-estimation", model=MODEL, device=dev)
    for p in paths:
        img = Image.open(p).convert("RGB")
        d = np.asarray(pipe(img)["predicted_depth"].squeeze().float().cpu().numpy(), dtype=np.float32)
        lo, hi = np.percentile(d, 1), np.percentile(d, 99)                  # robust to a few wild pixels
        d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
        out = p.with_suffix(".depth.png")
        Image.fromarray((d * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC).save(out)
        print(f"{p.name}: depth -> {out.name} ({img.size[0]}x{img.size[1]}, {dev})")


if __name__ == "__main__":
    main()
