"""A light, measured grade for a one-camera podcast (the owner: "a little bit of color grading").

One grade for the episode (one camera, one light): read the skin of both faces on 8 frames, then
  - white balance: move the skin's R/G and B/G halfway toward a natural skin ratio (at most +-8 % per channel);
  - exposure: move the faces' luma halfway toward 0.52 (at most +-0.5 stop);
  - a soft S-curve (LOOK contrast), saturation a touch up (LOOK sat), warmth a touch (LOOK warmth);
  - phone footage: light temporal denoise (hqdn3d) and luma sharpening, a gentle vignette.
It never pushes skin toward a palette. The filter string is applied per shot after the crop (fast on long episodes).
"""
import subprocess

import numpy as np

SKIN_RG, SKIN_BG, FACE_Y = 1.28, 0.82, 0.52


def frame(src, t, w=960):
    from kit.podcast.render import tonemap
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", "-vf", f"{tonemap(src)}scale={w}:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    h = len(raw) // (w * 3)
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32) / 255.0


def measure(src, duration, people, n=8):
    rs = []
    for t in np.linspace(duration * 0.08, duration * 0.92, n):
        im = frame(src, t)
        H, W = im.shape[:2]
        for p in people:
            b = p["box"]
            x0, x1 = int((b["x"] + b["w"] * 0.28) * W), int((b["x"] + b["w"] * 0.72) * W)
            y0, y1 = int((b["y"] + b["h"] * 0.45) * H), int((b["y"] + b["h"] * 0.68) * H)   # the cheeks, under the eyes
            patch = im[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3)
            if len(patch) > 50:
                rs.append(np.median(patch, axis=0))
    if not rs:
        return {"r": 1.0, "g": 1.0, "b": 1.0, "exp": 1.0}
    m = np.median(np.array(rs), axis=0)
    r, g, b = m
    gr = np.clip(1 + 0.5 * (SKIN_RG * g / max(r, 1e-3) - 1), 0.92, 1.08)
    gb = np.clip(1 + 0.5 * (SKIN_BG * g / max(b, 1e-3) - 1), 0.92, 1.08)
    y = 0.2126 * r * gr + 0.7152 * g + 0.0722 * b * gb
    exp = float(np.clip(1 + 0.5 * (FACE_Y / max(y, 1e-3) - 1), 2 ** -0.5, 2 ** 0.5))
    return {"r": float(gr), "g": 1.0, "b": float(gb), "exp": exp, "skin": [round(float(v), 3) for v in m]}


def filters(meas, look):
    c, s, w = look.get("contrast", 1.06), look.get("sat", 1.06), look.get("warmth", 0.02)
    k = meas["exp"]
    rr, bb = meas["r"] * (1 + w) * k, meas["b"] * (1 - w) * k
    curve = f"0/0 0.25/{0.25 - 0.03 * (c - 1) / 0.06:.3f} 0.75/{0.75 + 0.03 * (c - 1) / 0.06:.3f} 1/1"
    # 2026-10-12, the owner on the first episode: "the quality of the video has been decreased" next to his original.
    # A 100 % comparison showed hqdn3d waxing skin and beard, unsharp haloing the glasses, and the vignette darkening the
    # frame. They are opt-in now (LOOK denoise / sharpen / vignette): the iPhone already denoises, and lanczos is enough.
    return ",".join(
        (["hqdn3d=1.5:1.5:4:4"] if look.get("denoise") else []) + [
        f"colorchannelmixer=rr={rr:.4f}:gg={k:.4f}:bb={bb:.4f}",
        f"curves=all='{curve}'",
        f"eq=saturation={s:.3f}",
    ] + (["unsharp=5:5:0.5:5:5:0.0"] if look.get("sharpen") else [])
      + (["vignette=angle=PI/6:mode=forward"] if look.get("vignette") else [])
      + ([look["extra"]] if look.get("extra") else []))       # a per-episode finish, e.g. calmer greens (films/guest-podcast)
