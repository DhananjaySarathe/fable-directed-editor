"""The grade: look v2 (kit/look/grade.py --v2) on the cut's camera track, so only what the edit keeps is graded and the
cut is never re-graded (films/ai-workflows/grade_cut.py, kit/reel/prep.py; 2026-10-20). film.py:

    GRADE = dict(look="natural", room="woodoffice", tracks=["aroll"], vignette=0.0, matte=False, reel=None, set="")

  - each shot gets its own exposure and white balance: a shot is a stretch of one take and one view kind (the shots are
    the pieces' take / kind changes, so a café take and a screen recording are never balanced together);
  - the face track is the cut's own (work/<track>.face.json, YuNet in the track's pixels: kit/film/cut.py faces());
  - his room stays as shot (OWNER_DEFAULTS §2: "no blur, dimming, vignette or background replacement"): vignette 0 and
    no matte by default. `matte=True` (personseg masks: the room set back and desaturated per the look) and a vignette
    are opt-ins for a film he asked that of. `set` passes any other look v2 number (GRADE_V2_SET, kit/look/v2.py);
  - the graded track is work/<track>_graded.mp4, complete or absent: kit/look/grade.py writes <track>_graded.mp4.part
    and renames it only when every frame of the cut is in it, then writes <track>_graded.mp4.ok (what it was graded
    from and the settings it was graded with). Build and reels use it only while that record matches the cut as it is
    now AND GRADE as it is now (config.track_file -> want()), and the 4K render refuses a missing, stale, short or
    differently-graded one when GRADE is set (--force to override). So changing GRADE (look="clean", kinds, regions,
    room, set...) and running `grade` re-grades: no --force needed. A graded file from before settings were recorded
    is compared on its looks only (its .balance.json), so an unchanged film is never re-graded for the upgrade;
  - kinds (2026-10-22, v11): {view kind: look name | None}. None = that kind passes through exactly as recorded (a
    screen recording: UI text stays crisp and neutral, page whites stay white); a name grades that kind with its own
    look (cam="clean" while the film's look stays for the rest); a kind not listed gets `look`. regions: {view kind:
    [x, y, w, h]} in the track's pixels: only that rectangle is graded (a Framecast cam bubble over a screen
    recording), balanced on its own face; one rectangle per track. A {kind: rect} region applies to each GRADE track
    whose frame holds it (a 1080 face track skips the room's 4K bubble rectangle, with a note); {track: {kind: rect}}
    names the track. Each kind is its own shot already (shots());
  - A/B: `--sheet=8,30,120` grades the same frames in the film's look and in 'clean' (kit/look/looks.py) side by side,
    each drawn the way the white page shows him (a card and a circle on #FFFFFF), with the scopes numbers (skin, his
    wall's Y' and cast) under every tile and in the sheet's .json. --sheet-looks=natural,clean,... and --stage=#F5F5F7
    change the columns and the stage. Nothing is graded for the film by a sheet.

    GRADE = dict(look="natural", kinds={"chrome": None, "github": None}, regions={"chrome": [3184, 1504, 576, 576]})

    uv run python -m kit.film <film> grade [--sheet=8,30,120] [--force]     (--sheet: the A/B, to choose a look)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

from kit.film.cut import frames
from kit.paths import ROOT

DEFAULTS = dict(look="natural", room=None, tracks=None, vignette=0.0, matte=False, reel=None, set="", workers=4, kinds=None, regions=None, crf=13)
# crf: x264 CRF of the graded intermediate (the render re-encodes it; lower keeps more of a 4K night take's grain and
# the tone map's dither: who-gonna-hire, 2026-10-23, 10)
AB = "clean"                     # the look every A/B sheet sets beside the film's own (v11: the white page's grade)


def _opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def stretches(Fm, edl, name):
    """[(t0, t1, kind)]: the track's timeline by the view kind it shows (each piece to the next piece's start, as the
    cut writes the track), consecutive pieces of one kind merged; None where the track shows black."""
    from kit.film.cut import vf_for
    P, out = edl["pieces"], []
    for k, p in enumerate(P):
        t1 = P[k + 1]["out_a"] if k + 1 < len(P) else edl["total"]
        kind = p["kind"] if vf_for(Fm, name, p["clip"], p["kind"]) is not None else None
        if out and out[-1][2] == kind and abs(out[-1][1] - p["out_a"]) < 1e-3:
            out[-1] = (out[-1][0], t1, kind)
        else:
            out.append((p["out_a"], t1, kind))
    return out


def track_regions(Fm, g, name, quiet=False) -> dict:
    """GRADE regions for one track -> {view kind: [x, y, w, h]}. Two forms: {track: {kind: rect}} (one track's own
    rectangles), or {kind: rect} for every GRADE track, where a rectangle applies only to a track whose frame holds it
    (2026-10-22, v11 review: the face track (1080 x 1080) also shows oss-editor's chrome kind, and the room track's
    [3184, 1504, 576, 576] bubble stopped grade.py there with 'outside the frame')."""
    regions = g.get("regions") or {}
    if any(isinstance(v, dict) for v in regions.values()):
        return dict(regions.get(name) or {})
    if not regions:
        return {}
    W, H = Fm.track_size(name)
    out = {}
    for k, r in regions.items():
        if r[0] >= 0 and r[1] >= 0 and r[0] + r[2] <= W and r[1] + r[3] <= H:
            out[k] = r
        elif not quiet:
            print(f"GRADE regions: {k} {list(r)} is outside {name}'s {W}x{H} frame: not a region on {name} "
                  f"(regions={{track: {{kind: rect}}}} names the track)")
    return out


def kind_spec(Fm, g, edl, name, quiet=False) -> tuple:
    """GRADE kinds / regions -> (kit/look/grade.py arguments for one track, --looks plan or None); nothing is written.
    Arguments: --passthrough, --region + --region-at; the plan (hard switches at the stretches' starts) when a kind has
    its own look. No kinds and no regions: ([], None) (the grade is exactly what it was before). Edges are written to
    the millisecond and kit/look/grade.py snaps each to its nearest frame (edge_frame), which is the frame the cut
    starts that stretch on (cut.py write_track: round(out_a * FPS)), so a .3f that rounds past its frame is harmless."""
    kinds, regions = g.get("kinds") or {}, track_regions(Fm, g, name, quiet)
    if not kinds and not regions:
        return [], None
    st = stretches(Fm, edl, name)
    rects = {tuple(regions[k]) for _, _, k in st if k in regions}
    if len(rects) > 1:
        raise SystemExit(f"GRADE regions: {name} shows {len(rects)} different rectangles ({sorted(rects)}); one per track")
    fmt = lambda rs: ",".join(f"{a:.3f}-{b:.3f}" for a, b in rs)          # noqa: E731
    passes = [(a, b) for a, b, k in st if k in kinds and kinds[k] is None and k not in regions]
    at = [(a, b) for a, b, k in st if k in regions]
    args = ([f"--passthrough={fmt(passes)}"] if passes else []) + \
        ([f"--region={','.join(str(int(v)) for v in next(iter(rects)))}", f"--region-at={fmt(at)}"] if rects else [])
    plan, cur = [], None
    for a, b, k in st:
        lk = (kinds.get(k) if k is not None else None) or g["look"]
        if lk != cur:
            plan.append({"t": round(a, 3), "look": lk, "fade": 0.0})
            cur = lk
    return args, (plan if any(p["look"] != g["look"] for p in plan) else None)


def kind_args(Fm, g, edl, name) -> list:
    """kind_spec's arguments, with its plan written to work/<track>.looks.json (--looks)."""
    args, plan = kind_spec(Fm, g, edl, name)
    if plan:
        pf = Fm.work / f"{name}.looks.json"
        pf.write_text(json.dumps(plan, indent=1))
        args.append(f"--looks={pf}")
    return args


def command(Fm, name, g=None, edl=None, quiet=False) -> tuple:
    """(kit/look/grade.py arguments for one GRADE track, GRADE_V2_SET, --looks plan or None), with nothing generated or
    written: the matte folder is named, not made (run() makes it before a grade); the plan is returned, not written."""
    g = g or cfg(Fm)
    edl = edl or Fm.edl()
    src, out = Fm.work / f"{name}.mp4", Fm.work / f"{name}_graded.mp4"
    reel = g["reel"] if g["reel"] is not None else Fm.H > Fm.W
    sh = shots(Fm, edl, name)
    args = [src, out, "--v2", f"--look={g['look']}", f"--track={Fm.work / f'{name}.face.json'}"] + ([f"--room={g['room']}"] if g["room"] else []) + \
        ([f"--shots={','.join(f'{s:.3f}' for s in sh)}"] if sh else []) + (["--reel"] if reel else [])
    if g["matte"]:
        args.append(f"--matte={Fm.work / f'{name}_matte'}")
    ka, plan = kind_spec(Fm, g, edl, name, quiet)
    args += ka
    if plan:
        args.append(f"--looks={Fm.work / f'{name}.looks.json'}")
    v2set = ",".join(x for x in (f"vignette={g['vignette']}", g["set"]) if x)
    return args, v2set, plan


def want(Fm, name) -> dict:
    """What GRADE asks of this track's grade now (kit/look/ffio.settings): status() refuses a graded file made with
    anything else (another look, room, kinds plan, region, matte, GRADE_V2_SET)."""
    from kit.look import ffio as FF
    args, v2set, plan = command(Fm, name, quiet=True)
    return FF.settings(args[2:], v2set, plan)


def cfg(Fm) -> dict:
    if not Fm.GRADE:
        raise SystemExit(f"{Fm.dir}: set GRADE in film.py (e.g. GRADE = dict(look=\"natural\", room=\"woodoffice\"))")
    g = dict(DEFAULTS, **Fm.GRADE)
    g["tracks"] = g["tracks"] or [Fm.FACE_TRACK]
    return g


def shots(Fm, edl, name):
    """Output times where the track's picture changes take or view kind (each such stretch is balanced on its own)."""
    from kit.film.cut import vf_for
    key = lambda p: (str(p["clip"]), p["kind"], vf_for(Fm, name, p["clip"], p["kind"]) is None)   # noqa: E731
    P = edl["pieces"]
    return [round(q["out_a"], 3) for p, q in zip(P, P[1:]) if key(p) != key(q)]


def matte(Fm, src, d, chunk=900):
    """personseg person masks of every frame (from 1920-wide frames), f00001.png ..."""
    n = frames(src)
    if d.exists() and len(list(d.glob("f*.png"))) >= n:
        return d
    d.mkdir(exist_ok=True)
    tmp = d.parent / (d.name + "_frames")
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(a - 0.5) / Fm.FPS:.5f}" if a else "0", "-i", str(src), "-frames:v", str(b - a),
                        "-vf", "scale=1920:-2:flags=area", "-start_number", str(a + 1), str(tmp / "f%05d.png")], check=True)
        subprocess.run([str(ROOT / "kit/bin/personseg"), str(tmp), str(d), "--mask"], check=True, stdout=subprocess.DEVNULL)
        print(f"masks {a + 1}-{b} of {n}", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return d


def run(Fm, sheet=None, force=False, sheet_looks=None, stage=None, sheet_out=None):
    """Grade the GRADE tracks; with `sheet` (seconds, comma-separated) write the A/B sheet instead (into sheet_out, a
    folder or a .jpg; default work/<track>_grade_sheet.jpg)."""
    from kit.look import ffio as FF
    g = cfg(Fm)
    edl = Fm.edl()
    for name in g["tracks"]:
        src, out = Fm.work / f"{name}.mp4", Fm.work / f"{name}_graded.mp4"
        log = Fm.work / f"{name}_grade.log"
        if not src.exists():
            raise SystemExit(f"no {src}: run the cut first")
        track = Fm.work / f"{name}.face.json"
        if not track.exists():
            subprocess.run([sys.executable, str(ROOT / "kit/look/faces.py"), str(src), str(track)], check=True, cwd=ROOT)
        args, v2set, plan = command(Fm, name, g, edl)
        sh = shots(Fm, edl, name)
        env = dict(os.environ, GRADE_WORKERS=os.environ.get("GRADE_WORKERS", str(g["workers"])),
                   GRADE_PRESET=os.environ.get("GRADE_PRESET", "veryfast"),      # an intermediate: the render re-encodes it
                   GRADE_CRF=os.environ.get("GRADE_CRF", str(g["crf"])),
                   GRADE_V2_SET=v2set)
        if g["matte"]:
            matte(Fm, src, Fm.work / f"{name}_matte")                    # (command() names the folder; made here)
        if plan:
            (Fm.work / f"{name}.looks.json").write_text(json.dumps(plan, indent=1))
        if sheet:
            looks = (sheet_looks or _opt("sheet-looks") or ",".join(dict.fromkeys([g["look"], AB]))).split(",")
            jpg = Fm.work / f"{name}_grade_sheet.jpg"
            if sheet_out:
                from pathlib import Path
                so = Path(sheet_out)
                jpg = so if so.suffix.lower() in (".jpg", ".jpeg", ".png") else so / f"{Fm.dir.name}_{name}_grade_sheet.jpg"
                jpg.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, ROOT / "kit/look/grade.py", src, jpg, f"--sheet={sheet}", f"--sheet-looks={','.join(looks)}",
                            f"--stage={stage or _opt('stage', '#FFFFFF')}", *map(str, args[2:])], check=True, cwd=ROOT, env=env)
            print("->", jpg)
            continue
        wanted = FF.settings(args[2:], v2set, plan)                       # GRADE as it is now (ffio.settings)
        ok, why = FF.status(src, out, want=wanted)
        if ok and not force:
            print(f"{name}: graded already ({out.name}, with these settings)")
            continue
        if why and out.exists():
            print(f"{name}: {why}")
        print(f"$ grade.py {name}.mp4 -> {out.name} ({len(sh) + 1} shots, look {g['look']}, room {g['room'] or 'paper'}, "
              f"GRADE_V2_SET={env['GRADE_V2_SET']})", flush=True)
        with open(log, "w") as lf:
            r = subprocess.run([sys.executable, str(ROOT / "kit/look/grade.py"), *map(str, args)], stdout=lf, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
        tail = log.read_text().strip().splitlines()[-1:] or [""]
        if r.returncode:
            raise SystemExit(f"grade failed: see {log}" + (f" ({tail[0]})" if tail[0] else ""))
        ok, why = FF.status(src, out, want=wanted)                        # the .ok kit/look/grade.py wrote, re-read
        if not ok:
            raise SystemExit(f"{out.name}: {why}")
        print(f"-> {out} ({frames(out)} frames; {tail[0]})")
