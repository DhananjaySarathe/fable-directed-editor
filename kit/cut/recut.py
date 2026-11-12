"""Re-cut an assembled A-roll (ungraded or graded) to a new frame map without going back to the takes or re-grading.

A cut tweak (an edge moved by a few frames, a sentence restored from frames already in the cut) used to mean
rebuilding the 4K A-roll from the takes, re-matting and re-grading it: over an hour on films/ai-workflows (2026-10-10).
When every frame of the new cut is already in the old one, each new frame is simply looked up:

    uv run python -m kit.cut.recut --old-map=<old aroll.map.json> --old=<old video> --new-map=<new aroll.map.json> \\
        --out=<new video> [--matte-old=<dir> --matte-new=<dir>] [--crf=10] [--preset=veryfast] [--max-miss=40]

A map is [[take, source_frame], ...] per output frame (edl.py writes it). A new frame that isn't in the old cut takes
the nearest source frame of the same take (+-2 frames, a one-frame repeat nobody sees). More misses than --max-miss,
or a miss farther than 2 frames, stops it: those frames need the takes.
With --matte-old/--matte-new the person mattes (f00001.png...) are remapped the same way, so the grade can run on the
new cut without re-matting.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                          "-of", "json", str(p)], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], round(int(n) / int(d))


def lookup(old_map, new_map, reach=2):
    """For every new frame: the index of the same (take, frame) in the old cut, else the nearest same-take frame."""
    where = {}
    for i, (c, f) in enumerate(old_map):
        where.setdefault((c, f), i)
    idx, miss = [], []
    for k, (c, f) in enumerate(new_map):
        i = where.get((c, f))
        if i is None:
            for d in range(1, reach + 1):
                i = where.get((c, f - d), where.get((c, f + d)))
                if i is not None:
                    break
            miss.append((k, c, f, i))
        if i is None:
            raise SystemExit(f"recut: new frame {k} (take {c}, frame {f}) is not within {reach} frames of the old cut: rebuild it from the takes")
        idx.append(i)
    return idx, miss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-map", required=True); ap.add_argument("--old", required=True)
    ap.add_argument("--new-map", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--matte-old"); ap.add_argument("--matte-new")
    ap.add_argument("--crf", default="10"); ap.add_argument("--preset", default="veryfast"); ap.add_argument("--max-miss", type=int, default=40)
    a = ap.parse_args()
    old_map, new_map = json.load(open(a.old_map)), json.load(open(a.new_map))
    idx, miss = lookup(old_map, new_map)
    print(f"recut: {len(old_map)} -> {len(new_map)} frames; {len(miss)} taken from a neighbouring source frame", flush=True)
    if len(miss) > a.max_miss:
        sys.exit(f"recut: {len(miss)} frames missing (> {a.max_miss}): rebuild from the takes")
    if a.matte_old and a.matte_new:
        mo, mn = Path(a.matte_old), Path(a.matte_new)
        shutil.rmtree(mn, ignore_errors=True); mn.mkdir(parents=True)
        for k, i in enumerate(idx):
            shutil.copyfile(mo / f"f{i + 1:05d}.png", mn / f"f{k + 1:05d}.png")
        print(f"recut: mattes -> {mn}", flush=True)
    w, h, fps = probe(a.old)
    fb = w * h * 3
    # the new order is non-decreasing in the old cut except where a piece repeats or reorders: stream forward, and
    # restart the decoder at the frame when an index goes back
    def decoder(start):
        return subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{(start - 0.5) / fps:.5f}" if start else "0", "-i", a.old, "-an",
                                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                            "-c:v", "libx264", "-crf", a.crf, "-preset", a.preset, "-g", "15", "-pix_fmt", "yuv420p",
                            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", a.out],
                           stdin=subprocess.PIPE)
    dec, cur, buf, restarts = decoder(0), -1, None, 0
    for i in idx:
        if i < cur:
            dec.stdout.close(); dec.kill(); dec, cur, buf = decoder(i), i - 1, None; restarts += 1
        while cur < i:
            nb = dec.stdout.read(fb)
            if len(nb) < fb:
                raise SystemExit(f"recut: the old video ended at frame {cur}")
            buf, cur = nb, cur + 1
        enc.stdin.write(buf)
    dec.stdout.close(); dec.kill()
    enc.stdin.close(); enc.wait()
    print(f"recut: -> {a.out} ({len(idx)} frames, {restarts} decoder restarts)")


if __name__ == "__main__":
    main()
