"""The flat diagram (kit/hf/diagram.js style "flat"; kit/refs/DIAGRAMS.md; engine-adopt, 2026-10-22): diagram-design's
rules (cathrynlavery/diagram-design 2.6, MIT) at video scale on the whitespace look. Pure logic in node: which style a
call draws, the layout (margins, the 4 px grid, gaps, ports that never share a point, lanes for a way back, z turns
that never cross), the budgets it warns about, the step counter, and the geometry gate (HF.diagram.verify, ported
from diagram-design's verify-geometry.py) catching each defect it is for. In Chrome: a flat page publishes clean
geometry to window.__diagrams and seeks pure; old styles draw what they drew unless a page opts in to the fixes."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "kit/hf"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")

PURE = """
globalThis.window = globalThis;
globalThis.gsap = { parseEase: () => (p) => p };
for (const f of %(files)s) require(f);
const D = HF.diagram, out = {};
const lay = (o, w = 1920, h = 1080, x = {}) => { const ws = []; const g = D.layout(o, w, h, Object.assign({ warn: (m) => ws.push(m) }, x)); return { g, ws, v: D.verify(g) }; };
const loop = { title: "the loop", nodes: [{ id: "build", label: "Build", sub: "HTML + GSAP", mono: true }, { id: "draft", label: "Draft", sub: "1080p", mono: true },
  { id: "critic", label: "Critic", sub: "checks every frame", focal: true }], edges: [["build", "draft"], ["draft", "critic"], { from: "critic", to: "build", label: "fix what broke", accent: true }] };
out.loop = lay(loop);
// a way back between neighbours (films/expensewaale's check -> edit): never on the way there's start point
out.pingpong = lay({ nodes: [{ id: "a", label: "Edit" }, { id: "b", label: "Check" }, { id: "c", label: "Ship" }], edges: [["a", "b"], ["b", "a"], ["b", "c"]] });
out.pingStraight = lay({ nodes: [{ id: "a", label: "Edit" }, { id: "b", label: "Check" }], edges: [["a", "b"], { from: "b", to: "a", route: "straight" }] });
out.hub = lay({ layout: "hub", hub: "main", nodes: [{ id: "main", label: "Main agent" }, { id: "x", label: "Design" }, { id: "y", label: "Build" }, { id: "z", label: "Review" }, { id: "w", label: "Ship" }],
  edges: [["main", "x"], ["main", "y"], ["main", "z"], ["main", "w"]] });
out.fanin = lay({ layout: "hub", hub: "main", nodes: [{ id: "main", label: "The page" }, { id: "x", label: "Look" }, { id: "y", label: "Camera" }, { id: "z", label: "Sound" }],
  edges: [["x", "main"], ["y", "main"], ["z", "main"]] });
out.column = lay({ title: "the loop", layout: "column", nodes: loop.nodes.concat([{ id: "ship", label: "Ship", sub: "4K", mono: true }]),
  edges: [["build", "draft"], ["draft", "critic"], ["critic", "ship"], { from: "critic", to: "build", label: "fix it" }] }, 1080, 980, { portrait: true });
out.nested = lay({ nodes: ["a", "b", "c", "d"].map((id) => ({ id, label: id.toUpperCase() })), edges: [["a", "b"], ["b", "c"], ["c", "d"], ["d", "a"], ["d", "b"], ["a", "c"]] });
out.free = lay({ nodes: [{ id: "a", label: "In", x: 400, y: 540 }, { id: "b", label: "Out", x: 1400, y: 300 }], edges: [["a", "b"]] });
// over budget: six boxes, seven edges, three focal, a long label
out.budget = lay({ nodes: [1, 2, 3, 4, 5, 6].map((i) => ({ id: "n" + i, label: "N" + i, focal: i < 4 })),
  edges: [["n1", "n2"], ["n2", "n3"], ["n3", "n4"], ["n4", "n5"], ["n5", "n6"], ["n6", "n1"], { from: "n3", to: "n1", label: "a label far too long" }] }).ws;
// the gate catches each defect it is for (made-up geometry)
const box = (id, x, y, w = 300, h = 180) => ({ id, x, y, w, h });
const N2 = [box("a", 100, 400), box("b", 700, 400), box("c", 400, 400)];
out.bad = {
  diagonal: D.verify({ nodes: [box("a", 100, 100), box("b", 800, 600)], edges: [{ from: "a", to: "b", pts: [[400, 190], [800, 690]] }] }),
  shared: D.verify({ nodes: N2.slice(0, 2), edges: [{ from: "a", to: "b", pts: [[400, 490], [700, 490]] }, { from: "b", to: "a", pts: [[700, 500], [400, 500]] }] }),
  corner: D.verify({ nodes: N2.slice(0, 2), edges: [{ from: "a", to: "b", pts: [[400, 410], [700, 410]] }] }),
  behind: D.verify({ nodes: [box("a", 100, 400), box("c", 600, 400), box("b", 1100, 400)], edges: [{ from: "a", to: "b", pts: [[400, 490], [1100, 490]] }] }),
  border: D.verify({ nodes: N2.slice(0, 2), edges: [{ from: "a", to: "b", pts: [[250, 400], [390, 400], [390, 300], [800, 300], [800, 400]] }] }),
  stacked: D.verify({ nodes: [box("a", 100, 100), box("b", 100, 700)], edges: [{ from: "a", to: "b", pts: [[200, 280], [200, 700]] }, { from: "a", to: "b", pts: [[201, 280], [201, 700]] }] }),
  label: D.verify({ nodes: N2.slice(0, 2), edges: [{ from: "a", to: "b", pts: [[400, 490], [700, 490]], lab: { x: 380, y: 470, w: 200, h: 38 } }] }),
  clean: D.verify({ nodes: N2.slice(0, 2), edges: [{ from: "a", to: "b", pts: [[400, 490], [700, 490]], lab: { x: 450, y: 442, w: 200, h: 38 } }] }),
};
// the legacy bug, measured: HF.diagram's old anchor put check -> edit's end on edit -> check's start
out.steps = [D.steps([0, 0.1, 0.2]), D.steps([0, 0.48, 0.96]), D.steps([0, 0.24, 0.48]), D.steps([])];
const L = HF.look;
L("paper_studio"); out.style = [D.styleOf({}), D.styleOf({ shape: "card" })];
L("whitespace"); out.style.push(D.styleOf({}), D.styleOf({ shape: "card" }), D.styleOf({ style: "circle" }));
L("canvas_studio"); out.style.push(D.styleOf({}), D.styleOf({ style: "flat" }));
out.textW = [D.textW("Main agent", 48), D.textW("FIX WHAT BROKE", 26, "kick"), D.textW("1080p", 32, "mono")];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    files = [str(HF / f) for f in ("core.js", "diagram.js")]
    p = subprocess.run(["node", "-e", PURE % {"files": json.dumps(files)}], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def segs(e):
    return list(zip(e["pts"], e["pts"][1:]))


def test_a_page_built_before_v11_keeps_its_circles(r):
    # no style and never whitespace: the icon circles, as before; explicit shapes win everywhere; flat on whitespace
    assert r["style"] == ["circle", "card", "flat", "card", "circle", "circle", "flat"]


def test_the_loop_is_one_clean_system(r):
    g, ws, v = r["loop"]["g"], r["loop"]["ws"], r["loop"]["v"]
    assert v == [] and ws == []
    n = {x["id"]: x for x in g["nodes"]}
    for x in g["nodes"]:                                           # the grid, the margins, the sizes
        assert x["x"] % 4 == 0 and x["y"] % 4 == 0 and x["w"] % 4 == 0 and x["h"] % 4 == 0
        assert x["x"] >= 120 and x["x"] + x["w"] <= 1800 and x["h"] >= 176
    assert n["draft"]["x"] - (n["build"]["x"] + n["build"]["w"]) >= 112
    assert [x["tag"] for x in g["nodes"]] == ["01", "02", "03"]
    back = g["edges"][2]
    assert back["route"] == "under" and back["dash"] and back["accent"]          # the way back: dashed, under the row
    assert back["pts"][1][1] > n["critic"]["y"] + n["critic"]["h"]               # it leaves downward
    lab = back["lab"]                                                            # its meaning, 10 px over its run
    assert lab["y"] + lab["h"] == back["pts"][1][1] - 10
    for e in g["edges"][:2]:                                                     # neighbours: straight, level
        assert e["route"] == "straight" and e["pts"][0][1] == e["pts"][1][1]
    # no two connectors on one point
    ends = [tuple(p) for e in g["edges"] for p in (e["pts"][0], e["pts"][-1])]
    assert len(ends) == len(set(ends))
    # the block sits in the middle of the frame
    xs = [x["x"] for x in g["nodes"]] + [x["x"] + x["w"] for x in g["nodes"]]
    assert abs((min(xs) + max(xs)) / 2 - 960) <= 4


def test_a_way_back_between_neighbours_never_shares_a_port(r):
    for k in ("pingpong", "pingStraight"):
        g, v = r[k]["g"], r[k]["v"]
        assert v == [], (k, v)
        ab, ba = g["edges"][0], g["edges"][1]
        assert {tuple(ab["pts"][0]), tuple(ab["pts"][-1])}.isdisjoint({tuple(ba["pts"][0]), tuple(ba["pts"][-1])})
    assert r["pingpong"]["g"]["edges"][1]["route"] == "under"
    sb = r["pingStraight"]["g"]["edges"]                                         # asked straight: two parallel lines
    assert abs(sb[0]["pts"][0][1] - sb[1]["pts"][0][1]) >= 32


def test_a_hub_fans_out_without_crossing(r):
    g, v = r["hub"]["g"], r["hub"]["v"]
    assert v == []
    hub = g["nodes"][0]
    starts = sorted(e["pts"][0][1] for e in g["edges"])
    assert all(b - a >= 32 for a, b in zip(starts, starts[1:]))                   # fanned on the hub's side
    assert all(hub["y"] + 22 <= s <= hub["y"] + hub["h"] - 22 for s in starts)
    for e in g["edges"]:                                                          # each lands mid-side on its spoke
        to = next(x for x in g["nodes"] if x["id"] == e["to"])
        assert e["pts"][-1][1] == to["y"] + to["h"] / 2 or e["route"] == "straight"
    assert r["fanin"]["v"] == []
    straight = [e for e in r["fanin"]["g"]["edges"] if e["route"] == "straight"]
    assert len(straight) == 1                                                     # the one that lines up runs straight


def test_a_portrait_column_fits_a_reels_band(r):
    g, v = r["column"]["g"], r["column"]["v"]
    assert v == []
    assert g["size"]["inline"] and g["size"]["KS"] == 30 and g["size"]["NZ"] == 52
    ys = [x["y"] for x in g["nodes"]] + [x["y"] + x["h"] for x in g["nodes"]] + [g["title"]["y"]]
    assert min(ys) >= 40 and max(ys) <= 940                                       # inside the 980 px band, 40 px margins
    xs = [x["x"] for x in g["nodes"]] + [x["x"] + x["w"] for x in g["nodes"]]
    back = g["edges"][3]
    assert back["route"] == "under" and back["pts"][1][0] > max(xs)               # the way back on the right
    right = back["lab"]["x"] + back["lab"]["w"]
    # the boxes centred as far as the margins allow: its label may push the column left, never past 120 px
    assert right <= 960 and min(xs) >= 120
    assert abs((min(xs) + max(xs)) / 2 - 540) <= 4 or right > 952


def test_nested_lanes_and_skips_stay_traceable(r):
    g, v = r["nested"]["g"], r["nested"]["v"]
    assert v == [], v
    routes = {(e["from"], e["to"]): e["route"] for e in g["edges"]}
    assert routes[("d", "a")] == routes[("d", "b")] == "under" and routes[("a", "c")] == "over"
    da, db = (next(e for e in g["edges"] if (e["from"], e["to"]) == k) for k in (("d", "a"), ("d", "b")))
    assert da["pts"][1][1] > db["pts"][1][1]                                      # the longer way back runs outside
    assert r["free"]["v"] == [] and r["free"]["g"]["edges"][0]["route"] in ("z", "straight")


def test_budgets_are_said(r):
    ws = " | ".join(r["budget"])
    assert "6 nodes (at most 5" in ws and "7 edges (at most 6)" in ws and "3 focal nodes" in ws and "20 characters" in ws


def test_the_gate_catches_what_it_is_for(r):
    b = r["bad"]
    assert any("diagonal" in x for x in b["diagonal"])
    assert any("fan the ports" in x for x in b["shared"])                         # an end and a start count as a pair
    assert any("corner" in x for x in b["corner"])
    assert any("passes behind" in x for x in b["behind"])
    assert any("border" in x for x in b["border"])
    assert any("runs on top of" in x for x in b["stacked"])
    assert any("sits on" in x for x in b["label"]) and any("covers the line" in x for x in b["label"])
    assert b["clean"] == []                                                       # a label 10 px over its line is fine


def test_steps_count_items_entering_together(r):
    assert r["steps"] == [3, 1, 2, 0]


def test_widths_are_estimated_without_fonts(r):
    name, kick, mono = r["textW"]
    assert 240 <= name <= 270                                                     # Inter 600 48 px: 249 px in Chrome
    assert kick == pytest.approx(14 * 26 * 0.74) and mono == pytest.approx(5 * 32 * 0.62)


CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
chrome = pytest.mark.skipif(not CHROME.exists() or not (ROOT / "node_modules/puppeteer-core").exists(), reason="needs puppeteer-core and Google Chrome")
PAGE = """<!doctype html><html lang="en"><head><meta charset="UTF-8" /><!--HF:KIT--></head><body>
<div id="root" data-composition-id="fx" data-start="0" data-duration="10" data-width="1920" data-height="1080" style="position:relative;width:1920px;height:1080px;overflow:hidden"></div>
<script>
const D = /*D*/;
(function () {
  HF.look(D.look);
  const tl = gsap.timeline({ paused: true });
  window.__timelines = { fx: tl };
  const K = HF.kit({ tl, id: "fx", width: 1920, height: 1080, words: [], pieces: [] });
  const L = K.el(document.getElementById("root"), "left:0;top:0;width:1920px;height:1080px");
  const dg = HF.diagram(K, L, Object.assign({ title: "the loop", nodes: [{ id: "a", label: "Build", sub: "the page" }, { id: "b", label: "Draft" }, { id: "c", label: "Critic", focal: true }],
    edges: [["a", "b"], ["b", "c"], { from: "c", to: "a", label: "fix it", curve: 0.3 }] }, D.opt));
  dg.show(0.2, 9.5).reveal("a", 0.5).reveal("b", 1.0).reveal("c", 1.5).connect("a", "b", 0.8).connect("b", "c", 1.3).connect("c", "a", 2.0, 0.8);
  dg.flow("c", "a", 3, { dur: 1 }).highlight("b", 4, 6).done("a", 6.5).focus("c", 7, { zoom: 1.4 }).overview(8.4);
  K.finish(10);
})();
</script></body></html>"""
PROBE = """
import { createRequire } from "node:module";
const puppeteer = createRequire(%(pkg)s)("puppeteer-core");
const [file] = process.argv.slice(2);
const br = await puppeteer.launch({ executablePath: %(chrome)s, headless: true, args: ["--allow-file-access-from-files"] });
const p = await br.newPage(), errs = [], warns = [];
p.on("pageerror", (e) => errs.push(String(e.message || e)));
p.on("console", (m) => { if (m.type() === "warning") warns.push(m.text()); });
await p.setViewport({ width: 1920, height: 1080 });
await p.goto("file://" + file, { waitUntil: "domcontentloaded" });
await p.waitForFunction(() => !!(window.__timelines && window.__timelines.fx), { timeout: 60000 });
const r = await p.evaluate(() => {
  const tl = window.__timelines.fx, ts = [0.1, 0.7, 1.2, 2.4, 3.5, 5, 6.8, 7.5, 9];
  const els = [...document.querySelectorAll("#root div, #root svg *")];
  const seen = (e) => { let o = 1; for (let x = e; x && x.nodeType === 1; x = x.parentNode) { const cs = getComputedStyle(x);
    if (cs.visibility === "hidden" || cs.display === "none") return 0; o *= +cs.opacity * (x.getAttribute && x.getAttribute("opacity") != null ? +x.getAttribute("opacity") : 1); } return o; };
  const state = (t) => { tl.seek(t, false); return els.map((e) => { const o = seen(e); if (o < 0.001) return "h"; const cs = getComputedStyle(e);
    return [o.toFixed(3), e.style.transform, e.getAttribute("cx"), e.style.strokeDashoffset, cs.backgroundColor, cs.color].join("|"); }).join(";"); };
  const fwd = ts.map(state), back = ts.slice().reverse().map(state).reverse(), jump = ts.map((t) => { tl.seek(9.9, false); return state(t); });
  const d = window.__diagrams;
  return { pure: fwd.every((x, i) => x === back[i] && x === jump[i]), n: d.length, style: d[0].style, gate: d[0].gate, show: d[0].show,
    verify: d[0].gate ? HF.diagram.verify(d[0]) : null, nodes: d[0].nodes.length, edges: d[0].edges.map((e) => e.pts.length) };
});
console.log(JSON.stringify(Object.assign(r, { errs, warns })));
await br.close();
"""


def run_page(tmp_path, D):
    import sys
    sys.path.insert(0, str(HF))
    import vendor
    vendor.copy_assets(tmp_path)
    f = tmp_path / "fx.html"
    f.write_text(vendor.inline(PAGE).replace("/*D*/", json.dumps(D)))
    js = tmp_path / "probe.mjs"
    js.write_text(PROBE % {"pkg": json.dumps(str(ROOT / "package.json")), "chrome": json.dumps(str(CHROME))})
    p = subprocess.run(["node", str(js), str(f)], capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["errs"] == [], out["errs"]
    return out


@chrome
def test_a_flat_page_publishes_clean_geometry_and_seeks_pure(tmp_path):
    out = run_page(tmp_path, {"look": "whitespace", "opt": {}})
    assert out["style"] == "flat" and out["gate"] and out["verify"] == [] and out["n"] == 1
    assert out["show"] == [[0.2, 9.5]] and out["nodes"] == 3
    assert out["pure"]
    assert not [w for w in out["warns"] if "HF.diagram" in w]                      # inside every budget


@chrome
@pytest.mark.parametrize("opt", [{}, {"margin": 120, "ports": "fan"}, {"shape": "card", "margin": 120, "ports": "fan"}])
def test_old_styles_seek_pure_and_publish_their_ends(tmp_path, opt):
    out = run_page(tmp_path, {"look": "canvas_studio", "opt": opt})
    assert out["style"] == opt.get("shape", "circle") and not out["gate"]
    assert out["edges"] == [2, 2, 2] and out["pure"]
