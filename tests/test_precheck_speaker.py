"""kit/qa/precheck.mjs since 2026-10-22 (kit v11): the SPEAKER section (window.__speaker, else __faceRect / __box), the
DENSITY gate, transitions from window.__trans, the 'still' check crediting camera moves, and the layout gate from
__speaker. The measurements are pure functions in kit/qa/speaker.mjs, run here in node; then the real precheck runs in
headless Chrome on the fixture page kit/hf/demos/audit/src/speaker.html, with the contract and with only __faceRect."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEAKER = ROOT / "kit/qa/speaker.mjs"
FIXTURE = ROOT / "kit/hf/demos/audit/src/speaker.html"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
needs_chrome = pytest.mark.skipif(shutil.which("node") is None or not CHROME.exists(), reason="needs node and Google Chrome")

JS = """
const SP = await import(%s);
const step = 0.2, FW = 1920, FH = 1080;
const at = (a, b, f) => { const out = []; for (let t = a; t < b - 1e-6; t += step) out.push({ t: +t.toFixed(3), src: "__speaker", ...f(+t.toFixed(3)) }); return out; };
const card = (o = {}) => ({ on: true, kind: "card", rect: { x: 1200, y: 240, w: 560, h: 600 }, face: { x: 1380, y: 330, w: 200, h: 240 }, zoom: 1, lens: "", ...o });
const off = { on: false, kind: "off", rect: null, face: null, zoom: 1, lens: "" };
const grow = (k) => ({ x: 1480 - 100 * k, y: 450 - 120 * k, w: 200 * k, h: 240 * k });
const R = {};
// a slow push (+10 %% over 6 s) is a framing change; a held card is not
R.push = SP.speakerStats([...at(0, 10, () => card()), ...at(10, 16, (t) => card({ face: grow(1 + 0.1 * (t - 10) / 6) })), ...at(16, 20, () => card({ face: grow(1.1) }))], { step, FW, FH });
// a whip: the face crosses the frame in 0.6 s, many samples over 2 %% -> one move
R.whip = SP.speakerStats([...at(0, 5, () => card()), ...at(5, 5.6, (t) => card({ face: { x: 1380 - 1800 * (t - 5), y: 330, w: 200, h: 240 } })), ...at(5.6, 10, () => card({ face: { x: 300, y: 330, w: 200, h: 240 } }))], { step, FW, FH });
// a declared hold of 12 s, an undeclared one of 12 s, away 13 s, off in the hook
R.hold = SP.speakerFindings(SP.speakerStats([...at(0, 1, () => off), ...at(1, 13, () => card({ lens: "hold" })), ...at(13, 26, () => off), ...at(26, 38, () => card({ rect: { x: 100, y: 240, w: 560, h: 600 }, face: { x: 280, y: 330, w: 200, h: 240 } }))], { step, FW, FH }), { longForm: false });
// a long-form share: off 10 %% -> faceoff MEDIUM only on long-form
const lf = SP.speakerStats([...at(0, 54, (t) => card({ face: grow(1 + 0.05 * Math.floor(t / 6)) })), ...at(54, 60, () => off)], { step, FW, FH });
R.lf = { long: SP.speakerFindings(lf, { longForm: true }).map((f) => f.kind), reel: SP.speakerFindings(lf, { longForm: false }).map((f) => f.kind), off: lf.off };
// zoom budgets: the sample's own, its track's, his track by name, the default
R.budget = [SP.budgetOf({ max_zoom: 1.5 }, { face: 1.1 }), SP.budgetOf({ track: "room" }, { room: 1.3, face: 1.1 }), SP.budgetOf({}, { room: 1.3, face: 1.1 }),
  SP.budgetOf({}, { room: 1.3 }), SP.budgetOf({}, {})];
// the tracks.json contract (P-M2) when the sample publishes no max_zoom: max(1, sharp_px / S), the kind playing at t wins
const TJ = { face: { sharp_px: 1080, max_zoom: 1.0, soft: 0.24, kinds: { cam: { sharp_px: 540 } } } };
const bs = (s, T = TJ, o = {}) => { const b = SP.budgetsOf({ t: 1, ...s }, T, o); return [b.sharp, b.soft, b.how, b.kind || null]; };
R.budgets = { card: bs({ rect: { x: 0, y: 0, w: 560, h: 600 } }), frame: bs({}), cam: bs({}, TJ, { pieces: [{ kind: "cam", out_a: 0 }] }),
  sample: bs({ max_zoom: 1.5 }), track: bs({}, { face: { max_zoom: 1.1, soft_zoom: 1.3 } }) };
const z = SP.speakerStats(at(0, 6, (t) => card({ zoom: 1 + 0.06 * t })), { step, FW, FH, tracks: { face: 1.2 } });
R.zoom = { max: z.zoom.max, over: z.zoom.over.map((r) => [r.a, +r.max.toFixed(2)]), sev: SP.speakerFindings(z).filter((f) => f.kind === "upscale").map((f) => f.sev) };
// no speaker published at all: nothing measured, nothing flagged
R.none = SP.speakerFindings(SP.speakerStats(at(0, 30, () => ({ ...off, src: "none" })).map((s) => ({ ...s, src: "none" })), { step, FW, FH }));
// density: > 3 groups for exactly 2 s is not a finding; 2.2 s is MEDIUM; 6 groups for 2.2 s is HIGH
const dn = (n, a, b) => at(a, b, () => ({ n, labels: [] }));
R.den = [[...dn(1, 0, 3), ...dn(4, 3, 5), ...dn(1, 5, 8)], [...dn(4, 0, 2.2), ...dn(1, 2.2, 4)], [...dn(6, 0, 2.2), ...dn(2, 2.2, 4)]]
  .map((S) => SP.densityStats(S, step).findings.map((f) => f.sev));
// transitions: cuts may repeat, a whip twice is MEDIUM, whips over 40 %%
R.tr = SP.transStats([{ t: 1, kind: "cut" }, { t: 2, kind: "cut" }, { t: 3, kind: "whip" }, { t: 4, kind: "whip" }, { t: 5, kind: "zoom" }]);
R.slots = [SP.slotOf({ on: true, kind: "card", rect: { x: 1200, y: 0, w: 500, h: 500 } }, FW, FH), SP.slotOf({ on: true, kind: "circle", rect: { x: 760, y: 300, w: 400, h: 400 } }, FW, FH),
  SP.slotOf({ on: true, kind: "full", rect: { x: 0, y: 0, w: FW, h: FH } }, FW, FH), SP.slotOf({ on: false }, FW, FH), SP.mergeSides("small card right"), SP.mergeSides("card centre"),
  SP.slotOf({ on: true, kind: "card", rect: { x: 100, y: 1300, w: 880, h: 500 } }, 1080, 1920), SP.mergeSides(SP.slotOf({ on: true, kind: "card", rect: { x: 100, y: 100, w: 500, h: 500 } }, FW, FH))];
// the fallback for pages without __speaker (review 2026-10-22): the page's own face decides on / off; the box names the
// kind only while shown; a full-bleed plate of his footage is him
const fb = (o) => { const s = SP.fallbackSpeaker({ FW, FH, ...o }); return [s.src, s.on, s.kind, !!s.face, s.rect ? s.rect.w : null, s.est]; };
const hidden = { cx: 1480, cy: 540, w: 560, h: 600, op: 0 }, shownBox = { ...hidden, op: 1 }, plate = { x: -100, y: -60, w: 2120, h: 1200 };
const face = { x: 820, y: 220, w: 280, h: 340 };
R.fb = { hiddenBoxFace: fb({ faceRect: true, face, box: hidden, boxed: true, plate }), hiddenBoxFaceNoPlate: fb({ faceRect: true, face, box: hidden, boxed: true }),
  shownBoxFace: fb({ faceRect: true, face, box: shownBox, boxed: true }), plateOnly: fb({ faceRect: true, face: null, plate }), nothing: fb({ faceRect: true, face: null }),
  boxZone: fb({ face, box: shownBox, boxed: true }), boxHidden: fb({ face: null, box: hidden, boxed: true }), none: fb({}), offFrame: fb({ faceRect: true, face: { x: 2000, y: 0, w: 100, h: 100 } }) };
// the contract allows rect and face null: frame from the published zoom (a push is a change), and with no zoom either
// the time is unmeasured, never "unchanged"
const full = (o) => ({ on: true, kind: "full", rect: null, face: null, lens: "push", ...o });
const zp = SP.speakerStats(at(0, 30, (t) => full({ zoom: 1 + 0.12 * t / 30 })), { step, FW, FH });
const zn = SP.speakerStats(at(0, 30, () => full({ zoom: null, lens: "" })), { step, FW, FH });
R.zonly = { moves: zp.moves, longest: zp.longest.dur, framing: SP.speakerFindings(zp).filter((f) => f.kind === "framing").map((f) => f.sev),
  un: zn.unmeasured, stretches: zn.stretches.length, unFindings: SP.speakerFindings(zn).map((f) => f.kind) };
// estimated on / off (no __speaker): away and hook say so, and away stays MEDIUM
const est = SP.speakerStats([...at(0, 1, () => off), ...at(1, 10, () => card()), ...at(10, 23, () => off), ...at(23, 30, () => card())].map((s) => ({ ...s, src: "__faceRect" })), { step, FW, FH });
R.est = { est: est.est, f: SP.speakerFindings(est).filter((f) => f.kind !== "framing").map((f) => [f.kind, f.sev, f.text.startsWith("estimated (no window.__speaker)")]) };
// a corner held 20 s through an insert is not judged (plan_check skips a corner too); into and out of it are changes
const cn = SP.speakerStats([...at(0, 5, () => card()), ...at(5, 25, () => card({ kind: "corner", rect: { x: 1500, y: 760, w: 380, h: 280 }, face: { x: 1620, y: 800, w: 100, h: 120 } })),
  ...at(25, 30, () => card())], { step, FW, FH });
R.corner = { corner: cn.corner, framing: SP.speakerFindings(cn).filter((f) => f.kind === "framing").length, changes: cn.changes.map((t) => +t.toFixed(1)), perMin: cn.perMin };
// the 35 %% layout gate: kit/film/example's shares (card right 27 %%, left 23 %%), then xchakra-shorts-b's (card bottom 36 %%)
const ex = { "card right": 9.8, "card left": 8.2, "off (graphic)": 5.4, "small card left": 4.4, "full": 3.6, "small card right": 2.4, "card centre": 2.2 };
const xb = { "card bottom": 17.6, "full": 11.4, "corner top": 10.2, "off (graphic)": 7.4, "small card bottom": 2, "corner bottom": 0.5 };
const lg = (slots, contract) => SP.layoutGate(slots, 36, { contract }).findings.map((f) => [f.sev, f.text]);
R.layout = { exOld: lg(ex, false), exNew: lg(ex, true), xbOld: SP.layoutGate(xb, 49.1, {}).findings.map((f) => [f.sev, f.text]),
  xbList: SP.layoutGate(xb, 49.1, {}).list.map(([k]) => k), calm: lg({ "card right": 6, "full": 6, "off (graphic)": 6 }, true), none: lg({}, true) };
console.log(JSON.stringify(R));
"""


@pytest.fixture(scope="module")
def r():
    js = JS % json.dumps(SPEAKER.as_uri())
    out = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@needs_node
def test_a_slow_push_is_a_framing_change(r):
    p = r["push"]
    # +4 % scale is first crossed ~2.4 s into the push, and again ~2.4 s later from the new framing: a +10 % push over
    # 6 s reads as two framing changes, each its own move (more than 1 s apart)
    assert p["moves"] == 2 and 12 <= p["changes"][0] <= 13
    assert p["longest"]["a"] == 0 and 12 <= p["longest"]["dur"] <= 13   # 0 s to the first change: held


@needs_node
def test_a_whip_is_one_move_however_many_samples_cross(r):
    assert r["whip"]["moves"] == 1 and len(r["whip"]["changes"]) >= 2 and r["whip"]["perMin"] == 6.0


@needs_node
def test_declared_holds_away_and_hook(r):
    kinds = [(f["kind"], f["sev"], round(f["a"], 1)) for f in r["hold"]]
    assert ("framing", "MEDIUM", 26.0) in kinds                          # 12 s undeclared: MEDIUM (> 8, < 15)
    assert not any(k == "framing" and a == 1.0 for k, _, a in kinds)     # 12 s with lens "hold": declared, no finding
    assert ("away", "HIGH", 13.0) in kinds and ("hook", "MEDIUM", 0) in kinds


@needs_node
def test_face_off_share_is_a_long_form_rule(r):
    assert round(r["lf"]["off"], 2) == 0.1 and "faceoff" in r["lf"]["long"] and "faceoff" not in r["lf"]["reel"]


@needs_node
def test_zoom_budget(r):
    assert r["budget"] == [1.5, 1.3, 1.1, 1.3, 1.2]
    assert r["zoom"]["max"] == 1.348 and r["zoom"]["over"][0][0] == pytest.approx(3.4, abs=0.21)
    assert r["zoom"]["sev"] == ["HIGH"]                                  # 1.35 > 1.2 x 1.05


@needs_node
def test_zoom_budget_follows_the_tracks_contract_without_a_sample_cap(r):
    b = r["budgets"]
    assert b["card"] == [1.8, 1.8, "contract", None]                     # 1080 px of source in a 600 px card
    assert b["frame"] == [1, 1.24, "contract", None]                     # full height: 1, soft tier 1 + 0.24
    assert b["cam"] == [1, 1.12, "contract", "cam"]                      # the kind playing at t wins over the track's
    assert b["sample"] == [1.5, None, "sample", None] and b["track"] == [1.1, 1.3, "track", None]


@needs_node
def test_no_speaker_published_flags_nothing(r):
    assert r["none"] == []


@needs_node
def test_density_thresholds(r):
    assert r["den"] == [[], ["MEDIUM"], ["HIGH"]]


@needs_node
def test_transitions(r):
    assert r["tr"]["kinds"] == {"cut": 2, "whip": 2, "zoom": 1} and [x["kind"] for x in r["tr"]["repeats"]] == ["whip"]
    assert [f["text"].split(" ")[0] for f in r["tr"]["findings"]] == ["'whip'"]     # 2/5 = 40 %: not over


@needs_node
def test_slots_name_the_side_and_precheck_merges_them(r):
    # slotOf says which side (precheck prints the split); mergeSides makes left / right / top / bottom one layout
    assert r["slots"] == ["card right", "circle centre", "full", "off (takeover)", "small card beside", "card centre", "card bottom", "card beside"]


@needs_node
def test_fallback_trusts_the_pages_own_face(r):
    fb = r["fb"]
    # [src, on, kind, has face, rect width, est]
    assert fb["hiddenBoxFace"] == ["__faceRect", True, "full", True, 2120, True]       # claude-makes-claude: box op 0, A-roll full frame
    assert fb["hiddenBoxFaceNoPlate"] == ["__faceRect", True, "?", True, None, True]   # on; the kind unknown
    assert fb["shownBoxFace"] == ["__faceRect", True, "card", True, 560, True]
    assert fb["plateOnly"] == ["__faceRect", True, "full", False, 2120, True]          # oss-editor-reels-a: the room plate opens
    assert fb["nothing"][1:3] == [False, "off"] and fb["offFrame"][1:3] == [False, "off"]
    assert fb["boxZone"] == ["__box", True, "card", False, 560, True]                  # the face zone is a guess: frame on the rect
    assert fb["boxHidden"] == ["__box", False, "off", False, None, True] and fb["none"][0:2] == ["none", False]


@needs_node
def test_contract_with_no_rect_or_face_frames_from_the_zoom(r):
    z = r["zonly"]
    assert z["moves"] >= 2 and z["longest"] < 15 and "HIGH" not in z["framing"]    # a +12 % push over 30 s is seen
    assert z["un"] == pytest.approx(30, abs=0.3) and z["stretches"] == 0 and "framing" not in z["unFindings"]


@needs_node
def test_estimated_on_off_is_labelled_and_never_high(r):
    assert r["est"]["est"] is True
    assert ["away", "MEDIUM", True] in r["est"]["f"] and ["hook", "MEDIUM", True] in r["est"]["f"]


@needs_node
def test_a_corner_is_not_judged_for_framing(r):
    # review 2026-10-22: a 20 s corner picture-in-picture during an insert was a framing HIGH that stopped the build;
    # plan_check never judges a corner, so precheck doesn't either. Into and out of the corner are framing changes
    c = r["corner"]
    assert c["corner"] == pytest.approx(20, abs=0.21) and c["framing"] == 0
    assert c["changes"] == [5.0, 25.0] and c["perMin"] == 12.0             # 2 moves over the 10 s he is framed


@needs_node
def test_layout_gate_merges_sides_on_contract_pages_only(r):
    L = r["layout"]
    # kit/film/example (no window.__speaker): no side over 35 % (it passed before v11), the merged 50 % is a MEDIUM
    assert len(L["exOld"]) == 1 and L["exOld"][0][0] == "MEDIUM" and '"card beside" for 50 %' in L["exOld"][0][1]
    assert "(right 27 %, left 23 %)" in L["exOld"][0][1] and "HIGH once it publishes it" in L["exOld"][0][1]
    # the same shares on a page that publishes the contract: HIGH
    assert len(L["exNew"]) == 1 and L["exNew"][0][0] == "HIGH" and '"card beside" for 50 %' in L["exNew"][0][1]
    # a page from before with one side over 35 %: the HIGH it always had, in its own words
    assert L["xbOld"] == [["HIGH", 'the speaker box is "card bottom" for 36 % of the runtime (max 35 %): vary it (beside, corner, hero, a takeover, a punch)']]
    # a corner is one layout wherever it sits (not 'beside' anything)
    assert L["xbList"][:3] == ["card beside", "full", "corner"] and L["calm"] == [] and L["none"] == []


# ---------------------------------------------------------------- the real precheck on the fixture page
@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    d = tmp_path_factory.mktemp("precheck_speaker")
    html = FIXTURE.read_text()
    out = {}
    for mode in ("speaker", "fallback", "boxhidden", "plate"):
        (d / mode).mkdir()
        (d / mode / "index.html").write_text(html.replace('const MODE = "speaker";', f'const MODE = "{mode}";'))
        js = d / f"{mode}.json"
        p = subprocess.run(["node", str(ROOT / "kit/qa/precheck.mjs"), str(d / mode / "index.html"), f"--json={js}"], capture_output=True, text=True, cwd=ROOT, timeout=180)
        out[mode] = (p.returncode, p.stdout, json.loads(js.read_text()))
    return out


def kinds(rep):
    return {(f["kind"], f["sev"], round(f["a"], 1)) for f in rep["findings"]}


@needs_chrome
def test_contract_page(pages):
    code, text, rep = pages["speaker"]
    k = kinds(rep)
    assert code == 3                                                      # HIGH findings stop a build
    assert ("framing", "HIGH", 0.0) in k and not any(x[0] == "framing" and x[2] == 30.0 for x in k)   # 30-40 s: a declared hold
    assert ("away", "HIGH", 40.0) in k and ("upscale", "MEDIUM", 23.8) in k
    assert ("density", "MEDIUM", 5.0) in k and ("density", "HIGH", 14.0) in k
    assert ("trans", "MEDIUM", 20.0) in k and ("layout", "HIGH", 0.0) in k
    sp = rep["speaker"]
    assert sp["src"] == "__speaker" and round(sp["on"], 2) == 0.68 and round(sp["full"], 2) == 0.17
    assert [t["dur"] for t in sp["takeovers"]] == [6.0, 13.0] and sp["zoom"]["budget"] == 1.25
    assert rep["density"]["max"] == 7 and rep["transitions"]["kinds"] == {"whip": 2, "zoom": 1, "cut": 2}
    assert rep["ambition"]["layouts"]["card beside"] == pytest.approx(31.0, abs=0.3)   # 24 s right + 7 s left: one layout
    # the 'still' check counts his framing changes and the transitions: the longest stretch is the static 13 s takeover,
    # not the 42 s from the last card (17.4 s) to the end
    assert rep["ambition"]["longestStill"] == pytest.approx(12.8, abs=0.3)


@needs_chrome
def test_fallback_page(pages):
    code, text, rep = pages["fallback"]
    k = kinds(rep)
    sp = rep["speaker"]
    assert sp["src"] == "__faceRect" and sp["full"] is None and sp["zoom"] is None and round(sp["on"], 2) == 0.68
    assert ("framing", "MEDIUM", 30.0) in k                              # no lens to declare the hold
    assert not any(x[0] in ("upscale", "layout") for x in k)             # no zoom, no kind: not measured
    assert ("away", "MEDIUM", 40.0) in k and sp["est"] is True           # on / off is a guess here: never HIGH
    assert "__faceRect fallback: on / off estimated" in text and "zoom not published" in text


@needs_chrome
def test_fallback_hidden_box_with_his_face_is_on(pages):
    # claude-makes-claude (review 2026-10-22): __box hidden the whole time, his A-roll full frame, __faceRect his face
    code, text, rep = pages["boxhidden"]
    k = kinds(rep)
    sp = rep["speaker"]
    assert round(sp["on"], 2) == 1.0 and round(sp["full"], 2) == 1.0 and sp["takeovers"] == []
    assert not any(x[0] in ("away", "hook", "framing") for x in k)        # his face moves 3 % every 6 s
    assert "off (graphic)" not in rep["ambition"]["layouts"] and rep["ambition"]["layouts"]["full"] == pytest.approx(60, abs=0.3)


@needs_chrome
def test_fallback_room_plate_opens_the_hook(pages):
    # oss-editor-reels-a: the first 3 s are his room plate (card hidden, __faceRect null); a full-bleed screen recording
    # in the 24-30 s takeover is not him
    code, text, rep = pages["plate"]
    k = kinds(rep)
    sp = rep["speaker"]
    assert not any(x[0] == "hook" for x in k) and [t["dur"] for t in sp["takeovers"]] == [6.0, 13.0]
    assert round(sp["on"], 2) == 0.68 and sp["fullMin"] is True and "full frame >= 5%" in text


@needs_chrome
def test_no_ambition_prints_the_new_gates_as_medium(tmp_path):
    (tmp_path / "index.html").write_text(FIXTURE.read_text())
    p = subprocess.run(["node", str(ROOT / "kit/qa/precheck.mjs"), str(tmp_path / "index.html"), "--no-ambition", f"--json={tmp_path / 'o.json'}"],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    rep = json.loads((tmp_path / "o.json").read_text())
    assert p.returncode == 0 and not [f for f in rep["findings"] if f["sev"] == "HIGH"]
