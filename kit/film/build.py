"""The page: the film's template with the kit inlined (kit/hf/vendor.py) and the cut's data, staged as a HyperFrames
project in F.hf; the words on screen (spellings, respelled text placed on its sound); captions.srt; the page's sound
cues; precheck (the defect and ambition gate, OWNER_DEFAULTS §8).

MOUNTS (film.py) are HyperFrames catalog pieces (kit/hf/catalog), written into the page's root composition as static
sub-compositions (kit/hf/mounts.py: a mount made by the page's script is never rendered).
The template gets D = { total, talk, pieces, words, caps, tracks, lens, faces?, music?, ...DATA } at /*DATA*/ (music: the
MUSIC beds' beats, downbeats and sections in film time, kit/film/mix.py music_map, read by HF.music; tracks: each picture
track's file and its zoom budget from work/tracks.json; lens: the camera on him, HF.motion.lens, with LENS / STRESS, the
visual plan's cam and its eyes, lens.faces: the face track per output frame in that track's px; faces: a Reel's edl
faces, page px, for HF.reel's box), and __TOTAL__ /
__TALK__ / __END-<s>__ (the total minus s: a closing clip's static data-start, memory hf-kit-gotchas 12) in its text.
Each picture track is assets/<name>.mp4 (a hard link to work/<name>.mp4), so a static
<video id="aroll" src="assets/aroll.mp4" data-start="0" data-duration="__TOTAL__" ...> plays the cut.

    uv run python -m kit.film <film> build | cues | precheck | snap --at=3,12.5
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

from kit.paths import ROOT

sys.path.insert(0, str(ROOT / "kit/hf"))
import vendor  # noqa: E402

CUES_JS = ROOT / "kit/presets/paper_studio/example/cues.mjs"
ENV = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1")


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd)[:220], flush=True)
    return subprocess.run([str(c) for c in cmd], **kw)


def link(src, dst):
    """The big media in the HF project are hard links (no second copy)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_ino == src.stat().st_ino:
        return
    dst.unlink(missing_ok=True)
    os.link(src, dst)


# ---------------------------------------------------------------- the words on screen
def respelled(Fm, edl):
    """RESPELL texts placed on their own sound (kit/cut/respell.py place(): a forced alignment of the whole text on the
    range's cleaned voice; ranges that follow each other in one take aligned as one run; a crowded slot spills only
    inside its own piece). -> ({edit id: text}, {edit id: (t, e) on the film}). Cached in work/words_respelled.json
    until edl.json or the texts change. From films/reverse-engineer/shorts/cut.py film_respelled() (2026-10-18: an
    even spread put captions up to 1.5 s off)."""
    if not Fm.RESPELL:
        return {}, {}
    key = hashlib.sha1(json.dumps({str(k): v for k, v in Fm.RESPELL.items()}, sort_keys=True).encode()).hexdigest()[:12]
    stamp = f"{Fm.edl_path.stat().st_mtime}-{key}"
    cache = Fm.work / "words_respelled.json"
    if cache.exists():
        c = json.loads(cache.read_text())
        if c.get("stamp") == stamp:
            return {int(k): v for k, v in c["text"].items()}, {int(k): tuple(v) for k, v in c["times"].items()}
    from kit.cut.respell import place
    from kit.film.cut import voice
    from shorts.analyze.align import Aligner, load_vocab
    al, vocab = Aligner(), load_vocab()
    have = {w["i"] for w in edl["words"]}
    piece_of = {}
    for p in edl["pieces"]:
        for i in range(p["w"][0], p["w"][1] + 1):
            piece_of.setdefault(i, p)
    def norm(k):                                   # (src, first, last[, "copy"]), or (first, last[, "copy"]) with one source
        copy, k = "copy" in k, [x for x in k if x != "copy"]
        return (next(iter(Fm.SOURCES)), k[0], k[1], copy) if len(k) == 2 else (k[0], k[1], k[2], copy)
    keys = sorted(Fm.RESPELL, key=lambda k: (str(norm(k)[0]), norm(k)[3], norm(k)[1]))
    runs = []
    for k in keys:
        c, a, b, copy = norm(k)
        if runs and norm(runs[-1][-1])[0] == c and norm(runs[-1][-1])[3] == copy and norm(runs[-1][-1])[2] + 1 == a:
            runs[-1].append(k)
        else:
            runs.append([k])
    v16, words, texts, times = {}, {}, {}, {}
    for r in runs:
        c, _, _, copy = norm(r[0])
        ids = [i for k in r for i in range(norm(k)[1], norm(k)[2] + 1)]
        eids = [Fm.eid(c, i, copy) for i in ids]
        if not any(e in have for e in eids):
            continue                                            # ranges the cut no longer keeps
        if c not in v16:
            words[c] = Fm.words(c)
            v16[c] = voice(Fm, c, sr=16000)
        W = words[c]
        slots = [(W[i]["start"], W[i]["end"]) for i in ids]
        nxt = W[ids[-1] + 1]["start"] if ids[-1] + 1 < len(W) else slots[-1][1] + 1.5
        t0, t1 = max(0.0, slots[0][0] - 0.4), min(slots[-1][1] + 1.5, max(slots[-1][1] + 0.3, nxt + 0.15))
        grp = [id(piece_of[e]) if e in piece_of else -1 for e in eids]
        tx, tm = place(" ".join(Fm.RESPELL[k] for k in r), v16[c][int(t0 * 16000):int(t1 * 16000)], t0, slots, al, vocab, group=grp)
        for e, s_, m in zip(eids, tx, tm):
            if e not in have:
                continue
            texts[e] = s_
            p = piece_of.get(e)
            if m and p:
                sp = p.get("speed", 1.0) or 1.0
                fa = min(max(p["out_a"] + (m[0] - p["src_a"]) / sp, p["out_a"]), p["out_b"] - 0.03)
                fb = min(p["out_b"], max(p["out_a"] + (m[1] - p["src_a"]) / sp, fa + 0.03))
                times[e] = (round(fa, 3), round(fb, 3))
    cache.write_text(json.dumps({"stamp": stamp, "text": {str(k): v for k, v in texts.items()}, "times": {str(k): v for k, v in times.items()}}))
    print(f"respelled: {len(texts)} words placed ({len(times)} re-timed on their sound)")
    return texts, times


def fixed_words(Fm, edl):
    """The cut's words as shown: RESPELL text (and its measured times), then TEXT (one word; "" hides it), then SPELL."""
    texts, times = respelled(Fm, edl)
    out = []
    for w in edl["words"]:
        w = dict(w)
        if w["i"] in texts:
            w["text"] = texts[w["i"]]
        if w["i"] in times:
            w["t"], w["e"] = times[w["i"]]
        if w["i"] in Fm.TEXT:
            w["text"] = Fm.TEXT[w["i"]]
        elif w["text"] in Fm.SPELL:
            w["text"] = Fm.SPELL[w["text"]]
        out.append(w)
    return out


def caption_groups(Fm, words):
    """[{t, e, ids, text}]: a caption ends at a sentence end, at CAPTIONS chars, at a pause or after `span` s
    (films/xchakra and films/ai-workflows build.py); each starts on its first word and ends just before the next."""
    cfg = {**dict(chars=42, pause=0.6, span=3.2), **(Fm.CAPTIONS or {})}
    caps, cur = [], []
    for w in [w for w in words if w["text"]]:
        if cur and (len(" ".join(x["text"] for x in cur + [w])) > cfg["chars"] or w["t"] - cur[-1]["e"] > cfg["pause"]
                    or w["e"] - cur[0]["t"] > cfg["span"]):
            caps.append(cur)
            cur = []
        cur.append(w)
        if w["text"].endswith((".", "?", "!", '."', '?"', "!\"")):
            caps.append(cur)
            cur = []
    if cur:
        caps.append(cur)
    out, prev = [], 0.0
    for k, c in enumerate(caps):
        a = max(c[0]["t"], prev + 0.02)
        b = min(c[-1]["e"] + 0.25, caps[k + 1][0]["t"] - 0.02) if k + 1 < len(caps) else c[-1]["e"] + 0.4
        b = max(b, a + 0.4)
        out.append({"t": round(a, 3), "e": round(b, 3), "ids": [x["i"] for x in c], "text": " ".join(x["text"] for x in c)})
        prev = b
    return out


def srt(Fm, caps):
    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    p = Fm.F.final / Fm.CAPTIONS_FILE
    p.write_text("\n".join(f"{k + 1}\n{ts(c['t'])} --> {ts(c['e'])}\n{c['text']}\n" for k, c in enumerate(caps)))
    print(f"-> {p}: {len(caps)} captions")


# ---------------------------------------------------------------- the camera on him (2026-10-22, kit v11)
CAMS = {"push", "pull", "punch", "arc", "drift", "hold"}   # kit/hf/plan_check.py's: the lens on him, one move per passage


def track_data(Fm, files: dict) -> dict:
    """D.tracks (the tracks.json contract): {name: {"file": "assets/<name>.mp4", w, h, src_w, src_h, max_zoom, ...}}: each
    picture track's file and what work/tracks.json (kit/film/cut.py write_tracks) says about its zoom budget. A track
    the cut wrote no entry for has its file only (the page's lens then caps at 1.2, precheck the same)."""
    p = Fm.work / "tracks.json"
    info = json.loads(p.read_text()) if p.exists() else {}
    return {name: {"file": f, **(info.get(name) or {})} for name, f in files.items()}


def plan_rows(Fm, words: list) -> tuple[list, list]:
    """The visual plan's camera (schema 2: a passage's "cam", kit/hf/plan_check.py) for the lens, timed on the cut's words:
    ([{a, b, cam, punch?}], [punch word ids]). A passage is timed by its "t": [a, b] or its "words": [first, last] (edit
    ids, their spoken times); "punch": <word id> names the word a cam "punch" lands on, and a beat {"at": <id>,
    "punch": true} adds a punch word anywhere. A plan the cut can't time (or none) gives nothing."""
    vp = Fm.dir / "visual_plan.json"
    if not vp.exists():
        return [], []
    try:
        plan = json.loads(vp.read_text())
    except ValueError:
        return [], []
    have = {w["i"]: w for w in words}
    rows, punch = [], []
    for p in plan.get("passages") or []:
        sp = None
        if isinstance(p.get("t"), list) and len(p["t"]) == 2:
            sp = (float(p["t"][0]), float(p["t"][1]))
        elif isinstance(p.get("words"), list) and len(p["words"]) == 2 and p["words"][0] in have and p["words"][1] in have:
            sp = (have[p["words"][0]]["t"], have[p["words"][1]]["e"])
        for b in p.get("beats") or []:
            if isinstance(b, dict) and b.get("punch") and b.get("at") in have:
                punch.append(b["at"])
        if not sp or p.get("cam") not in CAMS:
            continue
        row = {"a": round(sp[0], 3), "b": round(sp[1], 3), "cam": p["cam"]}
        if p.get("punch") in have:
            row["punch"] = p["punch"]
        rows.append(row)
    return rows, punch


def lens_faces(Fm, edl: dict):
    """The face track per output frame in the FACE TRACK's own px ([cx, cy, size] | None per frame), and that track's
    size [w, h]: the lens's eyes (D.lens.faces / faces_px; canvas.js scales them to its <video>'s fo.src). A film reads
    work/<FACE_TRACK>.face.json (YuNet on the cut track, its px). A Reel's edl faces are in the FILM's page px
    (kit/film/reels.py scales the film's track by film.W / track_w for HF.reel's box), so they are divided back
    (review 2026-10-22: read as track px, a Reel's lens anchored x1.78 off and __faceRect missed his face). D.faces
    keeps the edl's own (page px) for HF.reel. -> (None, None) without a face track."""
    size = (edl.get("tracks") or {}).get(Fm.FACE_TRACK)
    if getattr(Fm, "reel", None):
        if not edl.get("faces"):
            return None, None
        s = Fm.parent.W / size[0] if size else 1.0
        return [[round(v / s, 1) for v in f[:3]] if f else None for f in edl["faces"]], list(size) if size else None
    fp = Fm.work / f"{Fm.FACE_TRACK}.face.json"
    if not fp.exists():
        return None, None
    return [[round(float(v), 1) for v in f[:3]] if f else None for f in json.loads(fp.read_text())], list(size) if size else None


def lens_why(Fm) -> tuple[bool, str]:
    """(on, why): is the lens on for this film or Reel. LENS in film.py (or lens= in a REELS entry) wins when it is set:
    True / False, or any dict (an empty one included) for on with its calm / budget / rules. Unset (None, the config
    default since 2026-10-22): on only for a film made on or after kit/film/mix.py's V11_FROM (made_on: git's first
    commit of film.py, a Reel's own template.html), the same date gate as the v11 sound, so a rebuild of a film delivered
    before v11 (oss-editor, kit-v10-sample, ai-video-editor, xchakra and their Reels) adds no lens moves to it
    (OWNER_DEFAULTS §7: old videos are not re-edited unless he asks; review 2026-10-22, E-M3)."""
    cfg = getattr(Fm, "LENS", None)
    if cfg is not None:
        return isinstance(cfg, dict) or bool(cfg), "LENS in film.py"
    from kit.film.mix import V11_FROM, made_on      # read-only: the sound's gate (kit/film/mix.py is sound's)
    d = made_on(Fm)
    return d >= V11_FROM, f"made on {d}, v11 from {V11_FROM}"


def lens_data(Fm, words: list) -> dict:
    """D.lens: the camera on him (kit/hf/motion.js HF.motion.lens; HF.canvas speakers on FACE_TRACK and HF.box read it).
    {on, track (FACE_TRACK: the speaker / tracks.json entry it moves), fps, calm?, budget?, rules?, stress (punch word
    ids: film.py STRESS + the plan's punch beats), plan (the visual plan's cam per passage)}; build() adds faces /
    faces_px (lens_faces). On or off by lens_why: LENS in film.py when set (False / 0 off; True or any dict LENS, an
    empty one included, on with its calm / budget / rules), else by the film's date (V11_FROM)."""
    on, why = lens_why(Fm)
    print(f"lens: {'on' if on else 'off'} ({why})")
    cfg = getattr(Fm, "LENS", None)
    out = {"on": on, "track": Fm.FACE_TRACK, "fps": Fm.FPS}
    if not on:
        return out
    if isinstance(cfg, dict):
        out.update({k: cfg[k] for k in ("calm", "budget", "rules", "track") if k in cfg})
    have = {w["i"] for w in words}
    rows, punch = plan_rows(Fm, words)
    out["stress"] = list(dict.fromkeys(i for i in [*getattr(Fm, "STRESS", []), *punch] if i in have))
    out["plan"] = rows
    return out


# ---------------------------------------------------------------- the page
def build(Fm):
    edl = Fm.edl()
    F = Fm.F
    F.stage()
    if not (F.hf / "hyperframes.json").exists():
        (F.hf / "hyperframes.json").write_text(json.dumps({"name": F.name, "paths": {"assets": "assets"}}) + "\n")
    vendor.copy_assets(F.hf)
    tracks = {}
    for name in edl.get("tracks", {}):
        src, why = Fm.track_file(name)
        if not src.exists():
            raise SystemExit(f"no {src}: run the cut first")
        if why:
            print("NOTE:", why, "(this page shows the ungraded cut)")
        link(src, F.assets / f"{name}.mp4")
        tracks[name] = f"assets/{name}.mp4"
    words = fixed_words(Fm, edl)
    caps = caption_groups(Fm, words)
    total = edl["total"]
    D = {"total": total, "talk": edl["talk_end"], "pieces": edl["pieces"], "words": words, "caps": caps,
         "tracks": track_data(Fm, tracks), "lens": lens_data(Fm, words)}
    if edl.get("faces"):
        D["faces"] = edl["faces"]
    if D["lens"]["on"]:                            # the lens anchors on his eyes: the face track per output frame, its px
        faces, px = lens_faces(Fm, edl)
        if faces:
            D["lens"].update({"faces": faces, "faces_px": px} if px else {"faces": faces})
    if Fm.MUSIC:                                   # the beds' beats, downbeats and sections in film time (HF.music)
        from kit.film import mix as MX
        D["music"] = MX.music_map(Fm, edl)
    from kit.film import doc                       # the documentary preset only (PRESET = "documentary"): D.doc for kit/hf/doc.js
    if doc.on(Fm):
        doc.link_broll(Fm, edl, F.assets)
        doc.copy_fonts(F.hf)
        D["doc"] = doc.page_data(Fm, edl, caps)
    D.update(Fm.DATA)
    tpl = Fm.template.read_text()
    if Fm.MOUNTS:                                  # catalog pieces, written into the root composition (kit/hf/mounts.py)
        import mounts
        from kit.film.mix import when
        tpl = mounts.install(F.hf, Fm.MOUNTS, [when(edl, m["at"]) for m in Fm.MOUNTS], tpl)
        print(f"mounts: {', '.join(m['name'] for m in Fm.MOUNTS)} ({mounts.look_of(tpl)} look)")
    html = vendor.inline(tpl, stickman=Fm.STICKMAN)
    html = html.replace("/*DATA*/", "const D = " + json.dumps(D) + ";").replace("__TOTAL__", f"{total}").replace("__TALK__", f"{edl['talk_end']}")
    html = re.sub(r"__END-([0-9.]+)__", lambda m: f"{total - float(m.group(1)):.4f}", html)
    (F.hf / "index.html").write_text(html)
    credits(Fm, tpl)                               # the film's own template: the inlined kit mentions HF.emoji in its docs
    print(f"-> {F.hf / 'index.html'}: {len(edl['pieces'])} pieces, {len(words)} words, {len(caps)} captions, total {total:.2f} s")
    srt(Fm, caps)
    return F.hf


def credits(Fm, html):
    """output/final/<film>/credits.txt: every credit the film owes, to paste into the description: the MUSIC beds whose
    licence asks for one (kit/music/library.json "credit") and the animated emoji (Noto, CC BY 4.0) when the page uses any."""
    lib = {t["file"]: t for t in json.loads((ROOT / "kit/music/library.json").read_text())}
    lines = []
    for m in Fm.MUSIC:
        t = lib.get("music/" + m["file"])
        if t and "none" not in t["credit"].lower() and t["credit"] not in lines:
            lines.append(t["credit"])
    if vendor.emoji_used(html):
        lines.append("Animated emoji: Google Noto Emoji (CC BY 4.0)")
    out = Fm.F.final / (f"reel_{Fm.reel}_credits.txt" if Fm.reel else "credits.txt")   # a Reel shares the film's final folder
    if lines:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n\n".join(lines) + "\n")
        print(f"credits: {len(lines)} -> {out} (paste into the description)")
    elif out.exists():
        out.unlink()


def lint(Fm):
    r = run(["npx", "hyperframes", "lint", Fm.F.hf], cwd=ROOT, env=ENV, capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-600:])
    return r.returncode


def cues(Fm):
    """The page's sound cues (sfx() calls) -> work/cues.json, plus cues.holds.json (declared holds) and cues.quiet.json
    (where the music steps back). The page needs at least one cue (cues.mjs waits for one)."""
    out = Fm.work / "cues.json"
    r = run(["node", CUES_JS, Fm.F.hf / "index.html", out], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr.strip()[-400:])
    if r.returncode or "ERRORS" in r.stdout:
        raise SystemExit("cues: page errors (above): fix the template")
    return out


def precheck(Fm, force=False, ambition=True):
    """kit/qa/precheck.mjs on the page (defects + ambition, OWNER_DEFAULTS §8). A HIGH stops the draft unless --force."""
    js = Fm.work / "precheck.json"
    r = run(["node", ROOT / "kit/qa/precheck.mjs", Fm.F.hf / "index.html", "--fps=5", f"--holds-out={Fm.work / 'holds.json'}",
             f"--json={js}"] + ([] if ambition else ["--no-ambition"]) + (["--doc"] if getattr(Fm, "PRESET", None) == "documentary" else []), cwd=ROOT, capture_output=True, text=True)
    print(precheck_text(r.stdout), r.stderr[-400:])
    if r.returncode == 3 and not force:
        raise SystemExit(f"precheck: HIGH findings (above; every finding in {js}). Fix the template, or pass --force to go on anyway")
    return r.returncode


def precheck_text(out: str, tail: int = 2500) -> str:
    """What build.precheck prints of precheck.mjs's stdout: its verdict line ('FAIL: ...' / 'WARN: ...' / 'PASS: ...',
    the first line after the holds note; else the first line), every HIGH finding in full ('  HIGH ' lines), then the
    tail. A long-form page's stdout ran past the old 3500-char tail, which cut the FAIL header and the HIGH texts off
    (the closing summary line names at most 3 a kind; review 2026-10-22, E-S4)."""
    lines = out.splitlines()
    if len(out) <= tail or not lines:
        return out
    verdict = next((x for x in lines if re.match(r"(FAIL|WARN|PASS): ", x)), lines[0])
    head = [verdict] + [x for x in lines if x.startswith("  HIGH ")]
    rest = out[-tail:]
    rest = rest[rest.find("\n") + 1:] if "\n" in rest else rest          # from a whole line
    return "\n".join(head) + "\n  ...\n" + rest


def snap(Fm, times):
    out = Fm.F.renders / "snap"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    r = run(["npx", "hyperframes", "snapshot", Fm.F.hf, "-o", out, "--no-end", "--describe", "false", "--at", ",".join(f"{t}" for t in sorted(times))],
            cwd=ROOT, env=ENV, capture_output=True, text=True)
    print(r.stdout[-800:], r.stderr[-800:])
    return out
