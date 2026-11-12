"""The 2026-10-20 motion additions, run in node (no browser): log-space zoom in HF.keyed (kit/hf/core.js) and the
kinetic "cascade" / "focus" styles (kit/hf/kinetic.js)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HF = Path(__file__).resolve().parents[1] / "kit/hf"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")

JS = """
globalThis.window = globalThis;
globalThis.gsap = { parseEase: () => (p) => p };
require(%s); require(%s);
const lin = HF.keyed([{ t: 0, dur: 1, ease: (p) => p, v: { z: 4, x: 100 } }], { z: 1, x: 0 });
const log = HF.keyed([{ t: 0, dur: 1, ease: (p) => p, v: { z: 4, x: 100 } }], { z: 1, x: 0 }, { log: ["z"] });
const el = () => { const e = { style: {}, dataset: {}, children: [], append(...c) { this.children.push(...c); } }; return e; };
globalThis.document = { createElement: el };
const tw = [];
const K = { tl: { fromTo(t, a, b, at) { tw.push([a, b]); }, to() {}, set() {} }, Q: (t) => t, fps: 30, width: 1920, words_: [], sfx() {}, el: () => el() };
const out = { lin: lin(0.5), log: log(0.5), styles: {} };
for (const style of ["cascade", "focus"]) {
  tw.length = 0;
  const kt = HF.kinetic(K, null, { text: "Agents do the *boring* part", at: 0.5, style });
  out.styles[style] = { words: kt.words.length, chars: kt.words[0].inner.children.length, tweens: tw.length, from: tw[0] && Object.keys(tw[0][0]).sort() };
}
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    js = JS % (json.dumps(str(HF / "core.js")), json.dumps(str(HF / "kinetic.js")))
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


def test_log_zoom_is_halfway_in_ratio_and_pans_stay_linear(r):
    assert r["lin"]["z"] == pytest.approx(2.5)             # linear: 1 -> 4 is 2.5 at the half (rushes, then crawls)
    assert r["log"]["z"] == pytest.approx(2.0)             # log: 1 -> 4 is 2x at the half (an even pace to the eye)
    assert r["log"]["x"] == pytest.approx(50.0)            # only z is in log space


def test_cascade_splits_letters_and_focus_keeps_words(r):
    assert r["styles"]["cascade"]["chars"] == len("Agents")   # one span per letter
    assert "rotateX" in r["styles"]["cascade"]["from"]
    assert r["styles"]["focus"]["chars"] == 0 and r["styles"]["focus"]["words"] == 5
    assert "filter" in r["styles"]["focus"]["from"]
