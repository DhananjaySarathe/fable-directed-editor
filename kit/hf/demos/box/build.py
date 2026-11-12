"""Demo of the speaker box (kit/hf/box.js): the director's moves on a real 46 s take, in the paper-studio style.

    python3 build.py --take <video.mp4>      # once: the 16:9 A-roll -> assets/take.mp4 (media stays out of git)
    python3 build.py                         # index.html with the kit inlined
    npx hyperframes lint && npx hyperframes render -o work/raw.mp4 --fps 30 --quality delivery
    python3 build.py --cues && python3 build.py --mux    # sound cues from the page, the take's audio + cues -> box_demo.mp4

The beats are notes on what each passage shows (kit/refs/MOTION.md §3); HF.box.direct picks the moves from them.
The take used on 2026-10-08 was the "Original" half of the reference in kit/refs/MOTION.md §1 (a test take, not ours
to publish), so the timings below follow its phrases. A new take only needs new beats.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
ROOT = KIT.parent
sys.path.insert(0, str(KIT / "hf"))
import vendor  # noqa: E402

TOTAL = 46.0
FACE = [945, 300]                     # eyes in the 1920x1080 take (measured on a frame at 5 s)
# one beat per visual idea: what the passage shows, where its content sits, section changes, card hand-offs
BEATS = [
    {"t": 0.0, "show": "face", "tag": "open"},                                  # the face first: it is the hook
    {"t": 1.95, "show": "hero", "tag": "hero"},                                 # "AI can finally do high-level editing"
    {"t": 4.0, "show": "beside", "side": "left", "tag": "noob"},                # "like, not any noob-level work"
    {"t": 6.0, "show": "graphic", "tag": "pro"},                                # "professional-grade editing, premium motion graphics"
    {"t": 10.1, "show": "punch", "section": True, "tag": "crazy"},             # "and the crazy part"
    {"t": 11.3, "show": "aside", "side": "right", "tag": "mins"},               # the number
    {"t": 14.1, "show": "face", "tag": "share"},                                # "I'm sharing the process"
    {"t": 16.7, "show": "graphic", "card": True, "tag": "cheap"},               # way cheaper / why / pixels vs code
    {"t": 26.9, "show": "beside", "side": "right", "tag": "refs"},              # "in the start, give it references, lock the aesthetic"
    {"t": 30.6, "show": "graphic", "tag": "prompt"},                            # the prompt card types
    {"t": 33.2, "show": "beside", "side": "right", "card": True, "tag": "talk"},  # "talk to Claude": the prompt card turns over into him
    {"t": 35.4, "show": "aside", "side": "right", "tag": "move"},               # "I make things move"
    {"t": 38.8, "show": "graphic", "tag": "hours"},                             # keyframing, hours in editing
    {"t": 43.5, "show": "punch", "section": True, "tag": "end"},               # "you talk, it designs"
]


def run(cmd, **kw):
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def take(src):
    (HERE / "assets").mkdir(exist_ok=True)
    shutil.copy2(src, HERE / "assets/take.mp4")


def build():
    (HERE / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    vendor.copy_assets(HERE)
    D = {"total": TOTAL, "beats": BEATS, "face": FACE}
    html = vendor.inline((HERE / "src/template.html").read_text(), stickman=False).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    (HERE / "index.html").write_text(html.replace("__TOTAL__", str(TOTAL)))
    print("index.html:", TOTAL, "s,", len(BEATS), "beats")


def cues():
    """window.__CUES from the built page (headless Chrome), plus the director's log -> cues.json, box_log.json."""
    chrome = subprocess.run(["npx", "hyperframes", "browser", "path"], capture_output=True, text=True, cwd=HERE).stdout.strip().splitlines()[-1]
    js = ("import puppeteer from 'puppeteer-core'; import fs from 'node:fs';"
          f"const b = await puppeteer.launch({{ executablePath: {json.dumps(chrome)}, headless: true, args: ['--allow-file-access-from-files','--no-sandbox'] }});"
          "const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e.message || e)));"
          f"await p.goto('file://' + {json.dumps(str(HERE / 'index.html'))}, {{ waitUntil: 'domcontentloaded' }});"
          "await p.waitForFunction(() => window.__boxlog, { timeout: 30000 });"
          "const r = await p.evaluate(() => ({ cues: window.__CUES, log: window.__boxlog, pace: HF.box.pace(window.__box, " + str(TOTAL) + ") }));"
          f"fs.writeFileSync({json.dumps(str(HERE / 'cues.json'))}, JSON.stringify(r.cues.sort((a, b) => a.at - b.at)));"
          f"fs.writeFileSync({json.dumps(str(HERE / 'box_log.json'))}, JSON.stringify({{ log: r.log, pace: r.pace }}, null, 1));"
          "console.log(r.cues.length, 'cues', JSON.stringify(r.pace), errs.length ? 'ERRORS: ' + errs.join(' | ') : ''); await b.close();")
    run(["node", "--input-type=module", "-e", js], cwd=ROOT)


def dec(p, sr=48000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def mux():
    """The take's own audio + the box's sound cues, -14 LUFS / -1.5 dBTP, onto the render."""
    sr, n = 48000, int(TOTAL * 48000)
    mix = np.zeros((n, 2), np.float32)
    v = dec(HERE / "assets/take.mp4")[:n]
    mix[: len(v)] += v
    for c in json.load(open(HERE / "cues.json")):
        x = dec(ROOT / "kit/sfx" / f"{c['name']}.wav")
        x = x / (np.abs(x).max() + 1e-9) * 10 ** ((-3 + c["gain_db"]) / 20)
        i = int(c["at"] * sr); j = min(n, i + len(x))
        if 0 <= i < n:
            mix[i:j] += x[: j - i]
    work = HERE / "work"; work.mkdir(exist_ok=True)
    pre = work / "mix_pre.wav"
    run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", sr, "-ac", 2, "-i", "-", "-c:a", "pcm_f32le", pre], input=mix.tobytes())
    run(["ffmpeg", "-v", "error", "-y", "-i", work / "raw.mp4", "-i", pre, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", HERE / "box_demo.mp4"])
    print("-> box_demo.mp4")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--take"]:
        take(a[1])
    else:
        {"--cues": cues, "--mux": mux}.get(a[0] if a else "", build)()
