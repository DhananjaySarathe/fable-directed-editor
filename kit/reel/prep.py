"""Footage prep for a 9:16 Reel (from films/youtube-automation-bridge/prep.py, made generic 2026-10-10).

`shorts probe` makes the upright SDR copy (output/jobs/<take>/source.mp4, 1080x1920). Here it goes to CFR, is tracked,
matted and graded WHOLE once (look v2, --reel), so the cut is made from the graded picture and never re-graded.

Steps (each skips when its output exists; --force=<step> redoes one):
  take     work/take.mp4          1080x1920 SDR, CFR (Reel FPS), x264 crf 10 (hflip when FLIP)
  track    work/take.face.json    YuNet face track (kit/look/faces.py)
  matte    work/matte/f00001.png  personseg masks, one per frame (the grade's separation and the cut-outs)
  voice    work/voice_df.wav      WPE dereverb on both mics (kit/reel/dereverb.py, its own venv) then DeepFilterNet3
  grade    work/take_graded.mp4   look v2 --reel; complete or absent (take_graded.mp4.ok, kit/look/ffio.py)

The grade keeps his room as shot (2026-10-22, v11; OWNER_DEFAULTS §2 "no blur, dimming, vignette or background
replacement"): no vignette, no person matte (the matte is what set the room back -0.8 stop, defocused it by 4 px and
greyed it), and the room profile reel.py names (ROOM = "shelf" ...), else 'asshot' (kit/look/looks.py: the room's colour
as shot, half its cast kept, no warm studio highlights; the woodoffice default was the old set-back look's).
ROOM_SET_BACK = True in reel.py brings that old look back (the matte, the room's vignette) for a Reel he asked it of.
The matte step still runs: the cut-out WebMs use it. The grade step re-grades when LOOK / ROOM / ROOM_SET_BACK /
GRADE_V2_SET changed since the take was graded (the settings in take_graded.mp4.ok).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
STEPS = ("take", "track", "matte", "voice", "grade")


def sh(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd)[:240], flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def nframes(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True).stdout
    return int(out.strip().split(",")[0])


def take(R, force):
    out = R.work / "take.mp4"
    if out.exists() and not force:
        return
    vf = f"fps={R.FPS},setsar=1" + (",hflip" if R.FLIP else "")
    sh(["ffmpeg", "-v", "error", "-y", "-i", R.source, "-map", "0:v:0", "-an", "-vf", vf, "-fps_mode", "cfr",
        "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-g", "30", "-pix_fmt", "yuv420p", *TAGS, "-movflags", "+faststart", out])
    print(f"take: {nframes(out)} frames")


def track(R, force):
    out = R.work / "take.face.json"
    if out.exists() and not force:
        return
    sh(["uv", "run", "python", ROOT / "kit/look/faces.py", R.work / "take.mp4", out], cwd=ROOT)


def matte(R, force):
    d = R.work / "matte"
    n = nframes(R.work / "take.mp4")
    if d.exists() and len(list(d.glob("f*.png"))) >= n and not force:
        return
    d.mkdir(exist_ok=True)
    tmp = R.work / "frames"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    sh(["ffmpeg", "-v", "error", "-y", "-i", R.work / "take.mp4", "-start_number", "1", tmp / "f%05d.png"])
    sh([ROOT / "kit/bin/personseg", tmp, d, "--mask"], stdout=subprocess.DEVNULL)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"matte: {len(list(d.glob('f*.png')))} masks")


def voice(R, force):
    out = R.work / "voice_df.wav"
    if out.exists() and not force:
        return
    raw, wpe = R.work / "voice_raw.wav", R.work / "voice_wpe.wav"
    sh(["ffmpeg", "-v", "error", "-y", "-i", R.source, "-map", "0:a:0", "-vn", "-ar", "48000", raw])          # both mics
    src = raw
    if R.DEREVERB and (Path.home() / ".venvs/wpe/bin/python").exists():
        sh([Path.home() / ".venvs/wpe/bin/python", ROOT / "kit/reel/dereverb.py", raw, wpe], stdout=subprocess.DEVNULL)
        src = wpe
    sh([Path.home() / ".venvs/df/bin/deepFilter", src, "-o", R.work], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (R.work / f"{src.stem}_DeepFilterNet3.wav").rename(out)
    raw.unlink(missing_ok=True)
    wpe.unlink(missing_ok=True)
    print("voice ->", out)


AS_SHOT = "asshot"     # the room profile when reel.py names none (kit/look/looks.py ROOMS): his room's colour as shot
SET_BACK_ROOM = "woodoffice"   # the set-back look's room when reel.py names none (config's ROOM default before v11)


def grade_args(R) -> tuple:
    """(kit/look/grade.py options, GRADE_V2_SET) for the take's grade. By default his room stays as shot: no matte, no
    vignette, and the room profile reel.py sets (ROOM = "shelf" ...), else 'asshot' (config's ROOM default is None;
    its old "woodoffice" belonged to the set-back look). Not no profile at all: grade.py's default is 'paper', the cream
    studio, whose warm highlights and 85 % kept wall cast tripled the cream on his white walls (|CbCr| 0.016 vs 0.0055;
    v11 review, scratchpad review_picture/reel_room.log). ROOM_SET_BACK = True: the pre-v11 grade (the room's profile,
    else woodoffice as before, the matte, its vignette). The arguments (and so the settings a graded take was recorded
    with) are the same as before config's defaults changed: a re-grade only when reel.py changes."""
    if getattr(R.mod, "ROOM_SET_BACK", False):
        return [f"--room={getattr(R, 'ROOM', None) or SET_BACK_ROOM}", f"--matte={R.work / 'matte'}"], ""
    room = getattr(R.mod, "ROOM", None) or AS_SHOT
    return [f"--room={room}"], "vignette=0"


def grade_cmd(R) -> tuple:
    """(kit/look/grade.py arguments, GRADE_V2_SET as the grade will see it) for the take."""
    opts, v2set = grade_args(R)
    v2set = ",".join(x for x in (v2set, os.environ.get("GRADE_V2_SET", "")) if x)
    return [R.work / "take.mp4", R.work / "take_graded.mp4", "--v2", "--reel", f"--look={R.LOOK}",
            f"--track={R.work / 'take.face.json'}", *opts], v2set


def grade(R, force):
    sys.path.insert(0, str(ROOT / "kit/look"))
    import ffio as FF
    take, out = R.work / "take.mp4", R.work / "take_graded.mp4"
    log = R.work / "grade.log"
    cmd, v2set = grade_cmd(R)
    # complete, of this take, and made with these settings (LOOK, ROOM, ROOM_SET_BACK, GRADE_V2_SET: a change re-grades;
    # a graded take from before settings were recorded is compared on its look only, so a finished Reel never is)
    if not force:
        ok, why = FF.status(take, out, want=FF.settings(cmd[2:], v2set))
        if ok:
            return
        if out.exists():
            print(f"grade: {why}: grading again")
    env = dict(os.environ)
    env.setdefault("GRADE_WORKERS", "4")          # leave room for another session's render
    env.setdefault("GRADE_PRESET", "veryfast")    # the graded take is an intermediate (the cut re-encodes it at crf 12)
    if v2set:
        env["GRADE_V2_SET"] = v2set
    with open(log, "w") as lf:
        sh(["uv", "run", "python", ROOT / "kit/look/grade.py", *cmd], stdout=lf, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
    print(f"grade: {log.read_text().strip().splitlines()[-1]}")


def run(R, only=None, force=()):
    R.work.mkdir(parents=True, exist_ok=True)
    for step in STEPS:
        if only and step not in only:
            continue
        globals()[step](R, step in force)
