"""The podcast's sound: the voice cleaned gently, cut on the edit, the two people levelled, mastered.

  1. clean   the take's audio, [WPE dereverb if DEREVERB], then DeepFilterNet3 with an attenuation limit (DENOISE_DB,
             default 14 dB): the background drops, it isn't erased (the owner asked for "noise reduction a bit")
  2. cut     the edit's pieces in order, 25 ms hsin fades on every join (room tone comes with the kept quiet)
  3. level   each person's speech is measured (their words only) and brought to the same level, with 120 ms gain
             ramps at speaker changes: the far person on one phone mic is often 4-8 dB quieter
  4. polish  high-pass 80 Hz, a gentle compressor (2:1 above -24 dB), a light de-esser
  5. master  two-pass loudnorm to LUFS (-14 YouTube / -16 audio-only), true peak -1.5 dBTP (kit/audio/mix.master)
  Music: none by default. MUSIC = {...} adds a quiet bed under the intro and outro only.
"""
import subprocess
from pathlib import Path

import numpy as np

SR = 48000
VENV = Path.home() / ".venvs"


def sh(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def dec(p, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def wav(path, x, sr=SR):
    sh(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", sr, "-ac", 1, "-i", "-", "-c:a", "pcm_s24le", path], input=x.astype(np.float32).tobytes())


def clean(P):
    raw, out = P.work / "voice_raw.wav", P.work / "voice_clean.wav"
    if out.exists() and out.stat().st_mtime > Path(P.source).stat().st_mtime:
        return out
    sh(["ffmpeg", "-v", "error", "-y", "-i", P.source, "-vn", "-ac", "1", "-ar", SR, "-c:a", "pcm_s16le", raw])
    src = raw
    if P.DEREVERB and (VENV / "wpe/bin/python").exists():
        wpe = P.work / "voice_wpe.wav"
        sh([VENV / "wpe/bin/python", Path(__file__).resolve().parents[1] / "reel/dereverb.py", raw, wpe], stdout=subprocess.DEVNULL)
        src = wpe
    df = VENV / "df/bin/deepFilter"
    if df.exists():
        sh([df, src, "-o", P.work, "-a", str(P.DENOISE_DB)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (P.work / f"{src.stem}_DeepFilterNet3.wav").rename(out)
    else:
        print("audio: DeepFilterNet not found (~/.venvs/df): using ffmpeg's afftdn (gentler, simpler)")
        sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"afftdn=nr={min(20, P.DENOISE_DB)}:nf=-40", out])
    return out


def cut(x, pieces, fade=0.025):
    n = int(fade * SR)
    ramp = np.sin(np.linspace(0, np.pi / 2, n)) ** 2                    # hsin
    parts = []
    for p in pieces:
        seg = x[int(p["src_a"] * SR):int(p["src_b"] * SR)].copy()
        if len(seg) > 2 * n:
            seg[:n] *= ramp; seg[-n:] *= ramp[::-1]
        parts.append(seg)
    return np.concatenate(parts) if parts else x[:0]


def level(y, words, ramp=0.12):
    """Bring each person's speech RMS to the mean of all; returns the levelled signal and the gains in dB."""
    def rms_db(seg):
        return 20 * np.log10(np.sqrt(np.mean(seg * seg)) + 1e-9)
    by = {}
    for w in words:
        a, b = int(w["ot"] * SR), int(w["oe"] * SR)
        if b > a:
            by.setdefault(w["who"], []).append(y[a:b])
    lv = {k: rms_db(np.concatenate(v)) for k, v in by.items() if v}
    if len(lv) < 2:
        return y, {k: 0.0 for k in lv}
    target = float(np.mean(list(lv.values())))
    gain = {k: float(np.clip(target - v, -9, 9)) for k, v in lv.items()}
    g = np.zeros(len(y), np.float32)
    ws = sorted(words, key=lambda w: w["ot"])
    for j, w in enumerate(ws):                                        # each word's stretch, up to the next word, takes
        a = 0 if j == 0 else int(w["ot"] * SR)                        # its speaker's gain (held through the pause)
        b = int(ws[j + 1]["ot"] * SR) if j + 1 < len(ws) else len(y)
        g[a:b] = gain.get(w["who"], 0.0)
    k = int(ramp * SR)
    if k > 1:
        g = np.convolve(g, np.ones(k) / k, mode="same").astype(np.float32)
    return y * (10 ** (g / 20)), gain


def master(P, y, total):
    sys_path = Path(__file__).resolve().parents[2]
    import sys
    sys.path.insert(0, str(sys_path))
    from kit.audio.mix import master as kmaster
    pre, mid, out = P.work / "pod_pre.wav", P.work / "pod_polish.wav", P.work / "pod_mix.wav"
    wav(pre, y[: int(total * SR)])
    sh(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
        "highpass=f=80,acompressor=threshold=0.063:ratio=2:attack=10:release=180:makeup=1,deesser=i=0.35", mid])
    if P.MUSIC:
        mid = music(P, mid, total)
    kmaster(mid, out, lufs=P.LUFS)
    return out


def music(P, voice, total):
    """A quiet bed under the intro and the outro only (never under the conversation)."""
    m = P.MUSIC
    root = Path(__file__).resolve().parents[1] / "music"
    intro, outro, under = m.get("intro", 6.0), m.get("outro", 8.0), m.get("under", -24)
    out = P.work / "pod_music.wav"
    vol = 10 ** (under / 20)
    expr = f"if(lt(t,{intro}),1,if(gt(t,{total - outro}),1,0))"
    sh(["ffmpeg", "-v", "error", "-y", "-i", voice, "-stream_loop", "-1", "-i", root / m["file"], "-filter_complex",
        f"[1:a]atrim=0:{total},volume='{vol}*{expr}':eval=frame,afade=t=in:d=1,afade=t=out:st={total - 3}:d=3[m];[0:a][m]amix=inputs=2:normalize=0[a]",
        "-map", "[a]", "-ac", "2", "-ar", SR, out])
    return out


def run(P, edl):
    x = dec(clean(P))
    y = cut(x, edl["pieces"])
    y, gains = level(y, edl["words"])
    out = master(P, y, edl["total"])
    print("audio: levelled " + ", ".join(f"{k} {v:+.1f} dB" for k, v in gains.items()) + f" -> {out}")
    return out, gains
