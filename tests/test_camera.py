"""kit/motion/camera.py: the motion-blur bake must show the same picture as the page's unblurred A-roll."""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit/motion"))
import camera  # noqa: E402

pytestmark = pytest.mark.skipif(subprocess.run(["node", "--version"], capture_output=True).returncode != 0, reason="needs node")

# HF.motion.at(P, t).m per frame: the CSS matrix the page puts on the A-roll when nothing is baked (the same motion.js)
AT_JS = """
const fs = require("fs"), vm = require("vm"), ctx = vm.createContext({ console });
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), ctx);
const { plan, frames } = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(frames.map((f) => ctx.HF.motion.at(plan, f / plan.fps).m)));
"""


def page_matrices(P: dict, frames: list[int], tmp: Path) -> list:
    js = tmp / "at.cjs"
    js.write_text(AT_JS)
    plan = {k: v for k, v in P.items() if k != "windows"}
    out = subprocess.run(["node", str(js), str(ROOT / "kit/hf/motion.js")], input=json.dumps({"plan": plan, "frames": frames}),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def portrait_take(path: Path, seconds: float = 4.0) -> np.ndarray:
    """A still 1080x1920 selfie stand-in: a smooth lit "face" around (540, 700) (motion blur barely changes it) over a
    shirt of vertical stripes from y 1150 down (what the misread bake showed). Returns the frame as the bake decodes it."""
    w, h, n = 1080, 1920, int(seconds * 30)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    blob = np.exp(-((xx - 540) ** 2 + (yy - 700) ** 2) / (2 * 260.0 ** 2))
    img = np.stack([60 + 150 * blob + 0.02 * xx, 50 + 120 * blob + 0.03 * yy, 40 + 90 * blob], -1)
    shirt = yy >= 1150
    img[shirt] = np.where((xx[shirt] // 24 % 2)[:, None] > 0, [40, 90, 170], [200, 140, 60])
    rgb = np.clip(img, 0, 255).astype(np.uint8).tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", "30", "-i", "-",
                    "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-pix_fmt", "yuv444p", "-g", "1", str(path)],
                   input=rgb * n, check=True)
    return camera._decode(path, 1, 1, 30, (w, h))[0]


def read_clip(path: Path, size: tuple[int, int]) -> np.ndarray:
    w, h = size
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "yuv444p", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 3, h, w).transpose(0, 2, 3, 1)


def test_panel_bake_shows_the_face_the_page_shows(tmp_path):
    """9:16 panel (a 1080x1920 take in a 1080x1000 panel at y 920): every baked frame of a snap matches the page's own
    unblurred frame over the face. The bug: the take was decoded as 1920x1080 (the same byte count), so the bake showed
    the shirt's rows stretched with vertical streaks instead of the face."""
    take = tmp_path / "aroll.mp4"
    src = portrait_take(take)
    words = [{"i": i, "t": 0.3 + 0.4 * i, "e": 0.6 + 0.4 * i, "text": t}
             for i, t in enumerate("So here is the joke I told you about today.".split())]
    P = camera.plan({"pieces": [{"out_a": 0, "out_b": 4, "face": [540, 700, 420], "tag": "a"}], "words": words, "fps": 30,
                     "mode": "panel", "top": 920, "width": 1080, "height": 1920, "src": [1080, 1920], "format": "reel",
                     "tags": {"joke": [4]}, "auto": False})
    assert P["view"] == [1080, 1000] and [w["view"] for w in P["windows"]] == [[1080, 1000]]
    (w,) = camera.bake(take, P, tmp_path / "aroll_motion")["windows"]
    assert (w["view"], w["top"], w["src"]) == ([1080, 1000], 920, "aroll_motion_1080x1000.mp4")
    baked = read_clip(tmp_path / w["src"], (1080, 1000))
    assert len(baked) == w["f1"] - w["f0"]
    for k, (a, b, c, d, e, f) in enumerate(page_matrices(P, list(range(w["f0"], w["f1"])), tmp_path)):
        page = cv2.warpAffine(src, np.array([[a, c, e], [b, d, f]]), (1080, 1000), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
        fx, fy = round(a * 540 + c * 700 + e), round(b * 540 + d * 700 + f)       # the face centre in the panel
        box = (slice(max(0, fy - 250), fy + 250), slice(fx - 300, fx + 300))
        diff = np.abs(baked[k][box].astype(np.float32) - page[box])
        # the fixed bake is within 0.2 levels (3 on the snap's fastest frame: real blur); the misread one was 21-40 off
        assert diff.mean() < 5.0, f"frame {w['f0'] + k}: the face is off by {diff.mean():.1f} levels"


def test_bake_refuses_a_take_that_is_not_the_plans_source(tmp_path):
    take = tmp_path / "aroll.mp4"
    portrait_take(take, seconds=0.2)
    P = {"fps": 30, "src": [1920, 1080], "windows": [{"f0": 1, "f1": 2, "view": [1920, 1080], "top": 0, "frames": [[[1, 0, 0, 1, 0, 0]]]}]}
    with pytest.raises(SystemExit, match="1080x1920"):
        camera.bake(take, P, tmp_path / "aroll_motion")
