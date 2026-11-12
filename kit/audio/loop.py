"""Section-aware bed looping (2026-10-22, v11): one calm track fills a whole film even when it is shorter than its bed.

A long-form film runs 4-7 minutes and the calm beds run 2-3.5 (kit/music/calm). Until v11 a bed that ran out was padded
with zeros (a hole under the last minutes) or swapped for a second track. plan() builds a play list from the music map
(kit/music/beats.json) instead: it plays the track, jumps from a phrase start J back to an earlier one K, plays on, and
ends on the track's own ending. The jumps are chosen so the listener cannot hear them:
  - J and K are both downbeats a whole number of 4-bar phrases apart (the same bar phase), J never inside the ending
    and K never inside the intro, and a jump replays at least MIN_SPAN s (a short loop is heard as a loop);
  - the body loudness after K is within DB_MAX of the loudness after J (what plays next is as loud as what would have
    played), and the chroma (12 pitch classes) and RMS of the WIN s before and after each point match best, so the
    harmony and the section are the same on both sides;
  - section starts (the model's own boundaries) score a little better than mid-section phrase starts;
  - the groove lines up: the onsets in the 2 bars either side of J and of K are cross-correlated (10 ms steps, up to
    80 ms), and a jump whose onsets clearly line up at another offset than 0 by more than GROOVE_MS is dropped. A
    downbeat the map placed 50-60 ms off made the beat stumble at every seam (dim-the-lights' 96.22 -> 34.45, found
    by the 2026-10-22 seam check: the onsets matched at -60 ms with correlation 0.65 against 0.07 at 0);
  - each seam is an 80 ms equal-power crossfade centred on the downbeat (kit/audio/mix.py render()).
For the last bed (end=True) the play list ends on the track's last audible moment, landing between half a bar before
and one bar after the film's end (as kit/film/mix.py's end_on: the film's own tail fade covers the overshoot); the
start may move later by whole bars (up to SHIFT_BARS) to make the lengths meet. A middle bed only needs enough music.
plan() returns None when no seam passes: kit/film/mix.py then crossfades (2 s) into a second long-form bed.

    uv run python -m kit.audio.loop music/calm/calm__mixkit__piano-reflections.mp3 398      # the seams and a plan
"""
from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

FR = 22050             # analysis rate (the seams' fingerprints; the mix itself decodes at 48 kHz)
SEAM = 0.08            # s: the equal-power crossfade at each seam, centred on the downbeat
DB_MAX = 2.0           # dB: body loudness after K vs after J
WIN = 4.0              # s: the windows compared before and after each point
MIN_SPAN = 16.0        # s: a jump replays at least this much
PHRASE = 4             # bars: J and K this many bars apart (a multiple of it)
COS_AFTER = 0.85       # chroma similarity after the two points (cosine) at least ...
COS_BEFORE = 0.75      # ... and before them
SHIFT_BARS = 8         # the last bed's start may move this many bars later to make the lengths meet
TOP = 8                # the best seams combined
MAX_JUMPS = 8
GROOVE_MS = 20         # ms: the onsets either side of J and K may line up this far apart (two 10 ms steps) ...
GROOVE_CLEAR = (0.3, 0.15)   # ... a larger offset drops the jump when its correlation is at least 0.3 and 0.15 over 0's


@lru_cache(maxsize=6)
def pcm(path: str) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(FR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def audible_end(x: np.ndarray, floor_db=-50.0, sr=FR) -> float:
    """The track's last audible moment (s): the end of the last 50 ms window above `floor_db` (zero-padded tails and
    trailing silence are not music)."""
    w = int(0.05 * sr)
    n = len(x) // w
    if not n:
        return len(x) / sr
    lv = 10 * np.log10(np.mean(np.square(x[: n * w].reshape(n, w)), axis=1) + 1e-12)
    on = np.where(lv > floor_db)[0]
    return float((on[-1] + 1) * w / sr) if len(on) else 0.0


def chroma(x: np.ndarray, sr=FR) -> np.ndarray:
    """12 pitch classes (A = 0), summed over 4096-sample frames, unit length."""
    n = 4096
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    fr = np.lib.stride_tricks.sliding_window_view(x, n)[:: n // 2] * np.hanning(n)
    mag = np.sqrt(np.abs(np.fft.rfft(fr, axis=1)).sum(axis=0))
    f = np.fft.rfftfreq(n, 1 / sr)
    m = (f >= 65) & (f <= 4000)
    pc = np.round(12 * np.log2(f[m] / 440.0)).astype(int) % 12
    c = np.bincount(pc, weights=mag[m], minlength=12)
    return c / (np.linalg.norm(c) + 1e-12)


def feat(x: np.ndarray, t: float, w: float, sr=FR):
    """(dB, chroma) of [t, t + w) (w > 0) or [t + w, t) (w < 0)."""
    a, b = sorted((t, t + w))
    seg = x[max(0, int(a * sr)): max(0, int(b * sr))]
    if len(seg) < sr // 2:
        return None
    return 10 * np.log10(np.mean(np.square(seg)) + 1e-12), chroma(seg, sr)


def onsets(x: np.ndarray, t0: float, t1: float, sr=FR) -> np.ndarray:
    """The onset envelope of [t0, t1): the positive spectral flux of 512-sample frames every 10 ms."""
    hop, n = int(0.01 * sr), 512
    seg = x[max(0, int(t0 * sr)):max(0, int(t1 * sr))]
    if len(seg) < n:
        return np.zeros(max(1, len(seg) // hop))
    fr = np.lib.stride_tricks.sliding_window_view(np.pad(seg, (0, n)), n)[::hop][: len(seg) // hop] * np.hanning(n)
    S = np.log1p(np.abs(np.fft.rfft(fr, axis=1)))
    return np.concatenate([[0.0], np.maximum(np.diff(S, axis=0), 0).sum(1)])


def groove_lag(a: np.ndarray, b: np.ndarray, most=8) -> tuple[int, float, float]:
    """(lag ms, correlation there, correlation at 0) of two onset envelopes centred on J and K: the offset (10 ms steps,
    up to `most`) at which b's onsets line up with a's. 0 = the beat carries straight through the jump."""
    m = min(len(a), len(b))
    a, b = a[:m] - a[:m].mean(), b[:m] - b[:m].mean()
    den = np.linalg.norm(a) * np.linalg.norm(b)
    if m <= 2 * most or den <= 0:
        return 0, 0.0, 0.0
    c = np.array([float(np.dot(a[max(0, k):m + min(0, k)], b[max(0, -k):m - max(0, k)])) for k in range(-most, most + 1)]) / den
    i = int(np.argmax(c))
    return 10 * (i - most), float(c[i]), float(c[most])


def points(e: dict) -> list[tuple[float, int, bool]]:
    """(t, downbeat index, is a section start) for every phrase start: the downbeats PHRASE bars apart from the first
    section start that sits on a downbeat, plus every section start on a downbeat (within 0.15 s)."""
    d = np.array(e["downbeats"])
    if not e.get("steady") or len(d) < 2 * PHRASE:
        return []
    sec = {}
    for s in e["sections"]:
        i = int(np.argmin(np.abs(d - s["t"])))
        if abs(d[i] - s["t"]) <= 0.15:
            sec[i] = True
    ref = min(sec) if sec else 0
    out = {i: False for i in range(ref % PHRASE, len(d), PHRASE)}
    out.update(sec)
    return [(float(d[i]), i, s) for i, s in sorted(out.items())]


def seams(file: str | Path, e: dict) -> list[dict]:
    """Every jump J -> K that passes, best first: {j, k, span, score, d_after, d_before, cos_after, cos_before}."""
    x = pcm(str(file))
    end = audible_end(x)
    pts = points(e)
    if not pts:
        return []
    secs = [s["t"] for s in e["sections"]]
    # the intro ends at the first section start; the ending starts at the last section that falls (a breakdown into the
    # outro) in the last 30 s, else 2 bars before the audible end: K after the one, J before the other
    bar = float(np.median(np.diff(e["downbeats"])))
    intro = min(secs) - 0.2 if secs else 2 * bar
    falls = [s["t"] for s in e["sections"] if s["rise"] < 0 and s["t"] > end - 30]
    outro = min(falls) + 0.2 if falls else end - 2 * bar
    F = {t: (feat(x, t, WIN), feat(x, t, -WIN)) for t, _, _ in pts}
    G = {}                                                                 # onset envelopes, 2 bars each side (lazily)
    on = lambda t: G[t] if t in G else G.setdefault(t, onsets(x, t - 2 * bar, t + 2 * bar))
    out = []
    for tj, ij, sj in pts:
        if tj > outro or F[tj][0] is None or F[tj][1] is None:
            continue
        for tk, ik, sk in pts:
            if tk < intro or tk >= tj - MIN_SPAN + 1e-6 or (ij - ik) % PHRASE or F[tk][0] is None or F[tk][1] is None:
                continue
            (aj, cj), (bj, cbj) = F[tj]
            (ak, ck), (bk, cbk) = F[tk]
            d_after, d_before = abs(aj - ak), abs(bj - bk)
            cos_after, cos_before = float(cj @ ck), float(cbj @ cbk)
            if d_after > DB_MAX or cos_after < COS_AFTER or cos_before < COS_BEFORE:
                continue
            lag, c_lag, c0 = groove_lag(on(tj), on(tk))
            if abs(lag) > GROOVE_MS and c_lag >= GROOVE_CLEAR[0] and c_lag - c0 >= GROOVE_CLEAR[1]:
                continue                                                   # the beat would stumble by `lag` ms
            score = (1 - cos_after) + (1 - cos_before) + 0.05 * d_after + 0.025 * d_before - 0.02 * (sj + sk)
            out.append({"j": tj, "k": tk, "span": round(tj - tk, 3), "score": round(float(score), 4), "d_after": round(float(d_after), 2),
                        "d_before": round(float(d_before), 2), "cos_after": round(cos_after, 3), "cos_before": round(cos_before, 3),
                        "lag_ms": lag})
    return sorted(out, key=lambda s: s["score"])


def _orders(A, nA, B, nB):
    """The jump sequences for nA x A and nB x B (A's first, then B's first)."""
    yield [A] * nA + [B] * nB
    if B is not None and nB:
        yield [B] * nB + [A] * nA


def _valid(start, seq, end):
    """Play [start -> J1][K1 -> J2]...[Kn -> end]: every piece runs forward and lasts at least a bar's worth."""
    t = start
    for s in seq:
        if s["j"] <= t + 1.0:
            return False
        t = s["k"]
    return end > t + 1.0


def plan(file: str | Path, e: dict, start: float, need: float, end: bool = True, shift: bool = True) -> dict | None:
    """A play list for `need` s of music from track second `start`:
    {segments: [(t0, t1)], start, total, seams: [dict], how} or None (no seam passes; the caller falls back).
    end=True: the last piece ends on the track's last audible moment and the total lands within [need - 1/2 bar,
    need + 1 bar] (start may move up to SHIFT_BARS later when shift is True). end=False: total >= need."""
    x = pcm(str(file))
    D = audible_end(x)
    if D - start >= need:
        return None                                                         # no loop needed
    cand = seams(file, e)[:TOP]
    if not cand:
        return None
    d = np.array(e["downbeats"])
    bar = float(np.median(np.diff(d)))
    starts = [start]
    if end and shift:
        starts += [float(t) for t in d if start < t <= start + SHIFT_BARS * bar + 1e-6]
    lo, hi = (need - bar / 2, need + bar) if end else (need, float("inf"))
    best = None
    for s0 in starts:
        for ia, A in enumerate(cand):
            for B in [None] + cand[ia + 1:]:
                for nA in range(1, MAX_JUMPS + 1):
                    for nB in range(0, (MAX_JUMPS - nA if B is not None else 0) + 1):
                        if B is not None and not nB:
                            continue
                        total = D - s0 + nA * A["span"] + nB * (B["span"] if B else 0)
                        if not lo <= total <= hi:
                            continue
                        for seq in _orders(A, nA, B, nB):
                            if not _valid(s0, seq, D):
                                continue
                            # fewest seams first; then the best seams, with landing nearer the film's end as a small
                            # bonus (anywhere in the window is fine: the film's tail covers it); then the least start shift
                            key = (len(seq), sum(s["score"] for s in seq) + (0.02 * abs(total - need) / bar if end else 0), s0 - start)
                            if best is None or key < best[0]:
                                best = (key, s0, seq, total)
                            break
    if best is None:
        return None
    _, s0, seq, total = best
    segs, t = [], s0
    for s in seq:
        segs.append((round(t, 4), s["j"]))
        t = s["k"]
    segs.append((round(t, 4), round(D, 4)))
    jumps = ", ".join("%g->%g" % (s["j"], s["k"]) for s in seq)
    how = (f"loops {len(seq)}x ({jumps}), " + (f"ends on the track's ending {total - need:+.2f} s from the bed's end" if end else
                                                f"{total:.1f} s of music for the {need:.1f} s it needs")
           + (f"; start {start:g} -> {s0:g} (whole bars)" if s0 != start else ""))
    return {"segments": segs, "start": s0, "total": round(total, 3), "seams": seq, "how": how}


def seam_times(a: float, segs) -> list[float]:
    """Film times of the seams of a play list that starts at film time a."""
    out, t = [], a
    for t0, t1 in segs[:-1]:
        t += t1 - t0
        out.append(round(t, 3))
    return out


def film_downbeats(e: dict, a: float, segs) -> list[float]:
    """The track's downbeats in film time through a play list (each piece maps its own range)."""
    out, t = [], a
    for t0, t1 in segs:
        out += [t + (x - t0) for x in e["downbeats"] if t0 - 1e-6 <= x < t1 - 1e-6]
        t += t1 - t0
    return out


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from kit.audio import beats as BT
    f = sys.argv[1]
    e = BT.entry(f)
    if not e:
        raise SystemExit(f"{f}: not in the music map (python -m kit.audio.beats --check)")
    p = Path(f)
    p = p if p.is_absolute() else (BT.MUSIC / p.relative_to("music") if p.parts[0] == "music" else BT.MUSIC / p)
    for s in seams(p, e)[:12]:
        print(s)
    if len(sys.argv) > 2:
        print(plan(p, e, float(sys.argv[3]) if len(sys.argv) > 3 else 0.0, float(sys.argv[2])))


if __name__ == "__main__":
    main()
