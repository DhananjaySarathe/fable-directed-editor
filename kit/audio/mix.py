"""The film mix: cleaned voice + music beds + the composition's sound cues, mastered to -14 LUFS / -1.5 dBTP.

Generalised from films/ai-workflows/audio.py (2026-10-10). A film's audio.py only lists its beds:

    from kit.audio.mix import Bed, mix
    beds = [Bed(M / "tech/tech__mixkit__electro-dreams.mp3", 0.0, CH1, start=DROP - PR),       # the hook: its drop on PR
            Bed(M / "chill/chill__lakey-inspired__chill.mp3", CH1, CH2, start=35.0), ...]
    mix(F.work / "cut", ED, beds, total=TOTAL)          # reads vo.wav + cues.json there, writes mix.wav

Rules it enforces (each one a finding on a real film):
  - every bed is set relative to the voice: `under` dB under it while he talks (the owner's rule: about -12 on Reels, -18 with a calm bed on long-form films),
    `gap` dB in the pauses; a bed's level comes from its own body loudness, not its file gain;
  - beds crossfade (`xfade` s, default 0.2) where one ends and the next begins: no hole between chapters;
  - scan(): a bed's used range is checked for its own silent gaps (a track's breakdown fell under a line and the mix
    dropped to digital silence). mix() prints them before mixing; choose another `start` when it reports any;
  - a dropout guard: 50 ms windows under -50 dBFS mid-film are printed (single windows inside a gated synth intro
    are the music's rhythm; a run of them is a hole; a run inside a quiet window is printed apart as meant);
  - small UI cues are thinned to the playbook's 6-12 a minute (none within 0.8 s of a kept cue, at most 2 small ones
    in any 10 s); story sounds (hits, whooshes, stamps) and cues marked `keep` (a result landing) always play;
  - a cue's time is when it should be HEARD (2026-10-11): each sound is shifted so its audible attack (UI sounds,
    impacts) or its peak (whooshes) lands on the cue (a riser starts on its cue and builds), measured from the file itself. Unshifted, the library's
    check hit 100 ms late, the bass hit 85 ms and the chapter whoosh peaked 1.07 s after its card. A cue may say
    align: "start" | "onset" | "peak"; mix(..., align=False) is the old placement;
  - quiet moments (kit/hf/evidence.js S.quiet, written to <cues>.quiet.json by cues.mjs): the music steps back
    (default: out, 0.35 s ramps) so a price, a failure or a reaction lands on the voice alone;
  - the measured music-under-speech level is printed (the owner's rule, measured, not assumed);
  - `even` (dB, default 0 = off; 2026-10-18): a slow leveler on the bed (1.5 s windows) lifts the track's own quieter
    passages toward its body level by up to that much, at the same average level. A critic heard the music "18-22 dB
    under" where the track itself dipped while the film sat at -11.8 overall; even=3 keeps it near the rule there.
    Real silences (25 dB under its body: breaks, fades) are left alone; scan() still reports them.
  - `end_fade` (s, default None = 2.5 s; 2026-10-18): the last bed fades out over the film's last 2.5 s (and the whole
    music over its last 1.2 s), right for a film's outro. A Short that ends on its drop sets it on the last bed (~0.4):
    both fades then take that length, so the drop is heard instead of fading under the last word.

v11 (2026-10-22: "holistic, not heavy"; the oss-editor film's beds pumped 7 dB five to eight times a minute and 49 of
its 74 cues were one bubble pop). All of it is opt-in, so every mix made before reproduces sample for sample:
Bed(duck="mask") and mix(sound=None) are the v10 mix; kit/film/mix.py turns v11 on for films made from 2026-10-22.
  - Bed.duck="voice": duck_env() keys the bed on the voice itself: speech = the 10 ms RMS of vo.wav (over a threshold
    between the room and the voice) OR the word mask; 60 ms look-ahead, 40 ms attack, hold 0.4 s, release 0.8 s (Reels
    0.2 / 0.3 s), and the bed lifts only in pauses of 0.8 s or more (Reels 0.4 s): it sits still under the talk and
    breathes in the real pauses. kit/film/mix.py's default gap becomes under + 6 (films -18 / -12, Reels -12 / -6).
    Bed.carve (dB, e.g. 3) dips the bed's 1.2-5 kHz band under speech on the same envelope (the voice's presence band);
  - the mix prints its lifts a minute (pauses where the bed rises 3 dB or more) and the steepest slope (dB/s) of the
    bed's gain, up and down, and the mix's loudness range;
  - Sound.clip_quiet (dB, -19 on v11): the music steps back under every edl piece of kind "clip" (a clip with its own
    audio) by itself, no hand-placed S.quiet;
  - Bed.loop / Bed.segments: a bed whose track runs out plays a section-aware play list (kit/audio/loop.py: jumps
    between matching phrase starts, 80 ms equal-power seams on the downbeat, ending on the track's own ending);
  - Sound.phrase (s, 1.5 on films): a bed change waits for the outgoing bed's own next downbeat (at most a bar after
    the change) and the two cross with an equal-power fade over that window (Bed.xfade overrides it per bed, e.g. 2 s
    into a second long-form bed); decode() pads a negative start with silence instead of clamping it to 0 (the
    v10 clamp played a bed that starts within 0.1 s of its track's head up to 0.1 s early);
  - Sound.rotate: a cue whose file has a family in kit/sfx/library.json ("family") plays the family's 2-3 files in
    turn (the asked file first), each matched to the asked file's body loudness, +-1.5 dB of jitter fixed per cue;
    Sound.per_min caps small cues a minute (long-form 8: the budget is 4-8; Reels 12: 6-12), and no single file
    plays more than Sound.file_share (25 %) of the played cues or Sound.file_per_min (4) times in any minute (only
    small, non-keep cues are dropped for it: story sounds and `keep` cues always play).
"""
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

KIT = Path(__file__).resolve().parents[1]
SR = 48000
SMALL = ("ui__", "whoosh__air-woosh", "whoosh__technology-transition-slide", "typing__")
# duck_env()'s timings per format (s): look-ahead, attack, hold, release, and the shortest pause the bed lifts in
DUCK = {"film": dict(look=0.06, attack=0.04, hold=0.4, release=0.8, pause=0.8),
        "reel": dict(look=0.06, attack=0.04, hold=0.2, release=0.3, pause=0.4)}
CARVE_BAND = (1200.0, 5000.0)    # Hz: the voice's presence band, dipped in the bed under speech (Bed.carve)
SEAM = 0.08                      # s: the equal-power crossfade at each seam of a looped bed (kit/audio/loop.py)
LIFT_DB = 3.0                    # a lift = the bed rising at least this much over its `under` level


@dataclass
class Bed:
    file: Path
    a: float                  # film time it starts (the chapter card)
    b: float                  # film time it ends (the next chapter card)
    start: float = 0.0        # track time at `a`
    gap: float = -5.0         # dB vs the voice in pauses
    under: float = -12.0      # dB vs the voice while he talks
    fade_in: float = 0.3
    fade_out: float = 0.3
    even: float = 0.0         # dB: lift the track's own quiet passages toward its body level (0 = off)
    end_fade: float = None    # s: the last bed's fade at the film's end (None = the film default, 2.5 s)
    allow_silence: tuple = () # track-time (a, b) spans whose silence is meant (the break before a placed drop): not warned
    # ---- v11 (2026-10-22); the defaults are the v10 mix
    duck: str = "mask"        # "mask": the word mask, smoothed (v10) | "voice": duck_env() on vo.wav's RMS or the words
    carve: float = 0.0        # dB: dip the bed's 1.2-5 kHz band this much under speech (duck="voice" only; 3 is plenty)
    loop: bool = False        # the track runs out before b: plan a section-aware play list (kit/audio/loop.py)
    segments: tuple = None    # a ready play list [(track t0, t1)] that starts at a (kit/film/mix.py plans it)
    xfade: float = None       # s: the equal-power crossfade into this bed (Sound.phrase mode; None = Sound.phrase)


@dataclass
class Sound:
    """The mix-wide choices v11 added (2026-10-22). Sound() is the v10 mix exactly; V11 / V11_REEL are the new defaults."""
    fmt: str = "film"              # "film" | "reel": duck_env()'s timings (DUCK)
    rotate: bool = False           # SFX families in turn (kit/sfx/library.json "family"), loudness-matched, +-jitter dB
    jitter: float = 1.5            # dB
    per_min: int = None            # small cues a minute at most (thin(); None = the v10 rules only)
    file_share: float = None       # one file's share of the played cues at most (cap())
    file_per_min: int = None       # one file's plays in any 60 s at most (cap())
    clip_quiet: float = None       # dB: the music under edl pieces of kind "clip" (None = off)
    phrase: float = None           # s: phrase-aware bed changes with an equal-power crossfade this long (None = v10's)
    pad: bool = False              # decode() pads a negative bed start with silence (v10 clamped it to 0)
    lra: float = 11.0              # LU: master()'s loudnorm range; past it loudnorm compresses (a documentary's score, which
                                   # swells on purpose, takes 16: kit/film/mix.py, 2026-10-25)


V11 = Sound(fmt="film", rotate=True, per_min=8, file_share=0.25, file_per_min=4, clip_quiet=-19.0, phrase=1.5, pad=True)
V11_REEL = Sound(fmt="reel", rotate=True, per_min=12, file_share=0.25, file_per_min=4, clip_quiet=-19.0, phrase=None, pad=True)


def decode(p, start=None, dur=None, ch=2, pad=False):
    """`p` from `start` s for `dur` s as float32 (n, ch) at SR. pad=True (v11): a negative start is that much silence
    before the file's head (v10 clamped it to 0, so the audio came early) and a decode that ends early is padded to `dur`."""
    lead = 0.0
    if pad and start is not None and start < 0:
        lead, start, dur = -start, 0.0, (dur + start if dur else dur)
        if dur is not None and dur <= 0:
            return np.zeros((int(round((lead + dur) * SR)) if lead + dur > 0 else 0, ch), np.float32)
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{max(0, start):.4f}"] if start is not None else []) + (["-t", f"{dur:.4f}"] if dur else [])
    raw = subprocess.run(cmd + ["-i", str(p), "-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, ch).copy()
    if pad:
        x = np.concatenate([np.zeros((int(round(lead * SR)), ch), np.float32), x])
        if dur:
            want = int(round((lead + dur) * SR))
            x = np.pad(x, ((0, max(0, want - len(x))), (0, 0)))[:want]
    return x


def db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9)


def level(x, body, most, win=1.5, hop=0.1):
    """Bed.even: lift the passages of x quieter than `body` dB by up to `most` dB (1.5 s RMS windows, smoothed over
    ~1.2 s, so it rides the track's sections, never its beats); windows 25 dB or more under the body stay as they are."""
    h, w = int(hop * SR), int(win * SR)
    if len(x) < w:
        return x
    c = np.arange(0, len(x) - w + 1, h)
    sq = np.concatenate([[0.0], np.cumsum(np.square(x[:, 0].astype(np.float64)))])
    st = 10 * np.log10((sq[c + w] - sq[c]) / w + 1e-12)
    lift = np.where(st < body - 25, 0.0, np.clip(body - st, 0, most))
    k = np.hanning(13); k /= k.sum()
    lift = np.convolve(np.pad(lift, 6, mode="edge"), k, mode="valid")
    g = np.interp(np.arange(len(x)), c + w // 2, lift)
    return x * (10 ** (g / 20))[:, None]


def scan(bed, xfade=0.2, floor=-45.0):
    """Silent 50 ms windows inside the part of the track a bed will play (its fades excluded): [(film_t, track_t)]."""
    dur = bed.b - bed.a + xfade
    x = decode(bed.file, bed.start, dur + 0.1, ch=1)[:, 0]
    w = int(0.05 * SR)
    out = []
    short = dur - len(x) / SR                                       # the track ends before the bed does: the mix pads
    if short > bed.fade_out + 0.05 and not bed.loop and not bed.segments:                     # zeros (a silent tail)
        print(f"WARNING {Path(bed.file).name}: the track runs out at film {bed.a + len(x) / SR:.2f} s (track "
              f"{bed.start + len(x) / SR:.2f} s): {short:.1f} s of silence under the bed's end: loop it (Bed.loop, v11) or add a bed")
    for i in range(int(bed.fade_in * SR), len(x) - w - int(bed.fade_out * SR), w):
        if db(x[i:i + w]) < floor:
            out.append((round(bed.a + i / SR, 2), round(bed.start + i / SR, 2)))
    return out


def is_small(c):
    """A small cue (a UI pop, a soft swish, typing) that thinning may drop; `keep` cues and story sounds never are."""
    return any(s in c.get("asked", c["name"]) for s in SMALL) and not c.get("keep")


def thin(cues, near=0.8, window=10.0, per_window=2, per_min=None):
    """Small cues to the playbook's 6-12 a minute: a small cue is dropped when a kept cue is within `near` s of it or
    `per_window` small ones already played in the last `window` s. Story sounds and `keep` cues always play.
    per_min (v11): also at most that many small cues in any 60 s (the format's budget: 8 on calm long-form, 12 on Reels)."""
    kept = []
    for c in sorted(cues, key=lambda c: c["at"]):
        if is_small(c) and (any(abs(k["at"] - c["at"]) < near for k in kept) or
                            sum(1 for k in kept if is_small(k) and c["at"] - window < k["at"] <= c["at"]) >= per_window or
                            (per_min is not None and sum(1 for k in kept if is_small(k) and c["at"] - 60.0 < k["at"] <= c["at"]) >= per_min)):
            continue
        kept.append(c)
    return kept


def families(sfx_dir=KIT / "sfx") -> dict:
    """{cue name: [the family's cue names, library order]} from kit/sfx/library.json's "family" field (a cue name is the
    file under kit/sfx without .wav, as HF.S gives it: "ui/ui__bubble-pop-up-alert-notification__mixkit-2357")."""
    p = Path(sfx_dir) / "library.json"
    if not p.exists():
        return {}
    fam = {}
    for e in json.load(open(p)):
        if e.get("family"):
            fam.setdefault(e["family"], []).append(e["file"].removeprefix("sfx/").removesuffix(".wav"))
    return {n: m for m in fam.values() for n in m if len(m) > 1}


def _jit(c, most):
    """A fixed pseudo-random gain in [-most, +most] dB for one cue (the same on every run: md5 of its name and time)."""
    h = int(hashlib.md5(f"{c.get('asked', c['name'])}@{c['at']:.3f}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return round((2 * h - 1) * most, 2)


def rotate(cues, fam, jitter=1.5):
    """v11: the k-th cue of a family plays member k mod n (the asked file first, then the others in library order), with
    a fixed jitter of up to +-`jitter` dB. Each cue keeps the asked name in "asked" (its smallness and its loudness
    target); the mix matches every variant to the asked file's body loudness."""
    count, out = {}, []
    for c in sorted(cues, key=lambda c: c["at"]):
        m = fam.get(c["name"])
        c = dict(c, asked=c.get("asked", c["name"]))
        if m:
            key = m[0]
            k = count.get(key, 0)
            count[key] = k + 1
            order = m[m.index(c["asked"]):] + m[: m.index(c["asked"])]
            c["name"] = order[k % len(order)]
            c["jitter_db"] = _jit(c, jitter)
        out.append(c)
    return out


def cap(cues, share=0.25, per_min=4):
    """v11: no single file plays more than `share` of the played cues or more than `per_min` times in any 60 s. Only
    small, non-keep cues are dropped for it (the one closest to its neighbours first); story sounds and keep cues stay.
    The share applies from 8 played cues (3 cues of 10 is not a pattern)."""
    out = sorted(cues, key=lambda c: c["at"])
    if per_min is not None:
        kept = []
        for c in out:
            same = [k for k in kept if k["name"] == c["name"] and c["at"] - 60.0 < k["at"] <= c["at"]]
            if is_small(c) and len(same) >= per_min:
                continue
            kept.append(c)
        out = kept
    while share is not None and len(out) >= 8:
        n = {}
        for c in out:
            n[c["name"]] = n.get(c["name"], 0) + 1
        over = [f for f, k in n.items() if k > share * len(out)]
        drop = [i for i, c in enumerate(out) if c["name"] in over and is_small(c)]
        if not drop:
            break
        gap = lambda i: min([abs(out[i]["at"] - out[j]["at"]) for j in (i - 1, i + 1) if 0 <= j < len(out)] or [1e9])
        del out[min(drop, key=gap)]
    return out


_OFFSETS = {}


def sfx_offset(x, align):
    """Seconds from a sound file's start to the moment that should land on its cue: "onset" = the attack (the first
    5 ms window within 20 dB of the loudest), "peak" = the loudest 5 ms window, "start" = 0."""
    if align == "start":
        return 0.0
    m = x if x.ndim == 1 else x.mean(axis=1)
    w = int(0.005 * SR)
    env = np.sqrt(np.convolve(m * m, np.ones(w) / w, mode="valid")[::w])
    if not len(env) or env.max() <= 0:
        return 0.0
    i = int(np.argmax(env > env.max() * 0.1)) if align == "onset" else int(env.argmax())
    return i * w / SR


def align_of(name, cue=None):
    """How a cue lines up: whooshes by their peak, risers from their start (a riser builds up TO the moment after its
    cue: the caller gives the start of the build), everything else by its attack."""
    if cue and cue.get("align"):
        return cue["align"]
    if any(k in name for k in ("riser", "swell")):
        return "start"
    return "peak" if "whoosh" in name else "onset"


def quiet_env(quiet, total, sr=SR):
    """Gain (linear, per sample) for the music: 1, dipping to `depth` dB inside each quiet window with `ramp` s ramps.
    A window with a positive depth is a swell (the documentary preset's DC.swell, 2026-10-25): the music comes UP that
    many dB over a held beat (an exhibit, an explainer, a chapter card); overlapping quiet windows still win."""
    t = np.arange(int(total * sr)) / sr
    g_db = np.zeros(len(t), np.float32)
    up = np.zeros(len(t), np.float32)
    for q in quiet:
        a, b, d, r = q["a"], q["b"], q.get("depth", -60.0), q.get("ramp", 0.35)
        w = np.clip(np.minimum((t - (a - r)) / r, ((b + r) - t) / r), 0, 1)        # 0 outside, 1 inside, linear ramps
        if d > 0:
            up = np.maximum(up, d * w)
        else:
            g_db = np.minimum(g_db, d * w)
    return (10 ** ((g_db + up) / 20)).astype(np.float32)


def _runs(m):
    """[(i, j)] of the True runs of a bool array (j exclusive)."""
    d = np.diff(np.concatenate([[0], m.astype(np.int8), [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def voice_threshold(lv, vo_db):
    """dBFS a 10 ms frame of vo.wav must pass to count as speech: 12 dB under the voice's level, but at least 6 dB over
    its quietest tenth (the room, a cleaned voice's floor). oss-editor: voice -18.5, words' 10th percentile -30, pause
    centres' median -35.7 -> -30.5."""
    return max(vo_db - 12.0, float(np.percentile(lv, 10)) + 6.0)


def duck_env(vo, words, total, vo_db, fmt="film", rate=100):
    """v11 (Bed.duck="voice"): the duck per 1/rate s, 1 = ducked (the bed at `under`), 0 = lifted (at `gap`).
    Speech = a 10 ms frame of vo.wav over voice_threshold() (runs under 50 ms dropped: clicks) OR inside a word; gaps
    shorter than DUCK[fmt]["pause"] count as speech (the bed never lifts between words); the duck starts `look` s
    before speech and takes `attack` s, holds `hold` s after it and releases over `release` s (linear in dB), and a
    5-frame Hann rounds the corners. -> (env, speech mask)."""
    T = DUCK[fmt]
    n = int(total * rate) + 1
    h = SR // rate
    x = np.pad(vo.astype(np.float64), (0, max(0, n * h - len(vo))))[: n * h]
    lv = 10 * np.log10(np.mean(np.square(x.reshape(n, h)), axis=1) + 1e-12)
    act = lv > voice_threshold(lv, vo_db)
    for i, j in _runs(act):
        if j - i < 5:
            act[i:j] = False
    for w in words:
        act[max(0, int(w["t"] * rate)):int(np.ceil(w["e"] * rate))] = True
    speech = act.copy()
    for i, j in _runs(~act):
        if 0 < i and j < n and (j - i) / rate < T["pause"]:
            speech[i:j] = True
    tgt = np.zeros(n, bool)
    look, hold = int(round(T["look"] * rate)), int(round(T["hold"] * rate))
    for k, (i, j) in enumerate(_runs(speech)):
        # the first words within `pause` of the start: the bed enters under him (no lift before the hook's first word)
        tgt[0 if k == 0 and i < T["pause"] * rate else max(0, i - look):min(n, j + hold)] = True
    up, down = 1 / max(1, T["attack"] * rate), 1 / max(1, T["release"] * rate)
    env = np.zeros(n)
    v = 1.0 if tgt[0] else 0.0
    for k in range(n):
        v = min(1.0, v + up) if tgt[k] else max(0.0, v - down)
        env[k] = v
    k5 = np.hanning(7)[1:-1]
    env = np.convolve(np.pad(env, 2, mode="edge"), k5 / k5.sum(), mode="valid")
    return env, speech


def gain_stats(curves, rate=100):
    """Lifts and slopes of the beds' voice-relative gain (dB per 1/rate s frames, one curve per bed, fades excluded):
    {lifts, lifts_per_min, up_db_s, down_db_s}. A lift = a run where a bed rises LIFT_DB or more over its `under`."""
    lifts, up, down, secs = 0, 0.0, 0.0, 0.0
    for g, under in curves:
        if len(g) < 2:
            continue
        secs += len(g) / rate
        lifts += len(_runs(g >= under + LIFT_DB))
        d = np.diff(g) * rate
        up, down = max(up, float(d.max())), max(down, float(-d.min()))
    return {"lifts": lifts, "lifts_per_min": round(lifts / max(secs / 60, 1e-9), 2), "up_db_s": round(up, 1), "down_db_s": round(down, 1)}


def carve(x, env_s, most_db, band=CARVE_BAND):
    """Bed.carve: x minus a share of its zero-phase 1.2-5 kHz band, so the band dips `most_db` dB where env_s (0..1 per
    sample) is 1 and not at all where it is 0. Zero-phase (forward-backward), so x - band leaves the rest untouched."""
    from scipy.signal import butter, sosfiltfilt
    sos = butter(2, [band[0], band[1]], btype="bandpass", fs=SR, output="sos")
    b = sosfiltfilt(sos, x.astype(np.float64), axis=0)
    return (x - (1 - 10 ** (-most_db / 20)) * b * env_s[:, None]).astype(np.float32)


def clip_windows(edl, depth):
    """Sound.clip_quiet: a quiet window (`depth` dB, 0.35 s ramps) over every run of edl pieces of kind "clip" (a clip
    with its own audio): the music steps back by itself, no hand-placed S.quiet."""
    out = []
    for p in sorted((p for p in edl.get("pieces", []) if p.get("kind") == "clip"), key=lambda p: p["out_a"]):
        if out and p["out_a"] - out[-1]["b"] < 0.5:
            out[-1]["b"] = max(out[-1]["b"], p["out_b"])
        else:
            out.append({"a": p["out_a"], "b": p["out_b"], "depth": depth, "ramp": 0.35})
    return out


def _track_entry(file):
    """The music map entry of a bed's track (kit/music/beats.json), or None (no map, a file outside kit/music)."""
    try:
        from kit.audio import beats as BT
        return BT.entry(file)
    except (ValueError, OSError, KeyError):
        return None


def render(file, a, ra, rb, segs, seam=SEAM):
    """Film span [ra, rb) of a bed whose play list `segs` [(track t0, t1)] starts at film time a. ra < a is the track's
    own lead-in before t0 (silence where that is before the file's head: the v11 decode); each seam is an equal-power
    crossfade `seam` s long centred on it; the last piece runs on past t1 while rb needs it (to the file's end)."""
    out = np.zeros((int(round((rb - ra) * SR)), 2), np.float32)
    F, hs = a, seam / 2
    for k, (t0, t1) in enumerate(segs):
        last = k == len(segs) - 1
        h_in = (a - ra) if k == 0 else hs
        h_out = max(0.0, rb - (F + t1 - t0)) if last else hs
        x = decode(file, t0 - h_in, (t1 - t0) + h_in + h_out, pad=True)
        if k:
            r = int(round(seam * SR))
            x[:r] *= np.sin(np.linspace(0, np.pi / 2, r))[:, None]
        if not last:
            r = int(round(seam * SR))
            x[len(x) - r:] *= np.cos(np.linspace(0, np.pi / 2, r))[:, None]
        i = int(round((F - h_in - ra) * SR))
        j0, j1 = max(0, i), min(len(out), i + len(x))
        if j1 > j0:
            out[j0:j1] += x[j0 - i: j1 - i]
        F += t1 - t0
        if F >= rb:
            break
    return out


def master(pre: Path, out: Path, lufs=-14.0, tp=-1.5, lra=11.0):
    """Two-pass loudnorm (linear) + a 4x-oversampled limiter -> 24-bit WAV. A mix whose range is over `lra` LU makes
    loudnorm leave linear mode and compress it (Sound.lra)."""
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af", f"loudnorm=I={lufs}:TP={tp}:LRA={lra:g}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    lim = 10 ** ((tp - 0.5) / 20)
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA={lra:g}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=192000,alimiter=limit={lim:.3f}:level=false,aresample=48000")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pre), "-af", af, "-c:a", "pcm_s24le", str(out)], check=True)
    return m


def _v10(bd, sound):
    """A bed the v10 code path mixes (sample for sample as before 2026-10-22)."""
    return bd.duck == "mask" and not bd.loop and not bd.segments and sound.phrase is None and not sound.pad and not bd.carve


def _layout(beds, total, xfade, sound):
    """Where each v11 bed plays: [(ra, rb, segs, fade_in(t), fade_out(t))]. Looped beds get their play list here
    (kit/audio/loop.py) unless one was given. With Sound.phrase, a change at T waits for the outgoing bed's own next
    downbeat d (at most a bar after T, through its play list) and both beds cross with equal-power fades over
    [min(T, d - xf), d]: the incoming bed's lead-in plays under the outgoing one and its entry downbeat lands on T."""
    from kit.audio import loop as LP
    lin_in = lambda a, f: (lambda t: np.clip((t - a) / max(f, 1e-3), 0, 1))
    lin_out = lambda b, f: (lambda t: np.clip((b - t) / max(f, 1e-3), 0, 1))
    eq_in = lambda x0, x1: (lambda t: np.sin(np.pi / 2 * np.clip((t - x0) / max(x1 - x0, 1e-3), 0, 1)))
    eq_out = lambda x0, x1: (lambda t: np.cos(np.pi / 2 * np.clip((t - x0) / max(x1 - x0, 1e-3), 0, 1)))
    ents, segs = [], []
    for j, bd in enumerate(beds):
        last = j == len(beds) - 1
        e = _track_entry(bd.file)
        ents.append(e)
        s = [tuple(x) for x in bd.segments] if bd.segments else None
        if s is None and bd.loop and e:                                   # (direct API; kit/film hands its own play lists)
            bar = 240 / e["bpm"]
            need = (bd.b - bd.a) + (0 if last else bar + (sound.phrase or 0) + 0.5)
            # the typed start first; only when no plan fits from it may the last bed start up to 8 bars later
            p = LP.plan(bd.file, e, bd.start, need, end=last, shift=False) or (last and LP.plan(bd.file, e, bd.start, need, end=True))
            if p:
                s = p["segments"]
                print(f"loop {Path(bd.file).name}: {p['how']}; seams at film {', '.join('%.2f' % x for x in LP.seam_times(bd.a, s))} s (listen to each)")
        segs.append(s or [(bd.start, float("inf"))])
    lay = []
    for j, bd in enumerate(beds):
        last = j == len(beds) - 1
        win = None                                                        # the handover window into the next bed (phrase mode)
        if sound.phrase is None:                                          # v10's crossfade (Reels): xfade/2 each side, linear
            ra, rb = max(0.0, bd.a - (xfade / 2 if j else 0)), min(total, bd.b + (0 if last else xfade / 2))
            fin = lin_in(ra, bd.fade_in if j else 0.02)
            fout = lin_out(rb, bd.fade_out if not last else (bd.end_fade if bd.end_fade is not None else 2.5))
        else:
            prev = lay[j - 1][5] if j else None                           # the previous bed hands over to this one
            ra, fin = (prev[0], eq_in(*prev)) if prev else (bd.a, lin_in(bd.a, bd.fade_in if j else 0.02))
            if last:
                rb = min(total, bd.b)
                fout = lin_out(rb, bd.end_fade if bd.end_fade is not None else 2.5)
            else:
                nxt, e = beds[j + 1], ents[j]
                handover = abs(nxt.a - bd.b) <= 0.5                       # a change; else a layer or a gap: each fades alone
                T = nxt.a if handover else bd.b
                xf = (nxt.xfade or sound.phrase) if handover else sound.phrase
                downs = LP.film_downbeats(e, bd.a, segs[j]) if e and e.get("steady") else []
                bar = 240 / e["bpm"] if e else 0.0
                # the window never starts before the incoming bed has music (a track started at its head has no lead-in)
                lead = max(0.0, nxt.segments[0][0] if nxt.segments else nxt.start) if handover else float("inf")
                x0 = lambda d: max(0.0, min(T, d - xf), T - lead) if handover else max(bd.a, d - xf)
                near = [d for d in downs if T - 1e-3 <= d <= T + bar + 0.05 and d - x0(d) >= xf / 2 - 1e-6]
                d = min(near) if near else T + xf / 2                       # no map: a crossfade centred on the change
                w = (x0(d), min(total, d))
                rb, fout = w[1], eq_out(*w)
                win = w if handover else None
        lay.append((ra, rb, segs[j], fin, fout, win))
    out = []
    for j, (ra, rb, s, fin, fout, _) in enumerate(lay):
        if s[-1][1] == float("inf"):
            s = [(s[0][0], s[0][0] + (rb - beds[j].a))]
        out.append((ra, rb, s, fin, fout, ents[j]))
    return out


def mix(work: Path, edl: dict, beds, total: float, out_name="mix.wav", xfade=0.2, sfx_dir=KIT / "sfx", cues_name="cues.json", align=True,
        sound: Sound = None, quiet_extra=(), cues_extra=()):
    """work/vo.wav + beds + work/cues.json -> work/mix.wav. edl: the film's edl.json (words with t/e, talk_end).
    sound: the v11 choices (Sound; None = the v10 mix). quiet_extra: more quiet windows (a planned 'stop');
    cues_extra: more cues (a planned riser). -> {under_db, dropouts, cues, lifts..., sfx...}"""
    sound = sound or Sound()
    n = int(total * SR)
    vo = decode(work / "vo.wav", ch=1)[:n, 0]
    vo = np.pad(vo, (0, max(0, n - len(vo))))
    vo_db = db(vo[np.abs(vo) > 1e-3])
    rate = 100
    tt = np.arange(int(total * rate) + 1) / rate
    sp = np.zeros(len(tt))                                              # 1 while he talks (words padded), smoothed
    for w in edl["words"]:
        sp[int((w["t"] - 0.12) * rate):int((w["e"] + 0.2) * rate)] = 1
    k = np.hanning(31); k /= k.sum()
    sp = np.clip(np.convolve(sp, k, mode="same") * 1.6, 0, 1)
    beds = sorted(beds, key=lambda b: b.a)
    music = np.zeros((n, 2), np.float32)
    old = [_v10(bd, sound) for bd in beds]
    env_v = duck_env(vo, edl["words"], total, vo_db, sound.fmt, rate)[0] if any(bd.duck == "voice" for bd in beds) else None
    lay = _layout(beds, total, xfade, sound) if not all(old) else None
    curves = []                                                          # (the bed's voice-relative gain at 100 Hz, its under)
    for j, bd in enumerate(beds):
        last = j == len(beds) - 1
        if not old[j]:                                                   # v11: voice duck, loops, phrase-aware changes
            ra, rb, segs, fin, fout, e = lay[j]
            x = render(bd.file, bd.a, ra, rb, segs)
            dur = rb - ra
            if e and len(segs) == 1 and segs[0][0] + (rb - bd.a) > e["duration"] + 0.5:
                print(f"WARNING {Path(bd.file).name}: the track runs out at film {bd.a + e['duration'] - segs[0][0]:.2f} s: "
                      f"{segs[0][0] + (rb - bd.a) - e['duration']:.1f} s of silence under the bed's end: loop=True or another bed")
            body = db(x[int(min(2, dur / 3) * SR):])
            if bd.even > 0:
                x = level(x, body, bd.even)
                body = db(x[int(min(2, dur / 3) * SR):])
            t = ra + np.arange(len(x)) / SR
            dk = np.interp(t, tt, env_v if bd.duck == "voice" else sp)
            if bd.carve > 0 and bd.duck == "voice":
                x = carve(x, dk, bd.carve)
            g = vo_db + (bd.gap + (bd.under - bd.gap) * dk) - body
            env = fin(t) * fout(t)
            w = int(0.05 * SR)                                           # the track's own silences inside its full-level part
            full = np.where(env >= 0.999)[0]
            if len(full):
                lv = [(ra + i / SR, db(x[i:i + w])) for i in range(full[0], full[-1] - w, w)]
                quiet = [round(tq, 2) for tq, lq in lv if lq < -45.0 and not (len(segs) == 1 and any(
                    p <= segs[0][0] + (tq - bd.a) <= q for p, q in bd.allow_silence))]
                if quiet:
                    print(f"WARNING {Path(bd.file).name}: the track is silent at film {quiet[0]} s and {len(quiet) - 1} more: pick another start")
            seg = x * (10 ** (g / 20) * env)[:, None]
            i = int(round(ra * SR))
            e2 = min(n, i + len(seg))
            music[i:e2] += seg[: e2 - i]
            m = (tt >= ra) & (tt <= rb) & (fin(tt) * fout(tt) >= 0.999)
            sel = env_v if bd.duck == "voice" else sp
            curves.append((bd.gap + (bd.under - bd.gap) * sel[m], bd.under))
            continue
        m = (tt >= bd.a) & (tt <= bd.b)                                  # (stats only: the v10 path below is unchanged)
        curves.append((bd.gap + (bd.under - bd.gap) * sp[m], bd.under))
        a = max(0.0, bd.a - (xfade / 2 if j else 0))                     # crossfade: the next bed starts before this one ends
                                                                         # (never before 0: a second layer from 0, e.g. a game's
                                                                         # own sound under the music, went to a negative index)
        b = min(total, bd.b + (0 if last else xfade / 2))
        holes = scan(Bed(bd.file, a, b, bd.start - (bd.a - a), bd.gap, bd.under, bd.fade_in, bd.fade_out), 0)
        holes = [h for h in holes if not any(x <= h[1] <= y for x, y in bd.allow_silence)]
        if holes:
            print(f"WARNING {bd.file.name}: the track is silent at film {holes[0][0]} s (track {holes[0][1]} s) and {len(holes) - 1} more: pick another start")
        dur = b - a
        x = decode(bd.file, bd.start - (bd.a - a), dur + 0.5)[: int(dur * SR)]
        x = np.pad(x, ((0, int(dur * SR) - len(x)), (0, 0)))
        body = db(x[int(min(2, dur / 3) * SR):])
        if bd.even > 0:
            x = level(x, body, bd.even)
            body = db(x[int(min(2, dur / 3) * SR):])
        t = a + np.arange(len(x)) / SR
        g = vo_db + (bd.gap + (bd.under - bd.gap) * np.interp(t, tt, sp)) - body
        fi, fo = (bd.fade_in if j else 0.02), (bd.fade_out if not last else (bd.end_fade if bd.end_fade is not None else 2.5))
        env = np.clip((t - a) / max(fi, 1e-3), 0, 1) * np.clip((b - t) / max(fo, 1e-3), 0, 1)
        i = int(a * SR)
        seg = x * (10 ** (g / 20) * env)[:, None]
        e = min(n, i + len(seg))
        music[i:e] += seg[: e - i]
    tq = np.arange(n) / SR
    tail = beds[-1].end_fade if beds and beds[-1].end_fade is not None else 1.2
    music *= np.clip((total - 0.05 - tq) / max(tail, 1e-3), 0, 1)[:, None]
    quiet_p = work / cues_name.replace(".json", ".quiet.json")
    quiet = json.load(open(quiet_p)) if quiet_p.exists() else []
    if sound.clip_quiet is not None:                                    # v11: the music steps back under clips by itself
        quiet = quiet + clip_windows(edl, sound.clip_quiet)
    quiet = quiet + list(quiet_extra)
    if quiet:
        music *= quiet_env(quiet, total)[:n, None]
        spans = ", ".join("%.1f-%.1f" % (q["a"], q["b"]) for q in quiet if q.get("depth", -60.0) <= 0)
        ups = ", ".join("%.1f-%.1f +%g" % (q["a"], q["b"], q["depth"]) for q in quiet if q.get("depth", -60.0) > 0)
        print(f"quiet: music steps back at {spans or 'nothing'}" + (f"; swells (music up, dB) at {ups}" if ups else ""))
    sfx = np.zeros((n, 2), np.float32)
    cues_p = work / cues_name
    raw = (json.load(open(cues_p)) if cues_p.exists() else []) + list(cues_extra)
    if sound.rotate or sound.per_min is not None or sound.file_share is not None or sound.file_per_min is not None:
        cues = thin(raw, per_min=sound.per_min)                         # v11: the format's budget, families, per-file caps
        cues = cap(rotate(cues, families(sfx_dir), sound.jitter) if sound.rotate else cues, sound.file_share, sound.file_per_min)
    else:
        cues = thin(raw)
    print(f"cues: {len(raw)} asked, {len(cues)} played ({len(cues) / (total / 60):.1f} a minute)")
    cache, seen, shifts, played, bodies = {}, set(), [], [], {}

    def body_of(name):                                                   # a sound's body loudness (dB): RMS of its 5 ms
        if name not in bodies:                                           # envelope where it is within 20 dB of its peak
            m = cache[name].mean(axis=1)
            w = int(0.005 * SR)
            env = np.sqrt(np.convolve(m * m, np.ones(w) / w, mode="valid")[::w] + 1e-12)
            bodies[name] = 20 * np.log10(np.sqrt(np.mean(np.square(env[env > env.max() * 0.1]))) + 1e-9)
        return bodies[name]
    for c in cues:
        key = (c["name"], round(c["at"], 2))
        if key in seen:
            continue
        seen.add(key)
        for nm in {c["name"], c.get("asked", c["name"])}:
            if nm not in cache:
                x = decode(sfx_dir / f"{nm}.wav")
                cache[nm] = x / (np.abs(x).max() + 1e-9) * 10 ** (-3 / 20)
        if "asked" in c:                                                 # v11: a variant at the asked file's loudness, +-jitter
            match = float(np.clip(body_of(c["asked"]) - body_of(c["name"]), -6, 6)) if c["asked"] != c["name"] else 0.0
            x = cache[c["name"]] * 10 ** ((c["gain_db"] + match + c.get("jitter_db", 0.0)) / 20)
        else:
            x = cache[c["name"]] * 10 ** (c["gain_db"] / 20)
        if c.get("dur"):                                                 # a cue cut to length (typing that stops with
            k = min(len(x), int(c["dur"] * SR))                          # its text), a 60 ms fade at the cut
            f = min(k, int(0.06 * SR))
            x = x[:k].copy()
            x[k - f:] *= np.linspace(1, 0, f)[:, None]
        played.append(c)
        mode = align_of(c["name"], c) if align else "start"
        key2 = (c["name"], mode)
        if key2 not in _OFFSETS:
            _OFFSETS[key2] = sfx_offset(cache[c["name"]], mode)
        off = _OFFSETS[key2]
        shifts.append(off)
        i = int(round((c["at"] - off) * SR))
        if i < 0:                                                    # the sound would start before 0: drop its head
            x, i = x[-i:], 0
        e = min(n, i + len(x))
        if i < n:
            sfx[i:e] += x[: e - i]
    if shifts:
        print(f"sfx aligned ({'attack/peak on the cue' if align else 'file start on the cue'}): shifts {min(shifts) * 1000:.0f}-{max(shifts) * 1000:.0f} ms, median {np.median(shifts) * 1000:.0f} ms")
    mixed = vo[:, None] + music + sfx
    fr = int(0.05 * SR)
    holes = [round(i / SR, 2) for i in range(SR, int(edl["talk_end"] * SR) - fr, fr) if db(mixed[i:i + fr, 0]) < -50]
    runs = [h for h in holes if any(abs(h - g - 0.05) < 1e-6 for g in holes)]
    # a run inside a quiet window (the page's S.quiet, a plan's 'stop', a clip) is the music taken out on purpose over a
    # cleaned voice's silent breath: reported apart, not as a hole to fix (kit-v10-sample's planned stop at 28.7 s, v11)
    inq = lambda h: any(q["a"] - q.get("ramp", 0.35) <= h and h + 0.05 <= q["b"] + q.get("ramp", 0.35)
                        and q.get("depth", -60.0) <= -20.0 for q in quiet)
    meant = [h for h in runs if inq(h)]
    runs = [h for h in runs if not inq(h)]
    print(f"dropouts (50 ms below -50 dBFS): {holes if holes else 'none'}{'  RUNS (holes, fix them): ' + str(runs) if runs else ''}"
          f"{'  in quiet windows (meant; ROOM_TONE gives them air): ' + str(meant) if meant else ''}")
    pre = work / "mix_pre.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a", "pcm_s24le", str(pre)],
                   input=mixed.astype(np.float32).tobytes(), check=True)
    m = master(pre, work / out_name, lra=sound.lra)
    pre.unlink()
    on = np.array([sp[min(len(sp) - 1, int(i / SR * rate))] > 0.9 for i in range(0, n - fr, fr)])
    v = np.array([db(vo[i:i + fr]) for i in range(0, n - fr, fr)]); mu = np.array([db(music[i:i + fr, 0]) for i in range(0, n - fr, fr)])
    under = float(np.median(mu[on]) - np.median(v[on])) if on.any() else float("nan")
    print(f"voice {vo_db:.1f} dBFS; music under speech: {under:.1f} dB vs the voice; {len(seen)} sfx -> {work / out_name}")
    # what v11 measures on every mix (the same numbers for a v10 one, to compare): the bed's lifts and slopes, the
    # sound budget (cues a minute, the most-played file's share) and the loudness range
    st = gain_stats(curves, rate)
    mins = total / 60
    files = {}
    for c in played:
        files[c["name"]] = files.get(c["name"], 0) + 1
    top = max(files.items(), key=lambda kv: kv[1]) if files else ("", 0)
    small = sum(1 for c in played if is_small(c))
    sfx_st = {"sfx_per_min": round(len(played) / mins, 1), "small_per_min": round(small / mins, 1), "top_file": top[0],
              "top_share": round(top[1] / max(1, len(played)), 3), "variants": len(files)}
    print(f"bed: {st['lifts']} lifts of {LIFT_DB:g} dB or more ({st['lifts_per_min']} a minute), steepest slope +{st['up_db_s']} dB/s "
          f"up, -{st['down_db_s']} dB/s down; sfx {sfx_st['sfx_per_min']} a minute ({sfx_st['small_per_min']} small), "
          f"{len(files)} files, the most played {top[0].split('/')[-1]} {100 * sfx_st['top_share']:.0f} %; "
          f"loudness range {float(m['input_lra']):.1f} LU")
    return {"under_db": under, "dropouts": holes, "cues": len(cues), **st, **sfx_st, "lra": float(m["input_lra"])}
