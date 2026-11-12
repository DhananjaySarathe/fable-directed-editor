"""Source prep: the words (shorts probe + analyze), the picture intermediate, the cleaned voice and its measured EQ, so a
film needs no prep.py of its own (from films/reverse-engineer/prep.py + voice_eq.py, films/ai-workflows/prep.py and
kit/reel/prep.py, 2026-10-20). Each step skips when its output exists; `--force=<step>` redoes it.

  words    `shorts probe [--landscape]` + `shorts analyze` for a source with a `file` and no analysis.json yet
  picture  work/take<c>.mp4: a CFR SDR copy at the film's FPS from the original file (HLG tone-mapped as shorts probe
           does), for `picture=True` (a 4K take: shorts probe keeps a 16:9 take at 1080p) or `picture=(w, h)`
  voice    work/voice<c>_df.wav for `clean=True` or `clean=dict(...)`:
             mic       "mono" (the first channel; default), "mid" ((L+R)/2: a screen recording whose mic is the
                       centre) or "right"
             declip    3 dB of headroom and adeclip first (a recording whose mix clips)
             dereverb  two-channel WPE (kit/reel/dereverb.py, ~/.venvs/wpe) on both mics before DeepFilterNet: only
                       when the two channels really differ (identical channels cancelled a take's voice to -61 LUFS, 2026-10-18)
           then DeepFilterNet3 (~/.venvs/df). The source's `voice` then points here by itself
  eq       work/voice_eq.json: each cleaned voice's 1/3-octave speech spectrum against one target (the long-term
           average speech spectrum, darker on top), a smooth correction capped at -8 / +6 dB, and a gain to -21 LUFS;
           the cut's voice chain becomes the measured EQ, a gentle expander, a de-esser, compression and -19 LUFS (the
           same target is what made three different mics sit together in films/reverse-engineer). `clean=dict(eq=False)`
           keeps the plain chain

    uv run python -m kit.film <film> prep [--only=words,picture,voice,eq] [--force=voice]
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from kit.film import tonemap as T
from kit.paths import ROOT, job_dir

TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
# HLG -> SDR (2026-10-22, v11): HLG's reference white is 203 nits, so npl=203 puts it at 1.0 (npl=100 put it at 2.03
# and left hable to squash it); mobius is linear up to its knee and rolls off only above, where hable bends the mids
# too. On an iPhone HLG selfie (output/jobs/reel0236, 3 frames): mid tones +16-20 code values (p50 123 -> 143), skin
# +7-8, the brightest wall and the 99th percentile unchanged (243 / 244-246): a more open picture with the same
# highlights, before look v2 re-exposes the face per shot (scratchpad build/picture/hlg). shorts probe's own copy
# (shorts/media/normalize.py) still uses the old chain.
# 2026-10-23: the tone map is a per-film choice, TONEMAP in film.py (kit/film/tonemap.py: "mobius" (this default, so
# older films stay as they were), "hable", "bt2390" (BT.2390's roll-off as a 3D LUT, dithered to 8 bit), "bt2390c")
TONEMAP = T.chain("mobius")
DF = Path.home() / ".venvs/df/bin/deepFilter"
WPE = Path.home() / ".venvs/wpe/bin/python"
STEPS = ("words", "picture", "voice", "eq")
# voice_eq: the target (Byrne et al. 1994 LTASS to 4 kHz, a little darker above), the bands, the caps
BANDS = [63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500]
TARGET = {63: -16, 80: -10, 100: -3, 125: 4, 160: 3.5, 200: 6.5, 250: 6.6, 315: 5.8, 400: 7.5, 500: 7.2, 630: 6.0, 800: 3.1,
          1000: 0, 1250: -0.7, 1600: -1.7, 2000: -4.2, 2500: -5.2, 3150: -6.6, 4000: -8.0, 5000: -10.0, 6300: -11.5,
          8000: -13.0, 10000: -16.0, 12500: -20.0}
EQ_LO, EQ_HI = -8.0, 6.0


def sh(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd)[:220], flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def clean_opts(s) -> dict | None:
    c = s.get("clean")
    if not c:
        return None
    return dict(dict(mic="mono", declip=False, dereverb=False, eq=True), **(c if isinstance(c, dict) else {}))


def original(Fm, c) -> Path:
    """The recording itself: the source's `file`, else the probe's input."""
    s = Fm.SOURCES[c]
    if s.get("file"):
        return Path(s["file"])
    return Path(json.loads((job_dir(s["job"]) / "probe.json").read_text())["input"])


# ---------------------------------------------------------------- words
def words(Fm, c, force=False):
    s = Fm.src(c)
    if (job_dir(s["job"]) / "analysis.json").exists() and not force:
        return
    if not s.get("file"):
        raise SystemExit(f"source {c}: no analysis for job {s['job']} and no `file` to probe")
    sh(["uv", "run", "shorts", "probe", s["file"], "--job", s["job"]] + (["--landscape"] if s["landscape"] else []), cwd=ROOT)
    sh(["uv", "run", "shorts", "analyze", s["job"]] + (["--language", s["language"]] if s.get("language") else []), cwd=ROOT)


# ---------------------------------------------------------------- picture
def picture(Fm, c, force=False):
    want = Fm.SOURCES[c].get("picture")
    if not want:
        return
    out = Fm.work / f"take{c}.mp4"
    if out.exists() and not force:
        return
    src = original(Fm, c)
    trc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer", "-of", "csv=p=0", str(src)],
                         capture_output=True, text=True).stdout.strip().split("\n")[0].strip().rstrip(",")   # an iPhone HLG take prints "arib-std-b67," (side data): who-gonna-hire, 2026-10-23
    tm = Fm.TONEMAP or "mobius"
    vf = ([T.chain(tm)] if trc == "arib-std-b67" else []) + ([f"scale={want[0]}:{want[1]}:flags=lanczos"] if isinstance(want, (list, tuple)) else [])
    vf.append(f"fps={Fm.FPS}")
    sh(["nice", "-n", "10", "ffmpeg", "-v", "error", "-y", "-i", src, "-an", "-vf", ",".join(vf), "-fps_mode", "cfr", "-c:v", "libx264",
        "-crf", str(Fm.PICTURE_CRF), "-preset", "veryfast", "-g", str(Fm.FPS), "-pix_fmt", "yuv420p", *TAGS, "-movflags", "+faststart", out])
    print(f"picture {c} -> {out}" + (f" (HLG tone-mapped: {tm})" if trc == "arib-std-b67" else ""))


# ---------------------------------------------------------------- voice
def channels_differ(p) -> bool:
    """True when the recording has two channels that are not the same signal (WPE needs two real mics)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-t", "120", "-i", str(p), "-map", "0:a:0", "-ac", "2", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2)
    if len(x) < 1600 or np.std(x[:, 0]) < 1e-6 or np.std(x[:, 1]) < 1e-6:
        return False
    return float(np.corrcoef(x[:, 0], x[:, 1])[0, 1]) < 0.999


def voice(Fm, c, force=False):
    o = clean_opts(Fm.SOURCES[c])
    if o is None:
        return
    out = Fm.work / f"voice{c}_df.wav"
    if out.exists() and not force:
        return
    if not DF.exists():
        raise SystemExit(f"no {DF}: DeepFilterNet's venv (./setup.sh)")
    src = original(Fm, c)
    raw = Fm.work / f"voice{c}_raw.wav"
    wpe = bool(o["dereverb"]) and channels_differ(src)
    if o["dereverb"] and not wpe:
        print(f"source {c}: dereverb skipped: its two channels are the same signal (WPE would cancel the voice)")
    af = "aformat=channel_layouts=stereo" if wpe else {"mono": "pan=mono|c0=c0", "right": "pan=mono|c0=c1", "mid": "pan=mono|c0=0.5*c0+0.5*c1"}[o["mic"]]
    af += ",volume=-3dB,adeclip=window=55:overlap=75:arorder=8:threshold=10:hsize=1000" if o["declip"] else ""
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:a:0", "-vn", "-af", af, "-ar", "48000", "-c:a", "pcm_f32le", raw])
    cur = raw
    if wpe:
        if not WPE.exists():
            raise SystemExit(f"no {WPE}: WPE's venv (kit/reel/dereverb.py has the install line)")
        cur = Fm.work / f"voice{c}_wpe.wav"
        sh([WPE, ROOT / "kit/reel/dereverb.py", raw, cur], stdout=subprocess.DEVNULL)
    sh(["nice", "-n", "10", DF, cur, "-o", Fm.work], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (Fm.work / f"{cur.stem}_DeepFilterNet3.wav").rename(out)
    for p in {raw, cur}:
        p.unlink(missing_ok=True)
    print(f"voice {c} -> {out}")


# ---------------------------------------------------------------- the measured EQ
def _load(p, d=120):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-t", str(d), "-i", str(p), "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def spectrum(x):
    """1/3-octave levels of the louder 40 % of 85 ms frames, relative to 1 kHz."""
    n, hop = 4096, 2048
    fr = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    lv = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    P = (np.abs(np.fft.rfft(fr[lv > np.percentile(lv, 60)], axis=1)) ** 2).mean(0)
    f = np.fft.rfftfreq(n, 1 / 48000)
    out = {b: 10 * np.log10(P[(f >= b / 2 ** (1 / 6)) & (f < b * 2 ** (1 / 6))].sum() + 1e-12) for b in BANDS}
    return {b: v - out[1000] for b, v in out.items()}


def curve(meas):
    d = np.clip(np.array([TARGET[b] - meas[b] for b in BANDS]), EQ_LO, EQ_HI)
    sm = d.copy()
    for i in range(1, len(d) - 1):                    # 1-2-1 smoothing: no narrow notch from one band's quirk
        sm[i] = 0.25 * d[i - 1] + 0.5 * d[i] + 0.25 * d[i + 1]
    sm[:3] = np.minimum(sm[:3], 0)                    # never boost the rumble region
    return {str(b): round(float(v), 1) for b, v in zip(BANDS, sm)}


def lufs(p, d=120):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-t", str(d), "-i", str(p), "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(out[out.rindex("I:"):].split()[1])


def eq(Fm, force=False):
    out = Fm.work / "voice_eq.json"
    srcs = [c for c in Fm.SOURCES if (clean_opts(Fm.SOURCES[c]) or {}).get("eq")]
    if not srcs or (out.exists() and not force and all(str(c) in json.loads(out.read_text()) for c in srcs)):
        return
    res = json.loads(out.read_text()) if out.exists() and not force else {}
    for c in srcs:
        p = Fm.work / f"voice{c}_df.wav"
        res[str(c)] = curve(spectrum(_load(p)))
        res[f"gain{c}"] = round(-21.0 - lufs(p), 2)
        print(f"eq {c}: " + " ".join(f"{b}:{res[str(c)][str(b)]:+.1f}" for b in BANDS) + f"  gain {res[f'gain{c}']:+.1f} dB")
    out.write_text(json.dumps(res, indent=1))
    print("->", out)


def measured_chain(Fm, c) -> str | None:
    """The cut's voice chain for a cleaned source with eq: its measured EQ, a static gain to -21 LUFS, a gentle downward
    expander (the leftover floor in pauses down by up to 4 dB, words untouched), a de-esser, gentle compression, -19
    LUFS (films/reverse-engineer edl.py voice_chain)."""
    p = Fm.work / "voice_eq.json"
    if not p.exists():
        return None
    E = json.loads(p.read_text())
    if str(c) not in E:
        return None
    fe = "firequalizer=gain_entry='" + ";".join(f"entry({k},{v})" for k, v in E[str(c)].items()) + "':multi=0:zero_phase=1"
    # v11 films: a de-plosive high-pass after the EQ too (the EQ may lift 63-80 Hz by up to 6 dB after the 70 Hz one)
    dp = f",highpass=f={DEPLOSIVE_HZ},highpass=f={DEPLOSIVE_HZ}" if v11_voice(Fm) else ""
    return (f"volume={E[f'gain{c}']}dB,agate=threshold=0.012:ratio=1.8:attack=4:release=120:knee=3:range=0.63,"
            f"highpass=f=70,{fe}{dp},deesser=i=0.35,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120:makeup=3,"
            "loudnorm=I=-19:TP=-3:LRA=8")


# the de-plosive (2026-10-23, v11-sample draft 1: a plosive on "stop." stood 23 dB over its surroundings below 100 Hz):
# a 4-pole 90 Hz high-pass after the measured EQ (measured on that word: the pop under 60 Hz down 20 dB, 100-160 Hz
# down 3 dB; one 2-pole stage took only 9.5 dB off the pop), and the same on the room tone looped under the pauses
# (kit/film/cut.py room_tone: a low thump in the room candidate was why v11-sample turned ROOM_TONE off). Films made
# from kit/film/mix.py's V11_FROM; an older film's voice re-cuts exactly as before
DEPLOSIVE_HZ = 90


def v11_voice(Fm) -> bool:
    if getattr(Fm, "_v11_voice", None) is None:
        from kit.film.mix import V11_FROM, made_on
        try:
            Fm._v11_voice = made_on(Fm) >= V11_FROM
        except AttributeError:                                     # a config without a dir/work (a test double): v11
            Fm._v11_voice = True
    return Fm._v11_voice


def run(Fm, only=None, force=()):
    Fm.work.mkdir(parents=True, exist_ok=True)
    only = only or STEPS
    for c in Fm.SOURCES:
        for step in ("words", "picture", "voice"):
            if step in only:
                globals()[step](Fm, c, step in force)
    if "eq" in only:
        eq(Fm, "eq" in force)
