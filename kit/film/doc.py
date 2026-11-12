"""The documentary preset's film side (kit/presets/documentary, 2026-10-24): cutaways (B-roll) over the voice, J/L cuts,
natural sound, and the page data for kit/hf/doc.js (lower-thirds, chapter cards, time stamps, subtitles, letterbox).

OPT-IN ONLY. A film is a documentary when its film.py says PRESET = "documentary" (the owner asked for a "Netflix-style"
film; his normal talking-head and tutorial edits never do). Every function here returns at once for any other film,
and guard() refuses the documentary settings (DOC, a J/L dict on a KEEP entry) on a film that is not one, so a normal
film's cut, page and mix are byte-identical to what they were before this file existed (tests/test_documentary.py).

film.py of a documentary:

    PRESET = "documentary"
    SOURCES = {
        "me":    dict(job=..., kind="interview", speaker="Alex", role="Developer · @yourchannel", tracks={"aroll": ""}),
        "owner": dict(job=..., kind="guest", speaker="Priya", role="Owner, Café X", base=4000, tracks={"aroll": ""}),
    }
    KEEP = [
        ("owner", 12, 40, "client", {"l": 0.6}),   # L-cut: her picture comes in 0.6 s early, over the end of his line
        ("me", 101, 130, "attempt1", {"j": 0.8}),   # J-cut: his voice starts 0.8 s before his picture replaces hers
    ]
    DOC = dict(
        broll=[dict(file="assets/broll/typing.mp4", at="w104", dur=3.5, src_in=1.2, audio="natural", gain=-10),
               dict(file="assets/screens/site_v1.mp4", at="w118-0.3", until="w130", audio="mute", grade=False)],
        chapters=[dict(at="tag:attempt1", title="Attempt one", sub="Day 1 · 23:10", dur=2.4)],
        stamps=[dict(at="w104", text="DAY 1 · 23:10", dur=3.0)],
        letterbox=[("tag:client", "tag:attempt1")],         # thin 2.39:1 bars over these spans (never on screen work)
        lower_thirds="first",                               # each speaker's name + role on their first piece ("all", False)
        subtitles=True,                                     # documentary subtitles instead of word-by-word captions
        grade="doc",                                        # the LUT the cutaways are graded with (None: as shot)
    )

B-roll: each entry is cut on the film's frame grid to work/broll/b<NN>.mp4 (16:9 cover at the page aspect, up to
3840x2160, no audio), graded with the doc look's LUT unless grade=False (a screen recording), and placed by the page
(D.doc.broll, HF.doc(...).broll()) over the speaker. at / until take kit/film/mix.py when() values: seconds, "w<id>",
"w<id>+0.4", "tag:<tag>", "end-2". audio "natural": the clip's own sound under the voice (gain dB, ducked a further
duck dB while he talks) is mixed into work/vo.wav, so the music steps back for it as it does for his voice; the voice
alone stays in work/vo_voice.wav for the join re-listen.

J/L cuts: a KEEP entry's dict {"j": s} starts that range's PICTURE s later than its sound (the previous shot holds over
the first words), {"l": s} starts it s earlier (this shot comes in over the end of the previous line). Only the picture
moves (piece["pic_a"], read by kit/film/cut.py write_track); the voice, the words and the captions keep their times.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

NAME = "documentary"
SCORE_CUES = 6               # a documentary's MUSIC is a score: up to this many cues (one per act, an explainer's own)
SCORE_LRA = 16.0             # LU the master keeps linear (a normal film: 11; past it loudnorm squashes the swells)
DOC_KEYS = {"broll", "chapters", "stamps", "letterbox", "lower_thirds", "subtitles", "grade", "results"}
BROLL_KEYS = {"file", "at", "dur", "until", "src_in", "audio", "gain", "duck", "grade", "vf", "speed", "label", "z"}
MAX_W, MAX_H = 3840, 2160


def on(Fm) -> bool:
    return getattr(Fm, "PRESET", None) == NAME


def jl_marks(Fm) -> list:
    """[(index into Fm.keep(), {"j": s, "l": s})] for the KEEP entries that carry a J/L dict."""
    out = []
    for n, k in enumerate(Fm.KEEP):
        d = next((x for x in k if isinstance(x, dict)), None)
        if d:
            out.append((n, d))
    return out


def guard(Fm):
    """Refuse documentary settings on a film that is not a documentary (and unknown keys on one that is)."""
    doc_set = bool(getattr(Fm, "DOC", None))
    jl = jl_marks(Fm)
    preset = getattr(Fm, "PRESET", None)
    if preset not in (None, NAME):
        raise SystemExit(f"{Fm.dir}: PRESET = {preset!r}: kit/film knows only None (the normal pipeline) and {NAME!r}")
    if not on(Fm):
        if doc_set or jl:
            what = "DOC" if doc_set else "a J/L dict on KEEP"
            raise SystemExit(f"{Fm.dir}: {what} is a documentary setting: set PRESET = \"{NAME}\" in film.py, or remove it "
                             "(normal films never use the documentary pipeline)")
        return
    bad = set(Fm.DOC) - DOC_KEYS
    if bad:
        raise SystemExit(f"{Fm.dir}: DOC has unknown keys {sorted(bad)} (known: {sorted(DOC_KEYS)})")
    for n, b in enumerate(Fm.DOC.get("broll") or []):
        extra = set(b) - BROLL_KEYS
        if extra:
            raise SystemExit(f"{Fm.dir}: DOC broll[{n}] has unknown keys {sorted(extra)} (known: {sorted(BROLL_KEYS)})")
        if "file" not in b or "at" not in b or ("dur" not in b and "until" not in b):
            raise SystemExit(f"{Fm.dir}: DOC broll[{n}] needs file, at and dur (or until)")
        if b.get("audio", "mute") not in ("mute", "natural"):
            raise SystemExit(f"{Fm.dir}: DOC broll[{n}] audio must be 'mute' or 'natural'")
    for _, d in jl:
        if set(d) - {"j", "l"} or any(float(v) < 0 for v in d.values()) or ("j" in d and "l" in d):
            raise SystemExit(f"{Fm.dir}: a KEEP J/L dict is {{'j': s}} or {{'l': s}} (s >= 0, one of them): got {d}")


# ------------------------------------------------------------------------------------------------ J/L cuts
def apply_jl(Fm, edl) -> list:
    """Set piece["pic_a"] (the picture's start on the film) on the first piece of each KEEP range with a J/L dict.
    -> the moves made [{tag, out_a, pic_a}]. A move that can't be made (no picture before the source's start, a
    picture that would start before the previous shot's or after its own piece ends) is clamped and printed."""
    if not on(Fm):
        return []
    FPS, P, keeps = Fm.FPS, edl["pieces"], Fm.keep()
    moves = []
    for n, d in jl_marks(Fm):
        k = keeps[n]
        e0 = Fm.eid(k["c"], k["a"], k["copy"])
        i = next((i for i, p in enumerate(P) if p["w"][0] == e0 and p["tag"] == k["tag"]), None)
        if i is None or i == 0:
            print(f"J/L {k['tag']}: {'the film starts here' if i == 0 else 'no piece found'}: skipped")
            continue
        p = P[i]
        shift = float(d.get("j", 0.0)) - float(d.get("l", 0.0))
        lo = P[i - 1].get("pic_a", P[i - 1]["out_a"]) + 1.0 / FPS                    # never before the previous shot
        lo = max(lo, p["out_a"] - p["src_a"] / p["speed"])                            # nor before the take's first frame
        hi = p["out_b"] - 1.0 / FPS
        want = p["out_a"] + shift
        got = min(max(want, lo), hi)
        got = round(round(got * FPS) / FPS, 4)                                        # on the frame grid
        if abs(got - want) > 0.5 / FPS:
            print(f"J/L {k['tag']}: {shift:+.2f} s clamped to {got - p['out_a']:+.2f} s (previous shot, take start or piece end)")
        if abs(got - p["out_a"]) < 0.5 / FPS:
            continue
        p["pic_a"] = got
        moves.append({"tag": k["tag"], "out_a": p["out_a"], "pic_a": got})
    if moves:
        print("J/L: " + ", ".join(f"{m['tag']} picture {m['pic_a'] - m['out_a']:+.2f} s" for m in moves))
    edl["jl"] = moves
    return moves


# ------------------------------------------------------------------------------------------------ B-roll
def _file(Fm, f) -> Path:
    p = Path(f)
    return p if p.is_absolute() else (Fm.dir / p)


def _probe(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-show_entries", "format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise SystemExit(f"{p}: no video stream")
    return {"w": int(v["width"]), "h": int(v["height"]), "dur": float(j["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def broll_plan(Fm, edl) -> list:
    """DOC broll -> [{n, file, src, a, b, nf, src_in, speed, audio, gain, duck, grade, vf, label, z}] on the film's
    frame grid (a: its first frame, b = a + nf / FPS), in film order. Times past the film's end are clamped."""
    from kit.film.mix import when
    FPS, total = Fm.FPS, edl["total"]
    out = []
    for n, b in enumerate(Fm.DOC.get("broll") or []):
        src = _file(Fm, b["file"])
        if not src.exists():
            raise SystemExit(f"DOC broll[{n}]: no {src}")
        a = when(edl, b["at"])
        e = when(edl, b["until"]) if "until" in b else a + float(b["dur"])
        a, e = max(0.0, a), min(total, e)
        fa, fb = int(round(a * FPS)), int(round(e * FPS))
        if fb - fa < 1:
            raise SystemExit(f"DOC broll[{n}] ({b['file']}): it lasts no whole frame ({a:.2f}-{e:.2f} s)")
        info = _probe(src)
        sp = float(b.get("speed", 1.0))
        need = float(b.get("src_in", 0.0)) + (fb - fa) / FPS * sp
        if need > info["dur"] + 0.05:
            raise SystemExit(f"DOC broll[{n}] ({b['file']}): needs {need:.2f} s of the clip, it has {info['dur']:.2f} s")
        audio = b.get("audio", "mute")
        if audio == "natural" and not info["audio"]:
            raise SystemExit(f"DOC broll[{n}] ({b['file']}): audio='natural' but the clip has no sound")
        out.append({"n": n, "file": f"broll/b{n:02d}.mp4", "src": str(src), "a": round(fa / FPS, 4), "b": round(fb / FPS, 4), "nf": fb - fa,
                    "src_in": float(b.get("src_in", 0.0)), "speed": sp, "audio": audio, "gain": float(b.get("gain", -8.0)),
                    "duck": float(b.get("duck", 10.0)), "grade": b.get("grade", True), "vf": b.get("vf", ""), "label": b.get("label"),
                    "z": b.get("z", 1), "w": info["w"], "h": info["h"]})
    out.sort(key=lambda x: x["a"])
    return out


def lut(Fm) -> Path | None:
    """The cutaways' grade: the DOC grade look (default "doc") baked as a look v2 LUT, once, into work/."""
    look = Fm.DOC.get("grade", "doc")
    if not look:
        return None
    from kit.paths import ROOT
    p = Fm.work / f"doc_{look}.cube"
    if not p.exists():
        subprocess.run(["python3", str(ROOT / "kit/look/looks.py"), "bake", look, str(p), "--v2", "--size=33"], check=True, cwd=ROOT,
                       capture_output=True)
    return p


def size_for(Fm, w, h) -> tuple[int, int]:
    """A cutaway's frame: the page's aspect, as big as the clip can fill without upscaling (up to 3840 x 2160)."""
    ar = Fm.W / Fm.H
    ch = min(h, w / ar, MAX_H)
    ch = int(ch) // 2 * 2
    return int(round(ch * ar / 2)) * 2, ch


def write_broll(Fm, items) -> list:
    """Each item -> work/broll/b<NN>.mp4: the clip from src_in, cover-cropped to the page's aspect, the doc LUT (unless
    grade=False), on the frame grid (fps=FPS:round=down, exactly nf frames), no audio."""
    d = Fm.work / "broll"
    d.mkdir(parents=True, exist_ok=True)
    cube = lut(Fm)
    for it in items:
        OW, OH = size_for(Fm, it["w"], it["h"])
        chain = (it["vf"] + "," if it["vf"] else "") + f"scale={OW}:{OH}:force_original_aspect_ratio=increase:flags=lanczos,crop={OW}:{OH}"
        if cube and it["grade"]:
            chain += f",lut3d=file='{cube}'"
        sp = it["speed"]
        chain += (f",setpts=PTS/{sp}" if sp != 1.0 else "") + f",fps={Fm.FPS}:round=down,trim=end_frame={it['nf']},setsar=1,format=yuv420p"
        out = Fm.work / it["file"]
        subprocess.run(["nice", "-n", "10", "ffmpeg", "-v", "error", "-y", "-ss", f"{it['src_in']:.4f}", "-t", f"{it['nf'] / Fm.FPS * sp + 0.3:.4f}",
                        "-i", it["src"], "-vf", chain, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(Fm.TRACK_CRF),
                        "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        "-movflags", "+faststart", str(out)], check=True)
        from kit.film.cut import frames
        got = frames(out)
        if got != it["nf"]:
            raise SystemExit(f"{out.name}: {got} frames, want {it['nf']} (the clip ran out: check src_in / dur)")
        it["size"] = [OW, OH]
        print(f"broll b{it['n']:02d} {it['a']:7.2f}-{it['b']:7.2f} s  {Path(it['src']).name} from {it['src_in']:.2f} s -> {OW}x{OH}"
              f"{' graded' if cube and it['grade'] else ''}{', natural sound' if it['audio'] == 'natural' else ''}")
    return items


def natural_sound(Fm, edl, items):
    """The cutaways' natural sound into work/vo.wav (the voice alone kept as work/vo_voice.wav): each clip's own audio at
    `gain` dB, 0.25 s fades, ducked a further `duck` dB (60 ms ramps) where the voice is speaking."""
    nat = [it for it in items if it["audio"] == "natural"]
    vo_p, voice_p = Fm.work / "vo.wav", Fm.work / "vo_voice.wav"
    if not vo_p.exists():
        return
    import shutil
    shutil.copyfile(vo_p, voice_p)                       # the voice alone (joins re-listens this one on a documentary)
    if not nat:
        return
    SR = Fm.SR
    dec = lambda p, *a: np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", *a, "-i", str(p), "-map", "0:a:0", "-ac", "1", "-ar", str(SR),   # noqa: E731
                                                       "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32)
    vo = dec(voice_p).copy()
    n = len(vo)
    fr = SR // 100                                        # the voice's 10 ms RMS: where he speaks
    m = n // fr
    rms = np.sqrt(np.mean(np.square(vo[:m * fr].reshape(m, fr).astype(np.float64)), axis=1)) + 1e-9
    db = 20 * np.log10(rms)
    speech = db > max(db.max() - 30, -50)
    k = np.ones(6) / 6                                    # 60 ms ramps
    speech = np.clip(np.convolve(speech.astype(float), k, mode="same") * 1.5, 0, 1)
    sp_env = np.repeat(speech, fr)[:n]
    sp_env = np.pad(sp_env, (0, n - len(sp_env)), mode="edge")
    add = np.zeros(n, np.float32)
    for it in nat:
        x = dec(it["src"], "-ss", f"{it['src_in']:.4f}", "-t", f"{(it['b'] - it['a']) * it['speed']:.4f}")
        if it["speed"] != 1.0:
            x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af",
                                              f"atempo={it['speed']}", "-f", "f32le", "-"], input=x.tobytes(), capture_output=True,
                                             check=True).stdout, np.float32)
        i0 = int(round(it["a"] * SR))
        x = x[:max(0, min(len(x), n - i0))].astype(np.float32)
        f = min(len(x) // 2, int(0.25 * SR))
        if f:
            ramp = np.linspace(0, 1, f, dtype=np.float32)
            x[:f] *= ramp
            x[-f:] *= ramp[::-1]
        g = 10 ** (it["gain"] / 20) * 10 ** (-it["duck"] * sp_env[i0:i0 + len(x)] / 20)
        add[i0:i0 + len(x)] += x * g.astype(np.float32)
    y = vo + add
    peak = float(np.max(np.abs(y))) if n else 0.0
    if peak > 0.98:
        y *= 0.98 / peak
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s24le", str(vo_p)],
                   input=y.astype(np.float32).tobytes(), check=True)
    print(f"natural sound: {len(nat)} cutaway(s) under the voice -> {vo_p.name} (the voice alone: {voice_p.name})")


def cut(Fm, edl, picture=True):
    """kit/film/cut.py run() calls this after vo.wav (and the tracks): the cutaways' clips, their sound, edl["broll"]."""
    if not on(Fm):
        return
    items = broll_plan(Fm, edl)
    if picture:
        write_broll(Fm, items)
    natural_sound(Fm, edl, items)
    edl["broll"] = [{k: v for k, v in it.items() if k not in ("w", "h")} for it in items]


def voice_wav(Fm) -> Path:
    """The voice-only file the join re-listen should hear: vo_voice.wav on a documentary with natural sound, else vo.wav."""
    p = Fm.work / "vo_voice.wav"
    return p if on(Fm) and p.exists() else Fm.work / "vo.wav"


# ------------------------------------------------------------------------------------------------ the page's data
def page_data(Fm, edl, caps) -> dict:
    """D.doc for kit/hf/doc.js: broll (assets paths and film times), speakers (each source's name and role, and the film
    spans each speaks), chapters, stamps, letterbox spans, subtitles (the caption groups, documentary-styled), results."""
    from kit.film.mix import when
    D = Fm.DOC
    speakers, spans = {}, []
    for c in Fm.SOURCES:
        s = Fm.src(c)
        if s.get("speaker"):
            speakers[str(c)] = {"name": s["speaker"], "role": s.get("role", "")}
    for p in edl["pieces"]:
        key = str(p["clip"])
        a = p.get("pic_a", p["out_a"])
        if spans and spans[-1]["src"] == key:
            continue
        spans.append({"src": key, "a": round(a, 3)})
    for k, s in enumerate(spans):
        s["b"] = spans[k + 1]["a"] if k + 1 < len(spans) else edl["total"]
    lt = D.get("lower_thirds", "first")
    thirds, seen = [], set()
    if lt:
        for s in spans:
            if s["src"] not in speakers or (lt == "first" and s["src"] in seen) or s["b"] - s["a"] < 2.0:
                continue
            seen.add(s["src"])
            thirds.append({"src": s["src"], **speakers[s["src"]], "a": round(s["a"] + 0.6, 3), "b": round(min(s["b"] - 0.3, s["a"] + 4.6), 3)})
    T = lambda v: round(when(edl, v), 3)                                                     # noqa: E731
    return {
        "broll": [{"file": f"assets/{b['file']}", "a": b["a"], "b": b["b"], "label": b.get("label"), "z": b.get("z", 1),
                   "size": b.get("size")} for b in edl.get("broll", [])],
        "speakers": speakers, "spans": spans, "thirds": thirds,
        "chapters": [{"a": T(c["at"]), "dur": float(c.get("dur", 2.4)), "title": c["title"], "sub": c.get("sub", "")}
                     for c in D.get("chapters") or []],
        "stamps": [{"a": T(s["at"]), "dur": float(s.get("dur", 3.0)), "text": s["text"]} for s in D.get("stamps") or []],
        "letterbox": [[T(a), T(b)] for a, b in D.get("letterbox") or []],
        "subtitles": caps if D.get("subtitles", True) else [],
        "results": ({"a": T(D["results"]["at"]), "b": T(D["results"]["until"]), "title": D["results"].get("title", ""),
                     "rows": D["results"].get("rows", [])} if D.get("results") else None),
    }


def copy_fonts(hf: Path):
    """The v2 documentary type (kit/hf/doc.js: condensed names and titles in Oswald) for the page's assets/fonts: a
    documentary-only copy, so no other page's assets change."""
    import shutil
    kit_fonts = Path(__file__).resolve().parents[1] / "fonts"
    (hf / "assets/fonts").mkdir(parents=True, exist_ok=True)
    for w in (500, 600, 700):
        shutil.copy2(kit_fonts / f"Oswald-{w}.ttf", hf / "assets/fonts" / f"Oswald-{w}.ttf")


def link_broll(Fm, edl, assets: Path):
    """Hard-link each cutaway into the page's assets/broll/ (kit/film/build.py link)."""
    from kit.film.build import link
    for b in edl.get("broll", []):
        link(Fm.work / b["file"], assets / b["file"])
