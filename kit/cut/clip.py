"""A highlight clip from a finished film: whole-sentence word ranges cut out of the rendered video, joined with soft
audio edges, plus a branded end card. For X / LinkedIn / teaser posts (films/ai-workflows, 2026-10-10).

    uv run python -m kit.cut.clip <film edl.json> <rendered.mp4> <out.mp4> --ranges=0-50,2007-2041,... \\
        [--card="Full *breakdown*|in the reply ↓"] [--handles="<a>,<b>" (default: kit/brand.json end_card)] \\
        [--card-audio=<start s>] [--card-dur=2.5] [--fps=30]

- A range is first-last word id, inclusive, in the edl's ids. It must be whole sentences: the tool refuses a range
  whose last word doesn't end a sentence (. ? !) unless --loose. Cuts sit halfway into the gap to the next or previous
  word in the cut, at most 0.35 s from the word, so they land in the pause, never inside a word.
- Each join gets 40 ms audio fades. The picture is a hard cut, which reads as a scene change in a graphics-led film.
- The card is a pastel frame (the pastel_box world) with the title in Instrument Serif ("*word*" = italic accent,
  "|" = a new line) and the handles as pills, with a slow 3 % push so it never freezes. Its sound is the film's own
  audio from --card-audio (for example the music under the film's end card), faded out.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = Path(__file__).resolve().parents[1] / "fonts"
HANDLES = json.loads((FONTS.parent / "brand.json").read_text())["end_card"]     # the channel's handles live only there


def spans(edl, ranges, loose=False):
    W = [w for w in edl["words"] if w["text"]]
    pos = {w["i"]: k for k, w in enumerate(W)}
    out = []
    for a, b in ranges:
        if a not in pos or b not in pos:
            raise SystemExit(f"clip: word {a if a not in pos else b} is not in the cut")
        if not loose and not W[pos[b]]["text"].rstrip('"”').endswith((".", "?", "!")):
            raise SystemExit(f"clip: range {a}-{b} ends on {W[pos[b]]['text']!r}, not a sentence end (whole sentences only; --loose to override)")
        i, j = pos[a], pos[b]
        s = W[i]["t"] - min(0.35, (W[i]["t"] - W[i - 1]["e"]) / 2) if i > 0 else 0.0
        e = W[j]["e"] + min(0.35, (W[j + 1]["t"] - W[j]["e"]) / 2) if j + 1 < len(W) else W[j]["e"] + 0.35
        out.append((round(max(0.0, s), 3), round(e, 3), " ".join(w["text"] for w in W[i:j + 1])))
    return out


def card(path, title, handles, size=(1920, 1080), accent=(79, 59, 224), ink=(23, 22, 31)):
    W, H = size
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    img = np.ones((H, W, 3), np.float32) * np.array([246, 241, 236], np.float32)
    for (cx, cy, r, col, k) in [(260, 160, 760, (176, 160, 255), .85), (1700, 340, 720, (255, 190, 160), .85), (600, 1080, 660, (170, 232, 205), .75),
                                (1450, 1000, 560, (255, 226, 170), .55)]:
        m = np.clip(1 - np.hypot(x - cx, y - cy) / r, 0, 1) ** 1.6 * k
        img = img * (1 - m[..., None]) + np.array(col, np.float32) * m[..., None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    d = ImageDraw.Draw(im)
    reg, ita = ImageFont.truetype(str(FONTS / "InstrumentSerif-Regular.ttf"), 132), ImageFont.truetype(str(FONTS / "InstrumentSerif-Italic.ttf"), 132)
    sym = ImageFont.truetype(str(FONTS / "Inter-700.ttf"), 104)                 # arrows and symbols: the serif has no glyphs for them
    font = lambda t, it: sym if not any(ch.isalnum() for ch in t) else (ita if it else reg)
    lines = title.split("|")
    top = 300 if len(lines) > 1 else 380
    for li, ln in enumerate(lines):
        parts = [(p.strip("*"), p.startswith("*")) for p in ln.split()]
        widths = [d.textlength(t + " ", font=font(t, it)) for t, it in parts]
        xx = (W - sum(widths) + d.textlength(" ", font=reg)) / 2
        for (t, it), w in zip(parts, widths):
            f = font(t, it)
            d.text((xx, top + li * 150 + (22 if f is sym else 0)), t, font=f, fill=accent if (it or f is sym) else ink)
            xx += w
    pill = ImageFont.truetype(str(FONTS / "Inter-700.ttf"), 34)
    hs = [h.strip() for h in handles if h.strip()]
    ws = [d.textlength(h, font=pill) + 64 for h in hs]
    xx, yy = (W - sum(ws) - 24 * (len(hs) - 1)) / 2, top + len(lines) * 150 + 70
    for k, (h, w) in enumerate(zip(hs, ws)):
        d.rounded_rectangle((xx, yy, xx + w, yy + 76), radius=38, fill=ink if k == 0 else accent)
        d.text((xx + 32, yy + 18), h, font=pill, fill=(255, 255, 255))
        xx += w + 24
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl"); ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--ranges", required=True); ap.add_argument("--card", default=""); ap.add_argument("--handles", default="")
    ap.add_argument("--card-audio", type=float); ap.add_argument("--card-dur", type=float, default=2.5)
    ap.add_argument("--fps", type=int, default=30); ap.add_argument("--loose", action="store_true")
    a = ap.parse_args()
    edl = json.load(open(a.edl))
    ranges = [tuple(int(v) for v in r.split("-")) for r in a.ranges.split(",")]
    segs = spans(edl, ranges, a.loose)
    tmp = Path(tempfile.mkdtemp())
    parts = []
    for k, (s, e, text) in enumerate(segs):
        p = tmp / f"s{k:02d}.mp4"
        d = e - s
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.3f}", "-i", a.video, "-t", f"{d:.3f}",
                        "-vf", f"fps={a.fps},format=yuv420p", "-af", f"afade=t=in:d=0.04,afade=t=out:st={d - 0.04:.3f}:d=0.04",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", str(p)], check=True)
        parts.append(p)
        print(f"  {s:7.2f}-{e:7.2f} ({d:4.1f} s)  {text[:90]}")
    if a.card:
        png, p = tmp / "card.png", tmp / "card.mp4"
        card(png, a.card, a.handles.split(",") if a.handles else HANDLES)
        n, dur = int(a.card_dur * a.fps), a.card_dur
        zoom = f"zoompan=z='1+0.03*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1920x1080:fps={a.fps}"
        cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(a.fps), "-i", str(png)]
        if a.card_audio is not None:
            cmd += ["-ss", f"{a.card_audio:.3f}", "-t", f"{dur:.3f}", "-i", a.video, "-map", "0:v", "-map", "1:a",
                    "-af", f"afade=t=in:d=0.04,afade=t=out:st={dur - 1.0:.3f}:d=1.0"]
        else:
            cmd += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a"]
        cmd += ["-vf", f"{zoom},format=yuv420p", "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                "-c:a", "aac", "-b:a", "256k", "-ar", "48000", str(p)]
        subprocess.run(cmd, check=True)
        parts.append(p)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", a.out], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.out], capture_output=True, text=True).stdout)
    print(f"-> {a.out} ({dur:.1f} s, {len(segs)} pieces{' + card' if a.card else ''})")


if __name__ == "__main__":
    main()
