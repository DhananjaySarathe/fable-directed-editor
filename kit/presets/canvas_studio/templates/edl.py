"""The cut for a preset_canvas_studio film (from films/chakra-redline/edl.py). Copy to films/<film>/edl.py, set JOB and KEEP.

KEEP is a list of word-id ranges, each a whole sentence or a run of whole sentences (no-cropped-sentences). Pauses between
them are trimmed down to KEEP_GAP of the room's own quiet; every join must sit in real quiet (kit/cut/edges.py), or the
script stops. Re-listen to work/vo_raw.wav at every join before any picture work (audit-joins-before-render).

    uv run python films/<film>/edl.py        # -> work/edl.json, work/take.mov (the cut, picture untouched), work/vo_raw.wav
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from kit.cut.edges import audit, envelope, joint, onset, offset, speech_threshold  # noqa: E402
from kit.paths import Film, job_dir, job_source  # noqa: E402

F = Film(__file__)
JOB = "<job>"                                         # the ingested take (uv run shorts probe/analyze)
SR = 48000
FPS = 30
KEEP = [(0, 0)]                                       # word ids (inclusive), whole sentences: [(first, last), ...]
KEEP_GAP = (0.16, 0.0)                                # s of real quiet kept after a trimmed pause's last word (~0.16 s heard)
TAIL = 0.55                                           # s of room after the last word


def main():
    words = {w["i"]: w for w in json.load(open(job_dir(JOB) / "analysis.json"))["words"]}
    src = job_source(JOB)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    env = envelope(np.frombuffer(raw, np.float32))
    thr = speech_threshold(env)
    pieces = []
    for k, (a, b) in enumerate(KEEP):
        wa, wb = words[a], words[b]
        if k == 0:
            sa = onset(env, wa["start"], words[a - 1]["end"] + 0.01, thr)
        else:
            kind, e, s = joint(env, words[KEEP[k - 1][1]], wa, thr)
            if kind != "quiet":
                raise SystemExit(f"join before word {a} has no quiet: {kind}")
            sa = s - KEEP_GAP[1]
            pieces[-1]["src_b"] = e + KEEP_GAP[0]
        sb = offset(env, wb["end"], words[b + 1]["start"] - 0.01, thr)
        if k == len(KEEP) - 1:                                        # the room after the last word, stopping before the next one
            nxt = onset(env, words[b + 1]["start"], wb["end"] + 0.01, thr)
            sb = min(sb + TAIL, nxt - 0.06)
        pieces.append({"clip": 1, "src_a": sa, "src_b": sb, "w": [a, b]})
    t = 0.0
    for p in pieces:                                                  # frame-exact pieces
        p["src_a"] = round(np.round(p["src_a"] * FPS) / FPS, 4)
        p["src_b"] = round(np.round(p["src_b"] * FPS) / FPS, 4)
        p["out_a"] = round(t, 4)
        t += p["src_b"] - p["src_a"]
        p["out_b"] = round(t, 4)
    total = round(t, 4)
    out_words = []
    for p in pieces:
        for i in range(p["w"][0], p["w"][1] + 1):
            w = words[i]
            out_words.append({"i": i, "text": w["text"], "t": round(p["out_a"] + w["start"] - p["src_a"], 3), "e": round(p["out_a"] + w["end"] - p["src_a"], 3)})
    bad = audit(pieces, {1: env}, {1: thr})
    print(f"threshold {thr:.1f} dB; edges in sound:", bad or "none")
    edl = {"job": JOB, "fps": FPS, "total": total, "talk_end": out_words[-1]["e"], "pieces": pieces, "words": out_words}
    (F.work / "edl.json").write_text(json.dumps(edl, indent=1))
    (HERE / "edl.json").write_text(json.dumps({k: edl[k] for k in ("job", "fps", "total", "pieces")}, indent=1))
    # the cut: picture untouched (one encode, near-lossless), audio with 10 ms fades at the joins
    fc, n = [], len(pieces)
    for k, p in enumerate(pieces):
        d = p["src_b"] - p["src_a"]
        fc.append(f"[0:v]trim={p['src_a']:.4f}:{p['src_b']:.4f},setpts=PTS-STARTPTS[v{k}]")
        fc.append(f"[0:a]atrim={p['src_a']:.4f}:{p['src_b']:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st={d - 0.01:.4f}:d=0.01[a{k}]")
    fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "pcm_s16le", "-ar", str(SR),
                    str(F.work / "take.mov")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(F.work / "take.mov"), "-map", "0:a", "-ac", "1", "-ar", str(SR), str(F.work / "vo_raw.wav")], check=True)
    print(f"{total:.2f} s in {n} pieces: " + ", ".join(f"{p['src_a']:.2f}-{p['src_b']:.2f}" for p in pieces))


if __name__ == "__main__":
    main()
