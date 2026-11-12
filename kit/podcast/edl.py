"""The podcast's edit list: the take's words minus podcast.py's CUT ranges, with long pauses shortened.

Every edge sits in real quiet on the voice envelope (kit/cut/edges.py): a piece starts before the breath of its first
word and ends once its last word has stopped sounding. A shortened pause keeps GAP_KEEP s of the room's own quiet
(half from each side), so there is room tone, never inserted digital silence. Times snap to the frame grid.

    build(P, attr) -> {"pieces": [{src_a, src_b, out_a, out_b, first, last}], "words": [... with out times + who],
                       "total": s, "cuts": [out times]}
"""
import json
import subprocess

import numpy as np

from kit.cut.edges import SR, envelope, offset, onset, speech_threshold


def voice_env(src):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    env = envelope(x)
    return env, speech_threshold(env)


def build(P, attr, env, thr):
    """SEQUENCE (optional): [(first word, last word), ...] in output order, for a part that plays somewhere else than
    where it was recorded (a topic recorded later, placed where it fits). Default: the whole take in order."""
    fps = P.FPS
    q = lambda s: round(s * fps) / fps
    cut = set()
    for a, b, *_ in P.CUT:
        cut.update(range(a, b + 1))
    by_i = {w["i"]: w for w in attr}
    seq = getattr(P, "SEQUENCE", None) or [(attr[0]["i"], attr[-1]["i"])]
    # pieces: break where a CUT removed words, the pause is longer than GAP_MAX, or the sequence jumps
    groups = []
    for a0, b0 in seq:
        W = [w for w in attr if a0 <= w["i"] <= b0 and w["i"] not in cut]
        if not W:
            continue
        cur = [W[0]]
        for a, b in zip(W, W[1:]):
            if b["i"] != a["i"] + 1 or b["t"] - a["e"] > P.GAP_MAX:
                groups.append(cur); cur = []
            cur.append(b)
        groups.append(cur)
    pieces, half = [], P.GAP_KEEP / 2
    for k, g in enumerate(groups):
        # the edges search the quiet between this piece and its neighbours in the SOURCE (cut words included)
        pw, nw = by_i.get(g[0]["i"] - 1), by_i.get(g[-1]["i"] + 1)
        prev_end = pw["e"] if pw else 0.0
        next_start = nw["t"] if nw else g[-1]["e"] + 1.0
        sa = onset(env, g[0]["t"], prev_end + 0.01, thr)
        sb = offset(env, g[-1]["e"], next_start - 0.01, thr)
        sa = max(prev_end, sa - half) if pw else max(0.0, sa - 0.25)
        sb = min(next_start, sb + half)
        pieces.append({"src_a": q(sa), "src_b": q(sb), "first": g[0]["i"], "last": g[-1]["i"]})
    # merge pieces that touch (a short pause inside a kept stretch): no cut where none is needed
    merged = [pieces[0]]
    for p in pieces[1:]:
        if 0 <= p["src_a"] - merged[-1]["src_b"] <= 1e-6 or (merged[-1]["src_a"] < p["src_a"] <= merged[-1]["src_b"] + 1e-6):
            merged[-1].update(src_b=p["src_b"], last=p["last"])
        else:
            merged.append(p)
    t = 0.0
    for p in merged:
        p["out_a"] = round(t, 4)
        t += p["src_b"] - p["src_a"]
        p["out_b"] = round(t, 4)
    words = []
    for p in merged:
        for w in attr:
            if p["first"] <= w["i"] <= p["last"] and w["i"] not in cut:
                words.append(dict(w, ot=round(w["t"] - p["src_a"] + p["out_a"], 3), oe=round(w["e"] - p["src_a"] + p["out_a"], 3)))
    return {"pieces": merged, "words": words, "total": round(t, 4), "cuts": [p["out_a"] for p in merged[1:]]}


def save(path, edl):
    open(path, "w").write(json.dumps(edl, indent=0))
