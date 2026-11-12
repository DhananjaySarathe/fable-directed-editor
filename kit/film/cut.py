"""The cut: KEEP (whole sentences by word id, from one or more sources) -> work/edl.json + cuts.json, work/vo.wav and
one picture track per track name (work/aroll.mp4, work/screen.mp4...), everything on the film's frame grid.

Generalised from films/ai-workflows, films/reverse-engineer and films/xchakra edl.py (2026-10-20, kit/refs/
AUDIT_2026-10-20.md phase 4) and kit/reel/edl.py, which one film after another re-learned:
  - gate: kit.cut.cutcheck on the KEEP list before any media work. FAIL stops (exit 3); a REVIEW must be in JUDGED
  - words: the take's analysis.json with TIME_FIX / START_FIX / END_FIX (the aligner drifts up to 1 s on Hinglish)
  - edges in real quiet on the cleaned voice (kit/cut/edges.py): the breath and attack kept, the word allowed to finish;
    two kept phrases on consecutive words lose only the quiet between them, or stay continuous with no gap inserted;
    inside a kept range a quiet pause longer than MAX_GAP becomes a SLIVER
  - the frame grid: a piece starts on a frame (floor) and lasts a whole number of output frames at its speed; its
    picture is cut per piece with `-ss a -t d+0.2`, then `fps=FPS:round=down,trim=end_frame=n` (Framecast's .mov
    frames sit 0.02 s off the grid: -ss/-t alone put every part a frame late and a frame short). In the pause after a
    piece the source keeps playing (a real pause, never a frozen frame); black where a track has nothing
  - the voice: cut once from the cleaned source at the measured edges (va/vb), hsin fades on every splice (none inside
    a continuous run), atempo at the piece's speed
  - faces: YuNet (kit/look/faces.py) on the face track, each piece's median, for the speaker box

    uv run python -m kit.film <film> cut [--plan] [--words] [--voice] [--force]
    uv run python -m kit.film <film> joins [--no-relisten] [--at=12.3,40.1]
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np

from kit.cut.edges import envelope, in_sound, joint, offset, onset, speech_threshold
from kit.reel.edl import quiet_gap

TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
BATCH = 16                     # inputs per ffmpeg graph (a long film has hundreds of pieces; each input is a decoder)


def lead_pad(Fm, text):
    w = text.lower().strip(".,?!'\"“”")
    return Fm.SIB_LEAD if w.startswith(("s", "sh", "z", "f", "th", "ch", "c", "h")) else Fm.LEAD


def tail_pad(text):
    w = text.lower().strip(".,?!'\"…")
    if w.endswith(("s", "sh", "z", "ch", "x", "ce", "se", "%")):
        return 0.12
    if w and w[-1] in "aeiouy":
        return 0.03
    return 0.05


def voice(Fm, c, sr=None):
    """Source c's voice, cleaned (its chain), mono float32 at SR (or sr)."""
    p = Fm.voice_file(c)
    af = Fm.voice_chain(c) or "anull"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-map", "0:a:0", "-vn", "-af", af, "-ac", "1", "-ar", str(sr or Fm.SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def gate(Fm, force=False):
    """kit.cut.cutcheck on the KEEP list: FAIL stops the build (exit 3); a REVIEW must be in JUDGED with its reason."""
    from kit.cut import cutcheck
    from kit.cut.common import IdMap
    ids = IdMap.parse(",".join(f"{Fm.src(c)['job']}={Fm.src(c)['base']}" for c in Fm.SOURCES), wrap=Fm.COPY)
    rng = [(Fm.eid(k["c"], k["a"], k["copy"]), Fm.eid(k["c"], k["b"], k["copy"])) for k in Fm.keep()]
    res = cutcheck.check(cutcheck.words_from_ranges(rng, ids), ids, do_relisten=False, log=lambda *a, **k: None)
    judged = lambda j: (j["left_id"], j["right_id"]) in Fm.JUDGED      # noqa: E731
    bad = [j for j in res["joins"] if j["verdict"] in ("FAIL", "REVIEW") and not judged(j)]
    print(f"cutcheck: {res['verdict']} ({sum(j['verdict'] == 'FAIL' for j in bad)} FAIL, {sum(j['verdict'] == 'REVIEW' for j in bad)} "
          f"unjudged REVIEW, {sum(1 for j in res['joins'] if judged(j))} judged)")
    for j in res["joins"]:
        if judged(j):
            print("   judged", j["verdict"], j["left_id"], "->", j["right_id"], "|", Fm.JUDGED[(j["left_id"], j["right_id"])][:100])
    for j in bad:
        print("  ", j["verdict"], j.get("kind"), j["left_id"], "->", j["right_id"], j.get("why", ""), "|", j.get("left"), "||", j.get("right"))
    for e in res.get("edges", []):
        if e.get("verdict") in ("FAIL", "REVIEW"):
            print("   edge", e)
    (Fm.work / "cutcheck_plan.json").write_text(json.dumps(res, indent=1, default=str))
    if bad and not force:
        raise SystemExit(3)


def segments(Fm, W, env, thr):
    """Each kept range, split where a quiet pause is longer than MAX_GAP (it becomes a SLIVER)."""
    segs = []
    for k in Fm.keep():
        c, copy = k["c"], k["copy"]
        Wc = W[c]
        run = [Wc[k["a"]]]
        for w in Wc[k["a"] + 1:k["b"] + 1]:
            e = Fm.eid(c, w["i"], copy)
            g0, g1 = run[-1]["end"], w["start"]
            if g1 - g0 > Fm.MAX_GAP and e not in Fm.NOTRIM and (quiet_gap(env[c], g0, g1, thr[c]) or e in Fm.SLIVER_AT):
                segs.append({"c": c, "run": run, "tag": k["tag"], "after": Fm.SLIVER_AT.get(e, Fm.SLIVER), "copy": copy})
                run = []
            run.append(w)
        segs.append({"c": c, "run": run, "tag": k["tag"], "after": Fm.GAP if k["gap"] is None else k["gap"], "copy": copy})
    return segs


def view_of(S, t):
    return next((v for a, b, v in S["views"] if a <= t < b), S["kind"])


def split_views(Fm, p, run):
    """A piece -> sub-pieces at its source's view edges (each one kind), on whole output frames; the voice and the
    pause after it stay with the run (write_voice merges continuous pieces)."""
    S = Fm.src(p["clip"])
    sp, FPS = p["speed"], Fm.FPS
    cuts = sorted({round((x - p["src_a"]) / sp * FPS) for a, b, _ in S["views"] for x in (a, b) if p["src_a"] < x < p["src_b"]})
    edges = [0] + [m for m in cuts if 0 < m < p["nf"]] + [p["nf"]]
    out = []
    for j, (m0, m1) in enumerate(zip(edges, edges[1:])):
        sa, sb = p["src_a"] + m0 * sp / FPS, p["src_a"] + m1 * sp / FPS
        q = dict(p, src_a=round(sa, 4), src_b=round(sb, 4), out_a=round(p["out_a"] + m0 / FPS, 4), out_b=round(p["out_a"] + m1 / FPS, 4),
                 nf=m1 - m0, kind=view_of(S, (sa + sb) / 2), after=p["after"] if m1 == p["nf"] else 0.0)
        ids = [w for w in run if sa - 0.05 <= w["start"] < sb] or [max((w for w in run if w["start"] < sb), key=lambda w: w["start"], default=run[0])]
        q["w"] = [Fm.eid(p["clip"], ids[0]["i"], p["copy"]), Fm.eid(p["clip"], ids[-1]["i"], p["copy"])]
        out.append(q)
    return out


def plan(Fm, vo=None):
    """KEEP -> {total, talk_end, fps, pieces, words} (no media written). vo: {source: cleaned voice} when already decoded."""
    FPS = Fm.FPS
    used = list(dict.fromkeys(k["c"] for k in Fm.keep()))
    W = {c: Fm.words(c) for c in used}
    vo = vo or {c: voice(Fm, c) for c in used}
    env = {c: envelope(vo[c], Fm.SR) for c in used}
    thr = {c: speech_threshold(env[c]) for c in used}
    segs = segments(Fm, W, env, thr)
    pieces, words, joints, tf = [], [], {}, 0
    for k, s in enumerate(segs):
        c, run, copy = s["c"], s["run"], s["copy"]
        S, Wc = Fm.src(c), W[c]
        sp = S["speed"]
        i0, i1 = run[0]["i"], run[-1]["i"]
        e0, e1 = Fm.eid(c, i0, copy), Fm.eid(c, i1, copy)
        lo = Wc[i0 - 1]["end"] + 0.01 if i0 > 0 else 0.0
        hi = Wc[i1 + 1]["start"] - 0.01 if i1 + 1 < len(Wc) else 1e9
        sa = onset(env[c], run[0]["start"], lo, thr[c], lead=lead_pad(Fm, run[0]["text"]))
        sb = offset(env[c], run[-1]["end"], hi, thr[c])
        sb = max(sb, min(hi, run[-1]["end"] + tail_pad(run[-1]["text"]) * 0.5))
        sa, sb = Fm.IN_AT.get(e0, sa), Fm.OUT_AT.get(e1, sb)              # hard edges, measured by hand
        va, vb = max(sa, lo), min(sb, hi)                                  # the voice: the measured edges
        sa, sb = np.floor(sa * FPS + 1e-6) / FPS, np.ceil(sb * FPS - 1e-6) / FPS     # the picture: the frame grid
        if sa < lo and e0 not in Fm.IN_AT:
            sa = np.ceil(lo * FPS - 1e-6) / FPS
        if sb > hi and e1 not in Fm.OUT_AT:
            sb = np.floor(hi * FPS + 1e-6) / FPS
        after, fo, cont = s["after"], 0.025, False
        nxt = segs[k + 1] if k + 1 < len(segs) else None
        if nxt and nxt["c"] == c and nxt["copy"] == copy and nxt["run"][0]["i"] == i1 + 1:
            # the next segment starts on the very next word (a pause trim or a tag split): cut out only real quiet, or
            # stay continuous (no gap) when there is none: a gap inside a breath is what the owner heard as a cut voice
            kind, e_prev, s_next = joint(env[c], run[-1], nxt["run"][0], thr[c], FPS)
            sb = vb = e_prev
            joints[(c, i1 + 1, copy)] = s_next
            if kind == "continuous":
                after, fo, cont = 0.0, 0.04, True
        key = (c, i0, copy)
        fi = 0.015 if key in joints else 0.025
        if key in joints:
            sa = va = joints[key]
        if fo < 0.04 and in_sound(env[c], vb, thr[c]):
            fo = 0.05                                                  # he talks on into a dropped line: a softer fade
        if key not in joints and in_sound(env[c], va, thr[c]):
            fi = 0.035
        nf = max(1, int(round((sb - sa) / sp * FPS)))
        sb = sa + nf * sp / FPS                                         # whole output frames at this speed
        va, vb = max(va, sa), min(vb, sb)
        if cont:                                                        # the next piece picks up exactly here
            joints[(c, i1 + 1, copy)] = vb = sb
        af = 0 if cont else int(round(after / sp * FPS))
        p = {"kind": S["kind"], "clip": c, "tag": s["tag"], "src_a": round(float(sa), 4), "src_b": round(float(sb), 4), "speed": sp,
             "out_a": round(tf / FPS, 4), "out_b": round((tf + nf) / FPS, 4), "nf": nf, "fi": fi, "fo": fo,
             "va": round(float(va), 4), "vb": round(float(vb), 4), "w": [e0, e1], "after": round(af / FPS, 4), "copy": copy}
        for w in run:
            words.append({"i": Fm.eid(c, w["i"], copy), "text": w["text"], "tag": s["tag"],
                          "t": round(p["out_a"] + max(0.0, w["start"] - sa) / sp, 3),
                          "e": round(min(p["out_b"], p["out_a"] + (w["end"] - sa) / sp), 3)})
        pieces += split_views(Fm, p, run) if S["views"] else [p]
        tf += nf + af
    talk_end = pieces[-1]["out_b"]
    total = round((round(talk_end * FPS) + round(Fm.TAIL * FPS)) / FPS, 4)
    return {"total": total, "talk_end": round(talk_end, 4), "fps": FPS, "speed": Fm.SPEED, "pieces": pieces, "words": words}


def runs_of(pieces):
    """Continuous runs (same source, contiguous in source and output time): one voice segment each."""
    out = []
    for p in pieces:
        q = out[-1][-1] if out else None
        if q and q["clip"] == p["clip"] and abs(q["src_b"] - p["src_a"]) < 1e-3 and abs(q["out_b"] - p["out_a"]) < 1e-3:
            out[-1].append(p)
        else:
            out.append([p])
    return out


def write_voice(Fm, edl, vo):
    SR = Fm.SR
    n = int(round(edl["total"] * SR))
    y = np.zeros(n, np.float32)
    for run in runs_of(edl["pieces"]):
        p, q = run[0], run[-1]
        sp = p["speed"]
        x = vo[p["clip"]][int(round(p["va"] * SR)):int(round(q["vb"] * SR))]
        mutes = [(a, b) for c, a, b in Fm.VOICE_MUTE if c == p["clip"] and a < q["vb"] and b > p["va"]]
        if mutes:                                                      # VOICE_MUTE: a click before a word, silenced in place
            x = x.copy()
            r = max(1, int(0.005 * SR))
            for a, b in mutes:
                i0, i1 = int(round((a - p["va"]) * SR)), int(round((b - p["va"]) * SR))
                g = np.ones(len(x), np.float32)
                g[max(0, i0):max(0, i1)] = 0.0
                for j in range(r):                                     # raised-cosine ramps into and out of the silence
                    w = 0.5 - 0.5 * np.cos(np.pi * j / r)
                    if 0 <= i0 - r + j < len(x):
                        g[i0 - r + j] = min(g[i0 - r + j], 1 - w)
                    if 0 <= i1 + j < len(x):
                        g[i1 + j] = min(g[i1 + j], w)
                x = x * g
        af = f"afade=t=in:d={p['fi']}:curve=hsin,areverse,afade=t=in:d={q['fo']}:curve=hsin,areverse"
        if Fm.VOICE_GAIN.get(p["tag"]):
            af = f"volume={Fm.VOICE_GAIN[p['tag']]}dB," + af
        if sp != 1.0:
            af = f"atempo={sp}," + af
        seg = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", af,
                                            "-f", "f32le", "-"], input=x.tobytes(), capture_output=True, check=True).stdout, np.float32)
        i = int(round((p["out_a"] + (p["va"] - p["src_a"]) / sp) * SR))
        end = int(round(q["out_b"] * SR))                              # never past the run's own last frame
        seg = seg[:max(0, min(len(seg), end - i, n - i))]
        y[i:i + len(seg)] += seg
    if Fm.ROOM_TONE is not None:
        y += room_tone(Fm, edl, y, n)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s24le",
                    str(Fm.work / "vo.wav")], input=y.tobytes(), check=True)
    print(f"-> {Fm.work / 'vo.wav'} ({n / SR:.2f} s)")


def room_audio(Fm, c, hp=None):
    """The take's own sound, uncleaned (the room is in it): the probe's working file, else the source's video. hp: a
    4-pole high-pass at hp Hz (v11: kit/film/prep.py DEPLOSIVE_HZ, so a thump or rumble under 90 Hz is not looped)."""
    import json as _json
    from kit.paths import job_dir
    probe = job_dir(Fm.src(c)["job"]) / "probe.json"
    p = _json.loads(probe.read_text())["working_path"] if probe.exists() else Fm.video(c)
    af = ["-af", f"highpass=f={hp},highpass=f={hp}"] if hp else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-map", "0:a:0", "-ac", "1", "-ar", str(Fm.SR)] + af + ["-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def room_tone(Fm, edl, vo, n):
    """ROOM_TONE (dB vs the room's natural level; kit/reel/edl.py room_tone, per source): a cleaned voice leaves digital
    silence in every pause (a hole, not a beat; mix.py prints them as dropout RUNS). Each source's quietest 0.8 s with no
    word in it is looped (50 ms crossfades) under that source's stretches of the cut (each piece to the next piece's
    start, 50 ms ramps), set where the room sat under his voice in the take. -> n samples"""
    from kit.film.prep import DEPLOSIVE_HZ, v11_voice
    SR, fr = Fm.SR, Fm.SR // 20
    out = np.zeros(n, np.float32)
    P = edl["pieces"]
    hp = DEPLOSIVE_HZ if v11_voice(Fm) else None                   # v11: no sub-90 Hz thump looped under the pauses
    for c in dict.fromkeys(p["clip"] for p in P):
        x = room_audio(Fm, c, hp=hp)
        m = len(x) // fr
        env = np.sqrt(np.mean(np.square(x[:m * fr].reshape(m, fr).astype(np.float64)), axis=1)) + 1e-9    # 50 ms RMS
        Wc = Fm.words(c)
        talk = np.zeros(len(env), bool)
        for w in Wc:
            talk[max(0, int((w["start"] - 0.25) * 20)):int((w["end"] + 0.35) * 20)] = True
        k = 16                                                       # 0.8 s
        cand = [(float(np.median(env[j:j + k])), j) for j in range(len(env) - k) if not talk[j:j + k].any() and env[j:j + k].min() > 1e-5]
        if not cand:
            print(f"room tone {c}: no 0.8 s without words or digital silence: skipped")
            continue
        def clean(j):                                                # no click in it: a one-sample step in the loop is a
            s_ = x[j * fr:(j + k) * fr].astype(np.float64)           # tick in every pause it fills (critic, 2026-10-21)
            return np.max(np.abs(np.diff(s_))) < 8 * (np.sqrt(np.mean(s_ ** 2)) + 1e-9)
        cand.sort()
        j0 = next((j for _, j in cand[:400] if clean(j)), cand[0][1])
        seg = x[j0 * fr:(j0 + k) * fr].astype(np.float32)
        ramp = np.linspace(0, 1, fr, dtype=np.float32)
        loop = np.zeros(n + len(seg), np.float32)
        pos = 0
        while pos < n:
            piece = seg.copy()
            piece[:fr] *= ramp
            piece[-fr:] *= ramp[::-1]
            loop[pos:pos + len(piece)] += piece
            pos += len(piece) - fr
        mine = [w for w in edl["words"] if Fm.of_eid(w["i"])[0] == c]
        said = np.concatenate([vo[int(w["t"] * SR):int(w["e"] * SR)] for w in mine]) if mine else np.zeros(1)
        speech = np.concatenate([x[int(Wc[Fm.of_eid(w["i"])[1]]["start"] * SR):int(Wc[Fm.of_eid(w["i"])[1]]["end"] * SR)] for w in mine]) if mine else np.ones(1)
        g = 20 * np.log10((np.sqrt(np.mean(said ** 2)) + 1e-9) / (np.sqrt(np.mean(speech ** 2)) + 1e-9)) + Fm.ROOM_TONE
        mask = np.zeros(n, np.float32)
        for k2, p in enumerate(P):
            if p["clip"] != c:
                continue
            a = int(round(p["out_a"] * SR))
            b = int(round(P[k2 + 1]["out_a"] * SR)) if k2 + 1 < len(P) else n
            mask[a:b] = 1.0
        cs = np.concatenate([[0.0], np.cumsum(mask, dtype=np.float64)])   # a 50 ms moving average: ramps where it starts or stops
        idx = np.arange(n)
        lo_, hi_ = np.clip(idx - fr // 2, 0, n), np.clip(idx + fr // 2, 0, n)
        mask = ((cs[hi_] - cs[lo_]) / fr).astype(np.float32)
        out += loop[:n] * mask * np.float32(10 ** (g / 20))
        print(f"room tone {c}: take {j0 * 0.05:.2f}-{(j0 + k) * 0.05:.2f} s, {20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9):.1f} dB raw, set {g:+.1f} dB")
    return out


def vf_for(Fm, name, c, kind):
    """The ffmpeg filter for source c's picture on track `name` while it shows `kind`; None = black."""
    t = Fm.src(c)["tracks"].get(name)
    if isinstance(t, dict):
        return t.get(kind)
    return t


def frames(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return int(r.stdout.strip().split("\n")[0].strip().rstrip(",") or 0)   # some ffprobe builds print "5826," (who-gonna-hire, 2026-10-23)


def hold_gap(Fm, P, k) -> bool:
    """Piece k ends its scene (the next piece has another tag, or it is the last) and its tag holds its picture there."""
    hg = Fm.HOLD_GAP
    if not hg or (k + 1 < len(P) and P[k + 1]["tag"] == P[k]["tag"]):
        return False
    return hg is True or P[k]["tag"] in hg


def write_track(Fm, edl, name):
    """One picture track over the whole timeline: each piece's source picture from its out_a to the next piece's
    (the source plays on through the pause after it), black where this track shows nothing. At the end of a scene in
    Fm.HOLD_GAP the picture holds the piece's last frame instead (hold_gap)."""
    FPS, (OW, OH) = Fm.FPS, Fm.track_size(name)
    P, N = edl["pieces"], int(round(edl["total"] * FPS))
    parts, tf = [], 0                                         # ("black", n) | ("src", c, sa, speed, n, vf, m: frames that play)
    pic = lambda q: q.get("pic_a", q["out_a"])                # noqa: E731  a documentary's J/L cut moves the picture only (kit/film/doc.py)
    for k, p in enumerate(P):
        a = int(round(pic(p) * FPS))
        if a > tf:
            parts.append(("black", a - tf))
        b = int(round(pic(P[k + 1]) * FPS)) if k + 1 < len(P) else N
        m = max(1, min(b, int(round(p["out_b"] * FPS))) - a) if hold_gap(Fm, P, k) else b - a
        vf = vf_for(Fm, name, p["clip"], p["kind"])
        sa = p["src_a"] if "pic_a" not in p else round(p["src_a"] + (a / FPS - p["out_a"]) * p["speed"], 4)
        parts.append(("black", b - a) if vf is None else ("src", p["clip"], sa, p["speed"], b - a, vf, m))
        tf = b
    merged = []
    for q in parts:
        if q[0] == "black" and merged and merged[-1][0] == "black":
            merged[-1] = ("black", merged[-1][1] + q[1])
        elif (q[4] if q[0] == "src" else q[1]) > 0:
            merged.append(q)
    tmp = Fm.work / f"{name}_parts"
    tmp.mkdir(exist_ok=True)
    files = []
    for b0 in range(0, len(merged), BATCH):
        out = tmp / f"p{b0 // BATCH:03d}.mp4"
        args, fl = ["nice", "-n", "10", "ffmpeg", "-v", "error", "-y"], []
        for j, q in enumerate(merged[b0:b0 + BATCH]):
            if q[0] == "black":
                n = q[1]
                args += ["-f", "lavfi", "-t", f"{n / FPS + 0.1:.4f}", "-i", f"color=c=black:s={OW}x{OH}:r={FPS}"]
                fl.append(f"[{j}:v]trim=end_frame={n},setsar=1,format=yuv420p[v{j}]")
            else:
                _, c, sa, sp, n, vf, m = q
                # a quarter frame early: sa written at 4 decimals rounds 17/30 UP to 0.5667, past the frame's own time, so
                # -ss dropped it and every piece starting on a frame 2 mod 3 ran a frame late (found on the example)
                args += ["-threads", "3", "-ss", f"{max(0.0, sa - 0.25 / FPS):.5f}", "-t", f"{m / FPS * sp + 0.2:.4f}", "-i", str(Fm.video(c))]
                chain = (vf + "," if vf else "") + f"scale={OW}:{OH}:flags=lanczos,"
                chain += (f"setpts=PTS/{sp}," if sp != 1.0 else "") + f"fps={FPS}:round=down,"
                chain += (f"trim=end_frame={m}," if m < n else "") + f"tpad=stop_mode=clone:stop_duration={(n - m) / FPS + 1:.4f},"
                fl.append(f"[{j}:v]{chain}trim=end_frame={n},setsar=1,format=yuv420p[v{j}]")
        m = len(fl)
        fl.append("".join(f"[v{j}]" for j in range(m)) + f"concat=n={m}:v=1:a=0[out]")
        args += ["-filter_complex", ";".join(fl), "-map", "[out]", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(Fm.TRACK_CRF),
                 "-g", "15", "-bf", "0", "-pix_fmt", "yuv420p", *TAGS, "-an", str(out)]     # no B-frames: the parts join by copy
        subprocess.run(args, check=True)
        files.append(out)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    out = Fm.work / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    got = frames(out)
    for f in files:
        f.unlink()
    if got != N:
        raise SystemExit(f"{out.name}: {got} frames, want {N} (a piece lost or gained frames: check its source and -ss)")
    print(f"-> {out} ({OW}x{OH}, {N} frames, {len(merged)} parts)")
    return out


def faces(Fm, edl):
    """Each piece's face [cx, cy, size] in page pixels: the median of YuNet's track on FACE_TRACK over the piece."""
    name = Fm.FACE_TRACK
    if not Fm.FACES or name not in Fm.tracks():
        for p in edl["pieces"]:
            p["face"] = list(Fm.FACE)
        return
    from kit.paths import ROOT
    tr_path = Fm.work / f"{name}.face.json"
    subprocess.run([sys.executable, str(ROOT / "kit/look/faces.py"), str(Fm.work / f"{name}.mp4"), str(tr_path)], check=True, cwd=ROOT)
    tr = json.loads(tr_path.read_text())
    s = Fm.W / Fm.track_size(name)[0]
    for p in edl["pieces"]:
        a = int(round(p["out_a"] * Fm.FPS))
        fs = [f for f in tr[a:max(a + 1, int(round(p["out_b"] * Fm.FPS)))] if f and f[2] > 0]
        p["face"] = [round(float(np.median([f[i] for f in fs])) * s, 1) for i in range(3)] if fs else list(Fm.FACE)
    print(f"faces: {tr_path.name} ({len(tr)} frames; a stretch with no face holds the last one found)")


# ------------------------------------------------------------------------------------------------ track sizes / zoom budget
# 2026-10-22 (v11, the camera on him): the page's lens zooms his footage inside its shapes, and a zoom is only free while
# each render pixel still has a source pixel behind it. A 4K selfie cropped 2160 square and scaled to a 1080 track has
# thrown that headroom away before the page sees it. So a film can keep the native crop (TRACK_SIZE "native", no scale
# in its vf), and the cut writes work/tracks.json: per track, what the page may zoom before the picture softens.
import math as _math

_FN = {"min": min, "max": max, "abs": abs, "trunc": _math.trunc, "floor": _math.floor, "ceil": _math.ceil, "round": round,
       "sqrt": _math.sqrt}


def _split(s, sep):
    """s split at `sep` outside quotes and brackets, honouring ffmpeg's backslash escape ('min(iw,ih)' stays whole)."""
    out, cur, depth, q, k = [], "", 0, None, 0
    while k < len(s):
        ch = s[k]
        if ch == "\\" and k + 1 < len(s):
            cur += s[k + 1]
            k += 2
            continue
        if q:
            q = None if ch == q else q
        elif ch in "'\"":
            q = ch
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == sep and depth == 0:
            out.append(cur)
            cur, k = "", k + 1
            continue
        cur += ch
        k += 1
    return out + [cur]


def _num(expr, iw, ih, ow=None, oh=None):
    """An ffmpeg size argument (1080, iw/2, 'ih*9/16', 'min(iw,ih)', trunc(oh*a/2)*2) -> float, or None (-1/-2: keep
    the aspect). Raises ValueError for one it can't evaluate (v11 review: an unread expression used to count as the
    whole input, overstating the source pixels behind a track)."""
    s = str(expr).strip().replace("'", "").replace('"', "").replace("in_w", "iw").replace("in_h", "ih") \
        .replace("out_w", "ow").replace("out_h", "oh")
    names = {"iw": iw, "ih": ih, "a": iw / ih, "dar": iw / ih, "sar": 1.0, **_FN}
    names.update({k: v for k, v in (("ow", ow), ("oh", oh)) if v is not None})
    try:
        v = float(eval(s, {"__builtins__": {}}, names))
    except Exception as e:                       # noqa: BLE001 (any parse / name error: the expression is not read)
        raise ValueError(f"vf size {expr!r}: can't evaluate ({type(e).__name__})") from None
    return None if v < 0 else v


def _args(a):
    """A filter's 'w:h:x=..' arguments -> (positional, {key: value})."""
    parts = [x for x in _split(a, ":") if x != ""] if a else []
    return [x for x in parts if "=" not in x], dict(x.split("=", 1) for x in parts if "=" in x)


def vf_size(size, vf):
    """The picture after the ffmpeg chain `vf` from a frame of `size`: ((w, h), (ew, eh)) = its frame size and the
    source pixels behind it across each axis (a crop keeps the density, a downscale lowers it to the new size, an
    upscale adds none; transpose swaps the axes). Filters other than crop / scale / transpose (delogo, eq, hflip...)
    change neither. An expression it can't read raises ValueError (never assumed to be the whole frame)."""
    w, h = float(size[0]), float(size[1])
    ew, eh = w, h
    for f in filter(None, (s.strip() for s in _split(vf or "", ","))):
        name, _, a = f.partition("=")
        pos, kw = _args(a)
        if name == "crop":
            cw = _num(kw.get("w", kw.get("out_w", pos[0] if pos else "iw")), w, h)
            cw = w if cw is None else cw
            ch = _num(kw.get("h", kw.get("out_h", pos[1] if len(pos) > 1 else "ih")), w, h, ow=cw)
            ch = h if ch is None else ch
            ew, eh, w, h = ew * cw / w, eh * ch / h, cw, ch
        elif name == "scale":
            ws = kw.get("w", kw.get("width", pos[0] if pos else "iw"))
            hs = kw.get("h", kw.get("height", pos[1] if len(pos) > 1 else "ih"))
            try:
                nw = _num(ws, w, h)
                nh = _num(hs, w, h, ow=nw)
            except ValueError:                   # w written in terms of oh (scale=w=oh*a:h=720): h first
                nh = _num(hs, w, h)
                nw = _num(ws, w, h, oh=nh)
            nw, nh = (nw or (nh or h) * w / h), (nh or (nw or w) * h / w)
            ew, eh, w, h = min(ew, nw), min(eh, nh), nw, nh
        elif name == "transpose":
            pt = kw.get("passthrough", "none")   # passthrough=landscape: a landscape input is left as it is
            if not ((pt == "landscape" and w >= h) or (pt == "portrait" and h >= w)):
                ew, eh, w, h = eh, ew, h, w      # every direction (0-3, clock, cclock...) swaps the axes
    return (w, h), (ew, eh)


def native_size(Fm, name):
    """TRACK_SIZE "native": the largest picture any source feeds this track (after its vf), even-sized: a 2160 square
    selfie crop stays 2160 (the 576 Framecast bubble on the same track is scaled up to it once, by the cut)."""
    best = (0, 0)
    for c in Fm.SOURCES:
        t = Fm.src(c)["tracks"].get(name)
        if t is None:
            continue
        for vf in (t.values() if isinstance(t, dict) else [t]):
            if vf is None:
                continue
            (w, h), _ = vf_size(Fm.size(c), vf)
            if w * h > best[0] * best[1]:
                best = (int(round(w / 2)) * 2, int(round(h / 2)) * 2)
    if not best[0]:
        raise SystemExit(f"TRACK_SIZE {name}: native, but no source feeds it")
    return best


# Two numbers per showing (v11 review, 2026-10-22):
#   max_zoom   the tracks.json contract's: source px / shown px at the render size (r), never under 1 (a zoom is over
#              cover): how far the page may zoom before it softens at all. A 4K room on a 4K render at full height: 1.0
#   soft_zoom  how far it may zoom accepting mild softness: r, and at least 1 + SOFT * min(r, 1) (a judgment constant
#              that gives the budgets the v11 gap map named: a 1080 take on a 4K render ~1.12, a Framecast bubble ~1.05,
#              the 4K room at full height 1.24). Offered, not imposed: the lens and precheck cap at max_zoom unless the
#              owner takes the softer allowance
SOFT = 0.24


def zoom_budget(sharp_px: float, shown_px: float) -> float:
    """The contract's max_zoom for footage sharp up to `sharp_px` page px in a shape `shown_px` page px tall:
    max(1, r), r = sharp_px / shown_px (the zoom at which a source pixel is one render pixel)."""
    return round(max(1.0, sharp_px / max(shown_px, 1e-6)), 3)


def soft_budget(sharp_px: float, shown_px: float) -> float:
    """The softer allowance: max(r, 1 + SOFT * min(r, 1)) (a picture already stretched, r < 1, may zoom SOFT * r
    further; one with headroom zooms to its 1:1 point, and at least 1 + SOFT)."""
    r = sharp_px / max(shown_px, 1e-6)
    return round(max(r, 1 + SOFT * min(r, 1.0)), 3)


def render_scale(Fm) -> float:
    """Render px per page px at the film's one render (kit/film/render.py: 16:9 renders 3840 wide; a Reel at its page).
    RENDER_SCALE in film.py wins (1.0: a film delivered at its page size, e.g. a 1080p film whose framings crop a 4K
    take past what a 4K render could back: who-gonna-hire, 2026-10-23)."""
    if getattr(Fm, "RENDER_SCALE", None):
        return float(Fm.RENDER_SCALE)
    return 3840 / Fm.W if Fm.W >= Fm.H else 1.0


def _kind_px(Fm, edl, name, OW, OH) -> dict:
    """{view kind: (ew, eh)}: the source pixels behind track `name` (frame OW x OH) per kind it shows in this film's
    edl, the poorest piece of each kind (each piece's own vf, then the cut's scale to the track size: write_track)."""
    P = edl["pieces"]
    sizes = {c: Fm.size(c) for c in dict.fromkeys(p["clip"] for p in P)}
    kinds = {}
    for p in P:
        vf = vf_for(Fm, name, p["clip"], p["kind"])
        if vf is None:
            continue
        _, (ew, eh) = vf_size(sizes[p["clip"]], (vf + "," if vf else "") + f"scale={OW}:{OH}")
        cur = kinds.get(p["kind"])
        if cur is None or ew * eh < cur[0] * cur[1]:
            kinds[p["kind"]] = (ew, eh)
    return kinds


def track_info(Fm, edl) -> dict:
    """work/tracks.json (the engine's D.tracks contract): per track {w, h (the track file's frame), src_w, src_h (source
    pixels behind it: the poorest kind it shows), render_scale, ref_px, sharp_px, max_zoom, soft_zoom, soft, kinds}.

      sharp_px   the page height (px) up to which the footage still has a source pixel per render pixel (a 1080 track
                 on a 4K render: 540; the 576 px Framecast bubble: 288)
      ref_px     the reference showing: TRACK_SHOW[track], default the page height (a full-height card, or full bleed)
      max_zoom   zoom_budget(sharp_px, ref_px) = max(1, sharp_px / ref_px): the contract's cap over cover at that
                 showing (the poorest kind's); any shape S px tall: max(1, sharp_px / S)
      soft_zoom  soft_budget(sharp_px, ref_px): the allowance with mild softening (soft = SOFT), for the owner to take
      ZOOM_CAP   (film.py) sharp_px = ZOOM_CAP x ref_px instead of the source's: max_zoom = soft_zoom = ZOOM_CAP at the
                 reference showing, and the same footage scale (page px per source px) in every smaller shape
      kinds      {view kind: {src_w, src_h, sharp_px, max_zoom, soft_zoom, soft, share}} (share = fraction of the
                 timeline). The kind is a piece's "kind" (D.pieces); a kind this track shows black for has no entry.

    The top-level budget fields are the poorest kind's (the lowest sharp_px). Each kinds entry carries the same fields
    (2026-10-22, v11 fix: the per-kind contract tracks.json[name].kinds[kind] = {sharp_px, max_zoom, soft_zoom, soft}),
    so the page's lens reads the kind playing in a hold as it reads a track: MO.lensBudget(kinds[kind], Hc, ...) gives
    max(1, sharp_px / Hc), and its "soft" mode soft_budget(sharp_px, Hc). On v11-sample's face track the cam kind is
    native 4K (sharp 1080: x1.143 in a 945 px card) while the Framecast bubble is 162; the top level says 162 for both.

    A Reel (kit/film reels: Fm.reel, its pieces cut from the film's tracks) gets the same file for its own page: the
    source pixels per kind from the film's edl, the shares from the Reel's pieces, render_scale and ref_px from the
    Reel's page (a 1080 x 1920 Reel renders at its page: 1.0, ref 1920)."""
    R = render_scale(Fm)
    cap = getattr(Fm, "ZOOM_CAP", None)
    show = getattr(Fm, "TRACK_SHOW", {}) or {}
    parent = getattr(Fm, "parent", None) if getattr(Fm, "reel", None) else None
    srcF, srcE = (parent, parent.edl()) if parent is not None else (Fm, edl)
    if parent is not None and show is (getattr(parent, "TRACK_SHOW", None) or {}):
        show = {}                                # the film's TRACK_SHOW is in the film page's px: a Reel sets its own (track_show=)
    P = edl["pieces"]
    out = {}
    for name in srcF.tracks():
        OW, OH = (edl.get("tracks") or {}).get(name) or srcF.track_size(name)
        ref = float(show.get(name, Fm.H))
        kinds = _kind_px(srcF, srcE, name, OW, OH)
        secs = {}
        for k, p in enumerate(P):
            if p["kind"] not in kinds or (parent is None and vf_for(Fm, name, p["clip"], p["kind"]) is None):
                continue
            t1 = P[k + 1]["out_a"] if k + 1 < len(P) else edl["total"]
            secs[p["kind"]] = secs.get(p["kind"], 0.0) + (t1 - p["out_a"])
        if not secs:
            continue
        tot = sum(secs.values()) or 1.0
        ks = {}
        for kd in secs:
            ew, eh = kinds[kd]
            sharp = round(min(eh, ew * OH / OW) / R, 1)        # the budgets from the sharp_px written, as the lens reads it
            if cap:                                             # ZOOM_CAP: x cap over the page's full-frame cover, at most
                sharp = round(cap * ref, 1)
            ks[kd] = {"src_w": int(round(ew)), "src_h": int(round(eh)), "sharp_px": sharp, "max_zoom": zoom_budget(sharp, ref),
                      "soft_zoom": soft_budget(sharp, ref), "soft": SOFT, "share": round(secs[kd] / tot, 3)}
        worst = min(ks.values(), key=lambda v: v["sharp_px"])
        out[name] = {"w": OW, "h": OH, "src_w": worst["src_w"], "src_h": worst["src_h"], "render_scale": round(R, 4), "ref_px": ref,
                     "sharp_px": worst["sharp_px"], "max_zoom": worst["max_zoom"], "soft_zoom": worst["soft_zoom"], "soft": SOFT,
                     "kinds": ks}
    return out


def write_tracks(Fm, edl, path=None):
    """track_info -> work/tracks.json (or `path`), with one line per track in the log. A film's cut writes it (save);
    a Reel's (kit/film reels) is written the same way from the Reel's config and edl: write_tracks(R, reel_edl)."""
    info = track_info(Fm, edl)
    p = path or Fm.work / "tracks.json"
    p.write_text(json.dumps(info, indent=1))
    for n, v in info.items():
        print(f"tracks: {n} {v['w']}x{v['h']} (source {v['src_w']}x{v['src_h']} px at the poorest), sharp to {v['sharp_px']:.0f} page px "
              f"tall at x{v['render_scale']:g} render: max zoom {v['max_zoom']:.2f} (soft {v['soft_zoom']:.2f}) at {v['ref_px']:.0f} px")
        if len(v["kinds"]) > 1:                  # the lens budgets each hold by the kind playing in it, not the poorest
            print("        per kind: " + ", ".join(f"{k} sharp {e['sharp_px']:.0f} px, max {e['max_zoom']:.2f} (soft {e['soft_zoom']:.2f}), "
                                                   f"{e['share']:.0%} of the time" for k, e in v["kinds"].items()))
    print(f"-> {p}")
    return info


def save(Fm, edl):
    edl = dict(edl, tracks={n: list(Fm.track_size(n)) for n in Fm.tracks()})
    Fm.edl_path.write_text(json.dumps(edl, indent=0))
    try:
        write_tracks(Fm, edl)
    except (SystemExit, OSError, subprocess.CalledProcessError, ValueError) as e:   # a --words / --voice run before prep's picture
        print(f"tracks.json: skipped ({e})")
    P = edl["pieces"]
    cuts = [p["out_a"] for q, p in zip(P, P[1:]) if not (p["clip"] == q["clip"] and abs(p["src_a"] - q["src_b"]) < 1e-3
                                                         and abs(p["out_a"] - q["out_b"]) < 1e-3)]
    (Fm.work / "cuts.json").write_text(json.dumps([round(c, 3) for c in cuts]))
    print(f"-> {Fm.edl_path}: {len(P)} pieces, {len(edl['words'])} words, {len(cuts)} cuts")


def report(edl):
    P, ws = edl["pieces"], edl["words"]
    print(f"{len(P)} pieces, talk {sum(p['out_b'] - p['out_a'] for p in P):.2f} s (cut ends {edl['talk_end']:.2f} s), total {edl['total']:.2f} s")
    for p in P:
        txt = " ".join(w["text"] for w in ws if p["w"][0] <= w["i"] <= p["w"][1])
        print(f"  {p['out_a']:7.3f}-{p['out_b']:7.3f}  {str(p['clip']):>3} {p['kind']:6s} {p['src_a']:8.3f}-{p['src_b']:8.3f} x{p['speed']}"
              f"  {p['tag']:10s} {txt[:70]}")


def run(Fm, force=False, plan_only=False, words_only=False, voice_only=False):
    Fm.work.mkdir(parents=True, exist_ok=True)
    gate(Fm, force)
    used = list(dict.fromkeys(k["c"] for k in Fm.keep()))
    vo = {c: voice(Fm, c) for c in used}
    edl = plan(Fm, vo)
    from kit.film import doc                                   # the documentary preset only (PRESET = "documentary")
    doc.apply_jl(Fm, edl)
    report(edl)
    if plan_only:
        return edl
    if not words_only:
        write_voice(Fm, edl, vo)
    if words_only or voice_only:
        if not words_only:
            doc.cut(Fm, edl, picture=False)
        for p in edl["pieces"]:
            p.setdefault("face", list(Fm.FACE))
        save(Fm, edl)
        return edl
    for name in Fm.tracks():
        write_track(Fm, edl, name)
    faces(Fm, edl)
    doc.cut(Fm, edl)
    save(Fm, edl)
    return edl


def joins(Fm, relisten=True, at=None):
    """The voice-cut audit: every piece edge on the cleaned voice's envelope (an edge inside a sound is printed), then
    the re-listen: whisper on each join of vo.wav, the words meant vs the words heard (kit.cut.relisten). Exit 2 if
    any join needs a check."""
    from kit.cut.edges import audit
    edl = Fm.edl()
    code = 0
    if not Fm.reel:
        used = list(dict.fromkeys(p["clip"] for p in edl["pieces"]))
        env = {c: envelope(voice(Fm, c), Fm.SR) for c in used}
        thr = {c: speech_threshold(env[c]) for c in used}
        bad = audit([dict(r[0], src_a=r[0]["va"], src_b=r[-1]["vb"], out_b=r[-1]["out_b"], w=[r[0]["w"][0], r[-1]["w"][1]])
                     for r in runs_of(edl["pieces"])], env, thr)
        print(f"edges in a sound: {len(bad)}" + "".join(f"\n  {t:7.2f} {side:5s} {lv} dB  word {w}" for t, side, lv, w in bad))
    if relisten:
        from kit.cut.relisten import main as rl
        from kit.film.doc import voice_wav                      # vo.wav, or a documentary's voice without its natural sound
        args = [str(Fm.edl_path), str(voice_wav(Fm))] + (["--hinglish"] if Fm.HINGLISH else []) + ([f"--at={at}"] if at else [])
        code = rl(args + [f"--json={Fm.work / 'relisten.json'}"])
    return code
