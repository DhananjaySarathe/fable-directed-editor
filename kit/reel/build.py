"""Build, render and check a Reel (kit/reel). The page is the film's src/template.html with the kit inlined (kit/hf, plus
reel.js); the data it gets is D = { total, talk, words, pieces, faces, ...R.DATA }.

  build(R, sample)   cut-outs, assets (aroll, the film's assets/), index.html  (sample: output/temp/films/<name>/hf_sample,
                     the same page cut to R.SAMPLE seconds)
  render(R, sample)  lint -> cues (headless Chrome) -> precheck (layout, phone-readable text, reading holds; its
                     ambition gates on for Reels made from 2026-10-22) -> mix (kit/audio/mix.py: voice + beds + cues +
                     quiet moments, -14 LUFS; work/music.json) -> HyperFrames render (1080x1920, 30 fps, delivery) ->
                     mux (-aac_pns 0) -> kit/qa/qa.py (--music on the v11 sound). Returns qa's exit code.
  snap(R, times)     snapshots of the built page at the given times (renders/snap/) for a look before rendering

MUSIC beds in reel.py: [dict(file="upbeat/....mp3", a=0 or "w205", b="end" or "w205", drop=52.5, at="w135",
under=-12, gap=-5)] -- a/b/at take seconds or "w<id>" (that word's start on the cut); drop+at line the track's drop up
with that moment (start = drop - (at - a)); or give start= (track seconds at a) directly (snapped to a downbeat), or
drop="auto" / "section:N" from the music map (kit/film/mix.py resolve, kit/music/beats.json). end_fade= on the last bed:
its fade at the end (default 2.5 s, kit/audio/mix.py), ~0.4 for a Short that ends on its drop.

The sound (2026-10-22): a Reel made from kit/film/mix.py's V11_FROM mixes with the v11 sound, as a Reel cut from a
film does (sound()): SOUND = "v10" | "v11" in reel.py wins; else the sound its last full mix recorded in
work/music.json (sticky: editing or copying the Reel never flips it); else the day its src/template.html was made
(made_on). Older Reels mix exactly as before. On v11 kit/film/mix.py plans the beds (music_plan): every bed ducks on
the voice (duck="voice", gap = under + 6: -12 / -6), a track that runs out loops on its own phrases (loop=False turns it
off; the seams' times are printed: listen to each), the visual plan's stop / riser / drop are played, SFX families
rotate and the Reel budget holds (12 small cues a minute, no file over 25 % or 4 a minute; kit/audio/mix.py V11_REEL).
Beds change with v10's quick crossfade (Reels change on drops). The mix writes work/music.json (music_sample.json for
a sample): the sound, the beds and seams, the measured mix and the findings qa.py --music reports.
"""
import json
import re
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kit/hf"))
import vendor  # noqa: E402

MUSIC_DIR = ROOT / "kit/music"


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd)[:200], flush=True)
    return subprocess.run([str(c) for c in cmd], **kw)


def link(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_ino == src.stat().st_ino:
        return
    dst.unlink(missing_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def edl_of(R):
    return json.loads((R.dir / "edl.json").read_text())


def wtime(edl, v):
    if isinstance(v, str) and v.startswith("w"):
        i = int(v[1:])
        return next(w["t"] for w in edl["words"] if w["i"] == i)
    if v == "end":
        return edl["total"]
    if isinstance(v, str) and v.startswith("end-"):        # "end-7.25": that many seconds before the end (a closing clip's bed)
        return edl["total"] - float(v[4:])
    return float(v)


def smooth_faces(R, edl, sec=0.6):
    """The per-frame face track of the cut, smoothed (a handheld selfie: the box frames the face, not the shake)."""
    tr = np.array(json.load(open(R.work / "aroll.track.json")), np.float32)
    k = max(1, int(sec * R.FPS)) | 1
    pad = np.pad(tr, ((k // 2, k // 2), (0, 0)), mode="edge")
    ker = np.ones(k) / k
    sm = np.stack([np.convolve(pad[:, j], ker, mode="valid") for j in range(tr.shape[1])], 1)
    # a jump cut is a new shot: never smooth across a cut
    for p in edl["pieces"]:
        f0 = int(round(p["out_a"] * R.FPS))
        if 0 < f0 < len(tr):
            for f in range(f0, min(len(tr), f0 + k // 2)):
                sm[f] = tr[f0:min(len(tr), f0 + k // 2)].mean(0)
            for f in range(max(0, f0 - k // 2), f0):
                sm[f] = tr[max(0, f0 - k // 2):f0].mean(0)
    return [[round(float(a), 1) for a in r] for r in sm]


def choke(m):
    """The person matte (0..1) choked 3 px and feathered: the cut-out's default edge."""
    import cv2
    mf = cv2.erode(m, np.ones((7, 7), np.uint8))
    return np.clip((cv2.GaussianBlur(mf, (0, 0), 2.0) - 0.12) / 0.88, 0, 1) ** 1.4


def refine_edge(rgb, m, deep=26, ring=3, sig=14):
    """CUTOUT_REFINE: the person matte runs 10-20 px into a bright wall at the shoulders and around the hair, which glows
    on a dark background. Within `deep` px of its edge each pixel is re-judged on the picture where he is clearly darker
    than the wall behind (hair, a dark shirt): by where it sits between his colour and the wall's next to it (a mix is
    partly him; a colour off that line, e.g. a lit fold, is his). Elsewhere (skin on a pale wall) the choked matte stays:
    re-cutting there bit rim-lit cheeks, and a colour-difference rule made notches and blocks (2026-10-18). Partial pixels
    take his interior colour. A plum curtain inside the edge (judged against the backdrop next to it, so his lips in
    profile against a wall are safe) is cut out. -> (alpha, rgb)"""
    import cv2
    img = rgb.astype(np.float32)
    hard = (m > 0.5).astype(np.uint8)
    d_in = cv2.distanceTransform(hard, cv2.DIST_L2, 3)
    inner = (d_in > deep).astype(np.float32)
    outer = (cv2.distanceTransform(1 - hard, cv2.DIST_L2, 3) > ring).astype(np.float32)

    def fill(mask):                              # the mask's colours carried into the band (a normalised blur)
        den = cv2.GaussianBlur(mask, (0, 0), sig)
        return cv2.GaussianBlur(img * mask[..., None], (0, 0), sig) / np.maximum(den, 1e-4)[..., None], den
    fg, fd = fill(inner)
    bg, bd = fill(outer)
    d = fg - bg
    t = ((img - bg) * d).sum(2) / np.maximum((d * d).sum(2), 1.0)
    perp = np.sqrt(((img - bg - t[..., None] * d) ** 2).sum(2))
    a_line = np.maximum(np.clip(t, 0, 1), np.clip((perp - 25) / 30, 0, 1))
    conf = np.clip((bg.mean(2) - fg.mean(2) - 25) / 35, 0, 1) * np.clip(bd / 0.05, 0, 1) * np.clip(fd / 0.05, 0, 1)
    band = (1 - inner) * (1 - outer)
    plum = lambda c: np.clip((np.minimum(c[..., 0], c[..., 2]) - c[..., 1] - 2) / 6, 0, 1)   # green under red and blue
    curtain = cv2.GaussianBlur(band * plum(img) * plum(bg), (0, 0), 2.0)   # a plum curtain behind him inside the matte's edge: backdrop
    a = np.clip(cv2.GaussianBlur((inner + band * (conf * a_line + (1 - conf) * choke(m))) * (1 - curtain), (0, 0), 1.2), 0, 1)
    keep = np.clip((a - 0.85) / 0.1, 0, 1)[..., None]
    out = img * keep + fg * (1 - keep)
    rb = np.minimum(out[..., 0], out[..., 2])           # what is left of it near the edge turns warm grey (hair-like)
    out[..., 1] += (rb - out[..., 1]) * plum(out) * plum(bg) * np.clip((deep + 8 - d_in) / 8, 0, 1)
    return a, np.clip(out, 0, 255).astype(np.uint8)


def dull_room(rgb, a, o, vig):
    """BG_DULL: him as shot, the room behind him dulled (blurred, desaturated, darkened, fading to black toward the frame's
    top and sides), so he stays in his own room instead of a cut-out on a new background (the owner, 2026-10-19: "dull
    the bg a lot but not remove"). The matte is choked and blurred wide for this, so where it runs into the wall the
    room's dulling rolls off across his outermost pixels instead of leaving a bright rim. o: ev, sat, blur, choke, feather."""
    import cv2
    img = rgb.astype(np.float32)
    room = cv2.GaussianBlur(img, (0, 0), o.get("blur", 5)) if o.get("blur", 5) else img
    luma = (room * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2, keepdims=True)
    room = (luma + (room - luma) * o.get("sat", 0.25)) * (2 ** o.get("ev", -1.7)) * vig[..., None]
    k = int(o.get("choke", 8)) * 2 + 1
    m = cv2.GaussianBlur(cv2.erode(a, np.ones((k, k), np.uint8)), (0, 0), o.get("feather", 12))[..., None]
    return np.clip(img * m + room * (1 - m), 0, 255).astype(np.uint8)


def cutouts(R, edl):
    """One transparent VP9 WebM per CUTOUTS tag span: the cut A-roll's graded frames with the source frame's person
    matte (edges choked and feathered). Returns {tag: (file, start, dur)}."""
    if not R.CUTOUTS:
        return {}
    import cv2
    FPS = R.FPS
    amap = json.load(open(R.work / "aroll.map.json"))
    res = {}
    for tag in R.CUTOUTS:
        if tag == "all":                     # the whole Reel (type behind the speaker, a corner cut-out on takeovers)
            a, b = 0.0, round(edl["total"], 4)
        else:
            ps = [p for p in edl["pieces"] if p["tag"] == tag]
            a, b = round(max(0.0, ps[0]["out_a"] - 0.5), 4), round(min(edl["total"], ps[-1]["out_b"] + 0.4), 4)
        out = R.work / f"cutout_{tag}.webm"
        res[tag] = (out, a, round(b - a, 4))
        if out.exists() and out.stat().st_mtime > (R.work / "aroll.mp4").stat().st_mtime:
            continue
        k0, k1 = int(round(a * FPS)), int(round(b * FPS))
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{R.W}x{R.H}", "-r", str(FPS),
                                "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "26", "-row-mt", "1",
                                "-deadline", "good", "-cpu-used", "4", "-auto-alt-ref", "0", str(out)], stdin=subprocess.PIPE)
        # half a frame BEFORE frame k0 (as write_picture does): +0.5 dropped frame k0, so every WebM frame was the next
        # A-roll frame: the picture ran a frame ahead of the page (each cut a frame before its reframe) and each matte sat
        # on the following frame's picture (a ghost of the room on fast moves) - found 2026-10-19
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, (k0 - 0.5) / FPS):.5f}", "-i", str(R.work / "aroll.mp4"), "-frames:v",
                                str(k1 - k0), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        prev = vig = None
        xx = np.arange(R.W, dtype=np.float32)[None, :]
        yy = np.arange(R.H, dtype=np.float32)[:, None]
        border = np.clip(np.minimum(xx, R.W - 1 - xx) / 90.0, 0, 1) * np.clip((R.H - 1 - yy) / 60.0, 0, 1)
        for k in range(k0, k1):
            buf = dec.stdout.read(R.W * R.H * 3)
            if len(buf) < R.W * R.H * 3:
                break
            rgb = np.frombuffer(buf, np.uint8).reshape(R.H, R.W, 3)
            m = cv2.imread(str(R.work / "matte" / f"f{amap[min(k, len(amap) - 1)] + 1:05d}.png"), cv2.IMREAD_GRAYSCALE)
            m = cv2.resize(m, (R.W, R.H)) if m.shape != (R.H, R.W) else m
            shot = rgb
            if R.CUTOUT_REFINE:
                mf, rgb = refine_edge(rgb, m.astype(np.float32) / 255)
            else:
                mf = choke(m.astype(np.float32) / 255)
            # edge flicker is smoothed with the frame before; a big change (he moved fast, or the take jumps at a cut) is
            # taken as it is: blending it left a grey ghost of the room where his head had been (critic 2026-10-18)
            jump = k > k0 and amap[min(k, len(amap) - 1)] - amap[min(k - 1, len(amap) - 1)] not in (0, 1)
            if prev is not None and not jump:
                mf = np.where(np.abs(mf - prev) < 0.5, 0.65 * mf + 0.35 * prev, mf)
            prev = mf
            if R.BG_DULL:                       # the room stays, dulled: an opaque frame (only the frame's own edges fade)
                if vig is None:
                    top, side = R.BG_DULL.get("top", 480), R.BG_DULL.get("side", 200)
                    ss = lambda u: u * u * (3 - 2 * u)
                    vig = (ss(np.clip(yy / top, 0, 1)) * ss(np.clip(np.minimum(xx, R.W - 1 - xx) / side, 0, 1))).astype(np.float32)
                rgb = dull_room(shot, mf, R.BG_DULL, vig)
                mf = np.ones_like(mf)
            enc.stdin.write(np.dstack([rgb, np.clip(mf * border * 255 + 0.5, 0, 255).astype(np.uint8)]).tobytes())
        dec.stdout.close(); dec.wait()
        enc.stdin.close(); enc.wait()
        print(f"cut-out {tag}: {a:.2f}+{b - a:.2f} s -> {out.name}")
    return res


def hf_dir(R, sample):
    return R.F.temp / ("hf_sample" if sample else "hf")


def build(R, sample=False):
    edl = edl_of(R)
    total = min(edl["total"], R.SAMPLE) if sample else edl["total"]
    hf = hf_dir(R, sample)
    if sample:
        shutil.rmtree(hf, ignore_errors=True)
    hf.mkdir(parents=True, exist_ok=True)
    (hf / "hyperframes.json").write_text(json.dumps({"name": R.F.name, "version": 1}))
    vendor.copy_assets(hf)
    if (R.dir / "assets").is_dir():
        shutil.copytree(R.dir / "assets", hf / "assets", dirs_exist_ok=True)
    aroll = R.work / "aroll.mp4"
    if R.HIDE:                                   # a bystander hidden (kit/reel/hide.py): use the baked A-roll, never a stale one
        hid = R.work / "aroll_hidden.mp4"
        if not hid.exists() or hid.stat().st_mtime < aroll.stat().st_mtime:
            raise SystemExit(f"{R.dir.name}: HIDE is set but {hid.name} is missing or older than aroll.mp4: run the `hide` step")
        aroll = hid
    link(aroll, hf / "assets/aroll.mp4")
    co = cutouts(R, edl)
    for tag, (p, a, d) in co.items():
        link(p, hf / "assets" / p.name)
    D = {"total": round(total, 4), "talk": min(edl["talk_end"], total), "full_total": edl["total"], "words": edl["words"],
         "pieces": edl["pieces"], "faces": smooth_faces(R, edl), "sample": bool(sample),
         "cutouts": {t: {"src": f"assets/{p.name}", "start": a, "dur": d} for t, (p, a, d) in co.items()}}
    # tracked points (kit/reel/track.py: work/track_<name>.json) -> D.tracks.<name>
    D["tracks"] = {f.stem[6:]: json.loads(f.read_text()) for f in sorted(R.work.glob("track_*.json"))}
    D.update(R.DATA)
    mods = vendor.MODULES
    vendor.MODULES = mods + [m for m in ("reel.js", "footage.js", "agent.js", "night_reel.js") if m not in mods]
    try:
        html = vendor.inline((R.dir / "src/template.html").read_text(), stickman=False)
    finally:
        vendor.MODULES = mods
    html = html.replace("/*DATA*/", "const D = " + json.dumps(D) + ";").replace("__TOTAL__", f"{total}").replace("__AROLL__", f"{edl['total']}")
    # "__END-7.25__": that many seconds before the end, for a clip's static data-start (the renderer reads media timing from
    # the HTML attributes, not from a script that changes them: a clip timed in JS rendered black, 2026-10-19)
    html = re.sub(r"__END-([0-9.]+)__", lambda m: f"{total - float(m.group(1)):.4f}", html)
    (hf / "index.html").write_text(html)
    print(f"index.html -> {hf} ({'sample ' if sample else ''}{total:.2f} s)")
    return hf


def cues(R, sample=False):
    hf = hf_dir(R, sample)
    out = R.work / ("cues_sample.json" if sample else "cues.json")
    r = run(["node", ROOT / "kit/presets/paper_studio/example/cues.mjs", hf / "index.html", out], cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr.strip()[-400:])
    if "ERRORS" in r.stdout:
        raise SystemExit("page errors: fix the template")
    return out


def beds(R, edl, total=None):
    sys.path.insert(0, str(ROOT))
    from kit.audio import beats as BT
    from kit.audio.mix import Bed
    from kit.film.mix import resolve                     # the music map: snapped starts, drop="auto" (kit/film/README "mix")
    out = []
    total = total or edl["total"]
    tracks = BT.load()
    for m in R.MUSIC:
        a, b = wtime(edl, m.get("a", 0)), min(total, wtime(edl, m.get("b", "end")))
        if a >= total - 0.3:
            continue
        start, how = resolve(m, a, b, edl, tracks)
        print(f"music {m['file'].split('/')[-1]} {a:.2f}-{b:.2f} s: {how}")
        out.append(Bed(MUSIC_DIR / m["file"], a, b, max(0.0, start), m.get("gap", -5.0), m.get("under", -12.0),
                       m.get("fade_in", 0.3), m.get("fade_out", 0.3), even=m.get("even", 0.0), end_fade=m.get("end_fade")))
    return out


def sound_fm(R, edl=None, music=None):
    """This Reel as kit/film/mix.py's sound code reads a film (FilmConfig's names): SOUND from reel.py, work/ (its
    music.json), the day its src/template.html was made (made_on's made_file), MUSIC, and the folder that holds its
    visual_plan.json."""
    from types import SimpleNamespace
    return SimpleNamespace(dir=R.dir, reel=R.dir.name, made_file=R.dir / "src/template.html", work=R.work, mod=R.mod,
                           SOUND=getattr(R, "SOUND", None) or getattr(R.mod, "SOUND", None),
                           MUSIC=R.MUSIC if music is None else music, W=R.W, H=R.H, edl=lambda: edl)


def sound(R):
    """('v11' | 'v10', why): kit/film/mix.py's sound gate (sound_why) for this Reel."""
    sys.path.insert(0, str(ROOT))
    from kit.film import mix as MX
    s = getattr(R, "SOUND", None) or getattr(R.mod, "SOUND", None)
    if s:
        if s not in ("v10", "v11"):
            raise SystemExit(f"{R.dir.name}/reel.py: SOUND = {s!r}: use 'v10' or 'v11'")
        return s, "SOUND in reel.py"
    return MX.sound_why(sound_fm(R))


def music_plan(R, edl, total, v11, cues=(), quiet=()):
    """kit/film/mix.py's planner on this Reel: {fm, edl, planned, beds, moments, notes} (beds: the v11 Beds; None on
    v10, where beds() builds them as it always has). a / b (seconds, "w<id>", "end", "end-<s>") and at are resolved on
    the whole cut first, b at most `total`, and a bed that starts in the last 0.3 s is left out (a sample's beds end on
    its last second, as before)."""
    from kit.film import mix as MX
    music = []
    for m in R.MUSIC:
        a, b = wtime(edl, m.get("a", 0)), min(total, wtime(edl, m.get("b", "end")))
        if a >= total - 0.3:
            continue
        music.append(dict(m, a=a, b=b, **({"at": MX.when(edl, m["at"])} if "at" in m else {})))
    e3 = dict(edl, total=total)
    fm = sound_fm(R, e3, music)
    notes = []
    mom = MX.moments(fm, edl, "reel", notes, cues, quiet) if v11 else {"quiet": [], "cues": [], "drops": []}
    planned = MX.plan(fm, e3, v11=v11, drops=mom["drops"], notes=notes)
    return {"fm": fm, "edl": e3, "planned": planned, "beds": MX.beds(fm, e3, planned, v11=True, notes=notes) if v11 else None,
            "moments": mom, "notes": notes}


def mix(R, sample=False):
    """vo.wav + the MUSIC beds + the page's cues -> work/mix.wav (mix_sample.wav), and work/music.json
    (music_sample.json). The sound by sound(): v10 exactly as before 2026-10-22, or v11 (the module docstring)."""
    sys.path.insert(0, str(ROOT))
    from kit.audio.mix import V11_REEL, mix as kmix
    from kit.film import mix as MX
    edl = edl_of(R)
    total = min(edl["total"], R.SAMPLE) if sample else edl["total"]
    e2 = dict(edl)
    if sample:
        e2 = dict(edl, words=[w for w in edl["words"] if w["t"] < total], talk_end=min(edl["talk_end"], total))
    v, why = sound(R)
    print(f"sound: {v} (reel; {why})")
    cues_name = "cues_sample.json" if sample else "cues.json"
    cues_p, quiet_p = R.work / cues_name, R.work / cues_name.replace(".json", ".quiet.json")
    cues = json.load(open(cues_p)) if cues_p.exists() else []
    P = music_plan(R, edl, total, v == "v11", cues, json.load(open(quiet_p)) if quiet_p.exists() else [])
    if v != "v11":
        r = kmix(R.work, e2, beds(R, edl, total), total, out_name="mix_sample.wav" if sample else "mix.wav",
                 cues_name=cues_name)
    else:
        for m, a, b, start, how, e in P["planned"]:
            print(f"music {m['file'].split('/')[-1]} {a:.2f}-{b:.2f} s: {how}")
        r = kmix(R.work, e2, P["beds"], total, out_name="mix_sample.wav" if sample else "mix.wav", cues_name=cues_name,
                 sound=V11_REEL, quiet_extra=P["moments"]["quiet"], cues_extra=P["moments"]["cues"])
    # music.json (kit/film/mix.py's): the beds on the music map, the sound (sticky: sound_why reads it back), the findings
    # (qa.py --music) and the measured mix
    M = MX.music_map(P["fm"], P["edl"], P["planned"], bedlist=P["beds"])
    M["sound"] = v
    M["findings"] = MX.findings(M, cues) + (MX.v11_findings(P["fm"], M, P["beds"], r, P["notes"], "reel") if v == "v11" else [])
    for f in M["findings"]:
        print(f"MUSIC {f['id']}: {f['detail']} -> {f['fix']}")
    M["mix"] = {k: x for k, x in r.items() if k != "dropouts"}
    (R.work / ("music_sample.json" if sample else "music.json")).write_text(json.dumps(M, indent=1))
    if not sample and R.MUSIC:
        MX.record_usage(P["fm"], P["beds"] or MX.beds(P["fm"], P["edl"], P["planned"], v11=False))
    return r


def mux(R, sample=False):
    raw = R.F.renders / ("sample_raw.mp4" if sample else "raw.mp4")
    out = (R.F.renders / "sample.mp4") if sample else (R.F.final / R.OUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-i", R.work / ("mix_sample.wav" if sample else "mix.wav"), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-aac_pns", "0", "-b:a", "320k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out], check=True)
    print("->", out)
    return out


def ambition(R):
    """(on, why): precheck's ambition, speaker and density gates as HIGH (on) or MEDIUM (off, --no-ambition).
    --ambition / --no-ambition on the command line win, then AMBITION in reel.py, else on for a Reel made from V11_FROM
    (made_on, as kit/film's films): a rebuilt older page now publishes window.__speaker, and the gates added since went
    HIGH on Reels delivered before them, with no --no-ambition to pass (kit/reel never forwarded it)."""
    if "--no-ambition" in sys.argv:
        return False, "--no-ambition"
    if "--ambition" in sys.argv:
        return True, "--ambition"
    a = getattr(R, "AMBITION", None)
    a = getattr(R.mod, "AMBITION", None) if a is None else a
    if a is not None:
        return bool(a), "AMBITION in reel.py"
    sys.path.insert(0, str(ROOT))
    from kit.film import mix as MX
    d = MX.made_on(sound_fm(R))
    return d >= MX.V11_FROM, f"made on {d}, on from {MX.V11_FROM}"


def precheck_report(out, tail=2000, most=12):
    """What the terminal shows of precheck's stdout: its verdict line ("PASS|WARN|FAIL: <page> ..."), its HIGH lines
    (`most` at most; precheck.json has every finding), then the last `tail` characters, which end on its closing line
    ("precheck PASS|WARN|FAIL: n HIGH [kinds], m MEDIUM"). stdout[-3000:] lost the verdict and the HIGHs under a long
    page's MEDIUM lines (planning request 50). A short output is shown whole."""
    out = out.rstrip()
    if len(out) <= tail + 400:
        return out
    rest = out[-tail:]
    rest = rest[rest.find("\n") + 1:]                       # from the first whole line
    shown = set(rest.splitlines())
    lines = out.splitlines()
    head = [ln for ln in lines if re.match(r"(PASS|WARN|FAIL): ", ln) and ln not in shown][:1]
    highs = [ln for ln in lines if ln.startswith("  HIGH") and ln not in shown]
    more = [f"  ... {len(highs) - most} more HIGH (precheck.json)"] if len(highs) > most else []
    return "\n".join(head + highs[:most] + more + ["  ..."] + rest.splitlines())


def precheck(R, sample=False):
    """kit/qa/precheck.mjs on the page: layout, phone-readable text, reading time; writes the reading holds for qa.py.
    Exit 3 (a HIGH finding) stops the render unless --force."""
    hf = hf_dir(R, sample)
    holds = R.work / ("holds_sample.json" if sample else "holds.json")
    js = R.work / ("precheck_sample.json" if sample else "precheck.json")
    amb, why = ambition(R)
    print(f"ambition: {'on' if amb else 'off (its HIGHs print as MEDIUM)'} ({why})")
    r = run(["node", ROOT / "kit/qa/precheck.mjs", hf / "index.html", "--fps=5", f"--holds-out={holds}", f"--json={js}"]
            + ([] if amb else ["--no-ambition"]), cwd=ROOT, capture_output=True, text=True)
    print(precheck_report(r.stdout), r.stderr[-400:])
    if r.returncode == 3 and "--force" not in sys.argv:
        raise SystemExit(f"precheck: HIGH findings (above; every finding in {js}). Fix the template, or re-run with --force to render anyway")
    return holds


def render(R, sample=False, draft=False):
    hf = build(R, sample)
    env = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1")
    lint = run(["npx", "hyperframes", "lint", hf], cwd=ROOT, env=env, capture_output=True, text=True)
    print(lint.stdout[-1500:], lint.stderr[-600:])
    cues(R, sample)
    holds = precheck(R, sample)
    mix(R, sample)
    raw = R.F.renders / ("sample_raw.mp4" if sample else "raw.mp4")
    # HF_WORKERS=2: fewer Chrome workers when another render or grade shares the Mac (default: hyperframes' auto)
    workers = ["--workers", os.environ["HF_WORKERS"]] if os.environ.get("HF_WORKERS") else []
    r = run(["npx", "hyperframes", "render", hf, "-o", raw, "--fps", str(R.FPS), "--quality", "draft" if draft else "delivery"] + workers, cwd=ROOT, env=env)
    if r.returncode:
        raise SystemExit("render failed")
    out = mux(R, sample)
    edl = edl_of(R)
    total = min(edl["total"], R.SAMPLE) if sample else edl["total"]
    cuts = R.dir / "cuts.json"
    declared = R.work / ("cues_sample.holds.json" if sample else "cues.holds.json")
    # the music map's findings (qa.py --music) on the v11 sound; a v10 Reel's qa stays as it was
    mj = R.work / ("music_sample.json" if sample else "music.json")
    music = [f"--music={mj}"] if mj.exists() and json.loads(mj.read_text()).get("sound") == "v11" else []
    q = run([sys.executable, ROOT / "kit/qa/qa.py", out, f"--cuts={cuts}", f"--expect-duration={total:.2f}", f"--expect-size={R.W}x{R.H}",
             f"--holds={holds},{declared}"] + music, cwd=ROOT)
    return q.returncode


def snap(R, times, sample=False):
    hf = hf_dir(R, sample)
    out = R.F.renders / "snap"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    env = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1")
    args = ["npx", "hyperframes", "snapshot", hf, "-o", out, "--no-end", "--describe", "false", "--at", ",".join(f"{t}" for t in times)]
    r = run(args, cwd=ROOT, env=env, capture_output=True, text=True)
    print(r.stdout[-800:], r.stderr[-800:])
    return out
