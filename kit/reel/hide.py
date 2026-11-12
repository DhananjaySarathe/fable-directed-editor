"""Hide a bystander's face in the cut A-roll: a heavy feathered blur + an emoji over every frame they are in (2026-10-11,
the owner: "make sure my friend who is beside me is not recognizable… put an emoji and a little bit of blur around it").

    uv run python -m kit.reel films/<name> hide        (detect + bake; build then uses work/aroll_hidden.mp4)

reel.py:  HIDE = dict(emoji="🤓", scale=1.25, blur=1.7,   # emoji size and blur radius as multiples of the face width
                 words=[(0, 40), (238, 257)])         # only the shots the bystander is in (word id ranges)

detect(R): YuNet on every frame of work/aroll.mp4 (low threshold: a bowed head still counts). The speaker is the face in
work/aroll.track.json; any other face is the bystander. Gaps up to 0.6 s are bridged, and every run is held 0.25 s past
its ends (a face must never flash through). -> work/hide.json [[cx, cy, w] or null] per frame. Check it with the
contact sheet bake() writes (work/hide_check.jpg, every 0.5 s): every frame the bystander is in must show the emoji.
bake(R): the blur + emoji burnt into the frames -> work/aroll_hidden.mp4 (same timing, audio-less like aroll.mp4), so
every layout (full, crash zoom, split card, face circle) hides them without per-layout code.
"""
import json
import subprocess
from pathlib import Path

import numpy as np

MODEL = Path(__file__).resolve().parents[1] / "models/face_detection_yunet_2023mar.onnx"
APPLE_EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"


def _frames(R, src):
    """Yield BGR frames of a 1080x1920 video."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    fb = R.W * R.H * 3
    while True:
        b = p.stdout.read(fb)
        if len(b) < fb:
            break
        yield np.frombuffer(b, np.uint8).reshape(R.H, R.W, 3)
    p.wait()


def windows(R):
    """Output-time windows to search: the pieces holding HIDE["words"] [(first id, last id), ...] (the shots the bystander
    is really in; elsewhere the detector finds bits of the speaker's own close, cropped face). None = everywhere."""
    rng = (getattr(R, "HIDE", None) or {}).get("words")
    if not rng:
        return None
    edl = json.load(open(R.dir / "edl.json"))
    return [(p["out_a"], p["out_b"]) for p in edl["pieces"] if any(p["w"][0] <= b and p["w"][1] >= a for a, b in rng)]


def detect(R, thr=0.45, gap=0.6, hold=0.25):
    import cv2
    spk = json.load(open(R.work / "aroll.track.json"))
    win = windows(R)
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (R.W, R.H), thr)
    found = []
    for i, img in enumerate(_frames(R, R.work / "aroll.mp4")):
        if win is not None and not any(a - 0.02 <= i / R.FPS < b + 0.02 for a, b in win):
            found.append(None)
            continue
        sx, sy, sw = spk[min(i, len(spk) - 1)][:3]
        _, faces = det.detect(img)
        best = None
        for f in (faces.tolist() if faces is not None else []):
            x, y, w, h = f[:4]
            cx, cy = x + w / 2, y + h / 2
            if w > 0.62 * sw or np.hypot(cx - sx, cy - sy) < 0.55 * sw:     # the speaker (or a piece of him)
                continue
            if best is None or w > best[2]:
                best = (cx, cy, w)
        found.append(best)
    n, fps = len(found), R.FPS
    idx = [i for i, f in enumerate(found) if f]
    out = list(found)
    for a, b in zip(idx, idx[1:]):                                          # bridge short gaps
        if 1 < b - a <= gap * fps:
            for k in range(a + 1, b):
                u = (k - a) / (b - a)
                out[k] = tuple(found[a][j] * (1 - u) + found[b][j] * u for j in range(3))
    h = int(hold * fps)                                                     # hold past the ends of every run
    held = list(out)
    for i in range(n):
        if out[i] is None:
            near = [j for j in range(max(0, i - h), min(n, i + h + 1)) if out[j] is not None]
            if near:
                held[i] = out[min(near, key=lambda j: abs(j - i))]
    sm = [None] * n                                                         # light smoothing inside runs
    for i in range(n):
        if held[i] is None:
            continue
        win = [held[j] for j in range(max(0, i - 2), min(n, i + 3)) if held[j] is not None]
        sm[i] = [round(float(np.mean([w[j] for w in win])), 1) for j in range(3)]
    (R.work / "hide.json").write_text(json.dumps(sm))
    runs, cur = [], None
    for i, f in enumerate(sm):
        if f and cur is None:
            cur = i
        if not f and cur is not None:
            runs.append((cur / fps, i / fps)); cur = None
    if cur is not None:
        runs.append((cur / fps, n / fps))
    print(f"hide: bystander in {sum(1 for f in sm if f)}/{n} frames; runs: " + ", ".join(f"{a:.2f}-{b:.2f}" for a, b in runs))
    return sm


def emoji_png(ch, px):
    """The emoji as an RGBA array (Apple Color Emoji is a 160 px bitmap font; scaled to px)."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(APPLE_EMOJI, 160)
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 20), ch, font=font, embedded_color=True)
    im = im.crop(im.getbbox()).resize((px, px), Image.LANCZOS)
    return np.array(im)


def bake(R):
    import cv2
    cfg = dict(emoji="🤓", scale=1.25, blur=1.7)
    cfg.update(getattr(R, "HIDE", None) or {})
    sm = json.load(open(R.work / "hide.json"))
    base = emoji_png(cfg["emoji"], 512).astype(np.float32)
    out = R.work / "aroll_hidden.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{R.W}x{R.H}", "-r", str(R.FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                           stdin=subprocess.PIPE)
    checks = []
    for i, img in enumerate(_frames(R, R.work / "aroll.mp4")):
        f = sm[i] if i < len(sm) else None
        img = img.copy()
        if f:
            cx, cy, w = f
            w = max(w, cfg.get("min_w", 120))                               # a face half out of frame detects small: never a tiny mask
            r = int(w * cfg["blur"])                                         # the blurred disc: head and hair
            x0, y0, x1, y1 = max(0, int(cx - r)), max(0, int(cy - r * 1.1)), min(R.W, int(cx + r)), min(R.H, int(cy + r))
            if x1 > x0 and y1 > y0:
                roi = img[y0:y1, x0:x1].astype(np.float32)
                bl = cv2.GaussianBlur(roi, (0, 0), max(8.0, w * 0.22))
                yy, xx = np.mgrid[y0:y1, x0:x1]
                d = np.hypot((xx - cx) / r, (yy - (cy - 0.05 * r)) / (r * 1.05))
                a = np.clip((1.0 - d) / 0.25, 0, 1)[..., None]               # feathered edge
                img[y0:y1, x0:x1] = (roi * (1 - a) + bl * a).astype(np.uint8)
            s = max(24, int(w * cfg["scale"]))                              # the emoji on the face
            em = cv2.resize(base, (s, s), interpolation=cv2.INTER_AREA)
            ex0, ey0 = int(cx - s / 2), int(cy - s / 2)
            sx0, sy0, sx1, sy1 = max(0, -ex0), max(0, -ey0), min(s, R.W - ex0), min(s, R.H - ey0)
            if sx1 > sx0 and sy1 > sy0:
                patch = em[sy0:sy1, sx0:sx1]
                al = patch[..., 3:4] / 255.0
                rgb = patch[..., [2, 1, 0]]
                dst = img[ey0 + sy0:ey0 + sy1, ex0 + sx0:ex0 + sx1].astype(np.float32)
                img[ey0 + sy0:ey0 + sy1, ex0 + sx0:ex0 + sx1] = (dst * (1 - al) + rgb * al).astype(np.uint8)
        enc.stdin.write(img.tobytes())
        if i % int(R.FPS / 2) == 0:                                      # every 0.5 s of the whole cut, hidden or not
            th = cv2.resize(img, (180, 320))
            cv2.putText(th, f"{i / R.FPS:.1f}", (6, 22), 0, 0.7, (0, 255, 255), 2)
            checks.append(th)
    enc.stdin.close(); enc.wait()
    if checks:
        rows = [np.hstack(checks[k:k + 12] + [np.zeros_like(checks[0])] * (12 - len(checks[k:k + 12]))) for k in range(0, len(checks), 12)]
        cv2.imwrite(str(R.work / "hide_check.jpg"), np.vstack(rows))
    print(f"hide: -> {out} (check: {R.work / 'hide_check.jpg'})")
    return out


def run(R):
    detect(R)
    return bake(R)
