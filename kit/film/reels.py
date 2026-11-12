"""Reels cut from the finished film by whole sentences (generalised from films/xchakra/shorts/cut.py and films/
reverse-engineer/shorts/cut.py, 2026-10-20). A Reel is a list of the film's sentences by the FILM's word ids, lifted
from the film's own tracks (its voice with every join already re-listened, its graded pictures, its respelled words),
so nothing is re-cut from the sources. Each Reel must tell a complete story on its own (OWNER_DEFAULTS §5).

In film.py:
    REELS = {"a": dict(sentences=[(first id, last id), ...],       # in the Reel's order, each a whole sentence
                       out="reel_a_<slug>.mp4", music=[dict(file=..., a=0, b="end", start=12.0, end_fade=0.6)],
                       start_at={id: film s}, end_at={id: film s},   # measured edges where the voice runs together
                       split=[id, ...],                              # a new range at these words: the film's held pause
                                                                     # before each is cut to its quiet points
                       hold={id: s},                                 # s with no voice after the range ending at word id
                                                                     # (the film's picture plays on; the page covers it)
                       voice_fx=[(id0, id1, "af")],                  # an ffmpeg filter on that passage of the voice
                       text={id: "text"}, data={...})}               # the Reel's own caption fixes and page data
and the page is <film>/reels/<name>/template.html (HF.reel, 1080x1920; a 16:9 track needs HF.reel(..., { src: [1920,
1080] })). Per Reel this writes, in the Reel's work folder: edl.json + cuts.json (pieces with their film span, kind and
face; the film's words re-timed), vo.wav, one picture track per film track (exact frames), faces (per frame), and
tracks.json (the Reel page's zoom budget per track and kind: kit/film/cut.py track_info).

    uv run python -m kit.film <film> reels [a b] [--plan]
    uv run python -m kit.film <film>/reels/a build | joins | mix | draft | render | mux
"""
from __future__ import annotations

import json
import subprocess

import numpy as np

from kit.film import build as B
from kit.film.config import FilmConfig

GAP_PIECE = 0.3                # an edge that spills under this far into the next / previous film piece ends on the piece


def mono(p, sr):
    return np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                                        capture_output=True, check=True).stdout, np.float32)


def env_db(x, sr):
    hop = sr // 100
    n = len(x) // hop
    return 20 * np.log10(np.sqrt(np.mean(np.square(x[: n * hop].reshape(n, hop)), axis=1)) + 1e-9)


def quiet_point(env, t, lo, hi):
    """The quietest 10 ms point in [lo, hi] (film s), nearest t on a tie."""
    a, b = max(0, int(lo * 100)), min(len(env) - 1, int(hi * 100))
    if b <= a:
        return t
    k = int(np.argmin(env[a:b + 1] + 0.02 * np.abs(np.arange(a, b + 1) / 100 - t)))
    return (a + k) / 100


def ranges(R, film, words, env):
    """Whole sentences -> film-time sub-ranges [{a, b, kind, face, clip, ids}], edges at quiet points on the film's voice,
    on the frame grid, split at the film's piece edges (each sub-range one kind and face)."""
    FPS, total = film.FPS, film.edl()["total"]
    order = [w["i"] for w in words]
    W = {w["i"]: w for w in words}
    merged = []
    for i0, i1 in R.SENTENCES:                                 # back-to-back sentences are one range (unless SPLIT
        if merged and order.index(merged[-1][1]) + 1 == order.index(i0) and i0 not in R.SPLIT:   # starts one there)
            merged[-1] = (merged[-1][0], i1)
        else:
            merged.append((i0, i1))
    out = []
    for i0, i1 in merged:
        k0, k1 = order.index(i0), order.index(i1)
        w0, w1 = W[i0], W[i1]
        prev = words[k0 - 1]["e"] if k0 else 0.0
        nxt = words[k1 + 1]["t"] if k1 + 1 < len(words) else total
        t0 = R.START_AT.get(i0, quiet_point(env, w0["t"] - 0.12, max(prev + 0.02, w0["t"] - 0.3), w0["t"] - 0.03))
        t1 = R.END_AT.get(i1, quiet_point(env, w1["e"] + 0.12, w1["e"] + 0.04, min(nxt - 0.02, w1["e"] + 0.35)))
        t0, t1 = np.floor(t0 * FPS + 1e-6) / FPS, np.ceil(t1 * FPS - 1e-6) / FPS
        ids = set(order[k0:k1 + 1])
        subs = []
        P = film.edl()["pieces"]
        for j, p in enumerate(P):              # a piece's span runs to the next piece's start: the pause after it (its
            end = P[j + 1]["out_a"] if j + 1 < len(P) else total     # picture plays on) stays with it, so sentences keep their breath
            a, b = max(t0, p["out_a"]), min(t1, end)
            if b - a >= 1 / FPS - 1e-6:
                subs.append({"a": round(a, 4), "b": round(b, 4), "kind": p["kind"], "face": p.get("face"), "ids": ids, "w": [i0, i1]})
        while len(subs) > 1 and subs[-1]["b"] - subs[-1]["a"] < GAP_PIECE:
            subs.pop()
        while len(subs) > 1 and subs[0]["b"] - subs[0]["a"] < GAP_PIECE:
            subs.pop(0)
        out += subs
    return out


def save_tracks(R, edl):
    """The Reel's own work/tracks.json (2026-10-22, v11 fix Pi-M1): its 1080 x 1920 page's zoom budget per track and per
    kind (kit/film/cut.py track_info: the film's source pixels per kind, the Reel's shares, render x1, ref = its page
    height), which build.track_data loads as D.tracks for the Reel's lens and precheck. Without it a Reel page's D.tracks
    carried only {file} and both fell back to the 1.2 guess. If it can't be worked out (a source missing), the Reel is
    still cut, and an older tracks.json is removed rather than left to describe another cut."""
    from kit.film.cut import write_tracks
    try:
        return write_tracks(R, edl)
    except (SystemExit, OSError, subprocess.CalledProcessError, ValueError, KeyError) as e:
        (R.work / "tracks.json").unlink(missing_ok=True)
        print(f"NOTE: tracks.json: skipped ({e}); the Reel's lens and precheck use the 1.2 default")
        return None


def cut_one(film, name, words, vo, env, plan_only=False):
    R = FilmConfig(film.dir / "reels" / name)
    FPS, SR = film.FPS, film.SR
    rs = ranges(R, film, words, env)
    t, pieces, ws = 0.0, [], []
    for k, r in enumerate(rs):
        n = int(round((r["b"] - r["a"]) * FPS))
        d = n / FPS
        cont = k and abs(rs[k - 1]["b"] - r["a"]) < 1e-3 and not pieces[-1].get("mute")
        pieces.append({"kind": r["kind"], "clip": "film", "tag": f"s{k}", "face": r["face"], "src_a": r["a"], "src_b": round(r["a"] + d, 4),
                       "speed": 1.0, "out_a": round(t, 4), "out_b": round(t + d, 4), "nf": n, "w": r["w"], "va": r["a"], "vb": round(r["a"] + d, 4),
                       "fi": 0.0 if cont else 0.025, "fo": 0.025, "after": 0.0})
        if cont:
            pieces[-2]["fo"] = 0.0
        for w in words:
            if w["i"] in r["ids"] and r["a"] - 1e-3 <= w["t"] < r["a"] + d:
                ws.append(dict(w, t=round(t + w["t"] - r["a"], 3), e=round(t + min(w["e"], r["a"] + d) - r["a"], 3)))
        t = round(t + d, 4)
        last = k + 1 == len(rs) or rs[k + 1]["w"] != r["w"]          # the range's last sub-range
        if last and R.HOLD.get(r["w"][1]):                            # a beat with no voice: the picture plays on
            m = int(round(R.HOLD[r["w"][1]] * FPS))
            pieces.append(dict(pieces[-1], tag=f"s{k}h", src_a=round(r["a"] + d, 4), src_b=round(r["a"] + (n + m) / FPS, 4), out_a=t,
                               out_b=round(t + m / FPS, 4), nf=m, va=round(r["a"] + d, 4), vb=round(r["a"] + (n + m) / FPS, 4), fi=0.0, fo=0.0, mute=True))
            t = round(t + m / FPS, 4)
    total = round((round(t * FPS) + round(R.TAIL * FPS)) / FPS, 4)          # a short tail: the Reel loops
    seen, words_out = set(), []
    for w in sorted(ws, key=lambda x: x["t"]):
        if w["i"] not in seen:
            seen.add(w["i"])
            words_out.append(w)
    print(f"reel {name}: {len(pieces)} pieces, talk {t:.2f} s, total {total:.2f} s")
    for p in pieces:
        txt = " ".join(w["text"] for w in words_out if p["out_a"] - 1e-3 <= w["t"] < p["out_b"])
        print(f"  film {p['src_a']:8.3f}-{p['src_b']:8.3f} -> {p['out_a']:6.2f}-{p['out_b']:6.2f}  {p['kind']:6s} {txt[:80]}")
    if plan_only:
        return
    # the voice: each range with short half-sine fades where it doesn't continue the one before
    y = np.zeros(int(round(total * SR)), np.float32)
    spf = SR / FPS                                         # samples a frame: placed by frame index, so pieces that continue
    for p in pieces:                                       # each other stay sample-contiguous (4-decimal times slipped 5 samples)
        if p.get("mute"):                                  # a hold: silence (the mix's bed fills it)
            continue
        s0 = int(round(round(p["src_a"] * FPS) * spf))
        seg = vo[s0:s0 + int(round(p["nf"] * spf))].copy()
        for side, d in (("in", p["fi"]), ("out", p["fo"])):
            m = min(len(seg), int(d * SR))
            if m:
                ramp = ((1 - np.cos(np.linspace(0, np.pi, m))) / 2).astype(np.float32)
                if side == "in":
                    seg[:m] *= ramp
                else:
                    seg[-m:] *= ramp[::-1]
        i = int(round(round(p["out_a"] * FPS) * spf))
        y[i:i + len(seg)] += seg[: len(y) - i]
    for i0, i1, af in R.VOICE_FX:                          # a filter on one passage (a soft line: a presence lift)
        w0, w1 = (next((w for w in words_out if w["i"] == i), None) for i in (i0, i1))
        if not (w0 and w1):
            print(f"NOTE: voice_fx {i0}-{i1}: not in this Reel")
            continue
        a, b = max(0, int((w0["t"] - 0.12) * SR)), min(len(y), int((w1["e"] + 0.12) * SR))
        fx = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", af,
                                           "-f", "f32le", "-"], input=y[a:b].tobytes(), capture_output=True, check=True).stdout, np.float32)[: b - a]
        m = min(len(fx) // 2, int(0.04 * SR))
        k = np.ones(len(fx), np.float32)                   # 1 = the filtered voice; raised-cosine ramps at both edges
        k[:m] = ((1 - np.cos(np.linspace(0, np.pi, m))) / 2).astype(np.float32)
        k[len(fx) - m:] = k[:m][::-1]
        y[a:a + len(fx)] = y[a:a + len(fx)] * (1 - k) + fx * k
        print(f"  voice_fx {i0}-{i1} ({a / SR:.2f}-{b / SR:.2f} s): {af}")
    R.work.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s24le",
                    str(R.work / "vo.wav")], input=y.tobytes(), check=True)
    # the pictures: the film's tracks over the same frames (they sit on the 1/FPS grid from 0); the tail holds the last frame
    N = int(round(total * FPS))
    tracks = film.edl().get("tracks", {})
    for name_t in tracks:
        tf, why = film.track_file(name_t)                 # the film's graded track while it is current
        if why:
            print("NOTE:", why, "(this Reel gets the ungraded cut)")
        args, fl = ["ffmpeg", "-v", "error", "-y"], []
        for k, p in enumerate(pieces):
            f0 = int(round(p["src_a"] * FPS))
            # a quarter frame before frame f0 (f0/FPS at 4 decimals rounds up past the frame for f0 = 2 mod 3: a frame late)
            args += ["-ss", f"{max(0.0, (f0 - 0.25) / FPS):.5f}", "-t", f"{p['nf'] / FPS + 0.2:.4f}", "-i", str(tf)]
            fl.append(f"[{k}:v]trim=end_frame={p['nf']},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{k}]")
        tail = N - sum(p["nf"] for p in pieces)
        # fps before tpad: after a concat tpad padded 2 of 12 frames (and xchakra's `-r 30` output hid nothing: count them)
        fl.append("".join(f"[v{j}]" for j in range(len(pieces))) + f"concat=n={len(pieces)}:v=1:a=0,fps={FPS},"
                  f"tpad=stop_mode=clone:stop_duration={tail / FPS + 1:.3f},trim=end_frame={N}[out]")
        out = R.work / f"{name_t}.mp4"
        args += ["-filter_complex", ";".join(fl), "-map", "[out]", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(film.TRACK_CRF),
                 "-g", "15", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                 "-movflags", "+faststart", str(out)]
        subprocess.run(args, check=True)
        from kit.film.cut import frames
        got = frames(out)
        if got != N:
            raise SystemExit(f"reel {name}: {out.name} has {got} frames, want {N}")
    # faces per Reel frame (the film's face track, mapped; a light 3-frame smoothing against detector jitter)
    ft = film.work / f"{film.FACE_TRACK}.face.json"
    tr = json.loads(ft.read_text()) if ft.exists() else None
    s = film.W / tracks[film.FACE_TRACK][0] if tr and film.FACE_TRACK in tracks else 1.0
    faces, last = [], list(film.FACE)
    for k in range(N):
        tt = (k + 0.5) / FPS
        p = next((q for q in pieces if q["out_a"] <= tt < q["out_b"]), None)
        if p is not None:
            f = tr[min(len(tr) - 1, int((p["src_a"] + tt - p["out_a"]) * FPS))] if tr else p["face"]
            if f and f[2] > 0:
                last = [round(v * (s if tr else 1.0), 1) for v in f[:3]]
        faces.append(last)
    for j in range(1, len(faces) - 1):
        faces[j] = [round((faces[j - 1][i] + faces[j][i] + faces[j + 1][i]) / 3, 1) for i in range(3)]
    edl = {"total": total, "talk_end": round(t, 4), "fps": FPS, "pieces": pieces, "words": words_out, "faces": faces, "tracks": tracks}
    R.edl_path.write_text(json.dumps(edl, indent=0))
    save_tracks(R, edl)
    cuts = [p["out_a"] for q, p in zip(pieces, pieces[1:]) if abs(p["src_a"] - q["src_b"]) >= 1e-3]
    (R.work / "cuts.json").write_text(json.dumps([round(c, 3) for c in cuts]))
    print(f"  -> {R.edl_path}, vo.wav, {', '.join(f'{n}.mp4' for n in tracks)} ({N} frames)")


def run(film, names=None, plan_only=False):
    if film.reel:
        raise SystemExit("reels: run it on the film, not on a Reel")
    if not film.REELS:
        raise SystemExit(f"{film.dir}/film.py has no REELS")
    edl = film.edl()
    words = B.fixed_words(film, edl)                     # the film's words as shown (spelled, placed on their sound)
    vo = mono(film.work / "vo.wav", film.SR)
    env = env_db(vo, film.SR)
    for name in names or list(film.REELS):
        cut_one(film, name, words, vo, env, plan_only)
