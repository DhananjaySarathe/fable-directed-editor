"""Cut edges in real quiet, measured on the voice: never inside a breath or a word (films/ai-workflows, 2026-10-10).

The owner heard the delivered cut: "I'm just about to say something, and you just cut in between". Measured, 28 piece
starts and 23 ends sat inside a sound. Whisper's word times run late, so a 40 ms lead clipped breaths and attacks. A
joint between consecutive words was cut at a valley, often inside a breath, and silence was then inserted there.

    from kit.cut.edges import envelope, speech_threshold, onset, offset, joint
    env = envelope(voice_48k)                      # dB per 10 ms
    thr = speech_threshold(env)                    # the take's speech level (p75) - 24 dB
    sa = min(sa, onset(env, word["start"], prev_word_end + 0.01, thr))        # before the breath / attack
    sb = max(sb, offset(env, word["end"], next_word_start - 0.01, thr))       # once the word stops sounding
    cut = joint(env, last_word, next_word, thr)    # two kept phrases on consecutive words

joint() returns ("quiet", end_of_a, start_of_b): cut out only the quiet between them, and an inserted pause then
replaces quiet. Or it returns ("continuous", t, t): no quiet, so cut at the valley t and insert NO gap.
"""
import numpy as np

SR = 48000
QUIET = 10           # dB under the speech threshold that counts as real silence (before an onset)
END_DROP = 4         # dB under the threshold at which a word has stopped sounding (the room tail below is not waited for)


def envelope(x, sr=SR):
    """RMS level in dB per 10 ms."""
    hop = sr // 100
    n = len(x) // hop
    r = np.sqrt(np.mean(np.square(x[: n * hop].reshape(n, hop)), axis=1) + 1e-12)
    return 20 * np.log10(r)


def speech_threshold(env):
    return float(np.percentile(env[env > -60], 75)) - 24


def quietest(env, a, b, fps=30):
    """The frame time in [a, b] where the voice is quietest and that is a valley (3 dB under the loudest point
    10-80 ms either side), or None."""
    lvl = lambda t0, t1: env[int(round(t0 * 100)):int(round(t1 * 100)) + 1]
    best = None
    for n in range(int(np.ceil(a * fps)), int(np.floor(b * fps)) + 1):
        t = n / fps
        v = float(np.mean(lvl(t - 0.015, t + 0.015)))
        if lvl(t - 0.08, t - 0.01).max() - v >= 3 and lvl(t + 0.01, t + 0.08).max() - v >= 3 and (best is None or v < best[0]):
            best = (v, t)
    return best[1] if best else None


def onset(env, t, lo, thr, lead=0.04):
    """Where a piece starts when the aligner puts its first word at t: 30 ms before the sound really begins (the breath
    and the attack kept). The search walks back from t (up to 0.5 s, never before lo) to 40 ms of real quiet."""
    q, i, i_lo = thr - QUIET, int(t * 100), max(int(np.ceil(lo * 100)), int((t - 0.5) * 100))
    run = 0
    for j in range(min(i + 3, len(env) - 1), i_lo - 1, -1):
        run = run + 1 if env[j] < q else 0
        if run >= 4:
            return max(lo, (j + 4) / 100 - 0.03)
    v = quietest(env, max(lo, t - 0.25), t)
    return v if v is not None else max(lo, t - lead)


def offset(env, t, hi, thr):
    """Where a piece ends when the aligner ends its last word at t: 30 ms after the word stops sounding (END_DROP dB
    under the threshold, within 0.25 s, never after hi)."""
    q, i, i_hi = thr - END_DROP, int(t * 100), min(int(hi * 100), int((t + 0.25) * 100), len(env) - 1)
    run = 0
    for j in range(max(0, i - 3), i_hi + 1):
        run = run + 1 if env[j] < q else 0
        if run >= 4:
            return min(hi, (j - 3) / 100 + 0.03)
    v = quietest(env, t, min(hi, t + 0.25))
    return v if v is not None else min(hi, t + 0.05)


def joint(env, a_word, b_word, thr, fps=30):
    """Two kept phrases on consecutive words (a tag split or a pause trim): words are {start, end} in source seconds."""
    e = offset(env, a_word["end"], b_word["start"] - 0.01, thr)
    s = onset(env, b_word["start"], a_word["end"] + 0.01, thr)
    if s - e >= 0.04:
        sb = float(np.ceil(e * fps - 1e-6) / fps)
        return "quiet", sb, float(max(sb, np.floor(s * fps + 1e-6) / fps))
    q = quietest(env, max(a_word["start"] + 0.04, a_word["end"] - 0.15), min(b_word["end"] - 0.04, b_word["start"] + 0.02), fps)
    if q is None:
        q = float(np.round((a_word["end"] + b_word["start"]) / 2 * fps) / fps)
    return "continuous", q, q


def in_sound(env, t, thr, pad=0.02):
    """True when the voice at t (+- pad) is above the speech threshold: an edge there needs a softer fade."""
    lv = lambda tt: env[max(0, min(len(env) - 1, int(round(tt * 100))))]
    return max(lv(t - pad), lv(t + pad)) > thr


def audit(pieces, envs, thrs):
    """Edges inside a sound, for a quick report: [(out_time, "start"|"end", level_db, word_id)]. A join between two pieces
    of one take that meet exactly (src_b == next src_a) is continuous audio and is skipped."""
    bad = []
    lv = lambda c, t: float(envs[c][max(0, min(len(envs[c]) - 1, int(round(t * 100))))])
    for k, p in enumerate(pieces):
        c = p["clip"]
        jprev = k and pieces[k - 1]["clip"] == c and abs(pieces[k - 1]["src_b"] - p["src_a"]) < 0.02
        jnext = k + 1 < len(pieces) and pieces[k + 1]["clip"] == c and abs(pieces[k + 1]["src_a"] - p["src_b"]) < 0.02
        pre = max(lv(c, p["src_a"] - 0.02), lv(c, p["src_a"] - 0.04))
        post = max(lv(c, p["src_b"] + 0.02), lv(c, p["src_b"] + 0.04))
        if not jprev and pre > thrs[c]:
            bad.append((round(p["out_a"], 2), "start", round(pre), p["w"][0]))
        if not jnext and post > thrs[c]:
            bad.append((round(p["out_b"], 2), "end", round(post), p["w"][1]))
    return bad
