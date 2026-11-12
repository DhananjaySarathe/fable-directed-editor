"""Track a point on the cut A-roll (work/aroll.mp4, the Reel's own timeline): a person in the background, an object to
pin a label to, a zoom target that should stay steady while the phone shakes.

    from kit.reel import track
    pts = track.point(R, a=7.0, b=9.6, seed=(735, 940), seed_t=8.2)   # -> [[t, x, y, score], ...] at 30 fps

A patch around the seed (at seed_t) is matched frame by frame (normalised cross-correlation) inside a search window
around the last position, forward and backward from seed_t, so short jump cuts inside [a, b] don't lose it. The
template is refreshed slowly (10 %) from confident matches. Positions are smoothed (0.25 s) for zooms; a low score
(< 0.45) keeps the last good position and is reported.
"""
import json
import subprocess

import numpy as np


def frames(R, a, b):
    FPS = R.FPS
    k0, k1 = int(round(a * FPS)), int(round(b * FPS))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(k0 + 0.5) / FPS:.4f}", "-i", str(R.work / "aroll.mp4"), "-frames:v",
                          str(k1 - k0), "-vf", "format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (R.W * R.H)
    return k0, np.frombuffer(raw[: n * R.W * R.H], np.uint8).reshape(n, R.H, R.W)


def point(R, a, b, seed, seed_t, patch=130, search=170, smooth=0.25):
    import cv2
    k0, F = frames(R, a, b)
    n = len(F)
    si = min(n - 1, max(0, int(round(seed_t * R.FPS)) - k0))
    h = patch // 2

    def crop(img, x, y, r):
        x0, y0 = int(max(0, x - r)), int(max(0, y - r))
        return img[y0:int(min(R.H, y + r)), x0:int(min(R.W, x + r))], x0, y0

    tpl0, _, _ = crop(F[si], seed[0], seed[1], h)
    tpl0 = tpl0.astype(np.float32)
    pos = [None] * n
    pos[si] = (float(seed[0]), float(seed[1]), 1.0)
    for step in (1, -1):
        tpl, (x, y) = tpl0.copy(), seed
        i = si + step
        while 0 <= i < n:
            win, x0, y0 = crop(F[i], x, y, h + search)
            if win.shape[0] > tpl.shape[0] and win.shape[1] > tpl.shape[1]:
                res = cv2.matchTemplate(win.astype(np.float32), tpl, cv2.TM_CCOEFF_NORMED)
                _, sc, _, loc = cv2.minMaxLoc(res)
                if sc >= 0.45:
                    x, y = x0 + loc[0] + tpl.shape[1] / 2, y0 + loc[1] + tpl.shape[0] / 2
                    new, _, _ = crop(F[i], x, y, h)
                    if new.shape == tpl.shape and sc > 0.7:
                        tpl = 0.9 * tpl + 0.1 * new.astype(np.float32)
                pos[i] = (float(x), float(y), float(sc))
            else:
                pos[i] = (float(x), float(y), 0.0)
            i += step
    xy = np.array([[p[0], p[1]] for p in pos])
    k = max(1, int(smooth * R.FPS)) | 1
    pad = np.pad(xy, ((k // 2, k // 2), (0, 0)), mode="edge")
    sm = np.stack([np.convolve(pad[:, j], np.ones(k) / k, mode="valid") for j in range(2)], 1)
    out = [[round((k0 + i) / R.FPS, 4), round(float(sm[i, 0]), 1), round(float(sm[i, 1]), 1), round(pos[i][2], 3)] for i in range(n)]
    low = [o[0] for o in out if o[3] < 0.45]
    print(f"track {a:.2f}-{b:.2f}: {n} frames, seed {seed} @ {seed_t}; low-confidence frames: {len(low)}"
          + (f" ({low[0]:.2f}..{low[-1]:.2f})" if low else ""))
    return out


def save(R, name, pts):
    p = R.work / f"track_{name}.json"
    p.write_text(json.dumps(pts))
    return p


def other_face(R, a, b, smooth=0.3, near=None):
    """The face of the OTHER person in the shot (not the speaker's, the largest), per frame of the cut A-roll in [a, b]:
    YuNet at full size (a background face is small). near=(x, y): prefer the face closest to it. Gaps are filled from
    neighbours, then smoothed. Returns [[t, cx, cy, w], ...] (w = the YuNet box width)."""
    import cv2
    from pathlib import Path
    model = str(Path(__file__).resolve().parents[1] / "models/face_detection_yunet_2023mar.onnx")
    FPS = R.FPS
    k0, k1 = int(round(a * FPS)), int(round(b * FPS))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(k0 + 0.5) / FPS:.4f}", "-i", str(R.work / "aroll.mp4"), "-frames:v",
                          str(k1 - k0), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    fb = R.W * R.H * 3
    det = cv2.FaceDetectorYN.create(model, "", (R.W, R.H), 0.5)
    found = []
    for i in range(len(raw) // fb):
        img = np.frombuffer(raw[i * fb:(i + 1) * fb], np.uint8).reshape(R.H, R.W, 3)
        _, faces = det.detect(img)
        pick = None
        if faces is not None and len(faces):
            fs = sorted(faces.tolist(), key=lambda f: -f[2])        # largest first: the speaker
            others = fs[1:] if len(fs) > 1 else ([] if fs[0][2] > 260 else fs)
            if others:
                if near:
                    others.sort(key=lambda f: (f[0] + f[2] / 2 - near[0]) ** 2 + (f[1] + f[3] / 2 - near[1]) ** 2)
                f = others[0]
                pick = (f[0] + f[2] / 2, f[1] + f[3] / 2, f[2])
        found.append(pick)
    n = len(found)
    idx = [i for i, p in enumerate(found) if p]
    if not idx:
        raise SystemExit(f"other_face {a}-{b}: no second face found")
    arr = np.array([found[i] if found[i] else (np.nan,) * 3 for i in range(n)], float)
    for j in range(3):
        col = arr[:, j]
        good = ~np.isnan(col)
        arr[:, j] = np.interp(np.arange(n), np.flatnonzero(good), col[good])
    k = max(1, int(smooth * FPS)) | 1
    pad = np.pad(arr, ((k // 2, k // 2), (0, 0)), mode="edge")
    sm = np.stack([np.convolve(pad[:, j], np.ones(k) / k, mode="valid") for j in range(3)], 1)
    print(f"other_face {a:.2f}-{b:.2f}: found in {len(idx)}/{n} frames")
    return [[round((k0 + i) / FPS, 4), round(float(sm[i, 0]), 1), round(float(sm[i, 1]), 1), round(float(sm[i, 2]), 1)] for i in range(n)]
