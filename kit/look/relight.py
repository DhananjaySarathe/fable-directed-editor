"""Depth-based relighting for a talking head (2026-10-26, the owner: Filmora's lighting "adds natural lighting in footage
and gives a premium studio feel... can we also do that?"). grade.py's key light is a 2D gaussian: it brightens an area
but does not know the shape of the face. Here every frame gets a depth map (Depth Anything V2 Small, the model
kit/look/depth.py already uses), the surface normals come from it, and virtual lights shade the person by their shape:
a soft key that wraps round the cheek and nose, a fill, a rim from behind, while the room is set back a little. Only
the person is relit (Apple Vision matte, kit/bin/personseg); the room keeps its own light, darker. Opt-in: nothing in
the pipeline calls it.

    D=(uv run --no-project --python 3.13 --with transformers --with torch --with pillow --with opencv-python-headless)
    $D python -m kit.look.relight clip.mp4 out.mp4 [--preset=studio] [--test=2,6]   (--test: before/after JPGs only)

Presets (PRESETS): studio (soft warm key from the front-left, gentle fill, a faint rim, the room -0.7 stop), dramatic
(a harder key from the side, deeper shadow side, a cool rim, the room -1.3 stops), lamp (a warm low key like a desk
lamp, cool ambient, the room -1.6 stops: night interiors).
It shapes reasonably lit footage; it cannot rescue a dark or blown shot (light it on the day: kit/refs/SHOOT_PLAYBOOK.md).
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
# light directions in camera space: x right, y down, z toward the camera
PRESETS = {
    "studio":   dict(key_dir=(-0.55, -0.30, 0.78), key=0.75, key_col=(1.05, 1.0, 0.94), wrap=0.45, fill=0.30,
                     fill_col=(0.96, 0.99, 1.04), rim_dir=(0.9, -0.25, -0.35), rim=0.22, rim_col=(1.0, 0.97, 0.92),
                     room=0.60, contrast=1.04, gain=1.07),
    "dramatic": dict(key_dir=(-0.85, -0.20, 0.48), key=1.05, key_col=(1.06, 1.0, 0.92), wrap=0.20, fill=0.12,
                     fill_col=(0.92, 0.98, 1.08), rim_dir=(0.95, -0.15, -0.30), rim=0.35, rim_col=(0.85, 0.95, 1.12),
                     room=0.40, contrast=1.10, gain=1.04),
    "lamp":     dict(key_dir=(-0.65, 0.15, 0.74), key=0.75, key_col=(1.12, 0.98, 0.80), wrap=0.30, fill=0.10,
                     fill_col=(0.86, 0.95, 1.12), rim_dir=(0.9, -0.3, -0.3), rim=0.18, rim_col=(0.80, 0.92, 1.15),
                     room=0.33, contrast=1.08, gain=1.02),
}


def frames_of(clip, w=None):
    """All frames of a clip as RGB float32 0..1 (scaled to width w if given), plus fps."""
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height,r_frame_rate", "-of", "json", str(clip)],
                                     capture_output=True, text=True, check=True).stdout)["streams"][0]
    W0, H0 = info["width"], info["height"]
    num, den = map(int, info["r_frame_rate"].split("/"))
    W, H = (w, int(round(H0 * w / W0 / 2)) * 2) if w else (W0, H0)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"scale={W}:{H}:flags=lanczos", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (W * H * 3)
    return np.frombuffer(raw, np.uint8)[: n * W * H * 3].reshape(n, H, W, 3), num / den


def mattes(frames):
    """Apple Vision person mattes (kit/bin/personseg), 0..1 float, one per frame."""
    d = Path(tempfile.mkdtemp())
    (d / "in").mkdir()
    (d / "out").mkdir()
    for k, f in enumerate(frames):
        cv2.imwrite(str(d / "in" / f"f{k + 1:05d}.png"), cv2.cvtColor(f, cv2.COLOR_RGB2BGR))
    subprocess.run([str(ROOT / "kit/bin/personseg"), str(d / "in"), str(d / "out"), "--mask"], check=True, stdout=subprocess.DEVNULL)
    H, W = frames.shape[1:3]
    out = [cv2.resize(cv2.imread(str(d / "out" / f"f{k + 1:05d}.png"), cv2.IMREAD_GRAYSCALE), (W, H)).astype(np.float32) / 255
           for k in range(len(frames))]
    shutil.rmtree(d, ignore_errors=True)
    return out


def depths(frames, ms):
    """Relative depth (near = 1) per frame from Depth Anything V2 Small, each frame's scale and shift fitted to the
    previous one on the person, then smoothed in time, so the light does not flicker."""
    import torch
    from PIL import Image
    from transformers import pipeline
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    pipe = pipeline("depth-estimation", model=MODEL, device=dev)
    H, W = frames.shape[1:3]
    out, prev = [], None
    for f, m in zip(frames, ms):
        d = np.asarray(pipe(Image.fromarray(f))["predicted_depth"].squeeze().float().cpu().numpy(), np.float32)
        d = cv2.resize(d, (W, H), interpolation=cv2.INTER_CUBIC)
        lo, hi = np.percentile(d, 1), np.percentile(d, 99.5)
        d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
        if prev is not None:
            sel = m > 0.5
            if sel.sum() > 500:                                             # fit a, b: a*d + b ~ prev on the person
                A = np.stack([d[sel], np.ones(sel.sum(), np.float32)], 1)
                a, b = np.linalg.lstsq(A, prev[sel], rcond=None)[0]
                d = np.clip(a * d + b, 0, 1.2)
            d = 0.55 * d + 0.45 * prev                                      # temporal smoothing
        out.append(d)
        prev = d
    return out


def normals(d, m, sigma):
    """Surface normals of the person. A monocular depth map sees a person as a near plateau over the room (the big step
    at the silhouette, little relief inside), so the shape is built from two parts: the silhouette inflated into a
    rounded body (a distance-transform dome: the sides of the head and torso turn away like a real volume) and the
    depth map's own relief inside the person (nose, cheeks, folds), re-stretched on the person only."""
    sil = (m > 0.5).astype(np.uint8)
    if sil.sum() < 100:
        return np.dstack([np.zeros_like(d), np.zeros_like(d), np.ones_like(d)])
    dt = cv2.distanceTransform(sil, cv2.DIST_L2, 5)
    dome = np.sqrt(dt / max(dt.max(), 1e-6))
    inner = cv2.erode(sil, np.ones((5, 5), np.uint8), iterations=3) > 0
    lo, hi = np.percentile(d[inner], 2), np.percentile(d[inner], 98)
    rel = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1) * sil
    h = cv2.GaussianBlur(0.75 * dome + 0.25 * rel, (0, 0), sigma)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3)
    k = 1.0 / max(np.percentile(np.hypot(gx, gy)[inner], 90) * 1.2, 1e-5)
    n = np.dstack([-gx * k, -gy * k, np.ones_like(d)])                     # high = near: the surface faces the camera
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n


def unit(v):
    v = np.float32(v)
    return v / np.linalg.norm(v)


def relight_frame(img, d, m, p, face_scale):
    """One frame: the person shaded by the virtual lights over their own light; the room set back."""
    x = img.astype(np.float32) / 255
    m = cv2.GaussianBlur(cv2.erode(m, np.ones((3, 3), np.uint8), iterations=1), (0, 0), 1.5)[..., None]
    n = normals(d, m[..., 0], sigma=max(2.0, face_scale * 0.05))
    L, R = unit(p["key_dir"]), unit(p["rim_dir"])
    ndl = np.clip((n @ L + p["wrap"]) / (1 + p["wrap"]), 0, 1)              # wrapped Lambert: a soft source
    # the key adds light by shape, relative to the mean on the person (the overall exposure stays where it was)
    mean = float((ndl * m[..., 0]).sum() / max(m.sum(), 1))
    key = (ndl - mean)[..., None] * p["key"]
    fill = (1 - ndl)[..., None] * p["fill"] * 0.25
    # the rim: grazing surfaces (normal turned away from the camera) on the rim side
    graze = np.clip(1 - n[..., 2], 0, 1) ** 2.2
    rim = (graze * np.clip(n[..., :2] @ R[:2] / max(np.linalg.norm(R[:2]), 1e-6), 0, 1))[..., None] * p["rim"]
    lum = x.mean(axis=2, keepdims=True)
    lit = x * (1 + key * np.float32(p["key_col"])) + fill * lum * np.float32(p["fill_col"]) + rim * np.float32(p["rim_col"]) * (0.25 + lum)
    lit = (0.5 + (lit - 0.5) * p["contrast"]) * p.get("gain", 1.0)
    # the room: its own light, set back, with a soft falloff so it reads as a lit set, not a cut-out
    yy, xx = np.mgrid[0:x.shape[0], 0:x.shape[1]].astype(np.float32)
    ys, xs = np.nonzero(m[..., 0] > 0.5)
    cy, cx = (ys.mean(), xs.mean()) if len(ys) else (x.shape[0] / 2, x.shape[1] / 2)
    pool = np.exp(-(((xx - cx) / (x.shape[1] * 0.45)) ** 2 + ((yy - cy) / (x.shape[0] * 0.65)) ** 2))[..., None]
    room = x * (p["room"] + (1 - p["room"]) * 0.45 * pool)
    hot = np.clip((lum - 0.72) / 0.22, 0, 1)                               # practicals (lamps, windows) keep glowing
    room = room * (1 - hot) + x * hot
    out = room * (1 - m) + lit * m
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def run(clip, out, preset="studio", test=None):
    p = PRESETS[preset]
    frames, fps = frames_of(clip)
    if test:
        idx = [min(len(frames) - 1, int(t * fps)) for t in test]
        frames = frames[idx]
    print(f"{len(frames)} frames, mattes...")
    ms = mattes(frames)
    print("depth...")
    ds = depths(frames, ms)
    face_scale = frames.shape[2] * 0.06
    relit = [relight_frame(f, d, m, p, face_scale) for f, d, m in zip(frames, ds, ms)]
    if test:
        for t, a, b in zip(test, frames, relit):
            pair = np.concatenate([a, b], axis=1)
            dst = Path(out).with_name(f"{Path(out).stem}_{preset}_{t:g}s.jpg")
            cv2.imwrite(str(dst), cv2.cvtColor(pair, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
            print("->", dst)
        return
    H, W = relit[0].shape[:2]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", f"{fps}",
                            "-i", "-", "-i", str(clip), "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)], stdin=subprocess.PIPE)
    for f in relit:
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    enc.wait()
    print("->", out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        raise SystemExit(__doc__)
    opt = {a.split("=", 1)[0][2:]: a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--") and "=" in a}
    test = [float(t) for t in opt["test"].split(",")] if "test" in opt else None
    run(args[0], args[1], opt.get("preset", "studio"), test)


if __name__ == "__main__":
    main()
