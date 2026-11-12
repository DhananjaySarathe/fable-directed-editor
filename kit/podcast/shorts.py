"""Vertical Shorts (1080x1920) from a one-camera podcast (2026-10-12, films/guest-podcast).

A Short is a whole-sentence stretch of the episode (the owner's rules: it stands alone, never a teaser or montage; no
cropped sentences; a ~2.5 s "full podcast on YouTube" card at the end because the long video goes with it), cut tighter
than the episode (pauses to ~0.12 s), framed for a phone:

  face    the speaker, a 9:16 crop that follows whoever talks (face on the upper third, ~17 % of the height)
  stack   both people, one above the other (the classic podcast-clip frame), for exchanges and reactions
  card    a full-screen proof (a screenshot, a page) with the speaker in a circle, from the film's assets
  slam    one hero word over the darkened face

The recipe (films/<name>/shorts.py) lists, per Short: keep (word ranges in order), trim (extra cuts), the hook line,
captions (phrase-level, spelling fixed by hand: Hinglish transcripts are rough), layouts (word id -> layout), cards,
slams and the music. This module makes the pieces, both picture layers and the voice; the page is kit/podcast/short.html.
"""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from kit.podcast import audio, look, speakers
from kit.podcast import edl as pedl
from kit.podcast.render import tonemap

SR = 48000
FPS = 30


def sh(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def edit(P, S, attr, env, thr):
    """The Short's edit list: its keep ranges in order, the episode's cuts + its own trims, tight pauses."""
    R = SimpleNamespace(FPS=FPS, CUT=list(P.CUT) + [tuple(t) for t in S.get("trim", [])], GAP_MAX=S.get("gap_max", 0.32),
                        GAP_KEEP=S.get("gap_keep", 0.12), SEQUENCE=[tuple(k) for k in S["keep"]])
    return pedl.build(R, attr, env, thr)


def people(P, M):
    edges = [0.0, *P.SPLITS, 1e9]
    return [{"a": a, "b": b, "p": {p["id"]: p["box"] for p in speakers.people([m for m in M if a <= m["t"] < b], k=len(P.PEOPLE))}}
            for a, b in zip(edges, edges[1:])]


def crop(box, SW, SH, aspect, share, eye=0.36):
    """A crop of the given aspect (w/h) with the face at `share` of its height, eyes near `eye` from the top."""
    fh = box["h"] * SH
    h = min(SH, fh / share)
    w = min(SW, h * aspect)
    h = w / aspect
    cx, cy = (box["x"] + box["w"] / 2) * SW, (box["y"] + box["h"] / 2) * SH
    x = min(max(0, cx - w / 2), SW - w)
    y = min(max(0, cy - eye * h), SH - h)
    return [round(x / 2) * 2, round(y / 2) * 2, round(w / 2) * 2, round(h / 2) * 2]


def speaker_shots(E, min_hold=1.2):
    """Who to show on the face layer: the speaker, switching 2 frames after a new voice, interjections < 0.8 s folded."""
    T = []
    for w in E["words"]:
        if T and T[-1]["who"] == w["who"]:
            T[-1]["b"] = w["oe"]
        else:
            T.append({"a": w["ot"], "b": w["oe"], "who": w["who"]})
    T = [t for t in T if t["b"] - t["a"] >= 0.8] or T
    out = []
    for t in T:
        a = 0.0 if not out else t["a"] + 2 / FPS
        if out and out[-1]["who"] == t["who"]:
            continue
        if out and a - out[-1]["a"] < min_hold:
            continue
        out.append({"a": round(a, 3), "who": t["who"]})
    for i, s in enumerate(out):
        s["b"] = out[i + 1]["a"] if i + 1 < len(out) else E["total"]
    return out


def _seg(P, src_a, dur, rect, vf, out, W, H):
    x, y, w, h = rect
    parts = vf.split(",") if vf else []
    post = [g for g in parts if g.startswith(("unsharp", "vignette"))]
    pre = [g for g in parts if g not in post]
    chain = ",".join([f"crop={w}:{h}:{x}:{y}", tonemap(P.source).rstrip(",")] + pre + [f"scale={W}:{H}:flags=lanczos"] + post + [f"fps={FPS}", "format=yuv420p"])
    chain = chain.replace(",,", ",")
    sh(["ffmpeg", "-v", "error", "-y", "-hwaccel", "videotoolbox", "-ss", f"{src_a:.3f}", "-i", P.source, "-t", f"{dur:.3f}", "-vf", chain,
        "-an", "-c:v", "h264_videotoolbox", "-b:v", "24M", "-g", "30", out])


def layers(P, E, shots, PB, vf, work):
    """face.mp4 (the speaker, 1080x1920) and stack.mp4 (both, 1080x960 each) for the Short's whole timeline."""
    SW, SH = 3840, 2160
    from concurrent.futures import ThreadPoolExecutor
    jobs = []
    for p in E["pieces"]:
        take = next(x for x in PB if x["a"] <= p["src_a"] < x["b"])
        for s in shots:
            a, b = max(s["a"], p["out_a"]), min(s["b"], p["out_b"])
            if b - a > 1e-3:
                jobs.append(("face", a, p["src_a"] + a - p["out_a"], b - a, crop(take["p"][s["who"]], SW, SH, 9 / 16, 0.17), 1080, 1920))
        for who in ("A", "B"):
            jobs.append((f"stack{who}", p["out_a"], p["src_a"], p["out_b"] - p["out_a"], crop(take["p"][who], SW, SH, 1080 / 960, 0.26, 0.42), 1080, 960))
    seg = work / "seg"
    seg.mkdir(parents=True, exist_ok=True)
    jobs.sort(key=lambda j: (j[0], j[1]))

    def one(k_j):
        k, (layer, a, src_a, d, rect, W, H) = k_j
        o = seg / f"{layer}_{k:04d}.mp4"
        _seg(P, src_a, d, rect, vf, o, W, H)
        return layer, o
    with ThreadPoolExecutor(6) as ex:
        done = list(ex.map(one, enumerate(jobs)))
    out = {}
    for layer in ("face", "stackA", "stackB"):
        files = [o for l, o in done if l == layer]
        lst = seg / f"{layer}.txt"
        lst.write_text("".join(f"file '{f}'\n" for f in files))
        out[layer] = work / f"{layer}.mp4"
        sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out[layer]])
    stack = work / "stack.mp4"
    sh(["ffmpeg", "-v", "error", "-y", "-i", out["stackA"], "-i", out["stackB"], "-filter_complex", "[0:v][1:v]vstack=inputs=2[v]", "-map", "[v]",
        "-c:v", "h264_videotoolbox", "-b:v", "24M", "-g", "30", stack])
    return work / "face.mp4", stack


def voice(P, E, work):
    """The Short's voice: the episode's cleaned take, cut on the pieces (25 ms fades), polished like the episode."""
    x = audio.dec(P.work / "voice_clean.wav")
    y = audio.cut(x, E["pieces"])
    y, _ = audio.level(y, E["words"])
    pre, out = work / "voice_pre.wav", work / "voice.wav"
    audio.wav(pre, y[: int(E["total"] * SR)])
    sh(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af", "highpass=f=80,acompressor=threshold=0.063:ratio=2:attack=10:release=180:makeup=1,deesser=i=0.35", out])
    return out


def mix(voice_wav, music, total, end_len, cues, out, sfx_dir, music_dir):
    """Voice + a bed (about 12 dB under the voice while he talks, up in the gaps and under the end card) + cues -> -14 LUFS."""
    from kit.audio.mix import master
    n = int((total + end_len) * SR)
    raw = sh(["ffmpeg", "-v", "error", "-i", voice_wav, "-ac", "1", "-ar", SR, "-f", "f32le", "-"], capture_output=True).stdout
    v = np.zeros(n, np.float32)
    vv = np.frombuffer(raw, np.float32)[:n]
    v[:len(vv)] = vv
    rms = np.sqrt(np.mean(vv[np.abs(vv) > 1e-3] ** 2)) if len(vv) else 1
    v *= 10 ** (-20 / 20) / max(rms, 1e-6)
    out_st = np.repeat(v[:, None], 2, axis=1)
    if music:
        raw = sh(["ffmpeg", "-v", "error", "-ss", f"{music.get('from', 0):.2f}", "-i", music_dir / music["file"], "-t", f"{(total + end_len) + 0.5:.2f}",
                  "-ac", "2", "-ar", SR, "-f", "f32le", "-"], capture_output=True).stdout
        m = np.frombuffer(raw, np.float32).reshape(-1, 2)[:n].copy()
        if len(m) < n:
            m = np.vstack([m, np.zeros((n - len(m), 2), np.float32)])
        # talk envelope (50 ms windows), smoothed: the bed ducks under the voice
        win = int(0.05 * SR)
        e = np.sqrt(np.convolve(v ** 2, np.ones(win) / win, mode="same"))
        talk = (e > 10 ** (-38 / 20)).astype(np.float32)
        k = int(0.25 * SR)
        talk = np.convolve(talk, np.ones(k) / k, mode="same")
        mrms = np.sqrt(np.mean(m[: int(min(len(m), 20 * SR))] ** 2)) + 1e-6
        base = 10 ** ((-20 + music.get("under", -12)) / 20) / mrms              # ~12 dB under the voice
        g = base * (1 + talk * (10 ** (-3 / 20) - 1)) / (10 ** (-3 / 20))      # a little up in the gaps (+3 dB)
        g = np.minimum(g, base * 1.41)
        g[int(total * SR):] = base * 2.0                                        # the end card: the bed up
        fade = int(1.2 * SR)
        g[-fade:] *= np.linspace(1, 0, fade)
        g[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
        out_st += m * g[:, None]
    for name, t, db in cues:
        r = sh(["ffmpeg", "-v", "error", "-i", sfx_dir / name, "-ac", "2", "-ar", SR, "-f", "f32le", "-"], capture_output=True).stdout
        s = np.frombuffer(r, np.float32).reshape(-1, 2) * 10 ** (db / 20)
        i = max(0, int(t * SR))
        s = s[: n - i]
        out_st[i:i + len(s)] += s
    pre = Path(out).with_name("mix_pre.wav")
    sh(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", SR, "-ac", 2, "-i", "-", "-c:a", "pcm_s24le", pre], input=out_st.astype(np.float32).tobytes())
    master(pre, out, lufs=-14.0)
    return out


def grade(P, M):
    ppl = speakers.people([m for m in M if m["t"] < (P.SPLITS[0] if P.SPLITS else 1e9)], k=len(P.PEOPLE))
    meas = look.measure(P.source, P.SPLITS[0] if P.SPLITS else 600, ppl)
    return look.filters(meas, P.LOOK)
