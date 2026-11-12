"""Hero objects for the paper-collage look (kit/presets/paper_collage): cut each source image out of its background with
Apple Vision (kit/bin/fgcut, on-device, ~1 s an image) into a transparent PNG cropped to the object.

    uv run python -m kit.look.objects films/<name>               # films/<name>/assets/objects/* -> <temp>/work/objects/*.png
    uv run python -m kit.look.objects films/<name> --stage       # ... and copy them into the HyperFrames project (assets/cut/)

Sources: the owner's own photos and screenshots, or images he generates in ChatGPT from the film's prompt sheet
(prompts in the preset README). A photo cuts out best on a plain, contrasting background with the whole object in frame.
Reports any image where Vision found no object (exit 2 for that file): reshoot/regenerate on a plainer background.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from kit.paths import Film  # noqa: E402

BIN = ROOT / "kit/bin/fgcut"
SRC = ROOT / "kit/hf/tools/fgcut.swift"
EXTS = (".png", ".jpg", ".jpeg", ".webp", ".heic")


def fgcut_bin() -> Path:
    if not BIN.exists() or BIN.stat().st_mtime < SRC.stat().st_mtime:
        BIN.parent.mkdir(exist_ok=True)
        subprocess.run(["swiftc", "-O", "-o", str(BIN), str(SRC)], check=True)      # Xcode's compiler, already on the Mac
    return BIN


def cut(src: Path, out: Path, pad: int = 24) -> dict:
    r = subprocess.run([str(fgcut_bin()), str(src), str(out), str(pad)], capture_output=True, text=True)
    info = json.loads(r.stdout.strip() or "{}") if r.stdout.strip().startswith("{") else {}
    info.update({"src": src.name, "ok": r.returncode == 0, "out": str(out) if r.returncode == 0 else None})
    if r.returncode not in (0, 2):
        info["error"] = r.stderr.strip()[-300:]
    return info


def run(film: Path, stage: bool = False) -> list:
    F = Film(film / "x.py")
    srcs = sorted(p for p in (film / "assets/objects").glob("*") if p.suffix.lower() in EXTS)
    if not srcs:
        raise SystemExit(f"no images in {film / 'assets/objects'}: put the photos / generated images there first")
    out_dir = F.work / "objects"
    out_dir.mkdir(parents=True, exist_ok=True)
    res = []
    for p in srcs:
        o = out_dir / f"{p.stem}.png"
        if o.exists() and o.stat().st_mtime > p.stat().st_mtime:
            res.append({"src": p.name, "ok": True, "out": str(o), "cached": True})
            continue
        res.append(cut(p, o))
    for r in res:
        print(("ok   " if r["ok"] else "FAIL ") + r["src"] + ("" if r["ok"] else "  (no object found: use a plainer background)") +
              (f"  {r.get('w')}x{r.get('h')}, covers {r.get('cover')}" if r.get("w") else ""))
    if stage:
        dst = F.assets / "cut"
        dst.mkdir(parents=True, exist_ok=True)
        for r in res:
            if r["ok"]:
                (dst / Path(r["out"]).name).write_bytes(Path(r["out"]).read_bytes())
        print(f"staged -> {dst}")
    if not all(r["ok"] for r in res):
        sys.exit(2)
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    run(Path(args[0]).resolve(), stage="--stage" in sys.argv)
