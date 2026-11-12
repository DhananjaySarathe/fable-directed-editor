"""Measure a reference edit's motion: how often things move, how long a move takes, how long holds last, and (with
--box) every move of the speaker's video box. The numbers behind kit/refs/MOTION.md; run it on any reference first.

    python3 kit/refs/motion_ref.py ref.mp4 [--crop=x:y:w:h] [--box=dark|light] [--out=dir] [--strips]

--crop    measure only this region (e.g. one half of a side-by-side comparison)
--box     track the speaker's footage as a box: "dark" = the footage is darker than the stage (a dark room on light
          designed backgrounds, the usual case), "light" = the reverse. Prints every box move: grow / shrink / move /
          enter / exit, with its length in frames
--strips  write a frame-by-frame strip (10 frames at full rate) around each box move to <out>/strip_<t>.jpg
Writes <out>/motion.json (default: next to the video). Pace targets from it go in MOTION.md §2.
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np


def frames(path, crop, fps_out):
    vf = (f"crop={crop}," if crop else "") + f"fps={fps_out},scale=320:-2"
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                           capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h = (int(crop.split(":")[0]), int(crop.split(":")[1])) if crop else (int(probe[0]), int(probe[1]))
    h2 = int(round(320 * h / w / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h2, 320, 3)


def box_of(f, mode):
    """The footage box in one frame: (cx, cy, w, h, area) as fractions, or None."""
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    v, s = hsv[..., 2], hsv[..., 1]
    m = (v < 120) & (s < 200) if mode == "dark" else (v > 150)
    m = m.astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return None
    c = max(cs, key=cv2.contourArea)
    H, W = m.shape
    a = cv2.contourArea(c) / (W * H)
    if a < 0.04:
        return None
    x, y, w, h = cv2.boundingRect(c)
    return ((x + w / 2) / W, (y + h / 2) / H, w / W, h / H, a)


def runs(mask):
    """[(start, length)] of True runs."""
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            out.append((i, j - i)); i = j
        else:
            i += 1
    return out


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    opt = dict(x[2:].split("=", 1) if "=" in x else (x[2:], "1") for x in sys.argv[1:] if x.startswith("--"))
    if not a:
        sys.exit(__doc__)
    src, fps = a[0], 30
    out = Path(opt.get("out", Path(src).with_suffix("").as_posix() + "_motion"))
    out.mkdir(parents=True, exist_ok=True)
    F = frames(src, opt.get("crop"), fps)
    g = np.array([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in F])
    d = np.r_[0, np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))]
    total = len(F) / fps
    cut = d > 28                                                    # a hard change in one frame
    moving = d > 2.2                                                # anything travelling
    mv = [(s / fps, n / fps) for s, n in runs(moving) if n >= 2]
    holds = [n / fps for s, n in runs(~moving) if n >= 6]
    R = {"video": src, "seconds": round(total, 2),
         "cuts": [round(i / fps, 2) for i in np.where(cut)[0]],
         "moves_per_min": round(len(mv) / total * 60, 1),
         "move_len_median": round(float(np.median([x[1] for x in mv])), 3) if mv else None,
         "hold_median": round(float(np.median(holds)), 2) if holds else None,
         "hold_p90": round(float(np.quantile(holds, 0.9)), 2) if holds else None,
         "in_motion_share": round(float(moving.mean()), 3)}
    if "box" in opt:
        B = [box_of(f, opt["box"]) for f in F]
        for k in range(1, len(B) - 1):                              # one-frame dropouts / blips (a flash, a dark graphic)
            if (B[k] is None) != (B[k - 1] is None) and (B[k - 1] is None) == (B[k + 1] is None):
                B[k] = B[k - 1]
        on = np.array([b is not None for b in B])
        full = np.array([b is not None and b[2] > 0.9 and b[3] > 0.9 for b in B])
        R["face_share"] = round(float(on.mean()), 3)
        R["full_share"] = round(float(full.mean()), 3)
        R["longest_away"] = round(max([n for s, n in runs(~on)] or [0]) / fps, 2)
        ev, i = [], 1
        while i < len(B):                                           # a box event: area or centre changes > 4 % per frame
            p, q = B[i - 1], B[i]
            ch = (p is None) != (q is None) or (p and q and (abs(q[4] - p[4]) > 0.02 or abs(q[0] - p[0]) > 0.02 or abs(q[1] - p[1]) > 0.02))
            if not ch:
                i += 1; continue
            j = i
            while j + 1 < len(B):
                p2, q2 = B[j], B[j + 1]
                more = (p2 is None) != (q2 is None) or (p2 and q2 and (abs(q2[4] - p2[4]) > 0.01 or abs(q2[0] - p2[0]) > 0.01))
                if not more:
                    break
                j += 1
            a0, a1 = B[i - 1], B[j]
            kind = ("enter" if a0 is None else "exit" if a1 is None else "grow" if a1[4] > a0[4] * 1.15 else "shrink" if a1[4] < a0[4] / 1.15 else "move")
            ev.append({"t": round((i - 1) / fps, 3), "frames": j - i + 1, "kind": kind,
                       "from": [round(x, 3) for x in a0] if a0 else None, "to": [round(x, 3) for x in a1] if a1 else None})
            i = j + 1
        def real(e):                                                # drop jitter: hands in a full frame, sub-4 % nudges
            a0, a1 = e["from"], e["to"]
            if a0 is None or a1 is None:
                return e["frames"] >= 2
            if min(a0[2], a0[3], a1[2], a1[3]) > 0.88:
                return False
            ratio = max(a1[4], 1e-6) / max(a0[4], 1e-6)
            return abs(a1[0] - a0[0]) > 0.04 or abs(a1[1] - a0[1]) > 0.04 or not (1 / 1.15 < ratio < 1.15)
        ev = [e for e in ev if real(e)]
        R["box_moves"] = ev
        if "strips" in opt:
            for e in ev:
                k0 = max(0, int(e["t"] * fps) - 1)
                strip = np.hstack([F[min(len(F) - 1, k0 + k)] for k in range(10)])
                cv2.imwrite(str(out / f"strip_{e['t']:07.3f}.jpg"), strip)
    (out / "motion.json").write_text(json.dumps(R, indent=1))
    print(f"{Path(src).name}: {R['seconds']} s, {len(R['cuts'])} hard cuts, {R['moves_per_min']} moves/min, move median {R['move_len_median']} s, "
          f"hold median {R['hold_median']} s (p90 {R['hold_p90']}), in motion {R['in_motion_share']:.0%}")
    if "box" in opt:
        print(f"  box: face {R['face_share']:.0%} (full frame {R['full_share']:.0%}), longest away {R['longest_away']} s, {len(R['box_moves'])} moves")
        for e in R["box_moves"]:
            print(f"   {e['t']:7.2f}s  {e['kind']:6s} {e['frames']:2d} frames ({e['frames'] / fps * 1000:.0f} ms)")
    print("->", out / "motion.json")


if __name__ == "__main__":
    main()
