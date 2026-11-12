"""Full-frame grade for a talking head in a real room (no cut-out, so no matte edges can ever show).

The room stays; the look comes from light, not masks:
  1. tone: the clip's own black point and wall level are measured, then one luma curve sets blacks deep, lifts skin and
     rolls the bright wall off so the subject is no longer darker than the background (top channels: subject brightest);
  2. a soft key light that follows the face (a wide gaussian from the head track, offset to one side for shape, slightly
     warm) and a gentle falloff on the far cheek; it also brushes the wall a little, the way a real lamp would;
  3. an elliptical vignette that pulls the frame edges down, warm highlights / neutral shadows, saturation up except skin;
  4. luma-only sharpening (phone footage is usually upscaled) and a whisper of fine grain so it reads as film, not plastic.

The head track comes from the Vision person mask at quarter resolution (kit/bin/personseg), smoothed over time, and is
written next to the output as <out>.face.json: per frame [cx, cy, head_w] in output pixels (for framing / punch-ins).

    python3 kit/look/grade.py <clip.mp4> <out.mp4> [--light=1.0] [--test=5,40,90]   (--test writes before/after JPGs)
    python3 kit/look/grade.py <clip.mp4> <out.mp4> --look=cinematic                 (one look: kit/look/looks.py LOOKS)
    python3 kit/look/grade.py <clip.mp4> <out.mp4> --looks=looks.json               ([{t, look, fade}]: looks per scene)
    python3 kit/look/grade.py <clip.mp4> sheet.jpg --sheet=12.5 [--track=...]        (one frame in every look, labelled)
    ... --room=shelf                    a room profile (looks.ROOMS): tone targets for a different background
    ... --matte=<dir>                   person mattes (kit/bin/personseg --mask on the clip's frames, f00001.png ...):
                                        portrait mode, the room defocused and set back (per look, from the room's "bg")

To grade only what an edit keeps: track the whole take once (`--track-only`), cut the picture, then grade the cut with
`--track=<take>.face.json --map=<cut>.map.json` (the map gives each cut frame's frame in the take).

Look v2 (opt-in, kit/look/v2.py; the same looks, rooms, mattes, --looks plans, --test and --sheet):
    ... --v2                            per-shot exposure / white balance from the face, sigmoid tone curve, subtractive
                                        saturation, skin secondaries, halation, grain and dither (see kit/look/README.md)
    ... --v2 --track-only               a YuNet face track (kit/look/faces.py) instead of the person-mask head track
    ... --shots=12.4,80.2               shot boundaries in seconds (each shot gets its own balance; default: one shot)
    ... --balance=<out>.balance.json    reuse the per-shot balance of an earlier grade (written next to every v2 output)
    ... --reel                          Reels/Shorts finish: lifted shadows (+0.02), half grain, gentler vignette

What a frame is graded as (2026-10-22, kit/film GRADE kinds; any engine):
    ... --passthrough=12.4-80.2,90-95   output seconds written exactly as decoded (screen recordings: UI text stays crisp
                                        and neutral, no orange halo, no greyed page whites); not analysed
    ... --region=3184,1504,576,576      grade only this rectangle (x, y, w, h in the clip's pixels; a Framecast cam
                                        bubble), the rest passes through; its balance is measured on the rectangle
    ... --region-at=12.4-80.2           only in these seconds (elsewhere the whole frame is graded); default everywhere
                                        (every range's edges are shot edges: a shot is one mode, --shots or not)
    Every edge (--shots, the ranges, a --looks switch) snaps to its nearest frame, so a range a-b is exactly frames
    round(a*fps) .. round(b*fps)-1 even when the edge was written to the millisecond; a --sheet / --test time is the
    frame on screen then, decoded exactly (edge_frame / frame_at / decode_frame).
Sheets for choosing a look:
    ... --sheet=8,30,120 --sheet-looks=natural,clean [--stage=#FFFFFF]
                                        several times: one row per time (source + each look), the scopes numbers under
                                        each tile and in <sheet>.json; --stage draws each tile the way the page shows him
                                        (a card and a circle on that colour)

Every video it writes is complete or absent: frames go to <out>.part, which becomes <out> only when the frames graded,
the source's frames and the file's frames agree, and <out>.ok then records what it was graded from and the settings it
was asked for (kit/look/ffio.py; kit/film and kit/reel trust a graded track only through it, and re-grade when their
settings changed). Decoding converts YUV with accurate rounding and full
chroma interpolation (whites reach 255), and the output is tagged BT.709 in the stream itself (x264 VUI).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from look import luma, skin_weight, smoothstep  # noqa: E402
import looks as LK  # noqa: E402
import ffio as FF  # noqa: E402

# the targets, light, colour and finish of every look live in kit/look/looks.py (LOOKS); "natural" is the approved
# preset_paper_studio grade: black 0.03, skin 0.50, wall 0.87, key 0.20, falloff 0.08, vignette 0.16, sat 1.10, grain 1 %


def arg(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def probe(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                          "-of", "csv=p=0", str(src)], capture_output=True, text=True, check=True).stdout.strip().split(",")
    return int(out[0]), int(out[1]), round(eval(out[2]))


def head_track(src, W, H):
    """Per frame (cx, cy, head width) in full-res pixels, from Vision masks at quarter size; smoothed (median + EMA)."""
    tmp = Path(tempfile.mkdtemp(prefix="grade_"))
    try:
        fr, mk = tmp / "f", tmp / "m"
        fr.mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"scale={W // 4}:{H // 4}", "-q:v", "3", str(fr / "f%05d.jpg")], check=True)
        subprocess.run([str(KIT / "bin/personseg"), str(fr), str(mk), "--mask"], check=True, capture_output=True)
        raw = []
        for p in sorted(mk.glob("*.png")):
            a = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) > 127
            rows = np.where(a.sum(1) > 3)[0]
            if not len(rows):
                raw.append(None); continue
            y0 = rows[0]
            xs = np.where(a[min(a.shape[0] - 1, y0 + int(0.07 * a.shape[0]))])[0]
            if len(xs) < 4:
                raw.append(None); continue
            hw = (xs[-1] - xs[0])
            raw.append(((xs[0] + xs[-1]) / 2 * 4, (y0 + 0.75 * hw) * 4, hw * 4))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    last = next((r for r in raw if r), (W / 2, H * 0.42, W * 0.16))
    filled = []
    for r in raw:
        last = r or last
        filled.append(last)
    arr = np.array(filled, np.float64)
    k = 7
    pad = np.pad(arr, ((k, k), (0, 0)), mode="edge")
    med = np.array([np.median(pad[i:i + 2 * k + 1], 0) for i in range(len(arr))])
    out, s = [], med[0]
    for m in med:                                   # slow EMA: the light drifts with the head, it never jitters
        s = s + 0.12 * (m - s)
        out.append(s.copy())
    return np.array(out)


def levels(src):
    """The clip's black point (0.5th pct luma) and its wall level (median of the top band), over sampled frames."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), *FF.vf("fps=0.5", FF.scale(480, 270)), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 270, 480, 3).astype(np.float32) / 255
    y = luma(fr)
    sk = skin_weight(fr) > 0.6
    return float(np.percentile(y, 0.5)), float(np.median(y[:, 5:60])), float(np.median(y[sk])) if sk.any() else 0.4


def tone(y, lo, wall, skin, tg):
    """Monotone luma curve through (lo, black), (skin, skin), (wall, wall) targets with a soft toe and a shoulder."""
    xs = np.array([0.0, lo, skin, wall, 1.0])
    ys = np.array([0.0, tg["black"], tg["skin"], tg["wall"], min(0.93, tg["wall"] + (1 - wall) * 0.8)])
    xs, ys = np.maximum.accumulate(xs + np.arange(5) * 1e-4), np.maximum.accumulate(ys)
    # smooth monotone interpolation (PCHIP-like via cv2-free numpy): piecewise cubic Hermite with Fritsch-Carlson slopes
    h = np.diff(xs); d = np.diff(ys) / h
    m = np.zeros(5); m[0], m[-1] = d[0], d[-1]
    for i in range(1, 4):
        m[i] = 0 if d[i - 1] * d[i] <= 0 else 3 * (h[i - 1] + h[i]) / ((2 * h[i] + h[i - 1]) / d[i - 1] + (h[i] + 2 * h[i - 1]) / d[i])
    yi = np.clip(y, 0, 1)
    i = np.clip(np.searchsorted(xs, yi) - 1, 0, 3)
    t = (yi - xs[i]) / h[i]
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1]


_G = {}
LS = 4                                      # the light and vignette are smooth: computed at 1/4 size, then upsampled


def _lut(x, a, b):
    """smoothstep(a, b, x) as a 1024-entry table lookup on x in 0..1 (x is clipped)."""
    key = ("ss", a, b)
    if key not in _G:
        _G[key] = smoothstep(a, b, np.linspace(0, 1, 1024, dtype=np.float32)).astype(np.float32)
    return _G[key][np.clip((x * 1023 + 0.5).astype(np.int32), 0, 1023)]


def _look_frame(img, cx, cy, hw, W, H, lo, wall, skin, light, seed, name, room=None, matte=None):
    """One frame through one look: tone targets -> face key / falloff / vignette -> colour (LUT) -> halation ->
    portrait background (with a person matte) -> sharpen, grain. `room` picks a room profile (looks.ROOMS)."""
    key_ = (name, room)
    if ("look",) + key_ not in _G:
        _G[("look",) + key_] = LK.look_for(name, room)
    L = _G[("look",) + key_]
    lt, fin = L["light"], L["finish"]
    name = key_
    if ("grid", name) not in _G:
        h4, w4 = H // LS, W // LS
        yy, xx = (np.mgrid[0:h4, 0:w4].astype(np.float32) + 0.5) * LS
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.46) / (H * 0.70)) ** 2)
        _G[("grid", name)] = (yy, xx, (1 - lt["vignette"] * smoothstep(0.45, 1.25, r)).astype(np.float32))
        lut = tone(np.linspace(0, 1, 4096), lo, wall, skin, lt)
        _G[("tone", name)] = (lut / np.maximum(np.linspace(0, 1, 4096), 1e-4)).astype(np.float32)   # gain per luma level
        if L["colour"].get("mode") != "paper":
            _G[("lut", name)] = LK.bake(name[0], colour=L["colour"], tag=room or "")
    if "grain" not in _G:
        rng = np.random.default_rng(7)                                                         # 6 unit grain plates, cycled
        _G["grain"] = [cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.7) for _ in range(6)]
    yy, xx, vig = _G[("grid", name)]
    y = luma(img)
    out = img * _G[("tone", name)][np.clip((y * 4095 + 0.5).astype(np.int32), 0, 4095)][..., None]
    # light: a wide soft key on the camera-left cheek, a little falloff on the far side; both centred on the head track
    key = np.exp(-(((xx - (cx - 0.30 * hw)) / (1.05 * hw)) ** 2 + ((yy - (cy - 0.05 * hw)) / (1.25 * hw)) ** 2))
    far = np.exp(-(((xx - (cx + 0.55 * hw)) / (0.55 * hw)) ** 2 + ((yy - cy) / (1.0 * hw)) ** 2))
    # the light lands mostly on skin (a soft colour weight, no edges); the wall only catches a little spill
    small = cv2.resize(out, (W // LS, H // LS), interpolation=cv2.INTER_AREA)
    sk = cv2.GaussianBlur(skin_weight(small), (0, 0), 5 / LS)
    ks = lt.get("key_skin", 0.55)                                         # how much the key prefers skin (strong keys: less, or it looks patchy)
    key = key * ((1 - ks) + ks * sk)
    if matte is not None:                                                 # with a matte the key lands on the person, not on tan book spines
        key = key * (0.3 + 0.7 * cv2.GaussianBlur(cv2.resize(matte, (W // LS, H // LS), interpolation=cv2.INTER_AREA), (0, 0), 3))
    gain = cv2.resize(((1 + light * (lt["key"] * key - lt["fall"] * far)) * vig).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    tint = cv2.resize((light * lt.get("key_warm", 0.012) * key).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    out = out * gain[..., None] + tint[..., None] * np.array([1.0, 0.5, -0.4], np.float32)
    # colour: natural computes its paper-studio colour directly (exact); every other look goes through its baked LUT
    if L["colour"].get("mode") == "paper":
        out = LK.colour_op(np.clip(out, 0, 1), L["colour"]).astype(np.float32)
    else:
        out = LK.apply_lut(out, _G[("lut", name)])
    out = LK.halation(out, fin.get("halation", 0.0))
    bg = L.get("bg")
    if matte is not None and bg:                                          # portrait: the room behind is defocused, calmer, a little darker
        h2, w2 = H // 2, W // 2
        o2 = cv2.resize(out, (w2, h2), interpolation=cv2.INTER_AREA)
        m2 = cv2.resize(matte, (w2, h2), interpolation=cv2.INTER_AREA)
        b2 = 1 - m2
        sg = bg["blur"] * H / 1080 / 2
        # 1) defocus: a normalised (masked) blur, so the person never bleeds into the room; composited with a slightly
        #    eroded matte, so the unblurred rim of room that the matte always includes around hair is defocused too
        bl = cv2.GaussianBlur(o2 * b2[..., None], (0, 0), sg) / (cv2.GaussianBlur(b2, (0, 0), sg)[..., None] + 1e-3)
        me = cv2.GaussianBlur(cv2.erode(m2, np.ones((3, 3), np.uint8)), (0, 0), 1.0)
        me = cv2.resize(me, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        out = out * me + cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR) * (1 - me)
        # 2) separation as light, not as a cut-out: the room falls off smoothly away from the person (a wide blur of the
        #    matte), so darkening never draws a line around hair or fingers
        soft = cv2.resize(cv2.GaussianBlur(m2, (0, 0), 24 * H / 1080 / 2), (W, H), interpolation=cv2.INTER_LINEAR)
        soft = np.clip(soft * 1.25, 0, 1)[..., None]
        yb = luma(out)[..., None]
        sat = bg["sat"] + (1 - bg["sat"]) * soft
        out = (yb + (out - yb) * sat) * (bg["gain"] + (1 - bg["gain"]) * soft)
    # luma-only unsharp mask (on the person only when the room is defocused), then fine grain
    yo = luma(out)
    det = yo - cv2.GaussianBlur(yo, (0, 0), 1.3)
    if matte is not None and bg:
        det = det * (0.3 + 0.7 * matte)
    out = out + (fin.get("sharpen", 0.45) * det)[..., None]
    if fin.get("grain"):
        out = out + (_G["grain"][seed % 6] * fin["grain"] * (1 - _lut(yo, 0.6, 1.0)))[..., None]
    return np.clip(out, 0, 1)


def load_matte(path, W, H):
    """A person matte (kit/bin/personseg --mask PNG, any size) as float32 HxW 0..1: the soft edge is tightened a little
    and feathered by ~1.5 px so hair and fingers blend instead of showing a line. Missing file -> None."""
    m = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if m is None:
        return None
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255
    m = np.clip((m - 0.08) / 0.84, 0, 1)
    return cv2.GaussianBlur(m, (0, 0), 1.5 * H / 1080)


_V2P = {}


def _v2_frame(buf, track, W, H, seed, look, room, matte, opts):
    """One frame through look v2 (kit/look/v2.py) with this frame's shot balance (opts["bal"][look])."""
    import faces as FC
    import v2 as V2
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    face = FC.from_track(*[float(v) for v in track])

    def one(name, u8):
        key = (name, room, opts.get("reel", False))
        if key not in _V2P:
            _V2P[key] = V2.params(name, room, opts.get("reel", False))
        return V2.grade(img, opts["bal"][name], _V2P[key], face, matte, seed, out_u8=u8)
    if isinstance(look, str):
        return one(look, True).tobytes()
    a, b, m = look
    out = one(a, False) * np.float32(1 - m) + one(b, False) * np.float32(m)
    return V2.quantise(out, seed, _V2P[(b, room, opts.get("reel", False))]["dither"]).tobytes()


def grade_frame(job):
    """job = (rgb bytes, (cx, cy, head_w), W, H, lo, wall, skin, light, frame index, look[, room, matte path, v2 opts])
    where look is a name or (name_a, name_b, mix) during a crossfade between looks (a 'lights dim' moment). With v2 opts
    ({"bal": {look: balance}, "reel": bool}) the frame goes through look v2 instead."""
    buf, (cx, cy, hw), W, H, lo, wall, skin, light, seed = job[:9]
    look = job[9] if len(job) > 9 else "natural"
    room = job[10] if len(job) > 10 else None
    mpath = job[11] if len(job) > 11 else None
    matte = load_matte(mpath, W, H) if mpath else None
    if len(job) > 12 and job[12]:
        return _v2_frame(buf, (cx, cy, hw), W, H, seed, look, room, matte, job[12])
    cx, cy, hw = float(cx), float(cy), float(hw)
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32) * np.float32(1 / 255)
    if isinstance(look, str):
        out = _look_frame(img, cx, cy, hw, W, H, lo, wall, skin, light, seed, look, room, matte)
    else:
        a, b, m = look
        out = (_look_frame(img, cx, cy, hw, W, H, lo, wall, skin, light, seed, a, room, matte) * (1 - m)
               + _look_frame(img, cx, cy, hw, W, H, lo, wall, skin, light, seed, b, room, matte) * m)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()


def look_at(t, plan):
    """The look at time t from a list of switches [{t, look, fade}] (fade 0 = a hard switch, e.g. on a cut)."""
    cur, prev, start, fade = plan[0]["look"], None, plan[0]["t"], 0.0
    for p in plan:
        if t >= p["t"]:
            prev, cur, start, fade = cur, p["look"], p["t"], p.get("fade", 0.0)
    if prev and cur and prev != cur and fade > 0 and t < start + fade:      # (no crossfade to or from a passthrough)
        m = (t - start) / fade
        return (prev, cur, m * m * (3 - 2 * m))
    return cur


def _ranges(s):
    """'12.4-80.2,90-95' -> [(12.4, 80.2), (90.0, 95.0)] (seconds); None or '' -> []."""
    out = []
    for part in filter(None, (s or "").split(",")):
        a, b = part.split("-", 1)
        out.append((float(a), float(b)))
    return out


# ------------------------------------------------------------------------------------------------ the frame grid
# 2026-10-22 (v11 review): every edge is a frame. The edges reach grade.py in seconds, written to the millisecond
# (kit/film writes its cut's frame edges, round(out_a * FPS) in cut.py write_track, as f"{t:.3f}"), and frames were
# classified by comparing i / fps against them. A frame k = 2 (mod 3) at 30 fps rounds UP past its own time (frame
# 1853 = 61.76667 s -> "61.767"), so the first frame of about a third of the stretches fell into the range before: a
# screen recording's first frame graded with the cam shot's balance, or his first frame after a passthrough written
# ungraded (a one-frame tone pop at the cut), and a sheet time just after an edge found no balance (SystemExit). Now an
# edge snaps to the nearest frame (edge_frame: the .3f error is <= 0.015 frame at 30 fps), ranges and shots are frame
# index ranges [f0, f1), and a frame is looked up by its index. A time that names a picture (--sheet, --test) is the
# frame on screen at that time (frame_at), and decode_frame decodes exactly that frame.
def edge_frame(t, fps) -> int:
    """An edge in seconds (a --shots time, a --passthrough / --region-at range end, a --looks switch) -> the frame it
    falls on: the nearest frame (the cut's own rule, kit/film/cut.py write_track)."""
    return int(round(float(t) * fps))


def frame_at(t, fps) -> int:
    """The frame on screen at t seconds (a --sheet / --test time): the last frame that starts at or before t (1e-6
    absorbs float error: 2.3 * 30 = 68.99999999999999 is frame 69)."""
    return int(np.floor(float(t) * fps + 1e-6))


def frame_mode(passes, region, region_at, fps):
    """frame index -> "pass" (written as decoded) | "region" (only the rectangle graded) | "full". The ranges are in
    seconds; a range a-b covers frames edge_frame(a) .. edge_frame(b) - 1."""
    P = [(edge_frame(a, fps), edge_frame(b, fps)) for a, b in passes]
    R = [(edge_frame(a, fps), edge_frame(b, fps)) for a, b in region_at]

    def mode(i):
        if any(a <= i < b for a, b in P):
            return "pass"
        if region and (not R or any(a <= i < b for a, b in R)):
            return "region"
        return "full"
    return mode


def in_region(tr, region):
    """A track entry [cx, cy, head_w] in a region's own pixels."""
    return (float(tr[0]) - region[0], float(tr[1]) - region[1], float(tr[2]))


def decode_frame(src, i, fps, W, H):
    """Frame i (0-based) as rgb24 bytes (accurate YUV -> RGB), or b'' past the end. The seek lands half a frame before
    it: an -ss on the frame's own time, written to the millisecond, can sit just after it, and ffmpeg then returns the
    next frame (measured: every frame k = 2 (mod 3) at 30 fps with .3f; scratchpad build/picture/fix2). kit/film/grade.py
    matte() seeks the same way."""
    ss = f"{(i - 0.5) / fps:.6f}" if i > 0 else "0"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", ss, "-i", str(src), "-frames:v", "1", *FF.vf(), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return raw if len(raw) >= W * H * 3 else b""


def shot_cuts(n_frames, fps, shots=None, bounds=()):
    """The shots' edges as frame indices: 0, the --shots times, the edges of every --passthrough / --region-at range
    (so a shot never mixes "pass", "region" and "full" frames: its mode is the mode of every frame in it), n_frames.
    Each time snaps to its frame (edge_frame), so a shot is frames [f0, f1)."""
    inner = {edge_frame(t, fps) for t in (shots or [])} | {edge_frame(t, fps) for t in bounds}
    return [0] + sorted(f for f in inner if 0 < f < n_frames) + [int(n_frames)]


def balance_shots(rows, fps):
    """A .balance.json -> [(f0, f1, balance or None)]; one from before the frame grid has seconds only (snapped)."""
    return [(int(s["f0"]) if "f0" in s else edge_frame(s["t0"], fps), int(s["f1"]) if "f1" in s else edge_frame(s["t1"], fps), s["bal"])
            for s in rows]


def shot_of(shots, i):
    """The (f0, f1, balance) shot holding frame i (frames past the last shot: the last one)."""
    return next((s for s in shots if s[0] <= i < s[1]), shots[-1])


def v2_balances(src, plan, track, mp, room, reel, fps, n_frames, mode=lambda i: "full", region=None, only=None, bounds=()):
    """Look v2's per-shot balance: [(f0, f1, {look: balance} | None)] (frame indices, a shot is frames f0 .. f1 - 1) for
    the shots in --shots (default one shot), each from up to 12 frames sampled across the shot (YuNet face on the frame,
    else the track; the person matte when given). The edges of the passthrough / region ranges (`bounds`) split shots
    too (shot_cuts), so a shot is one mode: one that passes through gets None; a "region" shot is measured on the
    rectangle only (its face, its blacks); with `only` (a sheet's times, each the frame on screen then: frame_at) shots
    holding none of them are skipped (None) too."""
    import faces as FC
    import v2 as V2
    cuts = shot_cuts(n_frames, fps, arg("shots").split(",") if arg("shots") else None, bounds)
    names = sorted({p["look"] for p in plan if p["look"]} | set(arg("sheet-looks", ",".join(LK.LOOKS)).split(",") if arg("sheet") else []))
    W, H, _ = probe(src)
    want = None if only is None else {min(frame_at(x, fps), n_frames - 1) for x in only}
    shots = []
    for f0, f1 in zip(cuts[:-1], cuts[1:]):
        t0, t1 = f0 / fps, f1 / fps
        md = mode(f0)                                                    # (every frame of a shot has one mode)
        if md == "pass" or (want is not None and not any(f0 <= f < f1 for f in want)):
            shots.append((f0, f1, None))
            continue
        n = int(np.clip((t1 - t0) / 3, 4, 12))
        frames = []
        for i in sorted({f0 + int((k + 0.5) * (f1 - f0) / n) for k in range(n)}):   # frames inside the shot, decoded exactly
            raw = decode_frame(src, i, fps, W, H)
            if not raw:
                continue
            im = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
            tr = track[min(i, len(track) - 1)]
            if md == "region":
                x, y, w, h = region
                im = np.ascontiguousarray(im[y:y + h, x:x + w])
                frames.append((im.astype(np.float32) / 255, FC.detect(im) or FC.from_track(*in_region(tr, region)), None))
                continue
            face = FC.detect(im) or FC.from_track(*tr)
            m = load_matte(mp(i), W, H) if mp(i) else None
            frames.append((im.astype(np.float32) / 255, face, m))
        bal = {nm: V2.analyse(frames, V2.params(nm, room, reel)) for nm in names}
        shots.append((f0, f1, bal))
        for nm in names[:1] if "natural" not in bal else ["natural"]:
            b0 = bal[nm]
            print(f"v2 shot {t0:.1f}-{t1:.1f}s ({nm}{', region' if md == 'region' else ''}): ev {b0['ev']:+.2f}, wb {b0['wb']}, skin rot {b0['skin_rot']:+.1f} deg, flare {b0['flare']:.5f}"
                  f" (skin {b0['src'].get('skin_hue', 0):.1f} deg / {b0['src'].get('skin_c', 0):.3f} -> {b0['out'].get('skin_hue', 0):.1f} / {b0['out'].get('skin_c', 0):.3f})")
        for nm in names:
            if "white" in bal[nm]:
                o = bal[nm]["out"]
                print(f"   {nm}: white {bal[nm]['white']:.3f} -> wall Y' {o.get('wall_y', 0):.3f} |CbCr| {o.get('wall_c', 0):.4f}, skin Y' {o['skin_y']:.3f}")
    return shots


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[k:k + 2], 16) for k in (0, 2, 4))


def stage_tile(im, face, stage, TW=640, TH=360):
    """The frame the way a page shows him (kit/hf canvas): on a stage of colour `stage` (RGB), as a rounded card (a soft
    shadow under it) and as a circle centred on his face. RGB uint8 TH x TW."""
    H, W = im.shape[:2]
    out = np.zeros((TH, TW, 3), np.float32) + np.array(stage, np.float32)

    def place(tile, mask, x0, y0):
        h, w = mask.shape
        sh = cv2.GaussianBlur(mask, (0, 0), 9)                             # e2-ish: a soft, low shadow under the shape
        oy = 7
        reg = out[y0 + oy:y0 + oy + h, x0:x0 + w]
        reg *= (1 - 0.16 * sh[:reg.shape[0], :reg.shape[1]])[..., None]
        a = mask[..., None]
        out[y0:y0 + h, x0:x0 + w] = out[y0:y0 + h, x0:x0 + w] * (1 - a) + tile.astype(np.float32) * a
    ch = 300
    cw = min(380, int(round(W * ch / H)))
    vw, vh = (int(round(H * cw / ch)), H) if W * ch > cw * H else (W, int(round(W * ch / cw)))   # cover crop, centred
    x0_, y0_ = (W - vw) // 2, (H - vh) // 2
    card = cv2.resize(im[y0_:y0_ + vh, x0_:x0_ + vw], (cw, ch), interpolation=cv2.INTER_AREA)
    m = np.zeros((ch * 4, cw * 4), np.uint8)
    r = 18 * 4
    cv2.rectangle(m, (r, 0), (cw * 4 - r, ch * 4), 255, -1)
    cv2.rectangle(m, (0, r), (cw * 4, ch * 4 - r), 255, -1)
    for cx, cy in ((r, r), (cw * 4 - r, r), (r, ch * 4 - r), (cw * 4 - r, ch * 4 - r)):
        cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    place(card, cv2.resize(m, (cw, ch), interpolation=cv2.INTER_AREA).astype(np.float32) / 255, 24, 26)
    d = 200
    if face is not None:
        x, y, w, h = face["box"]
        s = int(min(max(2.4 * w, 64), H, W))
        cx, cy = int(np.clip(x + w / 2 - s / 2, 0, W - s)), int(np.clip(y + h * 0.55 - s / 2, 0, H - s))
        circ = cv2.resize(im[cy:cy + s, cx:cx + s], (d, d), interpolation=cv2.INTER_AREA)
        cm = np.zeros((d * 4, d * 4), np.uint8)
        cv2.circle(cm, (d * 2, d * 2), d * 2 - 2, 255, -1, cv2.LINE_AA)
        place(circ, cv2.resize(cm, (d, d), interpolation=cv2.INTER_AREA).astype(np.float32) / 255, TW - d - 26, (TH - d) // 2)
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def sheet_grid(src, out, times, names, render, W, H, stage=None, fps=30):
    """Rows = times, columns = source + each look: the same frames side by side for an A/B, the scopes numbers (skin
    Y' / hue / chroma on the face box, his wall's Y' and |CbCr|) under each tile and in <out>.json. Each row is the
    frame on screen at its time (frame_at), decoded exactly. render(raw, i, look) -> graded rgb24 bytes of frame i.
    With `stage` (RGB) each tile is drawn on it as the page shows him."""
    import faces as FC
    import scopes
    cols = ["source"] + names
    TW = 640
    th = 360 if stage else int(H * TW / W)
    band, head = 44, 34
    sheet = np.full((head + len(times) * (th + band), len(cols) * TW, 3), 244 if stage else 24, np.uint8)
    ink = (20, 20, 24) if stage else (236, 232, 226)
    for c, n in enumerate(cols):
        cv2.putText(sheet, n, (c * TW + 12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, ink, 2, cv2.LINE_AA)
    rec = []
    for r, t in enumerate(times):
        fi = frame_at(t, fps)
        raw = decode_frame(src, fi, fps, W, H)
        if not raw:
            continue
        srcim = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        face = FC.detect(srcim)                                            # one box per row: every version measured alike
        for c, n in enumerate(cols):
            im = srcim if n == "source" else np.frombuffer(render(raw, fi, n), np.uint8).reshape(H, W, 3)
            m = scopes.measure(im, face)
            rec.append({"t": t, "frame": fi, "look": n, **{k: round(float(v), 4) for k, v in m.items()}})
            tile = stage_tile(im, face, stage, TW, th) if stage else cv2.resize(im, (TW, th), interpolation=cv2.INTER_AREA)
            y0 = head + r * (th + band)
            sheet[y0:y0 + th, c * TW:(c + 1) * TW] = tile
            l1 = f"{n} {t:g}s   skin Y' {m.get('skin_y', float('nan')):.3f}  hue {m.get('skin_hue', float('nan')):.0f}  c {m.get('skin_c', float('nan')):.3f}"
            l2 = f"wall Y' {m.get('wall_y', float('nan')):.3f}  |CbCr| {m.get('wall_c', float('nan')):.4f}   black {m.get('black', float('nan')):.3f}  clip {m.get('clip', 0):.2f}%"
            cv2.putText(sheet, l1, (c * TW + 10, y0 + th + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.46, ink, 1, cv2.LINE_AA)
            cv2.putText(sheet, l2, (c * TW + 10, y0 + th + 37), cv2.FONT_HERSHEY_SIMPLEX, 0.46, ink, 1, cv2.LINE_AA)
            print(f"{t:7.2f}s {n:10s} " + "  ".join(f"{k}={m[k]:.3f}" for k in ("skin_y", "skin_hue", "skin_c", "wall_y", "wall_c", "black", "clip") if k in m))
    cv2.imwrite(str(out), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
    Path(str(Path(out).with_suffix("")) + ".json").write_text(json.dumps(rec, indent=1))
    print(f"{out}: {len(times)} frames x {len(cols)} ({', '.join(cols)})" + (f" on {stage}" if stage else ""))


def _worker_init():
    """One OpenCV thread per worker: 8 processes x OpenCV's own thread pool oversubscribed the cores (2.5x the CPU time
    went to the kernel)."""
    cv2.setNumThreads(1)


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    light = float(arg("light", 1.0))
    room = arg("room")
    if room and room not in LK.ROOMS:
        raise SystemExit(f"unknown room {room!r} (one of {sorted(LK.ROOMS)})")
    mdir = arg("matte")
    mp = (lambda i: str(Path(mdir) / f"f{i + 1:05d}.png")) if mdir else (lambda i: None)
    plan = [{"t": 0.0, "look": arg("look", "natural")}]
    if arg("looks"):
        plan = sorted(json.load(open(arg("looks"))), key=lambda p: p["t"])
    for p in plan:                                                           # look None: written as decoded (kit/film kinds)
        if p["look"] is not None and p["look"] not in LK.LOOKS:
            raise SystemExit(f"unknown look {p['look']!r} (one of {sorted(LK.LOOKS)})")
    W, H, fps = probe(src)
    # a switch lands on its frame like every other edge (edge_frame): look_at(i / fps) then compares k / fps with k / fps
    # (the same division of two integers, so a switch on frame k is exact); fades keep their length in seconds
    plan = [dict(p, t=edge_frame(p["t"], fps) / fps) for p in plan]
    use_v2, reel = "--v2" in sys.argv, "--reel" in sys.argv
    if use_v2:
        lo = wall = skin = 0.0                                               # v2 measures per shot (v2_balances)
    else:
        lo, wall, skin = [float(v) for v in arg("levels").split(",")] if arg("levels") else levels(src)   # --levels: match an earlier grade
        print(f"levels: black {lo:.3f}, wall {wall:.3f}, skin {skin:.3f}")
    if arg("track"):
        track = np.array(json.load(open(arg("track"))))
        if arg("map"):
            track = track[np.clip(np.array(json.load(open(arg("map")))), 0, len(track) - 1)]
    else:
        if use_v2:                                                           # v2 wants the face, not the hairline
            import faces as FC
            track = np.array(FC.track_clip(str(src)))
        else:
            track = head_track(src, W, H)
        json.dump([[round(float(v), 1) for v in r] for r in track], open(str(out) + ".face.json", "w"))
        if "--track-only" in sys.argv:
            print(f"track: {len(track)} frames -> {out}.face.json")
            return
    passes, region, region_at = _ranges(arg("passthrough")), None, _ranges(arg("region-at"))
    if arg("region"):
        region = [int(float(v)) for v in arg("region").split(",")]
        if len(region) != 4 or region[0] < 0 or region[1] < 0 or region[0] + region[2] > W or region[1] + region[3] > H:
            raise SystemExit(f"--region={arg('region')}: x,y,w,h inside the {W}x{H} frame")
    mode = frame_mode(passes, region, region_at, fps)                         # frame index -> pass | region | full
    sheet_times = [float(x) for x in arg("sheet").split(",")] if arg("sheet") else None
    v2o = lambda i: None                                                     # noqa: E731  (per frame: v2 options or None)
    if use_v2:
        if arg("balance"):
            shots = balance_shots(json.load(open(arg("balance"))), fps)
        else:
            # 2026-10-22 (v11 review): every range edge is a shot edge. A passthrough or region-at range that didn't
            # line up with --shots (the direct CLI, no --shots) gave a whole shot the mode of its middle frame: a
            # passthrough middle left the shot's graded frames with no balance (a TypeError in the pool), a region
            # middle graded the shot's full frames on the bubble's balance
            bounds = [t for a, b in passes + (region_at if region else []) for t in (a, b)]
            shots = v2_balances(src, plan, track, mp, room, reel, fps, len(track), mode, region,
                                sheet_times if (sheet_times and (len(sheet_times) > 1 or arg("stage"))) else None, bounds)
            Path(str(out) + ".balance.json").write_text(json.dumps([{"t0": round(a / fps, 6), "t1": round(b / fps, 6), "f0": a, "f1": b, "bal": c}
                                                                    for a, b, c in shots], indent=1))
        def v2o(i):  # noqa: E306
            bal = shot_of(shots, i)[2]
            if bal is None:                                                  # (a --balance from another grade's shots)
                raise SystemExit(f"v2: no balance for frame {i} ({i / fps:.4f}s): its shot was passed through or skipped when "
                                 f"the balance was measured: re-measure without --balance, or line --shots up with the ranges")
            return {"bal": bal, "reel": reel}

    def job(buf, i, look):
        """(grade_frame job or None, the full frame, region or None): None = the frame is written as decoded."""
        md = mode(i)
        if md == "pass" or not look:
            return None, buf, None
        tr = track[min(i, len(track) - 1)]
        if md == "region":
            x, y, w, h = region
            crop = np.ascontiguousarray(np.frombuffer(buf, np.uint8).reshape(H, W, 3)[y:y + h, x:x + w]).tobytes()
            return (crop, in_region(tr, region), w, h, lo, wall, skin, light, i, look, room, None, v2o(i)), buf, region
        return (buf, tr, W, H, lo, wall, skin, light, i, look, room, mp(i), v2o(i)), buf, None

    def paste(full, graded, rg):
        if rg is None:
            return graded
        x, y, w, h = rg
        a = np.frombuffer(full, np.uint8).reshape(H, W, 3).copy()
        a[y:y + h, x:x + w] = np.frombuffer(graded, np.uint8).reshape(h, w, 3)
        return a.tobytes()

    def one(raw, i, look):
        j, full, rg = job(raw, i, look)
        return full if j is None else paste(full, grade_frame(j), rg)
    test = arg("test")
    if test:
        for t in (float(x) for x in test.split(",")):
            i = frame_at(t, fps)
            raw = decode_frame(src, i, fps, W, H)
            j, full, rg = job(raw, i, look_at(i / fps, plan))
            g = np.frombuffer(full if j is None else paste(full, grade_frame(j[:8] + (1,) + j[9:]), rg), np.uint8).reshape(H, W, 3)
            o = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
            cv2.imwrite(f"{out.with_suffix('')}_test_{t:g}.jpg", cv2.cvtColor(np.hstack([o, g]), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print("test frames written")
        return
    if sheet_times and (len(sheet_times) > 1 or arg("stage")):              # an A/B grid: times x looks, numbers under
        names = arg("sheet-looks", ",".join(n for n in LK.LOOKS)).split(",")
        sheet_grid(src, out, sheet_times, names, lambda raw, i, n: one(raw, i, n), W, H, _hex(arg("stage")) if arg("stage") else None, fps)
        return
    if arg("sheet"):                                                         # one frame in every look, labelled
        t = float(arg("sheet"))
        fi = frame_at(t, fps)
        names = arg("sheet-looks", ",".join(n for n in LK.LOOKS)).split(",")
        raw = decode_frame(src, fi, fps, W, H)
        tiles = [("source", np.frombuffer(raw, np.uint8).reshape(H, W, 3))]
        import scopes
        rows_ = []
        tr = track[min(len(track) - 1, fi)]
        for n in ["source"] + names:
            im = tiles[0][1] if n == "source" else np.frombuffer(grade_frame((raw, tr, W, H, lo, wall, skin, light, 1, n, room, mp(fi), v2o(fi))), np.uint8).reshape(H, W, 3)
            if n != "source":
                tiles.append((n, im))
            st = scopes.stats(im.astype(np.float32) / 255, face=tr)
            rows_.append(f"{n:10s} " + "  ".join(f"{k}={st.get(k, float('nan')):.3f}" for k in ("black", "white", "skin_luma", "skin_off", "skin_sat", "wall_luma", "wall_chroma", "wall_hue", "contrast")))
        print("\n".join(rows_))
        tw = 640
        th = int(H * tw / W)
        cols = 3 if len(tiles) > 4 else 2
        rows = -(-len(tiles) // cols)
        sheet = np.full((rows * th, cols * tw, 3), 24, np.uint8)
        for k, (n, im) in enumerate(tiles):
            r, c = divmod(k, cols)
            small = cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA).copy()
            cv2.rectangle(small, (0, 0), (14 + 15 * len(n), 34), (20, 18, 16), -1)
            cv2.putText(small, n, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (243, 238, 230), 2, cv2.LINE_AA)
            sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = small
        cv2.imwrite(str(out), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"{out}: {len(tiles)} looks at {t}s")
        return
    tmp = FF.part(out)                                                       # complete or absent: see ffio.finish
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-an", *FF.vf(), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                            "-c:v", "libx264", "-crf", os.environ.get("GRADE_CRF", "13"), "-preset", os.environ.get("GRADE_PRESET", "slow"), "-tune", "film", "-g", str(fps), "-pix_fmt", "yuv420p",
                            *FF.BT709, "-movflags", "+faststart", "-f", "mp4", str(tmp)], stdin=subprocess.PIPE)

    # frames go to the pool through a bounded window (an unbounded imap would decode the whole clip into memory and
    # swap): decoding, grading and encoding overlap, and frames are written in order. A pending item is (async result
    # or None, the decoded frame, region or None): None = written as decoded (--passthrough); a region is pasted back
    from collections import deque
    pending, n, i, n_pass = deque(), 0, 0, 0
    # GRADE_WORKERS (default 8) / GRADE_PRESET (x264, default slow). At 4K the encoder was the bottleneck (2026-10-10:
    # 12 workers sat at 25-43 % CPU behind -preset slow); the graded cut is an intermediate, so veryfast is fine for it
    with Pool(int(os.environ.get("GRADE_WORKERS", 8)), initializer=_worker_init) as pool:
        def emit():
            res, full, rg = pending.popleft()
            enc.stdin.write(full if res is None else paste(full, res.get(), rg))
        while True:
            buf = dec.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            j, full, rg = job(buf, i, look_at(i / fps, plan))
            n_pass += j is None
            pending.append((None if j is None else pool.apply_async(grade_frame, (j,)), full, rg))
            i += 1
            while pending and (len(pending) >= 24 or pending[0][0] is None or pending[0][0].ready()):
                emit()
                n += 1
        while pending:
            emit()
            n += 1
    enc.stdin.close()
    dec.wait()
    if enc.wait():
        raise SystemExit(f"encode failed (left {tmp.name})")
    FF.finish(tmp, out, src, n, passthrough=n_pass, region=region, look=sorted({str(p["look"]) for p in plan}), v2=use_v2,
              settings=FF.settings(sys.argv[3:], os.environ.get("GRADE_V2_SET", "")))   # what it was asked for (ffio.status)
    print(f"{out.name}: {n} frames graded" + (f" ({n_pass} passed through as decoded)" if n_pass else "") + f"; {Path(str(out) + '.ok').name} written")


if __name__ == "__main__":
    main()
