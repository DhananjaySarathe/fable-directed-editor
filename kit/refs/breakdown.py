"""Break a reference video down into numbers and sheets, so a director can match its editing without watching it.
Claude sees still images, not motion or sound: this measures the motion, the cuts, the type and the beat for it.

    uv run python kit/refs/breakdown.py ref.mp4 [--out=dir] [--fps=30] [--ocr-step=0.25] [--no-ocr]

Writes <out>/ (default output/temp/refs/<name>/):
  breakdown.json  every number below, per shot and per event
  BREAKDOWN.md    the summary a director reads first (pace, camera, cuts, type, sound, colour)
  shots.jpg       one frame per shot: time, length, framing, the moves inside it
  cuts.jpg        2 frames before and 2 after each cut (how it cuts: hard, flash, punch, layout change)
  moves.jpg       6 frames across each move (push, pull, snap zoom, pan) with its length and easing
  text.jpg        the frame where each headline and caption first appears (font, size, colour, placement)

What it measures:
  cuts            hard changes between frames (mean difference or a histogram break), plus the cuts inside one shot
                  that change few pixels: the whole picture stepping in scale or place in a single frame (a punch-in)
                  and a one-frame difference spike where the subject jumps (a jump cut on a locked camera). Two changes
                  1-2 frames apart are one flash / whip. A spike where nothing jumps is a pop: a graphic or caption
                  that appears at once
  at each cut     the scale and position change from the frame before to the frame after: punch-in, punch-out,
                  same-size jump cut, layout change (the same face much smaller, bigger or elsewhere: a box, a split),
                  or a new picture. From the face when both frames have one, else from matched features
  moves           the whole-picture similarity (scale, shift of the centre) between frames from tracked features
                  (RANSAC, used only where most features agree): slow pushes and pull-outs, snap zooms (fast), pans,
                  with size, length, speed and easing. On a designed layout (the speaker in a box beside graphics) a
                  box that grows or shrinks reads as a snap zoom: moves.jpg shows which it is, and
                  kit/refs/motion_ref.py --box measures the box itself
  framing         the face height / frame height per shot (ECU, CU, MCU, MS, WS, none) from YuNet
  type            Apple Vision text recognition every --ocr-step s (tesseract off macOS). Lines that sit together are
                  one text, followed from the sample it appears to the sample it is replaced or gone. By letter height
                  (a share of the frame's short side): headlines (8 % and over), captions (3.5-8 %, up to 6 words, gone
                  within 2 s), labels (caption-sized text that stays), small text; a number that changes while its
                  words stay is a counter
  sound           loudness (EBU R128), onsets, the tempo and beat grid from the bass band (the voice has little
                  there) with how clear the beat is, and how many cuts land on an onset / beat against chance
  colour          the look metrics of kit/refs/measure.py on each shot, and the main palette
A first pass, not the last word. Checked exactly on camera footage with known cuts, punch-ins, a push and a beat
(tests/test_fable_director.py). On a designed page (the speaker in a box beside graphics, 2026-11-11 trial) it is
weaker, so check it against frames: a box that moves or morphs can read as a transition or a snap zoom; framing is
the face against the whole frame, not against its box; colour and palette are of the whole frame, page included; a
sparse or quiet music bed under a voice reads as "no beat"; the level of the music against the voice and sound
effects are not measured; graphics that animate in are counted only as pops when they appear in one frame.
A URL is not fetched here: download the reference first (for example `yt-dlp -f "bv*+ba/b" -o ref.mp4 <url>`).
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "look"))
sys.path.insert(0, str(KIT / "refs"))
import faces as FC  # noqa: E402
import measure as MS  # noqa: E402

AW = 480                              # analysis width
CUT_DIFF, CUT_SOFT, CUT_HIST = 28.0, 12.0, 0.70
MOVE_V = 0.0012                       # |d log scale| per frame that counts as a zoom in progress (~3.6 %/s at 30 fps)
PAN_V = 0.0025                        # centre shift per frame, as a share of the width, that counts as a pan
SNAP_RATE = 0.25                      # log-scale per second: faster is a snap zoom, slower a push or pull
JUMP_STEP = 0.035                     # the whole picture stepping this far (scale + shift) in ONE frame is a cut
MOVING = 6.0                          # a frame difference this high means the picture is in motion (a transition)
SPIKE = 3.0                           # a one-frame difference this high, 2.5x its neighbours, is a jump cut or a pop
FRAMING = [(0.45, "ECU"), (0.28, "CU"), (0.18, "MCU"), (0.09, "MS"), (0.0, "WS")]
HEADLINE, CAPTION = 0.08, 0.035       # letter height / the frame's short side
SR, NFFT, HOP = 22050, 1024, 256
ONSET_LAG = (NFFT - HOP / 2) / SR     # a frame's flux peaks when the attack first enters its window


def probe(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", src],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                     "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip())
    return {"width": s["width"], "height": s["height"], "fps": round(num / den, 3), "seconds": float(d["format"]["duration"]),
            "audio": has_audio}


def stream(src, fps, w, h):
    """Yield BGR frames at `fps`, `w`x`h`, without holding the video in memory."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    p.wait()


def affine(g0, g1):
    """(scale, dx, dy, agreement) of the whole-picture similarity g0 -> g1, or None. dx, dy are the shift of the
    frame centre in pixels (a zoom about the centre gives 0); agreement is the share of features that follow it."""
    pts = cv2.goodFeaturesToTrack(g0, 300, 0.01, 8)
    if pts is None or len(pts) < 12:
        return None
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, pts, None, winSize=(21, 21), maxLevel=3)
    ok = st.ravel() == 1
    if ok.sum() < 12:
        return None
    M, inl = cv2.estimateAffinePartial2D(pts[ok], nxt[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if M is None or inl is None or inl.sum() < 10:
        return None
    h, w = g0.shape
    cx, cy = w / 2, h / 2
    dx = M[0, 0] * cx + M[0, 1] * cy + M[0, 2] - cx
    dy = M[1, 0] * cx + M[1, 1] * cy + M[1, 2] - cy
    inl, p = inl.ravel().astype(bool), pts[ok].reshape(-1, 2)
    agree = float(inl.mean())
    edge = (p[:, 0] < 0.15 * w) | (p[:, 0] > 0.85 * w) | (p[:, 1] < 0.15 * h) | (p[:, 1] > 0.85 * h)
    if edge.sum() >= 8:                            # a camera move carries the frame's edges; a speaker leaning does not
        agree = min(agree, float(inl[edge].mean()))
    return float(np.hypot(M[0, 0], M[1, 0])), float(dx), float(dy), agree


def face_of(bgr):
    f = FC.detect(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), scale=1.0)
    return f if f and f["score"] > 0.5 else None


def by_face(b0, b1):
    """(scale, shift, box) of the face from b0 to b1, or None: its height ratio, how far its centre moved (share of
    the frame) and its box in b0."""
    f0, f1 = face_of(b0), face_of(b1)
    if not (f0 and f1):
        return None
    H, W = b0.shape[:2]
    (x0, y0, w0, h0), (x1, y1, w1, h1) = f0["box"], f1["box"]
    return h1 / max(h0, 1e-6), float(np.hypot((x1 + w1 / 2 - x0 - w0 / 2) / W, (y1 + h1 / 2 - y0 - h0 / 2) / H)), f0["box"]


def by_features(b0, b1):
    """(scale, shift, points) of the whole picture from b0 to b1 from matched ORB features, or None when the two
    frames do not show the same picture. points = where in b0 the features that follow that motion sit."""
    H, W = b0.shape[:2]
    orb = cv2.ORB_create(800)
    k0, d0 = orb.detectAndCompute(cv2.cvtColor(b0, cv2.COLOR_BGR2GRAY), None)
    k1, d1 = orb.detectAndCompute(cv2.cvtColor(b1, cv2.COLOR_BGR2GRAY), None)
    if d0 is None or d1 is None or len(k0) < 30 or len(k1) < 30:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d0, d1)
    if len(m) < 30:
        return None
    p0 = np.float32([k0[x.queryIdx].pt for x in m])
    p1 = np.float32([k1[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(p0, p1, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    if M is None or inl is None or inl.sum() < 25 or inl.sum() < 0.35 * len(m):
        return None
    dx = M[0, 0] * W / 2 + M[0, 1] * H / 2 + M[0, 2] - W / 2
    dy = M[1, 0] * W / 2 + M[1, 1] * H / 2 + M[1, 2] - H / 2
    return float(np.hypot(M[0, 0], M[1, 0])), float(np.hypot(dx / W, dy / H)), p0[inl.ravel().astype(bool)]


def across_cut(b0, b1):
    """(scale, shift, by) across a cut: how much bigger the picture is after it and how far it moved (share of the
    frame); (None, None, None) = two unrelated pictures. by says what measured it:
      features  the whole picture: the precise measure of a punch on one shot, and of a jump cut (scale 1, shift 0)
      box       the face is another size (beyond x1.25) and either in another place, or in place while the room beside
                the head did not stay with the picture: the speaker's box changed on a designed page (a layout change).
                A face that only moved, at the same size, is a jump cut where the speaker sits elsewhere in the next take
      face      no common picture: only the face ties the two frames together"""
    feat, face = by_features(b0, b1), by_face(b0, b1)
    if face:
        resized, moved = not 1 / 1.25 < face[0] < 1.25, face[1] > 0.15
        if resized and feat and not moved:         # bigger or smaller in place: a real box change, or a face misread?
            x, y, w, h = face[2]
            pts = feat[2]
            beside = (pts[:, 0] > x - 2 * w) & (pts[:, 0] < x + 3 * w) & (pts[:, 1] > y - 1.5 * h) & (pts[:, 1] < y + 1.2 * h)
            on_face = (pts[:, 0] > x) & (pts[:, 0] < x + w) & (pts[:, 1] > y) & (pts[:, 1] < y + h)
            resized = (beside & ~on_face).sum() < 12   # the room beside the head stayed with the picture: trust the picture
        if resized and (moved or feat):            # another size, and another place or a page that stayed: a layout change
            return round(face[0], 3), round(face[1], 3), "box"
    pick, by = (feat, "features") if feat else (face, "face")
    return (round(pick[0], 3), round(pick[1], 3), by) if pick else (None, None, None)


def subject_jumped(b0, b1):
    """True when the picture or the speaker is somewhere else one frame later: a jump cut, not a graphic popping in."""
    for m in (by_face(b0, b1), by_features(b0, b1)):
        if m and (abs(np.log(m[0])) >= 0.03 or m[1] >= 0.012):
            return True
    return False


def cut_kind(scale, shift):
    if scale is None:
        return "new picture"
    if shift > 0.15 or scale > 1.6 or scale < 1 / 1.6:
        return "layout change"
    return "punch-in" if scale >= 1.06 else "punch-out" if scale <= 1 / 1.06 else "same-size"


def event_kind(scale, shift, by):
    if by == "box":
        return "layout change"
    if by == "face":                               # no common picture, only the face: a jump cut where the speaker sits
        return "same-size" if 1 / 1.25 < scale < 1.25 else "layout change"     # elsewhere, unless the face changed size
    return cut_kind(scale, shift)


def framing(face_h):
    if face_h is None:
        return "none"
    return next(name for lim, name in FRAMING if face_h >= lim)


def runs(mask):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def easing(v):
    """Name the speed curve of one move from its per-frame speeds."""
    v = np.abs(np.asarray(v, float))
    if len(v) < 4 or v.max() <= 0:
        return "snap"
    k = int(np.argmax(v)) / (len(v) - 1)
    n = max(1, len(v) // 5)
    head, tail = v[:n].mean() / v.max(), v[-n:].mean() / v.max()
    if head > 0.6 and tail > 0.6:
        return "linear"
    return "ease-out" if k < 0.3 else "ease-in" if k > 0.7 else "ease-in-out"


# ---------------------------------------------------------------- pass 1: frames

def hard_cut(r):
    return r["diff"] > CUT_DIFF or (r["hist"] < CUT_HIST and r["diff"] > CUT_SOFT)


def step(r):
    """How far the whole picture stepped in this frame: |log scale| + shift (share of the width). 0 = still or unknown."""
    a = r["aff"]
    if not a or a[3] < 0.5:
        return 0.0
    return abs(float(np.log(max(a[0], 1e-6)))) + float(np.hypot(a[1], a[2])) / AW


def soft_cut(rec, c, before, after):
    """A cut inside one shot, which changes too few pixels for hard_cut: a punch-in, or a jump between two sentences
    on a locked camera. Judged one frame late, from frame c's neighbours. A move (a snap zoom) steps on several
    frames in a row; a cut steps once."""
    if rec[c]["cut"] or rec[c - 1]["cut"] or rec[c + 1]["cut"]:
        return False
    q = step(rec[c])
    if q > JUMP_STEP and max(step(rec[c - 1]), step(rec[c + 1])) < 0.35 * q:
        return True                                # the picture jumped in scale or place within one frame
    d = rec[c]["diff"]
    if d > SPIKE and d > 2.5 * max(rec[c - 1]["diff"], rec[c + 1]["diff"], 0.4):
        if subject_jumped(before, after):
            return True                            # a jump cut
        rec[c]["pop"] = True                       # something appeared in one frame (a graphic, a caption): not a cut
    return False


def analyse_frames(src, info, fps):
    AH = int(round(AW * info["height"] / info["width"] / 2) * 2)
    face_every = max(1, int(round(fps / 2)))       # faces at 2 per second
    thumb_every = max(1, int(round(fps / 4)))      # thumbnails at 4 per second
    rec, thumbs, faces_t, cut_frames = [], {}, {}, {}
    ring, pending = [], []                         # the last 4 frames; hard cuts waiting for their after-frames
    prev_g, prev_h = None, None
    for i, f in enumerate(stream(src, fps, AW, AH)):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        h = cv2.calcHist([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 16], [0, 180, 0, 256])
        cv2.normalize(h, h)
        r = {"diff": 0.0, "hist": 1.0, "aff": None, "cut": False, "pop": False}
        if prev_g is not None:
            r["diff"] = float(np.abs(g.astype(np.int16) - prev_g.astype(np.int16)).mean())
            r["hist"] = float(cv2.compareHist(prev_h, h, cv2.HISTCMP_CORREL))
            if r["diff"] < CUT_DIFF:
                r["aff"] = affine(prev_g, g)
            r["cut"] = hard_cut(r)
        rec.append(r)
        ring = (ring + [f.copy()])[-4:]
        for c in pending:
            c["after"].append(ring[-1])
        for c in [c for c in pending if len(c["after"]) >= 2]:
            cut_frames[c["i"]] = c["before"] + c["after"]
            pending.remove(c)
        if r["cut"]:
            pending.append({"i": i, "before": ring[-3:-1], "after": [ring[-1]]})
        elif i >= 3 and soft_cut(rec, i - 1, ring[-3], ring[-2]):      # frame i-1 against i-2, now that i is known
            rec[i - 1]["cut"] = True
            cut_frames[i - 1] = list(ring)
        if i % face_every == 0:
            fc = face_of(f)
            faces_t[i] = None if fc is None else {"cx": (fc["box"][0] + fc["box"][2] / 2) / AW,
                                                  "cy": (fc["box"][1] + fc["box"][3] / 2) / AH, "h": fc["box"][3] / AH}
        if i % thumb_every == 0:
            thumbs[i] = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
        prev_g, prev_h = g, h
    for c in pending:
        cut_frames[c["i"]] = c["before"] + c["after"]
    return rec, thumbs, faces_t, cut_frames


def find_cuts(rec, cut_frames):
    """(cuts, flashes, morphs): shot boundaries by frame index; the ones that are one flash or whip; and {boundary:
    frames} for the ones that are a transition: several frames of motion with the big change inside it (a box that
    morphs, a wipe, a dissolve), placed at the frame the motion starts."""
    cuts, flashes, morphs = [], [], {}
    for i in (i for i, r in enumerate(rec) if r["cut"]):
        a = b = i
        while a > 1 and rec[a - 1]["diff"] > MOVING:
            a -= 1
        while b + 1 < len(rec) and rec[b + 1]["diff"] > MOVING:
            b += 1
        if i - a >= 2 and b - a + 1 >= 4:          # motion leads into the change
            if cuts and a <= cuts[-1] + 2:         # the same run as the boundary before it
                continue
            cuts.append(a)
            morphs[a] = b - a + 1
            cut_frames[a] = cut_frames.get(i, [])
            continue
        if cuts and i - cuts[-1] <= 2:             # two changes 1-2 frames apart are one event (a flash or a whip)
            flashes.append(cuts[-1])
            continue
        cuts.append(i)
    return cuts, sorted(set(flashes)), morphs


# ---------------------------------------------------------------- shots

def shots_from(rec, cuts, faces_t, fps, n):
    bounds = [0] + cuts + [n]
    shots = []
    for k in range(len(bounds) - 1):
        a, b = bounds[k], bounds[k + 1]
        logs, pans = [], []
        for r in rec[a + 1:b]:
            if r["aff"] and r["aff"][3] >= 0.5:    # most of the picture moves together: the camera, not the speaker's hands
                s, dx, _, _ = r["aff"]
                logs.append(np.log(max(s, 1e-6)))
                pans.append(dx / AW)
            else:
                logs.append(0.0)
                pans.append(0.0)
        ls = np.convolve(logs, np.ones(5) / 5, mode="same") if len(logs) >= 5 else np.asarray(logs)
        ps = np.convolve(pans, np.ones(5) / 5, mode="same") if len(pans) >= 5 else np.asarray(pans)
        moves = []
        for s0, ln in runs(list((np.abs(ls) > MOVE_V) | (np.abs(ps) > PAN_V))):
            if ln < 3:
                continue
            zoom = float(np.exp(np.sum(logs[s0:s0 + ln])))
            pan = float(np.sum(pans[s0:s0 + ln]))
            secs = ln / fps
            rate = abs(np.log(zoom)) / secs
            if zoom >= 1.03 or zoom <= 1 / 1.03:
                kind = ("snap-in" if zoom > 1 else "snap-out") if rate >= SNAP_RATE else ("push" if zoom > 1 else "pull")
                speed = ls[s0:s0 + ln]
            elif abs(pan) > 0.06:
                kind, rate, speed = "pan", abs(pan) / secs, ps[s0:s0 + ln]
            else:
                continue
            moves.append({"t": round((a + 1 + s0) / fps, 3), "seconds": round(secs, 3), "kind": kind, "zoom": round(zoom, 3),
                          "pan": round(pan, 3), "per_second": round(float(rate), 3), "easing": easing(speed)})
        fs = [faces_t[i] for i in faces_t if a <= i < b]
        seen = [f for f in fs if f]
        fh = float(np.median([f["h"] for f in seen])) if seen else None
        shots.append({"n": k + 1, "start": round(a / fps, 3), "end": round(b / fps, 3), "seconds": round((b - a) / fps, 3),
                      "face_share": round(len(seen) / len(fs), 2) if fs else 0.0, "face_h": round(fh, 3) if fh else None,
                      "framing": framing(fh) if seen and len(seen) >= len(fs) / 2 else "none",
                      "face_x": round(float(np.median([f["cx"] for f in seen])), 3) if seen else None, "moves": moves,
                      "in_motion": round(float(np.mean([r["diff"] > 2.2 for r in rec[a + 1:b]])) if b - a > 1 else 0.0, 3)})
    return shots


def cut_events(cuts, cut_frames, morphs, fps):
    out = []
    for i in cuts:
        fr = cut_frames.get(i)
        if not fr or len(fr) < 3:
            continue
        nb = len(fr) - 2                           # frames before the cut in the strip
        s, shift, how = across_cut(fr[nb - 1], fr[nb])
        if i in morphs:                            # frames from the middle of a move say nothing about scale
            out.append({"t": round(i / fps, 3), "scale": None, "shift": None, "by": None, "kind": "transition",
                        "seconds": round(morphs[i] / fps, 3)})
            continue
        out.append({"t": round(i / fps, 3), "scale": s, "shift": shift, "by": how, "kind": event_kind(s, shift, how)})
    return out


# ---------------------------------------------------------------- type

def text_class(h):
    return "headline" if h >= HEADLINE else "caption" if h >= CAPTION else "small"


def ocr(src, step, workdir):
    """(events, share of sampled frames with a headline or caption). An event is one text of one size class from the
    frame it appears to the frame it is replaced or gone."""
    d = workdir / "ocr_frames"
    d.mkdir(parents=True, exist_ok=True)
    for p in d.glob("*.png"):
        p.unlink()
    subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps=1/{step},scale='min(1280,iw)':-2", str(d / "%06d.png")], check=True)
    files = sorted(d.glob("*.png"))
    vision = KIT / "bin" / "ocrboxes"
    if not vision.exists() and sys.platform == "darwin":
        subprocess.run(["swiftc", "-O", "-o", str(vision), str(KIT / "hf" / "tools" / "ocrboxes.swift")], capture_output=True)

    def one(p):
        W, H = Image.open(p).size
        S, lines = min(W, H), []
        if vision.exists():                        # Apple Vision reads stroked and stylised captions tesseract misses
            for row in subprocess.run([str(vision), str(p)], capture_output=True, text=True).stdout.splitlines():
                try:
                    o = json.loads(row)
                except ValueError:
                    continue
                if o.get("conf", 0) >= 0.5 and any(ch.isalnum() for ch in o["text"]):
                    lines.append({"text": o["text"], "h": o["h"] / S, "y": (o["y"] + o["h"] / 2) / H})
            return lines
        tsv = subprocess.run(["tesseract", str(p), "-", "--psm", "11", "tsv"], capture_output=True, text=True).stdout
        for row in tsv.splitlines()[1:]:
            c = row.split("\t")
            if len(c) < 12 or not c[11].strip():
                continue
            conf, txt = float(c[10]), c[11].strip()
            if conf >= 80 and (len(txt) >= 3 or txt.isdigit()) and any(ch.isalnum() for ch in txt):
                y, h = int(c[7]), int(c[9])
                lines.append({"text": txt, "h": h / S, "y": (y + h / 2) / H})
        return lines

    with ThreadPoolExecutor(8) as ex:
        per = list(ex.map(one, files))
    key = lambda text: {re.sub(r"\d+([.,]\d+)?", "#", w.lower()) for w in text.split()}
    events, live, shown = [], [], 0
    for k, lines in enumerate(per):
        t = round(k * step, 3)
        shown += any(text_class(l["h"]) != "small" for l in lines)
        blocks = []                                # lines of one size class that sit together are one text
        for l in sorted(lines, key=lambda l: (text_class(l["h"]), l["y"])):
            cls = text_class(l["h"])
            if blocks and blocks[-1]["class"] == cls and l["y"] - blocks[-1]["lines"][-1]["y"] < 0.07:
                blocks[-1]["lines"].append(l)
            else:
                blocks.append({"class": cls, "lines": [l]})
        still = []
        for bl in blocks:
            text = " ".join(l["text"] for l in bl["lines"])
            ws = key(text)
            e = next((e for e in live if e["class"] == bl["class"] and e not in still
                      and len(ws & e["last"]) / len(ws | e["last"]) >= 0.5), None)
            if e:                                  # the same text, growing, highlighted or counting
                e["counter"] = e["counter"] or (text != e["seen"] and ws == e["last"])
                e["end"], e["last"], e["seen"] = round(t + step, 3), ws, text
                if len(text) >= len(e["text"]):
                    e["text"], e["words"] = text[:160], len(text.split())
            else:
                e = {"class": bl["class"], "start": t, "end": round(t + step, 3), "last": ws, "seen": text, "counter": False,
                     "frame": str(files[k]), "text": text[:160], "words": len(text.split()),
                     "height": round(float(np.median([l["h"] for l in bl["lines"]])), 4),
                     "y": round(float(np.median([l["y"] for l in bl["lines"]])), 3)}
                events.append(e)
            still.append(e)
        live = still
    for e in events:
        e.pop("last"), e.pop("seen")
        e["seconds"] = round(e["end"] - e["start"], 3)
        if e.pop("counter") and e["class"] != "small":
            e["class"] = "counter"                 # a number that counts up
        elif e["class"] == "caption" and (e["seconds"] > 2.0 or e["words"] > 6):
            e["class"] = "label"                   # caption-sized text that stays: a chip, a card line, UI
    events.sort(key=lambda e: e["start"])
    return events, round(shown / max(1, len(per)), 3)


# ---------------------------------------------------------------- sound

def sound(src, cuts_t, info):
    if not info["audio"]:
        return {"audio": False}
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    if len(x) < NFFT * 8:
        return {"audio": False}
    win = np.hanning(NFFT).astype(np.float32)
    view = np.lib.stride_tricks.sliding_window_view(x, NFFT)[::HOP]
    lo, hi = int(40 * NFFT / SR), int(180 * NFFT / SR) + 1          # the bass band: kick and bass, little voice
    full, low, prev = [], [], None
    for a in range(0, len(view), 4096):                             # in blocks: a long film never sits in memory whole
        m = np.log1p(np.abs(np.fft.rfft(view[a:a + 4096] * win, axis=1))).astype(np.float32)
        dm = np.maximum(np.diff(np.vstack([prev, m]) if prev is not None else np.vstack([m[:1], m]), axis=0), 0)
        full.append(dm.sum(axis=1))
        low.append(dm[:, lo:hi].sum(axis=1))
        prev = m[-1:]
    fr = SR / HOP
    norm = lambda v: (v - v.mean()) / (v.std() + 1e-9)
    flux, flux_low = norm(np.concatenate(full)), norm(np.concatenate(low))
    k = int(fr * 0.5)
    loc = np.convolve(flux, np.ones(2 * k + 1) / (2 * k + 1), mode="same")
    w = max(2, int(fr * 0.04))
    peaks = [i for i in range(w, len(flux) - w) if flux[i] == flux[i - w:i + w + 1].max() and flux[i] > loc[i] + 1.0]
    onsets = np.array(peaks) / fr + ONSET_LAG

    def tempo(v):
        ac = np.correlate(v, v, mode="full")[len(v) - 1:]
        lags = np.arange(int(fr * 60 / 180), int(fr * 60 / 60) + 1)
        score = ac[lags] * np.exp(-0.5 * (np.log2((60 * fr / lags) / 110) / 0.9) ** 2)
        j = int(np.argmax(score))
        frac = 0.0                                                  # parabolic peak between whole lags
        if 0 < j < len(score) - 1 and (score[j - 1] - 2 * score[j] + score[j + 1]) != 0:
            frac = 0.5 * (score[j - 1] - score[j + 1]) / (score[j - 1] - 2 * score[j] + score[j + 1])
        return float(lags[j] + frac), float(ac[lags[j]] / (ac[0] + 1e-9))

    lag, strength = tempo(flux_low)
    band, v = "bass", flux_low
    if strength < 0.1:                                              # no bass pulse: try the whole spectrum
        lag2, s2 = tempo(flux)
        if s2 > strength:
            lag, strength, band, v = lag2, s2, "full", flux
    phase = max(np.arange(0, lag, 0.5), key=lambda p: v[np.round(np.arange(p, len(v), lag)).astype(int).clip(0, len(v) - 1)].sum())
    beats = np.arange(phase, len(v), lag) / fr + ONSET_LAG
    tol = 0.07
    near = lambda t, grid: bool(len(grid)) and float(np.min(np.abs(grid - t))) <= tol
    dur = len(x) / SR
    stderr = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", src, "-af", "ebur128", "-f", "null", "-"],
                            capture_output=True, text=True).stderr.splitlines()
    val = lambda key: next((float(l.split()[1]) for l in reversed(stderr) if l.strip().startswith(key)), None)
    return {"audio": True, "lufs": val("I:"), "lra": val("LRA:"), "bpm": round(60 * fr / lag, 1),
            "beat": "clear" if strength >= 0.2 else "weak" if strength >= 0.1 else "none", "beat_strength": round(strength, 3),
            "beat_band": band, "onsets_per_s": round(len(onsets) / dur, 2),
            "beats": [round(float(b), 3) for b in beats[:4000]], "onsets": [round(float(o), 3) for o in onsets[:4000]],
            "cuts": len(cuts_t), "cuts_on_onset": sum(near(t, onsets) for t in cuts_t), "cuts_on_beat": sum(near(t, beats) for t in cuts_t),
            "chance_onset": round(min(1.0, 2 * tol * len(onsets) / dur), 2), "chance_beat": round(min(1.0, 2 * tol / (lag / fr)), 2)}


# ---------------------------------------------------------------- colour

def colour(thumbs, shots, fps):
    out, pix = [], []
    keys = sorted(thumbs)
    for s in shots:
        mid = int((s["start"] + s["end"]) / 2 * fps)
        im = cv2.imdecode(np.frombuffer(thumbs[min(keys, key=lambda i: abs(i - mid))], np.uint8), cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(cv2.resize(im, (MS.W, MS.H)), cv2.COLOR_BGR2RGB).astype(np.float32)
        out.append({k: (None if np.isnan(v) else round(float(v), 2)) for k, v in MS.stats(rgb).items()})
        pix.append(rgb.reshape(-1, 3)[::7])
    P = np.concatenate(pix).astype(np.float32)
    K = min(6, len(P))
    _, lab, cen = cv2.kmeans(P, K, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(lab.ravel(), minlength=K) / len(lab)
    pal = sorted(({"hex": "#%02x%02x%02x" % tuple(int(c) for c in cc), "share": round(float(s), 3)} for cc, s in zip(cen, share)),
                 key=lambda d: -d["share"])
    med = {k: round(float(np.nanmedian([o[k] for o in out if o[k] is not None])), 2) for k in ["p1", "p50", "p99", "sat", "colorful", "cme"]}
    return {"per_shot": out, "median": med, "palette": pal}


# ---------------------------------------------------------------- sheets

def tile(img, text, w):
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)) if isinstance(img, np.ndarray) else img
    im = im.resize((w, int(w * im.size[1] / im.size[0])))
    canvas = Image.new("RGB", (w, im.size[1] + 18), "white")
    canvas.paste(im, (0, 18))
    ImageDraw.Draw(canvas).text((3, 3), text, fill="black")
    return canvas


def grid(tiles, cols, path):
    if not tiles:
        return
    w, h = max(t.size[0] for t in tiles), max(t.size[1] for t in tiles)
    sheet = Image.new("RGB", (cols * (w + 4) + 4, -(-len(tiles) // cols) * (h + 4) + 4), (235, 235, 235))
    for k, t in enumerate(tiles):
        sheet.paste(t, (4 + (k % cols) * (w + 4), 4 + (k // cols) * (h + 4)))
    sheet.save(path, quality=86)


def grab(src, t, w):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", src, "-frames:v", "1", "-vf", f"scale={w}:-2",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(BytesIO(raw)).convert("RGB") if raw else None


def sheets(src, out, fps, shots, thumbs, cut_frames, cuts, events, text, vertical):
    tw, sw = (200, 150) if vertical else (300, 200)
    keys = sorted(thumbs)
    tiles = []
    for s in shots:
        mid = int((s["start"] + s["end"]) / 2 * fps)
        im = cv2.imdecode(np.frombuffer(thumbs[min(keys, key=lambda i: abs(i - mid))], np.uint8), cv2.IMREAD_COLOR)
        mv = ",".join(m["kind"] for m in s["moves"]) or "static"
        tiles.append(tile(im, f"#{s['n']} {s['start']:.2f}s +{s['seconds']:.2f}s {s['framing']} {mv}"[:tw // 6], tw))
    grid(tiles, 6 if vertical else 4, out / "shots.jpg")
    kinds = {e["t"]: e for e in events}
    tiles = []
    for i in cuts[:40]:
        fr = cut_frames.get(i) or []
        e = kinds.get(round(i / fps, 3), {})
        labels = [f"{i / fps:.2f}s {e.get('kind', '')}", f"x{e['scale']}" if e.get("scale") else "", "> after the cut", ""]
        row = [tile(f, labels[j + 4 - len(fr)], sw) for j, f in enumerate(fr)]
        tiles.extend([Image.new("RGB", row[0].size, "white")] * (4 - len(row)) + row if row else [])
    grid(tiles, 4, out / "cuts.jpg")
    tiles = []
    for m in [m for s in shots for m in s["moves"]][:16]:
        for j in range(6):
            t = m["t"] + m["seconds"] * j / 5
            im = grab(src, t, sw)
            if im:
                size = "" if m["kind"] == "pan" else f" x{m['zoom']:.2f}"
                tiles.append(tile(im, f"{m['kind']}{size} {m['t']:.2f}s" if j == 0 else f"{m['seconds']:.2f}s {m['easing']}" if j == 1 else f"+{t - m['t']:.2f}", sw))
    grid(tiles, 6, out / "moves.jpg")
    pick = [e for e in text if e["class"] == "headline"][:18] + [e for e in text if e["class"] == "caption"][:12]
    tiles = [tile(Image.open(e["frame"]).convert("RGB"), f"{e['class'][:4]} {e['start']:.1f}s +{e['seconds']:.1f}s {e['height'] * 100:.0f}%"[:tw // 6], tw)
             for e in sorted(pick, key=lambda e: e["start"])]
    grid(tiles, 6 if vertical else 4, out / "text.jpg")


# ---------------------------------------------------------------- summary

def summary(name, info, shots, cuts, flashes, pops, events, text, text_share, snd, col, fps):
    secs = info["seconds"]
    lens = [s["seconds"] for s in shots]
    med = lambda xs: float(np.median(xs))
    L = [f"# Breakdown: {name}\n",
         f"{info['width']}x{info['height']} at {info['fps']} fps, {secs:.1f} s, measured at {fps} fps. The numbers are measurements; "
         "the sheets (shots.jpg, cuts.jpg, moves.jpg, text.jpg) show the style. Read both.\n",
         "## Pace",
         f"- {len(shots)} shots, {len(cuts) / secs * 60:.0f} cuts a minute. Shot length: median {med(lens):.2f} s, "
         f"p10 {np.quantile(lens, .1):.2f} s, p90 {np.quantile(lens, .9):.2f} s, longest {max(lens):.2f} s.",
         f"- First 3 s: {sum(1 for s in shots if s['start'] < 3)} shots, {sum(1 for c in cuts if c / fps < 3)} cuts."]
    if pops:
        L.append(f"- {len(pops)} one-frame pops ({len(pops) / secs * 60:.0f} a minute): a graphic or caption that appears at once, with no "
                 "fade or slide. " + ", ".join(f"{t:.2f}s" for t in pops[:12]) + (" ..." if len(pops) > 12 else ""))
    if flashes:
        L.append(f"- {len(flashes)} flash or whip frames (two changes 1-2 frames apart) at " + ", ".join(f"{f / fps:.2f}s" for f in flashes[:12]) + ".")
    L.append(f"- Something moves in {np.average([s['in_motion'] for s in shots], weights=lens):.0%} of the frames.")
    L.append("\n## Cuts")
    for kind, what in (("punch-in", "the same subject, closer"), ("punch-out", "the same subject, wider"), ("same-size", "a jump cut at the same size"),
                       ("layout change", "the same face much smaller, bigger or elsewhere: into or out of a box or split"),
                       ("new picture", "B-roll, a screen, a graphic or another angle"),
                       ("transition", "several frames of motion with the change inside: a box morph, a wipe, a whip, a dissolve")):
        es = [e for e in events if e["kind"] == kind]
        if es:
            size = f", size median x{med([e['scale'] for e in es]):.2f}" if kind in ("punch-in", "punch-out") else ""
            size = f", length median {med([e['seconds'] for e in es]):.2f} s" if kind == "transition" else size
            L.append(f"- {len(es)} {kind} ({what}){size}: " + ", ".join(f"{e['t']:.2f}s" for e in es[:14]) + (" ..." if len(es) > 14 else ""))
    L.append("\n## Moves inside a shot")
    mv = [m for s in shots for m in s["moves"]]
    for kind, what in (("push", "slow zoom in"), ("pull", "slow zoom out"), ("snap-in", "fast zoom in"), ("snap-out", "fast zoom out"), ("pan", "sideways")):
        ms = [m for m in mv if m["kind"] == kind]
        if ms:
            ease = max(set(m["easing"] for m in ms), key=[m["easing"] for m in ms].count)
            size = "" if kind == "pan" else f", size median x{med([m['zoom'] for m in ms]):.3f}"
            L.append(f"- {len(ms)} {kind} ({what}; {len(ms) / secs * 60:.1f} a minute): length median {med([m['seconds'] for m in ms]):.2f} s{size}, "
                     f"most often {ease}.")
    L.append(f"- {sum(1 for s in shots if not s['moves'])} of {len(shots)} shots have no move. On a designed layout a box that grows or "
             "shrinks reads as a snap zoom: check moves.jpg.")
    fr = {}
    for s in shots:
        fr[s["framing"]] = fr.get(s["framing"], 0) + s["seconds"]
    L.append("- Framing by time: " + ", ".join(f"{k} {v / secs:.0%}" for k, v in sorted(fr.items(), key=lambda kv: -kv[1]))
             + " (from the face height; none = no face: B-roll, a screen, a graphic).")
    L.append("\n## On-screen text")
    if text:
        L.append(f"- A headline or caption is on screen in {text_share:.0%} of the sampled frames. Heights are a share of the frame's short side.")
        for cls in ("headline", "caption"):
            es = [e for e in text if e["class"] == cls]
            if es:
                gaps = np.diff([e["start"] for e in es])
                L.append(f"- {len(es)} {cls}s ({len(es) / secs * 60:.0f} a minute): {med([e['words'] for e in es]):.0f} words each (median), held "
                         f"{med([e['seconds'] for e in es]):.2f} s, letters {med([e['height'] for e in es]) * 100:.1f} %, "
                         f"{med([e['y'] for e in es]) * 100:.0f} % from the top"
                         + (f", a new one every {med(gaps):.2f} s" if len(gaps) else "") + ". First: "
                         + "; ".join(f"{e['start']:.1f}s \"{e['text'][:32]}\"" for e in es[:4]))
        n = lambda cls: sum(1 for e in text if e["class"] == cls)
        L.append(f"- {n('counter')} numbers that count up, {n('label')} labels (caption-sized text that stays over 2 s: chips, card lines), "
                 f"{n('small')} small-text events (UI).")
    else:
        L.append("- No text found (or --no-ocr).")
    L.append("\n## Sound")
    if snd.get("audio"):
        L.append(f"- Loudness {snd['lufs']} LUFS integrated, range {snd['lra']} LU; {snd['onsets_per_s']} onsets a second.")
        L.append(f"- Beat: {snd['beat']} (strength {snd['beat_strength']}, from the {snd['beat_band']} band), about {snd['bpm']} BPM."
                 + ("" if snd["beat"] == "clear" else " Without a clear beat the tempo and the beat share below mean little (a voice over a quiet bed)."))
        if snd["cuts"]:
            L.append(f"- Cuts within 70 ms of an onset: {snd['cuts_on_onset']} of {snd['cuts']} ({snd['cuts_on_onset'] / snd['cuts']:.0%}; chance "
                     f"{snd['chance_onset']:.0%}). On the beat grid: {snd['cuts_on_beat'] / snd['cuts']:.0%} (chance {snd['chance_beat']:.0%}).")
    else:
        L.append("- No audio track.")
    m = col["median"]
    L += ["\n## Colour",
          f"- Black/mid/white points {m['p1']}/{m['p50']}/{m['p99']}, saturation {m['sat']}, colourfulness {m['colorful']}, "
          f"centre-minus-edge {m['cme']} (kit/refs/measure.py metrics).",
          "- Palette: " + ", ".join(f"{p['hex']} {p['share']:.0%}" for p in col["palette"])]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--ocr-step", type=float, help="seconds between text samples (default 0.25, or 0.5 over 3 minutes)")
    ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args()
    src = str(Path(a.src).resolve())
    name = Path(src).stem
    out = Path(a.out) if a.out else KIT.parent / "output" / "temp" / "refs" / name
    out.mkdir(parents=True, exist_ok=True)
    info = probe(src)
    fps = min(a.fps, info["fps"])
    print(f"{name}: {info['width']}x{info['height']} {info['fps']} fps {info['seconds']:.1f} s -> {out}", flush=True)
    rec, thumbs, faces_t, cut_frames = analyse_frames(src, info, fps)
    cuts, flashes, morphs = find_cuts(rec, cut_frames)
    shots = shots_from(rec, cuts, faces_t, fps, len(rec))
    events = cut_events(cuts, cut_frames, morphs, fps)
    pops = [round(i / fps, 3) for i, r in enumerate(rec) if r["pop"] and not r["cut"]]
    text, text_share = ([], 0.0) if a.no_ocr else ocr(src, a.ocr_step or (0.25 if info["seconds"] <= 180 else 0.5), out)
    snd = sound(src, [c / fps for c in cuts], info)
    col = colour(thumbs, shots, fps)
    sheets(src, out, fps, shots, thumbs, cut_frames, cuts, events, text, info["height"] > info["width"])
    R = {"video": src, "info": info, "analysis_fps": fps, "cuts": [round(c / fps, 3) for c in cuts],
         "flashes": [round(f / fps, 3) for f in flashes], "pops": pops, "shots": shots, "cut_events": events, "text": text,
         "text_share": text_share, "sound": snd, "colour": col}
    (out / "breakdown.json").write_text(json.dumps(R, indent=1))
    md = summary(name, info, shots, cuts, flashes, pops, events, text, text_share, snd, col, fps)
    (out / "BREAKDOWN.md").write_text(md)
    print(md)
    print("->", out)


if __name__ == "__main__":
    main()
