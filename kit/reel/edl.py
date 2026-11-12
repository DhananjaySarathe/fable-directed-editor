"""The cut: KEEP (whole sentences, by word id) -> edl.json + cuts.json (in the film folder), vo.wav, aroll.mp4,
aroll.track.json, aroll.map.json (in its work folder). Generic version of the films' edl.py (2026-10-10).

  - gated by kit.cut.cutcheck before any media work (FAIL stops; REVIEW must be listed in JUDGED with the reason)
  - word times come from the take's analysis.json, with START_FIX / END_FIX (measured on the voice envelope by
    `kit.reel joins`) applied first
  - edges padded by how the word sounds at its end (vowel +30 ms, sibilant +120 ms, other +50 ms), 40 ms lead-in
    (100 ms before a hiss); never into the neighbouring word
  - inside a kept range a pause longer than MAX_GAP becomes a SLIVER (kept natural, never glued); a word in TRIM is cut
    from the word before it even with sound in the gap (END_FIX / START_FIX give the edges)
  - two consecutive pieces whose words run together are cut at the quietest valley between them (no pause added)
  - 25 ms half-sine fades on every splice; the voice is cut ONCE from the cleaned source
"""
import json
import subprocess
import sys

import numpy as np

VOICE_CLEAN = ("highpass=f=80,"
               "equalizer=f=220:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=2.5,equalizer=f=9000:t=h:w=1:g=1.5,"
               "acompressor=threshold=-26dB:ratio=3:attack=6:release=110:makeup=4,loudnorm=I=-19:TP=-3:LRA=7")


def lead_pad(R, text):
    w = text.lower().strip(".,?!'\"“”")
    return R.SIB_LEAD if w.startswith(("s", "sh", "z", "f", "th", "ch", "c", "h")) else R.LEAD    # h: a breathy onset


def tail_pad(text):
    w = text.lower().strip(".,?!'\"…")
    if w.endswith(("s", "sh", "z", "ch", "x", "ce", "se", "%")):
        return 0.12
    if w and w[-1] in "aeiouy":
        return 0.03
    return 0.05


def voice(R, clean=True):
    af = VOICE_CLEAN if clean else "anull"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(R.work / "voice_df.wav"), "-vn", "-af", af,
                          "-ac", "1", "-ar", str(R.SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def envelope(x, sr):
    hop = sr // 100
    n = len(x) // hop
    return 20 * np.log10(np.sqrt(np.mean(np.square(x[: n * hop].reshape(n, hop)), axis=1) + 1e-12))


def quiet_gap(env, a, b, thr):
    """True when the voice between a and b (s) is a real pause: no 80 ms run above `thr` dB (60 ms margins)."""
    i0, i1 = int((a + 0.06) * 100), int((b - 0.06) * 100)
    if i1 <= i0:
        return True
    run = best = 0
    for v in env[i0:i1] > thr:
        run = run + 1 if v else 0
        best = max(best, run)
    return best < 8


def quietest(env, a, b, fps):
    """The frame time in [a, b] where the voice is quietest and is a valley (3 dB under the loudest point 10-80 ms
    either side). None when there is none."""
    lvl = lambda t0, t1: env[int(round(t0 * 100)):int(round(t1 * 100)) + 1]
    best = None
    for n in range(int(np.ceil(a * fps)), int(np.floor(b * fps)) + 1):
        t = n / fps
        v = float(np.mean(lvl(t - 0.015, t + 0.015)))
        if lvl(t - 0.08, t - 0.01).max() - v >= 3 and lvl(t + 0.01, t + 0.08).max() - v >= 3 and (best is None or v < best[0]):
            best = (v, t)
    return best[1] if best else None


QUIET = 10        # dB under the speech threshold (speech - 24) that counts as real silence


def onset(env, t, lo, thr):
    """Where a piece starts when the aligner puts its first word at t: just before the sound really begins, its breath
    and attack kept (from films/ai-workflows/edl.py, 2026-10-10: the owner heard clipped onsets as voice cuts). Searches
    back up to 0.5 s for 40 ms of real quiet; falls back to the quietest valley just before the word."""
    q, i, i_lo = thr - QUIET, int(t * 100), max(int(np.ceil(lo * 100)), int((t - 0.5) * 100))
    run = 0
    for j in range(min(i + 3, len(env) - 1), i_lo - 1, -1):
        run = run + 1 if env[j] < q else 0
        if run >= 4:
            return max(lo, (j + 4) / 100 - 0.03), True
    v = valley(env, max(lo, t - 0.25), t + 0.02, last=False)
    return (v if v is not None else max(lo, t - 0.04)), False


def offset(env, t, hi, thr):
    """Where a piece ends when the aligner ends its last word at t: once the word stops sounding (4 dB under the speech
    threshold, 30 ms into the quiet); without quiet (he talks on into a dropped word), the last valley before t."""
    q, i, i_hi = thr - 4, int(t * 100), min(int(hi * 100), int((t + 0.25) * 100), len(env) - 1)
    run = 0
    for j in range(max(0, i - 3), i_hi + 1):
        run = run + 1 if env[j] < q else 0
        if run >= 4:
            return min(hi, (j - 3) / 100 + 0.03), True
    v = valley(env, t - 0.3, min(hi, t + 0.05), last=True)
    return (v if v is not None else min(hi, t + 0.05)), False


def valley(env, a, b, last=True):
    """A valley in [a, b] (3 dB under the loudest point 10-80 ms either side): the latest one (last) or the deepest."""
    lvl = lambda t0, t1: env[max(0, int(round(t0 * 100))):int(round(t1 * 100)) + 1]
    best = None
    for n in range(int(np.floor(b * 100)), int(np.ceil(a * 100)) - 1, -1):
        t = n / 100
        L0, L1, M = lvl(t - 0.08, t - 0.01), lvl(t + 0.01, t + 0.08), lvl(t - 0.015, t + 0.015)
        if not (len(L0) and len(L1) and len(M)):
            continue
        v = float(np.mean(M))
        if L0.max() - v >= 3 and L1.max() - v >= 3:
            if last:
                return t
            if best is None or v < best[0]:
                best = (v, t)
    return best[1] if best else None


def words(R):
    """The take's words with the film's START_FIX / END_FIX applied."""
    W = R.words()
    for i, v in R.START_FIX.items():
        W[i]["start"] = v
    for i, v in R.END_FIX.items():
        W[i]["end"] = v
    return W


def gate(R, force=False):
    """kit.cut.cutcheck on the KEEP list: FAIL stops the build; REVIEW must be in JUDGED."""
    from kit.cut import cutcheck
    from kit.cut.common import IdMap
    ids = IdMap.parse(f"{R.TAKE}=0")
    res = cutcheck.check(cutcheck.words_from_ranges([(a, b) for a, b, *_ in R.KEEP], ids), ids, do_relisten=False, log=lambda *a, **k: None)
    bad = [j for j in res["joins"] if j["verdict"] == "FAIL" and (j["left_id"], j["right_id"]) not in R.JUDGED]
    rev = [j for j in res["joins"] if j["verdict"] == "REVIEW" and (j["left_id"], j["right_id"]) not in R.JUDGED]
    print(f"cutcheck: {res['verdict']} ({len(bad)} FAIL, {len(rev)} unjudged REVIEW)")
    for j in res["joins"]:
        if j["verdict"] != "PASS" or j.get("kind") != "continuous":
            print("  ", j["verdict"], j.get("kind"), j["left_id"], "->", j["right_id"], j.get("why", ""), "|", j.get("left"), "||", j.get("right"))
    (R.work / "cutcheck_plan.json").write_text(json.dumps(res, indent=1, default=str))
    if (bad or rev) and not force:
        raise SystemExit(3)


def plan(R):
    """KEEP -> pieces on the Reel's timeline and the words' output times (no media written)."""
    FPS, SPEED = R.FPS, R.SPEED
    Wd = words(R)
    env = envelope(voice(R, clean=False), R.SR)
    thr = float(np.percentile(env[env > -60], 75)) - 24
    segs = []
    for k in R.KEEP:
        a, b, tag = k[:3]
        run = [Wd[a]]
        for w in Wd[a + 1:b + 1]:
            g0, g1 = run[-1]["end"], w["start"]
            forced = w["i"] in R.TRIM                        # a hum / drawl / fragment the owner wants out (edges measured by hand)
            if (g1 - g0 > R.MAX_GAP or forced) and w["i"] not in R.NOTRIM and (forced or quiet_gap(env, g0, g1, thr) or w["i"] in R.SLIVER_AT):
                segs.append((run, tag, R.SLIVER_AT.get(w["i"], R.SLIVER)))
                run = []
            run.append(w)
        segs.append((run, tag, R.GAP_AFTER.get(b, R.GAP)))
    pieces, out_words, t, joint = [], [], 0.0, {}
    for k, (run, tag, after) in enumerate(segs):
        t = float(np.round(t * FPS) / FPS)
        i0, i1 = run[0]["i"], run[-1]["i"]
        lo = Wd[i0 - 1]["end"] + 0.02 if i0 > 0 else 0.0
        hi = Wd[i1 + 1]["start"] - 0.02 if i1 + 1 < len(Wd) else 1e9
        # edges in real quiet on the voice envelope (breath and attack kept, the word allowed to finish); a START_FIX /
        # END_FIX (measured by hand) wins over the search
        if i0 in R.START_FIX:
            sa = max(0.0, run[0]["start"] - lead_pad(R, run[0]["text"]))
        else:
            sa = onset(env, run[0]["start"], max(lo, 0.0), thr)[0]
        if i1 in R.END_FIX:
            sb = run[-1]["end"] + tail_pad(run[-1]["text"])
        else:
            sb = offset(env, run[-1]["end"], min(hi, 1e9), thr)[0]
        nxt = segs[k + 1] if k + 1 < len(segs) else None
        fo, cont = 0.025, False
        # the voice is cut at the exact measured edges (va, vb); the picture on the frame grid (sa, sb)
        va, vb = max(sa, lo), min(sb, hi)
        sa, sb = np.floor(sa * FPS + 1e-6) / FPS, np.round(sb * FPS) / FPS
        if sa < lo:
            sa = np.ceil(lo * FPS) / FPS
        if sb > hi:
            sb = np.floor(hi * FPS) / FPS
        if nxt and nxt[0][0]["i"] == i1 + 1:
            nw = nxt[0][0]
            if nw["start"] - lead_pad(R, nw["text"]) <= run[-1]["end"] + tail_pad(run[-1]["text"]):
                a = max(run[-1]["start"] + 0.04, run[-1]["end"] - 0.15)
                b = min(nw["end"] - 0.04, nw["start"] + 0.02)
                q = quietest(env, a, b, FPS)
                if q is None:
                    print(f"  ! no quiet point between {run[-1]['text']!r} and {nw['text']!r} ({a:.2f}-{b:.2f} s): cut at the boundary")
                    q = float(np.round((run[-1]["end"] + nw["start"]) / 2 * FPS) / FPS)
                sb = joint[i1 + 1] = q
                vb = q
                fo, cont = 0.04, True
        fi = 0.015 if i0 in joint else 0.025
        if i0 in joint:
            sa = va = joint[i0]
        va = max(va, sa)
        dur = (sb - sa) / SPEED
        pieces.append({"kind": "face", "clip": 1, "tag": tag, "src_a": round(float(sa), 4), "src_b": round(float(sb), 4),
                       "speed": SPEED, "out_a": round(t, 4), "out_b": round(t + dur, 4), "fi": fi, "fo": fo,
                       "va": round(float(va), 4), "vb": round(float(vb), 4),
                       "w": [i0, i1], "after": 0.0 if cont else round(after / SPEED, 4)})
        for w in run:
            out_words.append({"i": w["i"], "text": w["text"], "tag": tag,
                              "t": round(t + (w["start"] - sa) / SPEED, 3), "e": round(t + (w["end"] - sa) / SPEED, 3)})
        t += dur + (0.0 if cont else after / SPEED)
    talk_end = pieces[-1]["out_b"]
    total = round(np.round((talk_end + R.TAIL) * FPS) / FPS, 4)
    return {"total": total, "talk_end": round(talk_end, 3), "speed": SPEED, "pieces": pieces, "words": out_words}


def write_voice(R, edl, src=None):
    SR = R.SR
    vo_src = voice(R) if src is None else src
    n = int(edl["total"] * SR)
    vo = np.zeros(n, np.float32)
    for p in edl["pieces"]:
        va, vb = p.get("va", p["src_a"]), p.get("vb", p["src_b"])
        x = vo_src[int(va * SR):int(vb * SR)]
        af = f"afade=t=in:d={p['fi']}:curve=hsin,areverse,afade=t=in:d={p['fo']}:curve=hsin,areverse"
        if R.VOICE_GAIN.get(p["tag"]):                   # a quieter voice in the take (someone off camera), lifted
            af = f"volume={R.VOICE_GAIN[p['tag']]}dB," + af
        if p["speed"] != 1.0:
            af = f"atempo={p['speed']}," + af
        raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", af,
                              "-f", "f32le", "-"], input=x.tobytes(), capture_output=True, check=True).stdout
        y = np.frombuffer(raw, np.float32)
        i = int(round((p["out_a"] + (va - p["src_a"]) / p["speed"]) * SR))
        vo[i:i + len(y)] += y[: max(0, n - i)]
    if R.ROOM_TONE is not None:
        vo += room_tone(R, edl, vo, n)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s24le",
                    str(R.work / "vo.wav")], input=vo.tobytes(), check=True)


def room_tone(R, edl, vo, n):
    """ROOM_TONE (dB vs the room's natural level): the cleaned voice has no room left in it, so every pause was digital
    silence (a hole, not a beat). The take's quietest 0.8 s with no word in it (raw audio, not the cleaned voice) is looped
    under the whole Reel, set where it sat under his voice in the take. -> n samples"""
    SR, fr = R.SR, R.SR // 20
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(R.source), "-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    env = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) + 1e-9 for i in range(0, len(x) - fr, fr)])
    talk = np.zeros(len(env), bool)
    for w in R.words():
        talk[max(0, int((w["start"] - 0.25) * 20)):int((w["end"] + 0.35) * 20)] = True
    k = 16                                           # 0.8 s
    best = min((float(np.median(env[j:j + k])), j) for j in range(len(env) - k) if not talk[j:j + k].any() and env[j:j + k].min() > 1e-5)[1]
    seg = x[best * fr:(best + k) * fr].astype(np.float32)
    xf = fr                                          # loop it with 50 ms crossfades
    ramp = np.linspace(0, 1, xf, dtype=np.float32)
    out = np.zeros(n + len(seg), np.float32)
    pos = 0
    while pos < n:
        piece = seg.copy()
        piece[:xf] *= ramp
        piece[-xf:] *= ramp[::-1]
        out[pos:pos + len(piece)] += piece
        pos += len(piece) - xf
    speech = np.concatenate([x[int(w["start"] * SR):int(w["end"] * SR)] for w in R.words()])
    said = np.concatenate([vo[int(w["t"] * SR):int(w["e"] * SR)] for w in edl["words"]])
    g = 20 * np.log10((np.sqrt(np.mean(said ** 2)) + 1e-9) / (np.sqrt(np.mean(speech ** 2)) + 1e-9)) + R.ROOM_TONE
    print(f"room tone: take {best * 0.05:.2f}-{(best + k) * 0.05:.2f} s, {20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9):.1f} dB raw, set {g:+.1f} dB")
    return out[:n] * 10 ** (g / 20)


def graded_take(R):
    """The picture the Reel's aroll is cut from: work/take_graded.mp4 while it is a complete grade of work/take.mp4 made
    with reel.py's grade settings as they are now (kit/look/ffio.py status, the check prep's grade step makes), else
    the ungraded take with a NOTE (2026-10-22, v11 fix Pi-S2: a stale or partial grade must not reach a Reel, as
    kit/film's track_file guards a film: ai-video-editor's grade stopped 220 frames short and its last ~7 s froze).
    No graded take and no unfinished one: prep has not graded, so stop as before."""
    from kit.look import ffio as FF
    from kit.reel.prep import grade_cmd
    take, graded = R.work / "take.mp4", R.work / "take_graded.mp4"
    if not graded.exists() and not FF.part(graded).exists():
        raise SystemExit(f"missing {graded}: run prep")
    cmd, v2set = grade_cmd(R)
    ok, why = FF.status(take, graded, want=FF.settings(cmd[2:], v2set))
    if ok:
        return graded
    if not take.exists():
        raise SystemExit(f"{why}; and no {take} to fall back on: run prep")
    print(f"NOTE: {why}: aroll.mp4 is cut from the UNGRADED {take.name}. Run prep (its grade step re-grades), then cut again")
    return take


def write_picture(R, edl):
    """Each output frame takes its piece's source frame (in a pause after a piece the take keeps playing; after the
    last word too, under the tail)."""
    FPS, W1, H1 = R.FPS, R.W, R.H
    pieces, total = edl["pieces"], edl["total"]
    track = json.load(open(R.work / "take.face.json"))
    for p in pieces:
        fs = track[int(p["src_a"] * FPS):max(int(p["src_a"] * FPS) + 1, int(p["src_b"] * FPS))]
        p["face"] = [round(float(np.median([f[i] for f in fs])), 1) for i in range(3)]
    nout = int(round(total * FPS))
    need, face = [], []
    for k in range(nout):
        tt = (k + 0.5) / FPS
        p = next((q for q in pieces if q["out_a"] <= tt < q["out_b"]), None) or max((q for q in pieces if q["out_b"] <= tt), key=lambda q: q["out_b"])
        f = min(int((p["src_a"] + (tt - p["out_a"]) * p["speed"]) * FPS), len(track) - 1)
        need.append(f)
        x, y, w = track[f]
        face.append([round(x, 1), round(y, 1), round(w, 1)])
    for k in range(min(R.OPEN_HOLD, len(need) - 1)):    # frame 1 on a blink: the first open-eyed frame held over it
        need[k], face[k] = need[R.OPEN_HOLD], face[R.OPEN_HOLD]
    (R.work / "aroll.track.json").write_text(json.dumps(face))
    (R.work / "aroll.map.json").write_text(json.dumps(need))
    clip, out = graded_take(R), R.work / "aroll.mp4"
    tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W1}x{H1}", "-r", str(FPS), *tags,
                            "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-g", "15", "-pix_fmt", "yuv420p", *tags,
                            "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    fb = W1 * H1 * 3
    f0, f1 = min(need), max(need)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{(f0 - 0.5) / FPS:.5f}", "-i", str(clip), "-frames:v", str(f1 - f0 + 1), "-an",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    frames, last_use = {}, {}
    for k, f in enumerate(need):
        last_use[f] = k
    cur = f0 - 1
    for k, f in enumerate(need):
        while cur < f:
            buf = dec.stdout.read(fb)
            if len(buf) < fb:
                raise SystemExit(f"short read at source frame {cur + 1}")
            cur += 1
            if cur in last_use:
                frames[cur] = buf
        enc.stdin.write(frames[f])
        for g in [g for g in frames if last_use[g] <= k]:
            del frames[g]
    dec.stdout.close(); dec.wait()
    enc.stdin.close(); enc.wait()
    print(f"-> {out.name}: {nout} frames ({nout / FPS:.2f} s)")


def save(R, edl):
    (R.dir / "edl.json").write_text(json.dumps(edl, indent=0))
    pcs = edl["pieces"]
    cuts = [p["out_a"] for i, p in enumerate(pcs) if i and abs(p["src_a"] - pcs[i - 1]["src_b"]) >= 0.02]
    (R.dir / "cuts.json").write_text(json.dumps([round(c, 3) for c in cuts]))


def report(edl):
    pcs, ow = edl["pieces"], edl["words"]
    kept = sum(p["out_b"] - p["out_a"] for p in pcs)
    print(f"{len(pcs)} pieces, talk {kept:.2f} s (0-{edl['talk_end']:.2f}), total {edl['total']:.2f} s")
    for p in pcs:
        print(f"   {p['out_a']:6.3f}-{p['out_b']:6.3f}  src {p['src_a']:6.3f}-{p['src_b']:6.3f}  {p['tag']:9s} "
              f"{' '.join(w['text'] for w in ow if p['w'][0] <= w['i'] <= p['w'][1])}")


def run(R, force=False, words_only=False, voice_only=False):
    R.work.mkdir(parents=True, exist_ok=True)
    gate(R, force)
    edl = plan(R)
    report(edl)
    if words_only:
        save(R, edl)
        return edl
    write_voice(R, edl)
    print("-> vo.wav")
    if voice_only:
        save(R, edl)
        return edl
    write_picture(R, edl)          # adds each piece's median face
    save(R, edl)
    return edl


if __name__ == "__main__":
    from kit.reel.config import Reel
    run(Reel(sys.argv[1]), force="--force" in sys.argv)
