"""uv run python -m kit.reel <film> <step> [options]   (see kit/reel/__init__.py)"""
import sys

from kit.reel.config import Reel


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        print(open(__file__.replace("__main__.py", "__init__.py")).read().split('"""')[1])
        raise SystemExit(2)
    R, step = Reel(args[0]), args[1]
    sample = "--sample" in sys.argv
    force = (opt("force", "") or "").split(",")
    if step in ("prep", "all"):
        from kit.reel import prep
        prep.run(R, only=(opt("only") or "").split(",") if opt("only") else None, force=force)
    if step == "transcript":
        from kit.reel import transcript
        transcript.fix(R.TAKE, R.mod.TRANSCRIPT, getattr(R.mod, "TIME_FIX", None))
    if step in ("edl", "all"):
        from kit.reel import edl
        edl.run(R, force="--force" in sys.argv, words_only="--words" in sys.argv, voice_only="--voice" in sys.argv)
    if step in ("joins", "all"):
        from kit.reel import joins
        code = joins.run(R, relisten="--no-relisten" not in sys.argv)
        if code and "--force" not in sys.argv:
            raise SystemExit(code)
    if step in ("hide", "all") and getattr(R, "HIDE", None):
        from kit.reel import hide
        hide.run(R)
    if step in ("build", "all"):
        from kit.reel import build
        build.build(R, sample=sample)
    if step == "sample":
        from kit.reel import build
        build.build(R, sample=True)
    if step in ("render", "all"):
        from kit.reel import build
        raise SystemExit(build.render(R, sample=sample, draft="--draft" in sys.argv))
    if step == "snap":
        from kit.reel import build
        build.snap(R, [float(x) for x in (opt("at") or "").split(",") if x], sample=sample)


if __name__ == "__main__":
    main()
