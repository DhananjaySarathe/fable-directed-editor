"""Takeovers and transitions (kit/hf/trans.js, the takeover side of kit/hf/canvas.js and kit/hf/box.js; 2026-10-22,
kit v11). Pure logic in node: his shots with the takeovers written in (HF.canvas.takeoverShots), the box's takeover
beats (HF.box.takeoverBeats / direct), the transition budget (HF.trans.check / pick). In Chrome: a canvas page with
takeovers publishes him "off" while the scene has the frame and back after, logs its transitions, and every frame is a
pure function of time (seeking forward, backward or straight to a frame gives the same page)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "kit/hf"
node = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")

PURE = """
globalThis.window = globalThis;
globalThis.gsap = { parseEase: () => (p) => p };
globalThis.document = { getElementById: () => null };
for (const f of %(files)s) require(f);
const C = HF.canvas.takeoverShots, card = (t, x, extra = {}) => Object.assign({ t, mode: "card", x, y: 540, w: 400, h: 400, r: 40 }, extra);
const tpl = [card(0, 1500), card(3, 400, { dur: 0.6 }), card(7, 900), card(12, 1500)];
const el = { id: "graphic" }, el2 = { id: "last" };
const out = {
  none: C(tpl, []).shots.map((s) => s === tpl[tpl.indexOf(s)]),
  noneT: C(tpl, []).shots.map((s) => s.t),
  cut: C(tpl, [{ a: 5, off: 5, on: 10, fadeIn: 0, fadeOut: 0.4 }]),
  near: C(tpl, [{ a: 5, off: 5, on: 12.03, fadeIn: 0, fadeOut: 0 }]).shots.map((s) => [s.t, !!s.off, s.tk || 0]),
  card: C(tpl, [{ a: 5, off: 5.55, on: 10, into: el, from: el2, fromDur: 0.55 }]).shots.map((s) => [s.t, !!s.off, s.into ? s.into.id : null, s.from ? s.from.id : null, s.intoAt != null ? s.intoAt : null, !!s.cut]),
  stays: C(tpl, [{ a: 5, off: 5.55, on: null, into: el }]).shots.map((s) => [s.t, !!s.off]),
  two: C(tpl, [{ a: 8, off: 8, on: 11 }, { a: 2, off: 2, on: 2.9 }]).shots.map((s) => [s.t, !!s.off, s.x]),
  check: HF.trans.check([{ t: 1, kind: "whip" }, { t: 2, kind: "cut" }, { t: 3, kind: "cut" }, { t: 4, kind: "zoom" }, { t: 5, kind: "zoom" }, { t: 6, kind: "whip" }]),
  whips: HF.trans.check([{ t: 1, kind: "whip" }, { t: 2, kind: "zoom" }, { t: 3, kind: "whip" }, { t: 4, kind: "fade" }, { t: 5, kind: "whip" }]),
  // review 2026-10-22: a speaker already off at a stays off (no morph into the card, no return); a speaker that is not
  // the primary fades off and back instead of morphing; a primary-only takeover (T.cardToGraphic) leaves it alone
  hidden: C([card(0, 700), card(4, 700, { off: true, cut: true })], [{ a: 8, off: 8.55, on: 12, into: el, from: el2, fromDur: 0.55 }, { a: 14, off: 14, on: 18 }])
    .shots.map((s) => [s.t, !!s.off, !!(s.into || s.from)]),
  hiddenLater: C([card(0, 700), card(4, 700, { off: true, cut: true }), card(20, 700)], [{ a: 8, off: 8, on: 12 }]).shots.map((s) => [s.t, !!s.off]),
  side: C(tpl, [{ a: 5, off: 5.55, on: 10, into: el, from: el2, fromDur: 0.55 }], { morph: false }).shots.map((s) => [s.t, !!s.off, !!(s.into || s.from), s.dur || 0, !!s.cut]),
  sidePrimary: C(tpl, [{ a: 5, off: 5.55, on: 10, into: el, from: el2, primary: true }], { morph: false }).shots.map((s) => s.t),
  firstLater: C([card(6, 900)], [{ a: 2, off: 2, on: 4 }]).shots.map((s) => [s.t, !!s.off, s.x]),
  dropped: C(tpl, [{ a: 1, off: 1, on: 2.5 }, { a: 5, off: 5, on: 7.2 }]),
  pick: [HF.trans.pick([{ t: 1, kind: "zoom" }, { t: 9, kind: "match" }], 5, ["zoom", "match", "whip"]),
    HF.trans.pick([{ t: 1, kind: "whip" }, { t: 2, kind: "zoom" }, { t: 3, kind: "fade" }], 5, ["whip", "card"]),
    HF.trans.pick([{ t: 1, kind: "zoom" }], 5, ["zoom"])],
  // review 2026-10-22 (round 3): a takeover's own in / out of one kind (and cardToGraphic's morph and return) is one
  // bracket; a kind between them, or the same kind again after the bracket, is judged as before
  bracket: HF.trans.check([{ t: 8, kind: "card", pair: 1 }, { t: 13, kind: "card", pair: 1 }, { t: 18, kind: "zoom" }]),
  between: HF.trans.check([{ t: 8, kind: "card", pair: 1 }, { t: 10, kind: "zoom" }, { t: 13, kind: "card", pair: 1 }]),
  after: HF.trans.check([{ t: 8, kind: "card", pair: 1 }, { t: 13, kind: "card", pair: 1 }, { t: 18, kind: "card", pair: 2 }]),
  twoPairs: HF.trans.check([{ t: 16, kind: "fade", pair: 3 }, { t: 22, kind: "fade", pair: 3 }, { t: 30, kind: "fade", pair: 4 }, { t: 36, kind: "fade", pair: 4 }]),
  folded: HF.trans.fold([{ t: 8, kind: "card", why: "in", pair: 1 }, { t: 13, kind: "card", why: "out", pair: 1 }]),
  pickIn: HF.trans.pick([{ t: 8, kind: "card", pair: 1 }, { t: 13, kind: "card", pair: 1 }], 10, ["card", "zoom"]),
  pickAfter: HF.trans.pick([{ t: 8, kind: "card", pair: 1 }, { t: 13, kind: "card", pair: 1 }], 20, ["card", "whip"]),
  // overlapping takeovers would leave him off for good: claim throws; under 3 s of face between two warns
  overlap: (() => { try { HF.trans.claim([{ a: 16, on: 22 }], 20, 26, "C.takeover"); return "no error"; } catch (e) { return e.message; } })(),
  gap: (() => { const ws = [], w0 = console.warn; console.warn = (m) => ws.push(m); HF.trans.claim([{ a: 16, on: 22 }], 23.5, 28, "C.takeover");
    HF.trans.claim([{ a: 16, on: 22 }], 26, 30, "C.takeover"); HF.trans.claim([{ a: 16, on: null }], 17, 20, "C.takeover"); console.warn = w0; return ws; })(),
  // the type kind's cascading line fits the frame like the statement does
  fit: [HF.takeover.typeFit({ text: "Neat.", then: { text: "and the camera does the rest of the work for you" } }, 1920, false, "Inter"),
    HF.takeover.typeFit({ text: "Neat.", then: { text: "short" } }, 1920, false, "Inter"),
    HF.takeover.typeFit({ text: "Neat.", then: { text: "and the camera does the rest of the work for you", size: 120 } }, 1920, false, "Inter"),
    HF.takeover.typeFit({ text: "Neat beats busy." }, 1080, true, "InstrumentSerif")],
};
// the box: a takeover beat with until -> off, the beats inside dropped, his previous show back at until
const B = HF.box, beats = [{ t: 0, show: "face" }, { t: 3, show: "beside", side: "left" }, { t: 6, show: "takeover", until: 11 }, { t: 8, show: "aside" }, { t: 16, show: "face" }];
out.tb = B.takeoverBeats(beats);
out.direct = B.direct({ beats }).shots.map((s) => [s.t, typeof s.at === "string" ? s.at : "obj:" + s.at.op, s.in, s.tag]);
out.kept = B.takeoverBeats([{ t: 0, show: "face" }, { t: 6, show: "takeover", until: 11 }, { t: 11.2, show: "hero" }]).beats.map((b) => [b.t, b.show]);
out.plain = B.direct({ beats: [{ t: 0, show: "face" }, { t: 3, show: "graphic" }, { t: 20, show: "face" }] }).log.filter((l) => l[2] === "note").map((l) => l[3]);
out.push = [{}, { push: 0 }, { push: null }, { push: 0.06 }, { push: false }, { push: -1 }].map((x) => HF.takeover.pushOf(x));
out.moved = B.direct({ beats: [{ t: 0, show: "face" }, { t: 4, show: "beside", side: "left" }, { t: 6, show: "takeover", until: 10, move: "collapse", card: true, backMove: "grow" }] }).shots.map((s) => [s.t, typeof s.at === "string" ? s.at : "obj:" + s.at.op, s.in]);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    files = [str(HF / f) for f in ("core.js", "kinetic.js", "motion.js", "box.js", "canvas.js", "trans.js")]
    p = subprocess.run(["node", "-e", PURE % {"files": json.dumps(files)}], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


@node
def test_no_takeover_leaves_his_shots_as_they_were(r):
    assert all(r["none"]) and r["noneT"] == [0, 3, 7, 12]                 # the same shot objects, in time order


@node
def test_a_takeover_takes_him_off_drops_the_shots_inside_and_brings_his_shape_back(r):
    sh, log = r["cut"]["shots"], r["cut"]["log"]
    rows = [(s["t"], bool(s.get("off")), s.get("cut", False), s.get("tk", 0), s["x"]) for s in sh]
    assert rows == [(0, False, False, 0, 1500), (3, False, False, 0, 400), (5, True, True, 1, 400), (10, False, False, 1, 400), (12, False, False, 0, 1500)]
    back = sh[3]
    assert back["dur"] == 0.4 and back["sfx"] is False                    # a fade back in, no whoosh of its own
    assert len(log) == 1 and "dropped his shot at 7.00" in log[0]


@node
def test_a_template_shot_on_the_return_is_the_return(r):
    assert r["near"] == [[0, False, 0], [3, False, 0], [5, True, 1], [12, False, 0]]   # 7 dropped; 12.03 is within 0.05 s


@node
def test_his_card_morphs_into_the_graphic_and_grows_back_out_of_the_last_card(r):
    assert r["card"] == [
        [0, False, None, None, None, False], [3, False, None, None, None, False],
        [5, False, "graphic", None, 5.55, False],          # the morph: his card into the graphic's frame
        [5.55, True, "graphic", None, 5.55, True],         # then off, the graphic is there
        [9.999, True, "last", None, 10, True],             # off in the last card's frame, just before the return
        [10, False, None, "last", None, False],            # grown back out of it
        [12, False, None, None, None, False]]


@node
def test_a_card_that_stays_the_graphic_has_no_return(r):
    # no return: his next template shot brings him back (here the one at 7 s)
    assert r["stays"] == [[0, False], [3, False], [5, False], [5.55, True], [7, False], [12, False]]


@node
def test_two_takeovers_each_restore_the_shape_before_them(r):
    assert r["two"] == [[0, False, 1500], [2, True, 1500], [2.9, False, 1500], [3, False, 400], [7, False, 900], [8, True, 900], [11, False, 900], [12, False, 1500]]


@node
def test_a_speaker_already_off_stays_off_through_a_takeover(r):
    # review 2026-10-22 (a screen speaker hidden at 4 s came back beside his face, morphed into the card and stayed on):
    # it gets an off shot at a, nothing morphs and nothing returns; its own next shot brings it back
    assert r["hidden"] == [[0, False, False], [4, True, False], [8, True, False], [14, True, False]]
    assert r["hiddenLater"] == [[0, False], [4, True], [8, True], [20, False]]


@node
def test_a_speaker_that_is_not_the_primary_fades_instead_of_morphing(r):
    assert r["side"] == [[0, False, False, 0, False], [3, False, False, 0.6, False],
                         [5, True, False, pytest.approx(0.55), False],    # off over the morph's time, no into
                         [10, False, False, 0.55, False],                 # back over the return's time, no from
                         [12, False, False, 0, False]]
    assert r["sidePrimary"] == [0, 3, 7, 12]                              # T.cardToGraphic: not its business


@node
def test_a_takeover_before_the_first_shot_keeps_the_shape_drawn_before_it(r):
    # a speaker is drawn in its first shot's shape from 0; the takeover's off shot must not become its first
    assert r["firstLater"] == [[0, False, 900], [2, True, 900], [4, False, 900], [6, False, 900]]


@node
def test_the_merge_says_what_it_drops(r):
    d = r["dropped"]
    assert d["dropped"] == [{"tk": 1, "t": 7}]
    assert len(d["log"]) == 1 and d["log"][0].startswith("7.00 takeover 2 (5.00-7.20): dropped his shot at 7.00")
    assert "a return meant for 7.20?" in d["log"][0]                    # 0.2 s before b: likely a mis-timed return


@node
def test_the_budget_never_repeats_a_kind_and_rations_whips(r):
    assert r["check"]["repeats"] == [{"a": 4, "b": 5, "kind": "zoom"}]     # cuts may repeat; zoom twice may not
    assert not r["check"]["ok"]
    assert r["whips"]["whips"] == pytest.approx(0.6) and any("whips are 60 %" in f for f in r["whips"]["findings"])
    assert r["pick"] == ["whip", "card", "cut"]                             # zoom and match touch their neighbours; whips over 40 %


@node
def test_a_bracket_of_one_kind_counts_once(r):
    # review 2026-10-22 (round 3): in "card" / out "card" (and cardToGraphic with until) failed the budget every time
    assert r["bracket"]["ok"] and r["bracket"]["n"] == 2
    assert r["between"]["ok"] and r["between"]["n"] == 3                 # a zoom inside: both ends stay, no repeat
    assert not r["after"]["ok"] and r["after"]["repeats"] == [{"a": 13, "b": 18, "kind": "card"}]   # card again after its return
    assert r["twoPairs"]["repeats"] == [{"a": 22, "b": 30, "kind": "fade"}]   # two brackets of one kind in a row: a repeat
    f = r["folded"]
    assert len(f) == 1 and f[0]["t"] == 8 and f[0]["until"] == 13 and f[0]["pair"] == 1 and "one bracket" in f[0]["why"]
    assert r["pickIn"] == "zoom"                                          # inside the bracket: card touches both ends
    assert r["pickAfter"] == "whip"                                       # after it: card would repeat the return


@node
def test_overlapping_takeovers_throw_and_a_short_face_gap_warns(r):
    assert "overlaps the one at 16.00-22.00" in r["overlap"] and "stay off" in r["overlap"]
    assert len(r["gap"]) == 1 and "1.50 s of his face" in r["gap"][0]    # 26 - 22 = 4 s is fine; an open span is skipped


@node
def test_the_type_kinds_cascading_line_fits_the_frame(r):
    long, short, fixed, serif = r["fit"]
    assert long["size"] == 200 and long["ts"] * 0.5 * 48 <= long["maxW"] + 1   # 48 characters at 0.5 em stay inside 1680 px
    assert long["ts"] < round(200 * 0.55)                                 # (it was 110 px: about 2480 px wide)
    assert short["ts"] == round(200 * 0.55)                               # a short line keeps 0.55 of the statement
    assert fixed["ts"] == 120                                             # an explicit size is the template's call
    assert serif["em"] == 0.34 and serif["ts"] == 0 and serif["size"] == 150


@node
def test_the_box_takeover_beat_returns_to_his_previous_show(r):
    b = r["tb"]["beats"]
    assert [(x["t"], x["show"]) for x in b] == [(0, "face"), (3, "beside"), (6, "takeover"), (11, "beside"), (16, "face")]
    assert b[3]["side"] == "left" and b[3]["tag"] == "takeover-back"
    assert r["tb"]["log"][0][3].startswith("inside the takeover 6-11: dropped")
    # the director: off at the takeover, his card back at 11 (after a hidden reset onto that slot), full at 16
    ats = [(t, at, mv) for t, at, mv, _ in r["direct"]]
    assert ats[2][1] == "off" and ats[2][0] == pytest.approx(5.96)
    assert any(at == "right" and t > 10 for t, at, mv in ats) and ats[-1][1] == "full"
    assert r["kept"] == [[0, "face"], [6, "takeover"], [11.2, "hero"]]     # a beat right after until is the return


@node
def test_a_blended_return_starts_from_its_own_slot_not_the_pill(r):
    # collapse into the pill, then "grow" back: a hidden cut onto the return's slot first (no lilac blob out of the pill)
    assert r["moved"][2][1] == "off" and r["moved"][2][2] == "collapse"
    assert r["moved"][3] == [9.84, "obj:0", "cut"] and r["moved"][4] == [9.9, "right", "grow"]


@node
def test_the_face_absent_note_is_12_s(r):
    assert r["plain"] == ["face absent 20.0 s (> 12 s)"]             # since his last face beat began


@node
def test_a_takeover_always_pushes_unless_push_false(r):
    """Fix round 2026-10-23: a takeover written with push: 0 held a still frame for 4-12 s. Its camera pushes 3.5 % over
    the hold by default (C.hold's 3-4 %); a positive push is kept; only push: false is still."""
    assert r["push"] == [0.035, 0.035, 0.035, 0.06, 0, 0.035]


# ---------------------------------------------------------------------------------------------------------- Chrome
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
chrome = pytest.mark.skipif(shutil.which("node") is None or not CHROME.exists() or not (ROOT / "node_modules/puppeteer-core").exists(),
                            reason="needs node, puppeteer-core and Google Chrome")
# a canvas page (a grey test card for him, never his face) with two takeovers and a zoom-through; D.look
PAGE = """<!doctype html><html lang="en"><head><meta charset="UTF-8" /><!--HF:KIT--></head><body>
<div id="root" data-composition-id="fx" data-start="0" data-duration="24" data-width="1920" data-height="1080" style="position:relative;width:1920px;height:1080px;overflow:hidden">
<img id="face" alt="" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'%3E%3Crect width='1920' height='1080' fill='%23889'/%3E%3C/svg%3E" /></div>
<script>
const D = /*D*/;
(function () {
  const tl = gsap.timeline({ paused: true });
  window.__timelines = { fx: tl };
  const K = HF.kit({ tl, id: "fx", width: 1920, height: 1080, words: [], pieces: [{ out_a: 0, out_b: 24 }] });
  const C = HF.canvas(K, document.getElementById("root"), { w: 5760, h: 3240, x: 960, y: 540, look: D.look });
  const T = HF.trans(K, C), F0 = C.station(0, 9, "mid", [960, 540]), F1 = C.station(8.9, 24, "mid", [2880, 540]);
  const c0 = C.card(F0, 200, 300, 600, 300, 0.3, { html: "<div class='cv-t' style='font-size:56px;padding:40px'>A card</div>", drift: false });
  const chip = C.chip(F1, 200, 700, "<span>a chip</span>", 9.5);
  C.takeover(3, 7.5, { kind: "type", in: "zoom", from: c0, text: "Neat beats *busy.*", out: "fade" });
  C.cam(5, { x: 2880, y: 540, z: 1 }, { dur: 0.01, sfx: false });          // under the plate: not a transition
  T.zoomThrough(11, chip, [960, 1620]);
  C.takeover(14, 18.5, { kind: "list", in: "card", title: "Three things", items: [["one", 14.6], ["two", 15.2], ["three", 15.8]], out: "cut" });
  C.speaker("face", [{ t: 0, mode: "card", x: 1500, y: 540, w: 560, h: 560, r: 280 }, { t: 11, mode: "card", x: 1500, y: 600, w: 500, h: 640, r: 32, cut: true }],
    { src: [1920, 1080], at: [960, 480], head: 300 });
  K.finish(24);
})();
</script></body></html>"""
PROBE = """
import { createRequire } from "node:module";
const puppeteer = createRequire(%(pkg)s)("puppeteer-core");
const [file] = process.argv.slice(2);
const br = await puppeteer.launch({ executablePath: %(chrome)s, headless: true, args: ["--allow-file-access-from-files"] });
const p = await br.newPage(), errs = [];
p.on("pageerror", (e) => errs.push(String(e.message || e)));
await p.setViewport({ width: 1920, height: 1080 });
await p.goto("file://" + file, { waitUntil: "domcontentloaded" });
await p.waitForFunction(() => !!(window.__timelines && window.__timelines.fx), { timeout: 60000 });
const r = await p.evaluate(() => {
  const tl = window.__timelines.fx, ts = [1, 2.75, 2.95, 3, 3.2, 5, 7.4, 7.6, 7.8, 8, 10.8, 10.95, 11, 11.2, 14.2, 14.7, 16, 18.6, 20];
  const roots = [...document.querySelectorAll("[data-takeover]")], view = roots[0].parentElement.querySelector("div[style*='z-index: 2']");
  const state = (t) => { tl.seek(t, false); const s = window.__speaker(t), fr = window.__faceRect(t);
    return { t, on: s.on, kind: s.kind, face: !!fr, roots: roots.map((e) => getComputedStyle(e).visibility === "visible" ? +getComputedStyle(e).opacity : 0),
      // what can be seen: every visible element's style (a hidden one may keep a tween's start values from one seek
      // direction and not the other, GSAP's immediateRender false; nobody sees it)
      dom: [...document.querySelectorAll("#root div, #root img")].map((e) => getComputedStyle(e).visibility === "hidden" ? "h"
        : [e.style.transform || "none", e.style.filter || "none", e.style.opacity === "" ? "1" : +e.style.opacity, e.style.left, e.style.top, e.style.clipPath].join("|")).join(";") }; };
  const fwd = ts.map(state), back = ts.slice().reverse().map(state).reverse(), jump = ts.map((t) => { tl.seek(23, false); return state(t); });
  const firstDiff = (A, B) => { for (let i = 0; i < A.length; i++) if (A[i].dom !== B[i].dom) { const a = A[i].dom.split(";"), b = B[i].dom.split(";"), k = a.findIndex((x, j) => x !== b[j]);
    return { t: A[i].t, el: k, a: a[k], b: b[k] }; } return null; };
  return { fwd: fwd.map(({ dom, ...x }) => x), sameBack: fwd.every((x, i) => x.dom === back[i].dom), sameJump: fwd.every((x, i) => x.dom === jump[i].dom),
    diff: firstDiff(fwd, back) || firstDiff(fwd, jump),
    trans: window.__trans(), takeovers: window.__takeovers };
});
console.log(JSON.stringify(Object.assign(r, { errs })));
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
@pytest.mark.parametrize("look", ["whitespace", "canvas_studio"])
def test_canvas_takeovers_take_him_off_log_the_transitions_and_seek_pure(tmp_path, look):
    out = run_page(tmp_path, {"look": look})
    st = {x["t"]: x for x in out["fwd"]}
    for t in (1, 2.95, 8, 10.8, 11.2, 20):                              # he is on outside the takeovers (and through the zoom)
        assert st[t]["on"] and st[t]["face"], (t, st[t])
    for t in (3, 3.2, 5, 7.4, 14.7, 16):                                 # off while a scene has the frame (in "card": after the morph)
        assert st[t]["kind"] == "off" and not st[t]["face"], (t, st[t])
    assert st[7.8]["on"] and st[7.6]["roots"][0] == 1 and st[8]["roots"] == [0, 0]   # out "fade": he fades in as the plate clears
    assert st[5]["roots"] == [1, 0] and st[14.2]["on"] and st[16]["roots"] == [0, 1] and st[18.6]["roots"] == [0, 0]   # out "cut": gone on the cut
    assert st[2.75]["roots"][0] == 0 and st[2.75]["kind"] in ("circle", "card")   # the zoom dives in before the takeover's plate
    kinds = [(x["t"], x["kind"]) for x in out["trans"]]
    assert kinds == [(3, "zoom"), (7.5, "fade"), (11, "zoom"), (14, "card"), (18.5, "cut")]   # the move at 5 s under the plate is not one
    assert out["sameBack"] and out["sameJump"], out["diff"]              # every frame a pure function of t
    assert [x["kind"] for x in out["takeovers"]] == ["type", "list"]


# HF.camera (scenes.js) pages publish window.__speaker through trans.js's wrapper: full, corner (PIP), off
CAM_PAGE = """<!doctype html><html lang="en"><head><meta charset="UTF-8" /><!--HF:KIT--></head><body>
<div id="root" data-composition-id="cam" data-start="0" data-duration="12" data-width="1920" data-height="1080" style="position:relative;width:1920px;height:1080px;overflow:hidden">
<img id="aroll" alt="" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'%3E%3Crect width='1920' height='1080' fill='%23889'/%3E%3C/svg%3E" /></div>
<script>
(function () {
  const tl = gsap.timeline({ paused: true });
  window.__timelines = { fx: tl };
  const pieces = [{ out_a: 0, out_b: 4, face: [960, 430, 300], tag: "intro" }, { out_a: 4, out_b: 8, face: [960, 430, 300], tag: "demo" }, { out_a: 8, out_b: 12, face: [960, 430, 300], tag: "end" }];
  const K = HF.kit({ tl, id: "fx", width: 1920, height: 1080, pieces, words: [] });
  const st = HF.stage(K, document.getElementById("root"), { aroll: "aroll" });
  HF.camera(K, st, { framing: { intro: "M", demo: "PIP", end: "OFF" }, sfx: false });
  K.finish(12);
})();
</script></body></html>"""
CAM_PROBE = """
import { createRequire } from "node:module";
const puppeteer = createRequire(%(pkg)s)("puppeteer-core");
const br = await puppeteer.launch({ executablePath: %(chrome)s, headless: true, args: ["--allow-file-access-from-files"] });
const p = await br.newPage(), errs = [];
p.on("pageerror", (e) => errs.push(String(e.message || e)));
await p.goto("file://" + process.argv[2], { waitUntil: "domcontentloaded" });
await p.waitForFunction(() => !!(window.__timelines && window.__timelines.fx), { timeout: 60000 });
const r = await p.evaluate(() => [1, 6, 10].map((t) => { window.__timelines.fx.seek(t, false); const s = window.__speaker(t); return { t, on: s.on, kind: s.kind, rect: s.rect, face: s.face }; }));
const lens = await p.evaluate(() => { const out = new Set(); for (let t = 0; t < 12; t += 0.1) { window.__timelines.fx.seek(t, false); out.add(window.__speaker(t).lens); } return [...out]; });
console.log(JSON.stringify({ r, lens, errs }));
await br.close();
"""


@chrome
def test_hf_camera_pages_publish_the_speaker_contract(tmp_path):
    import sys
    sys.path.insert(0, str(HF))
    import vendor
    vendor.copy_assets(tmp_path)
    f = tmp_path / "cam.html"
    f.write_text(vendor.inline(CAM_PAGE))
    js = tmp_path / "cam.mjs"
    js.write_text(CAM_PROBE % {"pkg": json.dumps(str(ROOT / "package.json")), "chrome": json.dumps(str(CHROME))})
    p = subprocess.run(["node", str(js), str(f)], capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["errs"] == []
    full, pip, off = out["r"]
    assert full["on"] and full["kind"] == "full" and full["face"] and full["rect"]["w"] == 1920
    assert pip["on"] and pip["kind"] == "corner" and pip["rect"]["w"] < 400 and pip["face"]
    assert not off["on"] and off["kind"] == "off" and off["face"] is None
    # HF.camera declares no holds: an idle frame reads "" so precheck's framing gate judges it (review 2026-10-22)
    assert "hold" not in out["lens"] and "" in out["lens"] and set(out["lens"]) <= {"", "push", "punch"}


# review 2026-10-22, on a canvas: a second speaker hidden at a stays hidden (as films/oss-editor's screen recording),
# template shots inside a takeover are named, a chapter whose t0 snaps to a downbeat keeps the template's return at
# t1, and the cover over a morphing card is opaque on canvas_studio (rgba(255,255,255,.92) cards)
EDGE = """<!doctype html><html lang="en"><head><meta charset="UTF-8" /><!--HF:KIT--></head><body>
<div id="root" data-composition-id="fx" data-start="0" data-duration="20" data-width="1920" data-height="1080" style="position:relative;width:1920px;height:1080px;overflow:hidden">
<img id="screen" alt="" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'%3E%3Crect width='1920' height='1080' fill='%2300a'/%3E%3C/svg%3E" />
<img id="face" alt="" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'%3E%3Crect width='1920' height='1080' fill='%23889'/%3E%3C/svg%3E" /></div>
<script>
const D = /*D*/;
(function () {
  const tl = gsap.timeline({ paused: true });
  window.__timelines = { fx: tl };
  window.__warns = [];
  const w0 = console.warn; console.warn = (...a) => { window.__warns.push(a.join(" ")); w0.apply(console, a); };
  const K = HF.kit({ tl, id: "fx", width: 1920, height: 1080, words: [], pieces: [{ out_a: 0, out_b: 20 }] });
  const C = HF.canvas(K, document.getElementById("root"), { w: 5760, h: 3240, x: 960, y: 540, look: D.look });
  const T = HF.trans(K, C);
  C.station(0, 20, "mid", [960, 540]);
  C.takeover(8, 12, { kind: "list", in: "card", title: "Three things", items: [["one", 8.6], ["two", 9.2], ["three", 9.8]], out: "card" });
  T.chapter(14, 15.8, { num: "02", title: "The pipeline", to: [2880, 540] });
  C.cam(8.6, { x: 1920, y: 540, z: 1 }, { dur: 0.01, sfx: false });        // under the list's plate (after the morph): no transition
  C.cam(8.3, { x: 960, y: 1620, z: 1 }, { dur: 0.01, sfx: false });        // during the morph, the plate still fading in: a cut
  window.__scr = C.speaker("screen", [
    { t: 0, mode: "card", x: 700, y: 540, w: 1100, h: 620, r: 20 },
    { t: 4, mode: "card", x: 700, y: 540, w: 1100, h: 620, r: 20, off: true, cut: true },
    { t: 9, mode: "card", x: 700, y: 540, w: 1100, h: 620, r: 20, cut: true }], { src: [1920, 1080], at: [960, 540], head: 10 });
  window.__face = C.speaker("face", [
    { t: 0, mode: "card", x: 1600, y: 540, w: 500, h: 640, r: 32 },
    { t: 10, mode: "card", x: 1500, y: 540, w: 500, h: 640, r: 32, cut: true },
    { t: 15.8, mode: "card", x: 1000, y: 540, w: 600, h: 700, r: 32, cut: true }], { src: [1920, 1080], at: [960, 480], head: 300 });
  K.finish(20);
})();
</script></body></html>"""
EDGE_PROBE = """
import { createRequire } from "node:module";
const puppeteer = createRequire(%(pkg)s)("puppeteer-core");
const br = await puppeteer.launch({ executablePath: %(chrome)s, headless: true, args: ["--allow-file-access-from-files"] });
const p = await br.newPage(), errs = [];
p.on("pageerror", (e) => errs.push(String(e.message || e)));
await p.setViewport({ width: 1920, height: 1080 });
await p.goto("file://" + process.argv[2], { waitUntil: "domcontentloaded" });
await p.waitForFunction(() => !!(window.__timelines && window.__timelines.fx), { timeout: 60000 });
const r = await p.evaluate(() => {
  const tl = window.__timelines.fx, box = (s) => ({ op: +s.box.style.opacity, x: Math.round(parseFloat(s.box.style.left)), w: Math.round(parseFloat(s.box.style.width)) });
  const at = (t) => { tl.seek(t, false); const s = window.__speaker(t);
    // the covers: decor divs over his shape (z 4, no pointer events) with a background while a card morphs
    const covers = [...document.querySelectorAll("#root > div")].filter((e) => e.style.zIndex === "4" && e.style.pointerEvents === "none" && +e.style.opacity > 0.01 && /rgb/.test(e.style.background));
    return { t, screen: box(window.__scr), face: box(window.__face), on: s.on, kind: s.kind, rect: s.rect, covers: covers.map((e) => e.style.background) }; };
  return { st: [2, 6, 8.3, 8.45, 9, 11.9, 12.2, 12.4, 13, 15.95, 17, 19].map(at), takeovers: window.__takeovers, warns: window.__warns,
    trans: window.__trans().map((x) => [x.t, x.kind]) };
});
console.log(JSON.stringify(Object.assign(r, { errs })));
await br.close();
"""


@chrome
@pytest.mark.parametrize("look,downbeat", [("canvas_studio", 14.1), ("whitespace", 13.9)])
def test_takeovers_leave_hidden_speakers_hidden_and_keep_the_chapter_return(tmp_path, look, downbeat):
    import sys
    sys.path.insert(0, str(HF))
    import vendor
    vendor.copy_assets(tmp_path)
    f = tmp_path / "edge.html"
    D = {"look": look, "music": {"beats": [downbeat], "downbeats": [downbeat], "sections": []}}
    f.write_text(vendor.inline(EDGE).replace("/*D*/", json.dumps(D)))
    js = tmp_path / "edge.mjs"
    js.write_text(EDGE_PROBE % {"pkg": json.dumps(str(ROOT / "package.json")), "chrome": json.dumps(str(CHROME))})
    p = subprocess.run(["node", str(js), str(f)], capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["errs"] == [], out["errs"]
    st = {x["t"]: x for x in out["st"]}
    assert st[2]["screen"]["op"] == 1                                       # the screen recording plays before 4 s
    for t in (6, 8.3, 8.45, 9, 11.9, 12.2, 12.4, 13, 15.95, 17, 19):        # hidden at 8: never shown again (its shot at 9 fell inside)
        assert st[t]["screen"]["op"] == 0, (t, st[t]["screen"])
    assert 0.05 < st[8.3]["face"]["op"] and st[8.3]["face"]["w"] > 520     # his card (the primary) morphs into the list card
    assert st[9]["kind"] == "off" and st[13]["on"] and st[13]["kind"] == "card"
    # the cover over his morphing card is opaque on every look (canvas_studio's card colour is 92 % white)
    assert st[8.45]["covers"] and all(c.startswith("rgb(") for c in st[8.45]["covers"]), st[8.45]["covers"]
    # the chapter's t0 snaps to the downbeat; t1 stays at 15.8, so the template's card there is his return
    for t in (15.95, 17):
        assert st[t]["on"] and st[t]["kind"] == "card" and abs(st[t]["face"]["x"] - 700) <= 2, (t, st[t])
    tk = out["takeovers"]
    assert [(x["kind"], x["a"], x["b"]) for x in tk] == [("list", 8, 12), ("chapter", pytest.approx(downbeat), pytest.approx(15.8))]
    assert sorted((d["speaker"], d["t"]) for d in tk[0]["dropped"]) == [("face", 10), ("screen", 9)]
    assert tk[1]["dropped"] == []
    assert sum("dropped his shot at 10.00" in w for w in out["warns"]) == 1   # said once, however often it re-plans
    # the camera's own moves: the cut under the plate is none, the one while the plate fades in over the morph is one
    assert [k for t, k in out["trans"]] == ["card", "cut", "card", "chapter", "zoom"], out["trans"]
    assert out["trans"][1][0] == pytest.approx(8.3, abs=0.04)


# review 2026-10-22 (round 3): soft entrances and exits out of / back into a FULL-BLEED frame. A saturated block sits on
# the station under his frame, never on screen: it must not show through at any of them. The control (D.full false: his
# card beside it, the station on screen) shows it, so the probe can see it. Also: overlapping takeovers throw, a T.match
# clone keeps one scale, a takeover's in / out of one kind is one bracket in window.__trans, and every frame is pure.
FULL = """<!doctype html><html lang="en"><head><meta charset="UTF-8" /><!--HF:KIT--></head><body>
<div id="root" data-composition-id="fx" data-start="0" data-duration="40" data-width="1920" data-height="1080" style="position:relative;width:1920px;height:1080px;overflow:hidden">
<img id="face" alt="" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'%3E%3Crect width='1920' height='1080' fill='%23889'/%3E%3C/svg%3E" /></div>
<script>
const D = /*D*/;
(function () {
  const tl = gsap.timeline({ paused: true });
  window.__timelines = { fx: tl };
  const K = HF.kit({ tl, id: "fx", width: 1920, height: 1080, words: [], pieces: [{ out_a: 0, out_b: 40 }] });
  const C = HF.canvas(K, document.getElementById("root"), { w: 5760, h: 3240, x: 960, y: 540, look: D.look });
  const T = HF.trans(K, C), F0 = C.station(0, 41, "mid", [960, 540]);
  K.el(F0, "left:20px;top:300px;width:180px;height:420px;background:#E0119D");
  const chip = C.chip(F0, 1300, 880, "<span>this chip flies</span>", 0.4), chip2 = C.chip(F0, 300, 120, "<span>a wide chip</span>", 0.4);
  const card2 = C.card(F0, 600, 300, 300, 500, 0.4, { html: "<div class='cv-t' style='font-size:40px;padding:30px'>Tall</div>", drift: false, ry: 0 });
  const items = (a) => [["one", a + 0.8], ["two", a + 1.4], ["three", a + 2]];
  C.takeover(6, 11, { kind: "list", in: "card", title: "Three things", items: items(6), out: "card" });
  C.takeover(17, 22, { kind: "type", in: "fade", text: "Neat beats busy.", out: "fade" });
  C.takeover(28, 33, { kind: "list", in: "match", match: chip, title: "Three more", items: items(28), out: "fade" });
  try { C.takeover(20, 26, { kind: "type", text: "Overlaps" }); window.__over = "no error"; } catch (e) { window.__over = e.message; }
  try { T.cardToGraphic(9, card2, { until: 12 }); window.__over2 = "no error"; } catch (e) { window.__over2 = e.message; }
  T.match(36, chip2, card2);
  C.speaker("face", [D.full ? { t: 0, mode: "frame", full: true } : { t: 0, mode: "card", x: 1500, y: 540, w: 500, h: 640, r: 32 }],
    { src: [1920, 1080], at: [960, 480], head: 300, lens: false });
  K.finish(40);
})();
</script></body></html>"""
FULL_PROBE = """
import { createRequire } from "node:module";
const puppeteer = createRequire(%(pkg)s)("puppeteer-core");
const [file, out] = process.argv.slice(2);
const br = await puppeteer.launch({ executablePath: %(chrome)s, headless: true, args: ["--allow-file-access-from-files"] });
const p = await br.newPage(), errs = [];
p.on("pageerror", (e) => errs.push(String(e.message || e)));
await p.setViewport({ width: 1920, height: 1080 });
await p.goto("file://" + file, { waitUntil: "domcontentloaded" });
await p.waitForFunction(() => !!(window.__timelines && window.__timelines.fx), { timeout: 60000 });
const ts = [5.9, 6.275, 8, 11.275, 17.175, 22.2, 28.125, 33.2];
const st = [];
for (const t of ts) {
  st.push(await p.evaluate((t) => { window.__timelines.fx.seek(t, false);
    const view = [...document.querySelectorAll("#root > div")].find((e) => e.style.zIndex === "2");
    return { t, clip: getComputedStyle(view).clipPath, vis: getComputedStyle(view).visibility, kind: window.__speaker(t).kind }; }, t));
  await new Promise((r) => setTimeout(r, 60));
  await p.screenshot({ path: out + "/full_" + t + ".png", clip: { x: 0, y: 250, width: 280, height: 520 } });
}
const r = await p.evaluate(() => {
  const tl = window.__timelines.fx, ts = [5.9, 6.1, 6.275, 6.5, 8, 11.1, 11.275, 11.5, 17.175, 17.3, 22.2, 22.35, 28.125, 28.3, 33.2, 36.25, 39];
  const dom = (t) => { tl.seek(t, false); return [...document.querySelectorAll("#root div, #root img")].map((e) => getComputedStyle(e).visibility === "hidden" ? "h"
    : [e.style.transform || "none", e.style.opacity === "" ? "1" : +e.style.opacity, e.style.left, e.style.top, e.style.clipPath].join("|")).join(";"); };
  const fwd = ts.map(dom), back = ts.slice().reverse().map(dom).reverse(), jump = ts.map((t) => { tl.seek(39.5, false); return dom(t); });
  // the match in flight: the box's clones (inside the overflow:hidden box) each at one scale
  tl.seek(36.25, false);
  const ov = [...document.querySelectorAll("div")].filter((e) => e.style.zIndex === "9").pop();
  const clones = [...ov.lastElementChild.lastElementChild.children].map((c) => c.style.transform);   // (the flight's clip box)
  const boxes = [...ov.lastElementChild.children].map((b) => [parseFloat(b.style.borderRadius), parseFloat(b.style.width), parseFloat(b.style.height)]);
  return { pure: fwd.every((x, i) => x === back[i] && x === jump[i]), clones, boxes, trans: window.__trans(), check: HF.trans.check(window.__trans()), over: window.__over, over2: window.__over2 };
});
console.log(JSON.stringify(Object.assign(r, { st, errs })));
await br.close();
"""


@chrome
@pytest.mark.parametrize("look", ["whitespace", "canvas_studio"])
@pytest.mark.parametrize("full", [True, False])
def test_a_full_bleed_frame_never_lets_the_hidden_canvas_through(tmp_path, look, full):
    import sys
    from PIL import Image
    sys.path.insert(0, str(HF))
    import vendor
    vendor.copy_assets(tmp_path)
    f = tmp_path / "full.html"
    f.write_text(vendor.inline(FULL).replace("/*D*/", json.dumps({"look": look, "full": full})))
    js = tmp_path / "full.mjs"
    js.write_text(FULL_PROBE % {"pkg": json.dumps(str(ROOT / "package.json")), "chrome": json.dumps(str(CHROME))})
    p = subprocess.run(["node", str(js), str(f), str(tmp_path)], capture_output=True, text=True, timeout=240)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["errs"] == [], out["errs"]

    def pink(t):                                                          # pixels of the hidden block (R over G: the grey test
        px = Image.open(tmp_path / f"full_{t}.png").convert("RGB").tobytes()   # card and the papers stay under 10; a quarter of
        return sum(1 for i in range(0, len(px), 3) if px[i] - px[i + 1] > 30)  # the block through a dissolve reads about 50)

    soft = [6.275, 11.275, 17.175, 22.2, 28.125, 33.2]                    # half-way through each soft in and out
    st = {x["t"]: x for x in out["st"]}
    if full:
        for t in [5.9] + soft:
            assert pink(t) == 0, (t, pink(t))
        for t in soft:                                                    # the view is hidden while the plate takes over
            assert st[t]["clip"] == "inset(50%)" or st[t]["vis"] == "hidden", st[t]
        assert st[5.9]["kind"] == "full" and st[8]["kind"] == "off"
    else:                                                                 # the control: the station is on screen, so it shows
        assert all(pink(t) > 500 for t in soft), [pink(t) for t in soft]
        assert st[6.275]["clip"] in ("none", "")
    assert out["pure"]                                                    # every frame a pure function of t
    assert "overlaps the one at 17.00-22.00" in out["over"]
    assert "overlaps the one at 6.00-11.00" in out["over2"]
    # T.match: one scale per clone (scale(s), never scale(sx, sy)), and the box's corner within its half side
    assert out["clones"] and all("scale(" in c and "," not in c.split("scale(")[1] for c in out["clones"]), out["clones"]
    assert all(r <= min(w, h) / 2 + 0.5 for r, w, h in out["boxes"]), out["boxes"]
    # the brackets: card there and back, fade there and back each count once; the budget holds
    kinds = [(x["t"], x["kind"], x.get("until")) for x in out["trans"]]
    assert kinds == [(6, "card", 11), (17, "fade", 22), (28, "match", None), (33, "fade", None), (36, "match", None)], kinds
    assert out["check"]["ok"], out["check"]


# HF.studio / HF.reel: a takeover after S.box() would never take him off (the director plans once): it throws
STUDIO_LATE = """<!doctype html><html lang="en"><head><meta charset="UTF-8" /><!--HF:KIT--></head><body>
<div id="root" data-composition-id="fx" data-start="0" data-duration="12" data-width="1920" data-height="1080" style="position:relative;width:1920px;height:1080px;overflow:hidden">
<img id="aroll" alt="" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'%3E%3Crect width='1920' height='1080' fill='%23889'/%3E%3C/svg%3E" /></div>
<script>
(function () {
  const tl = gsap.timeline({ paused: true });
  window.__timelines = { fx: tl };
  const K = HF.kit({ tl, id: "fx", width: 1920, height: 1080, words: [], pieces: [{ out_a: 0, out_b: 12, face: [960, 430] }] });
  const st = HF.stage(K, document.getElementById("root"), { aroll: "aroll" });
  const S = HF.studio(K, document.getElementById("root"), st, { end: 12, talk: 11.7, look: "whitespace" });
  S.beat(0, "face");
  S.takeover(2, 6.5, { kind: "type", text: "Before the box." });
  S.box();
  try { S.takeover(7, 11.5, { kind: "type", text: "After the box." }); window.__late = "no error"; } catch (e) { window.__late = e.message; }
  K.finish(12);
})();
</script></body></html>"""
LATE_PROBE = """
import { createRequire } from "node:module";
const puppeteer = createRequire(%(pkg)s)("puppeteer-core");
const br = await puppeteer.launch({ executablePath: %(chrome)s, headless: true, args: ["--allow-file-access-from-files"] });
const p = await br.newPage(), errs = [];
p.on("pageerror", (e) => errs.push(String(e.message || e)));
await p.goto("file://" + process.argv[2], { waitUntil: "domcontentloaded" });
await p.waitForFunction(() => !!(window.__timelines && window.__timelines.fx), { timeout: 60000 });
const r = await p.evaluate(() => ({ late: window.__late, kinds: [1, 4, 8].map((t) => { window.__timelines.fx.seek(t, false); return window.__speaker(t).kind; }) }));
console.log(JSON.stringify({ r, errs }));
await br.close();
"""


@chrome
def test_a_studio_takeover_after_the_box_throws(tmp_path):
    import sys
    sys.path.insert(0, str(HF))
    import vendor
    vendor.copy_assets(tmp_path)
    f = tmp_path / "late.html"
    f.write_text(vendor.inline(STUDIO_LATE))
    js = tmp_path / "late.mjs"
    js.write_text(LATE_PROBE % {"pkg": json.dumps(str(ROOT / "package.json")), "chrome": json.dumps(str(CHROME))})
    p = subprocess.run(["node", str(js), str(f)], capture_output=True, text=True, timeout=180)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["errs"] == [], out["errs"]
    assert "after S.box()" in out["r"]["late"]
    assert out["r"]["kinds"][1] == "off" and out["r"]["kinds"][0] != "off"   # the one declared before the box takes him off
