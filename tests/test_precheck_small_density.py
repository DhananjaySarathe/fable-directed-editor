"""kit/qa/precheck.mjs, review 2026-10-23 (v11-sample draft 1): the phone floor read .mono labels as decor and SVG text at
its viewBox size, so 25-30 px mechanism words passed; a large block (a stack, a diagram) counted as one group however
many lines it held. Runs the real precheck in headless Chrome on a small static fixture page."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
GSAP = ROOT / "node_modules/gsap/dist/gsap.min.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None or not CHROME.exists() or not GSAP.exists(),
                                reason="needs node, Google Chrome and node_modules/gsap")

A = "position:absolute;left:{x}px;top:{y}px"
LINES = "".join(f'<div style="font:500 40px sans-serif;margin:6px 24px">stack line {i}</div>' for i in range(12))
PAGE = f"""<!doctype html><html><head><meta charset="UTF-8"><script src="file://{GSAP}"></script></head><body>
<div id="root" data-composition-id="fx" data-start="0" data-duration="5" data-width="1920" data-height="1080"
     style="position:relative;width:1920px;height:1080px;overflow:hidden;background:#fafafa">
  <div style="position:absolute;inset:0;z-index:2">
    <div><div class="mono" style="{A.format(x=100, y=100)};font:500 30px monospace">runs commands</div></div>
    <div><div class="lbl" style="{A.format(x=100, y=200)};font:600 16px monospace">PART ONE KICKER</div></div>
    <div style="{A.format(x=100, y=300)};transform:scale(0.99);transform-origin:0 0"><div style="font:500 32px sans-serif">exactly the floor</div></div>
    <svg style="{A.format(x=100, y=450)}" width="600" height="100" viewBox="0 0 1200 200"><text x="0" y="120" font-size="50" font-family="sans-serif">a scaled svg label</text></svg>
    <div data-group="stack" style="{A.format(x=900, y=60)};width:900px;height:940px;background:#fff">{LINES}</div>
  </div>
  <div style="position:absolute;left:0;top:0;width:10px;height:10px;z-index:20"></div>
</div>
<script>const tl = gsap.timeline({{ paused: true }}); tl.to({{}}, {{ duration: 5 }}); window.__timelines = {{ fx: tl }};</script>
</body></html>"""


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    d = tmp_path_factory.mktemp("precheck_small")
    (d / "index.html").write_text(PAGE)
    out = d / "pc.json"
    p = subprocess.run(["node", str(ROOT / "kit/qa/precheck.mjs"), str(d / "index.html"), "--no-ambition", f"--json={out}"],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    return json.loads(out.read_text()), p.stdout


def small(report):
    return {f["text"].split()[0]: (f["sev"], f["px"]) for f in report[0]["findings"] if f["kind"] == "small"}


def test_a_mono_label_under_the_floor_is_small(report):
    assert small(report).get("runs") == ("MEDIUM", 30)


def test_svg_text_is_measured_at_its_drawn_size(report):
    assert small(report).get("a") == ("MEDIUM", 25)                  # font-size 50 in a viewBox drawn at half size


def test_kickers_and_the_floor_itself_pass(report):
    s = small(report)
    assert "PART" not in s and "exactly" not in s and "stack" not in s   # .lbl exempt; 31.7 px is 32 within 0.5 px


def test_a_large_block_counts_by_the_lines_it_holds(report):
    rep, out = report
    assert rep["density"]["max"] >= 4                                     # 12 lines in one stack: 4 groups, not 1
    assert "stack x4 (12 items)" in out
