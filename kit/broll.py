"""The B-roll library (broll/, git-ignored, his own): clips of him and his places that any future video can reuse.
Only the useful part of a take is kept: --use trims it by stream copy (no re-encode, so the quality, HDR and rotation
are the camera's own). Start a range on a keyframe (phone takes: every whole second) and the cut is exact; otherwise it
starts at the keyframe just before. Each clip gets a catalog entry saying what is in it, who is in frame, and where it
came from.

    uv run python kit/broll.py add <file>... --cat=me --tags=cafe,laptop,night --note="leans back while the agent works"
                                   [--use=0-6.5] [--people=him|others|none] [--from=not-ai-made]
                                   (several ranges, --use=0-4,9-16, make one clip each; no --use keeps the whole file)
    uv run python kit/broll.py find [--tags=cafe,laptop] [--cat=me] [--text=night]     matches, with paths and ranges
    uv run python kit/broll.py sheet                                                   rebuild broll/sheet.jpg

    broll/clips/<cat>/<file>     the original, as recorded
    broll/thumbs/<id>.jpg        three frames of it, for a quick look
    broll/catalog.json           one entry per clip
    broll/sheet.jpg              every clip at a glance, with its id and tags

Categories: me (him on camera), hands (typing, phone, writing), screens (a screen filmed with the camera), places (a
room, street or café with nobody), objects, motion (walking, driving, a door), misc. Tags carry the rest.
people=others means someone else is in frame: a reuse needs a tracked blur (kit/reel/hide.py) unless they agreed.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kit.paths import BROLL  # noqa: E402

CATS = ("me", "hands", "screens", "places", "objects", "motion", "misc")
CATALOG = BROLL / "catalog.json"
THUMB_H = 240


def arg(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def load():
    return json.loads(CATALOG.read_text()) if CATALOG.exists() else []


def save(cat):
    CATALOG.write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")


def fingerprint(p: Path) -> str:
    """Size plus the first and last 4 MB: enough to spot the same file added twice, fast on 4K takes."""
    h = hashlib.sha1(str(p.stat().st_size).encode())
    with open(p, "rb") as f:
        h.update(f.read(4 << 20))
        f.seek(max(0, p.stat().st_size - (4 << 20)))
        h.update(f.read())
    return h.hexdigest()


def probe(p: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate,color_transfer:stream_side_data=rotation",
                          "-of", "json", str(p)], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    rot = next((int(sd.get("rotation", 0)) for sd in v.get("side_data_list", []) if "rotation" in sd), 0)
    w, h = (v["height"], v["width"]) if abs(rot) == 90 else (v["width"], v["height"])
    tr = v.get("color_transfer", "")
    return {"duration": round(float(d["format"]["duration"]), 2), "w": w, "h": h, "fps": v.get("r_frame_rate"),
            "transfer": tr, "hdr": tr in ("arib-std-b67", "smpte2084"),
            "audio": any(s["codec_type"] == "audio" for s in d["streams"])}


def frame(p: Path, t: float, hdr: bool) -> Image.Image:
    # HLG/PQ takes are tone-mapped for the thumbnail only (the clip itself stays as recorded)
    tm = "zscale=t=linear:npl=100,format=gbrpf32le,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv," if hdr else ""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(p), "-frames:v", "1",
                          "-vf", f"{tm}scale=-2:{THUMB_H},format=rgb24", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True, check=True).stdout
    import io
    return Image.open(io.BytesIO(raw)).convert("RGB")


def trim(src: Path, dest: Path, a: float, b: float):
    """The part a-b s of src, by stream copy: the camera's own frames, audio, colour tags and rotation, no re-encode."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a}", "-i", str(src), "-t", f"{b - a}", "-map", "0:v:0", "-map", "0:a?",
                    "-c", "copy", "-map_metadata", "0", "-movflags", "+faststart", str(dest)], check=True)
    # a broken cut fails here, not in a film months later: decode the first and the last second
    for at in ("0", f"{max(0.0, b - a - 1.0)}"):
        subprocess.run(["ffmpeg", "-v", "error", "-ss", at, "-i", str(dest), "-t", "1", "-f", "null", "-"], check=True,
                       capture_output=True)


def thumbs(entry: dict):
    p = BROLL / entry["file"]
    a, b = entry["use"][0] if entry["use"] else (0, entry["duration"])
    ims = [frame(p, a + (b - a) * k, entry["hdr"]) for k in (0.1, 0.5, 0.9)]
    strip = Image.new("RGB", (sum(i.width for i in ims) + 8 * 2, THUMB_H), (12, 12, 12))
    x = 0
    for i in ims:
        strip.paste(i, (x, 0))
        x += i.width + 8
    (BROLL / "thumbs").mkdir(parents=True, exist_ok=True)
    strip.save(BROLL / "thumbs" / f"{entry['id']}.jpg", quality=85)


def sheet(cat):
    if not cat:
        return
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    rows = [(Image.open(BROLL / "thumbs" / f"{e['id']}.jpg"), e) for e in cat if (BROLL / "thumbs" / f"{e['id']}.jpg").exists()]
    W = max(im.width for im, _ in rows) + 20
    out = Image.new("RGB", (W, sum(im.height + 54 for im, _ in rows) + 10), (24, 24, 24))
    d = ImageDraw.Draw(out)
    y = 10
    for im, e in rows:
        d.text((10, y), f"{e['id']}  ·  {e['cat']}  ·  {e['duration']} s  ·  {e['w']}x{e['h']}{' HDR' if e['hdr'] else ''}"
                        f"{'  ·  OTHERS IN FRAME' if e['people'] == 'others' else ''}", fill=(255, 230, 120), font=font)
        d.text((10, y + 24), ", ".join(e["tags"]) + (f"  —  {e['note']}" if e["note"] else ""), fill=(200, 200, 200), font=font)
        out.paste(im, (10, y + 50))
        y += im.height + 54
    out.save(BROLL / "sheet.jpg", quality=85)


def add(files):
    cat_name = arg("cat", "misc")
    if cat_name not in CATS:
        raise SystemExit(f"--cat must be one of {', '.join(CATS)}")
    tags = [t.strip().lower() for t in (arg("tags") or "").split(",") if t.strip()]
    cat = load()
    known = {e["sha1"]: e for e in cat}
    ranges = [[float(x) for x in r.split("-")] for r in arg("use").split(",")] if arg("use") else [None]
    for f in map(Path, files):
        src_fp = fingerprint(f)
        for rng in ranges:
            fp = src_fp if rng is None else f"{src_fp}@{rng[0]:g}-{rng[1]:g}"
            if fp in known:
                print(f"= {f.name} {rng or ''} is already in the library as {known[fp]['id']}")
                continue
            part = "" if rng is None else f"_{rng[0]:g}-{rng[1]:g}s"
            dest = BROLL / "clips" / cat_name / f"{f.stem}{part}{f.suffix}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if rng is None:
                shutil.copy2(f, dest)
            else:
                trim(f, dest, *rng)
            info = probe(dest)
            stem = f"{f.stem}{part}".lower().replace(".", "_")
            e = {"id": "-".join(tags[:3] + [stem]) if tags else stem, "file": str(dest.relative_to(BROLL)), "cat": cat_name,
                 "tags": tags, "note": arg("note", ""), "use": [[0.0, info["duration"]]],
                 "people": arg("people", "him" if cat_name == "me" else "none"), **info,
                 "from": (arg("from") + ": " if arg("from") else "") + f.name + (f" {rng[0]:g}-{rng[1]:g} s" if rng else ""),
                 "added": date.today().isoformat(), "sha1": fp}
            cat.append(e)
            known[fp] = e
            thumbs(e)
            print(f"+ {e['id']}: {dest.relative_to(BROLL.parent)} ({info['duration']} s, {info['w']}x{info['h']}"
                  f"{', HDR' if info['hdr'] else ''}, {dest.stat().st_size / 1e6:.1f} MB)")
    save(cat)
    sheet(cat)


def find():
    want = {t.strip().lower() for t in (arg("tags") or "").split(",") if t.strip()}
    text = (arg("text") or "").lower()
    hits = [e for e in load() if (not want or want <= set(e["tags"])) and (not arg("cat") or e["cat"] == arg("cat"))
            and (not text or text in (e["note"] + " " + " ".join(e["tags"])).lower())]
    for e in hits:
        r = ", ".join(f"{a:g}-{b:g} s" for a, b in e["use"])
        print(f"{e['id']}\n  {BROLL / e['file']}\n  {e['cat']} · {', '.join(e['tags'])} · use {r} · {e['w']}x{e['h']} {e['fps']}"
              f"{' HDR' if e['hdr'] else ''} · people: {e['people']}\n  {e['note']}")
    print(f"{len(hits)} clip(s)")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or args[0] not in ("add", "find", "sheet"):
        raise SystemExit(__doc__)
    if args[0] == "add":
        add(args[1:])
    elif args[0] == "find":
        find()
    else:
        sheet(load())


if __name__ == "__main__":
    main()
