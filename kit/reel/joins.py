"""The voice-cut audit: no clipped word, no stray syllable, at any join (the owner's rule: "if you are saying
something, make sure it's completely said"). Run after `kit.reel edl`, before any picture work.

1. Envelope check of every piece edge on the cleaned source voice (10 ms frames), against the word times:
   CLIP-TAIL   the last word's sound goes on past the out-point (the word end was placed early) -> END_FIX
   CLIP-HEAD   the first word's sound starts before the in-point (its onset is cut)              -> START_FIX
   EXTRA-TAIL  a separate sound between the last word and the out-point (the next word's onset leaks in)
   EXTRA-HEAD  a separate sound between the in-point and the first word (the previous word's tail leaks in)
   HOT-CUT     the out- or in-point itself sits on loud voice (a click / chopped syllable even with the fade)
   Each finding prints the measured time to put in START_FIX / END_FIX (reel.py), then re-run edl.
2. The re-listen: kit.cut.cutcheck --media=vo.wav (whisper on t-8..t+4 s around every join): a join where the fresh
   transcript loses or adds words next to the cut becomes REVIEW.
Exit 3 when any HIGH finding (CLIP-*, EXTRA-*, HOT-CUT) or an unjudged REVIEW/FAIL is left.
"""
import json

import numpy as np

from kit.reel import edl as E


def _runs(mask):
    """[(i0, i1)] runs of True (i1 exclusive)."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def audit(R, edl):
    W = E.words(R)
    env = E.envelope(E.voice(R, clean=False), R.SR)
    speech = float(np.percentile(env[env > -60], 75))
    quiet = speech - 24            # under this: silence / room
    hot = speech - 10              # over this: clearly voiced
    at = lambda t: float(env[min(len(env) - 1, max(0, int(round(t * 100))))])
    find = []
    pcs = edl["pieces"]
    for k, p in enumerate(pcs):
        i0, i1 = p["w"]
        a, b = p.get("va", p["src_a"]), p.get("vb", p["src_b"])
        w0, w1 = W[i0], W[i1]
        cont_in = k > 0 and pcs[k - 1]["w"][1] + 1 == i0 and abs(pcs[k - 1]["src_b"] - a) < 0.02
        cont_out = k + 1 < len(pcs) and pcs[k + 1]["w"][0] == i1 + 1 and abs(pcs[k + 1]["src_a"] - b) < 0.02
        # ---- out-point
        if not cont_out:
            nxt = W[i1 + 1]["start"] if i1 + 1 < len(W) else 1e9
            # where the last word's sound really ends: first 50 ms run under speech-16 dB after its end time
            # (a room tail at -20 dB under a 25 ms fade is inaudible; a voiced syllable is not)
            t, end = w1["end"], None
            while t < min(nxt, w1["end"] + 0.6):
                if all(at(t + d) < speech - 16 for d in (0, 0.01, 0.02, 0.03, 0.04)):
                    end = t
                    break
                t += 0.01
            if end is not None and end > b + 0.02 and end < nxt - 0.03:
                find.append(("HIGH", "CLIP-TAIL", p, f"'{w1['text']}' sounds until {end:.2f} s, the cut is at {b:.2f} s",
                             {"END_FIX": {i1: round(end, 2)}}))
            seg = np.arange(int((w1["end"] + 0.03) * 100), int(b * 100))
            if len(seg):
                rs = [r for r in _runs(env[seg] > quiet + 6) if r[1] - r[0] >= 4]
                if rs and (end is None or seg[rs[0][0]] / 100 > end):
                    find.append(("HIGH", "EXTRA-TAIL", p, f"a separate sound {seg[rs[0][0]] / 100:.2f}-{seg[rs[0][1] - 1] / 100:.2f} s after "
                                 f"'{w1['text']}' (ends {w1['end']:.2f}) and before the cut {b:.2f}", {"END_FIX": {i1: round(w1["end"], 2)}}))
            if at(b) > hot:
                find.append(("HIGH", "HOT-CUT", p, f"out-point {b:.2f} s on loud voice ({at(b) - speech:+.0f} dB vs speech) after '{w1['text']}'", {}))
            elif at(b) > quiet and not cont_out:
                find.append(("MED", "EDGE-IN-SOUND", p, f"out-point {b:.2f} s not in quiet ({at(b) - speech:+.0f} dB) after '{w1['text']}'", {}))
        # ---- in-point
        if not cont_in:
            prv = W[i0 - 1]["end"] if i0 > 0 else -1
            t, st = w0["start"], None
            while t > max(prv, w0["start"] - 0.5):
                if all(at(t - d) < speech - 16 for d in (0, 0.01, 0.02, 0.03)):
                    st = t
                    break
                t -= 0.01
            if st is not None and st < a - 0.02 and st > prv + 0.03:
                find.append(("HIGH", "CLIP-HEAD", p, f"'{w0['text']}' starts sounding at {st:.2f} s, the cut is at {a:.2f} s",
                             {"START_FIX": {i0: round(st + 0.01, 2)}}))
            seg = np.arange(int(a * 100), int((w0["start"] - 0.03) * 100))
            if len(seg):
                rs = [r for r in _runs(env[seg] > quiet + 6) if r[1] - r[0] >= 4]
                if rs and (st is None or seg[rs[-1][1] - 1] / 100 < st):
                    find.append(("HIGH", "EXTRA-HEAD", p, f"a separate sound {seg[rs[0][0]] / 100:.2f}-{seg[rs[-1][1] - 1] / 100:.2f} s between the "
                                 f"cut {a:.2f} and '{w0['text']}' ({w0['start']:.2f})", {"START_FIX": {i0: round(w0["start"] - 0.03, 2)}}))
            if at(a) > hot:
                find.append(("HIGH", "HOT-CUT", p, f"in-point {a:.2f} s on loud voice ({at(a) - speech:+.0f} dB) before '{w0['text']}'", {}))
            elif at(a) > quiet:
                find.append(("MED", "EDGE-IN-SOUND", p, f"in-point {a:.2f} s not in quiet ({at(a) - speech:+.0f} dB) before '{w0['text']}' (a breath or attack may be clipped)", {}))
    return find


def relisten_media(R):
    from kit.cut import cutcheck
    from kit.cut.common import IdMap
    ids = IdMap.parse(f"{R.TAKE}=0")
    res = cutcheck.check(str(R.dir / "edl.json"), ids, media=str(R.work / "vo.wav"), do_relisten=True, log=lambda *a, **k: None)
    bad = []
    for j in res["joins"] + res.get("trims", []):
        if j["verdict"] in ("FAIL", "REVIEW") and (j["left_id"], j["right_id"]) not in R.JUDGED:
            bad.append(j)
    (R.work / "cutcheck_media.json").write_text(json.dumps(res, indent=1, default=str))
    return res, bad


def run(R, relisten=True):
    edl = json.loads((R.dir / "edl.json").read_text())
    find = audit(R, edl)
    for sev, kind, p, why, fix in find:
        print(f"  {sev:4s} {kind:10s} {p['out_a']:6.2f}s [{p['tag']}] {why}   fix: {fix}")
    code = 3 if any(f[0] in ("HIGH", "MED") for f in find) else 0
    print(f"joins audit: {len(edl['pieces'])} pieces, {len(find)} findings")
    if relisten:
        res, bad = relisten_media(R)
        print(f"re-listen: {res['verdict']}, {len(bad)} unjudged REVIEW/FAIL")
        for j in bad:
            print(f"  {j['verdict']:6s} {j.get('kind', 'trim'):10s} {j['t']:6.2f}s {j['left_id']}->{j['right_id']} {j.get('why', '')}"
                  f" | {j.get('left', '')} || {j.get('right', '')}  heard: {j.get('heard', j.get('relisten', ''))}")
        if bad:
            code = 3
    return code
