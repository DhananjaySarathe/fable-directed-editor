"""Our edit against a reference, number by number, plus a side-by-side video to watch.

    uv run python kit/refs/compare.py <reference.mp4 | its breakdown dir> <our render.mp4> [--video] [--seconds=20]

Runs kit/refs/breakdown.py on whichever side has no breakdown.json yet, prints each measure for both, and marks the
ones that differ by more than their tolerance. With --video it writes <our breakdown dir>/side_by_side.mp4 (the
reference on the left, both at the same height, the first --seconds seconds) for the owner or the critic to watch.
A marked number is a question, not a verdict: the critic decides whether a viewer would notice it.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "output" / "temp" / "refs"

# measure: (kind of tolerance, tolerance). "rel" = share of the larger value, "abs" = the same units.
TOL = {
    "cuts / min": ("rel", 0.25), "shot median s": ("rel", 0.25), "shot p90 s": ("rel", 0.3), "cuts in first 3 s": ("abs", 1),
    "punch-ins / min": ("rel", 0.3), "punch-in size": ("abs", 0.04), "jump cuts / min": ("rel", 0.3),
    "layout changes / min": ("rel", 0.3), "new pictures / min": ("rel", 0.3), "transitions / min": ("rel", 0.3),
    "pops / min": ("rel", 0.35),
    "pushes+pulls / min": ("rel", 0.3), "push size": ("abs", 0.03), "push length s": ("rel", 0.3),
    "snap zooms / min": ("rel", 0.3), "snap zoom size": ("abs", 0.05), "snap zoom length s": ("rel", 0.35),
    "easing (most common)": ("same", None), "shots with no move": ("abs", 0.2), "face on screen": ("abs", 0.15),
    "in motion share": ("abs", 0.15), "text on screen": ("abs", 0.2),
    "headlines / min": ("rel", 0.3), "headline height %": ("rel", 0.2), "headline held s": ("rel", 0.35),
    "counters / min": ("rel", 0.35), "captions / min": ("rel", 0.3), "caption words": ("abs", 1), "caption height %": ("rel", 0.2),
    "caption place % from top": ("abs", 8), "caption held s": ("rel", 0.35),
    "loudness LUFS": ("abs", 2), "beat": ("same", None), "tempo BPM": ("rel", 0.08), "cuts on beat share": ("abs", 0.2),
}


def arg(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith(f"--{name}=")), default)


def breakdown(p):
    p = Path(p)
    if p.is_dir():
        return p, json.loads((p / "breakdown.json").read_text())
    d = OUT / p.stem
    if not (d / "breakdown.json").exists() or (d / "breakdown.json").stat().st_mtime < p.stat().st_mtime:
        subprocess.run([sys.executable, str(HERE / "breakdown.py"), str(p), f"--out={d}"], check=True, stdout=subprocess.DEVNULL)
    return d, json.loads((d / "breakdown.json").read_text())


def measures(B):
    secs = B["info"]["seconds"]
    per_min = lambda xs: len(xs) / secs * 60
    med = lambda xs: float(np.median(xs)) if xs else None
    shots, ev, snd = B["shots"], B["cut_events"], B["sound"]
    lens = [s["seconds"] for s in shots] or [secs]
    moves = [m for s in shots for m in s["moves"]]
    slow = [m for m in moves if m["kind"] in ("push", "pull")]
    snap = [m for m in moves if m["kind"] in ("snap-in", "snap-out")]
    size = lambda ms: med([m["zoom"] if m["zoom"] >= 1 else 1 / m["zoom"] for m in ms])
    ease = [m["easing"] for m in slow + snap]
    kind = lambda k: [e for e in ev if e["kind"] == k]
    head = [e for e in B["text"] if e["class"] == "headline"]
    cap = [e for e in B["text"] if e["class"] == "caption"]
    clear = snd.get("beat") == "clear"
    return {
        "cuts / min": per_min(B["cuts"]), "shot median s": med(lens), "shot p90 s": float(np.quantile(lens, 0.9)),
        "cuts in first 3 s": sum(1 for c in B["cuts"] if c < 3),
        "punch-ins / min": per_min(kind("punch-in")), "punch-in size": med([e["scale"] for e in kind("punch-in")]),
        "jump cuts / min": per_min(kind("same-size")), "layout changes / min": per_min(kind("layout change")),
        "new pictures / min": per_min(kind("new picture")), "transitions / min": per_min(kind("transition")),
        "pops / min": per_min(B.get("pops", [])),
        "pushes+pulls / min": per_min(slow), "push size": size(slow), "push length s": med([m["seconds"] for m in slow]),
        "snap zooms / min": per_min(snap), "snap zoom size": size(snap), "snap zoom length s": med([m["seconds"] for m in snap]),
        "easing (most common)": max(set(ease), key=ease.count) if ease else None,
        "shots with no move": sum(1 for s in shots if not s["moves"]) / max(1, len(shots)),
        "face on screen": sum(s["seconds"] for s in shots if s["framing"] != "none") / secs,
        "in motion share": float(np.average([s["in_motion"] for s in shots], weights=lens)) if shots else None,
        "text on screen": B.get("text_share"),
        "headlines / min": per_min(head), "headline height %": med([e["height"] * 100 for e in head]),
        "headline held s": med([e["seconds"] for e in head]),
        "counters / min": per_min([e for e in B["text"] if e["class"] == "counter"]), "captions / min": per_min(cap), "caption words": med([e["words"] for e in cap]),
        "caption height %": med([e["height"] * 100 for e in cap]), "caption place % from top": med([e["y"] * 100 for e in cap]),
        "caption held s": med([e["seconds"] for e in cap]),
        "loudness LUFS": snd.get("lufs"), "beat": snd.get("beat"), "tempo BPM": snd.get("bpm") if clear else None,
        "cuts on beat share": (snd["cuts_on_beat"] / snd["cuts"]) if clear and snd.get("cuts") else None,
    }


def differs(key, a, b):
    how, tol = TOL[key]
    if a is None or b is None:
        return (a is None) != (b is None)          # one side has it, the other does not
    if how == "same":
        return a != b
    if how == "abs":
        return abs(a - b) > tol
    return abs(a - b) > tol * max(abs(a), abs(b), 1e-6)


def fmt(v):
    return "-" if v is None else v if isinstance(v, str) else f"{v:.2f}" if abs(v) < 100 else f"{v:.0f}"


def compare(ref, ours):
    """[(measure, reference value, our value, differs)]"""
    a, b = measures(ref), measures(ours)
    return [(k, a[k], b[k], differs(k, a[k], b[k])) for k in TOL]


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) != 2:
        sys.exit(__doc__)
    rd, R = breakdown(a[0])
    od, O = breakdown(a[1])
    rows = compare(R, O)
    print(f"{'measure':26s} {'reference':>12s} {'ours':>12s}")
    for k, rv, ov, flag in rows:
        print(f"{k:26s} {fmt(rv):>12s} {fmt(ov):>12s}  {'<- differs' if flag else ''}")
    print(f"\n{sum(r[3] for r in rows)} of {len(rows)} measures differ. Reference sheets: {rd}  Ours: {od}")
    if "--video" in sys.argv:
        secs = float(arg("seconds", 20))
        out = od / "side_by_side.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", str(secs), "-i", R["video"], "-t", str(secs), "-i", O["video"],
                        "-filter_complex", "[0:v]scale=-2:720,setsar=1,fps=30[a];[1:v]scale=-2:720,setsar=1,fps=30[b];[a][b]hstack=inputs=2[v]",
                        "-map", "[v]", "-map", "1:a?", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)], check=True)
        print("->", out)


if __name__ == "__main__":
    main()
