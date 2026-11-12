"""Virtual multicam for a one-camera podcast: one wide shot cropped into a WIDE, a SINGLE on each person and a TIGHT
(the emphasis / jump-cut size), directed from who is speaking. Rules from the research (kit/refs/RESEARCH.md
"podcasts"; EDITING.md §12), each a parameter:

  - cut to the person who starts talking 3 frames after their first word (a cut sits slightly behind its audio);
  - hold every shot at least MIN_HOLD (2.5 s); an interjection under 1.5 s ("haan", "right") doesn't cut;
  - a single runs at most MAX_HOLD (15 s): then, at a sentence boundary, a TIGHT on the same person, a 2-3 s
    REACTION of the listener, or the WIDE (in turn), so a long answer keeps moving without a jump;
  - quick back-and-forth (3+ turns inside 6 s) and crosstalk stay on the WIDE; the WIDE opens (5 s), marks each
    chapter (4 s) and closes (3 s);
  - an edit cut inside a shot (a trim) changes the size SINGLE <-> TIGHT (15-20 % punch), so the jump doesn't show.

Crops: SINGLE puts the face at ~26 % of the crop height, TIGHT at ~36 %, eyes on the upper third; never past the
frame. Each crop's upscale to the output is reported: over 1.5x looks soft (record in 4K for a 1080p episode).
"""
import numpy as np

SIZES = {"single": 0.26, "tight": 0.36}


def crops(P_people, SW, SH, out_h, sizes=None, wide_zoom=1.0):
    """Crop rects in source px per (kind, person); 'wide' frames both people. sizes overrides SIZES (a 4K episode
    from a 4K take: smaller face shares keep the upscale near 1.5x); wide_zoom > 1 tightens the wide on the pair."""
    R, warn = {}, []
    asp = 16 / 9
    for p in P_people:
        b = p["box"]
        fh, cx, cy = b["h"] * SH, (b["x"] + b["w"] / 2) * SW, (b["y"] + b["h"] / 2) * SH
        others = [o["box"] for o in P_people if o is not p]

        def place(h):
            """x for a crop of height h: centred on the face, slid away from any other face it would cut through (the
            speaker stays between 36 % and 64 % of the width); clear = no other face inside."""
            w = min(SW, h * asp)
            x = min(max(0, cx - w / 2), SW - w)
            clear = True
            for o in others:
                ox0, ox1 = (o["x"] - 0.25 * o["w"]) * SW, (o["x"] + 1.25 * o["w"]) * SW
                if ox1 > x and ox0 < x + w:
                    nx = ox1 if (o["x"] + o["w"] / 2) * SW < cx else ox0 - w
                    if cx - 0.64 * w <= nx <= cx - 0.36 * w and 0 <= nx <= SW - w:
                        x = nx
                    else:
                        clear = False
            return x, w, clear

        single_h = None
        for kind, share in (sizes or SIZES).items():
            h0 = min(SH, fh / share)
            if kind == "tight" and single_h:              # a tight is always a visible punch-in on the single (~16 %)
                h0 = min(h0, single_h * 0.84)
            # people sitting close: tighten up to 20 % until the other face is out of the single (else keep it whole)
            for k in (1.0, 0.95, 0.9, 0.85, 0.8):
                x, w, clear = place(h0 * k)
                if clear:
                    break
            if not clear:
                x, w, clear = place(h0)
            h = w / asp
            if kind == "single":
                single_h = h
            y = min(max(0, cy - 0.40 * h), SH - h)
            R[(kind, p["id"])] = [round(x), round(y), round(w), round(h)]
            up = out_h / h
            if up > 1.5:
                warn.append(f"{kind} {p['id']}: crop {round(w)}x{round(h)} -> {out_h}p is a {up:.2f}x upscale (soft); record in 4K, or use fewer tight shots")
    if SW / SH >= asp:
        h = SH / wide_zoom
        w = h * asp
        xs = [((p["box"]["x"] + p["box"]["w"] / 2) * SW) for p in P_people]
        ys = [((p["box"]["y"] + p["box"]["h"] / 2) * SH) for p in P_people]
        x = min(max(0, (min(xs) + max(xs)) / 2 - w / 2), SW - w)
        y = min(max(0, sum(ys) / len(ys) - 0.33 * h), SH - h)          # the faces on the upper third
        R[("wide", None)] = [round(x), round(y), round(w), round(h)]
    else:
        h = SW / asp
        R[("wide", None)] = [0, round((SH - h) / 2), SW, round(h)]
    return R, warn


def turns_out(words, gap=1.5):
    T = []
    for w in words:
        if T and T[-1]["who"] == w["who"] and w["ot"] - T[-1]["b"] < gap:
            T[-1]["b"] = w["oe"]; T[-1]["n"] += 1; T[-1]["ends"].append(w["oe"])
        else:
            T.append({"a": w["ot"], "b": w["oe"], "who": w["who"], "n": 1, "ends": [w["oe"]]})
    return T


def direct(edl, people_ids, total, chapters_t=(), min_hold=2.5, max_hold=15.0, fps=30):
    f = 1.0 / fps
    W = edl["words"]
    T = turns_out(W)
    # interjections fold into the surrounding turn (no cut)
    T = [t for t in T if not (t["b"] - t["a"] < 1.5 and t["n"] < 4)] or T
    starts = [t["a"] for t in T]
    busy = lambda t: sum(1 for s in starts if t - 6 <= s <= t) >= 3
    other = lambda who: next((p for p in people_ids if p != who), None)
    # where a long hold may change: the end of a word followed by a pause (each gap, biggest first within a window)
    gaps = [(a["oe"], b["ot"] - a["oe"]) for a, b in zip(W, W[1:])]

    def split_points(a, b):
        """Every ~max_hold*0.8 s inside [a, b - min_hold]: the biggest pause in the next window (a sentence end when
        there is one, else the longest breath), so a long answer changes shot without cutting into a word."""
        pts, last = [], a
        while True:
            lo, hi = last + max_hold * 0.6, min(last + max_hold, b - min_hold)
            if hi <= lo:
                return pts
            cand = [(g, -t) for t, g in gaps if lo <= t <= hi]
            if not cand:
                return pts
            g, t = max(cand)                                       # the biggest pause; on a tie, the earliest
            t = -t
            pts.append(t)
            last = t
    shots, log = [], []
    add = lambda a, kind, who, why: shots.append({"a": round(a, 3), "kind": kind, "who": who, "why": why})
    add(0.0, "wide", None, "open")
    for t in T:
        a = t["a"] + 3 * f
        if a < 5.0:
            a = max(a, 5.0)
            if a >= t["b"]:
                continue
        kind = "wide" if busy(t["a"]) else "single"
        # the same person again after a folded interjection: the shot never changed, so its hold started earlier
        base = a
        if kind == "single" and shots and shots[-1]["kind"] in ("single", "tight") and shots[-1]["who"] == t["who"]:
            base = shots[-1]["a"]
        add(a, kind, None if kind == "wide" else t["who"], "quick exchange" if kind == "wide" else f"{t['who']} talks")
        # a long turn: vary at sentence boundaries, every ~max_hold*0.8
        if kind == "single":
            cyc, k = ["tight", "react", "wide"], 0
            for bnd in split_points(base, t["b"]):
                v = cyc[k % 3]; k += 1
                if v == "react" and other(t["who"]):
                    add(bnd, "single", other(t["who"]), "reaction"); add(bnd + 2.5, "single", t["who"], "back to the speaker")
                elif v == "tight":
                    add(bnd, "tight", t["who"], "long answer: closer")
                else:
                    add(bnd, "wide", None, "long answer: breathe"); add(bnd + 4.0, "single", t["who"], "back to the speaker")
    for c in chapters_t:
        add(c, "wide", None, "chapter"); add(c + 4.0, "_resume", None, "")
    shots.sort(key=lambda s: s["a"])
    # resume markers take the shot that was running before the chapter wide
    for i, s in enumerate(shots):
        if s["kind"] == "_resume":
            prev = next((x for x in reversed(shots[:i]) if x["kind"] not in ("_resume",) and x["why"] != "chapter"), shots[0])
            s.update(kind=prev["kind"], who=prev["who"], why="after the chapter")
    # jump cuts from trims inside a shot: change the size there
    for c in edl["cuts"]:
        cur = max((s for s in shots if s["a"] <= c), key=lambda s: s["a"], default=None)
        if cur and abs(cur["a"] - c) > 0.3 and cur["kind"] in ("single", "tight"):
            add(c, "tight" if cur["kind"] == "single" else "single", cur["who"], "hide the trim")
            shots.sort(key=lambda s: s["a"])
    add(max(0.0, total - 3.0), "wide", None, "close")
    shots.sort(key=lambda s: s["a"])
    # min hold: drop a shot that would end too soon (the trim-hiding size change and the close are kept)
    kept = []
    for i, s in enumerate(shots):
        nxt = shots[i + 1]["a"] if i + 1 < len(shots) else total
        if kept and (s["kind"], s["who"]) == (kept[-1]["kind"], kept[-1]["who"]):
            continue
        if kept and nxt - s["a"] < min_hold and s["why"] not in ("hide the trim", "close"):
            log.append(f"{s['a']:.1f} skip {s['kind']} {s['who'] or ''} ({s['why']}): would hold {nxt - s['a']:.1f} s")
            continue
        if kept and s["a"] - kept[-1]["a"] < min_hold and kept[-1]["why"] not in ("open",):
            s = dict(s, a=round(kept[-1]["a"] + min_hold, 3))
            if s["a"] >= nxt:
                continue
        kept.append(s)
    for i, s in enumerate(kept):
        s["b"] = kept[i + 1]["a"] if i + 1 < len(kept) else total
    kept = [s for s in kept if s["b"] - s["a"] > 0.2]
    share = {}
    for s in kept:
        share[s["kind"]] = share.get(s["kind"], 0) + s["b"] - s["a"]
    stats = {"shots": len(kept), "per_min": round(len(kept) / max(1e-9, total / 60), 1), "share": {k: round(v / total, 2) for k, v in share.items()}}
    return kept, log, stats
