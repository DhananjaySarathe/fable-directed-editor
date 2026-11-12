"""Raw clip -> the speaker cut out and graded, as ONE transparent VP9 WebM (the only file kept).

Frames, Vision masks and the graded RGBA frames live in a temporary folder that is always deleted afterwards.
Disk kept: ~85 MB per minute at 1920x1080/30 fps (vs ~1.2 GB/min for per-frame PNG cut-outs). The WebM keeps the
clip's own timing, so a HyperFrames composition cuts it with data-media-start / data-duration / data-playback-rate.

    python3 kit/look/cutout.py <clip.mp4> <out.webm> [--from=SEC] [--to=SEC] [--crf=22] [--light=0..1] [--plate=room.mp4]

--plate also writes the whole frame with the same grade as an H.264 file, frame for frame with the cut-out: a speaker
card shows his real room from it (a cut-out on a gradient inside a card reads as a sticker), the stage uses the cut-out.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

KIT = Path(__file__).resolve().parents[1]


def arg(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    a, b, crf = float(arg("from", 0)), arg("to"), arg("crf", "22")
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                            "-of", "csv=p=0", str(src)], capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h, fps = int(probe[0]), int(probe[1]), round(eval(probe[2]))
    tmp = Path(tempfile.mkdtemp(prefix="cutout_"))
    try:
        frames, masks, look = tmp / "frames", tmp / "masks", tmp / "look"
        frames.mkdir()
        cut = ["-ss", f"{a:.3f}"] + (["-to", f"{float(b):.3f}"] if b else [])
        subprocess.run(["ffmpeg", "-v", "error", "-y", *cut, "-i", str(src), "-q:v", "2", str(frames / "f%05d.jpg")], check=True)
        subprocess.run([str(KIT / "bin/personseg"), str(frames), str(masks), "--mask"], check=True)
        subprocess.run([sys.executable, str(KIT / "look/look.py"), str(frames), str(masks), str(look)] + [f"--light={arg('light')}"] * bool(arg("light"))
                       + ["--plate"] * bool(arg("plate")), check=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                                "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", crf, "-row-mt", "1", "-deadline", "good",
                                "-cpu-used", "4", "-g", str(fps // 2), "-auto-alt-ref", "0", str(out)], stdin=subprocess.PIPE)
        names = sorted(look.glob("f*.webp"))
        for f in names:
            enc.stdin.write(np.asarray(Image.open(f).convert("RGBA")).tobytes())
        enc.stdin.close()
        if enc.wait():
            raise SystemExit("webm encode failed")
        if arg("plate"):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(look / "plate/f%05d.jpg"), "-c:v", "libx264", "-crf", "14",
                            "-preset", "medium", "-pix_fmt", "yuv420p", "-g", str(fps), "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", arg("plate")], check=True)
        mb = out.stat().st_size / 1e6
        print(f"{out.name}: {len(names)} frames ({len(names) / fps:.1f} s), {mb:.1f} MB, {mb / (len(names) / fps) * 60:.0f} MB/min; starts at source {a:.3f} s")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
