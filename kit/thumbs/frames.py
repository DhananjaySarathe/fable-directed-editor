"""Face frames for a thumbnail: the creator's sharpest, best-lit, most usable moments, as stills an image model (GPT)
can take as the face reference.

    uv run python kit/thumbs/frames.py <film-or-take> [--n=8] [--src=<video>] [--fps=2]

Source, cleanest first (no captions, no graphics): the film's graded take (output/temp/films/<f>/work/take_graded.mp4),
the take's source (output/jobs/<f>/source.mp4), else the newest video in output/final/<f>/. --src overrides.

Each sampled frame (2 per second) is scored on the largest face YuNet finds: sharpness (Laplacian variance of the face),
size, how frontal it is (eye line level, nose between the eyes, head not tipped down), eyes open (contrast in the eye
patches), exposure of the face, and expression (mouth width against the eye distance, away from the take's median: a
smile or an open mouth). The best N, at least 4 s apart and with mixed expressions, are written at full resolution.
Eyes lowered under open lids still pass: look at sheet.jpg and drop those before handing the photos on.

    output/final/<f>/thumbnail/photos/face_01.jpg ...   best first
    output/final/<f>/thumbnail/photos/ref_*.jpg         the photos in kit/refs/me/ (if any), copied beside them
    output/final/<f>/thumbnail/photos/sheet.jpg         all of them, numbered, for a quick look
    output/final/<f>/thumbnail/photos/frames.json       the times and scores
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from kit.look.faces import detect  # noqa: E402
from kit.paths import FINAL, JOBS, ROOT, TEMP  # noqa: E402

REFS = ROOT / "kit/refs/me"
SCAN_W = 960                     # frames are scored at this width; the chosen ones are cut at full size
MIN_GAP = 4.0                    # seconds between two chosen frames


def arg(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def source(name: str) -> Path:
    if arg("src"):
        return Path(arg("src"))
    for p in (TEMP / "films" / name / "work/take_graded.mp4", JOBS / name / "source.mp4"):
        if p.exists():
            return p
    vids = sorted((FINAL / name).glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if vids:
        return vids[0]
    sys.exit(f"no video for {name}: pass --src=<video>")


def probe(path: Path) -> tuple[int, int, float]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    w, h = s["width"], s["height"]
    rot = next((abs(int(d.get("rotation", 0))) for d in s.get("side_data_list", []) if "rotation" in d), 0)
    if rot in (90, 270):
        w, h = h, w
    return w, h, float(j["format"]["duration"])


def frames(path: Path, fps: float, w: int, h: int):
    """(t, rgb) at `fps`, scaled to SCAN_W wide, decoded once through ffmpeg (fast on 4K HEVC, unlike seeking)."""
    sw = SCAN_W if w >= SCAN_W else w
    sh = int(round(h * sw / w / 2)) * 2
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={sw}:{sh}", "-pix_fmt", "rgb24",
                          "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    size = sw * sh * 3
    i = 0
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield i / fps, np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
        i += 1
    p.wait()


def measure(img: np.ndarray) -> dict | None:
    f = detect(img, scale=1.0)
    if not f or f["score"] < 0.8:
        return None
    H, W = img.shape[:2]
    x, y, w, h = f["box"]
    x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(W, int(x + w)), min(H, int(y + h))
    if x1 - x0 < 24 or y1 - y0 < 24:
        return None
    gray = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY)
    face = cv2.resize(gray, (128, int(128 * (y1 - y0) / (x1 - x0))))
    (rex, rey), (lex, ley), (nx, ny), (rmx, rmy), (lmx, lmy) = f["lm"]
    eye = max(1.0, float(np.hypot(lex - rex, ley - rey)))
    return {
        "eyes": eyes_open(img, (rex, rey), (lex, ley), eye),
        "sharp": float(cv2.Laplacian(face, cv2.CV_64F).var()),
        "size": w / W,
        "roll": abs(float(np.degrees(np.arctan2(ley - rey, lex - rex)))),
        "yaw": abs((nx - (rex + lex) / 2) / eye),
        "light": float(gray.mean()) / 255,
        "mouth": float(np.hypot(lmx - rmx, lmy - rmy)) / eye,
        "pitch": (ny - (rey + ley) / 2) / max(1.0, (rmy + lmy) / 2 - (rey + ley) / 2),   # nose down the eye-mouth line
        "cx": (x + w / 2) / W,
    }


def eyes_open(img: np.ndarray, right: tuple, left: tuple, eye: float) -> float:
    """Contrast inside each eye's patch (iris and white against lid), the lower of the two: about 1.2-1.9 for eyes open
    to the camera, under 0.5 for lids down. Eyes lowered under open lids still read open: the sheet review catches those."""
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    r = max(3, int(eye * 0.22))
    vals = []
    for ex, ey in (right, left):
        p = g[max(0, int(ey - r * 0.6)):int(ey + r * 0.6), max(0, int(ex - r)):int(ex + r)]
        if p.size < 9:
            return 0.0
        vals.append(float((np.percentile(p, 90) - np.percentile(p, 5)) / max(1.0, p.mean())))
    return min(vals)


def rank(found: list[dict]) -> list[dict]:
    sharp = np.array([f["sharp"] for f in found])
    size = np.array([f["size"] for f in found])
    mouth = np.array([f["mouth"] for f in found])
    s_lo, s_hi = np.percentile(sharp, 10), np.percentile(sharp, 95)
    z_lo, z_hi = np.percentile(size, 10), np.percentile(size, 95)
    m_med, m_spread = float(np.median(mouth)), float(np.percentile(np.abs(mouth - np.median(mouth)), 90)) or 0.05
    for f in found:
        f["expr"] = min(1.0, abs(f["mouth"] - m_med) / m_spread)
        f["score"] = (
            1.6 * np.clip((f["sharp"] - s_lo) / max(1e-6, s_hi - s_lo), 0, 1)
            + 0.8 * np.clip((f["size"] - z_lo) / max(1e-6, z_hi - z_lo), 0, 1)
            + 0.8 * (1 - np.clip(f["yaw"] / 0.35, 0, 1))
            + 0.4 * (1 - np.clip(f["roll"] / 12, 0, 1))
            + 0.6 * (1 - np.clip(abs(f["light"] - 0.52) / 0.3, 0, 1))
            + 0.7 * f["expr"]
            + 0.9 * np.clip((f["eyes"] - 0.5) / 0.7, 0, 1)        # eyes open, not lids down
            - 1.0 * np.clip((f["pitch"] - 0.65) / 0.1, 0, 1)      # head tipped down
        )
    return sorted(found, key=lambda f: f["score"], reverse=True)


def choose(ranked: list[dict], n: int) -> list[dict]:
    """The best N, at least MIN_GAP apart; once half are in, a frame must differ in expression from those already in."""
    out: list[dict] = []
    for f in ranked:
        if any(abs(f["t"] - o["t"]) < MIN_GAP for o in out):
            continue
        if len(out) >= n // 2 and min(abs(f["mouth"] - o["mouth"]) for o in out) < 0.03:
            continue
        out.append(f)
        if len(out) == n:
            return out
    for f in ranked:                 # too few distinct expressions: fill on spacing alone
        if len(out) == n:
            break
        if f not in out and all(abs(f["t"] - o["t"]) >= MIN_GAP for o in out):
            out.append(f)
    return out


def cut(path: Path, t: float, dst: Path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-q:v", "2", str(dst)],
                   check=True)


def sheet(paths: list[Path], dst: Path, width: int = 300):
    ims = [Image.open(p).convert("RGB") for p in paths]
    ims = [im.resize((width, int(im.height * width / im.width))) for im in ims]
    cols = 4
    cell_h = max(im.height for im in ims)
    rows = (len(ims) + cols - 1) // cols
    out = Image.new("RGB", (cols * width, rows * cell_h), (20, 20, 20))
    d = ImageDraw.Draw(out)
    for i, (p, im) in enumerate(zip(paths, ims)):
        x, y = (i % cols) * width, (i // cols) * cell_h
        out.paste(im, (x, y))
        d.rectangle([x, y, x + 120, y + 22], fill=(0, 0, 0))
        d.text((x + 6, y + 5), p.stem, fill=(255, 255, 255))
    out.save(dst, quality=88)


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        sys.exit(__doc__)
    name = sys.argv[1]
    n = int(arg("n", 8))
    src = source(name)
    w, h, dur = probe(src)
    found = []
    for t, img in frames(src, float(arg("fps", 2)), w, h):
        m = measure(img)
        if m:
            found.append({"t": round(t, 2), **m})
    if not found:
        sys.exit(f"no face found in {src}")
    picked = choose(rank(found), n)

    out = FINAL / name / "thumbnail/photos"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    paths = []
    for i, f in enumerate(picked, 1):
        p = out / f"face_{i:02d}.jpg"
        cut(src, f["t"], p)
        paths.append(p)
    refs = sorted(p for p in REFS.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".webp")) if REFS.is_dir() else []
    for i, r in enumerate(refs, 1):
        dst = out / f"ref_{i:02d}{r.suffix.lower()}"
        shutil.copy2(r, dst)
        if dst.suffix != ".heic":
            paths.append(dst)
    sheet(paths, out / "sheet.jpg")
    (out / "frames.json").write_text(json.dumps({
        "source": str(src.relative_to(ROOT)) if src.is_relative_to(ROOT) else str(src), "size": [w, h],
        "duration": round(dur, 2), "sampled": len(found),
        "picked": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in f.items()} for f in picked],
        "refs": [r.name for r in refs],
    }, indent=1))
    print(f"{len(picked)} face frames + {len(refs)} reference photos -> {out.relative_to(ROOT)}  (from {src.name}, "
          f"{len(found)} frames with a face)")
    for i, f in enumerate(picked, 1):
        print(f"  face_{i:02d}  t={f['t']:7.2f}s  score {f['score']:.2f}  sharp {f['sharp']:.0f}  yaw {f['yaw']:.2f}  "
              f"expr {f['expr']:.2f}")


if __name__ == "__main__":
    main()
