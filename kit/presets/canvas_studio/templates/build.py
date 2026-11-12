"""Build a preset_canvas_studio film (from films/chakra-redline/build.py). Copy to films/<film>/build.py; run edl.py first,
then put his graded take at work/room.mp4 (kit/look/grade.py --v2, or kit/look/cutout.py ... --plate=work/room.mp4).

    uv run python films/<film>/build.py            # stage the page (output/temp/films/<film>/hf)
    uv run python films/<film>/build.py --snap     # ... and stills at SNAP into renders/snap (look at every one)
    uv run python films/<film>/build.py --all      # stage, precheck, cues, mix, render 1080p, mux, qa -> output/final/<film>

Sound: his voice (work/vo.wav: WPE dereverb + DeepFilterNet3), one bed about 12 dB under him, the page's cues (camera
whooshes, pops, the hero impact) and its HF.quiet dips.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kit/hf"))
from kit.audio.mix import Bed, mix  # noqa: E402
from kit.paths import Film  # noqa: E402
import vendor  # noqa: E402

F = Film(__file__)
ENV = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1")
MUSIC = ROOT / "kit/music/chill/chill__mixkit__dim-the-lights.mp3"
OUT = F.final / f"{F.name}.mp4"
SNAP = [0.0, 1.0, 3.0]                                                # one still per beat, plus every transition
HOLD = None                                                           # None: end with the take (the ring lands as he finishes)
# what he says, where whisper misheard it (from the re-listen of the cut): shown text only, {word id: text}
FIX = {}
ALLOW = []                                                            # precheck windows to allow, e.g. ["21.8-22.6"] for an overview move


def stage():
    edl = json.loads((F.work / "edl.json").read_text())
    F.stage()
    (F.hf / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    shutil.copy2(F.work / "room.mp4", F.assets / "room.mp4")                # his take, graded (he is only ever in a circle or a card)
    vendor.copy_assets(F.hf)
    words = [dict(w, text=FIX.get(w["i"], w["text"])) for w in edl["words"]]
    total = round(edl["talk_end"] + HOLD, 3) if HOLD else edl["total"]
    D = {"total": total, "talk": edl["talk_end"], "words": words, "pieces": edl["pieces"]}
    html = vendor.inline((HERE / "src/template.html").read_text(), stickman=False)
    (F.hf / "index.html").write_text(html.replace("/*DATA*/", "const D = " + json.dumps(D) + ";").replace("__TOTAL__", f"{total:.4f}")
                                     .replace("__MEDIA__", f"{edl['total']:.4f}"))
    print(f"{F.hf}/index.html: {total:.2f} s")
    return dict(edl, total=total)


def run(*cmd, **kw):
    subprocess.run([str(c) for c in cmd], check=True, cwd=ROOT, env=ENV, **kw)


def main():
    edl = stage()
    if "--snap" in sys.argv:
        run("npx", "hyperframes", "snapshot", F.hf, "--at", ",".join(f"{t:g}" for t in SNAP), "--no-end", "--describe", "false", "-o", F.renders / "snap")
    if "--all" not in sys.argv:
        return
    # an overview move shows earlier and later scenes small, side by side for a beat (read before and after it): ALLOW it
    run("node", ROOT / "kit/qa/precheck.mjs", F.hf / "index.html", f"--holds-out={F.work / 'holds.json'}", *([f"--allow={','.join(ALLOW)}"] if ALLOW else []))
    run("node", ROOT / "kit/presets/paper_studio/example/cues.mjs", F.hf / "index.html", F.work / "cues.json")
    mix(F.work, edl, [Bed(MUSIC, 0.0, edl["total"], start=8.0, under=-16, gap=-8, fade_in=0.4, even=2)], total=edl["total"])
    raw = F.renders / "sample_1080.mp4"
    run("npx", "hyperframes", "render", F.hf, "-o", raw, "--resolution", "1080p", "--quality", "delivery", "--fps", "30")
    F.final.mkdir(parents=True, exist_ok=True)
    run("ffmpeg", "-v", "error", "-y", "-i", raw, "-i", F.work / "mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
        "-aac_pns", "0", "-shortest", "-movflags", "+faststart", OUT)
    holds = ",".join(str(p) for p in (F.work / "holds.json", F.work / "cues.holds.json") if p.exists())
    cuts = F.work / "cuts.json"
    cuts.write_text(json.dumps([p["out_a"] for p in edl["pieces"][1:]]))
    subprocess.run([sys.executable, ROOT / "kit/qa/qa.py", OUT, f"--cuts={cuts}", f"--expect-duration={edl['total']:.2f}", "--expect-size=1920x1080",
                    f"--holds={holds}"], cwd=ROOT, env=ENV)
    print(OUT)


if __name__ == "__main__":
    main()
