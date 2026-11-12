"""The whitespace look (2026-10-22, kit/presets/whitespace) and the look-driven canvas, run in node (no browser):
HF.LOOKS.whitespace and its stage (kit/hf/core.js), canvas_studio's stage locked to the literals canvas.js drew
through v10 (its pages must stay pixel-identical), canvas.js's pure rules (a landed card holds still on whitespace
whatever drift a template passes; a film's palette accent reaches the whitespace stage, never canvas_studio's), one
grey for blocks, the preset's kicker rule, e1-e3 for older looks, HF.studioLook (kit/hf/studio.js), and the registry's
look detection (kit/hf/tools/registry.py)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "kit/hf"

JS = """
globalThis.window = globalThis;
globalThis.gsap = { parseEase: () => (p) => p };
require(%s); require(%s); require(%s); require(%s);
const out = { looks: Object.keys(HF.LOOKS), ws: HF.LOOKS.whitespace, cs: HF.LOOKS.canvas_studio.stage, applied: {} };
// canvas.js's pure rules: the drift a landed card keeps, and the stage's accent with and without a film's palette
const cs = HF.LOOKS.canvas_studio.stage, ws = HF.LOOKS.whitespace.stage, dr = HF.canvas.driftOf, ac = HF.canvas.accentOf;
const X = [{}, { drift: 1.2 }, { drift: false }, { drift: -1 }, { drift: 0 }, { drift: 12 }];
out.drift = { cs: X.map((x) => dr(x, cs)), ws: X.map((x) => dr(x, ws)) };
out.accent = { cs: ac(cs, cs.grad[0]), csPal: ac(cs, "#0F7B6C"), ws: ac(ws, HF.LOOKS.whitespace.C.acc), wsPal: ac(ws, "#0F7B6C") };
for (const n of ["pastel_box", "canvas_studio", "whitespace", "night"]) {
  HF.look(n);
  out.applied[n] = { e1: HF.C.e1, e2: HF.C.e2, e3: HF.C.e3, shadow: HF.C.shadow, shadowSoft: HF.C.shadowSoft, stage: !!HF.LOOK.stage, name: HF.LOOK.name };
}
out.studio = { pastel: HF.studioLook("pastel_box"), white: HF.studioLook("whitespace") };
try { HF.studioLook("nope"); out.unknown = null; } catch (e) { out.unknown = String(e.message); }
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    if shutil.which("node") is None:
        pytest.skip("needs node")
    js = JS % tuple(json.dumps(str(HF / m)) for m in ("core.js", "box.js", "studio.js", "canvas.js"))
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def _ratio(a, b):
    x, y = _lum(a), _lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def test_canvas_studio_stage_is_the_v10_literals(r):
    # canvas.js drew these as literals through v10; any drift here changes every canvas_studio page (the owner's approved look)
    s = r["cs"]
    assert s["seamless"] == "radial-gradient(ellipse 70% 75% at 50% 40%, #FFFEFC 0%, #F6F3EE 45%, #E9E4DB 100%)"
    assert s["edge"] == "#EEEAE3"
    assert s["grad"] == ["#6C5CE7", "#FF4D6D", "#FFB86B"]
    assert s["pastel"] == {"lilac": "#E7E1FF", "peach": "#FFE3D6", "mint": "#D9F2E6", "butter": "#FFF1C2", "sky": "#DCEBFF"}
    assert s["ring"] == "0 0 0 2px rgba(255,255,255,.9), 0 0 0 4px rgba(108,92,231,.55), 0 0 42px 6px rgba(255,77,109,.28), 0 30px 70px rgba(30,30,60,.18)"
    assert s["fill"] == "linear-gradient(160deg,#F3F0FF 0%,#FFF4F0 60%,#FFFFFF 100%)" and s["back"] is True
    assert s["win"]["dots"] == ["#FF5F57", "#FEBC2E", "#28C840"] and s["win"]["bar"] == "#F4F4F7"
    assert s["card"]["bg"] == "rgba(255,255,255,.92)"
    assert s["big"] == {"font": "'ArchivoCond', sans-serif", "weight": 900, "case": "uppercase", "lh": ".86", "track": "-0.01em", "ink": "#16161C"}
    assert s["hl"] == {"op": 0.42, "blend": "multiply"}                       # no bg: the gradient
    assert s["beam"] == {"glow": 0.55, "w": 10, "head": "#fff"}               # no line / wMax / ring: the v10 beam
    assert s["chart"] == {"area": 0.22, "glow": 0.45, "halo": 0.3, "grid": "#D9D9E1", "base": "#16161C", "w": 9}
    assert "driftMax" not in s and "blocks" not in s                          # its cards keep drifting, blocks by name


def test_drift_lands_still_on_whitespace_only(r):
    # canvas_studio: the template's drift or 2.2, exactly as v10 (drift: 0 now means none; no film passed it)
    assert r["drift"]["cs"] == [2.2, 1.2, 0, -1, 0, 12]
    # whitespace: every landed card holds still, a template's drift: 1.2 (canvas_studio's clue cards) included
    assert r["drift"]["ws"] == [0] * 6
    assert r["ws"]["stage"]["driftMax"] == 0


def test_whitespace_blocks_are_one_grey(r):
    assert r["ws"]["stage"]["blocks"] == "#F3F3F5"                            # a template's hex too, not only the names
    assert "ST.blocks || PAPER.pastel[col] || col" in (HF / "canvas.js").read_text()


def test_palette_accent_reaches_the_stage(r):
    a = r["accent"]
    # canvas_studio: its own gradient whatever the palette (as before), the white head, the gradient marker
    for k in ("cs", "csPal"):
        assert a[k]["G"] == {"a": "#6C5CE7", "b": "#FF4D6D", "c": "#FFB86B"} and a[k]["head"] == "#fff" and a[k]["hl"] is None
    # whitespace with no palette: exactly the stage's tokens
    assert a["ws"]["G"] == {"a": "#5646D6", "b": "#5646D6", "c": "#5646D6"} and a["ws"]["head"] == "#5646D6" and a["ws"]["hl"] == "#E4DFFF"
    # whitespace with a film's accent: one accent everywhere (stops, the beam's node, the marker's tint)
    p = a["wsPal"]
    assert set(p["G"].values()) == {"#0F7B6C"} and p["head"] == "#0F7B6C" and p["hl"] == "color-mix(in srgb, #0F7B6C 17%, #FFFFFF)"


def test_whitespace_kicker_rule_is_consistent():
    # the preset's one exception to the 32 px floor is the kicker, at >= 26 px in sub (>= 4.5:1), never in mute
    pj = json.loads((ROOT / "kit/presets/whitespace/preset.json").read_text())
    t = pj["type"]
    assert t["text_min_px"] == 32 and t["kicker_min_px"] == 26 and "sub" in t["kicker"] and "26-28 px" in t["kicker"]
    assert _ratio(pj["palette"]["sub"], "#FFFFFF") >= 4.5
    rd = (ROOT / "kit/presets/whitespace/README.md").read_text()
    assert "22-26 px" not in rd and "mono caps, 26-28 px, `HC.sub`" in rd


def test_canvas_js_has_no_stage_literals_left():
    # the stage's colours live in core.js now; one left behind in canvas.js would not follow the look
    src = (HF / "canvas.js").read_text()
    for lit in ("#FF4D6D", "#FFB86B", "#E9E4DB", "#EEEAE3", "#D9D9E1", "#FF5F57", "rgba(108,92,231,.55)"):
        assert lit not in src, lit


def test_whitespace_is_white_with_one_accent(r):
    w = r["ws"]
    C, st = w["C"], w["stage"]
    assert C["paper"] == C["card"] == "#FFFFFF"
    assert C["warm"] == C["acc"] and len(set(st["grad"])) == 1 and st["grad"][0] == C["acc"]   # one accent, no second hue
    assert st["seamless"].startswith("radial-gradient") and "#FFFFFF 0%" in st["seamless"]
    edge = int(st["edge"][1:3], 16) / 255
    assert 0.95 <= edge <= 0.975                                              # the falloff: only ~3-4 % darker at the corners
    assert st["beam"]["glow"] == 0 and st["chart"]["glow"] == 0 and st["chart"]["halo"] == 0   # no glows
    assert st["chart"]["areaEnd"] == st["chart"]["area"] <= 0.06              # a flat tint, no gradient fade
    assert st["back"] is False and set(st["pastel"].values()) == {"#F3F3F5"}  # no pastel blocks: one neutral grey
    assert st["beam"]["wMax"] <= 6
    assert all(k in C for k in ("e1", "e2", "e3")) and st["ring"] == C["e3"]
    assert w["F"]["display"] == w["F"]["body"] == "'Inter', sans-serif"


def test_whitespace_text_contrast_on_white(r):
    C = r["ws"]["C"]
    for k in ("ink", "text", "ink2", "sub", "acc", "ok", "bad"):
        assert _ratio(C[k], "#FFFFFF") >= 4.5, k
    assert _ratio(C["mute"], "#FFFFFF") >= 3 and _ratio(C["mute"], C["sunk"]) >= 3
    assert _ratio(C["ink"], "#FFFFFF") < 21                                   # near-black, never pure black on pure white


def test_elevation_falls_back_for_older_looks(r):
    a = r["applied"]
    for n in ("pastel_box", "canvas_studio", "night"):
        assert a[n]["e1"] == a[n]["shadowSoft"] and a[n]["e2"] == a[n]["e3"] == a[n]["shadow"], n
    assert a["whitespace"]["e1"] != a["whitespace"]["e3"]
    assert a["canvas_studio"]["stage"] and a["whitespace"]["stage"] and not a["pastel_box"]["stage"] and not a["night"]["stage"]


def test_studio_look(r):
    p, w = r["studio"]["pastel"], r["studio"]["white"]
    assert p["pastel"] and p["C"] == {} and p["boxShadow"] is None            # pastel_box: exactly the old frame
    assert p["chrome"] == "rgba(60,56,90,.62)" and p["stress"] == "italic"
    assert w["stress"] == "normal"                                            # Inter has no italic: the accent colour is the mark
    assert not w["pastel"] and w["world"] == r["ws"]["stage"]["seamless"] and w["edge"] == r["ws"]["stage"]["edge"]
    assert w["C"]["acc"] == r["ws"]["C"]["acc"] and w["C"]["okSoft"] == r["ws"]["C"]["okTint"] and w["C"]["aurora"] == []
    assert "unknown look nope" in r["unknown"]


def test_registry_knows_whitespace():
    sys.path.insert(0, str(HF / "tools"))
    import registry
    assert "whitespace" in registry.LOOKS_ALL
    assert "whitespace" in registry.HOME["canvas.js"][2] and "whitespace" in registry.HOME["studio.js"][2]
    assert registry.look_of('const C = HF.canvas(K, ROOT, { w: 5760, look: "whitespace" });') == "whitespace"
    assert registry.look_of("const S = HF.studio(K, ROOT, st, { end: 9, look: 'whitespace' });") == "whitespace"
    assert registry.look_of("const C = HF.canvas(K, ROOT, { w: 5760 });") == "canvas_studio"
    assert registry.look_of("const S = HF.studio(K, ROOT, st, { end: 9 });") == "pastel_box"
    reg = json.loads((HF / "registry.json").read_text())["components"]
    assert "whitespace" in reg["canvas.beam"]["looks"] and "whitespace" in reg["ui.pr"]["looks"]
