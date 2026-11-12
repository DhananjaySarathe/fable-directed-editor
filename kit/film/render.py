"""Renders: the 1080p draft (for qa.py and the critic) and the one 4K render, each muxed with the mix and checked.

  draft    plan_check (stops on an error) -> build -> lint -> cues -> precheck (stops on HIGH) -> mix
           -> `hyperframes render --quality draft` at 1080p -> renders/draft_av.mp4 -> kit/qa/qa.py (cuts, duration,
           size, holds). Returns qa's exit code (3 = FAIL). plan_check reads the recipe's own visual_plan.json (a
           Reel's in <film>/reels/<r>/, if it has one), timed on work/edl.json; its warnings print and the build goes on
  render   the same checks, then kit/hf/render4k.py (30 s chunks, videos kept from streaming; a finished chunk is
           skipped on a re-run) -> renders/raw.mp4 -> mux -> output/final/<video>/<OUT> -> qa.py again
  mux      renders/raw.mp4 (or draft.mp4 with --draft) + work/mix.wav -> the deliverable (AAC 320k, -aac_pns 0)

One heavy render at a time on this Mac (OWNER_DEFAULTS §7): `render` waits for nothing, so check first.
"""
from __future__ import annotations

import sys

from kit.film import build as B
from kit.film import mix as M
from kit.paths import ROOT


def plan(Fm, force=False):
    """kit/hf/plan_check.py on the recipe's visual_plan.json (kit/refs/SCENES.md), timed on the film's own cut when the
    plan names no EDL. Errors (exit 3) stop the build unless --force; warnings print. No plan: a note, and on we go
    (a Reel cut from its film usually has none; the film's plan is a long-form plan and would be judged as one)."""
    p = Fm.dir / "visual_plan.json"
    if not p.exists():
        print(f"plan_check: no visual_plan.json in {Fm.dir} (skipped)")
        return 0
    r = B.run([sys.executable, ROOT / "kit/hf/plan_check.py", p] + ([f"--edl={Fm.edl_path}"] if Fm.edl_path.exists() else []),
              cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.rstrip())                               # all of it: the errors come first, the verdict last
    if r.stderr.strip():
        print(r.stderr.rstrip()[-800:])
    if r.returncode not in (0, 2, 3) and not force:        # plan_check itself broke (a bad JSON, a crash): never silent
        raise SystemExit(f"plan_check: exit {r.returncode} on {p} (above). Fix it, or pass --force to go on anyway")
    if r.returncode == 3 and not force:
        raise SystemExit("plan_check: errors in visual_plan.json (above). Fix the plan, or pass --force to go on anyway")
    return r.returncode


def ambition_of(Fm, ambition=None):
    """precheck's ambition gate as (on, why). The command line wins (--ambition True, --no-ambition False), then
    AMBITION in film.py, else the film's date (kit/film/mix.py made_on): on for a film made on or after V11_FROM. The v11
    gates (merged layouts, framing, density) misfire on films delivered before them, whose rebuilt pages now publish
    window.__speaker (v11 fix P-M3)."""
    if ambition is not None:
        return bool(ambition), "--ambition" if ambition else "--no-ambition"
    a = getattr(Fm, "AMBITION", None)
    if a is not None:
        return bool(a), f"AMBITION = {a!r} in film.py"
    from kit.film.mix import V11_FROM, made_on
    day = made_on(Fm)
    return day >= V11_FROM, f"made {day}, {'on or after' if day >= V11_FROM else 'before'} {V11_FROM}"


def prepare(Fm, force=False, ambition=None):
    """plan_check, build, lint, cues, precheck, mix: everything a render needs, in the order that fails fastest.
    ambition: None decides by AMBITION / the film's date (ambition_of)."""
    on, why = ambition_of(Fm, ambition)
    print(f"precheck ambition: {'on' if on else 'off'} ({why})")
    plan(Fm, force=force)
    B.build(Fm)
    B.lint(Fm)
    B.cues(Fm)
    B.precheck(Fm, force=force, ambition=on)
    M.run(Fm)


def mux(Fm, draft=False, raw=None, out=None):
    src = raw or Fm.F.renders / ("draft.mp4" if draft else "raw.mp4")
    out = out or ((Fm.F.renders / "draft_av.mp4") if draft else (Fm.F.final / Fm.OUT))
    if not src.exists():
        raise SystemExit(f"no {src}: render first")
    out.parent.mkdir(parents=True, exist_ok=True)
    B.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", Fm.work / "mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
           "-c:a", "aac", "-aac_pns", "0", "-b:a", "320k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out], check=True)
    print("->", out)
    return out


def doc_black(Fm, edl) -> list:
    """A documentary's chapter cards are black by design (kit/film/doc.py): qa.py's --allow-black for them. [] otherwise."""
    from kit.film import doc
    if not doc.on(Fm) or not Fm.DOC.get("chapters"):
        return []
    from kit.film.mix import when
    spans = [(when(edl, c["at"]) - 0.1, when(edl, c["at"]) + float(c.get("dur", 2.4)) + 0.1) for c in Fm.DOC["chapters"]]
    return ["--allow-black=" + ",".join(f"{a:.2f}-{b:.2f}" for a, b in spans)]


def qa(Fm, video, size):
    edl = Fm.edl()
    holds = ",".join(str(p) for p in (Fm.work / "holds.json", Fm.work / "cues.holds.json") if p.exists())
    r = B.run([sys.executable, ROOT / "kit/qa/qa.py", video, f"--cuts={Fm.work / 'cuts.json'}", f"--expect-duration={edl['total']:.3f}",
               f"--expect-size={size}", f"--fps={Fm.FPS}", f"--voice={Fm.work / 'vo.wav'}", f"--json={Fm.work / ('qa_' + video.stem + '.json')}"]
              + ([f"--holds={holds}"] if holds else [])
              + ([f"--music={Fm.work / 'music.json'}"] if (Fm.work / "music.json").exists() else [])
              + doc_black(Fm, edl), cwd=ROOT)
    return r.returncode


def draft(Fm, force=False, ambition=None, workers=None):
    prepare(Fm, force, ambition)
    out = Fm.F.renders / "draft.mp4"
    portrait = Fm.H > Fm.W
    r = B.run(["npx", "hyperframes", "render", Fm.F.hf, "-o", out, "--fps", str(Fm.FPS), "--quality", "draft",
               "--workers", str(workers or Fm.DRAFT_WORKERS)] + ([] if portrait else ["--resolution", "1080p"]), cwd=ROOT, env=B.ENV)
    if r.returncode:
        raise SystemExit("draft render failed")
    av = mux(Fm, draft=True)
    return qa(Fm, av, f"{Fm.W}x{Fm.H}" if portrait else "1920x1080")


def render(Fm, force=False, ambition=None, skip_checks=False):
    """The one 4K render (16:9: 3840x2160; a Reel renders at its page size, 1080x1920, and with OUT_4K also at 2x)."""
    stale = [why for name in Fm.edl().get("tracks", {}) for why in [Fm.track_file(name)[1]] if why]
    if stale and not force:
        raise SystemExit("render: " + "; ".join(stale) + " (or --force to render the ungraded cut)")
    if not skip_checks:
        prepare(Fm, force, ambition)
    raw = Fm.F.renders / "raw.mp4"
    if Fm.H > Fm.W:
        r = B.run(["npx", "hyperframes", "render", Fm.F.hf, "-o", raw, "--fps", str(Fm.FPS), "--quality", "delivery",
                   "--workers", str(Fm.WORKERS)], cwd=ROOT, env=B.ENV)
        size = f"{Fm.W}x{Fm.H}"
    else:
        r = B.run([sys.executable, ROOT / "kit/hf/render4k.py", Fm.F.hf, f"--out={raw}", f"--fps={Fm.FPS}", f"--workers={Fm.WORKERS}",
                   f"--chunk={Fm.CHUNK}"], cwd=ROOT)
        size = "3840x2160"
    if r.returncode:
        raise SystemExit("render failed")
    code = qa(Fm, mux(Fm), size)
    if Fm.H > Fm.W and getattr(Fm, "OUT_4K", None):
        # the same Reel page at 2x (2160x3840) for YouTube Shorts, in chunks (a 4K page holds every frame in the node heap:
        # memory hf-4k-chunk-render); after the 1080 render, never beside it (one render at a time)
        raw4 = Fm.F.renders / "raw_4k.mp4"
        r = B.run([sys.executable, ROOT / "kit/hf/render4k.py", Fm.F.hf, f"--out={raw4}", f"--fps={Fm.FPS}", f"--workers={Fm.WORKERS}",
                   f"--chunk={Fm.CHUNK}", "--resolution=portrait-4k"], cwd=ROOT)
        if r.returncode:
            raise SystemExit("4K render failed")
        code = max(code, qa(Fm, mux(Fm, raw=raw4, out=Fm.F.final / Fm.OUT_4K), f"{2 * Fm.W}x{2 * Fm.H}"))
    return code
