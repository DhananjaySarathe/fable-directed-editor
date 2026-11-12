"""The music map: beats, downbeats and section changes for every track in kit/music, analysed once and cached in
kit/music/beats.json. The model is All-In-One (Kim & Nam 2023) through its Apple-Silicon port all-in-one-mlx (MIT).

    A=(uv run --no-project --python 3.13 --with all-in-one-mlx==1.0.14)
    $A python -m kit.audio.beats --all                      # analyse every track that is new or changed (~15 s each)
    $A python -m kit.audio.beats kit/music/tech/x.mp3       # one track
    uv run python -m kit.audio.beats --check                # missing / stale entries (no model needed)
    uv run python -m kit.audio.beats --show brainiac        # one track's map

The first run converts the Demucs weights once (into ~/.cache/demucs-mlx) and needs torch for that only:
    uv run --no-project --python 3.13 --with all-in-one-mlx==1.0.14 --with 'demucs-mlx[convert]' python -m kit.audio.beats --all

What an entry holds (seconds of track time):
  - bpm, beats, downbeats;
  - agree: each track is analysed twice (Demucs seeds 0 and 1); the share of downbeats both runs put within 70 ms.
    Under 0.9 (an ambient track with no clear bar) the downbeats are not used for snapping (`steady` false);
  - sections: [{t, rise}] the starts of the track's sections. The model's labels are dropped (on instrumental stock
    music it calls most sections "solo"); `rise` is the change in loudness across the start (2 s after vs 2 s before,
    dB): + a drop or a build landing, - a breakdown;
  - drops: kit/music/structure.json's energy drops (the old analysis), each with the downbeat it sits on, if any.

Checked on the library (2026-10-20): Electro Dreams' hand-measured drop 16.0 s -> a section and downbeat at 16.01; Max
Brhon's "AI" full hit at 52.87; seeds 0/1 put 97 % of section starts within 0.25 s; 39 of 41 tracks agree >= 95 %.

MLX's buffer cache is capped at 1 GB: uncapped, the analysis peaked at ~21 GB on a 24 GB Mac. Run it alone (like a render).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

KIT = Path(__file__).resolve().parents[1]
MUSIC = KIT / "music"
OUT = MUSIC / "beats.json"
MODEL = "all-in-one-mlx 1.0.14, harmonix-all, Demucs seeds 0+1"
AGREE_MIN = 0.9


def rel(p: Path) -> str:
    return Path(p).resolve().relative_to(KIT).as_posix()             # "music/tech/tech__mixkit__brainiac.mp3"


def load() -> dict:
    """{rel path: entry} (empty when the map has not been made)."""
    return json.load(open(OUT))["tracks"] if OUT.exists() else {}


def entry(file, tracks: dict | None = None) -> dict | None:
    """The map of one track (a path, or a path relative to kit/music), or None when it is missing or stale. A file
    outside the kit (a Reel's own clip as a bed, films/claude-makes-claude's assets/meme.mp4) has no map: None (it
    raised ValueError, so kit/reel's mix stopped on that Reel since the music map came in; 2026-10-22)."""
    p = Path(file)
    p = p if p.is_absolute() else (MUSIC / p if (MUSIC / p).exists() else KIT / p)
    try:
        key = rel(p)
    except ValueError:
        return None
    e = (tracks if tracks is not None else load()).get(key)
    return e if e and e.get("size") == p.stat().st_size else None


def loudness(p: Path, hop=0.1, sr=11025):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    h = int(hop * sr)
    n = len(x) // h
    return np.mean(np.square(x[: n * h].reshape(n, h)), axis=1) + 1e-12, hop


def rise_at(pw, hop, t, w=2.0):
    i, k = int(round(t / hop)), int(round(w / hop))
    a, b = pw[max(0, i - k): i], pw[i: i + k]
    if not len(a) or not len(b):
        return 0.0
    return round(float(10 * np.log10(b.mean() / a.mean())), 1)


def build(p: Path, r0: dict, r1: dict | None, struct: dict | None) -> dict:
    """One entry from two All-In-One results (seeds 0 and 1) and the old structure.json entry, if any."""
    downs = np.array(r0["downbeats"])
    agree = 1.0
    if r1 is not None and len(downs):
        d1 = np.array(r1["downbeats"]) if r1["downbeats"] else np.array([1e9])
        agree = float(np.mean([np.min(np.abs(d1 - x)) <= 0.07 for x in downs]))
    pw, hop = loudness(p)
    dur = len(pw) * hop
    secs = [{"t": round(s["start"], 2), "rise": rise_at(pw, hop, s["start"])}
            for s in r0["segments"] if 1.0 < s["start"] < dur - 1.0]
    drops = []
    for d in (struct or {}).get("drops", []):
        near = float(downs[np.argmin(np.abs(downs - d["t"]))]) if len(downs) else None
        drops.append({"t": d["t"], "strength": d["strength"], "downbeat": round(near, 2) if near is not None and abs(near - d["t"]) <= 0.15 else None})
    return {"size": p.stat().st_size, "duration": round(dur, 2), "bpm": r0["bpm"], "agree": round(agree, 2), "steady": agree >= AGREE_MIN,
            "beats": [round(x, 2) for x in r0["beats"]], "downbeats": [round(x, 2) for x in r0["downbeats"]], "sections": secs, "drops": drops}


def old_structure(p: Path) -> dict | None:
    f = MUSIC / "structure.json"
    if not f.exists():
        return None
    return json.load(open(f)).get(f"{rel(p)}:{p.stat().st_size}")


def save(tracks: dict):
    OUT.write_text(json.dumps({"model": MODEL, "tracks": dict(sorted(tracks.items()))}, separators=(",", ":")) + "\n")
    print(f"-> {OUT} ({len(tracks)} tracks, {OUT.stat().st_size // 1024} KB)")


def analyse(paths: list[Path]):
    """All-In-One on each path, twice (Demucs seeds 0 and 1), merged into kit/music/beats.json."""
    try:
        import mlx.core as mx
        from allin1_mlx import analyze
    except ImportError:
        raise SystemExit("all-in-one-mlx is not installed here; run it in its own environment:\n"
                         "  uv run --no-project --python 3.13 --with all-in-one-mlx==1.0.14 python -m kit.audio.beats --all")
    mx.set_cache_limit(1 << 30)
    tracks = load()
    with tempfile.TemporaryDirectory() as tmp:
        runs = []
        for seed in (0, 1):
            out = Path(tmp) / f"s{seed}"
            try:
                analyze(paths=[str(p) for p in paths], out_dir=str(out), multiprocess=False, demix_seed=seed)
            except ImportError as e:
                if "convert" in str(e):
                    raise SystemExit("the Demucs weights need converting once (torch): add --with 'demucs-mlx[convert]' to the command")
                raise
            runs.append(out)
        for p in paths:
            r0 = json.load(open(runs[0] / f"{p.stem}.json"))
            r1 = json.load(open(runs[1] / f"{p.stem}.json"))
            e = build(p, r0, r1, old_structure(p))
            tracks[rel(p)] = e
            print(f"{p.name}: {e['bpm']} bpm, {len(e['downbeats'])} downbeats (agree {e['agree']:.0%}), {len(e['sections'])} sections")
    save(tracks)


def import_runs(dirs: list[Path]):
    """Build the map from All-In-One results already on disk (one json per track stem; the second dir = seed 1)."""
    tracks = load()
    for p in sorted(MUSIC.rglob("*.mp3")):
        f0 = dirs[0] / f"{p.stem}.json"
        if not f0.exists():
            continue
        f1 = dirs[1] / f"{p.stem}.json" if len(dirs) > 1 else None
        tracks[rel(p)] = build(p, json.load(open(f0)), json.load(open(f1)) if f1 and f1.exists() else None, old_structure(p))
    save(tracks)


def check() -> list[Path]:
    tracks = load()
    todo = [p for p in sorted(MUSIC.rglob("*.mp3")) if entry(p, tracks) is None]
    for p in todo:
        print("missing or stale:", rel(p))
    wobbly = [k for k, e in tracks.items() if not e["steady"]]
    print(f"{len(tracks)} tracks mapped, {len(todo)} to analyse" + (f"; not steady (no snapping): {', '.join(Path(k).stem for k in wobbly)}" if wobbly else ""))
    return todo


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--check" in sys.argv:
        raise SystemExit(1 if check() else 0)
    if "--show" in sys.argv:
        for k, e in load().items():
            if all(a in k for a in args):
                print(k, {x: e[x] for x in ("duration", "bpm", "agree", "steady")})
                print("  sections:", ", ".join(f"{s['t']} ({s['rise']:+.1f} dB)" for s in e["sections"]))
        return
    imp = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--import=")), None)
    if imp:
        return import_runs([Path(d) for d in imp.split(",")])
    paths = check() if "--all" in sys.argv else [Path(a).resolve() for a in args]
    if not paths:
        print("nothing to analyse")
        return
    analyse(paths)


if __name__ == "__main__":
    main()
