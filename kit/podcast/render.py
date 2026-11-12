"""Picture for a podcast: every shot cropped from the one camera, graded, rendered in parallel, joined without re-encode.

A segment = one shot inside one edit piece: its source range, its crop. ffmpeg seeks each one exactly (decoding from
the keyframe before), crops, scales to RES with lanczos, grades (look.filters) and encodes; the segments are joined
with the concat demuxer (-c copy) and muxed with the podcast mix. Lower thirds (PEOPLE names) overlay the first single
shot of each person (4 s), drawn with PIL in the preset's type.
"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parents[1] / "fonts"


def transfer(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer", "-of", "csv=p=0", str(src)],
                         capture_output=True, text=True).stdout.strip().strip(",").split(",")[0]   # side data adds empty fields
    return out if out in ("arib-std-b67", "smpte2084") else None


def tonemap(src):
    """HDR (iPhone HLG / PQ) -> SDR bt709: the same zscale + hable chain as shorts probe (normalize.py); '' for SDR."""
    tin = transfer(src)
    if not tin:
        return ""
    return (f"zscale=tin={tin}:pin=bt2020:min=bt2020nc:t=linear:npl=100,format=gbrpf32le,"
            "zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")


def pick(rects, t):
    """rects: {(kind, who): rect}, or per joined take [{a, b, rects}] chosen by the source time."""
    return rects if isinstance(rects, dict) else next((r["rects"] for r in rects if r["a"] <= t < r["b"]), rects[-1]["rects"])


def segments(edl, shots, rects):
    segs = []
    for p in edl["pieces"]:                                              # output order (pieces may jump in the source)
        for s in shots:
            a, b = max(s["a"], p["out_a"]), min(s["b"], p["out_b"])
            if b - a > 1e-3:
                key = ("wide", None) if s["kind"] == "wide" else (s["kind"], s["who"])
                src_a = p["src_a"] + a - p["out_a"]
                segs.append({"out_a": a, "out_b": b, "src_a": src_a, "rect": pick(rects, src_a)[key], "shot": s})
    return sorted(segs, key=lambda g: g["out_a"])


def lower_third(path, name, sub="", W=1920, H=1080):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f1, f2 = ImageFont.truetype(str(FONTS / "Inter-800.ttf"), 46), ImageFont.truetype(str(FONTS / "Inter-500.ttf"), 30)
    x, y = 90, H - 230
    w = max(d.textlength(name, font=f1), d.textlength(sub, font=f2) if sub else 0) + 60
    d.rounded_rectangle((x, y, x + w, y + (124 if sub else 84)), radius=18, fill=(14, 14, 18, 215))
    d.rectangle((x, y, x + 8, y + (124 if sub else 84)), fill=(224, 69, 123, 255))
    d.text((x + 30, y + 16), name, font=f1, fill=(255, 255, 255, 255))
    if sub:
        d.text((x + 30, y + 74), sub, font=f2, fill=(220, 220, 228, 255))
    im.save(path)


def render(P, edl, shots, rects, grade_vf, mix_wav, out, preview=None, workers=6):
    res = 720 if preview else P.RES
    W = round(res * 16 / 9 / 2) * 2
    segs = segments(edl, shots, rects)
    if preview:                                                          # clip the segments to the window (picture = sound)
        a, b = preview
        clipped = []
        for sg in segs:
            oa, ob = max(sg["out_a"], a), min(sg["out_b"], b)
            if ob - oa > 1e-3:
                clipped.append(dict(sg, out_a=oa, out_b=ob, src_a=sg["src_a"] + oa - sg["out_a"]))
        segs = clipped
    tm = tonemap(P.source)
    tmp = P.work / ("seg_preview" if preview else "seg")
    tmp.mkdir(exist_ok=True)
    # lower thirds: the first single of each person after the open
    lt, seen = {}, set()
    for s in (shots if getattr(P, "LOWER_THIRDS", True) else []):
        if s["kind"] == "single" and s["who"] and s["who"] not in seen and s["b"] - s["a"] >= 3:
            seen.add(s["who"])
            name = P.PEOPLE.get(s["who"], s["who"]) if isinstance(P.PEOPLE.get(s["who"]), str) else P.PEOPLE.get(s["who"], {}).get("name", s["who"])
            sub = "" if isinstance(P.PEOPLE.get(s["who"]), str) else P.PEOPLE.get(s["who"], {}).get("sub", "")
            png = tmp / f"lt_{s['who']}_{res}.png"
            lower_third(png, name, sub, W, res)
            lt[s["who"]] = (s["a"] + 0.6, s["a"] + 4.6, png)

    def one(i_seg):
        i, sg = i_seg
        o = tmp / f"s{i:05d}.mp4"
        x, y, w, h = sg["rect"]
        dur = sg["out_b"] - sg["out_a"]
        # the grade runs at the crop's own size (a 4K episode upscales ~1.4-2x: 2-4x fewer pixels to denoise and colour),
        # then lanczos up, then the sharpening and the vignette at the output size
        parts = grade_vf.split(",") if grade_vf and grade_vf != "null" else []
        post = [g for g in parts if g.startswith(("unsharp", "vignette"))]
        pre = [g for g in parts if g not in post]
        vf = ",".join([f"crop={w}:{h}:{x}:{y}", tm.rstrip(",")] + pre + [f"scale={W}:{res}:flags=lanczos"] + post + [f"fps={P.FPS}", "format=yuv420p"])
        vf = vf.replace(",,", ",").lstrip(",")
        cmd = ["ffmpeg", "-v", "error", "-y", *(["-hwaccel", "videotoolbox"] if tm else []), "-ss", f"{sg['src_a']:.3f}", "-i", str(P.source)]
        who = sg["shot"]["who"]
        if who in lt and lt[who][0] < sg["out_b"] and lt[who][1] > sg["out_a"]:
            a0, a1, png = lt[who]
            la, lb = a0 - sg["out_a"], a1 - sg["out_a"]
            cmd += ["-loop", "1", "-i", str(png), "-filter_complex",
                    f"[0:v]{vf}[v];[1:v]format=rgba,fade=t=in:st={max(0, la):.2f}:d=0.3:alpha=1,fade=t=out:st={max(0, lb - 0.3):.2f}:d=0.3:alpha=1[l];"
                    f"[v][l]overlay=0:0:enable='between(t,{la:.2f},{lb:.2f})':shortest=1[o]", "-map", "[o]"]
        else:
            cmd += ["-vf", vf]
        if res > 1080 and not preview:                                   # 4K: the media engine (x264 ran at ~0.16x real time)
            # the media engine at the original's bitrate class (his iPhone 4K60 HEVC is ~105 Mbps): HEVC, 100 Mbps
            enc = ["-c:v", "hevc_videotoolbox", "-b:v", "100M", "-maxrate", "130M", "-bufsize", "200M", "-tag:v", "hvc1", "-profile:v", "main", "-g", str(2 * P.FPS),
                   "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
        else:
            enc = ["-c:v", "libx264", "-crf", "20" if preview else "15", "-preset", "veryfast" if preview else "medium", "-g", "60"]
        cmd += ["-t", f"{dur:.3f}", "-an", *enc, str(o)]
        subprocess.run(cmd, check=True)
        return o

    with ThreadPoolExecutor(workers) as ex:
        files = list(ex.map(one, enumerate(segs)))
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    vid = tmp / "video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vid)], check=True)
    a_args = ["-i", str(mix_wav)]
    if preview:
        a_args = ["-ss", f"{preview[0]:.3f}", "-t", f"{preview[1] - preview[0]:.3f}", "-i", str(mix_wav)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(vid), *a_args, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-aac_pns", "0", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out)], check=True)
    return out, len(segs)
