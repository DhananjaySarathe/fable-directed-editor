"""Who is speaking, with one camera and one mic: the person whose mouth moves (kit/bin/facemarks, Apple Vision).

    people(marks, k)      -> the k people in the frame (left to right), each with its median face box (0..1)
    activity(marks, P)    -> per person, mouth motion per sample (the spread of the lip gap over a 0.4 s window)
    attribute(words, ...) -> each word's speaker and a confidence; sentences vote, so a word isn't flipped alone
    turns(words)          -> [{a, b, who, first, last, n}]: runs of one speaker

Confidence is the winner's share of the mouth motion during the word. Below ~0.6 the sheet marks it "?" for a look.
Fix a stretch with SPEAKER_FIX in podcast.py. Laughter, coughs and a hand over the mouth fool it. A turn under ~1.5 s is
an interjection ("haan", "right").
"""
import json
from pathlib import Path

import numpy as np


def load(path):
    return [json.loads(l) for l in open(path)]


def people(marks, k=2):
    """k people by the x-centre of their faces (a fixed camera: people stay roughly in place); left to right."""
    xs = np.array([f["x"] + f["w"] / 2 for m in marks for f in m["faces"]])
    if len(xs) < k:
        raise SystemExit(f"facemarks: found {len(xs)} faces; is everyone in frame?")
    cs = np.quantile(xs, np.linspace(0.15, 0.85, k))
    for _ in range(30):                                        # 1-D k-means
        lab = np.argmin(np.abs(xs[:, None] - cs[None, :]), axis=1)
        cs = np.array([xs[lab == j].mean() if (lab == j).any() else cs[j] for j in range(k)])
    cs = np.sort(cs)
    P = []
    for j, c in enumerate(cs):
        fs = [f for m in marks for f in m["faces"] if np.argmin(np.abs(cs - (f["x"] + f["w"] / 2))) == j]
        med = {key: float(np.median([f[key] for f in fs])) for key in ("x", "y", "w", "h")}
        P.append({"id": "ABCDEFG"[j], "cx": float(c), "box": med, "seen": len(fs) / max(1, len(marks)),
                  "eyes_p50": float(np.median([f.get("eyes", 0) for f in fs]))})
    return P


def per_person(marks, P, key):
    """A series per person of a face field (NaN where that person's face wasn't found), sample times."""
    t = np.array([m["t"] for m in marks])
    out = {p["id"]: np.full(len(marks), np.nan) for p in P}
    cs = np.array([p["cx"] for p in P])
    for i, m in enumerate(marks):
        for f in m["faces"]:
            j = int(np.argmin(np.abs(cs - (f["x"] + f["w"] / 2))))
            out[P[j]["id"]][i] = f.get(key, 0.0)
    return t, out


def activity(marks, P, win=0.4):
    """Mouth motion: the spread (std) of the lip gap over a moving window; a talking mouth opens and closes."""
    t, m = per_person(marks, P, "mouth")
    dt = np.median(np.diff(t)) if len(t) > 1 else 0.1
    n = max(2, int(round(win / dt)))
    act = {}
    for pid, s in m.items():
        s = s.copy()
        ok = ~np.isnan(s)
        if ok.sum() < 2:
            act[pid] = np.zeros_like(s)
            continue
        s[~ok] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), s[ok])
        pad = np.pad(s, (n // 2, n - n // 2 - 1), mode="edge")
        win_std = np.array([pad[i:i + n].std() for i in range(len(s))])
        act[pid] = win_std * np.where(ok, 1.0, 0.3)            # a face that wasn't seen counts less
    return t, act


def attribute(words, t, act, sentences=None, fix=None):
    ids = list(act)
    out = []
    for w in words:
        a, b = w["start"] - 0.05, w["end"] + 0.05
        sel = (t >= a) & (t <= b)
        if not sel.any():
            sel = np.abs(t - (a + b) / 2) == np.abs(t - (a + b) / 2).min()
        sc = np.array([act[p][sel].mean() for p in ids])
        tot = sc.sum()
        j = int(np.argmax(sc))
        out.append({"i": w["i"], "text": w["text"], "t": w["start"], "e": w["end"], "who": ids[j], "conf": float(sc[j] / tot) if tot > 0 else 0.0, "score": sc.tolist()})
    if sentences:                                              # a sentence is one speaker unless the evidence is strong
        for s in sentences:
            ws = [o for o in out if s["start"] - 1e-3 <= o["t"] <= s["end"] + 1e-3]
            if len(ws) < 3:
                continue
            tot = np.sum([o["score"] for o in ws], axis=0)
            j = int(np.argmax(tot))
            for o in ws:
                if o["conf"] < 0.75:
                    o["who"] = ids[j]
    for (a, b), who in (fix or {}).items():
        for o in out:
            if a <= o["i"] <= b:
                o["who"], o["conf"] = who, 1.0
    return out


def turns(attr):
    T = []
    for o in attr:
        if T and T[-1]["who"] == o["who"] and o["t"] - T[-1]["b"] < 1.5:
            T[-1].update(b=o["e"], last=o["i"], n=T[-1]["n"] + 1)
        else:
            T.append({"a": o["t"], "b": o["e"], "who": o["who"], "first": o["i"], "last": o["i"], "n": 1})
    return T


def sheet(attr, T, path):
    """A readable speaker transcript for review: one line per turn, '?' where the evidence is weak."""
    by = {o["i"]: o for o in attr}
    lines = []
    for tr in T:
        ws = [by[i] for i in range(tr["first"], tr["last"] + 1) if i in by]
        weak = sum(1 for w in ws if w["conf"] < 0.6) > len(ws) / 3
        mm = f"{int(tr['a'] // 60):02d}:{tr['a'] % 60:04.1f}"
        lines.append(f"{mm} {tr['who']}{'?' if weak else ' '} [{tr['first']}-{tr['last']}] " + " ".join(w["text"] for w in ws))
    Path(path).write_text("\n".join(lines) + "\n")
    return lines
