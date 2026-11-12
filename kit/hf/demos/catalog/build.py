"""FIXTURE: the vendored HyperFrames catalog pieces (kit/hf/catalog) mounted in the kit's looks, two per 5 s window.

    uv run python kit/hf/demos/catalog/build.py [look ...]      # -> output/temp/demos/catalog/<look>/index.html
    uv run python kit/hf/demos/catalog/build.py --sheet         # build, then one still per window per look -> sheet.jpg

It goes through kit/hf/mounts.py exactly as a film's build does (film.py MOUNTS), so a piece that breaks here breaks in a
film. The content is made up (an AI-tools explainer's kind of lines); the screenshot is a kit preview still. These are
check pages, not edits.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
OUT = KIT.parent / "output/temp/demos/catalog"
sys.path.insert(0, str(KIT / "hf"))
import mounts  # noqa: E402
import vendor  # noqa: E402

LOOKS = ["pastel_box", "canvas_studio", "night"]
L, R = (80, 150, 860, 484), (980, 150, 860, 484)
PAIRS = [   # (label, pieces...): two half-frame pieces per window, or one full-frame piece
    ("screen demos", dict(name="cursor-zoom-follow", box=L, radius=22, vars=dict(image="assets/shot.png", zoom=1.9, click1_x=30, click1_y=20, click2_x=62, click2_y=55, click3_x=80, click3_y=30)),
     dict(name="agent-cursor", box=R, radius=22, vars=dict(agent_name="Claude", steps="Reading the repo,Running the tests,Fixing the upload,Done", targets="30,40;70,62"))),
    ("evidence", dict(name="cursor-text-select", box=L, radius=22, vars=dict(title="Release notes", text="The agent now opens a pull request on its own. It runs the tests first, fixes what fails, and only then asks for a review.", phrase="runs the tests first")),
     dict(name="marker-highlight", box=R, vars=dict(text="Agents do the boring part", emphasis_word="boring"))),
    ("headline", dict(name="headline-slam", vars=dict(text="Same model. Different limits.", accent_word_index=2))),
    ("lean in", dict(name="push-in", box=L, radius=22, vars=dict(text="Read the diff")),
     dict(name="notes-typing", box=R, radius=22, vars=dict(title="What I hand to the agent|first", lines="flaky test runs|release notes|the boring PRs"))),
    ("numbers", dict(name="decline-chart", box=L, vars=dict(label="Review time, minutes", start_value=45, end_value=12)),
     dict(name="conic-progress-ring", box=R, vars=dict(progress=72, label="72%"))),
    ("conversation", dict(name="chat-thread", box=(530, 150, 860, 484), radius=22, vars=dict(contact="Sam", messages="recv:did the agent fix it?|sent:it opened a PR 😅|recv:and the tests?|sent:all green"))),
]
TOTAL = 5.0 * len(PAIRS)


def build(look):
    d = OUT / look
    (d / "assets").mkdir(parents=True, exist_ok=True)
    (d / "hyperframes.json").write_text('{ "paths": { "assets": "assets" } }\n')
    take = d / "assets/take.mp4"
    if not take.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=1920x1080:rate=30:duration={TOTAL}",
                        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "32", str(take)], check=True)
    shutil.copy2(KIT / "graphics/_previews/ai_chat.png", d / "assets/shot.png")
    vendor.copy_assets(d)
    specs, times = [], []
    for i, (_, *pieces) in enumerate(PAIRS):
        for s in pieces:
            specs.append(dict(s, dur=4.8))
            times.append(i * 5.0 + 0.1)
    tpl = mounts.install(d, specs, times, (HERE / "src/template.html").read_text(), look=look)
    D = {"total": TOTAL, "look": look, "words": [], "pieces": [{"out_a": 0, "out_b": TOTAL, "face": [960, 420]}], "windows": [p[0] for p in PAIRS]}
    html = vendor.inline(tpl).replace("/*DATA*/", "const D = " + json.dumps(D) + ";")
    (d / "index.html").write_text(html.replace("__TOTAL__", str(TOTAL)))
    print(f"{d}/index.html: {look}, {len(specs)} mounts")
    return d


def sheet(looks):
    shots = []
    for look in looks:
        d = build(look)
        out = OUT / "shots" / look
        shutil.rmtree(out, ignore_errors=True)
        at = ",".join(f"{i * 5 + 2.8:.1f}" for i in range(len(PAIRS)))
        subprocess.run(["npx", "hyperframes", "snapshot", str(d), "--at", at, "--no-end", "-o", str(out)], check=True,
                       stdin=subprocess.DEVNULL, capture_output=True)
        shots.append(sorted(out.glob("frame-*.png")))
    rows = []
    for row in shots:
        ins = sum([["-i", str(p)] for p in row], [])
        f = "".join(f"[{i}:v]scale=480:270[v{i}];" for i in range(len(row))) + "".join(f"[v{i}]" for i in range(len(row))) + f"hstack=inputs={len(row)}"
        r = OUT / f"row_{len(rows)}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", f, str(r)], check=True)
        rows.append(r)
    stack = ["-filter_complex", f"vstack=inputs={len(rows)}"] if len(rows) > 1 else []
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + sum([["-i", str(r)] for r in rows], []) + stack + [str(OUT / "sheet.jpg")], check=True)
    print("->", OUT / "sheet.jpg", "(rows:", ", ".join(looks) + "; columns:", ", ".join(p[0] for p in PAIRS) + ")")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")] or LOOKS
    sheet(args) if "--sheet" in sys.argv else [build(lk) for lk in args]
