"""uv run python -m kit.film <film> <step> [options]   (the steps: kit/film/__init__.py, kit/film/README.md)

  <film>   films/<name>, a name under films/, kit/film/example, or <film>/reels/<r> for a Reel's own steps
  options  --force (cutcheck REVIEW/FAIL or precheck HIGH: go on anyway), --plan (cut/reels: print, write nothing),
           --words / --voice (cut: edl.json only / plus vo.wav), --no-relisten, --at=12.3,40.1 (joins / snap),
           --draft (mux the draft), --ambition / --no-ambition (precheck's ambition gate; unset: AMBITION in film.py,
           else on for films made from 2026-10-22), --workers=N, prep --only=words,picture,voice,eq --force=voice,
           grade [--sheet=8,30,120 (the film's look beside clean on white; --sheet-looks=, --stage=)] [--force]
           (a changed GRADE re-grades without --force)
"""
import sys

from kit.film.config import FilmConfig

STEPS = ("prep", "cut", "joins", "grade", "build", "cues", "precheck", "mix", "draft", "render", "mux", "reels", "snap", "paths", "all")


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2 or args[1] not in STEPS:
        print(__doc__)
        print(open(__file__.replace("__main__.py", "__init__.py")).read().split('"""')[1])
        raise SystemExit(2)
    Fm, step = FilmConfig(args[0]), args[1]
    force = "--force" in sys.argv
    # precheck's ambition gate: the command line wins, else kit/film/render.py ambition_of (AMBITION, the film's date)
    ambition = False if "--no-ambition" in sys.argv else True if "--ambition" in sys.argv else None
    if step == "paths":
        print(f"W={Fm.work}\nHF={Fm.F.hf}\nR={Fm.F.renders}\nFINAL={Fm.F.final}\nEDL={Fm.edl_path}")
        return
    if step == "prep":
        from kit.film import prep
        prep.run(Fm, only=(opt("only") or "").split(",") if opt("only") else None, force=(opt("force", "") or "").split(","))
    if step in ("cut", "all"):
        if Fm.reel:
            raise SystemExit("a Reel is cut from its film: python -m kit.film <film> reels " + Fm.reel)
        from kit.film import cut
        cut.run(Fm, force=force, plan_only="--plan" in sys.argv, words_only="--words" in sys.argv, voice_only="--voice" in sys.argv)
        if "--plan" in sys.argv:
            return
    if step in ("joins", "all"):
        from kit.film import cut
        code = cut.joins(Fm, relisten="--no-relisten" not in sys.argv, at=opt("at"))
        if code and not force:
            raise SystemExit(code)
    if step == "grade" or (step == "all" and Fm.GRADE):
        from kit.film import grade
        grade.run(Fm, sheet=opt("sheet"), force=force)
    if step == "build":
        from kit.film import build
        build.build(Fm)
    if step == "cues":
        from kit.film import build
        build.cues(Fm)
    if step == "precheck":
        from kit.film import build, render
        on, why = render.ambition_of(Fm, ambition)
        print(f"precheck ambition: {'on' if on else 'off'} ({why})")
        raise SystemExit(build.precheck(Fm, force=True, ambition=on))
    if step == "mix":
        from kit.film import mix
        mix.run(Fm)
    if step in ("draft", "all"):
        from kit.film import render
        raise SystemExit(render.draft(Fm, force=force, ambition=ambition, workers=opt("workers")))
    if step == "render":
        from kit.film import render
        raise SystemExit(render.render(Fm, force=force, ambition=ambition, skip_checks="--skip-checks" in sys.argv))
    if step == "mux":
        from kit.film import render
        render.mux(Fm, draft="--draft" in sys.argv)
    if step == "reels":
        from kit.film import reels
        reels.run(Fm, names=args[2:] or None, plan_only="--plan" in sys.argv)
    if step == "snap":
        from kit.film import build
        build.snap(Fm, [float(x) for x in (opt("at") or "").split(",") if x])


if __name__ == "__main__":
    main()
