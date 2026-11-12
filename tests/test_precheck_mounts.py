"""kit/qa/precheck.mjs reads the text inside HyperFrames catalog pieces (film.py MOUNTS): it fills each mount the way
HyperFrames' compiler does, so a piece's small type and a page line over it are findings named after the piece.
Runs the real precheck in headless Chrome on a fixture page built through kit/hf/mounts.py."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit/hf"))
import mounts  # noqa: E402

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
GSAP = ROOT / "node_modules/gsap/dist/gsap.min.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None or not CHROME.exists() or not GSAP.exists(),
                                reason="needs node, Google Chrome and node_modules/gsap")

PAGE = f"""<!doctype html><html><head><meta charset="UTF-8"><script src="file://{GSAP}"></script></head><body>
<div id="root" data-composition-id="fx" data-start="0" data-duration="5" data-width="1920" data-height="1080"
     style="position:relative;width:1920px;height:1080px;overflow:hidden;background:#f4f1ea">
  <div style="position:absolute;inset:0;z-index:2"><div style="position:absolute;left:900px;top:700px;font:700 60px sans-serif">Page line on top</div></div>
  <div style="position:absolute;left:0;top:0;width:10px;height:10px;z-index:20"></div>
</div>
<script>const tl = gsap.timeline({{ paused: true }}); tl.to({{}}, {{ duration: 5 }}); window.__timelines = {{ fx: tl }};</script>
</body></html>"""


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    d = tmp_path_factory.mktemp("precheck_mounts")
    specs = [dict(name="marker-highlight", box=(100, 100, 300, 90), vars=dict(text="Tiny words here", emphasis_word="words")),
             dict(name="marker-highlight", box=(700, 600, 1000, 300), vars=dict(text="Big words", emphasis_word="Big"))]
    (d / "index.html").write_text(mounts.install(d, specs, [0.5, 0.5], PAGE, look="paper_studio"))
    out = d / "pc.json"
    subprocess.run(["node", str(ROOT / "kit/qa/precheck.mjs"), str(d / "index.html"), "--no-ambition", f"--json={out}"],
                   capture_output=True, text=True, cwd=ROOT, timeout=180)
    return json.loads(out.read_text())


def test_both_pieces_are_filled_and_checked(report):
    assert [(m["name"], m["ok"]) for m in report["catalog"]] == [("marker-highlight", True)] * 2


def test_small_type_inside_a_piece_is_a_finding_named_after_it(report):
    small = [f for f in report["findings"] if f["kind"] == "small"]
    assert len(small) == 1 and small[0]["text"].startswith("catalog marker-highlight: Tiny words here")
    assert small[0]["px"] < 32 and small[0]["b"] - small[0]["a"] >= 0.8


def test_a_page_line_over_a_piece_overlaps_it(report):
    over = [f["text"] for f in report["findings"] if f["kind"] == "overlap"]
    assert any("Page line on top" in t and "catalog marker-highlight: " in t for t in over)
