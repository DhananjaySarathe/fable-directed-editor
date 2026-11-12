"""The documentary example's cutaways: three generated clips (no real footage), so kit/film's documentary path (cutaways,
natural sound, J/L cuts, D.doc, HF.doc) runs end to end on the kit/film example take.

    uv run python kit/film/example/make_take.py                        # the take (once; shared with kit/film/example)
    uv run python kit/presets/documentary/example/make_broll.py        # -> output/temp/films/<this film>/scratch/broll/
    uv run python -m kit.film kit/presets/documentary/example prep | cut | build | draft
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from kit.paths import Film  # noqa: E402

CLIPS = {
    # name: (video source, seconds, audio source or None): an "insert" with room sound, a "screen", a "location"
    "insert": ("testsrc2=size=1920x1080:rate=30", 6.0, "anoisesrc=color=pink:amplitude=0.05:sample_rate=48000"),
    "screen": ("smptehdbars=size=2560x1440:rate=60", 8.0, None),
    "location": ("mandelbrot=size=1920x1080:rate=30", 6.0, "sine=frequency=180:sample_rate=48000"),
}


def main():
    out = Film(HERE / "film.py").scratch / "broll"
    out.mkdir(parents=True, exist_ok=True)
    for name, (v, d, a) in CLIPS.items():
        args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", str(d), "-i", v]
        if a:
            args += ["-f", "lavfi", "-t", str(d), "-i", a, "-c:a", "aac", "-b:a", "160k"]
        args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out / f"{name}.mp4")]
        subprocess.run(args, check=True)
        print("->", out / f"{name}.mp4")


if __name__ == "__main__":
    main()
