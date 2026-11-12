"""Demo of the explanation and polish components (kit/hf/explain.js, kit/hf/polish.js): one beat each, ~46 s, 16:9.

    python3 build.py --take <video.mp4>     # once: the A-roll for the screen beat (media stays out of git)
    python3 build.py                        # index.html with the kit inlined (data/ holds the real data)
    npx hyperframes lint && npx hyperframes render -o work/raw.mp4 --fps 30 --quality delivery
    python3 build.py --cues && python3 build.py --mux     # cues from the page + a music bed -> explain_demo.mp4

data/tokens.json: kit/hf/tools/nexttoken.py --onnx gpt2-lm-head-10.onnx --tok <tok> \
    --prompt "The best way to learn to code is to" --steps 5 --temps 0.7,1.8
data/race.json:   kit/hf/tools/arena_race.py <arena-ai-leaderboards>/data --board code --every 14 --top 6
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

SEG = {"tokens": [0.0, 10.4], "stack": [10.4, 17.0], "screen": [17.0, 25.0], "race": [25.0, 35.6], "scramble": [35.6, 40.0], "sweep": [40.0, 46.0]}
TOTAL = 46.0
TAKE = {"at": 16.9, "dur": 8.2, "media": 13.9}            # the speaker's lines for the screen beat (the box test take)
FACE = [945, 300]
BED = ROOT / "kit/music/tech/tech__mixkit__electro-dreams.mp3"


def run(cmd, **kw):
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def build():
    (HERE / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    vendor.copy_assets(HERE)
    shutil.copy2(ROOT / "films/expensewaale/assets/shots/main-home.jpg", HERE / "assets/shot.jpg")
    D = {"total": TOTAL, "seg": SEG, "face": FACE, "tokens": json.load(open(HERE / "data/tokens.json")), "race": json.load(open(HERE / "data/race.json"))}
    html = vendor.inline((HERE / "src/template.html").read_text(), stickman=False).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    for k, v in {"__TOTAL__": TOTAL, "__TAKE_AT__": TAKE["at"], "__TAKE_DUR__": TAKE["dur"], "__TAKE_MEDIA__": TAKE["media"]}.items():
        html = html.replace(k, str(v))
    (HERE / "index.html").write_text(html)
    print("index.html:", TOTAL, "s")


def cues():
    chrome = subprocess.run(["npx", "hyperframes", "browser", "path"], capture_output=True, text=True, cwd=HERE).stdout.strip().splitlines()[-1]
    js = ("import puppeteer from 'puppeteer-core'; import fs from 'node:fs';"
          f"const b = await puppeteer.launch({{ executablePath: {json.dumps(chrome)}, headless: true, args: ['--allow-file-access-from-files','--no-sandbox'] }});"
          "const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e.message || e)));"
          f"await p.goto('file://' + {json.dumps(str(HERE / 'index.html'))}, {{ waitUntil: 'domcontentloaded' }});"
          "await p.waitForFunction(() => window.__CUES && window.__CUES.length, { timeout: 30000 });"
          f"const c = await p.evaluate(() => window.__CUES); fs.writeFileSync({json.dumps(str(HERE / 'cues.json'))}, JSON.stringify(c.sort((a, b) => a.at - b.at)));"
          "console.log(c.length, 'cues', errs.length ? 'ERRORS: ' + errs.join(' | ') : ''); await b.close();")
    run(["node", "--input-type=module", "-e", js], cwd=ROOT)


def dec(p, ss=0.0, t=None, sr=48000):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss)] + (["-t", str(t)] if t else []) + ["-i", str(p), "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).copy()


def mux():
    """A music bed (with fades) under the components' sound cues; -14 LUFS / -1.5 dBTP."""
    sr, n = 48000, int(TOTAL * 48000)
    bed = dec(BED, 8.0, TOTAL + 0.5)[:n]
    bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
    t = np.arange(n) / sr
    mix = bed * (0.35 * np.clip(t / 0.8, 0, 1) * np.clip((TOTAL - 0.05 - t) / 1.5, 0, 1))[:, None]
    for c in json.load(open(HERE / "cues.json")):
        x = dec(ROOT / "kit/sfx" / f"{c['name']}.wav")
        x = x / (np.abs(x).max() + 1e-9) * 10 ** ((-3 + c["gain_db"]) / 20)
        i = int(c["at"] * sr); j = min(n, i + len(x))
        if 0 <= i < n:
            mix[i:j] += x[: j - i]
    work = HERE / "work"; work.mkdir(exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", sr, "-ac", 2, "-i", "-", "-c:a", "pcm_f32le", work / "mix_pre.wav"], input=mix.astype(np.float32).tobytes())
    run(["ffmpeg", "-v", "error", "-y", "-i", work / "raw.mp4", "-i", work / "mix_pre.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.78:level=false", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", HERE / "explain_demo.mp4"])
    print("-> explain_demo.mp4")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--take"]:
        (HERE / "assets").mkdir(exist_ok=True); shutil.copy2(a[1], HERE / "assets/take.mp4")
    else:
        {"--cues": cues, "--mux": mux}.get(a[0] if a else "", build)()
